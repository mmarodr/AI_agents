from .base import BaseDatabaseManager
import json
import os
import io
import uuid
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import pandas as pd
import numpy as np
from pandas import DataFrame

class DatabaseManager_SQLite(BaseDatabaseManager):
    config_file = ""

    @classmethod
    def create_config_file(cls, config_json="config_datasources.json", db_url=None):
        if not os.path.exists(config_json):
            db_url = db_url or "sqlite:///zdb_analysis_database.db"
            db_path = db_url.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            os.makedirs(os.path.dirname(config_json), exist_ok=True)
            config = {
                "connection": {
                    "db_url": db_url
                },
                "data_sources": {}
            }

            with open(config_json, 'w', encoding='utf-8-sig') as file:
                json.dump(config, file, indent=2, ensure_ascii=False)

        cls.config_file = config_json

    def __init__(self, config_json=None):

        config_json = config_json or self.__class__.config_file
        
        super().__init__(config_json)
        self.db_url = self.config['connection']['db_url']
        self.engine = create_engine(self.db_url)

        self.SessionFactory = sessionmaker(bind=self.engine)
        
        self.available_collections = list(self.data_sources.keys())

    @property
    def generate_uuid(self):
        return str(uuid.uuid4())

    @contextmanager
    def session_scope(self):
        session = self.SessionFactory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def connect(self):
        connection = self.engine.connect()
        try:
            yield connection
        except: print("Não foi possível conectar ao banco")
        finally:
            connection.close()

    @property
    def collections(self):
        return list(self.config["data_sources"].keys())
    
    def add_datasource(self, data_source, process_description=None, relationships=None):
        
        if data_source in self.data_sources:
            print(f"O datasource '{data_source}' já existe.")
            self.data_sources[data_source]['process_description'] = process_description or self.data_sources[data_source]['process_description']
            self.data_sources[data_source]['relationships'] = relationships or self.data_sources[data_source]['relationships']

        else:
            self.data_sources[data_source] = {
                "process_description": process_description,
                "relationships": relationships,
                "tables": {}
            }

        self.save_config()

    def load_csv_to_table(self, data_source, column_type=None, conflict_option="replace", table_name=None, csv_file=None, file_path: str = None):
        '''
        conflict_option: replace, ignore
        '''
        
        if csv_file is None and file_path is None:
            print("Missing file or file_path.")
            return
                
        if data_source not in self.data_sources:
            print(f"O datasource '{data_source}' não existe.")
            return
        
        if table_name is None:
            if csv_file:
                table_name = os.path.splitext(csv_file["file_name"])[0]
            else:
                table_name = os.path.splitext(os.path.basename(file_path))[0]
        
        table_name = f"{data_source}_{table_name}"

        with self.connect() as connection:
            existing_tables = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall()
            existing_tables = [table[0] for table in existing_tables]
            print("existing_tables", existing_tables)

        if table_name in existing_tables:
            if conflict_option == "replace":
                self.delete_table_if_exists(table_name)
            elif conflict_option == "ignore":
                print(f"A tabela '{table_name}' já existe. A opção 'ignore' foi selecionada, o carregamento será ignorado.")
                return
        print("table_name", table_name)
        try:
            if csv_file:
                file_content = csv_file["file_content"]
                df = pd.read_csv(io.StringIO(file_content.decode('utf-8-sig')), sep=';', encoding='utf-8-sig', thousands='.', decimal=',')
            else:
                df = pd.read_csv(file_path, sep=';', encoding='utf-8-sig', thousands='.', decimal=',')
        except UnicodeDecodeError:
            try:
                if csv_file:
                    file_content = csv_file["file_content"]
                    df = pd.read_csv(io.StringIO(file_content.decode('ISO-8859-1')), sep=';', encoding='ISO-8859-1', thousands='.', decimal=',')
                else:
                    df = pd.read_csv(file_path, sep=';', encoding='ISO-8859-1', thousands='.', decimal=',')
            except Exception as e:
                print(f"Erro ao carregar o conteúdo do CSV: {e}")
                return
        except Exception as e:
            print(f"Erro ao ler o CSV: {e}")
            return

        try:
            if column_type:
                for col, col_type in column_type.items():
                    if col in df.columns:
                        try:
                            df[col] = df[col].str.replace(r'\s+', '', regex=True)  # Remover espaços em branco
                            df[col] = df[col].str.replace(r'\((.*?)\)', r'-\1', regex=True)  # Tratar parênteses como negativo
                            df[col] = df[col].str.replace('.', '', regex=False)  # Remover separadores de milhar
                            df[col] = df[col].str.replace(',', '.', regex=False)  # Substituir vírgula por ponto
                            df[col] = df[col].replace('-', np.nan)  # Substituir '-' por NaN
                            df[col] = df[col].astype(col_type.lower())  # Converter o tipo de dado
                            print(f"Coluna '{col}' convertida para o tipo '{col_type}'.")
                        except Exception as e:
                            print(f"Erro ao converter a coluna '{col}' para o tipo '{col_type}': {e}")
        except Exception as e:
            print(f"Erro ao processar tipos de coluna: {e}")
        
        
        with self.connect() as connection:
            try:
                df.to_sql(table_name, connection, if_exists='replace', index=False)
            except Exception as db_err:
                print(f"Erro ao tentar salvar a tabela '{table_name}' no banco de dados. Erro: {db_err}")
                return
            try:
                query = text(f"PRAGMA table_info({table_name})")
                result = connection.execute(query).fetchall()
                column_info = {row[1]: row[2] for row in result}  # {coluna: tipo}
            except Exception as e:
                print(e)

        try:
            if data_source not in self.data_sources:
                raise ValueError(f"Datasource '{data_source}' não encontrado.")
            self.data_sources[data_source]['tables'][table_name] = {
                "description": "",
                "columns": {col: {"description": "", "type": column_info.get(col, "TEXT")} for col in df.columns}
            }
            self.save_config()
        except Exception as e:
            print(f"Erro ao atualizar a configuração da fonte de dados: {e}")
            return

        # Imprimir os tipos de cada coluna após o processamento
        try:
            print("\nTipos das colunas após o carregamento:")
            for col, dict in self.data_sources[data_source]['tables'][table_name]["columns"].items():
                print(f"Coluna '{col}': {dict['type']}")
        except Exception as e:
            print(f"Erro ao imprimir tipos de coluna: {e}")

    def delete_table_if_exists(self, table_name):
        with self.connect() as connection:
            connection.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
            
    def update_column_properties(self, table_name, data_source, column, description=None, synonyms=None, content=None, examples=None):
        table_name = f"{data_source}_{table_name}"
        if data_source in self.data_sources and table_name in self.data_sources[data_source]["tables"]:
            if column in self.data_sources[data_source]["tables"][table_name]["columns"]:
                column_data = self.data_sources[data_source]["tables"][table_name]["columns"][column]

                if description is not None  : column_data["description"]    = description
                if synonyms is not None     : column_data["synonyms"]       = synonyms
                if content is not None      : column_data["content"]        = content
                if examples is not None     : column_data["examples"]       = examples

                self.save_config()
                print(f"Propriedades da coluna '{column}' na tabela '{table_name}' atualizadas com sucesso.")
            else:
                raise ValueError(f"Coluna '{column}' não encontrada na tabela '{table_name}' do datasource '{data_source}'.")
        else:
            raise ValueError(f"Table '{table_name}' ou datasource '{data_source}' não encontrados.")

    def delete_datasource(self, data_source):
        if data_source not in self.data_sources:
            raise ValueError(f"O datasource '{data_source}' não foi encontrado.")

        with self.connect() as connection:
            for table_name in self.data_sources[data_source].get('tables', {}).keys():
                connection.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
        
        del self.data_sources[data_source]
        self.save_config()

    def get_datasource(self, data_source):
        if data_source not in self.data_sources:
            raise ValueError(f"O datasource '{data_source}' não foi encontrado.")
        return self.data_sources[data_source]

    def get_table(self, sql_query=None, table=None):
        if sql_query is None and table is not None:
            sql_query = f'SELECT * FROM {table}'
        
        with self.connect() as connection:
            result = connection.execute(text(sql_query)).fetchall()
        
        return result

    def get_table_as_dictionary(self, sql_query=None, table=None):
        result = self.get_table(sql_query=sql_query, table=table)
        return DataFrame(result).to_dict(orient='records')

    def save_config(self):
        with open(self.config_file, 'w', encoding='utf-8-sig') as file:
            json.dump({
                "connection": self.config['connection'],
                "data_sources": self.data_sources,
            }, file, indent=2, ensure_ascii=False)

    def close_connection(self):
        self.engine.dispose()

    def list_tables(self):
        with self.connect() as connection:
            # Use a consulta SQL encapsulada no objeto `text`
            tables = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall()
            return [table[0] for table in tables]     
