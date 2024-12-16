from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine, Column, String, Integer, JSON, TIMESTAMP, func, event
import uuid
from datetime import datetime

Base = declarative_base()

def generate_default_title():
    """Gera um título padrão no formato 'chat_[DATA&HORA]'."""
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"chat_{current_time}"

class ChatHistory(Base):
    __tablename__ = 'chat_history'
    
    chat_id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_title      = Column(String, default=generate_default_title)  # Define um valor padrão dinâmico
    user            = Column(String, default='user')
    language        = Column(String)
    created_at      = Column(TIMESTAMP, default=func.now())
    updated_at      = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

class ChatMessage(Base):
    __tablename__ = 'chat_messages'  
    
    message_id      = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id         = Column(String)
    related_chat_id = Column(String)
    order           = Column(Integer)
    user_query      = Column(String)
    final_answer    = Column(String)
    chat_screem     = Column(JSON)
    tool_result     = Column(JSON)
    created_at      = Column(TIMESTAMP, default=func.now())
    updated_at      = Column(TIMESTAMP, default=func.now(), onupdate=func.now())    
    
class ChatAgencyFlow(Base):
    __tablename__ = 'chat_agency_flow'  
    
    agency_flow_id  = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id      = Column(String)
    order           = Column(Integer)
    agent_name      = Column(String)
    agent_prompt    = Column(JSON)
    agent_context   = Column(JSON)
    agent_response  = Column(JSON)
    agent_tool      = Column(JSON)
    created_at      = Column(TIMESTAMP, default=func.now())
    updated_at      = Column(TIMESTAMP, default=func.now(), onupdate=func.now())       

class BaseChatDatabaseManager:
    Base = Base
    def create_new_chat(self, user, language, chat_title=None):
        pass
    
    def update_message(self, user_query=None, final_answer=None, chat_screem=None, tool_result=None):
        pass
    
    def add_chat_agency_flow(self, agent_name, agent_prompt, agent_context, agent_response, agent_tool):
        pass
    
    def create_initial_message(self):
        pass
    
    def get_chat_messages(self, chat_id, limit=10, columns=None):
        pass
    
    def list_chat_titles_and_ids(self):
        pass
    
    def update_chat_history(self, chat_id=None, chat_title=None):
        pass
    
    def delete_chat_history(self, chat_id):
        pass