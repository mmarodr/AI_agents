# é uma cópia da classe usada no databricks

import fitz
import ebooklib
from ebooklib import epub
import pandas as pd
import json
from bs4 import BeautifulSoup

import warnings

import os
import json
import re
import io
import csv
import tempfile
import base64
from typing import Union

class read_file:

    @classmethod
    def string_to_file(cls, text:str, as_string=False):
        file_content = text.encode('utf-8')
        if as_string: return base64.b64encode(file_content).decode('utf-8')
        return file_content

    @classmethod
    def json_to_file(cls, json_list:list, as_string=False):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=json_list[0].keys())
        writer.writeheader()
        writer.writerows(json_list)

        # Obtemos o conteúdo do CSV em uma string
        csv_string = output.getvalue()
        file_content = csv_string.encode('utf-8')  # Converte a string CSV para bytes
        if as_string: return base64.b64encode(file_content).decode('utf-8')
        return io.BytesIO(file_content)
        
    def __init__(self, file_name, file_content:Union[str, bytes]):
        self.file_name = file_name
        self.file_content = self._aj_file_content(file_content)
        self.processed_rows = []
        self._load_full_file() # gera self.read_result

    def decode_file_content(self, file_as_str: str) -> bytes:
        return base64.b64decode(file_as_str)

    def _aj_file_content(self, file_content: Union[str, bytes]) -> Union[bytes, None]:
        if isinstance(file_content, str):
            return self.decode_file_content(file_content)
        elif isinstance(file_content, bytes):
            return file_content
        else: return None        

    def _remove_illegal_characters(self, texto):
        if not isinstance(texto, str):
            return texto
        regex = re.compile(r'[\000-\010]|[\013-\014]|[\016-\037]')
        text = re.sub(regex, '', texto)
        return text

    def _split_words(self, text):
        text = self._remove_illegal_characters(text)
        text = re.split(r'\s+', text.strip())  # Dividir usando espaços
        return text
                    
    def _read_pdf(self):
        print('read_pdf')

        file_fitz = fitz.open(stream=self.file_content, filetype="pdf")
        text = "".join([page.get_text() for page in file_fitz])
        words = self._split_words(text)
        # try:
        #     keywords = json.loads(file_fitz.metadata.get("keywords", "{}"))
        # except:
        #     keywords = {} # Implementar outras formas de adicionar metadados        

        keywords = {}
        self.read_result = [(words, keywords)]

    def _read_epub(self):
        print('read_epub')
        
        warnings.filterwarnings('ignore', category=FutureWarning)
        warnings.filterwarnings('ignore', category=UserWarning)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp_file:
            tmp_file.write(self.file_content)
            tmp_file_path = tmp_file.name

        try:
            book = epub.read_epub(tmp_file_path)
            self.read_result = []
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:

                    soup = BeautifulSoup(item.content, 'lxml')
                    paragraph = soup.find_all('p')
                    text = ' '.join(p.get_text(strip=True) for p in paragraph)
                    words = self._split_words(text)
                    keywords = {'title': item.get_name()}

                    self.read_result.append((words, keywords))
                    
        finally:
            os.remove(tmp_file_path) 

    def _extract_chunks(self, words, words_per_chunk=200, overlap=20):
        chunks = []
        words_count = len(words)
        
        if words_per_chunk is None or words_count <= words_per_chunk:
            chunks = [words]
        else:
            start = 0
            while start < words_count:
                end = start + words_per_chunk
                end = min(end, words_count)
                chunk = words[start:end]
                if len(chunk) == overlap: break
                chunks.append(chunk)
                start = end - overlap
        return chunks
    
    def _create_rows_to_process(self, file_name, chunks, keywords):

        for chunk in chunks:
            processed_chunk = {}
            text = " ".join(chunk)
            
            processed_chunk['source'] = file_name
            # for key, value in keywords.items():
            #     processed_chunk[key] = value
            
            processed_chunk['page_content'] = f'{json.dumps(keywords)} {text}'

            self.processed_rows.append(processed_chunk)

    def _load_full_file(self):
        # print(self.file_name)
        _, file_extension = os.path.splitext(self.file_name.lower())

        if   file_extension == '.pdf': self._read_pdf()
        elif file_extension == '.epub': self._read_epub()
        else: return None
        
    def load_file_in_chuncks(self, words_per_chunk=500, overlap=25):
        # print(self.file_name)
        # _, file_extension = os.path.splitext(self.file_name.lower())

        # if   file_extension == '.pdf': self._read_pdf()
        # elif file_extension == '.epub': self._read_epub()
        # else: return None
        # print('processing rows')
        for result in self.read_result:
            words    = result[0]
            keywords = result[1]
            chunks   = self._extract_chunks(words, words_per_chunk, overlap)
            self._create_rows_to_process(self.file_name, chunks, keywords)
        result = self.processed_rows
        return result

        
        