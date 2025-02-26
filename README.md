# Agentes de IA - Desenvolvimento Próprio

#### Aluno: [Marcos de Mattos Amarante Rodrigues](https://github.com/mmarodr)  
#### Orientador: [Leonardo](https://github.com/link_do_github)

---

Trabalho apresentado ao curso [BI MASTER](https://ica.puc-rio.ai/bi-master) como pré-requisito para conclusão e obtenção de crédito na disciplina **"Projetos de Sistemas Inteligentes de Apoio à Decisão"**.

- [Link para o código](https://github.com/mmarodr/AI_agents/tree/main)

---

### Resumo

O barateamento e a disponibilização de diversos serviços oferecendo **Grandes Modelos de Linguagem (LLMs)** tornaram seu uso popular tanto entre programadores experientes quanto entre iniciantes. Mesmo em grandes corporações como a **Petrobras**, com estruturas bem definidas, não se consegue evitar que iniciativas utilizando LLMs ocorram fora da área de **Tecnologia da Informação (TI)**. Assim, alinhada com essa tendência, a Petrobras incentiva que suas áreas não técnicas explorem o uso e o aprimoramento de processos baseadas em LLMs.

Durante a primeira etapa deste projeto, foi entregue à área de **Contabilidade** um chat capaz de utilizar **RAG** (*Retrieval-Augmented Generation*) em documentos internos da Empresa. No entanto, esse método se mostrou incompleto para atender às necessidades dos gestores e analistas.

A ideia era permitir que o chat pudesse interpretar a entrada do analista e decidisse o melhor caminho a seguir. Isso poderia envolver o uso de RAG, mas também outras demandas como:

- Estatísticas da base de documentos;  
- Interpretação de documentos extensos;  
- Assistência para busca em bases de dados;  
- Interpretação de resultados;  
- Cálculos matemáticos;  
- Gestão de memória de curto e longo prazo;  
- Fluxo direto para responder a um simples "bom dia".

Dado o número de alternativas, apenas a utilização de comandos por prompts tornou-se inviável, e os **agentes** surgiram como a melhor opção.

Este projeto representa a conclusão sobre a abordagem mais viável encontrada para a área de Contabilidade no uso de um chat com agentes de IA.

A escolha pelo desenvolvimento de um **framework próprio** foi motivada por dois grandes fatores:

1. **Conectores personalizados**: Estabelecer conexões em ambientes restritos da empresa podem requerer algumas personalizações que nem sempre são facilmente integráveis com frameworks de mercado.  
2. **Dinâmica própria dos agentes**: Agentes seguem fluxos idealizados por seus criadores, o que pode não se enquadrar em um fluxo predefinido de uma atividade.

Outros ganhos relevantes com o desenvolvimento interno incluem:

- **Controle preciso do tráfego de dados**, enviando à LLM apenas os tokens necessários em cada etapa do processo.  
- **Liberdade de implementar novas técnicas** sem depender das atualizações de frameworks de terceiros.  
- **Código direto e acessível** para não programadores, facilitando a leitura e o entendimento por profissionais fora da área de TI.

### Abstract

texto

### 1. Introdução

O barateamento e a disponibilização de diversos serviços oferecendo **Grandes Modelos de Linguagem (LLMs)** tornaram seu uso popular tanto entre programadores experientes quanto entre iniciantes.

Mesmo grandes corporações como a **Petrobras**, que possuem estruturas bem definidas, não conseguem evitar que iniciativas utilizando LLMs ocorram fora da área de **Tecnologia da Informação (TI)**. Assim, alinhada com essa tendência, a Petrobras incentiva que suas áreas não técnicas explorem por conta própria o uso e o aprimoramento de técnicas baseadas em LLMs.

Diversas comunidades se reuniram ao redor desse assunto dentro da Petrobras, permitindo o compartilhamento de aprendizados e ideias. Alguns desses foruns são organizados pela própria TI, o que auxilia no direcionamento da arquitetura mais atual.

A Contabilidade possui uma área dedicada para iniciativas tecnológicas, onde esse projeto foi desenvolvido. Foi consedido acesso ilimitado à APIs de LLM como as da OpenAI para que todo teste necessário pudesse ser feito. Este projeto representa a conclusão sobre a abordagem mais viável encontrada para a área de Contabilidade no uso de um chat com agentes de IA após 1 ano de trabalho (jan/24 a dez/24).

Durante a primeira etapa do projeto, foi entregue à área de **Contabilidade** um chat capaz de utilizar **RAG** (*Retrieval-Augmented Generation*) em documentos internos. No entanto, esse método se mostrou incompleto para atender às necessidades dos gestores e analistas. 

A ideia era permitir que o chat pudesse interpretar a entrada do analista e decidisse o melhor caminho a seguir. Isso poderia envolver o uso de RAG, mas também outras demandas como:

- Estatísticas da base de documentos;  
- Interpretação de documentos extensos;  
- Assistência para busca em bases de dados;  
- Interpretação de resultados;  
- Cálculos matemáticos;  
- Gestão de memória de curto e longo prazo;  
- Fluxo direto para responder a um simples "bom dia".

Dado o número de alternativas, o uso de prompts tornou-se inviável, e os **agentes** surgiram como a melhor opção.

Este projeto representa a conclusão sobre a abordagem mais viável encontrada para a área de Contabilidade no uso de um chat com agentes de IA.

A escolha pelo desenvolvimento de um **framework próprio** foi motivada por dois grandes fatores:

1. **Conectores personalizados**: Nem sempre são facilmente integráveis com frameworks de mercado.  
2. **Dinâmica própria dos agentes**: Agentes seguem fluxos idealizados por seus criadores, o que pode não se enquadrar em um fluxo predefinido de uma atividade.

Outros ganhos relevantes com o desenvolvimento interno incluem:

- **Controle preciso do tráfego de dados**, enviando à LLM apenas os tokens necessários em cada etapa do processo.  
- **Liberdade de implementar novas técnicas** sem depender das atualizações de frameworks de terceiros.  
- **Código direto e acessível** para não programadores, facilitando a leitura e o entendimento por profissionais fora da área de TI.

### 2. Modelagem

#### 2.1. Manipulação da API

O primeiro passo foi compreender como funcionava a api da LLM para retornar textos e tambem embeddings.
Dentre os desafios enfrentados vale listar a necessidade de um arquivo de certificado para conexão com a API e o limite de requisições máximas por minuto.
Optei por criar uma classe **llmClient_AzureOpenAI** usando apenas a biblioteca **request**.
Foram implementadas as funções de recuperação de texto e de embedding, já considerando o formato esperado pela classe de agentes.
Tambem adicionei um fluxo para tratamento do tameout da api, impedindo que o código quebrasse e permitindo multiplas solicitações simultânias, algo extremamente util na criação da base de vetores.

#### 2.2. Base de Documentos

Em seguida, dediquei meus esforços na criação da base de documentos.
Optei por uma escolha não convencional ao utilizar delta tables do Databricks para armazenar os vetores.
A opção pelo Databricks se deu pela estrutura robusta fornecida pela empresa, garantindo assim manutenção, confiabilidadade e restrição de acesso por controle de perfil por usuário/tabela.
Diferente de bancos de dados vetoriais uma delta table não permite cálculos vetoriais diretamente no SQL. A solução foi disponibilizar no catálogo uma função usando numpy que pode ser chamada diretamente no SQL (db_finc_cosine_distance.png).
Cada coleção de documentos será armazenada em 2 tabelas: file_base e vec_base.

- file base: cada linha contém os documentos inteiros (codificados em strig) e tambem colunas com metadados sobre os documentos (quantas o gestor da coleção definir);
- vec_base: armazena os pedaçoes de texto de cada documento e o vetor correspondente.

Para o tratamento dos documentos foi utilizada a classe **read_file**, que tambem é usada por agentes para conversão de documentos.
A classe **BaseKnowledgeBaseManager** foi criada para gerencias as funções necessárias para as consultas em bases de documentos.
Atualmente criei classes derivadas para utilizar o Databricks e tambem bases do SQLite.

#### 2.3. Base de Analytics

Procurando integrar ainda mais o chat com o dia a dia dos analistas da Contabilidade, se fez necessário a interação com bases de dados.
Diferentemente da base de documentos, as bases de dados podem ter formatos distintos, apresentando estruturas variadas de tipos e quantidade de colunas.
Nesse tipo de conexão tambem foi optado por estabelecer o conceito de coleção, que pode comportar uma ou mais tabelas de dados.
Quando houver mais de uma tabela de dados, o gestor da coleção deve definir o relacionamento entre as tabelas (quando existir) utilizando linguagem natural.

A classe **BaseDatabaseManager** foi criada para gerencias as funções necessárias para as consultas em bases de dados.
Atualmente criei classes derivadas para utilizar o Databricks e tambem bases do SQLite.

#### 2.3. Documentação das Bases

Como são possíveis coleções diversas, não era viável a utilização de pronpts de instruções sobre o uso das bases diretamente no código.
Optei por fazer todas as configurações de prompts de forma local nas bases, e ou arquivos json de configuração.
Dessa forma, o agente receberá instruções específicas conforme a base selecionada, garantindo escalabilidade do código e que a gestão das informações possa ser feita diretamente pelo gestor das bases.

Dentre as informações esperadas temos:

- A descrição da base: que tem um papel importantíssimo para que o agente possa escolher a coleção que mais se ajusta ao questionamento do analista.
- Instruções para a LLM: permite que sejam definidos comportamentos específicos para utilização daquela coleção.
- Definição de cada coluna: com toda informação necessária para que a LLM possa utilizar a coluna de forma adequada numa consulta SQL. É passado como um dicionário contendo dados como descrição, sinônimos, exemplos de uso, limite de dados (como uma lista de opções possíveis).

No caso específico das bases de dados, incluí também as seguintes informações: relação de tabelas da coleção; e relacionamento, para explicar a semantica entre as bases.

#### 2.4. Base de Memória

Esta base desempenha um papel relevante dentro do fluxo definido dos agentes.
Atualmente ela permite a armazenagem e recuperação de conversas, mas a ideia é ampliar seu uso para armazenar memória de longo prazo, permitindo que informações relevantes passadas por um analista em uma conversa possa ser utilizada em outras conversas futuras.
Uma outra implementação que estou planejando envolve a vetorização de parte das conversas, permitindo a utilização de RAG consultando toda a base de conversas, e não apenas os ultimos X assuntos, conforme está rodando atualmente.

Considerando a gestão dos chats atualmente implementada, a classe **BaseChatDatabaseManager** possui as funções necessárias para manipulação da base de memória, dividida em 3 tabelas:

- **ChatHistory**: Contem as informações gerais da conversa, como titulo e usuário.
- **ChatMessage**: Cada linha representa uma interação de analista e agentes. Se conecta com a tabela anterior pela coluna chat_id. É a tabela mais consultada no fluxo de agentes, pois contem os dados necessários para o contexto da conversa.
- **ChatAgencyFlow**: Grava todos os passos de cada agente utilizado no fluxo de resposta, incluindo os prompts utilizados. Se conecta com a tabela de mensagens pela coluna message_id.

Já foram desenvolvidas as classes derivadas para utilização do Postgres e do SQLite.

#### 2.5. Criação dos Agente

Nos próximos tópicos irei discorrer sobre as estratégias que escolhi para fazer a gestão dos agentes.

#### 2.5.1 Agente Base

O primeiro passo foi desenvolver a lógica de como o processo de resposta seria desenrolado dentro de um agente.
A classe **BaseAgent** possui todos os parâmetros e funções necessários para que um agente possa executar seu trabalho.

Dentre os parâmetros se destacam:

- Referências e metas do agente;
- Ferramentas (funções python) que podem ser chamadas;
- Agentes que podem ser chamados;
- Tamanho da memória a ser utilizada.

Quanto às funções, ressalto:

- Chamada do trabalho;
- Montagem do prompt para LLM;
- Chamada das ferramentas.

Após uma chamada de trabalho, o agente passará os prompts e retornará o resultado.
Caso existam ferramentas disponíveis e a LLM decida utilizar uma delas, o fluxo da resposta é alterado para execução da ferramenta.
Após essa execução, o agente entra em uma nova chamada de trabalho onde é passado no prompt a resposta da ferramenta.

Caso seja necessário utilizar uma segunda ferramenta, isso não será possível de acordo com o ciclo definido atualmente.
Nesse caso, a LLM pode dicidir em chamar como próximo agente o mesmo agente, e ele poderá executar as tarefas necessárias.
Uma das implementações referente ao retorno ao mesmo agente, seja por chamada feita pelo proprio agente ou por uma chamada mais a frente por outro agente, é que durante um fluxo de resposta, o agente recebe no prompt as suas interações anteriores, permitindo entender melhor porque ele está recebendo novamente uma tarefa, e em alguns casos, evitando a recorrência de erros.

De acordo com os meus testes, percebi que a construção de prompts em formato de dicionário tornava a minha verificação muito mais simples ao mesmo tempo que gerava respostas mais coerentes da LLM.

Em relação às entradas recebidas na chamada, procurei trabalhar de forma simples e objetiva, evitando um incremento desnecessário do prompt do agente.
Logo, minha escolha foi de passar apenas a pergunta original do analista e a resposta do agente anterior. Todas as outras instruções são geradas dentro do agente conforme suas definições de parâmetros.

#### 2.5.2 Agente Especialista

Em muitos casos, a definição de como um agente deve se comportar e tambem suas ferramentas já estão definidas, logo não á motivo de se programar a cada trabalho os parâmetros para esse agente.
Além disso, alguns agentes podem usar em diversas chamadas conexões proprias com bancos de dados específicos. Se torna muito mais adequado ter uma classe que compreenda todas as definições desse agente.

Atualmente criei 3 agentes que já estão em uso:

- **KnowledgeBaseAgent**: Responsável por interagir com gases de texto. Capaz de exegutar RAG, interpretação completa e buscas de documentos.
- **ChatInterpretorAgent**: Dedicado a análises em bases de dados. Pode ser usado para gerar insigt em relatórios de dados, ou apenas como um gerador de sql a partir de linguagem natural, fornecendo o 'csv' resultante para o analista.
- **ChatInterpretorAgent**: Definido para ser a porta de entrada do chat que desenvolvi. Possui funções de memória com o histórico de conversas, aperfeiçoamento de questões do analista e tambem a capacidade de executar tarefas na máquina usando um interpretador python.

Também está em desenvolvimento um agente especialista em memória (**MemoryAgent**). A ideia é que ele consiga buscar contexto não apenas na conversa atual do analista, mas em todo o histórico de conversas, inclusive de outros usuários (desde que conpartilhadas).
Penso que pode ser criada uma base vetorizada das conversas para ser utilizada nessa consulta.

Outro desenvolvimento que está no radar é a utilização de memória de longo prazo referente a informações específicas, como o nome do analista, preferências, gostos. Essa base poderia ser consultada por uma ferramenta no chat analista, o que ajudaria a aperfeiçoar o contexto de uma pergunta antes da tarefa ser repassada para o próximo agente.

#### 2.5.3 Fluxo de Trabalho

Todo trabalho da equipe de agentes deve ser organizado dentro de uma classe (**AgentWork**) capaz de organizar o fluxo da conversa e tambem de fornecer informações para o chat.
Como existirão diversas sesões rodando em paralelo, sendo uma para cada analista, deve ser instanciado um objeto dessa classe para cada sessão.
Esse objeto deve ser passado dentro de cada um dos agentes instanciados, gerando assim a sua 'equipe de trabalho'.

O paâmetro LLM definido nessa classe pode ser herdado pelos agentes da equioe, entretanto, é possivel fazer a definição por agente sobre qual cliente de LLM cada um irá usar.

A principal função é a **crew_work**, que inicia uma chamada para o trabalho da equipe.
Essa função irá controlar não apenas a interação entre os agentes, mas como os estados de memória necessários para uso dos agentes, como para exibição na tela do chat.
Também é responsavel por recuperar e armazenar dados na memória do banco de dados, quando um objeto gerenciador de memória é passado. Porém, é possivel trabalhar apenas com memória da máquina para testes sem o uso da aplicação em flask.

#### 2.5.4 O Agente Humano

Considero que uma das melhores interações criadas nesse framework é a possibilidade de consulta ao analista no meio do processo de trabalho da equipe de agentes.

Quando o parâmetro **human_in_the_loop** de um agente é definido como **True**, o agente irá interromper sua parefa antes de sua resposta para que o analista possa avaliar se a resposta está adequada e se pode seguir para o próximo agente sugerido (ou encerrar o trabalho).
Em casos de execução de ferramentas, é adicionada uma outra interação com o analista, onde ele pode ver a função escolhida pelo agente e os parâmetros utilizados. Isso pode evitar, por exemplo, que uma consulta sql seja executada utilizando uma coluna errada, pois o analista tem tempo de informar a correção antes da execução.

Infelizmente ainda não consegui desenvolver no chat a interface adequada para essa interação, mas ela pode ser testada nos notebooks de exemplos.

### 2.6. Sobre a Aplicação

Neste primeiro desenvolvimento foi utilizada a biblioteca flask para executar o chat. Estão sendo feitos estudos para migração para a bilbioteca fastApi.

Ela está hospedada em um container Docker do Linux em um serviço da Petrobras.

Tanto do Banco Postgres, quanto o Databricks rodam em serviços independentes ao da aplicação.

### 3. Resultados

O framework se mostra sólido e capaz de atender a todas as especificações egigidas, entretanto certas funcionalidades ainda precisam ser melhoradas, como o uso de memória de longo prazo e a interação do analista diretamente no chat.

A aplicaação ainda precisa de diversas melhorias e testes de interação dos analistas no serviço web, principalmente relacionadas à capacidade do container e uso de memória.

Houve um esforço grande para reduzir o uso de memóeria do container com a serialização de objetos e salbamento em banco de dados, entretanto, alumas interações ainda ocorrem utilizando variáves globais para maior agilidade ou incapacidade de serialização.

Com a ampliação e disponibilização da aplicação e bases de conhecimento, é possível executar testes reais de casos de uso. Como próximo passo, deverão ser envolvidos analistas das áreas para que eles possam dar o retorno sobre a qualidade das respostas, e assim, possamos aperfeiçoar ainda mais os prompts dos agentes.

Além disso, continuarão sendo desenvolvidas funcionalidades facilitadoras que estão mapeadas e precisam de maiores testes e desenvolvimento.

Nesse link gravei um vídeo da aplicação em funcionamento para visualização das funcionalidades disponíveis:
[Chat Contabilidade](https://youtube.com)

### 4. Conclusões

De forma geral, esse trabalho fomentou um grande incremento no meu entendimento sobre como funcionam as interações de agentes, o uso de ferramentas e principalmente sobre a gestão de memória e conteúdo passado à LLM. Entender o funcionamento por dentro desse tipo de fluxo e tambem de processos de larga usabilidade como RAG me tornou mais capaz para manipular esse tipo de framework e tambem de ensinar sobre.

Muitos frameworks tem evoluido bastante desde que esse trabalho foi iniciado no início de 2024, dentre eles destaco o CrewAI.

Ainda deve ser analisada se a troca do framework criado por uma biblioteca mais robusta trará mais benefícios e se tem a capacidade de atender a todas as demandas desenvolvidas sem a necessidade de alterações complexas.

Certamente as comparações serão feitas e de forma muito mais simples a partir de agora.

---

Matrícula: 221100995

Pontifícia Universidade Católica do Rio de Janeiro

Curso de Pós Graduação *Business Intelligence Master*
