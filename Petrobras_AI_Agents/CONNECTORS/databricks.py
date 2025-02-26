from databricks import sql as dbks_sql
from decouple import config
from contextlib import contextmanager
from threading import Lock
connection_lock = Lock()

def databricks_connector(server_hostname: str = None, http_path: str = None, access_token: str = None, close_connection: bool = False, user=None):
    """Função que mantém e retorna uma conexão ativa com Databricks."""
    
    server_hostname = server_hostname or config("DATABRICKS_server_hostname", default="adb-671799829240675.15.azuredatabricks.net")
    http_path = http_path or config("DATABRICKS_http_path", default="/sql/1.0/warehouses/1fd972f888afd086")
    access_token = access_token or config("DATABRICKS_TOKEN", default=None)
    user = user or 'global'
    
    def is_connection_active(conn):
        """Verifica se a conexão com o Databricks ainda está ativa."""
        if conn is None:
            return False
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")  # Teste simples na conexão
            return True  # Conexão válida
        except Exception:
            print("KnowledgeBaseManager_Databricks: ⚠️ Conexão perdida! Será necessário reconectar.", flush=True)
            return False  # Conexão inválida
        
    def connector():
        """Cria uma nova conexão com o Databricks."""
        try:
            connection = dbks_sql.connect(
                server_hostname=server_hostname,
                http_path=http_path,
                access_token=access_token)
            print('✅ databricks_connector: Conectado ao Databricks', flush=True)
            return connection
        except Exception as e:
            print(f'❌ databricks_connector: Falha na conexão com Databricks → {e}', flush=True)
            return None  # Evita retornar um erro direto e permite re-tentativas

    with connection_lock:
        # Criar conexão apenas se necessário
        conn = getattr(databricks_connector, f"_conn_{user}", None)

        if close_connection and conn:
            conn.close()
            setattr(databricks_connector, f"_conn_{user}", None)
            print('✅ databricks_connector: Conexão com o Databricks fechada com sucesso', flush=True)
            
        else:
            if not is_connection_active(conn):
                conn = connector()
                if conn:
                    setattr(databricks_connector, f"_conn_{user}", conn)  # Armazena no escopo da função
                else:
                    raise ConnectionError("❌ Erro: Não foi possível conectar ao Databricks.")  # Erro explícito

        return conn

# @contextmanager
# def databricks_connection_thread_safe(server_hostname: str = None, http_path: str = None, access_token: str = None):
    # """Gerencia a conexão com o Databricks no escopo local."""
    # conn = None
    # try:
    #     conn = dbks_sql.connect(
    #         server_hostname=server_hostname or config("DATABRICKS_server_hostname"),
    #         http_path=http_path or config("DATABRICKS_http_path"),
    #         access_token=access_token or config("DATABRICKS_TOKEN")
    #     )
    #     yield conn
    # finally:
    #     conn.close()