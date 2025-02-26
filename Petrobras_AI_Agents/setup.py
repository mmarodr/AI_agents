from setuptools import setup, find_packages

setup(
    name="Petrobras_AI_Agents",  # Nome do seu pacote
    version="0.1",  # Versão inicial
    packages=find_packages(),  # Inclui automaticamente todas as subpastas com __init__.py
    install_requires=[  # Lista de dependências do seu projeto, se houver
        # Exemplo: 'numpy', 'pandas', 'requests'
    ],
    author="Marcos de Mattos Amarante Rodrigues",
    description="Framework de Agentes de IA para utilizar na Petrobras",
    url="https://seu-repositorio.com",  # Se você tiver um repositório, como GitHub
)