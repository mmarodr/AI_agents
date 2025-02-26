import copy
import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, String, JSON, TIMESTAMP, func, event
from sqlalchemy.dialects.sqlite import BLOB
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from contextlib import contextmanager
import uuid
import numpy as np
import os
import base64
import json
from .base import BaseChatDatabaseManager, ChatHistory, ChatMessage, ChatAgencyFlow, generate_default_title

logger = logging.getLogger(__name__)

class ChatDatabaseManager_SQLite(BaseChatDatabaseManager):
    
    def __init__(self, db_path:str=None, chat_title=None, user=None, language=None, chat_id=None):
        
        db_path = db_path or "zdb_memory.db"
        db_path = db_path.replace('\\', '/')
        db_url = f"sqlite:///{db_path}"
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.user = user
        self.language = language
        # Cria a engine do banco de dados
        self.engine = create_engine(db_url)
        # Cria as tabelas no banco de dados se ainda não existirem
        self.__class__.Base.metadata.create_all(self.engine)
        # Configura a fábrica de sessão para interagir com o banco de dados
        self.SessionFactory = sessionmaker(bind=self.engine)

        if chat_id:
            self.update_chat_id()
        else:
            # Cria um novo chat, chat_title pode ser None
            self.create_new_chat(user=self.user, language=self.language, chat_title=chat_title) # create a self.chat_id
            
        self._delete_empty_chats()
        
    @property
    def generate_uuid(self):
        """Gera um UUID em formato string."""
        return str(uuid.uuid4())

    @contextmanager
    def session_scope(self):
        """Proporciona um escopo transacional para operações com o banco."""
        session = self.SessionFactory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    def update_chat_id(self, chat_id):
        self.chat_id = self._get_existing_chat(chat_id)

        if self.chat_id:
            self.message_id, self.message_order = self._get_last_message(chat_id)
        else:
            raise ValueError(f"Chat ID {chat_id} não encontrado no banco de dados.")
        
    def create_new_chat(self, user, language, chat_title=None):
        """Cria uma nova entrada na tabela ChatHistory. chat_title pode ser None."""
        chat_title = chat_title or generate_default_title()
        
        with self.session_scope() as session:
            new_chat = ChatHistory(
                chat_id=self.generate_uuid,  # Usando a nova property
                chat_title=chat_title,       # Pode ser None e atualizado depois
                user=user,
                language=language
            )
            session.add(new_chat)
            session.flush()  # Garante que o chat_id seja retornado
            
            self.message_id = None  # Não há mensagens ainda
            self.message_order = 0  # Começa do zero
            
            self.chat_id = new_chat.chat_id

    def _delete_empty_chats(self):
        """Remove entradas de ChatHistory que não possuem mensagens associadas na tabela ChatMessage."""
        with self.session_scope() as session:
            # Encontra todos os chat_id na tabela ChatHistory que não têm mensagens na tabela ChatMessage
            empty_chats = session.query(ChatHistory.chat_id).filter(
                ~ChatHistory.chat_id.in_(
                    session.query(ChatMessage.chat_id).distinct()
                )
            ).all()

            # Remove os chats vazios da tabela ChatHistory
            if empty_chats:
                session.query(ChatHistory).filter(
                    ChatHistory.chat_id.in_([chat.chat_id for chat in empty_chats if chat.chat_id != self.chat_id])
                ).delete(synchronize_session=False)
                
    def _get_existing_chat(self, chat_id):
        """Recupera uma entrada de ChatHistory pelo ID do chat."""
        with self.session_scope() as session:
            existing_chat = session.query(ChatHistory).filter_by(chat_id=chat_id).first()
            return existing_chat.chat_id if existing_chat else None

    def _get_last_message(self, chat_id):
        """Recupera o último message_id e message_order de um chat existente."""
        with self.session_scope() as session:
            last_message = session.query(ChatMessage).filter_by(chat_id=chat_id).order_by(ChatMessage.order.desc()).first()
            if last_message:
                return last_message.message_id, last_message.order
            else:
                return None, 0  # Nenhuma mensagem foi encontrada

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
            raise ValueError("Nenhuma mensagem foi criada. Crie uma mensagem antes de adicionar o fluxo de agentes.")

        self.agent_order += 1  # Incrementa o order do fluxo de agentes
        with self.session_scope() as session:
            new_agency_flow = ChatAgencyFlow(
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
            raise ValueError("Nenhuma mensagem foi criada. Crie uma mensagem antes de atualizar.")

        with self.session_scope() as session:
            message = session.query(ChatMessage).filter_by(message_id=self.message_id).first()
            if message:
                if user_query  : message.user_query   = user_query
                if final_answer: message.final_answer = final_answer
                if screem_presentation  : message.screem_presentation  = screem_presentation
                if tool_result_for_chat : message.tool_result_for_chat = tool_result_for_chat
                    
    def delete_chat_history(self, chat_id):

        with self.session_scope() as session:
            latest_chat = session.query(ChatHistory)\
                .filter(ChatHistory.chat_id != chat_id)\
                .order_by(ChatHistory.created_at.desc())\
                .first()
            latest_chat_id = latest_chat.chat_id
                
        if latest_chat:
            self.chat_id = latest_chat_id
        else:
            self.create_new_chat(user=self.user, language=self.language)                
                
        with self.session_scope() as session:
            session.query(ChatAgencyFlow).filter(
                ChatAgencyFlow.message_id.in_(
                    session.query(ChatMessage.message_id).filter_by(chat_id=chat_id)
                )
            ).delete(synchronize_session=False)
            
            session.query(ChatMessage).filter_by(chat_id=chat_id).delete(synchronize_session=False)
            session.query(ChatHistory).filter_by(chat_id=chat_id).delete(synchronize_session=False)
            
            return self.chat_id
            
    def list_chat_titles_and_ids(self):
        """Retorna uma lista de dicionários com chat_title e chat_id, ordenada pelo mais recente."""
        with self.session_scope() as session:
            # Ordena os chats pela data de criação (campo 'created_at') de forma decrescente
            chats = session.query(ChatHistory.chat_id, ChatHistory.chat_title) \
                        .order_by(ChatHistory.created_at.desc()).all()
            return [{'chat_id': chat.chat_id, 'chat_title': chat.chat_title} for chat in chats]

    def update_chat_history(self, chat_id=None, chat_title=None, star_status=None):
        chat_id = chat_id or self.chat_id
        with self.session_scope() as session:
            chat = session.query(ChatHistory).filter_by(chat_id=chat_id).first()
            if chat:
                chat_title = chat_title or chat.chat_title
                if chat_title : chat.chat_title = chat_title

    def update_chat_history(self, chat_id=None, chat_title=None, agent_prompt=None, star_status=None):
        """Atualiza o título e/ou o status de estrela de um chat no SQLite."""
        chat_id = chat_id or self.chat_id
        with self.session_scope() as session:
            chat = session.query(ChatHistory).filter_by(chat_id=chat_id).first()
            if chat:
                if chat_title:
                    chat.chat_title = chat_title  # Atualiza o título do chat
                if star_status is not None:
                    chat.starry = star_status
                if agent_prompt is not None:
                    chat.agent_prompt = agent_prompt                    
                    
    def get_chat_history(self, chat_id=None):
        """Recupera uma entrada de ChatHistory pelo ID do chat."""
        
        chat_id = chat_id or self.chat_id
        
        with self.session_scope() as session:
            return session.query(ChatHistory).filter_by(chat_id=chat_id).first()

    def get_chat_messages(self, chat_id=None, limit=10, columns=None):
        """Recupera as mensagens do chat especificado com um limite e colunas opcionais."""
        
        chat_id = chat_id or self.chat_id
        
        with self.session_scope() as session:
            # Se nenhuma coluna for especificada, retorna todas as colunas
            if columns is None:
                query = session.query(ChatMessage).filter_by(chat_id=chat_id).filter(ChatMessage.user_query.isnot(None))
            else:
                selected_columns = [getattr(ChatMessage, col) for col in columns]
                query = session.query(*selected_columns).filter_by(chat_id=chat_id).filter(ChatMessage.user_query.isnot(None))
            
            messages = query.order_by(ChatMessage.order.asc()).limit(limit).all()
            
            # Extrai os dados enquanto a sessão ainda está aberta
            result = []
            for message in messages:
                message_dict = {}
                for col in (columns if columns else ChatMessage.__table__.columns.keys()):
                    value = getattr(message, col)
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    message_dict[col] = value
                result.append(message_dict)
            
            # Retorna os dados como uma lista de dicionários
            return result

    def get_agency_flow(self, message_id):
        """Recupera o fluxo de agência para uma mensagem específica."""
        with self.session_scope() as session:
            return session.query(ChatAgencyFlow).filter_by(message_id=message_id).all()
