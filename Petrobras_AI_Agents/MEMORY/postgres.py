from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid
from contextlib import contextmanager
from .base import BaseChatDatabaseManager, ChatHistory, ChatMessage, ChatAgencyFlow, generate_default_title
from .base import AppSessionManager, AppSession
from datetime import datetime
import dill
import base64

class AppSessionManager_Postgres(AppSessionManager):
    def __init__(self, db_path: str):
        self.db_url = f"postgresql://{db_path}"        
        if not self.db_url.startswith("postgresql://"):
            raise ValueError("ChatDatabaseManager_Postgres: A URL do banco deve começar com 'postgresql://'.")
        
        # Cria as tabelas no esquema `public` se ainda não existirem
        with create_engine(self.db_url).connect() as connection:
            self.__class__.Base.metadata.create_all(connection.engine)

    @contextmanager
    def session_scope(self):
        """Proporciona um escopo transacional para operações com o banco."""
        engine = create_engine(self.db_url) 
        SessionFactory = sessionmaker(bind=engine)
        session = SessionFactory()

        try:
            yield session
            session.flush()
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    def save_sessiont(self, user, obj_name, obj):
        """Serializa e salva um objeto no banco de dados."""
        serialized_obj = base64.b64encode(dill.dumps(obj)).decode('utf-8')
        with self.session_scope() as session:
            app_session = AppSession(user=user, session_dict={obj_name: serialized_obj})
            session.merge(app_session)
    
    def load_session(self, user, obj_name):
        """Carrega e desserializa um objeto a partir do banco de dados."""
        with self.session_scope() as session:
            app_session = session.query(AppSession).filter_by(user=user).first()
            if app_session and obj_name in app_session.session_dict:
                serialized_obj = app_session.session_dict[obj_name]
                return dill.loads(base64.b64decode(serialized_obj))
            return None
                    
class ChatDatabaseManager_Postgres(BaseChatDatabaseManager):
    
    def __init__(self, db_path: str, user: str, language: str, chat_id=None):
        """
        Inicializa a conexão com o banco PostgreSQL.

        # :param db_url: URL de conexão do PostgreSQL (exemplo: postgresql://user:password@host:port/dbname)
        :param user: Nome do usuário para garantir isolamento dos dados.
        :param language: Idioma do chat.
        :param chat_id: ID do chat existente a ser carregado (opcional).
        """

        self.db_url = f"postgresql://{db_path}"        
        if not self.db_url.startswith("postgresql://"):
            raise ValueError("ChatDatabaseManager_Postgres: A URL do banco deve começar com 'postgresql://'.")

        self.user = user
        self.language = language
        
        # Cria as tabelas no esquema `public` se ainda não existirem
        with create_engine(self.db_url).connect() as connection:
            self.__class__.Base.metadata.create_all(connection.engine)

        if chat_id: self.update_chat_id()
        else: self.create_new_chat(user=self.user, language=self.language)

        self._delete_empty_chats()

    @property
    def generate_uuid(self):
        """Gera um UUID em formato string."""
        return str(uuid.uuid4())

    @contextmanager
    def session_scope(self):
        """Proporciona um escopo transacional para operações com o banco."""
        engine = create_engine(self.db_url) 
        SessionFactory = sessionmaker(bind=engine)
        session = SessionFactory()

        try:
            yield session
            session.flush()
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
            engine.dispose()  # Fecha todas as conexõe

    def update_chat_id(self, chat_id):
        self.chat_id = self._get_existing_chat(chat_id)

        if self.chat_id:
            self.message_id, self.message_order = self._get_last_message(chat_id)
        else:
            raise ValueError(f"ChatDatabaseManager_Postgres: Chat ID {chat_id} não encontrado no banco de dados para o usuário {self.user}.")
        
    def create_new_chat(self, user, language, chat_title=None):
        """Cria um novo chat na tabela ChatHistory, garantindo que seja vinculado ao usuário."""
        chat_title = chat_title or generate_default_title()
        
        with self.session_scope() as session:
            new_chat = ChatHistory(
                chat_id=self.generate_uuid,
                chat_title=chat_title,
                user=user,  # 🔹 Garante que o chat pertence ao usuário
                language=language
            )
            session.add(new_chat)
            session.flush()
            
            self.message_id = None
            self.message_order = 0
            self.chat_id = new_chat.chat_id

    def _delete_empty_chats(self):
        """Remove chats do usuário que não possuem mensagens associadas."""
        with self.session_scope() as session:
            empty_chats = session.query(ChatHistory.chat_id).filter(
                ChatHistory.user == self.user,  # 🔹 Garante que só remove chats do usuário atual
                ~ChatHistory.chat_id.in_(
                    session.query(ChatMessage.chat_id).distinct()
                )
            ).all()

            if empty_chats:
                session.query(ChatHistory).filter(
                    ChatHistory.chat_id.in_([chat.chat_id for chat in empty_chats if chat.chat_id != self.chat_id])
                ).delete(synchronize_session=False)

    def _get_existing_chat(self, chat_id):
        """Recupera um chat existente do usuário."""
        with self.session_scope() as session:
            existing_chat = session.query(ChatHistory).filter_by(chat_id=chat_id, user=self.user).first()
            return existing_chat.chat_id if existing_chat else None

    def _get_last_message(self, chat_id):
        """Recupera a última mensagem de um chat do usuário."""
        with self.session_scope() as session:
            last_message = session.query(ChatMessage).filter_by(chat_id=chat_id, user=self.user).order_by(ChatMessage.order.desc()).first()
            return (last_message.message_id, last_message.order) if last_message else (None, 0)

    def create_initial_message(self):
        """Cria uma nova linha em ChatMessage e retorna o message_id."""
        self.message_order += 1  # Incrementa o order da mensagem
        with self.session_scope() as session:
            new_message = ChatMessage(
                user=self.user,
                related_chat_id=self.message_id,  # ID da última mensagem
                chat_id=self.chat_id,
                order=self.message_order
            )
            session.add(new_message)
            session.flush()  # Garante que o message_id seja retornado
            self.agent_order = 0  # Reinicia o agent_order para o novo fluxo de agentes
            self.message_id = new_message.message_id  # Atualiza o message_id para o novo
            
        return self.message_id

    def add_chat_agency_flow(self, agent_name, agent_prompt, agent_context, agent_response, agent_tool):
        """
        Adiciona um novo fluxo na tabela ChatAgencyFlow.
        Usa o message_id atualizado pela create_initial_message.
        """
        if not self.message_id:
            raise ValueError("ChatDatabaseManager_Postgres: Nenhuma mensagem foi criada. Crie uma mensagem antes de adicionar o fluxo de agentes.")

        self.agent_order += 1  # Incrementa o order do fluxo de agentes
        with self.session_scope() as session:
            new_agency_flow = ChatAgencyFlow(
                user=self.user,
                message_id=self.message_id,  # Usa a mensagem atual
                order=self.agent_order,
                agent_name=agent_name,
                agent_prompt=agent_prompt,
                agent_context=agent_context,
                agent_response=agent_response,
                agent_tool=agent_tool
            )
            session.add(new_agency_flow)

    def update_message(self, user_query=None, final_answer=None, screem_presentation=None, tool_result_for_chat=None):
        """
            Atualiza os campos de ChatMessage e encerra a sessão.
            Atualiza a última mensagem (self.message_id).
        """
        if not self.message_id:
            raise ValueError("ChatDatabaseManager_Postgres: Nenhuma mensagem foi criada. Crie uma mensagem antes de atualizar.")

        with self.session_scope() as session:
            message = session.query(ChatMessage).filter_by(message_id=self.message_id).first()
            if message:
                if user_query           : message.user_query   = user_query
                if final_answer         : message.final_answer = final_answer
                if screem_presentation  : message.screem_presentation  = screem_presentation
                if tool_result_for_chat : message.tool_result_for_chat = tool_result_for_chat
          
    def delete_chat_history(self, chat_id):
        """Remove um chat e suas mensagens associadas, garantindo que pertence ao usuário."""
        with self.session_scope() as session:
            chat = session.query(ChatHistory).filter_by(chat_id=chat_id, user=self.user).first()
            if not chat:
                raise ValueError(f"O chat {chat_id} não pertence ao usuário {self.user}.")

            # Recupera o chat mais recente do usuário, excluindo o que será apagado
            latest_chat = session.query(ChatHistory)\
                .filter(ChatHistory.chat_id != chat_id, ChatHistory.user == self.user)\
                .order_by(ChatHistory.created_at.desc())\
                .first()

            # Define um novo chat ativo caso seja necessário
            if latest_chat:
                self.chat_id = latest_chat.chat_id
            else:
                self.create_new_chat(user=self.user, language=self.language)

            # Apagar as mensagens e os fluxos de agentes do chat
            session.query(ChatAgencyFlow).filter(
                ChatAgencyFlow.message_id.in_(
                    session.query(ChatMessage.message_id).filter_by(chat_id=chat_id)
                )
            ).delete(synchronize_session=False)

            session.query(ChatMessage).filter_by(chat_id=chat_id).delete(synchronize_session=False)
            session.query(ChatHistory).filter_by(chat_id=chat_id).delete(synchronize_session=False)

        return self.chat_id

    def list_chat_titles_and_ids(self):
        """Lista os chats do usuário, ordenados pelo mais recente."""
        with self.session_scope() as session:
            chats = session.query(ChatHistory.chat_id, ChatHistory.chat_title).filter(
                        ChatHistory.user == self.user  # 🔹 Filtra pelo usuário
                    ).order_by(ChatHistory.created_at.desc()).all()
            return [{'chat_id': chat.chat_id, 'chat_title': chat.chat_title} for chat in chats]

    def update_chat_history(self, chat_id=None, chat_title: str = None, agent_prompt=None, star_status: bool = None):
        """Atualiza o título e/ou o status de estrela de um chat do usuário."""
        chat_id = chat_id or self.chat_id
        with self.session_scope() as session:
            chat = session.query(ChatHistory).filter_by(chat_id=chat_id, user=self.user).first()
            if chat:
                if chat_title:
                    chat.chat_title = chat_title
                if star_status is not None:
                    chat.starry = star_status
                if agent_prompt is not None:
                    chat.agent_prompt = agent_prompt

    def get_chat_history(self, chat_id=None):
        """Recupera uma entrada de ChatHistory pelo ID do chat e retorna como dicionário no mesmo formato que get_chat_messages."""
        
        chat_id = chat_id or self.chat_id
        print(chat_id)
        
        with self.session_scope() as session:
            chat_history = session.query(ChatHistory).filter_by(chat_id=chat_id, user=self.user).first()
            
            if not chat_history:
                return {}  # Retorna um dicionário vazio caso não encontre o chat

            # Criar um dicionário no mesmo formato que `get_chat_messages`
            chat_history_dict = {}

            for col in ChatHistory.__table__.columns.keys():
                value = getattr(chat_history, col)
                if isinstance(value, datetime):
                    value = value.isoformat()
                chat_history_dict[col] = value

            return chat_history_dict

    def get_chat_messages(self, chat_id=None, limit=10, columns=None):
        """Recupera mensagens de um chat específico, garantindo que pertencem ao usuário."""
        
        chat_id = chat_id or self.chat_id
        
        with self.session_scope() as session:
            # Define o filtro padrão para garantir que apenas as mensagens do usuário sejam retornadas
            query = session.query(ChatMessage).filter_by(chat_id=chat_id, user=self.user).filter(ChatMessage.user_query.isnot(None))
            
            if columns:
                # Seleciona apenas as colunas especificadas
                selected_columns = [getattr(ChatMessage, col) for col in columns]
                query = query.with_entities(*selected_columns)

            messages = query.order_by(ChatMessage.order.asc()).limit(limit).all()

            # Criar uma lista de dicionários no mesmo formato do SQLite
            result = []
            for message in messages:
                message_dict = {}
                
                # Se usou `with_entities`, `message` será uma tupla, então precisa mapear as colunas
                if columns:
                    for col, value in zip(columns, message):
                        if isinstance(value, datetime):
                            value = value.isoformat()
                        message_dict[col] = value
                else:
                    # Se não usou `with_entities`, `message` é um objeto ORM e podemos acessar diretamente
                    for col in ChatMessage.__table__.columns.keys():
                        value = getattr(message, col)
                        if isinstance(value, datetime):
                            value = value.isoformat()
                        message_dict[col] = value
                
                result.append(message_dict)
            
            return result

    def get_agency_flow(self, message_id):
        """Recupera o fluxo de agência de uma mensagem, garantindo que pertence ao usuário."""
        with self.session_scope() as session:
            return session.query(ChatAgencyFlow).filter(
                ChatAgencyFlow.message_id == message_id,  # 🔹 Correção da cláusula de filtro
                ChatAgencyFlow.user == self.user  # 🔹 Garante que pertence ao usuário correto
            ).all()
