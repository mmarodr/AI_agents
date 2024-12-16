# from Petrobras_AI_Agents import BasellmClient, BaseChatDatabaseManager
# from .base import BaseAgent, agent_response_par
# from typing import Union, Callable, List, Dict, Optional, Any
# import logging

# logger = logging.getLogger(__name__)

# class MemoryAgent(BaseAgent):
    
#     def __init__(self, chat_memory:BaseChatDatabaseManager, llm:BasellmClient=None, chats_to_retrieve=3, agent_name:str="Chat Memory Agent", next_agent_list:List = None):
        
#         self.chat_memory = chat_memory
#         self.chats_to_retrieve = chats_to_retrieve
#         self.background = [
#             "You are an agent with access to the user's chat history.",
#             "Your role is to clarify vague questions by providing context from previous conversations.",
#             "You may either provide a direct response based on the chat history or give context for another agent to answer."
#             ]
#         self.goal = [
#             "Leverage the chat history to provide accurate and contextually relevant responses.",
#             "Explain previous responses based on the stored chat history.",
#             "Decide whether to answer the user's question directly or provide context for another agent to answer based on the clarity and context of the user's query."
#             ]
        
#         super().__init__(llm=llm, agent_name=agent_name, background=self.background, goal=self.goal, next_agent_list=next_agent_list)
        
#     def retriver(self):
        
#         memory       = self.chat_memory.get_memory()  # as a dictionary. A method to retrieve the memory from ChatHistoryManager
#         user_query   = memory["user_query"][-self.chats_to_retrieve :]
#         llm_response = memory['llm_response'][-self.chats_to_retrieve :]

#         chat_contexts = {f"chat {i + 1}": {"user_query": q, "llm_response": r}
#                          for i, (q, r) in enumerate(zip(user_query, llm_response))}
        
#         self.chat_contexts = chat_contexts
        
#         return chat_contexts

#     def prompt_update(self): # will be called by the base class after super().llm_chat()
        
#         super().prompt_update()

#         # Add new llm_response_format Parameter
#         self.llm_response_format['Parameters'][agent_response_par.attachments] = [
#             "Previous conversation context",
#             ]
                
#         self.context["context_to_limit_response"] = {
#             "Instruction": [
#                 "**You must provide your response based on this knowledge**",
#                 "Identify if your response is based on the chat history or you are guiving context for another agent to respond.",
#                 f"Those are the last {self.chats_to_retrieve} turns of the conversation. Use the chat history to inform your decisions and provide explanations."
#                 ],
#             "Parameters": self.inner_context
#             }

#     def llm_chat(self, query_input, verbose=False):
        
#         self.inner_context = self.retriver()

#         response = super().llm_chat(query_input, verbose=verbose) # A method from client_llm
        
#         return response
 
from .base import BaseAgent, agent_response_par
from Petrobras_AI_Agents.LLM import BasellmClient
from Petrobras_AI_Agents.MEMORY import BaseChatDatabaseManager
from termcolor import colored

class MemoryAgent(BaseAgent):
    
    def __init__(
        self,
        llm: BasellmClient = None,
        agent_name: str = "Memory Retrieval Agent",
        next_agent_list = None,
        human_in_the_loop: bool = False,
        allow_direct_response: bool = True,
        memory_manager: BaseChatDatabaseManager = None,  # Adicionar a classe de memória ao agente
        max_memory_recall: int = 25  # Quantidade máxima de mensagens a serem recuperadas
    ):
       
        background = [
            "You are responsible for retrieving and using past conversation memory.",
            "You have full access to the conversation history stored in the database.",
            "You should provide context and answers based on previous conversations.",
            "If you cannot resolve the user's query using past data, pass the task to another agent.",
            "Your priority is to enhance the user's experience by referencing past interactions."
        ]
        
        goal = [
            "Retrieve relevant messages from the chat memory to answer the user's query.",
            "Use the memory to provide contextually accurate responses.",
            "If the user's query cannot be answered from memory, identify the best agent to resolve the issue.",
            "Ensure the correct agent is involved for complex tasks that require tools or specialized knowledge."
        ]
        
        super().__init__(llm=llm, agent_name=agent_name, background=background, goal=goal, next_agent_list=next_agent_list, allow_direct_response=allow_direct_response, human_in_the_loop=human_in_the_loop)
        self._specialist = True
        
        self.memory_manager    = memory_manager or self.__class__.chat_memory  # Gerenciador de memória
        self.max_memory_recall = max_memory_recall  # Definir quantas mensagens recuperar
        
        # self.full_result = None

        self.tools = [
            self.retrieve_memory,
            ]
        
    def retrieve_memory(self):
        """
            input:
                None
            
            description:
                Retrieve chat memory to gather relevant past interactions.
            
            details:
                - This task retrieves past messages from the memory database, focusing on conversations that might provide context to the current interaction.
                - The function limits the number of messages returned based on the `max_memory_recall` parameter and returns selected columns from the message records.
                - Useful for creating a more contextualized interaction by referring to previous questions and answers from the user.
            
            steps:
                1. Retrieves the latest messages from the memory using the `memory_manager.get_chat_messages` method.
                2. Limits the number of messages retrieved using the `max_memory_recall` parameter.
                3. Optionally, analyze the retrieved messages using an LLM to determine which chats are directly related to the user's current query.
            
            usage example:
                - When a user asks a question, retrieve the most recent messages from the memory and refer back to previous questions and answers to enhance the context of the conversation.
                - For instance, if the user asked about "company policy" before, this function can retrieve those past discussions to provide a more informed response.
        """

        steps = {
            'step_1': 'Recuperando  mensagens da memória.'}
        print(colored(f"thoughts: {steps}", 'cyan'))
        print(f"    Executando tool: memory_manager.get_chat_messages")
                
        chat_id = self.memory_manager.chat_id
        chat_message = self.memory_manager.get_chat_messages(chat_id, limit=self.max_memory_recall, columns=["message_id", "order", "user_query", "final_answer"])
        
        # Aumentar a quantidade de ações para melhorrar o resultado, como por exemplo usar llm para avaliar os chats que estão relacionados e depois, com o id, recuperar atividades dos agentes?????
        
        
        self._tool_input = {"max_memory_recall": self.max_memory_recall}
        if not chat_message:
            chat_message = "Não existem mensagens anteriores."
        return chat_message

    # def work(self, user_input, previous_agent_input=None, human_in_the_loop=None):

    #     work = super().work(user_input, previous_agent_input, human_in_the_loop)

    #     if self._tool_input:
    #         work['attachments'][agent_response_par.tool_input] = self._tool_input
    #         self._tool_input = None
            
    #     if self.full_result:
    #         work['attachments'][agent_response_par.full_result] = self.full_result
    #         self.full_result = None
        
    #     return work
