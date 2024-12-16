import json
import re
from datetime import datetime
from typing import Union, Callable, List, Dict, Optional, Any
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine, MetaData, Column, String, JSON, TIMESTAMP, func, event
from sqlalchemy import select, and_, or_, text
import uuid
import numpy as np

from Petrobras_AI_Agents.READERS import read_file

import logging
logger = logging.getLogger(__name__)

class BaseKnowledgeBaseManager:
    
    def __init__(self, config_json, user=None) -> None:
        
        self.config_json = config_json
        self.available_collections = []
        
        with open(self.config_json, 'r', encoding='utf-8-sig') as file:        
            self.config = json.load(file)        
        
        self.db_conectors = {}
        for collection_name in self.config["data_sources"]:      
            self.config["data_sources"][collection_name]["metadata"]  = self._get_metadata_from_table(collection_name)
            self.db_conectors.update(self._get_dynamic_classes(collection_name)) 
        print("Manager iniciated")
        
    def _create_connection(self):
        db_url     = self.config["connection"]["db_url"]
        engine     = create_engine(db_url)
        connection = sessionmaker(bind=engine)
        print("connected")
        return connection()
       
    def _get_metadata_from_table(self, collection_name=None):
        
        metadata = {
            "columns" : {"file_base": {},
                        "vec_base" : {}},
            "description" : { 
                "table_common_name": "",
                "curator": "",
                "table_description": "",
                "semantic_model": ""},
            "grants": []
            }

        return metadata
    
    def get_table(self, sql_query=None, table=None):
        self.connection = self._create_connection()
        
        if sql_query is None:
            sql_query = f'SELECT * FROM {table}'
        result = self.connection.execute(text(sql_query)).fetchall()
        self.connection.close()
        
        return result

    def get_table_as_dictionary(self, sql_query=None, table=None):
        pass
    
    def test_filters(self, base_sql:str, sql_condition_list:List) -> str:

        approved_filters = []  # Filtros que foram aceitos após os testes
        start_count = self.get_table_as_dictionary(sql_query=base_sql)[0]["count"]
        previous_count = start_count

        # Testa cada intenção de filtro
        for filter_clause in sql_condition_list:
            combined_filters = " AND ".join(approved_filters + [filter_clause])
            try: # In case test for a inexistent column
                test_sql = f"{base_sql} WHERE {combined_filters}"
                current_count = self.get_table_as_dictionary(sql_query=test_sql)[0]["count"]               
                # Verifica se o filtro atual melhora a filtragem (diminui o número de registros)
                if 0 < current_count < previous_count:
                    approved_filters.append(filter_clause)
                    previous_count = current_count
            except: pass
            
        # Retorna a query final com os filtros aprovados
        if approved_filters: return f"{base_sql} WHERE {' AND '.join(approved_filters)}", current_count
        else: return base_sql, start_count

    def apply_filters(self, collection_name, filters: Optional[List[Dict[str, str]]]) -> str:
        
        import html
        import re
        from datetime import datetime
        
        file_base_table = self.config["data_sources"][collection_name]["file_base"]
        sql_query = f'''
        SELECT count(*) as count FROM {file_base_table}
        '''

        logger.debug(f'apply_filters')
        
        # ajust_text_to_filter_field 
        try: exec(self.config["data_sources"][collection_name]['metadata']['description']['text_normalize_function'])
        except: ajust_text_to_filter_field = lambda v: (datetime.strptime(v, '%d/%m/%Y').strftime('%Y-%m-%d') if isinstance(v, str) and re.fullmatch(r'\\d{2}/\\d{2}/\\d{4}', v) else v if isinstance(v, (int, float, bool)) else re.sub(r'[^a-zA-Z0-9\\s]', '', re.sub(r'\\s+', ' ', html.unescape(v.replace('\\n', ' ').replace('\\r', '').lower()))).strip() if isinstance(v, str) else v)

        initial_count = self.get_table(sql_query=sql_query)[0][0] #['count'] #elf.get_table(sql_query=sql_query)[0][0]
        # Construindo cláusulas de filtro
        filter_clauses = []
        for criterion in filters:
            field = criterion['field']
            operator = criterion['operator']
            value = ajust_text_to_filter_field(criterion['value'])

            if operator.lower() == 'between':
                if not isinstance(value, list) or len(value) != 2:
                    raise ValueError("For the 'BETWEEN' operator, the value must be a list with two elements.")
                filter_clause = f"{field} BETWEEN {value[0]} AND {value[1]}"
            elif operator.lower() == 'not between':
                if not isinstance(value, list) or len(value) != 2:
                    raise ValueError("For the 'NOT BETWEEN' operator, the value must be a list with two elements.")
                filter_clause = f"{field} NOT BETWEEN {value[0]} AND {value[1]}"
            elif operator.lower() == 'like':
                if isinstance(value, list):
                    like_clauses = " OR ".join([f"{field} LIKE '%{v}%'" for v in value])
                    filter_clause = f"({like_clauses})"
                else:
                    filter_clause = f"{field} LIKE '%{value}%'"
            elif operator.lower() == 'in':
                if isinstance(value, list):
                    value_list = ", ".join([f"'{v}'" for v in value])
                    filter_clause = f"{field} IN ({value_list})"
                else:
                    filter_clause = f"{field} = '{value}'"
            elif operator.lower() == 'is not' and value.lower() == 'null':
                filter_clause = f"{field} IS NOT NULL"
            elif operator.lower() == 'is' and value.lower() == 'null':
                filter_clause = f"{field} IS NULL"
            else:
                if isinstance(value, str):
                    value = f"'{value}'"
                filter_clause = f"{field} {operator} {value}"

            filter_clauses.append(filter_clause)
        
        # Validando as cláusulas de filtro
        valid_filter_clauses = []
        for fc in filter_clauses:
            test_filter_clauses = valid_filter_clauses + [fc]
            test_filters_sql = " AND ".join(test_filter_clauses)
            test_sql_query = f"{sql_query} WHERE {test_filters_sql}"
            try: 
                filter_result = self.get_table(sql_query=test_sql_query)
                count_after_filter = filter_result[0][0] #['count'] #filter_result[0][0]
                logger.info(f'test filter {test_sql_query}')
                logger.info(f'filter_result: {filter_result}')
                logger.info(f'count_after_filter: {count_after_filter}')
                if count_after_filter < initial_count and count_after_filter > 0:
                    valid_filter_clauses = test_filter_clauses
            except: pass
                
        # Aplicando os filtros validados
        if valid_filter_clauses:
            filters_sql = " AND ".join(valid_filter_clauses)
            where_query = f" WHERE {filters_sql}"
        else:
            where_query = ""

        return where_query
    
    def similarity_search(self, collection_name:str, embedding, k: int = 10, filters: Optional[List[Dict[str, str]]] = None, distance_strategy='cosine'):

        file_base_table = self.config["data_sources"][collection_name]["file_base"]
        vec_base_table  = self.config["data_sources"][collection_name]["vec_base"]
        
        select_clause = f"""
            SELECT 
                vec_base.{self.config["columns"]["vec_base_file_id_col"]} AS file_id,
                vec_base.{self.config["columns"]["source_col"]} AS source, 
                vec_base.{self.config["columns"]["context_col"]} AS page_content,
                file_base.{self.config["columns"]["metadata_col"]} AS metadata
        """
        from_clause = f"""
            FROM 
                {vec_base_table} vec_base
            JOIN 
                {file_base_table} file_base
            ON 
                vec_base.{self.config["columns"]["vec_base_file_id_col"]} = file_base.{self.config["columns"]["file_base_id_col"]}
        """
        if filters: where_clause = filters
        else: where_clause = ""

        return select_clause, from_clause, where_clause

    def retrieve_full_documents(self, collection_name, filters, read_file_class:read_file=read_file, k=5, words_per_chunk=2500, overlap=25):
        
        file_base_table = self.config["data_sources"][collection_name]["file_base"]
        select_clause = f"""
            SELECT 
                file_base.{self.config["columns"]["source_col"]} AS source,
                file_base.{self.config["columns"]["file_col"]} AS file_col
            """
        
        from_clause = f"""
            FROM 
                {file_base_table} file_base
            """
        
        where_clause = filters
        
        return select_clause, from_clause, where_clause
    
    def _get_dynamic_classes(self, collection_name, table_description=None):

        Base = declarative_base()
        
        # Atualizar a tabela file_base usando a classe PersonalCollection
        class file_base_db_table(Base):
            __tablename__ = collection_name + "_file_base"
            __table_args__ = {'comment': json.dumps(table_description, ensure_ascii=False)}

            id                  = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), comment="Identificador único para as linhas da tabela")
            source              = Column(String, comment="Nome do arquivo de refeência do documento fonte")
            file_as_str         = Column(String, comment="Arquivo completo")
            metadata_dictionary = Column(String, comment="Palavras chaves relacionadas ao documento")
            llm_emb_model       = Column(String, comment="Nome do modelo usado para vetorização")
            created_at          = Column(TIMESTAMP, default=func.now(), comment="Data de inserção do documento na base de dados")
            updated_at          = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), comment="Última data de atualização do documento na base de dados")

        # Atualizar a tabela vec_base usando a classe PersonalCollectionChunks
        class vec_base_db_table(Base):
            __tablename__ = collection_name + "_vec_base"
            __table_args__ = {'comment': json.dumps(table_description, ensure_ascii=False)}

            id                  = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), comment="Identificador único para as linhas da tabela")
            file_id             = Column(String, comment="Identificador único de referência do documento fonte")
            source              = Column(String, comment="Nome do arquivo de refeência do documento fonte")
            page_content        = Column(String, comment="Parte do texto do documento fonte para otimização das buscas do conteúdo relevante")
            vector_embedding    = Column(String, comment="Embedding de texto usando llm para transformar o texto em vetor")
            created_at          = Column(TIMESTAMP, default=func.now(), comment="Data de inserção do documento na base de dados")
            updated_at          = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), comment="Última data de atualização do documento na base de dados")
        
        db_url = self.config["connection"]["db_url"]
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)

        return    {
            collection_name: {
                "file_base": file_base_db_table,
                "vec_base" : vec_base_db_table}}

    def create_collection(self, collection_name: str, table_common_name=None, curator=None, description=None, gpt_instructions=None):

        collection_name = collection_name.replace(" ", "_")
        self.config["data_sources"].update({collection_name:{}})
                        
        table_description = {
                "table_common_name": table_common_name,
                "curator"          : curator,
                "table_description": description,
                "gpt_instructions" : gpt_instructions}

        self.db_conectors.update(
            self._get_dynamic_classes(collection_name, table_description)
            )

        data_sources = {
            "file_base": self.db_conectors[collection_name]["file_base"].__tablename__,
            "vec_base" : self.db_conectors[collection_name]["vec_base"].__tablename__}
        self.config["data_sources"][collection_name].update(data_sources)
            
        # if collection_name in self.config["data_sources"]:
        #     print("Collection already exist. It is only going to update the description.")
        # else:
            # data_sources = {
            #     "file_base": self.db_conectors[collection_name]["file_base"].__tablename__,
            #     "vec_base" : self.db_conectors[collection_name]["vec_base"].__tablename__}
            # self.config["data_sources"].update({collection_name: data_sources})
            
        # self.config["data_sources"][collection_name]["metadata"]  = self._get_metadata_from_table(collection_name)
        
        # with open(self.config_json, 'w', encoding='utf-8-sig') as arquivo:
        #     json.dump(self.config, arquivo, indent=2, ensure_ascii=False)
                