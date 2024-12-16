# Agentes de IA - Desenvolvimento Próprio

#### Aluno: [Marcos de Mattos Amarante Rodrigues](https://github.com/mmarodr)
#### Orientadora: [Leonardo](https://github.com/link_do_github)

---

Trabalho apresentado ao curso [BI MASTER](https://ica.puc-rio.ai/bi-master) como pré-requisito para conclusão de curso e obtenção de crédito na disciplina "Projetos de Sistemas Inteligentes de Apoio à Decisão".

- [Link para o código](/AI_agents).

---

### Resumo

O barateamento e a disponibilização de diversos serviços oferecendo Grandes Modelos de Linguagem - LLMs tornou seu uso popular tanto entre experientes programadores quanto para iniciantes no assunto. Mesmo dentro de grandes corporações como a Petrobras, com estruturas bem definidadas sobre sua organização não conseguem evitar que iniciativas utilizando LLMs ocorram fora da sua area de Tecnologia, então, remando junto a corrente, a Petrobras incentiva que suas áreas fora da TI busquem seus usos e aprimoramentos em tecnicas utilizando LLMs.
Durante a primeira etapa de entendimento do projeto foi entregue em produção para a área de Contabilidade da Petrobras um chat capáz de utilizar RAG em documentos internos, entretanto esse método ainda se mostrava inclompleto para atender as necessidades dos gestores e analistas.
A ideia era permitir que o chat pudesse interpretar a entrada do analista e decidisse o melhor caminho a seguir, o que poderia ser pelo uso de RAG como primeiramente desenvolvido, mas tambem atendendo a outras demandas como:
  - estatisticas da base de documentos;
  - interpretação de documentos inteiros, mesmo que muito extensos;
  - assistente para busca em base de dados;
  - interpretador de resultados;
  - especialista em cálculos matemáticos;
  - gestor de memória de curto e longo prazo;
  - ou um fluxo direto para responder a um simples bom dia.
Como se tornara inviável o tratamento de tantas alternativas pelo uso de prompts, os agentes pareceram a melhor opção a ser seguida.
Este projeto representa minha conclusão sobre a forma mais viável encontrada para a área da Contabilidade no uso de um chat utilizando agentes de IA.
A escolha pelo desenvolvimento de um framework proprio foi motivada pela dificuldade de dois grandes fatores do projeto:
  - utilização de conectores próprios nem sempre é direta com frameworks de mercado;
  - agentes tendem a seguir uma dinâmica propria, idealizada por seus criadores, o que não necessariamente se enquadra em um fluxo pre definido de uma atividade.
Outros ganhos relevantes tambem se destacam ao optarmos pelo desenvolvimento interno:
  - controle preciso do trafego de dados, enviando para a LLM apenas os tokens necessários em cada etapa do processo;
  - liberdade para implementar novas técnicas sem depender que o framework escolhido já tenha incluido suas atualizações;
  - códigos mais diretos, voltado para não programadores, facilitando a leitura e entendimento por proficional fora da área de TI.

### Abstract

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Proin pulvinar nisl vestibulum tortor fringilla, eget imperdiet neque condimentum. Proin vitae augue in nulla vehicula porttitor sit amet quis sapien. Nam rutrum mollis ligula, et semper justo maximus accumsan. Integer scelerisque egestas arcu, ac laoreet odio aliquet at. Sed sed bibendum dolor. Vestibulum commodo sodales erat, ut placerat nulla vulputate eu. In hac habitasse platea dictumst. Cras interdum bibendum sapien a vehicula.

Proin feugiat nulla sem. Phasellus consequat tellus a ex aliquet, quis convallis turpis blandit. Quisque auctor condimentum justo vitae pulvinar. Donec in dictum purus. Vivamus vitae aliquam ligula, at suscipit ipsum. Quisque in dolor auctor tortor facilisis maximus. Donec dapibus leo sed tincidunt aliquam.

Donec molestie, ante quis tempus consequat, mauris ante fringilla elit, euismod hendrerit leo erat et felis. Mauris faucibus odio est, non sagittis urna maximus ut. Suspendisse blandit ligula pellentesque tincidunt malesuada. Sed at ornare ligula, et aliquam dui. Cras a lectus id turpis accumsan pellentesque ut eget metus. Pellentesque rhoncus pellentesque est et viverra. Pellentesque non risus velit. Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus.

### 1. Introdução

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Proin pulvinar nisl vestibulum tortor fringilla, eget imperdiet neque condimentum. Proin vitae augue in nulla vehicula porttitor sit amet quis sapien. Nam rutrum mollis ligula, et semper justo maximus accumsan. Integer scelerisque egestas arcu, ac laoreet odio aliquet at. Sed sed bibendum dolor. Vestibulum commodo sodales erat, ut placerat nulla vulputate eu. In hac habitasse platea dictumst. Cras interdum bibendum sapien a vehicula.

Proin feugiat nulla sem. Phasellus consequat tellus a ex aliquet, quis convallis turpis blandit. Quisque auctor condimentum justo vitae pulvinar. Donec in dictum purus. Vivamus vitae aliquam ligula, at suscipit ipsum. Quisque in dolor auctor tortor facilisis maximus. Donec dapibus leo sed tincidunt aliquam.

### 2. Modelagem

O primeiro passo foi compreender como funcionava a api da LLM para retornar textos e tambem embeddings. 

### 3. Resultados

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Proin pulvinar nisl vestibulum tortor fringilla, eget imperdiet neque condimentum. Proin vitae augue in nulla vehicula porttitor sit amet quis sapien. Nam rutrum mollis ligula, et semper justo maximus accumsan. Integer scelerisque egestas arcu, ac laoreet odio aliquet at. Sed sed bibendum dolor. Vestibulum commodo sodales erat, ut placerat nulla vulputate eu. In hac habitasse platea dictumst. Cras interdum bibendum sapien a vehicula.

Proin feugiat nulla sem. Phasellus consequat tellus a ex aliquet, quis convallis turpis blandit. Quisque auctor condimentum justo vitae pulvinar. Donec in dictum purus. Vivamus vitae aliquam ligula, at suscipit ipsum. Quisque in dolor auctor tortor facilisis maximus. Donec dapibus leo sed tincidunt aliquam.

### 4. Conclusões

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Proin pulvinar nisl vestibulum tortor fringilla, eget imperdiet neque condimentum. Proin vitae augue in nulla vehicula porttitor sit amet quis sapien. Nam rutrum mollis ligula, et semper justo maximus accumsan. Integer scelerisque egestas arcu, ac laoreet odio aliquet at. Sed sed bibendum dolor. Vestibulum commodo sodales erat, ut placerat nulla vulputate eu. In hac habitasse platea dictumst. Cras interdum bibendum sapien a vehicula.

Proin feugiat nulla sem. Phasellus consequat tellus a ex aliquet, quis convallis turpis blandit. Quisque auctor condimentum justo vitae pulvinar. Donec in dictum purus. Vivamus vitae aliquam ligula, at suscipit ipsum. Quisque in dolor auctor tortor facilisis maximus. Donec dapibus leo sed tincidunt aliquam.

---

Matrícula: 221100995

Pontifícia Universidade Católica do Rio de Janeiro

Curso de Pós Graduação *Business Intelligence Master*
