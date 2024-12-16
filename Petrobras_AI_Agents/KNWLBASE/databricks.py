from databricks import sql as dbks_sql
import json
import re
import os
import pandas as pd
from typing import Union, Callable, List, Dict, Optional, Any
from .base import BaseKnowledgeBaseManager
import os

from Petrobras_AI_Agents.READERS import read_file

from dotenv import load_dotenv
load_dotenv()

import logging

logger = logging.getLogger(__name__)

class KnowledgeBaseManager_Databricks(BaseKnowledgeBaseManager):

    config_file = ""
    
    @classmethod
    def create_config_file(
        cls,
        config_json,
        connection_server_hostname  = "adb-671799829240675.15.azuredatabricks.net",
        connection_http_path        = "/sql/1.0/warehouses/1fd972f888afd086",
        users_access_table_name     = "dtcore_prd.aida.acesso_usuario",
        users_access_profile_prefix = "GDB_DLKC_PRD_PFL_",
        db_functions_euclidean      = "dt0047_prd.db_functions.euclidean_distance",
        db_functions_cosine         = "dt0047_prd.db_functions.cosine_distance",
        source_col_name             = "source",
        file_col_name               = "file_as_str",
        context_col_name            = "page_content",
        rag_col_name                = "vector_embedding_3large",
        metadata_col_name           = "metadata_dictionary",
        file_base_id_col_name       = "id",
        vec_base_file_id_col_name   = "file_id"
        ):

        '''
        "data_sources": {
        "intimacoes_sefaz_rj": {
        "file_base": "dt0047_prd.chat_bot.intimacoes_fiscais_pgov_sefaz_rj_file_base",
        "vec_base": "dt0047_prd.chat_bot.intimacoes_fiscais_pgov_sefaz_rj_vec_base"
        },
        '''
    
        if not os.path.exists(config_json):
            os.makedirs(os.path.dirname(config_json), exist_ok=True)
            config = {
                "connection": 
                    {
                    "server_hostname" : connection_server_hostname,
                    "http_path"       : connection_http_path       
                    },
                "users_access": {
                    "table":  users_access_table_name,
                    "profile_prefix ": users_access_profile_prefix
                    },
                "columns":
                    {
                    "source_col"          : source_col_name,
                    "file_col"            : file_col_name,
                    "context_col"         : context_col_name,
                    "rag_col"             : rag_col_name,
                    "metadata_col"        : metadata_col_name,
                    "file_base_id_col"    : file_base_id_col_name,
                    "vec_base_file_id_col": vec_base_file_id_col_name
                    },
                "functions":
                    {
                    "euclidean": db_functions_euclidean,
                    "cosine"   : db_functions_cosine
                    },
                "data_sources":{}
            }

            # Salva o arquivo JSON
            with open(config_json, 'w', encoding='utf-8-sig') as arquivo:
                json.dump(config, arquivo, indent=2, ensure_ascii=False)

        # Update the config file name at the class level
        cls.config_file = config_json
    
    @classmethod  
    def add_data_source(cls, process_name, file_base, vec_base, config_json=None):
        # Carrega o arquivo de configuração existente
        config_json = config_json or cls.config_file
        if os.path.exists(config_json):
            with open(config_json, 'r', encoding='utf-8-sig') as arquivo:
                config = json.load(arquivo)
        else:
            raise FileNotFoundError(f"O arquivo {config_json} não foi encontrado.")
        
        # Adiciona um novo data source
        new_data_source = {
            process_name: {
                "file_base": file_base,
                "vec_base" : vec_base
            }
        }
        
        # Atualiza a seção de data_sources
        config["data_sources"].update(new_data_source)
        
        # Salva o arquivo de configuração com o novo data source
        with open(config_json, 'w', encoding='utf-8-sig') as arquivo:
            json.dump(config, arquivo, indent=2, ensure_ascii=False)
         
    def __init__(self, user, config_json=None, connection=None):
        config_json = config_json or self.__class__.config_file
        
        self.connection = connection or self._create_connection()
        super().__init__(config_json=config_json)
        
        self._ajust_grants_to_profile_id()
        self.available_collections = self._get_access_profile(user)

    def _get_dynamic_classes(self, collection_name, table_description=None):
        return {}       
    
    def _create_connection(self):
        
        if not hasattr(self, 'connection') or self.connection is None:
            print("create connection")
            access_token = os.getenv('DATABRICKS_CONN_TOKEN')
            try:
                connection = dbks_sql.connect(
                                server_hostname = self.config["connection"]["server_hostname"],
                                http_path = self.config["connection"]["http_path"] ,
                                access_token = access_token)                 
                print('Conected to Databricks')
                return connection
            except: 
                print('Connection fail')
                return
        return self.connection
            
    def _get_metadata_from_table(self, collection_name):
        logger.debug(f'get_metadata from {collection_name}')
        
        # Verifica se a conexão já existe antes de criar uma nova
        self.connection = self._create_connection()
        
        metadata = super()._get_metadata_from_table()

        tables = self.config["data_sources"][collection_name]
              
        try: # Acessing the table description
            table = tables["file_base"]
            cursor = self.connection.cursor()
            cursor.execute(f"DESCRIBE DETAIL {table}")
            result = cursor.fetchall()[0]['description'].replace("\\'", "'")
            metadata_dic_descr = result
            # metadata_dic_descr = json.loads(result)
        except Exception as e:
            # print(e)
            metadata_dic_descr = {'table_description': '', 'gpt_instructions': ''}      
        finally:
            try: cursor.close()
            except: pass              
            
        try:  # Acessando os Grants na tabela
            table = tables["file_base"]
            cursor = self.connection.cursor()
            cursor.execute(f"SHOW GRANTS ON TABLE {table}")
            result = cursor.fetchall()
            grants = list(set([row[0] for row in result]))  # Acessa a primeira coluna de cada linha (ajuste conforme necessário)
            
        except Exception as e:
            # print(e)
            grants = []
        finally:
            try: cursor.close()
            except: pass  

        # Acessing the table columns metadata
        try: 
            metadata_dic_col = {}
            cursor = self.connection.cursor()
            
            table = tables["file_base"]
            cursor.execute(f"DESCRIBE {table}")
            result = cursor.fetchall()
            metadata_dic_col["file_base"] = {row[0]:  f"TYPE: {row[1]} COMMENT: {row[2] }" for row in result}

            table = tables["vec_base"]
            cursor.execute(f"DESCRIBE {table}")
            result = cursor.fetchall()
            metadata_dic_col["vec_base"] = {row[0]:  f"TYPE: {row[1]} COMMENT: {row[2] }" for row in result}
            
        except Exception as e:
            # print(e)
            metadata_dic_col = {'Fail to load metadata': 'ignore'}
        finally:
            try: cursor.close()
            except: pass
        
        
        
        metadata["columns"] = metadata_dic_col
        metadata["description" ] = metadata_dic_descr
        metadata["grants"] = grants

        return metadata

    def get_table(self, sql_query=None, table=None):
        
        cursor = self.connection.cursor()
        
        if sql_query is None: sql_query = f'SELECT * FROM {table}'
        cursor.execute(sql_query)
        result = cursor.fetchall()

        return result
    
    def get_table_as_dictionary(self, sql_query=None, table=None):

        result = self.get_table(sql_query=sql_query, table=table)
        rows_as_dict = [row.asDict() for row in result]
        
        return rows_as_dict

    def similarity_search(self, collection_name:str, embedding, k: int = 10, filters:str = None, distance_strategy='cosine'):

        select_clause, from_clause, where_clause = super().similarity_search(collection_name, embedding, k, filters, distance_strategy)
        
        # Convertendo o embedding para um formato que pode ser usado na consulta SQL
        embedding_str      = f"ARRAY({', '.join(map(str, embedding))})"
        distance_func      = self.config["functions"][distance_strategy]
        distance_func      = f"{distance_func}( {self.config['columns']['rag_col']} , {embedding_str} )"
        select_clause     += f", {distance_func} AS distance"

        sql_query = f"""
            {select_clause}
            {from_clause}
            {where_clause}
            ORDER BY distance ASC
            LIMIT {k}
        """
        
        results = self.get_table_as_dictionary(sql_query)

        return results

    def retrieve_full_documents(self, collection_name, filters, read_file_class:read_file=read_file, k=5, words_per_chunk=2500, overlap=25):
        
        select_clause, from_clause, where_clause = super().retrieve_full_documents(collection_name, filters, read_file_class, k, words_per_chunk, overlap)
        
        sql_query = f"""
            {select_clause}
            {from_clause}
            {where_clause}
            LIMIT {k}
        """
        
        results = self.get_table_as_dictionary(sql_query)
        
        documents = {}
        for row in results:
            file_processor:read_file = read_file_class(file_name=row['source'], file_content=row['file_col'])
            processed_chunks:List[Dict] = file_processor.load_file_in_chuncks(words_per_chunk=2500, overlap=25)
            text = [chunk['page_content'] for chunk in processed_chunks]
            documents[row['source']] = text
        
        return documents

    def _ajust_grants_to_profile_id(self):
        
        profile_table = [{"profile_id": 999999, "collection": ""}]
        for table in self.config["data_sources"]:

            profile_prefix = self.config["users_access"]["profile_prefix "]

            self.config["data_sources"][table]['metadata']['grants'] = [
                int(profile[len(profile_prefix ):]) 
                for profile in self.config["data_sources"][table]['metadata']['grants'] 
                if profile.startswith(profile_prefix )]

            profile_table += [
                {"profile_id": p, "collection": table}
                for p in self.config["data_sources"][table]['metadata']['grants']]

        
        profile_table = pd.DataFrame(profile_table)
        self._profile_table = profile_table.drop_duplicates(subset=['profile_id', 'collection'])
          
    def _get_access_profile(self, user):
        table = self.config["users_access"]["table"]
        
        profile_ids = ','.join(map(str, self._profile_table['profile_id'].tolist()))

        sql = f'''
        SELECT PEPA_CD_PERFIL_PLATAFORMA as profile_id, VWRP_CD_ELEMENTO as user
        FROM {table}
        WHERE PEPA_CD_PERFIL_PLATAFORMA IN ({profile_ids})
        AND VWRP_CD_ELEMENTO = '{user.upper()}'
        '''
        result = self.get_table_as_dictionary(sql)
        if not result: result_df = pd.DataFrame(columns=["profile_id", "user"])
        else: result_df = pd.DataFrame(result)
        result_df = pd.merge(
            self._profile_table, 
            result_df, 
            on='profile_id', 
            how='inner'
        )

        result_df = result_df['collection'].unique().tolist()
        
        return result_df
