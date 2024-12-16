import json
import re
import os
from datetime import datetime
from typing import Union, Callable, List, Dict, Optional, Any
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Column, String, JSON, TIMESTAMP, func, event, text
from sqlalchemy import Table, MetaData
import uuid
import base64
from pandas import DataFrame
import numpy as np
import logging
from .base import BaseKnowledgeBaseManager
from Petrobras_AI_Agents.LLM import BasellmClient
from Petrobras_AI_Agents.READERS import read_file

logger = logging.getLogger(__name__)  

class KnowledgeBaseManager_SQLite(BaseKnowledgeBaseManager):

    config_file = ""
    
    @classmethod
    def create_config_file(cls, config_json="//config_personal_collection.json", db_url=None):
        if not os.path.exists(config_json):
            db_url = db_url or "sqlite:///zdb_personal_collection.db"
            db_path = db_url.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            os.makedirs(os.path.dirname(config_json), exist_ok=True)
            
            config = {
                "connection": {
                    "db_url": db_url
                },
                "columns": {
                    "source_col"            : "source",
                    "file_col"              : "file_as_str",
                    "context_col"           : "page_content",
                    "rag_col"               : "vector_embedding",
                    "metadata_col"          : "metadata_dictionary",
                    "file_base_id_col"      : "id",
                    "vec_base_file_id_col"  : "file_id"
                },
                "functions": {
                    'cosine': '1 - (np.dot(embedding, x) / (np.linalg.norm(embedding) * np.linalg.norm(x)))',
                    'euclidean': 'np.linalg.norm(embedding - x)',
                    'manhattan': 'np.sum(np.abs(embedding - x))'
                    },
                "data_sources": {},
                    "table_description": {},
                    "columns_description": {}
                }

            with open(config_json, 'w', encoding='utf-8-sig') as arquivo:
                json.dump(config, arquivo, indent=2, ensure_ascii=False)
        
        # Update the config file name at the class level
        cls.config_file = config_json
        
    def __init__(self, config_json=None):
        config_json = config_json or self.__class__.config_file  
        super().__init__(config_json)  
        self.available_collections = list(self.config["data_sources"].keys())
        
    def create_collection(self, collection_name: str, table_common_name=None, curator=None, description=None, gpt_instructions=None):

        if collection_name not in self.config["data_sources"]:
            print('Create')
            super().create_collection(collection_name, table_common_name, curator, description, gpt_instructions)
            column_descriptions = {
                "file_base": {column.name: column.comment for column in self.db_conectors[collection_name]["file_base"].__table__.columns},
                "vec_base" : {column.name: column.comment for column in self.db_conectors[collection_name]["vec_base"].__table__.columns}}
            self.config["columns_description"].update({collection_name: column_descriptions})

            table_description = {
                "table_common_name": table_common_name,
                "curator"          : curator,
                "table_description": description,
                "gpt_instructions" : gpt_instructions}

        else:
            table_description = {
                "table_common_name": table_common_name or self.config["data_sources"][collection_name]["metadata"]["table_common_name"],
                "curator"          : curator or self.config["data_sources"][collection_name]["metadata"]["curator"],
                "table_description": description or self.config["data_sources"][collection_name]["metadata"]["table_description"],
                "gpt_instructions" : gpt_instructions or self.config["data_sources"][collection_name]["metadata"]["gpt_instructions"]
                }
            
        self.config["table_description"].update({collection_name: table_description})
        self.config["data_sources"][collection_name]["metadata"] = self._get_metadata_from_table(collection_name)
        
        with open(self.config_json, 'w', encoding='utf-8-sig') as arquivo:
            json.dump(self.config, arquivo, indent=2, ensure_ascii=False)
    
    def _get_metadata_from_table(self, collection_name):
        
        # if collection_name in self.config["data_sources"][collection_name]:
        metadata = super()._get_metadata_from_table(collection_name)

        metadata["description"] = self.config.get("table_description", {}).get(collection_name, {})
        if collection_name in self.config["columns_description"]:
            metadata["columns"]["file_base"] = self.config["columns_description"][collection_name]["file_base"]
            metadata["columns"]["vec_base"]  = self.config["columns_description"][collection_name]["vec_base"]
                
        return metadata
    
    def get_table_as_dictionary(self, sql_query=None, table=None):
        result = self.get_table(sql_query=sql_query, table=table)
        return DataFrame(result).to_dict(orient='records')
    
    def similarity_search(self, collection_name:str, embedding, k: int = 10, filters: Optional[List[Dict[str, str]]] = None, distance_strategy='cosine'):

        select_clause, from_clause, where_clause = super().similarity_search(collection_name, embedding, k, filters, distance_strategy)

        # Definindo a função de distância com base na estratégia selecionada
        import numpy as np
        distance_formula = self.config["functions"].get(distance_strategy)
        distance_func = eval(f"lambda embedding, x: {distance_formula}")
        select_clause = select_clause + f", vec_base.{self.config['columns']['rag_col']} as vector_embedding"

        sql_query = f"""
            {select_clause}
            {from_clause}
            {where_clause}
        """

        results = self.get_table_as_dictionary(sql_query)
        # If vector_embedding columns is a string, convert it to a list
        if isinstance(results[0]["vector_embedding"], str): as_string = True
        for row in results:
            if as_string:
                row["vector_embedding"] = json.loads(row["vector_embedding"])
            row['distance'] = distance_func(embedding, row["vector_embedding"])
        
        sorted_results = sorted(results, key=lambda x: x['distance'], reverse=False)
        return sorted_results[:k]
   
    def delete_document(self, collection_name: str, source_name: str):
        """
        Exclui uma coleção e todos os chunks associados com base no source.
        """
        connection = self._create_connection()
        try:
            file_base_class = self.db_conectors[collection_name]["file_base"]
            vec_base_class  = self.db_conectors[collection_name]["vec_base"]

            # Buscar o documento com base no source
            document = connection.query(file_base_class).filter(file_base_class.source == source_name).one_or_none()

            if document:
                connection.query(vec_base_class).filter(vec_base_class.file_id == document.id).delete(synchronize_session=False)
                connection.query(file_base_class).filter(file_base_class.id == document.id).delete(synchronize_session=False)
                connection.commit()                
                logger.info(f"Documento {source_name} e chunks associados excluídos")
            else:
                logger.warning(f"Documento {source_name} não encontrado")
        except Exception as e:
            connection.rollback()
            logger.error(f"Erro ao excluir o documento {source_name}. Erro: {e}")
            raise e
        finally:
            connection.close()

    def upload_document(self, collection_name, llm_client: BasellmClient, 
                        read_file_class: read_file=read_file, words_per_chunk=500, overlap=25, 
                        metadata_dictionary='', conflict_option="replace", file=None, file_path:str=None):
        '''
        conflict_option: replace, duplicate, ignore
        '''

        def _store_file_in_personal_collection(connection, file_base_class, file_name, file_content, metadata_dictionary=''):
            try:               
                if not isinstance(metadata_dictionary, str):
                    metadata_dictionary = json.dumps(metadata_dictionary, indent=2)

                new_document = file_base_class(
                    source      = file_name,
                    file_as_str = base64.b64encode(file_content).decode('utf-8'),
                    metadata_dictionary = metadata_dictionary
                )
                connection.add(new_document)
                connection.commit()
                connection.refresh(new_document)
                
                logger.info(f"Document created with ID: {new_document.id}")
                return new_document
            except Exception as e:
                connection.rollback()
                logger.error(f"Erro ao criar o documento: {e}")
                raise e

        def _add_chunks_to_collection(connection, collection_name, document_id, file_name, chunks):
            try:
                vec_base_class = self.db_conectors[collection_name]["vec_base"]

                for chunk in chunks:
                    vector_embedding = None
                    new_chunk = vec_base_class(
                        file_id=document_id,
                        source=file_name,
                        page_content=chunk['page_content'],
                        vector_embedding=vector_embedding
                    )
                    connection.add(new_chunk)
                connection.commit()
                logger.info(f"All chunks added successfully to collection ID: {document_id}")
            except Exception as e:
                connection.rollback()
                logger.error(f"Failed to add chunks to collection ID: {document_id}. Error: {e}")
                raise e

        if file is None and file_path is None:
            print("Missing file or file_path.")
            return
        
        if collection_name not in self.config["table_description"]:
            print("Collection does not exist.")
            return

        connection = self._create_connection()

        if file: file_name = file["file_name"]
        else: file_name = os.path.basename(file_path)
        
        file_base_class = self.db_conectors[collection_name]["file_base"]
        existing_document = connection.query(file_base_class).filter_by(source=file_name).one_or_none()

        if existing_document:
            if conflict_option == "replace": # Remover a coleção e os chunks associados
                self.delete_document(collection_name, file_name)
            elif conflict_option == "duplicate":
                logger.info(f"Arquivo com o nome '{file_name}' será duplicado.")
            elif conflict_option == "ignore": 
                print('Upload ignored. File already in database.')
                return # Encerra a função

        if file: file_content = file["file_content"]
        else:
            with open(file_path, "rb") as file:
                file_content = file.read()
        new_document = _store_file_in_personal_collection(connection, file_base_class, file_name, file_content, metadata_dictionary)

        # Processa os chunks do conteúdo do arquivo
        file_processor: read_file = read_file_class(file_name=file_name, file_content=file_content)
        chunks = file_processor.load_file_in_chuncks(words_per_chunk, overlap)
        print(f'chunks: {len(chunks)}')
        _add_chunks_to_collection(connection, collection_name, new_document.id, file_name, chunks)

        logger.info(f"Arquivo '{file_name}' processado e armazenado com sucesso na coleção ID: {new_document.id}")        

        connection.close()
        self.update_embeddings(collection_name, llm_client, update_all=False)

    def update_embeddings(self, collection_name, llm_client: BasellmClient, update_all=False):
        
        connection = self._create_connection()
        
        try:
            db_url = self.config["connection"]["db_url"]
            engine = create_engine(db_url)
            metadata = MetaData()
            metadata.reflect(bind=engine)
            
            vec_base = metadata.tables[self.config["data_sources"][collection_name]["vec_base"]]
            
            query = vec_base.select()
            if not update_all: 
                query = query.where(vec_base.c.vector_embedding.is_(None))

            chunks_to_update = connection.execute(query).fetchall()

            if not chunks_to_update:
                logger.info("No chunks to update.")
                return
            
            batch_size = 10
            for index, chunk in enumerate(chunks_to_update, start=1):
                try:
                    embedding = llm_client.get_embeddings(chunk.page_content, as_list=True)
                    update_stmt = vec_base.update().where(vec_base.c.id == chunk.id).values({vec_base.c.vector_embedding: json.dumps(embedding)})
                    connection.execute(update_stmt)

                    if index % batch_size == 0:
                        connection.commit()
                        logger.info(f"Committed batch of {batch_size} embeddings.")
                except Exception as e:
                    connection.rollback()
                    logger.warning(f"Failed to generate embedding for chunk ID {chunk.id}: {e}")
            
            # Commit remaining chunks if they don't fill up a complete batch
            if index % batch_size != 0:
                connection.commit()
                logger.info("Committed final batch of embeddings.")
            
            logger.info("All embeddings updated successfully.")
        except Exception as e:
            connection.rollback()
            logger.error(f"Failed to update embeddings: {e}")
            raise e
        finally:
            connection.close()

    def rename_collection(self, old_collection_name: str, new_collection_name: str):
        """
        Renomeia uma coleção no config.json, nas variáveis da classe e nas tabelas do banco de dados.
        """
        if old_collection_name not in self.config["data_sources"]:
            logger.warning(f"Collection '{old_collection_name}' não encontrada.")
            return

        connection = self._create_connection()
        
        try:
            # Renomeia as tabelas no banco de dados
            old_file_base_table = self.db_conectors[old_collection_name]["file_base"].__tablename__
            old_vec_base_table = self.db_conectors[old_collection_name]["vec_base"].__tablename__

            new_file_base_table = new_collection_name + "_file_base"
            new_vec_base_table = new_collection_name + "_vec_base"

            # Executa a renomeação no banco de dados
            connection.execute(text(f"ALTER TABLE {old_file_base_table} RENAME TO {new_file_base_table}"))
            connection.execute(text(f"ALTER TABLE {old_vec_base_table} RENAME TO {new_vec_base_table}"))

            # Atualiza os db_conectors para refletir os novos nomes das tabelas
            self.db_conectors[new_collection_name] = {
                "file_base": self.db_conectors[old_collection_name]["file_base"],
                "vec_base": self.db_conectors[old_collection_name]["vec_base"]
            }
            
            self.db_conectors[new_collection_name]["file_base"].__tablename__ = new_file_base_table
            self.db_conectors[new_collection_name]["vec_base"].__tablename__ = new_vec_base_table

            # Remove o conector antigo
            del self.db_conectors[old_collection_name]

            # Atualiza as configurações no self.config e no arquivo config.json
            self.config["data_sources"][new_collection_name] = self.config["data_sources"].pop(old_collection_name)

            # Atualiza os nomes de file_base e vec_base no config.json
            self.config["data_sources"][new_collection_name]["file_base"] = new_file_base_table
            self.config["data_sources"][new_collection_name]["vec_base"] = new_vec_base_table

            # Verifique se "columns_description" e "table_description" precisam ser atualizados
            if old_collection_name in self.config["columns_description"]:
                self.config["columns_description"][new_collection_name] = self.config["columns_description"].pop(old_collection_name)

            if old_collection_name in self.config["table_description"]:
                self.config["table_description"][new_collection_name] = self.config["table_description"].pop(old_collection_name)

            # Salva o arquivo de configuração atualizado
            with open(self.config_json, 'w', encoding='utf-8-sig') as arquivo:
                json.dump(self.config, arquivo, indent=2, ensure_ascii=False)

            connection.commit()
            logger.info(f"Collection '{old_collection_name}' renomeada para '{new_collection_name}' com sucesso.")
            
        except Exception as e:
            connection.rollback()
            logger.error(f"Erro ao renomear a coleção '{old_collection_name}' para '{new_collection_name}': {e}")
            raise e
        finally:
            connection.close()


