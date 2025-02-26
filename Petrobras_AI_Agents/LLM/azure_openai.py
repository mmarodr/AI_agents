import requests
import json
import os
import time
import numpy as np
from typing import Optional, Union
from .base import BasellmClient
from io import StringIO
import tempfile
from decouple import config

import logging
logger = logging.getLogger(__name__)

class llmClient_AzureOpenAI(BasellmClient):
    def __init__(self, model_text, model_emb, api_version, base_url, cert_file, api_key=None, temperature=0):
        
        api_key = api_key or config("AZURE_OPENAI_API_KEY", None)
        super().__init__(model_text=model_text, model_emb=model_emb)
        
        self.api_version        = api_version
        self.base_url           = base_url
        self.model_chat_endpoint= f'{self.base_url}/deployments/{self.model_text}/chat/completions?api-version={self.api_version}'
        self.model_emb_endpoint = f'{self.base_url}/deployments/{self.model_emb}/embeddings/?api-version={self.api_version}'
        self.certificate        = cert_file
        self.temperature        = temperature
        self.seed               = 0
        self.headers            = {'Content-Type': 'application/json', 'api-key': api_key}
        
        # print(self.model_chat_endpoint, flush=True)
        
    def update_model_parameters(self, model_text=None, model_emb=None, api_version=None, temperature=None):
        if model_text is not None:   self.model_text = model_text
        if model_emb is not None:    self.model_emb = model_emb
        if api_version is not None:  self.api_version = api_version
        if temperature is not None:  self.temperature = temperature
           
    def get_text(self, query_input, system_prompt="", context="", as_json=True):

        if not isinstance(query_input, str): query_input = json.dumps(query_input, indent=2, ensure_ascii=False)
        if not isinstance(system_prompt, str): system_prompt = json.dumps(system_prompt, indent=2, ensure_ascii=False)
        if not isinstance(context, str): context = json.dumps(context, indent=2, ensure_ascii=False)

        # print("system_prompt", system_prompt)

        def run():
            
            response_dict = session.post(self.model_chat_endpoint, headers=self.headers, data=json.dumps(payload))
            response_dict.raise_for_status()
            response_json = response_dict.json()
            # print(f'llmClient_AzureOpenAI: response_json: {response_json}', flush=True)
            
            response_content = response_json['choices'][0]['message']['content']
            # print(f'llmClient_AzureOpenAI: response_json 2: {response_content}', flush=True)
            
            try:
                if as_json: 
                    response_content = json.loads(response_content)
                self.response_content = response_content
            except json.JSONDecodeError as e:
                print(f"llmClient_AzureOpenAI: Erro ao decodificar JSON: {e}", flush=True)
                print(f"llmClient_AzureOpenAI: Conteúdo recebido: {response_content}", flush=True)
            return response_content
            
        session         = requests.Session()
        session.verify  = self.certificate 

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
        # print(f"llmClient_AzureOpenAI: message to llm: {messages}", flush=True)
        
        payload = {
                    "messages": messages,
                    "stream": False,
                    "temperature": self.temperature,
                    # "seed": self.seed,
                }

        count = 1
        while count < 5:
            if count > 1: 
                print(f'llmClient_AzureOpenAI: Retrying request {count}', flush=True)
            try:
                return run()
            except requests.exceptions.RequestException as e:
                print(f"llmClient_AzureOpenAI: Request failed: {e}", flush=True)
            except (KeyError, json.JSONDecodeError) as e:
                print(f"llmClient_AzureOpenAI: Error parsing response: {e}", flush=True)

                
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
                    print(f'llmClient_AzureOpenAI: HTTP error occurred: {http_err}', flush=True)
                    print(f'llmClient_AzureOpenAI: Response content: {response.text}', flush=True)
                    return None
            except Exception as err:
                print(f'llmClient_AzureOpenAI: Other error occurred: {err}', flush=True)
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