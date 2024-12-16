# Agentes de IA - Desenvolvimento Próprio

#### Aluno: [Marcos de Mattos Amarante Rodrigues](https://github.com/mmarodr)  
#### Orientador: [Leonardo](https://github.com/link_do_github)

---

Trabalho apresentado ao curso [BI MASTER](https://ica.puc-rio.ai/bi-master) como pré-requisito para conclusão e obtenção de crédito na disciplina **"Projetos de Sistemas Inteligentes de Apoio à Decisão"**.

- [Link para o código](/AI_agents)

---

### Resumo

O barateamento e a disponibilização de diversos serviços oferecendo **Grandes Modelos de Linguagem (LLMs)** tornaram seu uso popular tanto entre programadores experientes quanto entre iniciantes. Mesmo em grandes corporações como a **Petrobras**, com estruturas bem definidas, não se consegue evitar que iniciativas utilizando LLMs ocorram fora da área de **Tecnologia da Informação (TI)**. Assim, alinhada com essa tendência, a Petrobras incentiva que suas áreas não técnicas explorem o uso e o aprimoramento de técnicas baseadas em LLMs.

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
