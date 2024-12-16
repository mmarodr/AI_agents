from .base import BaseAgent, agent_response_par
from Petrobras_AI_Agents import BasellmClient
from Petrobras_AI_Agents.ANALYSIS import BaseDatabaseManager
from Petrobras_AI_Agents.READERS import read_file
from Petrobras_AI_Agents.AGENTS import prompts
import pandas as pd
import json
from typing import Union, Callable, List, Dict, Optional, Any
from termcolor import colored
import logging

class DatabaseExpertAgent(BaseAgent):
    def __init__(
        self,
        database_manager: BaseDatabaseManager,
        collection_list: List[str]=None,
        llm: BasellmClient = None,
        agent_name: str = "DatabaseExpert Agent",
        next_agent_list: List[str] = None,
        allow_direct_response: bool = True,
        human_in_the_loop: bool = False,
        short_term_memory: bool = False):

        self.__database_manager = database_manager
        self.collection_list = collection_list or self.__database_manager.available_collections
        self.topics        = {collection: dic['process_description'] for collection, dic in self.__database_manager.data_sources.items() if collection in self.collection_list}
        self.relationships = {collection: dic['relationships']       for collection, dic in self.__database_manager.data_sources.items() if collection in self.collection_list}        
        self.tables        = {collection: dic['tables']              for collection, dic in self.__database_manager.data_sources.items() if collection in self.collection_list}

        background = [
            "You are an expert in structured database querying, capable of analyzing complex database schemas.",
            f"You have access to the following database structures: {json.dumps(self.topics, indent=2)}.",
            "Your primary task is to analyze the resulting table based on the user's request, focusing on insights, trends, or summaries derived from the queried data.",
            "The SQL generation is an intermediate step solely to retrieve the necessary data for analysis.",
            "You should also handle real-time data queries, leveraging relational mappings, views, and indexes for performance optimization.",
            "You can manage complex JOIN operations, subqueries, window functions, and nested queries as needed to support data retrieval.",
        ]

        goal = [
            "To must answer or delegate only after you run a tool.",
            "After run a tool, with the relevant context given, anwser the task using this context",
            "Always refer to the documentation to confirm that fields and values used in the query align with documented standards and definitions.",            
            "Analyze the resulting table and give a summary based on the query results.",
            "Return a plesant and well formated response.",
            "If the user explicitly requests only the SQL query, return just the query without additional analyses."
        ]


        super().__init__(llm=llm, agent_name=agent_name, background=background, goal=goal, next_agent_list=next_agent_list, allow_direct_response=allow_direct_response, human_in_the_loop=human_in_the_loop, short_term_memory=short_term_memory)
        self._specialist = True
        
        if not self.collection_list:
            self.active(is_active=False)
            
        # self._tool_input = ""
        # self.full_result = None

        self.tools = [
            self.data_analysis
        ]

    def _get_collection_name(self, query_input):
        
        steps = {
            "step_1": "Análise das coleções disponíveis e descrições:",
            "step_2": "Seleção da coleção mais adequada para a consulta do usuário.",
            "step_3": "Retorno da coleção selecionada."}
        print(colored(f"thoughts: {steps}", 'cyan'))
        BaseAgent.screem_presentation[-1].append({'text': f"    Executando tool: _get_collection_name"})
        print(f"    Executando tool: _get_collection_name")
        
        if len(self.topics) == 1:
            collection_name = list(self.topics.keys())[0]
        else:
            system_prompt = [
                "Evaluate the best collection of documents to answer the user's query.",
                f"These are the available collections and their descriptions: {json.dumps(self.topics, indent=2)}",
                "Consider the user's query, the data types in each collection, and the relevance of the data to the query.",
                "Return only the collection name that best matches the user's intent, no additional text is needed."
                ]
            
            collection_name = self.llm.get_text(
                query_input,
                system_prompt = system_prompt,
                context       = self._user_feedback(),
                as_json       = False)

        BaseAgent.screem_presentation[-1].append({'text': f"    tool result: {collection_name}"})
        print(f"    tool result: {collection_name}\n")
        
        return collection_name
    
    def _generates_sql(self, query_input, collection_name):
        steps = {
            "step_1": "Analyze the user's request and determine the database structure required.",
            "step_2": "Identify the relevant tables and relationships.",
            "step_3": "Construct an optimized SQL query based on the input and database schema.",
            "step_4": "Execute the query and return the results."
        }
        print(f"thoughts: {steps}")
        BaseAgent.screem_presentation[-1].append({'text': f"    Executando tool: _generates_sql"})
        print(f"    Executando tool: _generates_sql")
                
        system_prompt = [
            "You are tasked with generating an optimized SQL query to retrieve data from a complex relational database.",
            "Use only the information provided in 'tables', 'relationships', and other context elements, without assuming any access to other tables or relationships not specified.",
            "Ensure the SQL query aligns with documented schema standards, table definitions, and constraints provided. Always verify field names, values, and data types against this information.",
            "Apply known indexes whenever possible for performance optimization.",
            "Return the SQL query only, formatted in standard SQL syntax with no additional text or comments.",
            "Follow the `user_comment` in the context meticulously, including any specifications on columns, filters, or exclusions, treating them as mandatory for the query generation. Do not overlook any element in the `user_comment`.",
            "Double-check for any specific exclusions or instructions to avoid certain conditions or columns in the SQL query. If a filter, condition, or column should not be included, exclude it strictly.",
            "Each SQL query must be optimized for performance, considering indexes and data distribution.",
            "No extraneous text is needed in your response – only the complete and correct SQL query as instructed."
        ]

        
        user_comment = self._rejected_responses[-1]['user_comment'] if self._rejected_responses else ""
        
        context = {
            "user_comment": user_comment,
            "topics": self.topics[collection_name],
            "relations": self.relationships[collection_name],
            "tables": self.tables[collection_name],
            "previous_answer": self._sql_answers
                   }
        
        sql = self.llm.get_text(query_input, 
                                system_prompt=system_prompt, 
                                context=context, 
                                as_json=False) # A method from 

        sql = sql.replace("```sql", "").replace("```", "").strip()
        # print(sql)
        self._sql_answers.append(sql)
        BaseAgent.screem_presentation[-1].append({'text': f"    tool result: {sql}"})
        print(f"    tool result: {sql}\n")

        return sql
    
    def _suggest_optimizations(self, sql):
        
        system_prompt = [
            "You are an expert in SQL optimization. Given the following SQL query, optimize it and provide suggestions to improve its performance.",
            prompts.prompt_json_format,
            "Consider the following when optimizing the query:",
            "- Review the use of indexes. Suggest checking if columns used in WHERE or JOIN clauses have appropriate indexes.",
            "- Recommend using EXPLAIN to check the query execution plan and identify bottlenecks.",
            "- Avoid directly recommending CREATE INDEX. Instead, suggest verifying the need for new indexes.",
            "- Simplify any unnecessary subqueries, and rewrite them if possible.",
            "- Rewrite JOINs to improve efficiency where necessary.",
            "- Avoid SELECT *; specify the required columns instead.",
            "- Review GROUP BY, HAVING, and ORDER BY to ensure optimal performance.",
            "- If the query is already optimized, return the original query and note 'No optimizations needed'.",
            "Return the optimized SQL and suggestions in JSON format with two keys: 'sql' and 'optimizations'."
        ]
        
        result = self.llm.get_text(sql, 
                                   system_prompt=system_prompt,
                                   as_json=True) # A method from 
        
        # self.__class__.screem_presentation.append(f"    tool result: {sql}")
        print(result)
        return result['sql'].replace("```sql", "").replace("```", "").strip(), result['suggestions']
    
    def data_analysis(self, query_input):
        """
        input:
            query_input: The exact question from the user, in natural language only.
        description:
            This function focuses on querying structured data and analyzing it based on the user's request.
            The SQL query is generated within this function, so the input should only contain the user's question.
        details:
            - The function identifies the most relevant data collection for the query based on the user's question.
            - It creates a valid SQL query internally to retrieve data from the database, accounting for relationships and constraints.
            - The final result is returned as a structured table, based on the user's input.
        """

        self._sql_answers = []
        max_attempts = 5
        max_result_rows = 30
        attempt = 0
        success = False
        sql = None
        suggestions = None

        collection_name = self._get_collection_name(query_input)
        # sql = self._generates_sql(query_input, collection_name)
        # result = self.__database_manager.get_table_as_dictionary(sql)
        # return result
        
        # Loop to attempt SQL generation and correction
        while attempt < max_attempts and not success:
            try:
                if attempt == 0:
                    # Generate initial SQL
                    sql = self._generates_sql(query_input, collection_name)
                # else:
                    # Suggest optimizations and retry
                    # sql, suggestions = self._suggest_optimizations(sql)

                    
                # Try executing the SQL
                result_json = self.__database_manager.get_table_as_dictionary(sql)
                self._tool_input = sql
                
                success = True  # If no error, set success to True
            except Exception as e:
                print(f"SQL execution failed on attempt {attempt + 1}: {e}")
                # Pass error context to LLM for correction
                query_input += f" SQL execution failed with error: {str(e)}"
                attempt += 1

        if success:
            
            BaseAgent.tool_result_for_chat[-1].append(
                {self.agent_name: [
                    {f"{collection_name}.csv": read_file.json_to_file(result_json, as_string=True)},
                    {f"{collection_name}_sql.txt"            : read_file.string_to_file(sql, as_string=True)}
                    ]
                })
                        
            # Format the result for the final response
            if len(result_json) > max_result_rows:
                self.full_result = result_json
                result = {
                    "table": result_json[:max_result_rows],
                    "Comments": f"The result has {len(result_json)} rows. Only the first {max_result_rows} rows are shown."}

            else:
                result = {
                    "table": result_json,
                    "Comments": f"The result has {len(result_json)} rows."}
        else:
            result = {"error": "SQL execution failed after multiple attempts."}

        return result
