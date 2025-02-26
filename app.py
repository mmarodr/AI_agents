# %% Imports 1
from flask import Flask
from flask_cors import CORS
from flask import session as flask_session
from flask import redirect, render_template, jsonify, url_for
from flask import request as flask_request
import operator
from decouple import config
from requests import Session
from requests.adapters import HTTPAdapter
from urllib.parse import urlparse
from zeep import Client
from zeep.transports import Transport
import copy
import secrets
import os
from threading import Thread
from threading import Lock
import dill
import base64

from Petrobras_AI_Agents import databricks_connector
from Petrobras_AI_Agents import KnowledgeBaseManager_Databricks as Databricks_KnowledgeBase
from Petrobras_AI_Agents import DatabaseManager_Databricks
from Petrobras_AI_Agents import AgentWork, BaseAgent, ChatInterpretorAgent, KnowledgeBaseAgent, DatabaseExpertAgent
from Petrobras_AI_Agents import llmClient_AzureOpenAI as llmClient
from Petrobras_AI_Agents import ChatDatabaseManager_Postgres as ChatMemory
from Petrobras_AI_Agents import AppSessionManager_Postgres as AppSessionManager
from Petrobras_AI_Agents.TOOLS import search_web


# %% Variaveis

# CAV4
PARAM_APPLICATION_CATALOG_ID = "applicationCatalogId"
PARAM_REGIONAL_ID = "regionalId"
PARAM_ENVIRONMENT_ID = "environmentId"
PARAM_SUCCESSFUL_URL = "successfulUrl"
ENDPOINT_WSDL = "http://servicoca.petrobras.com.br/fwca/4.1/SecurityService.svc?wsdl"
ENV = "LOCAL"
APPLICATION_CATALOG_ID = "S10883"
REGIONAL_ID = "RIO"

# CERT_PATH
CERT_PATH = "servicoca-petrobras-com-br-chain.pem"

# OPENAI
AZURE_OPENAI_api_version = "2024-06-01"
AZURE_OPENAI_model_text  = "gpt-4o-petrobras"
AZURE_OPENAI_model_emb   = "text-embedding-3-large-petrobras"

# DATABRICKS
DATABRICKS_server_hostname = "adb-671799829240675.15.azuredatabricks.net"
DATABRICKS_http_path = "/sql/1.0/warehouses/1fd972f888afd086"

# Others
ENVIRONMENT_ID = config("ENVIRONMENT_ID")
if ENVIRONMENT_ID == "PRD":
    AZURE_OPENAI_BASE_URL = "https://api.petrobras.com.br/ia/openai/v1/openai-azure/openai"
    HOME_HOST = "https://chat-contabilidade.petrobras.com.br"
else:
    AZURE_OPENAI_BASE_URL = "https://apit.petrobras.com.br/ia/openai/v1/openai-azure/openai"
    if ENVIRONMENT_ID == "LOCAL":
        ENVIRONMENT_ID = "DSV"
        HOME_HOST = "http://localhost:5000/"
    else:
        HOME_HOST = f'https://chat-contabilidade-{ENVIRONMENT_ID.lower()}.petrobras.com.br'
    
# %% Create app
def create_app():
    print('app: create_app', flush=True)
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)
    CORS(app, headers={'Access-Control-Allow-Origin':'*', 'Access-Control-Allow-Headers': 'Content-Type, Authorization'})    
    app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config['SQLALCHEMY_POOL_TIMEOUT'] = 1200
    return app

app = create_app()

# %% CAV4 e criação da sessão inicial
def create_client(endpoint_wsdl, cert_path) -> Client:
    
    def create_session(cert_path):
        session = Session()
        adapter = HTTPAdapter(max_retries=3)
        session.mount("https://", adapter)
        session.verify = cert_path
        return session
    return Client(wsdl=endpoint_wsdl,
                    transport=Transport(session=create_session(cert_path))
                    )

client = create_client(ENDPOINT_WSDL, CERT_PATH)

def logout():
    flask_session.clear()
    return redirect_to_tlc(HOME_HOST + '/authentication/handler')

# CAV4
def redirect_to_tlc(successful_url):
    response = client.service.getAuthenticationHandlerUrlFor(ENDPOINT_WSDL)
    if response['value']:
        url = response['value'] + "?" \
            + PARAM_REGIONAL_ID + "=" + REGIONAL_ID + "&" \
            + PARAM_ENVIRONMENT_ID + "=" + ENVIRONMENT_ID + "&" \
            + PARAM_APPLICATION_CATALOG_ID + "=" + APPLICATION_CATALOG_ID + "&" \
            + PARAM_SUCCESSFUL_URL + "=" + urlparse(successful_url).geturl()
        return redirect(url, code=302)

def logon(user, userPassword):
    response = client.service.logon(None,
                                    REGIONAL_ID, 
                                    ENVIRONMENT_ID, 
                                    APPLICATION_CATALOG_ID,
                                    config("CAV4_PASSWORD"),
                                    user, userPassword, True)
    if response['value']:
        value = response['value']
        ans = {
            'login': value['user']['login'],
            'name' : value['user']['name'],
            'token': value['ticket']['sessionId']
            }
        return ans, 200
    else:
        ans = {
            'code'   : response['exceptionInfo']['code'],
            'message': response['exceptionInfo']['message']
            }
        return ans, 404

def authentication_handler(global_session_id):
    after_logon_page = None
    if not after_logon_page: after_logon_page = "/"
    url = HOME_HOST \
        + "/authentication/logonFromSessionId/" \
        + global_session_id + "?" \
        + PARAM_SUCCESSFUL_URL + "=" \
        + urlparse(after_logon_page).geturl()
    return redirect(url, 302)

def logon_from_session_id(session_id, successful_url):
    # client = get_client('cav4')
    response = client.service.connectApplicationEnvironmentWithSSO(None, 
                                                                   session_id, 
                                                                   REGIONAL_ID, 
                                                                   ENVIRONMENT_ID, 
                                                                   APPLICATION_CATALOG_ID,
                                                                   config("CAV4_PASSWORD"))
    if response['value']:
        value = response['value']
        flask_session.clear()
        flask_session['login'] = value['user']['login']
        flask_session['name'] = value['user']['name']
        flask_session['token'] = value['ticket']['sessionId']
        flask_session['department'] = value['user']['department']['acronym']
        try:
            flask_session['email']  = value['user']['email']
            flask_session['registration'] = value['user']['registrationNumber'].zfill(8)
        except:
            flask_session['email']  = 'alisson.pina@petrobras.com.br'
            flask_session['registration'] = ''
        return redirect(successful_url, 302)
    else:
        ans = {}
        ans['code'] = response['exceptionInfo']['code']
        ans['message'] = response['exceptionInfo']['message']
        return ans, 404
    
def all_methods():
    ans = {}
    for service in client.wsdl.services.values():
        operations_list = []
        for port in service.ports.values():
            operations = sorted(
                port.binding._operations.values(),
                key=operator.attrgetter('name'))
            for operation in operations:
                operations_list.append(
                    {
                        'name': operation.name, 
                        'input': operation.input.signature()
                    })
        ans[service.name] = operations_list
    return ans, 200

def requires_authentication(request_path):
    return 'authentication' not in request_path \
            and 'methods' not in request_path \
            and 'token' not in flask_session

def list_user_roles():
    # client = get_client('cav4')
    login = flask_session['login']
    header = {'ticket': {'sessionId': flask_session['token']}}
    response = client.service.findAllRolesOfUser(header, login)
    
    if not response['exceptionInfo']:
        roles = [role['id'] for role in response['value']]
        return {'roles': roles }, 200
    else:
        ans = {
                'code': response['exceptionInfo']['code'],
                'message': response['exceptionInfo']['message']
                }
        return ans, 404

@app.route('/health')
def health():
    return 'Ok'

@app.before_request
def before_request():
    flask_session.permanent = False
    if flask_request.path == '/health':
        return
    if requires_authentication(flask_request.path):
        return redirect_to_tlc(HOME_HOST + '/authentication/handler')
    
@app.route("/list_user_roles")
def user_roles():
    return list_user_roles()

@app.route("/logon")
def logon_route():
    return logon(flask_request.args.get('login'), flask_request.args.get('password'))

@app.route("/authentication/redirectToTLC")
def redirect_to_tlc_route():
    return redirect_to_tlc(flask_request.args.get('successfulUrl'))

@app.route("/authentication/handler")
def authentication_handler_route():
    print("request.args.get('globalSessionId')", flask_request.args.get('globalSessionId'))
    return authentication_handler(flask_request.args.get('globalSessionId'))

@app.route("/authentication/logonFromSessionId/<session_id>")
def logon_from_session_id_route(session_id):
    return logon_from_session_id(
        session_id, 
        flask_request.args.get('successfulUrl'))

@app.route("/logout")
def logout_route():
    return logout()

@app.route("/methods")
def methods_route():
    return all_methods()

@app.errorhandler(403)
def access_forbidden(error):
    return render_template('home/page-403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('home/page-404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    print("error: ", error)
    return render_template('home/page-500.html'), 500

# %% Agentes

chat_interpretor_agent_name     = "Chat Analista"
search_agent_name               = "Informações Web"
databricks_knowledge_agent_name = "Documentos Databricks"
databricks_analytics_agent_name = "Analytics Databricks"
personal_knowledge_agent_name   = "Documentos Pessoais"
local_analytics_agent_name      = "Analytics Pessoal"  

global_section_lock = Lock()
global_section = {'global': {}}
global_session_db = None

def set_managers():
    
    global global_section, global_session_db
    
    try:
        doc_manager_databricks:Databricks_KnowledgeBase = Databricks_KnowledgeBase(
            config_json = os.path.join("config_json", "databricks", "config_databricks_doc_collection.json"),
            connection_as_function = databricks_connector
            )
        global_section['global']['doc_manager_databricks'] = doc_manager_databricks
        print("app: doc_manager_databricks initiated")
    except: pass
    
    try:
        database_manager:DatabaseManager_Databricks = DatabaseManager_Databricks(
            config_json = os.path.join("config_json", "databricks", "config_databricks_datasources.json"),
            connection_as_function = databricks_connector
            # user        = username
            )
        global_section['global']['database_manager'] = database_manager
        print("app: doc_manager_databricks initiated")
        databricks_connector(close_connection=True)
    except: pass

    global_session_db = AppSessionManager(db_path=config("POSTGRES_PASSWORD"))
    
def initiate_section(username):
    print('app: initiate_section', flush=True)
    
    global global_section
    
    with global_section_lock:
        global_section[username] = {'agent_work': None, 'connection': None}
    
    flask_session['agent_collections'] = {}
    flask_session['agent_states'] = {}
    flask_session['work_local_memory'] = {}

    language = "pt-br"    
    agent_work = AgentWork(
        start_agent = chat_interpretor_agent_name,
        language = language,
        chat_mode = True,
        llm = llmClient(
            model_text  = AZURE_OPENAI_model_text,
            model_emb   = AZURE_OPENAI_model_emb,
            api_version = AZURE_OPENAI_api_version,
            base_url    = AZURE_OPENAI_BASE_URL,
            cert_file   = CERT_PATH,
            api_key     =config("AZURE_OPENAI_API_KEY"),
            temperature=0.1),
        chat_memory = ChatMemory( 
            db_path     = config("POSTGRES_PASSWORD"),
            user        = username,
            language    = language),
    )

    flask_session['chat_id'] = agent_work.chat_memory.chat_id
    
    ChatInterpretorAgent(agent_name=chat_interpretor_agent_name, human_in_the_loop=False, work_instance = agent_work)
    BaseAgent(agent_name=search_agent_name, 
        allow_direct_response=False, 
        next_agent_list=[],
        background=[
            "Este agente realiza pesquisas na web para recuperar informações não disponíveis localmente."
            ],
        goal=[
            "Fornecer informações relevantes e atualizadas da web.",
            "Interprete a solicitação do usuário para gerar a melhor busca possível.",
            "Use seus conhecimentos para gerar a melhor query possível"
            ],
        tools=[search_web],
        work_instance = agent_work
    )
    flask_session['agent_states'][search_agent_name] = True

    def collections(available_collections): 
        return {collection: True for collection in available_collections}
    
    if 'doc_manager_databricks' in global_section['global']:
        doc_manager_databricks = copy.deepcopy(global_section['global'].get('doc_manager_databricks', None))
        doc_manager_databricks.user = username
        collection_list = doc_manager_databricks.get_available_collections()
        if collection_list:
            KnowledgeBaseAgent(agent_name=databricks_knowledge_agent_name, k=5,
                allow_direct_response=True,
                KnowledgeBase=doc_manager_databricks,
                human_in_the_loop=False,
                collection_list=collection_list,
                work_instance = agent_work
                )
            flask_session['agent_collections'][databricks_knowledge_agent_name] = collections(collection_list)
            flask_session['agent_states'][databricks_knowledge_agent_name] = True
    
    if 'database_manager' in global_section['global']:
        database_manager = copy.deepcopy(global_section['global'].get('database_manager', None))
        database_manager.user = username
        data_sources = database_manager.user_config_file()["data_sources"]
        collection_list = list(data_sources.keys())
        if collection_list:
            DatabaseExpertAgent(agent_name=databricks_analytics_agent_name,
                database_manager=database_manager,
                human_in_the_loop=False,
                allow_direct_response=True,
                collection_list=collection_list,
                work_instance = agent_work
            )
            flask_session['agent_collections'][databricks_analytics_agent_name] = collections(collection_list)
            flask_session['agent_states'][databricks_analytics_agent_name] = True
    
    global_session_db.save_sessiont(username, 'agent_work', agent_work)

set_managers()

# %% Suport
@app.route('/print')        
def print_special():
    if flask_session['login'] == "ZCFV":
        return {"1.ENVIRONMENT_ID": config("ENVIRONMENT_ID", "nao carregada"),
                "2.CAV4_PASSWORD": config("CAV4_PASSWORD", "nao carregada"),
                "3.DATABRICKS_TOKEN": config("DATABRICKS_TOKEN", "nao carregada"),
                "4.AZURE_OPENAI_API_KEY": config("AZURE_OPENAI_API_KEY", "nao carregada"),
                "5.POSTGRES_PASSWORD": config("POSTGRES_PASSWORD","nao carregada")}
    else: return {"Message": "nothing to show"}
    
# %% Routes
###############################
@app.route('/', methods=['GET', 'POST'])
def chat():
    
    if 'chat_id' not in flask_session:
        print('app: chat initiate', flush=True)

        flask_session['user_context'] = {
            'user': flask_session['name'].split(' ')[0].capitalize(),
            'user_id': flask_session['login'],
            'user_img': 'http://rondafotosp.petrobras.com.br/{}.jpg?'.format(flask_session['registration']),
            'user_email': flask_session['email'],
            'user_role': list_user_roles()[0]["roles"],
            'segment': 'chat.html'
        }
        
        initiate_section(flask_session['login'])
                        
        flask_session['crew_work_complete'] = True
             
    if flask_request.method == 'POST':
        
        
        user_question = flask_request.form.get('user_input', '')
        print(f'app: chat POST. user_question: {user_question[:20]}', flush=True)
        flask_session['crew_work_complete'] = False
        
        agent_work = global_session_db.load_session(flask_session['login'], 'agent_work')
        
        global global_section
        with global_section_lock:
            global_section[flask_session['login']]['agent_work'] = agent_work

        def process_crew_work(user_question, agent_work):
            '''
            Gerencia a atualização do chat em tempo de execução
            '''
            # agent_work.crew_work(user_question)
            try:
                agent_work.crew_work(user_question)
            finally:
                print("app: pop agent_work from global_section", flush=True)
                agent_work = None
                        
        # Inicia o processamento em um thread separado
        thread = Thread(target=process_crew_work, args=(user_question, global_section[flask_session['login']]['agent_work']))
        thread.start()
        
        return redirect(url_for('chat')) # Redireciona após o envio para evitar o reenvio em atualização de página
           
    agent_work = global_session_db.load_session(flask_session['login'], 'agent_work')
    paired_data = agent_work.pair_data_to_chat()
    chat_list = agent_work.chat_memory.list_chat_titles_and_ids()
    current_chat = agent_work.chat_memory.chat_id
    
    return render_template(
        'home/chat.html',
        paired_data = paired_data,
        agent_states = flask_session['agent_states'],
        agent_collections = flask_session['agent_collections'],
        personal_knowledge_agent_name = personal_knowledge_agent_name,
        local_analytics_agent_name = local_analytics_agent_name,
        chat_list = chat_list or [],
        current_chat = current_chat,
        user_context = flask_session['user_context'],
    )

@app.route('/get_answers')
def get_answers():
    print('app: get_answers', flush=True)

    if global_section[flask_session['login']]['agent_work']:
        paired_data = global_section[flask_session['login']]['agent_work'].pair_data_to_chat()
    else:
        agent_work = global_session_db.load_session(flask_session['login'], 'agent_work')
        paired_data = agent_work.pair_data_to_chat()

    return jsonify({
        'paired_data': paired_data,
        'complete': flask_session['crew_work_complete']
    })
    
@app.route('/toggle_agent', methods=['POST'])
def toggle_agent():
    print('app: toggle_agent', flush=True)
        
    data = flask_request.get_json()
    agent_id = data.get('agent_id')
    is_active = data.get('active')

    flask_session['agent_states'][agent_id] = is_active

    return jsonify({"status": "success", "agent": agent_id, "active": is_active})

@app.route('/update_collection_list', methods=['POST'])
def update_collection_list():
    print('app: update_collection_list', flush=True)
    
    data = flask_request.get_json()
    agent_name = data.get('agent_name')
    collection = data.get('collection')
    is_active = data.get('is_active')
    
    flask_session['agent_collections'][agent_name][collection] = is_active
    
    return jsonify({"status": "success", "agent": agent_name, "collection": collection, "is_active": is_active})

@app.route('/create_personal_collection', methods=['POST'])
def create_personal_collection_route():
    print('app: create_personal_collection_route', flush=True)

    agent_work = global_session_db.load_session(flask_session['login'], 'agent_work')
    # user_BaseAgent = dill.loads(base64.b64decode(flask_session['user_BaseAgent']))
    doc_manager_local = agent_work.agents[personal_knowledge_agent_name]['agent'].KnowledgeBase
    
    data = flask_request.json

    def create_doc_personal_collection(
        nome_da_colecao,
        table_common_name=None, curator=None, table_description=None, gpt_instructions=None,
        doc_manager_local=None
    ):
        print('app: create_doc_personal_collection', flush=True)
        doc_manager_local.create_collection(
            collection_name   = nome_da_colecao,
            table_common_name = table_common_name,
            curator           = curator,
            description       = table_description,
            gpt_instructions  = gpt_instructions
            )

        return {personal_knowledge_agent_name: {nome_da_colecao: True}}
    
    new_collection = create_doc_personal_collection(
        nome_da_colecao=data['nome_da_colecao'],
        table_common_name=data.get('table_common_name'),
        curator=data.get('curator'),
        table_description=data.get('table_description'),
        gpt_instructions=data.get('gpt_instructions'),
        doc_manager_local=doc_manager_local
    )
    
    global_session_db.save_sessiont(flask_session['login'], 'agent_work', agent_work)
    
    for agent_name, collections in new_collection.items():
        if agent_name in flask_session['agent_collections']:
            flask_session['agent_collections'][agent_name].update(collections)
        else:
            flask_session['agent_collections'][agent_name] = collections

    return jsonify({"status": "success", "new_collection": new_collection})

@app.route('/add_document', methods=['POST'])
def add_document():
    print('app: add_document', flush=True)

    agent_work = global_session_db.load_session(flask_session['login'], 'agent_work')
    # user_BaseAgent = dill.loads(base64.b64decode(flask_session['user_BaseAgent']))
    llm = agent_work.llm
    doc_manager_local = agent_work.agents[personal_knowledge_agent_name]['agent'].KnowledgeBase     
    
    nome_colecao = flask_request.form.get('nome_colecao', 'Sem nome')
    file = flask_request.files.get('file_for_doc_collection')  # Recebe o arquivo diretamente

    if not file:
        return jsonify({"message": "Nenhum arquivo foi selecionado."}), 400

    # Lê o conteúdo do arquivo diretamente para evitar problemas de fechamento de arquivo na thread
    file = {
        'file_content': file.read(),
        'file_name': file.filename}
    
    # Parâmetros opcionais
    words_per_chunk = 200
    overlap = 15
    metadata_dictionary = {}
    
    def add_doc_to_personal_collection(
        nome_colecao, file, words_per_chunk=200, overlap=15, metadata_dictionary={},
        llm=None, doc_manager_local=None):

        from Petrobras_AI_Agents import read_file
        
        doc_manager_local.upload_document(
            collection_name     = nome_colecao,
            file                = file,
            read_file_class     = read_file,
            llm_client          = llm,
            words_per_chunk     = words_per_chunk,
            overlap             = overlap,
            metadata_dictionary = metadata_dictionary
            )
        
        print("app: Processamento concluído.", flush=True)
        return 'Concluido.'
    
    # Processo assíncrono
    thread = Thread(target=add_doc_to_personal_collection, args=(nome_colecao, file, words_per_chunk, overlap, metadata_dictionary, llm, doc_manager_local))
    thread.start()

    global_session_db.save_sessiont(flask_session['login'], 'agent_work', agent_work)
    
    return jsonify({"message": "O processamento do documento foi iniciado. Você será notificado quando concluído."})

@app.route('/create_table_collection', methods=['POST'])
def create_table_collection_route():
    print('app: create_table_collection_route', flush=True)

    agent_work = global_session_db.load_session(flask_session['login'], 'agent_work')
    # user_BaseAgent = dill.loads(base64.b64decode(flask_session['user_BaseAgent']))
    dataanalytics_local = agent_work.agents[local_analytics_agent_name]['agent'].KnowledgeBase    
    
    data = flask_request.json
    
    def create_table_personal_collection(
        nome_da_colecao, process_description, relationships,
        dataanalytics_local):
        
        dataanalytics_local.add_datasource(
            data_source         = nome_da_colecao,
            process_description = process_description,
            relationships       = relationships
        )
        
        return {local_analytics_agent_name: {nome_da_colecao: True}}
    
    new_collection = create_table_personal_collection(
        nome_da_colecao=data['nome_tabela_colecao'],
        process_description=data['process_description'],
        relationships=data.get('relationships'),
        dataanalytics_local=dataanalytics_local
        )
    
    global_session_db.save_sessiont(flask_session['login'], 'agent_work', agent_work)
    
    for agent_name, collections in new_collection.items():
        if agent_name in flask_session['agent_collections']:
            flask_session['agent_collections'][agent_name].update(collections)
        else:
            flask_session['agent_collections'][agent_name] = collections
    
    return jsonify({"status": "success", "new_collection": new_collection})

@app.route('/add_table_to_collection', methods=['POST'])
def add_table_to_collection():
    print('app: add_table_to_collection', flush=True)
    print(f"app: Dados recebidos em request.form: {flask_request.form}", flush=True)  # Exibe todos os dados do form
    print(f"app: Dados recebidos em request.files: {flask_request.files}", flush=True)  # Exibe todos os arquivos

    agent_work = global_session_db.load_session(flask_session['login'], 'agent_work')
    # user_BaseAgent = dill.loads(base64.b64decode(flask_session['user_BaseAgent']))
    dataanalytics_local = agent_work.agents[local_analytics_agent_name]['agent'].KnowledgeBase        
        
    tabela_colecao = flask_request.form.get('tabela_colecao', 'Sem nome')
    table_name = flask_request.form.get('table_name')
    csv_file = flask_request.files.get('csv_file')
    column_type = flask_request.form.get('column_type', '{}')  # JSON como string

    if not csv_file:
        return jsonify({"message": "Nenhum arquivo foi selecionado."}), 400

    file_data = {
        'file_content': csv_file.read(),
        'file_name': csv_file.filename
    }

    def add_table_to_personal_collection(
        nome_colecao, csv_file, table_name, column_type={},
        dataanalytics_local=None):

        if table_name == "":
            table_name=None
        dataanalytics_local.load_csv_to_table(
            data_source         = nome_colecao,
            csv_file            = csv_file,
            table_name          = table_name,
            column_type         = column_type
        )
        
        print("app: Processamento concluído.", flush=True)
        return 'Concluido.'    

    # Inicia o processo em uma nova thread
    thread = Thread(target=add_table_to_personal_collection, args=(tabela_colecao, file_data, table_name, column_type, dataanalytics_local))
    thread.start()

    global_session_db.save_sessiont(flask_session['login'], 'agent_work', agent_work)
    
    return jsonify({"message": "Processamento da tabela iniciado."})

@app.route('/new_chat', methods=['POST'])
def new_chat():
    print('app: new_chat', flush=True)

    agent_work = global_session_db.load_session(flask_session['login'], 'agent_work')
    agent_work.new_chat(user=flask_session['login'])
    global_session_db.save_sessiont(flask_session['login'], 'agent_work', agent_work)
    flask_session['chat_id'] = agent_work.chat_memory.chat_id

    return jsonify({"status": "success"})

@app.route('/recover_chat', methods=['POST'])
def recover_chat():
    print(f'app: recover_chat {flask_request.json.get("chat_id")}', flush=True)
    
    flask_session['chat_id'] = flask_request.json.get("chat_id")
    
    agent_work = global_session_db.load_session(flask_session['login'], 'agent_work')
    agent_work.chat_memory.update_chat_id(flask_session['chat_id'])
    global_session_db.save_sessiont(flask_session['login'], 'agent_work', agent_work)
    paired_data = agent_work.pair_data_to_chat(force_recovery=True)
    
    return jsonify({"status": "success", "paired_data": paired_data})

@app.route('/edit_chat_title', methods=['POST'])
def edit_chat_title():
    print('edit_chat_title', flush=True)
    
    data = flask_request.json
    chat_id = data.get("chat_id", 'erro')
    new_title = data.get("new_title")
    
    agent_work = global_session_db.load_session(flask_session['login'], 'agent_work')
    agent_work.chat_memory.update_chat_history(chat_id, new_title)
    
    return jsonify({"status": "success"})

@app.route('/delete_chat', methods=['POST'])
def delete_chat():
    data = flask_request.json
    chat_id = data.get("chat_id", 'erro')
    print(f'delete chat {chat_id}', flush=True)
    
    agent_work = global_session_db.load_session(flask_session['login'], 'agent_work')
    flask_session['chat_id'] = agent_work.chat_memory.delete_chat_history(chat_id)
    global_session_db.save_sessiont(flask_session['login'], 'agent_work', agent_work)
    paired_data = agent_work.pair_data_to_chat(force_recovery=True)
    
    return jsonify({"status": "success", "paired_data": paired_data})

# %% app.run
if __name__ == "__main__":
    # schedule_task()
    
    app.run(debug=True, threaded=True)
    
