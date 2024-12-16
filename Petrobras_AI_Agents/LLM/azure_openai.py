import requests
import json
import os
import time
import numpy as np
from typing import Optional, Union
from .base import BasellmClient
from io import StringIO
import tempfile

from dotenv import load_dotenv
load_dotenv()

import logging
logger = logging.getLogger(__name__)

gpt4_model      = "gpt-4o-petrobras"
embedding_model = "text-embedding-petrobras" # "text-embedding-3-large-petrobras"
api_version     = "2024-06-01" # "2024-08-01-preview"
gpt_azure_url   = "https://apid.petrobras.com.br/ia/openai/v1/openai-azure/openai"
cert_file       = "petrobras-ca-root.pem"

api_key = os.getenv('AZURE_OPENAI_API_KEY')

class llmClient_AzureOpenAI(BasellmClient):
    def __init__(self, model_text=gpt4_model, model_emb=embedding_model, api_version=api_version, base_url=gpt_azure_url, cert_file=cert_file, temperature=0):
        
        super().__init__(model_text=model_text, model_emb=model_emb)
        
        self.api_version        = api_version
        self.base_url           = base_url
        self.model_chat_endpoint= f'{self.base_url}/deployments/{self.model_text}/chat/completions?api-version={self.api_version}'
        self.model_emb_endpoint = f'{self.base_url}/deployments/{self.model_emb}/embeddings/?api-version={self.api_version}'
        self.certificate        = cert_file
        self.temperature        = temperature
        self.seed               = 0
        self.headers            = {'Content-Type': 'application/json', 'api-key': os.getenv('AZURE_OPENAI_API_KEY')}
        
        logger.info(self.model_chat_endpoint)
        
    def update_model_parameters(self, model_text=None, model_emb=None, api_version=None, temperature=None):
        if model_text is not None:   self.model_text = model_text
        if model_emb is not None:    self.model_emb = model_emb
        if api_version is not None:  self.api_version = api_version
        if temperature is not None:  self.temperature = temperature
    
    # @property
    # def _create_session(self):
    #     # Cria a sessão com requests
    #     session = requests.Session()

    #     # Se o certificado for fornecido como texto, cria um arquivo temporário
    #     if self.certificate:
    #         with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as temp_cert:
    #             temp_cert.write(self.certificate.encode())  # Escreve o certificado no arquivo
    #             temp_cert.flush()
    #             session.verify = temp_cert.name  # Usa o arquivo temporário como certificado
    #     else:
    #         session.verify = True  # Usa o padrão se não houver certificado

    #     return session
        
    def get_text(self, query_input, system_prompt="", context="", as_json=True):

        if not isinstance(query_input, str): query_input = json.dumps(query_input, indent=2, ensure_ascii=False)
        if not isinstance(system_prompt, str): system_prompt = json.dumps(system_prompt, indent=2, ensure_ascii=False)
        if not isinstance(context, str): context = json.dumps(context, indent=2, ensure_ascii=False)

        # print("query_input", query_input)

        def run():
            
            response_dict = session.post(self.model_chat_endpoint, headers=self.headers, data=json.dumps(payload))
            response_dict.raise_for_status()
            response_json = response_dict.json()
            logger.debug(f'response_json: {response_json}')
            # print(f'response_json: {response_json}')
            
            response_content = response_json['choices'][0]['message']['content']
            logger.debug(f'response_json 2: {response_content}')
            # print(f'response_json 2: {response_content}')
            
            try:
                if as_json: response_content = json.loads(response_content)
                # print(f'response_json 2: {response_content}')
                self.response_content = response_content
            except json.JSONDecodeError as e:
                print(f"Erro ao decodificar JSON: {e}")
                print("Conteúdo recebido:", response_content)
            return response_content
            
        session         = requests.Session()
        session.verify  = self.certificate 
        # session = self._create_session
        messages = [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "assistant",
                        "content": context,
                        "context": {
                            "intent": "" #"cat care"
                        }
                    }, 
                    {
                        "role": "user",
                        "content": query_input
                    }]
        logger.debug(f"message to llm: {messages}")
        
        payload = {
                    "messages": messages,
                    "stream": False,
                    "temperature": self.temperature,
                    # "seed": self.seed,
                }
        # print(payload)
        count = 1
        while count < 5:
            if count > 1: logger.debug(f'Retrying request {count}')
            try:
                return run()
            except requests.exceptions.RequestException as e:
                logger.debug(f"Request failed: {e}")
                # print(f"Request failed: {e}")
            except (KeyError, json.JSONDecodeError) as e:
                logger.debug(f"Error parsing response: {e}")
                # print(f"Error parsing response: {e}")
                
            count += 1
            
        return run()
    
    def get_embeddings(self, user_input, as_list=True) -> Optional[Union[list, np.ndarray]]:
        session = requests.Session()
        session.verify = self.certificate
        # session = self._create_session
        payload = {"input": user_input}
        
        while True:
            try:
                response = session.post(self.model_emb_endpoint, headers=self.headers, data=json.dumps(payload))
                response.raise_for_status()
                
            except requests.exceptions.HTTPError as http_err:
                if response.status_code == 429:
                    retry_after = int(response.json().get("retryAfter", 1))  # Pega o valor de retryAfter, padrão é 1 segundo
                    logger.warning(f'Rate limit exceeded. Retrying after {retry_after} seconds...')
                    time.sleep(retry_after + 5)
                    continue  # Tenta novamente após a pausa
                else:
                    logger.error(f'HTTP error occurred: {http_err}')
                    logger.error(f'Response content: {response.text}')
                    return None
            except Exception as err:
                logger.error(f'Other error occurred: {err}')
                return None

            response_json = response.json()
            embeddings = response_json["data"][0]["embedding"]

            if as_list: 
                return np.array(embeddings).tolist()  # Converte para lista, ainda usando float32
            else:       
                return np.array(embeddings)

    def embed_documents(self, text):
        pass

    def _handle_error(self, error):
        error = str(error)
        start_index = error.find("'retryAfter': ")
        len_key = len("'retryAfter': ")
        end_error = error[start_index+len_key:]
        finish_indez = end_error.find("}")
        retryAfter = int(end_error[:finish_indez].replace("'", ""))
        time.sleep(retryAfter)
        return retryAfter