from .base import BaseDatabaseManager
from databricks import sql as dbks_sql
import json
import re
import os
import pandas as pd

from dotenv import load_dotenv
load_dotenv()

class DatabaseManager_Databricks(BaseDatabaseManager):
    
    config_file = ""
    
    @classmethod
    def create_config_file(
        cls,
        config_json,
        connection_server_hostname  = "adb-671799829240675.15.azuredatabricks.net",
        connection_http_path        = "/sql/1.0/warehouses/1fd972f888afd086",
        users_access_table_name     = "dtcore_prd.aida.acesso_usuario",
        users_access_profile_prefix = "GDB_DLKC_PRD_PFL_",
        data_sources                = {}
        ):
        
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
                    "profile_prefix": users_access_profile_prefix
                    },
                "data_sources": data_sources
            }

            # Salva o arquivo JSON
            with open(config_json, 'w', encoding='utf-8-sig') as arquivo:
                json.dump(config, arquivo, indent=2, ensure_ascii=False)

        # Update the config file name at the class level
        cls.config_file = config_json

    @classmethod  
    def add_data_source(cls, collection, process_description, relationships, tables:dict, config_json=None):
        '''
        tables: inform as a dict with the table name and the address of the table.
            example:
                {
                    "base_h": "dt0047_prd.gastos.base_h_pgov_sefaz_rj_gastos",
                    "base_r": "dt0047_prd.gastos.base_r_pgov_sefaz_rj_gastos"
                }

        "data_sources": {
            "dados_atendimento_intimacoes_sefaz_rj_pgov_gastos": {
                "process_description": "Rateio de gastos auditados pela SEFAZ-RJ relacionados às participações governamentais",
                "relationships": "A tabela 1 se relaciona com a 2 usando o campo abc",
                "tables": {
                    "base_h": {"address": "dt0047_prd.gastos.base_h_pgov_sefaz_rj_gastos"},
                    "base_r": {"address": "dt0047_prd.gastos.base_r_pgov_sefaz_rj_gastos"},
                    "base_resultado": {"address": "dt0047_prd.gastos.base_result_pgov_sefaz_rj_gastos"} 
                    }
                },
        '''        
        # Carrega o arquivo de configuração existente
        config_json = config_json or cls.config_file
        if os.path.exists(config_json):
            with open(config_json, 'r', encoding='utf-8-sig') as arquivo:
                config = json.load(arquivo)
        else:
            raise FileNotFoundError(f"O arquivo {config_json} não foi encontrado.")
        
        # Adiciona um novo data source
        new_data_source = {
            collection: {
                "process_description": process_description,
                "relationships": relationships,
                "tables": {
                    table_name: {"address": table_address}
                    for table_name, table_address in tables.items()
                }
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
        self._profile_table_list = [{"profile_id": 999999, "address": ""}]
        super().__init__(config_json)
        
        for collection in self.config["data_sources"]:
            for table in self.config["data_sources"][collection]["tables"]:
                self.config["data_sources"][collection]["tables"][table].update(
                    self._get_metadata_from_table(
                        self.config["data_sources"][collection]["tables"][table]['address']
                        )
                    )
                profile_prefix = self.config["users_access"]["profile_prefix"]
                self.config["data_sources"][collection]["tables"][table]['grants'] = [
                    int(profile[len(profile_prefix):]) 
                    for profile in self.config["data_sources"][collection]["tables"][table]['grants']
                    if profile.startswith(profile_prefix )]
                
                self._profile_table_list += [
                        {"profile_id": p, "address": self.config["data_sources"][collection]["tables"][table]['address']}
                        for p in self.config["data_sources"][collection]["tables"][table]['grants']
                        ]

        self._allowed_tables = self._get_allowed_tables(user)

        collection_to_remove = []
        for collection in self.config["data_sources"]:
            table_to_remove = []
            for table in self.config["data_sources"][collection]["tables"]:
                if not self.config["data_sources"][collection]["tables"][table]['address'] in self._allowed_tables:
                    table_to_remove.append(table)
            if table_to_remove:
                for table in table_to_remove:
                    print("Remove", table)
                    del self.config["data_sources"][collection]["tables"][table]
            if not self.config["data_sources"][collection]["tables"]:
                collection_to_remove.append(collection)
        if collection_to_remove:
            for collection in collection_to_remove:
                print("Remove", collection)
                del self.config["data_sources"][collection]
        
    @property
    def available_collections(self):
        return list(self.config["data_sources"].keys())
        
    def _create_connection(self):
        
        if not hasattr(self, 'connection') or self.connection is None:
            access_token = os.getenv('DATABRICKS_CONN_TOKEN')
            try:
                connection = dbks_sql.connect(
                                server_hostname = self.config["connection"]["server_hostname"],
                                http_path = self.config["connection"]["http_path"],
                                access_token = access_token)              
                print('Conected to Databricks')
                return connection
            except: 
                print('Connection fail')
                return
        return self.connection

    def _get_metadata_from_table(self, table):
        
        # metadata = super()._get_metadata_from_table()
        metadata = {
            "description": "",
            "columns": {},
            "grants": []
                    }
        
        try: # Acessing the table description
            cursor = self.connection.cursor()
            cursor.execute(f"DESCRIBE DETAIL {table}")
            result = cursor.fetchall()[0]['description'].replace("\\'", "'")
            metadata_dic_descr = result
        except:
            metadata_dic_descr = {'table_description': '', 'gpt_instructions': ''}      
        finally:
            try: cursor.close()
            except: pass              
            
        try:  # Acessando os Grants na tabela
            cursor = self.connection.cursor()
            cursor.execute(f"SHOW GRANTS ON TABLE {table}")
            result = cursor.fetchall()
            grants = list(set([row[0] for row in result]))  # Acessa a primeira coluna de cada linha (ajuste conforme necessário)
        except:
            grants = []
        finally:
            try: cursor.close()
            except: pass  

        # Acessing the table columns metadata
        try: 
            metadata_dic_col = {}
            cursor = self.connection.cursor()

            cursor.execute(f"DESCRIBE {table}")
            result = cursor.fetchall()
            metadata_dic_col = {row[0]:  f"TYPE: {row[1]} COMMENT: {row[2] }" for row in result}
            
        except:
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

    def _get_allowed_tables(self, user) -> list:
        table = self.config["users_access"]["table"]
        profile_table = pd.DataFrame(self._profile_table_list).drop_duplicates(subset=['profile_id', 'address'])

        profile_ids = ','.join(map(str, profile_table['profile_id'].tolist()))

        sql = f'''
        SELECT PEPA_CD_PERFIL_PLATAFORMA as profile_id, VWRP_CD_ELEMENTO as user
        FROM {table}
        WHERE PEPA_CD_PERFIL_PLATAFORMA IN ({profile_ids})
        AND VWRP_CD_ELEMENTO = '{user.upper()}'
        '''

        result = self.get_table_as_dictionary(sql)

        if not result: result_df = pd.DataFrame(columns=["profile_id", "address"])
        else: result_df = pd.DataFrame(result)
        
        result_df = pd.merge(
            profile_table, 
            result_df, 
            on='profile_id', 
            how='inner'
        )

        result_df = result_df['address'].unique().tolist()
        
        return result_df
