from termcolor import colored
from typing import Union, Callable, List, Dict, Optional, Any
import json
import copy
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
    tool_files      = "files"
    user_feedback   = "user_feedback"
    full_result     = "full_result"

class AgentWork:
    
    def __init__(
        self, 
        language = "pt-br",
        llm: BasellmClient = None,
        chat_memory: BaseChatDatabaseManager = None,
        start_agent: 'BaseAgent' = None,
        chat_mode:bool = False,
        short_memory_size = 10,
        agents = {},
        agemt_prompts = {},
        local_memory = [],        
        human_in_the_loop_screem_presentation = [False],
        user_interaction = None,
        user_Interaction_for_tool = True,
        need_user_evaluation = None,
        ):

        self.language: str                        = language
        self.llm: BasellmClient                   = llm
        self.chat_memory: BaseChatDatabaseManager = chat_memory
        self.start_agent: 'BaseAgent'             = start_agent
        self.chat_mode: bool                      = chat_mode

        self.short_memory_size: int = short_memory_size
        self.agents: Dict           = agents
        self.agemt_prompts: str     = agemt_prompts
        
        self.from_crew: bool    = False
        self.local_memory: list = local_memory
        
        self.human_in_the_loop_screem_presentation = human_in_the_loop_screem_presentation
        self.user_interaction                      = user_interaction
        self.user_Interaction_for_tool             = user_Interaction_for_tool
        self.need_user_evaluation                  = need_user_evaluation
        
    def find_by_name(self, name: str): 
        return self.agents.get(name, None)

    def agent_by_name(self, name:str) -> 'BaseAgent':
        return self.agents.get(name, {}).get('agent', None)
    
    def agent_prompt_update(self, dictionary=None):
        
        json_dict_as_json = dictionary or copy.deepcopy(self.agemt_prompts)
        
        for agent_name, agent_data in json_dict_as_json.items(): 
            agent = self.agent_by_name(agent_name)
            if agent:
                print(f"BaseAgent: Agent '{agent_name}' updated.", flush=True)
                if agent_name not in self.agemt_prompts:
                    self.agemt_prompts[agent_name] = {}
                                    
                background = agent_data.get("background", None)
                if background:
                    self.agemt_prompts[agent_name]['background'] = background
                
                goal = agent_data.get("goal", None)
                if goal: 
                    self.agemt_prompts[agent_name]['goal'] = goal
                    
            else: print(f"BaseAgent: Agent '{agent_name}' not found.", flush=True)
    
    def recover_chat_agent_prompt(self):
        chat_data = self.chat_memory.get_chat_history()
        self.agent_prompt_update(chat_data['agent_prompt'])
    
    def reset_agents(self):
        for agent_name in self.agents.keys():
            agent:BaseAgent = self.agents[agent_name]['agent']
            agent.works = []
            agent._tool_result = None
            agent._rejected_responses = []
        
        self.local_memory = []
            
    def new_chat(self, user=None, language=None):
        if self.chat_memory:
            user = user or 'user'
            language = language or self.language
            self.chat_memory.create_new_chat(user=user, language=language)
            self.local_memory = []
        
    def set_local_memory(self, limit=20):
        chat_history = self.chat_memory.get_chat_messages(limit=limit, columns=['user_query', 'final_answer', 'screem_presentation', 'tool_result_for_chat'])
        self.local_memory = {}
        self.local_memory['answers'] = [{agent_response_par.query_input: json.loads(chat['user_query']),
                                         agent_response_par.answer:      json.loads(chat['final_answer'])}
                        for chat in chat_history]
        self.local_memory['screem_presentation']  = [json.loads(chat['screem_presentation']) for chat in chat_history]
        self.local_memory['tool_result_for_chat'] = [json.loads(chat['tool_result_for_chat']) for chat in chat_history]        
    
    def pair_data_to_chat(self, force_recovery=False, local_memory=None):
        if force_recovery or not self.local_memory:
            self.set_local_memory()
        
        local_memory = local_memory or self.local_memory
        pair_data = list(zip(local_memory['answers'], local_memory['screem_presentation'], local_memory['tool_result_for_chat']))

        return pair_data
        
    def crew_work(self, user_input: str, start_agent: 'BaseAgent'=None, chat_memory: BaseChatDatabaseManager=None, chat_mode=False):
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
             "files"       : [] or None,
             "tool_full_result": "" or [] or {}} or None} or None,
          "user_feedback": {}
         }
        '''
        
        def start_local_memory(user_input):
            self.set_local_memory()
            self.local_memory['answers'].append({agent_response_par.query_input: user_input,
                                                 agent_response_par.answer:      "Processando..."})
            self.local_memory['screem_presentation'].append([])
            self.local_memory['tool_result_for_chat'].append({})
            
        def save_agent_work(work:dict):                    
            if chat_memory:
                chat_memory.add_chat_agency_flow(
                    agent_name     = agent.agent_name,
                    agent_prompt   = work["system_prompt"],
                    agent_context  = work["context"],
                    agent_response = work["response"],
                    agent_tool     = work["attachments"])     # Adicionar campo para user_feedback
        
        def text_to_html(work:dict, user_input):
            work['response'][agent_response_par.answer] = self.llm.get_text(
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
                        ])
        
        print("BaseAgent: crew_work", flush=True)
        chat_memory = chat_memory or self.chat_memory        
        chat_mode = chat_mode or self.chat_mode
        
        self.from_crew = True
        
        if chat_memory: self.recover_chat_agent_prompt()
        
        if self.user_interaction is None:
            self.reset_agents() # Delete all previous status inside each agent
            
            agent = start_agent or self.start_agent
            if isinstance(agent, str): agent = self.agents.get(agent)["agent"]
            
            if chat_memory: chat_memory.create_initial_message()
            
            start_local_memory(user_input)                
            
            previous_agent_input = {agent_response_par.agent_name: None}
            
        else:
            # temp_local_memory  = self.local_memory[-1]   # traz a última entrada para variável local
            # self.local_memory   = self.local_memory[:-1]  # remove a última entrada
            # temp_tool_response = self.tool_response[-1]  # traz a última entrada para variável local
            # self.tool_response  = self.tool_response[:-1] # remove a última entrada
            # temp_agent_full_result = self.agent_full_result [-1]   # traz a última entrada para variável local
            # self.agent_full_result  = self.agent_full_result[:-1]  # remove a última entrada
            
            # agent = self.agents.get(temp_local_memory[-1]['next_agent'])["agent"]
            # previous_agent = self.agents.get(temp_local_memory[-1]['agent_name'])["agent"]
            # previous_agent_input = previous_agent._agent_input()
            
            if self.user_interaction:
                agent._rejected_responses.append(
                    agent._rejected_response(
                        response=self.need_user_evaluation,
                        user_comment=self.user_interaction))
            self.need_user_evaluation = None

        while True:
            work = agent.work(user_input, previous_agent_input, from_crew=True)
            
            if 'need_user_input' in work: break
            self.local_memory['tool_result_for_chat'][-1][agent.agent_name] = work["attachments"].get(agent_response_par.tool_files, "")
            next_agent = work["response"][agent_response_par.next_agent]
            save_agent_work(work)
            
            if next_agent is None: 
                if chat_mode: text_to_html(work, user_input)
                break
            else:
                previous_agent_input = agent._agent_input()
                agent = self.agents[next_agent]['agent']   
    
        self.local_memory['answers'][-1][agent_response_par.answer] = work['response'][agent_response_par.answer]
        if chat_memory:
            chat_memory.update_message(
                user_query          = json.dumps(user_input, ensure_ascii=False),
                final_answer        = json.dumps(work['response'][agent_response_par.answer], ensure_ascii=False),
                screem_presentation = json.dumps(self.local_memory['screem_presentation'][-1], ensure_ascii=False),
                tool_result_for_chat= json.dumps(self.local_memory['tool_result_for_chat'][-1], ensure_ascii=False)
                )
            chat_memory.update_chat_history(
                agent_prompt = self.agemt_prompts
            )
            
        if chat_mode:
            self.reset_agents()
            self.agemt_prompts = {}
   
class BaseAgent:

    def __init__(
        self,
        agent_name: str,
        work_instance: AgentWork,
        background: Union[str, List[str]],
        goal: Union[str, List[str]],
        tools: List[Callable] = None,
        next_agent_list: List[str] = None,
        allow_direct_response: bool = True,
        llm: BasellmClient = None,
        human_in_the_loop: bool = False,
        short_term_memory: bool = False
        ):

        # start variables
        self.agent_name             = agent_name
        self.work_instance          = work_instance
        self.background             = background
        self.goal                   = goal
        self.tools                  = tools or []  # Usa uma lista vazia se None
        self.next_agent_list        = next_agent_list or []
        self.allow_direct_response  = allow_direct_response
        self.llm                    = llm or self.work_instance.llm
        self.human_in_the_loop      = human_in_the_loop
        self.short_term_memory      = short_term_memory
        
        # Create agent instance in the class
        self.work_instance.agents[self.agent_name] = {'agent': self, 'active': True}

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
            self.next_agent_list = [agent for agent in self.work_instance.agents.keys() if (agent != self.agent_name or agent == self.work_instance.start_agent or agent == self.work_instance.start_agent.agent_name)]
        else:
            self.next_agent_list = [agent if isinstance(agent, str) else agent.agent_name for agent in self.next_agent_list]
        return [
            agent_name 
            for agent_name, agent_object in self.work_instance.agents.items() 
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
                            "collection": agent_object['agent'].collection_txt,
                            "background": agent_object['agent'].background,
                            "goal": agent_object['agent'].goal
                            }
                            for agent_name, agent_object in self.work_instance.agents.items()  # Acesse diretamente as instâncias registradas
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
            return "Direct response allowed: You may respond directly to the user without involving other agents. In that case, use agent=None"
        else:
            return "Direct response prohibited: Forward the task to another agent."    

    @property
    def _before_run_tool(self):
        
        if not self._tools_options: return False
        elif self._tool_result:     return False
        else:                       return True

    @property
    def collection_txt(self):
        return []
    
    def active(self, is_active: bool):
        '''
        Switch the agent's activity status.
        Parameters:
        - is_active (bool): True to activate the agent, False to deactivate it.

        Returns:
        - None
        '''
        self.work_instance.agents[self.agent_name]['active'] = is_active

    def _system_prompt(self): # System Prompt to use in the LLM
        system_prompt = {}
        system_prompt.update(self._agent_description())
        # system_prompt.update(self._response_instruction())
        system_prompt.update(self._response_parameters())
        return system_prompt

    def _agent_description(self):

        if self.agent_name in self.work_instance.agemt_prompts:
            background = self.work_instance.agemt_prompts[self.agent_name].get("background", self.background)
            goal       = self.work_instance.agemt_prompts[self.agent_name].get("goal",       self.goal)
        else:
            background = self.background
            goal       = self.goal

        return {
            "agent_description": 
                {
                    "agent_name"    : self.agent_name,
                    "collection"    : self.collection_txt,
                    "background"    : background,
                    "goal"          : goal,
                }
            }
    
    def _response_instruction(self):
        return {
            "response_instruction": self._allow_direct_response_text
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
                    self._allow_direct_response_text,
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
                for response in self.works[-self.work_instance.short_memory_size:][::-1]]
            return {"agent_last_response": {
                "explanation": [
                    f"These are your last {self.work_instance.short_memory_size} responses to similar tasks, listed from the most recent to the oldest.",
                    "Consider carefully: why is this task recurring despite previous attempts? Identify any repeating patterns or mistakes.",
                    "If previous approaches were ineffective, adjust your strategy. Think critically about different ways to achieve success.",
                    "Focus on each detail in your responses to minimize potential errors and improve accuracy."
                ],
                "last_responses": responses
                }}
        return {}
    
    def _previous_chat_iteration(self):
        if self.short_term_memory:
            answers = self.work_instance.local_memory['answers'][:-1]
            return {"previous_chat_iteration": {
                "explanation": [
                    "This is a recent chat history between the crew and the user.",
                    f"Below are the last {self.work_instance.short_memory_size} user questions and crew responses, listed from the most recent to the oldest.",
                    "Use this information to gain context and insights to better complete your task."
                ],
                "crew_conversation": answers[::-1]  # Exibe em ordem decrescente
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
        
    def _human_in_the_loop_response(self, response, human_in_the_loop=None):
        if not human_in_the_loop:
            return False
        if self.work_instance.user_interaction == "":
            self.work_instance.user_interaction = None
            return False  # Aceita a resposta
        else: 
            self.screem_presentation(text=f"If you do not accept this response enter a comment to reject it. If not, press Enter", color="yellow")
            self.work_instance.need_user_evaluation = response
            return True
                     
    def _execute_tool(self, tool_name, tool_input, query_input, human_in_the_loop, **kwargs):

        tool = self.tools_dict[tool_name]
        tool_result = tool(**tool_input)
        
        if isinstance(tool_result, tuple):
            tool_result, files = tool_result
        else:
            files = ""
        
        self._tool_result = {
            agent_response_par.tool_choice: tool_name,
            agent_response_par.tool_input : tool_input,
            agent_response_par.tool_result: tool_result,
            agent_response_par.tool_files : files}
        
        tool_work:dict = self._message(
            user_input           = query_input[agent_response_par.user_input],
            previous_agent_input = query_input[agent_response_par.previous_agent],
            human_in_the_loop    = human_in_the_loop)

        tool_work["attachments"] = self._tool_result
        self._tool_result = None

        return tool_work

    def _message(self, user_input, previous_agent_input=None, human_in_the_loop=False, **kwargs):

        def validate_next_agent(response: dict):
            next_agent = response.get(agent_response_par.next_agent, None)
            # print("next_agent", next_agent)
            while next_agent not in self.next_agent_valid_list:
                if next_agent is None or next_agent == "None":
                    next_agent = None  # Finaliza o loop se next_agent for None
                    break
                else:
                    print("BaseAgent: Fail to find the next agent. Please select another agent.\n")
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
                    print('BaseAgent: tool_input informed as string')
                    tool_input = json.loads(tool_input)
                except:  pass
            
            self.screem_presentation(text=f"Executando tool: {tool_name}", ident=True)
            self.screem_presentation(text=f"tool param: {tool_input}", ident=True)
            
            if self.work_instance.user_Interaction_for_tool:
                if self._human_in_the_loop_response(response, human_in_the_loop):
                    return {'need_user_input': True}
                
            self.work_instance.user_Interaction_for_tool = False
            return self._execute_tool(tool_name, tool_input, query_input, human_in_the_loop, **kwargs)

        else:
            response: dict = validate_next_agent(response)
            
            if self.work_instance.chat_mode and response.get(agent_response_par.next_agent, None) is None: 
                self.screem_presentation(text=f"answer: Processando resposta...", bold=True)
            else:
                self.screem_presentation(text=f"answer: {response[agent_response_par.answer]}", bold=True)

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
        
    def work(self, user_input, previous_agent_input=None, human_in_the_loop=None, **kwargs):

        self.screem_presentation(text=f"Agent: {self.agent_name.upper()}", bold=True, color='blue', underline=True)
                    
        work:dict = self._message(user_input, previous_agent_input, human_in_the_loop, **kwargs)
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
               
        self.work_instance.user_Interaction_for_tool = True
        self.work_instance.need_user_evaluation = None
        self.work_instance.user_interaction = None
        self.work_instance.human_in_the_loop_screem_presentation = [False]
        self.works.append(work)
        
        return work
    
    def screem_presentation(self, text, bold:bool=False, color:str=None, ident:bool=False, underline:bool=False):
        
        if ident: text = "    " + text
        
        message = {}
        message['text'] = text
        if bold: message['bold'] = bold
        if color: message['color'] = color

        if self.work_instance.from_crew: 

            self.work_instance.local_memory['screem_presentation'][-1].append(message)
        
            text = "BaseAgent: " + text
            
            if not self.work_instance.chat_mode:
                if   color and bold and underline:            print(colored(f"{text}\n", color, attrs=['bold', 'underline']), flush=True)
                elif color and bold and not underline :       print(colored(f"{text}\n", color, attrs=['bold']), flush=True)
                elif color and not bold and underline :       print(colored(f"{text}\n", color, attrs=['underline']), flush=True)
                elif not color and bold and underline :       print(colored(f"{text}\n", attrs=['bold', 'underline']), flush=True)
                elif not color and bold and not underline :   print(colored(f"{text}\n", attrs=['bold']), flush=True)
                elif not color and not bold and underline :   print(colored(f"{text}\n", attrs=['underline']), flush=True)
                else:                                         print(colored(f"{text}\n"), flush=True)

        else: print(f"{text}\n", flush=True)