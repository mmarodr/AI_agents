from termcolor import colored
from typing import Union, Callable, List, Dict, Optional, Any
import json
import logging
from Petrobras_AI_Agents import BasellmClient, BaseChatDatabaseManager
from . import prompts 

logger = logging.getLogger(__name__)

class agent_response_par():
    query_input     = "query_input"
    user_input      = "user_input"
    agent_input     = "agent_input"
    previous_agent  = "complement from previous agent" #"previous_agent"
    language        = "language"
    agent_name      = "agent_name"
    next_agent      = "next_agent"
    thoughts        = "thoughts"
    answer          = "answer"
    attachments     = "attachments"     
    tool_choice     = "tool"
    tool_input      = "input"
    tool_result     = "result"
    user_feedback   = "user_feedback"
    full_result     = "full_result"

class BaseAgent:
    
    language = "pt-br"
    llm: BasellmClient = None
    start_agent: 'BaseAgent' = None
    chat_mode: 'BaseAgent' = False
    chat_memory: BaseChatDatabaseManager = None    
    short_memory_size = 10
    agents = {}
    
    answers = [] # List of Dictionaries with only the question and the final answer
    local_memory  = []
    tool_response = [] # Deve ser desativado e priorizar a memória por banco de dados
    
    screem_presentation = []
    tool_result_for_chat = []
    agent_full_result = []
    
    human_in_the_loop_screem_presentation = [False]
    user_interaction = None
    user_Interaction_for_tool = True
    need_user_evaluation = None
    
    @classmethod
    def find_by_name(cls, name: str): 
        return cls.agents.get(name)

    @classmethod
    def reset_agents(cls):
        for agent_name in cls.agents.keys():
            agent = cls.agents[agent_name]['agent']
            agent.works = []
            agent._tool_result = None
            agent._rejected_responses = []
            
    @classmethod
    def new_chat(cls, user=None, language=None):
        cls.screem_presentation = []
        cls.tool_result_for_chat = []
        cls.agent_full_result = []
        cls.answers = []
        cls.local_memory = []
        cls.tool_response = []
        
        if cls.chat_memory:
            user = user or 'user'
            language = language or cls.language
            cls.chat_memory.create_new_chat(user=user, language=language)
    
    @classmethod
    def recover_chat(cls, chat_id):
        print('initiate chat recovery for id', chat_id)
        cls.chat_memory.chat_id = chat_id
        chat_history = cls.chat_memory.get_chat_messages(chat_id, limit=cls.short_memory_size)
        cls.screem_presentation = [json.loads(chat['chat_screem']) for chat in chat_history]
        cls.tool_result_for_chat = [json.loads(chat['tool_result']) for chat in chat_history]
        cls.answers = [
            {agent_response_par.query_input: json.loads(chat['user_query']),
            agent_response_par.answer: json.loads(chat['final_answer'])} 
            for chat in chat_history]
        cls.local_memory = cls.answers.copy()
        
    @classmethod
    def crew_work(cls, user_input: str, start_agent: 'BaseAgent'=None, chat_memory: BaseChatDatabaseManager=None, chat_mode=False):
        '''
        returns:
        {"system_prompt": {},
         "context"      : {},
         "response"     : {
             "agent_name" : "",
             "query_input": {},
             "answer"     : "",
             "next_agent" : "" or None},
         "attachments"   : {} or {
             "tool_choice" : "",
             "tool_input"  : "",
             "tool_result" : "" or [] or {},
             "tool_full_result": "" or [] or {}} or None} or None,
          "user_feedback": {}
         }
        '''
        def save_agent_work(work:dict):
            temp_local_memory.append(work["response"])
            if work["attachments"]:
                temp_tool_response_dict = {
                    agent_response_par.agent_name: agent.agent_name,
                    **work["attachments"]}
                temp_tool_response.append(temp_tool_response_dict)
                
                if work["attachments"].get("full_result", None):
                    temp_agent_full_result_dict = {
                        agent.agent_name:work["attachments"].get("full_result", None)}
                    temp_agent_full_result.append(temp_agent_full_result_dict)
                    
            if chat_memory:
                chat_memory.add_chat_agency_flow(
                    agent_name     = agent.agent_name,
                    agent_prompt   = work["system_prompt"],
                    agent_context  = work["context"],
                    agent_response = work["response"],
                    agent_tool     = work["attachments"])     # Adicionar campo para user_feedback
        
        chat_memory = chat_memory or cls.chat_memory
        cls.chat_memory = chat_memory
        chat_mode = chat_mode or cls.chat_mode

        if cls.user_interaction is None:
            cls.reset_agents()
            cls.answers.append(
                {agent_response_par.query_input: user_input,
                agent_response_par.answer: "Processando..."}
                )
            cls.screem_presentation.append([])
            cls.tool_result_for_chat.append([])
            
            temp_local_memory  = []
            temp_tool_response = []
            temp_agent_full_result = []
            
            agent = start_agent or cls.start_agent
            if isinstance(agent, str): agent = cls.agents.get(agent)["agent"]
            if chat_memory: chat_memory.create_initial_message()
            previous_agent_input = {agent_response_par.agent_name: None}
        else:
            temp_local_memory  = cls.local_memory[-1]   # traz a última entrada para variável local
            cls.local_memory   = cls.local_memory[:-1]  # remove a última entrada
            temp_tool_response = cls.tool_response[-1]  # traz a última entrada para variável local
            cls.tool_response  = cls.tool_response[:-1] # remove a última entrada
            temp_agent_full_result = cls.agent_full_result [-1]   # traz a última entrada para variável local
            cls.agent_full_result   = cls.agent_full_result[:-1]  # remove a última entrada
            
            agent = cls.agents.get(temp_local_memory[-1]['next_agent'])["agent"]
            previous_agent = cls.agents.get(temp_local_memory[-1]['agent_name'])["agent"]
            previous_agent_input = previous_agent._agent_input()
            
            if cls.user_interaction:
                agent._rejected_responses.append(
                    agent._rejected_response(
                        response=cls.need_user_evaluation,
                        user_comment=cls.user_interaction))
            cls.need_user_evaluation = None

        while True:
            work = agent.work(user_input, previous_agent_input)
            if 'need_user_input' in work: break
            next_agent = work["response"][agent_response_par.next_agent]
            save_agent_work(work) # Update temporary memory_state for this crew job memory and save data on chat memory db
            if next_agent is None: 
                if chat_mode:
                    work['response'][agent_response_par.answer] = cls.llm.get_text(
                        query_input   = work['response'][agent_response_par.answer],
                        as_json       = False,
                        context       = f"User input: {user_input}",
                        system_prompt = [
                            "Format the provided content as HTML for a chat interface, using a user-friendly, readable structure.",
                            "For code snippets, use this exact HTML format without additional spaces or newlines:",
                            "",
                            "<div class='code-container'>",
                            "    <button class='copy-btn' onclick='copyCode(this)'>Copiar código</button>",
                            "    <pre class='code-block'><code class='python'>",
                            "        # Your code goes here",
                            "    </code></pre>",
                            "</div>",
                            "",
                            "Align each line of code to the left within the <code> block, without extra indentation or empty lines.",
                            "Use only <p>, <ul>, <li>, and <strong> tags for explanations; avoid markdown.",
                            "Do not add or change any content. Apply only HTML formatting for readability.",
                            "All links should open in a new tab (target='_blank'), but do not add new links.",
                        ]

                        )
                # print(work['response'][agent_response_par.answer])
                break
            previous_agent_input = agent._agent_input()
            agent = cls.agents[next_agent]['agent']
        cls.local_memory.append(temp_local_memory)
        cls.local_memory = cls.local_memory[-cls.short_memory_size:] # keep local_memory with the short_memory_size defined
        cls.tool_response.append(temp_tool_response) # Deve ser desativado e priorizar a memória por banco de dados
        cls.tool_response = cls.tool_response[-cls.short_memory_size:]  # keep tool_response with the short_memory_size defined
        cls.agent_full_result.append(temp_agent_full_result) # Deve ser desativado e priorizar a memória por banco de dados
        cls.agent_full_result = cls.agent_full_result[-cls.short_memory_size:]  # keep tool_response with the short_memory_size defined        

        # Update crew history and save data on chat memory db
        if 'need_user_input' not in work:
            cls.answers[-1][agent_response_par.answer] = work['response'][agent_response_par.answer]
            if chat_memory:
                chat_memory.update_message(
                    user_query   = json.dumps(user_input, ensure_ascii=False),
                    final_answer = json.dumps(work['response'][agent_response_par.answer], ensure_ascii=False),
                    chat_screem  = json.dumps(cls.screem_presentation[-1], ensure_ascii=False),
                    tool_result  = json.dumps(cls.tool_result_for_chat[-1], ensure_ascii=False)
                    )
                    
        print('fim')
        
    def __init__(
        self,
        agent_name: str,
        background: Union[str, List[str]],
        goal: Union[str, List[str]],
        tools: List[Callable] = None,
        next_agent_list: List[str] = None,
        allow_direct_response: bool = True,
        llm: BasellmClient = None,
        human_in_the_loop: bool = False,
        short_term_memory: bool = False,
        ):

        # start variables
        self.agent_name             = agent_name
        self.background             = background
        self.goal                   = goal
        self.tools                  = tools or []  # Usa uma lista vazia se None
        self.next_agent_list        = next_agent_list or []
        self.allow_direct_response  = allow_direct_response
        self.llm                    = llm or self.__class__.llm
        self.human_in_the_loop      = human_in_the_loop
        self.short_term_memory      = short_term_memory
        
        # Create agent instance in the class
        self.__class__.agents[self.agent_name] = {'agent': self, 'active': True}

        # work result variables (should be reset after each crew_work)
        self.works = []
        self._tool_result = None
        self._rejected_responses = []
        
        self._specialist = False
        self._tool_input = ""
        self.full_result = None
        
    @property
    def next_agent_valid_list(self):
        if self.next_agent_list == "All":
            self.next_agent_list = [agent for agent in self.__class__.agents.keys() if agent != self.agent_name]
        return [
            agent_name 
            for agent_name, agent_object in self.__class__.agents.items() 
            if agent_object['active'] and agent_name in self.next_agent_list]

    @property
    def _tools_options(self):
        if self.tools: 
            return {
                func.__name__: func.__doc__ 
                for func in self.tools
                }  
        else: return None

    @property
    def tools_dict(self):
        if self.tools: 
            return {
                func.__name__: func 
                for func in self.tools
                }  
        else: return {}
            
    @property
    def _next_agent_options(self):
        if self.next_agent_valid_list:
            return {
                "next_agent_options": 
                    {
                        agent_name: {
                            "background": agent_object['agent'].background,
                            "goal": agent_object['agent'].goal
                            }
                            for agent_name, agent_object in BaseAgent.agents.items()  # Acesse diretamente as instâncias registradas
                            if agent_name in self.next_agent_valid_list and agent_object['active']
                            }
                    }
        return {}

    @property
    def _before_run_tool_text(self):
        if not self._before_run_tool and self._tool_input:
            return "You have already run a tool, now give your anwser based on the tool result."
        else:
            return None    

    @property
    def _allow_direct_response_text(self):
        if self.allow_direct_response:
            return "Direct response allowed: You may respond directly to the user without involving other agents."
        else:
            return "Direct response prohibited: Forward the task to another agent."    

    @property
    def _before_run_tool(self):
        
        if not self._tools_options: return False
        elif self._tool_result:     return False
        else:                       return True
                
    def active(self, is_active: bool):
        '''
        Switch the agent's activity status.
        Parameters:
        - is_active (bool): True to activate the agent, False to deactivate it.

        Returns:
        - None
        '''
        BaseAgent.agents[self.agent_name]['active'] = is_active

    def _system_prompt(self): # System Prompt to use in the LLM
        system_prompt = {}
        system_prompt.update(self._agent_description())
        # system_prompt.update(self._response_instruction())
        system_prompt.update(self._response_parameters())
        return system_prompt

    def _agent_description(self):
        return {
            "agent_description": 
                {
                    "agent_name": self.agent_name,
                    "background": self.background,
                    "goal"      : self.goal,
                }
            }
   
    def _response_parameters(self):
        response_parameters = {'instructions':[
            *prompts.prompt_json_format,
            "Your response must be a dictionary with the folowwing keys and use instructions:"
        ]}
        
        if self._before_run_tool:
            if self._tools_options:
                response_parameters['instructions'].append(f"'{agent_response_par.tool_choice}' and '{agent_response_par.tool_input}'" )
                response_parameters[agent_response_par.tool_choice] = prompts.llm_response_tool_choice
                response_parameters[agent_response_par.tool_input]  = prompts.llm_response_tool_input
                response_parameters["tools_options"] = self._tools_options
        else:
            response_parameters['instructions'].append(f"'{agent_response_par.answer}'" )
            response_parameters[agent_response_par.answer] = prompts.llm_response_answer
                        
            if self._next_agent_options:
                response_parameters['instructions'].append(f"and '{agent_response_par.next_agent}'" )
                response_parameters[agent_response_par.next_agent] = [
                    *prompts.llm_response_next_agent,
                    self._next_agent_options]
            
            response_parameters['instructions'].append(self._before_run_tool_text)

        return {"response_parameters": response_parameters}
            
    def _context(self): # Context to use in the LLM
        context = {}
        context.update(self._tool_response_statement())
        context.update(self._agent_last_response())
        context.update(self._previous_chat_iteration())
        context.update(self._user_feedback())
        return context
    
    def _tool_response_statement(self):
        if not self._before_run_tool and self._tool_result:
            return {"tool_result": {
                "explanaion":[
                    "That is the tool's response context resulted after you run a tool to respond your task"],
                "result" : self._tool_result[agent_response_par.tool_result]}}
        return {}
            
    def _agent_last_response(self):
        if self.works:
            responses = [{
                agent_response_par.query_input: response["response"][agent_response_par.query_input],
                agent_response_par.next_agent:  response["response"].get(agent_response_par.next_agent, None),
                agent_response_par.answer:      response["response"].get(agent_response_par.answer, None),
                agent_response_par.tool_choice: response["response"].get(agent_response_par.attachments, {}).get(agent_response_par.tool_choice, None),  # Valor padrão para o caso de não existir
                agent_response_par.tool_input:  response["response"].get(agent_response_par.attachments, {}).get(agent_response_par.tool_input, None)  # Valor padrão para o caso de não existir
                }
                for response in self.works[-self.short_memory_size:][::-1]]
            return {"agent_last_response": {
                "explanation": [
                    f"These are your last {self.short_memory_size} responses to similar tasks, listed from the most recent to the oldest.",
                    "Consider carefully: why is this task recurring despite previous attempts? Identify any repeating patterns or mistakes.",
                    "If previous approaches were ineffective, adjust your strategy. Think critically about different ways to achieve success.",
                    "Focus on each detail in your responses to minimize potential errors and improve accuracy."
                ],
                "last_responses": responses
                }}
        return {}
    
    def _previous_chat_iteration(self):
        if self.short_term_memory and self.__class__.answers:
            return {"previous_chat_iteration": {
                "explanation": [
                    "This is a recent chat history between the crew and the user.",
                    f"Below are the last {self.short_memory_size} user questions and crew responses, listed from the most recent to the oldest.",
                    "Use this information to gain context and insights to better complete your task."
                ],
                "crew_conversation": self.__class__.answers[-self.short_memory_size:][::-1]  # Exibe em ordem decrescente
            }}
        return {}
    
    def _user_feedback(self):
        if self._rejected_responses:
            return {agent_response_par.user_feedback: {
                "explanation": [
                    "Below are your recent responses to this task that were rejected, listed from the most recent to the oldest..",
                    "Review the feedback provided by the user to understand why these responses were not accepted before proceeding your answer."
                ],
                "rejected_responses": self._rejected_responses[::-1]  # Exibe em ordem decrescente
            }}
        return {}
    
    def _agent_input(self): # Agent Input to use in the LLM
        return {
           f"{self.agent_name} ": self.works[-1]["response"][agent_response_par.answer],
                # agent_response_par.agent_name : self.agent_name,
                # "agent_goal"                  : self.goal,
                # agent_response_par.thoughts   : self.works[-1]["response"][agent_response_par.thoughts],
                # agent_response_par.answer     : self.works[-1]["response"][agent_response_par.answer ],
                }
    
    def _rejected_response(self, response, user_comment):
        context = {
                    "agent_not_acpted_answer" : response,
                    "user_comment" : user_comment}
        return context
        
    # def _human_in_the_loop_response(self, response, human_in_the_loop=None):
        # if not human_in_the_loop: return False
        # print(colored("\nIf you do not accept this response enter a comment to reject it. If not, press Enter", 'yellow'))
        # while True:
        #     user_interaction = input().strip()
        #     print('user_interaction', user_interaction)
        #     if user_interaction == "": 
        #         print(colored(f"Accepted\n"))
        #         return False
        #     else:
        #         comment = user_interaction
        #         self._rejected_responses.append(
        #             self._rejected_response(
        #                 response = response,
        #                 user_comment = comment)
        #             )
        #         print(colored(f"I am going to review the answer after those considerations:\n{comment}\n"))
        #         return True 

    def _human_in_the_loop_response(self, response, human_in_the_loop=None):
        if not human_in_the_loop:
            return False
        if BaseAgent.user_interaction == "":
            BaseAgent.user_interaction = None
            return False  # Aceita a resposta
        else: 
            print(colored("\nIf you do not accept this response enter a comment to reject it. If not, press Enter", 'yellow'))
            BaseAgent.need_user_evaluation = response
            return True
                     
    def _execute_tool(self, tool_name, tool_input, query_input, human_in_the_loop):

        tool = self.tools_dict[tool_name]
        tool_result = tool(**tool_input)  
        
        self._tool_result = {
            agent_response_par.tool_choice: tool_name,
            agent_response_par.tool_input: tool_input,
            agent_response_par.tool_result: tool_result}
        
        tool_work:dict = self._message(
            user_input           = query_input[agent_response_par.user_input],
            previous_agent_input = query_input[agent_response_par.previous_agent],
            human_in_the_loop    = human_in_the_loop)

        tool_work["attachments"] = self._tool_result
        self._tool_result = None

        return tool_work

    def _message(self, user_input, previous_agent_input, human_in_the_loop):

        def validate_next_agent(response: dict):
            next_agent = response.get(agent_response_par.next_agent, None)
            # print("next_agent", next_agent)
            while next_agent not in self.next_agent_valid_list:
                if next_agent is None or next_agent == "None":
                    next_agent = None  # Finaliza o loop se next_agent for None
                    break
                else:
                    print("\nFail to find the next agent. Please select another agent.\n")
                    next_agent = self.llm.get_text(
                        query_input=response,
                        system_prompt=[
                            "The next agent you have chosen is unavailable. Please select another agent.",
                            prompts.llm_response_next_agent,
                            self._allow_direct_response_text,
                            self._next_agent_options],
                        as_json=False
                    )
            response[agent_response_par.next_agent] = next_agent
            return response

        human_in_the_loop = human_in_the_loop or self.human_in_the_loop

        query_input = {
            agent_response_par.user_input    : user_input,
            agent_response_par.previous_agent: previous_agent_input}

        system_prompt = self._system_prompt()
        context       = self._context()

        response:dict = self.llm.get_text(query_input   = query_input,
                                    system_prompt = system_prompt, 
                                    context       = context,
                                    as_json       = True)

        if agent_response_par.tool_choice in response:
            tool_name        = response.get(agent_response_par.tool_choice, None)
            tool_input       = response.get(agent_response_par.tool_input, None)
            
            if isinstance(tool_input, str):
                try:
                    print('tool_input informed as string')
                    tool_input = json.loads(tool_input)
                except:  pass
            
            BaseAgent.screem_presentation[-1].append({'text': f"    Executando tool: {tool_name}"})
            BaseAgent.screem_presentation[-1].append({'text': f"    tool: {tool_input}"})
            
            print(f"    Executando tool: {tool_name}")
            print(f"    {tool_input}\n")
            
            if BaseAgent.user_Interaction_for_tool:
                if self._human_in_the_loop_response(response, human_in_the_loop):
                    return {'need_user_input': True}
                
            BaseAgent.user_Interaction_for_tool = False
            return self._execute_tool(tool_name, tool_input, query_input, human_in_the_loop)

        else:
            BaseAgent.screem_presentation[-1].append({'text': f"answer: {response[agent_response_par.answer]}",
                                                  'bold': True})
            print(colored(F"\nanswer: {response[agent_response_par.answer]}\n", attrs=['bold']))
            response: dict = validate_next_agent(response)

            if self._human_in_the_loop_response(response, human_in_the_loop):
                return {'need_user_input': True}
                        
            work = {"system_prompt": system_prompt, # The last system_prompt used
                    "context"      : context, # The last context used
                    "response"     : {
                        agent_response_par.agent_name : self.agent_name,
                        agent_response_par.query_input: query_input,
                        **response},
                    "attachments"  : {},
                    "user_feedback": {}
                    }
            
            return work
        
    def work(self, user_input, previous_agent_input=None, human_in_the_loop=None):

        # self.__class__.screem_presentation['user_input'] = user_input: user_input
        BaseAgent.screem_presentation[-1].append({'text': f"Agent: {self.agent_name.upper()}",
                                                  'bold': True,
                                                  'color': 'green'})
        print(colored(f"{self.agent_name.upper()}\n", "green", attrs=['bold', 'underline']))
                    
        work:dict = self._message(user_input, previous_agent_input, human_in_the_loop)
        if 'need_user_input' in work:
            return work
            
        if self._rejected_responses:
            work["user_feedback"] = self._rejected_responses
            self._rejected_responses = []
        
        if self._specialist:
            if self._tool_input:
                work['attachments'][agent_response_par.tool_input] = self._tool_input
                self._tool_input = None
                
            if self.full_result:
                work['attachments'][agent_response_par.full_result] = self.full_result
                self.full_result = None         
        
        # BaseAgent.tool_result_for_chat[-1].append({agent})
        
        BaseAgent.user_Interaction_for_tool = True
        BaseAgent.need_user_evaluation = None
        BaseAgent.user_interaction = None
        self.__class__.human_in_the_loop_screem_presentation = [False]
        self.works.append(work)
        
        return work
