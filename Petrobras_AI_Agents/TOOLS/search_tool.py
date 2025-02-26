from duckduckgo_search import DDGS
import json
import logging

logger = logging.getLogger(__name__)

def search_web(query, num_results) -> str:
    """
        Execute a web search using the DuckDuckGo search API via the duckduckgo-search Python library.

        :param inputs: The inputs to the function as a dictionary or uma string JSON.
            :param query: A string da consulta de busca.
            :param num_results: Número de resultados da busca a serem retornados.
        :return: Uma string JSON com os resultados da busca formatados como uma lista de dicionários, cada um contendo 'title', 'link' e 'snippet'.
    """
    try:
        # if isinstance(inputs, str):
        #     inputs = json.loads(inputs)

        # query = inputs.get('query', '')
        # num_results = inputs.get('num_results', 5)

        logger.info(f"Executando busca na web para a consulta: {query}")

        # Criando uma instância de DDGS
        with DDGS(verify=False) as ddgs:
            results = ddgs.text(query, max_results=num_results)

        if not results:
            logger.error("Nenhum resultado encontrado")
            return json.dumps({"error": "No results found"}, indent=2)

        search_results = []
        for result in results:
            search_results.append({
                'title': result.get('title'),
                'link': result.get('href'),
                'snippet': result.get('body')
            })

        logger.info(f"Busca concluída com sucesso com {len(search_results)} resultados.")
        return json.dumps(search_results, indent=2)

    except Exception as e:
        logger.error(f"Erro ao executar a busca na web: {e}")
        return json.dumps({"error": str(e)}, indent=2)


