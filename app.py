from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, make_response
from threading import Thread
import base64
import io
import os
import json
import time
import webbrowser
import sys

# Importações das suas classes e módulos
from Petrobras_AI_Agents import llmClient_AzureOpenAI as llmClient
from Petrobras_AI_Agents import ChatDatabaseManager_SQLite as ChatMemory
from Petrobras_AI_Agents import KnowledgeBaseManager_Databricks as Databricks_KnowledgeBase
from Petrobras_AI_Agents import KnowledgeBaseManager_SQLite as PersonalCollection
from Petrobras_AI_Agents import DatabaseManager_SQLite, DatabaseManager_Databricks
from Petrobras_AI_Agents import BaseAgent, ChatInterpretorAgent, KnowledgeBaseAgent, MemoryAgent, DatabaseExpertAgent
from Petrobras_AI_Agents import read_file, databricks_connector
from Petrobras_AI_Agents.TOOLS import basic_calculator, run_python_code, search_web

# Define o caminho base como o diretório do executável ou do script
if getattr(sys, 'frozen', False):  # Verifica se está sendo executado como um executável PyInstaller
    base_dir = sys._MEIPASS  # Diretório temporário onde o PyInstaller extrai os arquivos
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

# Configura o Flask com as pastas `templates` e `static` com base no `base_dir`
app = Flask(
    __name__, 
    template_folder=os.path.join(base_dir, 'templates'),
    static_folder=os.path.join(base_dir, 'static')
)

BaseAgent.chat_mode = True
BaseAgent.language = "pt-br"
BaseAgent.st = None  # Não estamos usando Streamlit aqui
databricks_connector = databricks_connector()

# Configuração inicial
username = os.getlogin().upper()

BaseAgent.llm = llmClient( model_text="gpt-4o-petrobras", model_emb="text-embedding-3-large-petrobras",
    api_version="2024-06-01",  # "2024-08-01-preview",
    base_url="https://apid.petrobras.com.br/ia/openai/v1/openai-azure/openai",
    cert_file="petrobras-ca-root.pem",
    temperature=0.1
)
BaseAgent.chat_memory = ChatMemory(db_url="sqlite:///data_base/zdb_memory.db", user=username, language=BaseAgent.language)

# Agentes

chat_interpretor_agent = ChatInterpretorAgent(agent_name="Chat Analista",
    human_in_the_loop=False
)
BaseAgent.start_agent = chat_interpretor_agent

doc_manager_databricks = Databricks_KnowledgeBase(config_json="config_json\\\databricks\\config_databricks_doc_collection.json", user=username, connection=databricks_connector)
databricks_knowledge_agent = KnowledgeBaseAgent(agent_name="Documentos Internos", k=5,
    allow_direct_response=True,
    KnowledgeBase=doc_manager_databricks,
    human_in_the_loop=False,
)

dataanalytics_databricks = DatabaseManager_Databricks(config_json="config_json\\databricks\\config_databricks_datasources.json", user=username, connection=databricks_connector)
databricks_analytics_agent = DatabaseExpertAgent(agent_name="Analytics Databricks",
    database_manager=dataanalytics_databricks,
    human_in_the_loop=False,
    allow_direct_response=True,
)

PersonalCollection.create_config_file(config_json = "config_json\\personal\\config_personal_doc_collection.json", db_url="sqlite:///data_base/zdb_personal_collection.db")
doc_manager_local = PersonalCollection()
personal_knowledge_agent = KnowledgeBaseAgent( agent_name="Documentos Pessoais", k=5,
    KnowledgeBase           = doc_manager_local,
    human_in_the_loop       = False,
    allow_direct_response   = True,
)

DatabaseManager_SQLite.create_config_file(config_json="config_json\\personal\\config_personal_datasources.json", db_url="sqlite:///data_base/zdb_analysis_database.db")
dataanalytics_local = DatabaseManager_SQLite()
local_analytics_agent = DatabaseExpertAgent(agent_name="Analytics Pessoal",
    database_manager      = dataanalytics_local,
    human_in_the_loop     = False,
    allow_direct_response = True,
)

search_agent = BaseAgent(agent_name="Informações Web", allow_direct_response=False, next_agent_list=[chat_interpretor_agent],
    background=[
        "Este agente realiza pesquisas na web para recuperar informações não disponíveis localmente."
        ],
    goal=[
        "Fornecer informações relevantes e atualizadas da web.",
        "Interprete a solicitação do usuário para gerar a melhor busca possível.",
        "Use seus conhecimentos para gerar a melhor query possível"
        ],
    tools=[search_web]
)

# Controls
if 'agent_states' not in globals():
    agent_states = {
        databricks_knowledge_agent.agent_name: BaseAgent.agents[databricks_knowledge_agent.agent_name]['active'],
        databricks_analytics_agent.agent_name: BaseAgent.agents[databricks_analytics_agent.agent_name]['active'],
        personal_knowledge_agent.agent_name  : BaseAgent.agents[personal_knowledge_agent.agent_name]['active'],
        local_analytics_agent.agent_name     : BaseAgent.agents[local_analytics_agent.agent_name]['active'],
        search_agent.agent_name              : BaseAgent.agents[search_agent.agent_name]['active'],
    }
    
if 'agent_collections' not in globals():
    agent_collections = {
        databricks_knowledge_agent.agent_name: {collection: True for collection in doc_manager_databricks.available_collections},
        databricks_analytics_agent.agent_name: {collection: True for collection in dataanalytics_databricks.available_collections},
        personal_knowledge_agent.agent_name  : {collection: True for collection in doc_manager_local.available_collections},
        local_analytics_agent.agent_name     : {collection: True for collection in dataanalytics_local.available_collections},
        }

crew_work_complete = False

# Functions & Routes
def process_crew_work(user_input):
    '''
    Gerencia a atualização do chat em tempo de execução
    '''
    global crew_work_complete
    BaseAgent.crew_work(user_input)
    crew_work_complete = True
    
def set_agent_state(agent_name, active):
    print(f"Atualizando estado do agente: {agent_name} para {'ativo' if active else 'inativo'}")
    agent_states[agent_name] = active
    BaseAgent.find_by_name(agent_name)['agent'].active(active)

def set_collection_list(agent_name, collection, active):
    print(f"Atualizando coleção {collection} para o agente {agent_name}")
    agent_collections[agent_name][collection] = active
    # Atualiza a lista de coleções ativas para o agente
    selected_list = [col for col, is_active in agent_collections[agent_name].items() if is_active]
    BaseAgent.find_by_name(agent_name)['agent'].collection_list = selected_list

def create_doc_personal_collection(
    nome_da_colecao,
    table_common_name=None, curator=None, table_description=None, gpt_instructions=None,
):
    print('create_doc_personal_collection')
    doc_manager_local.create_collection(
    collection_name   = nome_da_colecao,
    table_common_name = table_common_name,
    curator           = curator,
    description       = table_description,
    gpt_instructions  = gpt_instructions
    )

    return {personal_knowledge_agent.agent_name: {nome_da_colecao: True}}

def add_doc_to_personal_collection(nome_colecao, file, words_per_chunk=200, overlap=15, metadata_dictionary={}):

    doc_manager_local.upload_document(
        collection_name     = nome_colecao,
        file                = file,
        read_file_class     = read_file,
        llm_client          = BaseAgent.llm,
        words_per_chunk     = words_per_chunk,
        overlap             = overlap,
        metadata_dictionary = metadata_dictionary
        )
    
    print("Processamento concluído.")
    return 'Concluido.'

def create_table_personal_collection(nome_da_colecao, process_description, relationships):
    
    dataanalytics_local.add_datasource(
        data_source         = nome_da_colecao,
        process_description = process_description,
        relationships       = relationships
    )
    
    return {local_analytics_agent.agent_name: {nome_da_colecao: True}}

def add_table_to_personal_collection(nome_colecao, csv_file, table_name, column_type={}):

    if table_name == "":
        table_name=None
    dataanalytics_local.load_csv_to_table(
        data_source         = nome_colecao,
        csv_file            = csv_file,
        table_name          = table_name,
        column_type         = column_type
    )
    
    print("Processamento concluído.")
    return 'Concluido.'    

def open_browser():
    time.sleep(1)  # Espera um segundo para o servidor iniciar
    chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe %s"  # Caminho do Chrome no Windows
    webbrowser.get(chrome_path).open("http://127.0.0.1:5000")
    
# Renderiza o chat com garantia de que tool_result_for_chat é uma lista adequada
@app.route('/', methods=['GET', 'POST'])
def chat():
    global crew_work_complete  # Apenas crew_work_complete como global

    if request.method == 'POST':
        user_question = request.form.get('user_input', '')
        crew_work_complete = False

        # Inicia o processamento em um thread separado
        thread = Thread(target=process_crew_work, args=(user_question,))
        thread.start()

        # Redireciona após o envio para evitar o reenvio em atualização de página
        return redirect(url_for('chat'))

    # Usa zip para juntar cada resposta com o status correspondente e passa agent_states e agent_collections
    paired_data = list(zip(BaseAgent.answers, BaseAgent.screem_presentation, BaseAgent.tool_result_for_chat))

    chat_list = BaseAgent.chat_memory.list_chat_titles_and_ids()
    
    return render_template(
        'chat.html',
        paired_data=paired_data,
        agent_states=agent_states,
        agent_collections=agent_collections,
        personal_knowledge_agent_name=personal_knowledge_agent.agent_name,
        local_analytics_agent_name = local_analytics_agent.agent_name,
        chat_list=chat_list or [],
        current_chat = BaseAgent.chat_memory.chat_id
    )

@app.route('/get_answers')
def get_answers():
    paired_data = []
    for answer, status, attachment in zip(BaseAgent.answers, BaseAgent.screem_presentation, BaseAgent.tool_result_for_chat):
        # Ensure attachment is not None or empty
        if not attachment:
            attachment = []
        paired_data.append((answer, status, attachment))
    # print('BaseAgent.tool_result_for_chat', BaseAgent.tool_result_for_chat)
    return jsonify({
        'paired_data': paired_data,
        'complete': crew_work_complete
    })

@app.route('/toggle_agent', methods=['POST'])
def toggle_agent():
    data = request.get_json()
    agent_id = data.get('agent_id')
    is_active = data.get('active')

    # Atualiza o estado do agente correspondente
    set_agent_state(agent_id, is_active)
    print("Estado atualizado de agent_states:", agent_states)  # Para debug

    return jsonify({"status": "success", "agent": agent_id, "active": is_active})

@app.route('/update_collection_list', methods=['POST'])
def update_collection_list():
    data = request.get_json()
    agent_name = data.get('agent_name')
    collection = data.get('collection')
    is_active = data.get('is_active')
    
    # Aplica o estado da coleção para o agente específico
    set_collection_list(agent_name, collection, is_active)
    print(f"Lista de coleções atualizada para {agent_name}: {agent_collections[agent_name]}")  # Para debug

    return jsonify({"status": "success", "agent": agent_name, "collection": collection, "is_active": is_active})

@app.route('/create_personal_collection', methods=['POST'])
def create_personal_collection_route():
    data = request.json
    new_collection = create_doc_personal_collection(
        nome_da_colecao=data['nome_da_colecao'],
        table_common_name=data.get('table_common_name'),
        curator=data.get('curator'),
        table_description=data.get('table_description'),
        gpt_instructions=data.get('gpt_instructions')
    )
    # new_collection é um dicionário aninhado, ex: { "Documentos Pessoais": { "Nova Coleção": True } }
    for agent_name, collections in new_collection.items():
        if agent_name in agent_collections:
            agent_collections[agent_name].update(collections)
        else:
            # Se o agente não existir, cria uma nova entrada
            agent_collections[agent_name] = collections
    return jsonify({"status": "success", "new_collection": new_collection})

@app.route('/add_document', methods=['POST'])
def add_document():
    nome_colecao = request.form.get('nome_colecao', 'Sem nome')
    file = request.files.get('file_for_doc_collection')  # Recebe o arquivo diretamente

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

    # Processo assíncrono
    thread = Thread(target=add_doc_to_personal_collection, args=(nome_colecao, file, words_per_chunk, overlap, metadata_dictionary))
    thread.start()

    return jsonify({"message": "O processamento do documento foi iniciado. Você será notificado quando concluído."})

@app.route('/create_table_collection', methods=['POST'])
def create_table_collection_route():
    data = request.json
    new_collection = create_table_personal_collection(
        nome_da_colecao=data['nome_tabela_colecao'],
        process_description=data['process_description'],
        relationships=data.get('relationships')
    )
    for agent_name, collections in new_collection.items():
        if agent_name in agent_collections:
            agent_collections[agent_name].update(collections)
        else:
            agent_collections[agent_name] = collections
    return jsonify({"status": "success", "new_collection": new_collection})

@app.route('/add_table_to_collection', methods=['POST'])
def add_table_to_collection():
    print("Dados recebidos em request.form:", request.form)  # Exibe todos os dados do form
    print("Dados recebidos em request.files:", request.files)  # Exibe todos os arquivos
    
    tabela_colecao = request.form.get('tabela_colecao', 'Sem nome')
    table_name = request.form.get('table_name')
    csv_file = request.files.get('csv_file')
    column_type = request.form.get('column_type', '{}')  # JSON como string

    if not csv_file:
        return jsonify({"message": "Nenhum arquivo foi selecionado."}), 400

    file_data = {
        'file_content': csv_file.read(),
        'file_name': csv_file.filename
    }

    # Inicia o processo em uma nova thread
    thread = Thread(target=add_table_to_personal_collection, args=(tabela_colecao, file_data, table_name, column_type))
    thread.start()

    return jsonify({"message": "Processamento da tabela iniciado."})

@app.route('/new_chat', methods=['POST'])
def new_chat():
    username = request.json.get("username")
    BaseAgent.new_chat(user=username)
    return jsonify({"status": "success"})

@app.route('/recover_chat', methods=['POST'])
def recover_chat():
    chat_id = request.json.get("chat_id")
    print('recover', chat_id)
    BaseAgent.recover_chat(chat_id=chat_id)
    paired_data = list(zip(BaseAgent.answers, BaseAgent.screem_presentation, BaseAgent.tool_result_for_chat))
    return jsonify({"status": "success", "paired_data": paired_data})

@app.route('/edit_chat_title', methods=['POST'])
def edit_chat_title():
    data = request.json
    chat_id = data.get("chat_id", 'erro')
    new_title = data.get("new_title")
    BaseAgent.chat_memory.update_chat_history(chat_id, new_title)
    return jsonify({"status": "success"})

@app.route('/delete_chat', methods=['POST'])
def delete_chat():
    print('delete chat')
    data = request.json
    chat_id = data.get("chat_id", 'erro')

    new_chat_id = BaseAgent.chat_memory.delete_chat_history(chat_id)
    BaseAgent.recover_chat(chat_id=new_chat_id)
    paired_data = list(zip(BaseAgent.answers, BaseAgent.screem_presentation, BaseAgent.tool_result_for_chat))
    return jsonify({"status": "success", "paired_data": paired_data})

if __name__ == "__main__":
    # Inicia uma thread para abrir o navegador e depois executa o Flask
    Thread(target=open_browser).start()
    app.run(host="127.0.0.1", port=5000)