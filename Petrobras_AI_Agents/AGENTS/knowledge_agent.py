from .base import BaseAgent, agent_response_par
from Petrobras_AI_Agents import BasellmClient, BaseKnowledgeBaseManager
from Petrobras_AI_Agents.READERS import read_file
from Petrobras_AI_Agents.AGENTS import prompts
import pandas as pd
import json
from typing import Union, Callable, List, Dict, Optional, Any
from termcolor import colored
import logging

logger = logging.getLogger(__name__)

class KnowledgeBaseAgent(BaseAgent):
    def __init__(
        self,
        KnowledgeBase: BaseKnowledgeBaseManager,
        llm: BasellmClient = None,
        collection_list: List[str]=None,
        agent_name: str = "KnowledgeBase Agent",
        next_agent_list: List[str] = None,
        allow_direct_response: bool = True,
        k: int = 5,
        human_in_the_loop: bool = False,
        short_term_memory: bool = False):
        
        self.__KnowledgeBase = KnowledgeBase
        self.collection_list = collection_list or self.__KnowledgeBase.available_collections
        self.topics  = {collection: dic['metadata']['description'] for collection, dic in self.__KnowledgeBase.config["data_sources"].items() if collection in self.collection_list}
        self.columns = {collection: dic['metadata']['columns']     for collection, dic in self.__KnowledgeBase.config["data_sources"].items() if collection in self.collection_list}
        self.tables  = {collection: {"file_base": dic['file_base'], "vec_base": dic['vec_base']} for collection, dic in self.__KnowledgeBase.config["data_sources"].items()}
                
        background = [
            f"You are highly knowledgeable about the company's internal documentation, covering the following topics: {json.dumps(self.topics, indent=2)}.",
            "Your role involves performing various tasks related to document retrieval, summarization, and data analysis based on user queries.",
            "You are capable of retrieving relevant chunks of text from documents to answer specific questions (RAG).",
            "You can summarize or develop a broad understanding of entire documents when needed, providing detailed explanations or overviews.",
            "You can search and list documents relevant to user queries, similar to a search engine.",
            "Additionally, you are able to perform data analysis tasks, such as counting, grouping, and listing information, and return this as either structured data or natural language."
            "For all those tasks, you have to use one of the available tools, if any",
            "Avoid delegating tasks that you can execute directly. Responses should always be based on the content of documents and data, without assumptions or fabricated information."
            ]

        goal = [''
            # "Your goal is to determine the most appropriate task to perform based on the user's query, and execute it accurately.",
            "For specific user questions, retrieve relevant document fragments to provide accurate and context-based answers.",
            "For broader questions, provide summaries or detailed explanations of entire documents.",
            "If the user is searching for documents, return a relevant list of documents based on the query.",
            "For questions focused on data analysis, provide accurate counts, groupings, or other structured data as needed.",
            "Ensure that your responses are fully based in the documents and data, avoiding assumptions or fabrications."
            ]

        super().__init__(llm=llm, agent_name=agent_name, background=background, goal=goal, next_agent_list=next_agent_list, allow_direct_response=allow_direct_response, human_in_the_loop=human_in_the_loop, short_term_memory=short_term_memory)
        self._specialist = True

        if not self.collection_list:
            self.active(is_active=False)
                    
        self.__k = k 

        self.tools = [
            self.rag_complement, 
            self.document_summary,
            self.document_search, 
            self.data_analysis
            ]
        
    def _get_collection_name(self, query_input):
        
        steps = {
            "step_1": "Análise das coleções disponíveis e descrições:",
            "step_2": "Seleção da coleção mais adequada para a consulta do usuário.",
            "step_3": "Retorno da coleção selecionada."}
        BaseAgent.screem_presentation[-1].append({'text': f"    Executando tool: _get_collection_name"})
        print(colored(f"thoughts: {steps}", 'cyan'))
        print(f"    Executando tool: _get_collection_name")
        
        if len(self.topics) == 1:
            collection_name = list(self.topics.keys())[0]
        else:
            system_prompt = [
                "Evaluate the best collection of documents to answer the user's query.",
                f"These are the available collections and their descriptions: {self.topics}",
                "**Only return the collection name, no additional text is needed.**",
                ]
            
            collection_name = self.llm.get_text(
                query_input,
                system_prompt = system_prompt,
                context       = self._user_feedback(),
                as_json       = False)

        BaseAgent.screem_presentation[-1].append({'text': f"    tool result: {collection_name}"})
        print(f"    tool result: {collection_name}\n")
        
        return collection_name

    def _generate_sql_filters(self, query_input, collection_name, add_system_prompt:list=[]):

        steps = {
            "step_1": "Seleção da documentação relacionada à coleção selecionada.",
            "step_2": "Geração de SQL para filtrar os documentos relevantes.",
            "step_3": "Teste dos filtros gerados.",
            "step_4": "Retorno dos filtros válidos."}
        BaseAgent.screem_presentation[-1].append({'text': f"    Executando tool: _generate_sql_with_filters"})
        print(colored(f"thoughts: {steps}", 'cyan'))
        print(f"    Executando tool: _generate_sql_with_filters")
                
        system_prompt = [
            "Your task is to generate SQL filters for the WHERE clause based on the provided context and user query.",
            "Use the context, including 'topics', 'tables', and 'columns', to form effective and realistic filter conditions.",
            "Adapt filter types based on the column's data type:",
            " - For text-based columns, generate both an '=' filter and a 'LIKE' filter to increase match possibilities.",
            " - For numerical or date-based columns, focus on range filters (e.g., '>', '<', '>=', '<=') where appropriate.",
            "Each filter condition should specify the table explicitly to avoid ambiguity. For example, use 'file_base.column_name' or 'vec_base.column_name' as needed.",
            "Consider common scenarios for filter application, such as value ranges, text matching, and logical combinations of filters.",
            "Use SQL text cleaning functions where applicable (e.g., trimming spaces, removing invalid characters).",
            "An example of a filter intention could be: 'WHERE file_base.raf = 'value' OR vec_base.tipo_doc LIKE 'intima%'.",
            "In your output, include multiple filter suggestions based on the user's query and available columns, but limit to columns provided in the context.",
            "Construct the base SQL query as well, using the format 'SELECT COUNT(*) AS count FROM (...)'.",
            " - Only include a JOIN if filters include columns from more than one table.",
            " - If filters are from a single table, reference only that table in the base query (e.g., 'SELECT COUNT(*) AS count FROM file_base').",
            "If columns from both 'file_base' and 'vec_base' are referenced, construct a JOIN between them (e.g., 'file_base JOIN vec_base ON file_base.id = vec_base.file_id').",
            "The output **must be a valid Python list** of strings, where each string represents a filter intention.",
            "Ensure the list can be parsed in Python and avoid additional text or explanations in your response.",
            "Alongside the list of filters, provide the base SQL query structure as a JSON object.",
            "Your output should follow this JSON format strictly:",
            """Example 1:
            {
                "query": "SELECT COUNT(*) AS count FROM table_name",
                "filters": ["file_base.column_name = 'value'", "vec_base.column_name LIKE 'value%'"]
            }
            Example 2:
            {
                "query": "SELECT COUNT(*) AS count FROM file_base_table_name AS file_base JOIN vec_base_table_name AS vec_base ON file_base.id = vec_base.file_id",
                "filters": ["vec_base.column_name = 'value'", "file_base.column_name LIKE 'value%'"]
            }
            """,
            "Your response should be formatted as JSON, with the 'query' and 'filters' keys as described, and include suggestions for both '=' and 'LIKE' for text columns where applicable.",
            prompts.prompt_json_format
        ]
        
        filter_context = {
            "filter_context":
                {"topics" : self.topics[collection_name],
                 "tables" : self.tables[collection_name],
                 "columns": self.columns[collection_name]}}
        
        # LLM gera a lista de filtros potenciais
        response = self.llm.get_text(
            query_input,
            system_prompt = [*system_prompt, *add_system_prompt],
            context       = {**self._user_feedback(), **filter_context},
            as_json       = True)

        BaseAgent.screem_presentation[-1].append({'text': f"    tool result: {response}"})
        print(f"    tool result: {response}\n")
        
        steps = {
            "step_1": "Análise da lista de filtros gerados.",
            "step_2": "teste do retorno de linhas para conjuntos de filtros.",
            "step_3": "Retorno dos filtros válidos."}
        print(colored(f"thoughts: {steps}", 'cyan'))
        print(f"    Executando tool: KnowledgeBase.test_filters")
        
        base_sql = response['query']
        filters  = response['filters']

        sql, rows_returned = self.__KnowledgeBase.test_filters(base_sql, filters)

        import re
        regex = re.search(r"WHERE (.*)", sql, re.IGNORECASE)
        if regex: where_clause = f"WHERE {regex.group(1)}"
        else: where_clause = ""
        
        print(f"    tool result: {rows_returned} rows returned using:\n    {where_clause}\n")
        
        return where_clause
    
    def _generate_embedding(self, query_input):

        steps = {
            'step_1': 'Gerar o vetor com os embeddings do modelo apropriado.',
            "step_2": "Retorno do vetor gerado."}
        print(colored(f"thoughts: {steps}", 'cyan'))
        BaseAgent.screem_presentation[-1].append({'text': f"    Executando tool: llm.get_embeddings"})
        print(f"    Executando tool: llm.get_embeddings")
        
        embedding = self.llm.get_embeddings(query_input)    
        BaseAgent.screem_presentation[-1].append({'text': f"    tool result: vector embedding generated"})
        print(f"    tool result: vector embedding generated\n")
        
        return     embedding
    
    def _similatity_search(self, collection_name, embedding, filters, k=None):
        
        steps = {
            'step_1': 'Análise dos dados disponíveis ou abordagem de resolução de problemas.',
            'step_2': 'Geração de filtros pelos metadados das tabelas disponíveis.'}
        print(colored(f"thoughts: {steps}", 'cyan'))
        BaseAgent.screem_presentation[-1].append({'text': f"    Executando tool: KnowledgeBase.similarity_search"})
        print(f"    Executando tool: KnowledgeBase.similarity_search")
        
        if not k: k = self.__k
        
        retrivered_rows = self.__KnowledgeBase.similarity_search(
            collection_name = collection_name,
            embedding       = embedding,
            k               = k,
            filters         = filters)
        
        BaseAgent.screem_presentation[-1].append({'text': f"    tool result: vector embedding returned"})
        print(f"    tool result: vector embedding returned\n")
        
        return retrivered_rows
    
    def _aggregate_documents(self, query_input, docs:List[dict], as_list:bool=True):
        KnowledgeBase_docs = {}
        list_docs = docs
        for dict_item in list_docs:
            dict_item[self.__KnowledgeBase.config["columns"]["context_col"]] = [dict_item[self.__KnowledgeBase.config["columns"]["context_col"]]]
            source = dict_item[self.__KnowledgeBase.config["columns"]["source_col"]]
            if source not in KnowledgeBase_docs:
                KnowledgeBase_docs[source] = dict_item
            else:
                KnowledgeBase_docs[source][self.__KnowledgeBase.config["columns"]["context_col"]] += dict_item[self.__KnowledgeBase.config["columns"]["context_col"]]
        
        if as_list: KnowledgeBase_docs = [v for k, v in KnowledgeBase_docs.items()]
        
        return KnowledgeBase_docs
        
    def _select_relevant_documents(self, query_input, KnowledgeBase_docs:dict):

        steps = {
            "step_1": "Entendimento da solicitação do usuário.",
            "step_2": "Avaliação dos documentos em contexto.",
            "step_3": "Retorno dos documentos relevantes."}
        print(colored(f"thoughts: {steps}", 'cyan'))
        BaseAgent.screem_presentation[-1].append({'text': f"    Executando tool: _select_relevant_documents"})
        print(f"    Executando tool: _select_relevant_documents")
        
        response_format = {
                'relevant_documents': [
                    'document_name_1',
                    'document_name_2',]}
        
        system_prompt = [
            "Your task is to evaluate all the context to identify which documents are relevant to the user's query.",
            "If a documment is not relevant,it means that the information it contains is not going to help the user answer their question.",
            "You must return a list with the documents' name.",
            "Return your answer as a JSON object with the following structure:",
            response_format,
            "The context is passed as a JSON object with the following structure:",
            """{
                'document_1_name': a string or list of strings with the document content to be evaluated,
                'document_2_name': ...}""",
                
            prompts.prompt_json_format
            ]

        response = self.llm.get_text(
            query_input,
            system_prompt = system_prompt,
            context       = KnowledgeBase_docs,
            as_json       = True)

        
        print(f"    tool result: {response}\n")

        retrivered_rows_used = [v for k, v in KnowledgeBase_docs.items()
                                     if k in response['relevant_documents']]
        
        BaseAgent.screem_presentation[-1].append({'text': f"    tool result: {len(retrivered_rows_used)} ducuments used"})
        
        return retrivered_rows_used
    
    def rag_complement(self, query_input):
        '''
            input:
                query_input: exact the same input in the user's prompt.
            description:
                Perform RAG (Retrieval-Augmented Generation) on chunks of text to complement the user's question
            details:
                - Use this task when the user is asking a specific question that can be answered by retrieving fragments of text from documents.
                - Focus on retrieving relevant pieces of text that directly answer the user's question, without the need to provide an overview or a summary of the entire document.
                - For example, if the user asks 'What is the company's vacation policy?', retrieve the exact sections of the document that discuss the vacation policy.
        '''
        
        collection_name    = self._get_collection_name(query_input)
        where_clause       = self._generate_sql_filters(query_input, collection_name)
        embedding          = self._generate_embedding(query_input)
        retrivered_rows    = self._similatity_search(collection_name, embedding, k=self.__k, filters=where_clause)
        KnowledgeBase_docs = self._aggregate_documents(query_input, retrivered_rows, as_list=False)
        documents          = self._select_relevant_documents(query_input, KnowledgeBase_docs)
        
        # self.full_result = KnowledgeBase_docs
        self._tool_input = where_clause

        BaseAgent.tool_result_for_chat[-1].append(
            {self.agent_name: [
                {f"{doc['source']}_{i+1}.txt": read_file.string_to_file(d, as_string=True)} 
                for doc in documents for i, d in enumerate(doc['page_content'])]
             })
        # print('BaseAgent.tool_result_for_chat', BaseAgent.tool_result_for_chat[-1][-1])
        return documents
    
    def _retrieve_full_documents(self, collection_name, filters, k=5, words_per_chunk=2500, overlap=25):
        
        steps = {
            "step_1": "Lista documentos.",
            "step_2": "converte documento para texto.",
            "step_3": "Retorna dicionário de documentos com uma lista representando o conteúdo separado por em pedaços"}
        print(colored(f"thoughts: {steps}", 'cyan'))
        BaseAgent.screem_presentation[-1].append({'text': f"    Executando tool: KnowledgeBase.retrieve_full_documents"})
        print(f"    Executando tool: KnowledgeBase.retrieve_full_documents")
        
        documents = self.__KnowledgeBase.retrieve_full_documents(collection_name, filters, k=3, words_per_chunk=2500, overlap=25)

        return documents
    
    def _get_text_summary(self, query_input, text:Union[str, list]):
        
        steps = {
            "step_1": "resumo de parte do documento."}
        print(colored(f"thoughts: {steps}", 'cyan'))
        BaseAgent.screem_presentation[-1].append({'text': f"    Executando tool: _get_text_summary"})
        print(f"    Executando tool: _get_text_summary")
        
        system_prompt = [
            "Summarize the provided document chunk based on the user's query.",
            "Focus on the main points and avoid redundancy."
        ]
        
        if not isinstance(text, list):
            text = [text]
        
        summaries = []
        for i, chunk in enumerate(text): # Make it async
            print(f"Working on {i+1} of {len(text)} texts")
            BaseAgent.screem_presentation[-1].append({'text': f"Working on {i+1} of {len(text)} texts"})
            summary = self.llm.get_text(
                    query_input,
                    system_prompt=system_prompt,
                    context={"document_chunk": chunk},
                    as_json=False
                )
            summary_aj = f"Part {i+1}:\n\n" + summary
            summaries.append(summary_aj)
        
        summaries_str = "\n_____________________________\n".join(summaries)
        BaseAgent.screem_presentation[-1].append({'text': f"    tool result: documents split into {len(summaries)} summaries"})
        print(f"    tool result: documents split into {len(summaries)} summaries")
            
        return [summaries_str]
    
    def _validate_summary_size(self, query_input, documents):
        pass
        
    def document_summary(self, query_input):
        '''
            input:
                query_input: exact the same input in the user's prompt.
            description:
                Summarize or develop an understanding of entire documents or large sections
            details:
                - Use this task when the user is requesting a broad or complete understanding of one or more documents.
                - The LLM should provide a summary, analysis, or a detailed explanation based on the full content of the document, such as instructions from a manual or the content of an article.
                - For example, if the user asks 'How does the procedure described in the manual work?', the LLM should provide a detailed summary or understanding of the document.
                - Divides large documents into smaller chunks, summarizes each chunk, and then combines the summaries.
        '''        
        
        collection_name    = self._get_collection_name(query_input)
        add_system_prompt  = ["**YOU MUST FOLLOW THIS INSTRUCTION FOR THIS ROUND: Do not use vec_base**"]
        where_clause       = self._generate_sql_filters(query_input, collection_name, add_system_prompt)
        documents:Dict     = self._retrieve_full_documents(collection_name, filters=where_clause, k=3, words_per_chunk=2500, overlap=25)

        summaries = {}
        for source, content_list in documents.items():
            BaseAgent.screem_presentation[-1].append({'text': f"    Summarizing document: {source}"})
            print(f"    Summarizing document: {source}")
            
            text_summary_return = self._get_text_summary(query_input, text=content_list)
            summaries[source] = text_summary_return

        self._tool_input = where_clause
        
        BaseAgent.tool_result_for_chat[-1].append(
            {self.agent_name: [
                {f"{source}.txt": read_file.string_to_file(s, as_string=True)}
                for source, summary in summaries.items() for i, s in enumerate(summary)]
             })
        # print('BaseAgent.tool_result_for_chat', BaseAgent.tool_result_for_chat[-1][-1])
        return summaries

    def _get_intention(self, query_input):
        
        steps = {
            "step_1": "Avaliar a solicitação do usuário.",
            "step_2": "Separar a solicitação do usuário em intenção de busca e quantidade a retornar",
            "step_3": "Estabelecer a intenção e a quantidade de resultados a retornar."}
        print(colored(f"thoughts: {steps}", 'cyan'))
        BaseAgent.screem_presentation[-1].append({'text': f"    Executando tool: _get_intention"})
        print(f"    Executando tool: _get_intention")
        
        response_format = {
            'quantity': "number of documents to be retrieved. if the user does not specify, use 25, as an integer",
            'question':" the question that is to intend to search into the vector database, as a string"}
        
        system_prompt = [
            "Identify the intentions of the user's question and segragate into 2 parts to guive your answer as the following json format:",
            response_format,
            prompts.prompt_json_format
            ]

        response = self.llm.get_text(
            query_input,
            system_prompt = system_prompt,
            as_json       = True)
        
        BaseAgent.screem_presentation[-1].append({'text': f"    tool result: {response}"})
        print(f"    tool result: {response}\n")
        
        quantity = response["quantity"]
        question = response["question"]
        
        return quantity, question
    
    def document_search(self, query_input):
        '''
            input:
                query_input: exact the same input in the user's prompt.
            description:
                Search for available documents in the user's context, similar to a search engine query.
            details:
                - Use this task when the user is looking to find specific documents related to their query, but they are not asking for an answer directly.
                - The LLM should return a list of documents or parts of documents that are relevant to the user's question, similar to how a search engine would return results.
                - For example, if the user asks 'What documents discuss internal auditing?', the LLM should list relevant documents that mention internal auditing.
        '''             

        quantity, question = self._get_intention(query_input)
        collection_name    = self._get_collection_name(question)
        where_clause       = self._generate_sql_filters(question, collection_name)
        embedding          = self._generate_embedding(question)
        retrivered_rows    = self._similatity_search(collection_name, embedding, k=quantity, filters=where_clause)
        KnowledgeBase_docs = self._aggregate_documents(query_input, retrivered_rows)
        
        self.full_result = KnowledgeBase_docs
        self._tool_input = where_clause
        return len(KnowledgeBase_docs)

    def _generates_sql(self, query_input): # uses llm to generate sql query
        
        steps = {
            "step_1": "Compreender a tarefa.",
            "step_2": "Identificar as tabelas relevantes.",
            "step_3": "Identificar as colunas apropriadas.",
            "step_4": "Construir a query SQL."}
        print(colored(f"thoughts: {steps}", 'cyan'))
        BaseAgent.screem_presentation[-1].append({'text': f"    Executando tool: _generates_sql"})
        print(f"    Executando tool: _generates_sql")
        
        system_prompt = [
            "Your task is to generate a SQL query to answer the user's question based on the provided context.",
            "The context includes the following keys: 'topics', 'tables', and 'columns'.",
            "First, identify which collections (tables) are relevant, then select the appropriate tables (file_base and vec_base), and finally use the relevant columns to construct the query.",
            "Also, review previous failed SQL attempts provided in the context to avoid repeating errors.",
            "The SQL query must be written in standard SQL format, not in SQLAlchemy or Python code.",
            "Do not include unnecessary formatting or comments in your response.",
            "Each collection consists of two tables: one for metadata (file_base) and one for text chunks and vectors (vec_base). These two tables are linked by 'file_id' in vec_base and 'id' in file_base.",
            "**Important:** The response should be a plain SQL query like the example below:",
            "'SELECT file_base.tipo_doc, COUNT(*) as quantidade_documentos FROM file_base JOIN vec_base ON file_base.id = vec_base.file_id WHERE file_base.raf = 'value' GROUP BY file_base.tipo_doc'."
            ]
        
        context = {"topics": self.topics,
                   "tables": self.tables ,
                   "columns": self.columns,
                   "previous_answer": self._sql_answers}
        
        sql = self.llm.get_text(query_input, 
                                system_prompt=system_prompt, 
                                context=context, 
                                as_json=False) # A method from 

        self._sql_answers.append(sql)
        BaseAgent.screem_presentation[-1].append({'text': f"    tool result: {sql}"})
        print(f"    tool result: {sql}\n")

        return sql
    
    def data_analysis(self, query_input):
        '''
            input:
                query_input: exact the same input in the user's prompt.
            description:
                Focus on database analysis, rather than document text.
            details:
                - Use this task when the user's question is more related to data analysis, such as counts, groupings, or listings, and not focused on document content.
                - Even if the user formulates the question in natural language, the expected return is more likely to be a table or aggregation of data.
                - For example, if the user asks 'How many documents were filed this month?', the LLM should return a table or count, not text from documents.
        '''                        
        self._sql_answers = []
                       
        count = 0
        while True:
            try:
                sql = self._generates_sql(query_input)
                result_table = self.__KnowledgeBase.get_table_as_dictionary(sql)
                break
            except Exception as e:
                print(e)
                count += 1
                
            if count == 5:
                result_table = {}
                break
        
        self.full_result = result_table
        result_table = result_table[:20]
        result = {"result_table": result_table, "sql": sql}

        self._tool_input = sql

        return result