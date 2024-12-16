from databricks import sql as dbks_sql
import os
from dotenv import load_dotenv
load_dotenv()
    
def databricks_connector():

    try:
        connection = dbks_sql.connect(
                        server_hostname = os.getenv('DATABRICKS_server_hostname'),
                        http_path = os.getenv('DATABRICKS_http_path'),
                        access_token = os.getenv('DATABRICKS_CONN_TOKEN'))                
        print('Conected to Databricks')
        return connection
    except: 
        print('Connection fail')
        return