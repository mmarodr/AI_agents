from .base import BaseAgent, AgentWork, agent_response_par
from Petrobras_AI_Agents.LLM import BasellmClient
from Petrobras_AI_Agents.MEMORY import BaseChatDatabaseManager
from termcolor import colored

class MemoryAgent(BaseAgent):
    
    def __init__(
        self,
        work_instance: AgentWork,
        llm: BasellmClient = None,
        agent_name: str = "Memory Retrieval Agent",
        next_agent_list = None,
        human_in_the_loop: bool = False,
        allow_direct_response: bool = True,
        memory_manager: BaseChatDatabaseManager = None,  # Adicionar a classe de memória ao agente
        max_memory_recall: int = 25  # Quantidade máxima de mensagens a serem recuperadas
    ):
       
        self.work_instance = work_instance
       
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
        
        super().__init__(work_instance=self.work_instance, llm=llm, agent_name=agent_name, background=background, goal=goal, next_agent_list=next_agent_list, allow_direct_response=allow_direct_response, human_in_the_loop=human_in_the_loop)
        self._specialist = True
        
        self.llm               = llm or self.work_instance.llm
        self.memory_manager    = memory_manager or self.work_instance.chat_memory  # Gerenciador de memória
        self.max_memory_recall = max_memory_recall  # Definir quantas mensagens recuperar
        
        # self.full_result = None

        self.tools = [
            self.retrieve_memory
            ]
        
    def retrieve_memory(self, limit=25):
        """
            input:
            limit: the number of interactions to return. If not informed, use 25.
            
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

        self.screem_presentation(text=f"     Executando tool: memory_manager.get_chat_messages")
                
        chat_id = self.memory_manager.chat_id
        chat_message = self.memory_manager.get_chat_messages(chat_id, limit=limit, columns=["message_id", "order", "user_query", "final_answer"])
        
        # Aumentar a quantidade de ações para melhorrar o resultado, como por exemplo usar llm para avaliar os chats que estão relacionados e depois, com o id, recuperar atividades dos agentes?????

        self._tool_input = {"max_memory_recall": limit}
        
        if not chat_message:
            chat_message = "Não existem mensagens anteriores."
            self.screem_presentation(text=f"    tool result: {chat_message}.")
        else:
            self.screem_presentation(text=f"    tool result: {len(chat_message)} messages retrived.")
        
        print(chat_message)
        return chat_message
