from .base import BaseAgent, AgentWork
from Petrobras_AI_Agents import BasellmClient
from Petrobras_AI_Agents import BaseChatDatabaseManager
from typing import Union, Callable, List, Dict, Optional, Any
from Petrobras_AI_Agents.TOOLS import run_python_code, search_web
import json
       
class ChatInterpretorAgent(BaseAgent):
    def __init__(
        self,
        work_instance: AgentWork,
        llm: BasellmClient = None,
        agent_name: str = "Chat Interpretor Agent",
        next_agent_list = "All",
        human_in_the_loop: bool = False):

        self.work_instance = work_instance
        background = [
            "Seu conhecimento está limitado a um período no tempo, quando você parou de ser treinado.",
            "Por esse motivo, perguntas que envolvam dados atuais nunca devem ser respondidas com base no seu conhecimento.",
            "Além disso, seu conhecimento não comtempla as informações internas, conhecida por outros agentes.",
            ]
        
        goal = [
            "Responda diretamente perguntas simples de saudações.",
            "De preferencia para respostas que se baseiem no conhecimento interno, que são dominio de outros agentes.",
            "Não sendo o caso, avalie se é necessário o uso de alguma ferramenta ou se deve passar logo a tarefa para outro agente.",
            "Quando usar uma ferramenta, não mencione que ela foi usada, apenas use a resposta para responder ao usuário."
            ]
        
        next_agent_list         = next_agent_list
        allow_direct_response   = True
        short_term_memory       = True
        
        tools = [
            self.direct_anwser,
            self.remake_user_question,
            self.by_code, 
            self.prompt_update,
            self.agent_info
            # self.web
        ]
        
        
        super().__init__(work_instance=self.work_instance, llm=llm, agent_name=agent_name, background=background,
                         goal=goal, tools=tools, next_agent_list=next_agent_list,human_in_the_loop=human_in_the_loop,
                         allow_direct_response=allow_direct_response, short_term_memory=short_term_memory)
        
    def direct_anwser(self, query_input):
        """
        input:
            query_input: The exact question from the user, in natural language only.
        description:
            If you cam respond directly or another agent may have a better answer.
        details:
            - 
        """
        return query_input
    
    def remake_user_question(self, query_input, motivation):
        """
        input:
            query_input: The exact question from the user, in natural language only.
            motivation: the reason why it must be remake.
        description:
            Essa função usa a llm para recriar a pergunta do usuario ajustando termos vagos.
            São usadas as conversas prévias para reformular a pergunta do usuário para que ela fique completa.
        details:
            - 
        """
        
        system_prompt = [
            "Reformule a pergunta do usuário para que ela contenha todo o contexto necessário.",
            "Ex: Caso a pergunta seja, 'Como faço isso', você deve procurar no contexto as ultimas interações e retornar algo como 'Como faço para criar uma função de python que crie um jogo de caça palavras'",
            "Ex2: Caso a pergunta seja, 'Detalhe melhor', você retorna 'Detalhe melhor: [a resposta da última interação]'"
        ]
        
        response = self.llm.get_text(
            query_input   = query_input,
            system_prompt = system_prompt,
            context       = {
                "motivation_to_remake": motivation,
                **self._previous_chat_iteration()},
            as_json       = False)
        
        return response
    
    def by_code(self, code, variable_to_return):
        '''
        Usado para tarefas que precisem de informações do computados, como hora atual, data, agenda, logs...
        :param inputs: The inputs to the function as a dictionary or a JSON string.
            :param code: The code to run.
            :param variable_to_return: The variable to return.
            :return: value of `variable_to_return` if successful, otherwise returns an error message.
        '''
        
        response = run_python_code(code, variable_to_return)
        
        return response
    
    def prompt_update(self, json_dict):
        """
        input:
            json_dict: The json dictionary passed by the user that can be parsed into json.loads().
        description:
            If user asks for an update on agent prompts, get the JSON dictionary to update agents' background and goals.
        details:
            - input only a dictionary that can be parsed into json.loads().
            - The spected dictionat to use has the following format:
                {'json_dict': {'agent name':{'bacjgraund': list os string with prompt, 'goal': list os string with prompt}}}
            - May are multiple agents and may are only background or goal.
            - If nessassary, ajust the user question to the expected format
                        
        """
                
        json_dict_as_json = json.loads(json_dict) if isinstance(json_dict, str) else json_dict       
        self.work_instance.agent_prompt_update(json_dict_as_json)
        
        return "Prompts atualizados com sucesso."

    def agent_info(self, agent_name, agent_info):
        '''
        input:
            agent_name: str as agent name on availavles agent list
            agent_info: list as the info availables possibilities.
        description:
            If user asks for agent info. Take the agent name provided and the info requared
        details:
            - The info availables are:
                - backgroung
                - goal
        '''
                
        agent = self.work_instance.agent_by_name(agent_name)
        if not agent:
            return {agent_name: "Agente não encontrado"}

        response = {agent_name: {}}
        for info in agent_info:
            response[agent_name][info] = getattr(agent, info, f"info não encontrado em {agent_name}")

                
        return response
    
    def web(self, query):
        '''
        Usado para tarefas que precisem de informações da internet
        :param inputs: The inputs to the function as a dictionary or uma string JSON.
            :param query: A string da consulta de busca.
        :return: Uma string JSON com os resultados da busca formatados como uma lista de dicionários, cada um contendo 'title', 'link' e 'snippet'.
        '''


        response = search_web(query, num_results=20)
        
        return response        
        
