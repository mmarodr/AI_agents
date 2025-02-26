// Alterna a barra lateral para mostrar ou ocultar o menu sanduíche
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    sidebar.classList.toggle('expanded');
}

// Exibe a seção selecionada e salva a seleção no localStorage
function showContent(sectionId) {
    const sections = document.querySelectorAll('.content-section');
    sections.forEach(section => {
        section.style.display = section.id === sectionId ? 'block' : 'none';
    });
    localStorage.setItem('selectedSection', sectionId);
}




// Restaura a seção selecionada ao carregar a página
function restoreSelectedSection() {
    const selectedSection = localStorage.getItem('selectedSection') || 'home';
    showContent(selectedSection);
}

// Alterna o status de execução com efeito de expansão
function toggleStatus(index) {
    const statusBox = document.getElementById(`status-${index}`);
    if (statusBox.style.maxHeight === "0px" || statusBox.style.display === "none") {
        statusBox.style.display = "block";
        statusBox.style.maxHeight = `${statusBox.scrollHeight}px`; // Define a altura conforme o conteúdo
    } else {
        statusBox.style.maxHeight = "0px";
        setTimeout(() => { statusBox.style.display = "none"; }, 300); // Aguarda a animação antes de esconder
    }
}

// Alterna a seção de anexos
function toggleAttachment(index) {
    const attachmentBox = document.getElementById(`attachment-${index}`);
    if (attachmentBox.style.maxHeight === "0px" || attachmentBox.style.display === "none") {
        attachmentBox.style.display = "block";
        attachmentBox.style.maxHeight = `${attachmentBox.scrollHeight}px`; // Define a altura conforme o conteúdo
    } else {
        attachmentBox.style.maxHeight = "0px";
        setTimeout(() => { attachmentBox.style.display = "none"; }, 300); // Aguarda a animação antes de esconder
    }
}

// Ativa ou desativa um agente e envia a atualização para o backend
function toggleAgent(agentId) {
    const isActive = document.getElementById(agentId).checked;
    $.ajax({
        url: '/toggle_agent',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ agent_id: agentId, active: isActive }),
        success: function() {
            console.log(`Agente ${agentId} agora está ${isActive ? 'ativo' : 'inativo'}.`);
        },
        error: function(xhr, status, error) {
            console.error(`Erro ao alterar o estado do agente ${agentId}:`, error);
        }
    });
}

// Função para atualizar a lista de coleções selecionadas para um agente específico
function updateCollectionList(agent_name, collection, is_active) {
    $.ajax({
        url: '/update_collection_list',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ agent_name: agent_name, collection: collection, is_active: is_active }),
        success: function(response) {
            console.log("Coleção atualizada:", response);
        },
        error: function(error) {
            console.error("Erro ao atualizar coleção:", error);
        }
    });
}

// Função de rolagem suave ao final da conversa
function smoothScrollToEnd() {
    const messageContainer = document.getElementById("message-container");
    messageContainer.scroll({ top: messageContainer.scrollHeight, behavior: "smooth" });
}

// Envia a mensagem ao pressionar Enter, adiciona linha com Shift + Enter
function handleEnterPress(event) {
    const submitButton = document.getElementById('submit-button');
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault(); // Evita quebra de linha

        // Verifica se o botão de envio está desabilitado
        if (!submitButton.disabled) {
            document.querySelector("form").submit(); // Submete o formulário
        }
    }
}

// Limpar o Campo de Input Após o Envio
function handleFormSubmit(event) {
    event.preventDefault(); // Impede o envio padrão do formulário

    // Obtém o valor do campo de input e remove espaços em branco extras
    const userInput = document.querySelector("textarea[name='user_input']").value.trim();

    // Verifica se há algum texto antes de enviar
    if (userInput === "") {
        showAlert("Por favor, insira uma mensagem antes de enviar.", "danger");
        return false;
    }

    // Limpa o campo de input após o envio
    document.querySelector("textarea[name='user_input']").value = "";

    // Desabilita o botão de envio
    document.getElementById('submit-button').disabled = true;    

    // Envia o formulário manualmente
    event.target.submit();

    return true;
}

function checkForCompletion() {
    $.getJSON('/get_answers', function(data) {
        const messageContainer = $('#message-container');
        messageContainer.empty();

        let allComplete = true;
        data.paired_data.forEach(([answer, status, attachment], index) => {

            // Processando o status
            const statusContent = status.map(step => {
                const colorStyle = step.color ? `color: ${step.color};` : '';
                const fontWeightStyle = step.bold ? 'font-weight: bold;' : '';
                return `<p style="${colorStyle} ${fontWeightStyle}">${step.text || step}</p>`;
            }).join('');

            const isProcessing = (answer.answer === "Processando...");
            const loadingIndicator = isProcessing ? '<span class="loading-indicator"></span>' : '';

            // Processando os anexos
            let attachmentContent = '';
            if (attachment && attachment.length > 0) {
                attachment.forEach(item => {
                    for (const [agent, files] of Object.entries(item)) {
                        attachmentContent += `<p><strong>${agent}:</strong></p>`;
                        attachmentContent += '<ul>';
                        files.forEach(fileDict => {
                            for (const [fileName, fileContent] of Object.entries(fileDict)) {
                                // Criação do link de download com atributos de filename e filecontent
                                attachmentContent += `
                                    <li>
                                        <a href="#" data-filename="${fileName}" data-filecontent="${fileContent}" onclick="downloadFile(event, this)">
                                            ${fileName}
                                        </a>
                                    </li>
                                `;
                            }
                        });
                        attachmentContent += '</ul>';
                    }
                });
            } else {
                attachmentContent = '<p>Sem anexos disponíveis.</p>';
            }

            // Adiciona cada par de pergunta/resposta e o status de execução correspondente
            messageContainer.append(`
                <div class="chat-pair">
                    <div class="chat-bubble user-message">${answer.query_input.replace(/\n/g, '<br>')}</div>
                    
                    <!-- Botão para status -->
                    <button class="btn btn-link text-decoration-none p-0 execution-status-toggle" onclick="toggleStatus(${index})">
                        <i class="fas fa-eye"></i> Mostrar/Ocultar Status de Execução
                    </button>
                    <div class="execution-status" id="status-${index}" style="display: ${index === data.paired_data.length - 1 ? 'block' : 'none'};">
                        ${statusContent}
                    </div>
                    
                    <!-- Botão para anexos -->
                    <button class="btn btn-link text-decoration-none p-0 attachment-toggle" onclick="toggleAttachment(${index})">
                        <i class="fas fa-paperclip"></i> Mostrar/Ocultar Anexos
                    </button>
                    <div class="attachment-section" id="attachment-${index}" style="display: none;">
                        ${attachmentContent}
                    </div>
                    
                    <div class="chat-bubble agent-message" id="answer-${index}">${loadingIndicator} ${answer.answer}</div>
                </div>
            `);

            if (isProcessing) {
                allComplete = false;
            }
        });

        smoothScrollToEnd();
        document.getElementById('submit-button').disabled = !allComplete;

        if (!allComplete) {
            setTimeout(checkForCompletion, 1000);
        }
    });
}

function downloadFile(event, element) {
    event.preventDefault(); // Previne o comportamento padrão do link

    const fileName = element.getAttribute('data-filename');
    const fileContentBase64 = element.getAttribute('data-filecontent');

    if (!fileName || !fileContentBase64) {
        alert('Informações do arquivo ausentes.');
        return;
    }

    try {
        // Decodifica o conteúdo Base64
        const byteCharacters = atob(fileContentBase64);

        // Converte para um array de bytes
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);

        // Determina o tipo MIME com base na extensão do arquivo
        let mimeType = 'application/octet-stream';
        if (fileName.toLowerCase().endsWith('.pdf')) {
            mimeType = 'application/pdf';
        } else if (fileName.toLowerCase().endsWith('.txt')) {
            mimeType = 'text/plain';
        }
        // Adicione outros tipos MIME conforme necessário

        // Cria um Blob a partir do array de bytes
        const blob = new Blob([byteArray], { type: mimeType });

        // Cria um link temporário para download
        const link = document.createElement('a');
        link.href = window.URL.createObjectURL(blob);
        link.download = fileName;

        // Adiciona o link ao documento e clica nele
        document.body.appendChild(link);
        link.click();

        // Remove o link após o download
        document.body.removeChild(link);
        window.URL.revokeObjectURL(link.href);
    } catch (error) {
        console.error('Erro ao baixar o arquivo:', error);
        alert('Ocorreu um erro ao baixar o arquivo.');
    }
}

// função para ocultar a barra lateral
function toggleInfoSidebar() {
    const sidebar = document.getElementById("infoSidebar");
    sidebar.classList.toggle("hidden");
}

// Expande automaticamente a altura do textarea e envia a mensagem com Enter
document.addEventListener('input', function (event) {
    if (event.target.tagName.toLowerCase() === 'textarea') {
        event.target.style.height = 'auto'; // Redefine a altura
        event.target.style.height = (event.target.scrollHeight) + 'px'; // Define a altura conforme o conteúdo
    }
});

// Função para alternar a visibilidade da barra lateral
function toggleInfoSidebar() {
    const sidebar = document.getElementById("infoSidebar");
    sidebar.classList.toggle("hidden");

    const toggleButton = sidebar.querySelector(".toggle-button");
    toggleButton.textContent = sidebar.classList.contains("hidden") ? "❯" : "❮";
}

// Expande o textarea para cima em vez de crescer indefinidamente
document.addEventListener('input', function (event) {
    if (event.target.tagName.toLowerCase() === 'textarea') {
        event.target.style.height = 'auto';
        event.target.style.height = Math.min(event.target.scrollHeight, 150) + 'px'; // Limita o crescimento para cima
    }
});

// Abre o modal
function openCollectionModal() {
    console.log("Abrindo o modal..."); // Verifique se isso aparece no console
    document.getElementById("collectionModal").style.display = "flex";
}

// Fecha o modal
function closeCollectionModal() {
    document.getElementById("collectionModal").style.display = "none";
}

// Função para adicionar a nova coleção à UI
function addCollectionToUI(newCollection) {
    // newCollection é um objeto aninhado, ex: { "Documentos Pessoais": { "Nova Coleção": True } }
    for (const agentName in newCollection) {
        if (newCollection.hasOwnProperty(agentName)) {
            const collections = newCollection[agentName];
            for (const collectionName in collections) {
                if (collections.hasOwnProperty(collectionName)) {
                    const isActive = collections[collectionName];
                    
                    // Encontre o contêiner da coleção para o agente específico
                    const collectionContainer = $(`#agent-management .collection-selection h4:contains("${agentName}")`).parent();

                    if (collectionContainer.length > 0) {
                        // Adicione o novo checkbox à lista
                        const newCheckboxId = `${agentName}-${collectionName}`;
                        const newCheckboxHtml = `
                            <div>
                                <input type="checkbox" id="${newCheckboxId}" value="${collectionName}" ${isActive ? 'checked' : ''} onclick="updateCollectionList('${agentName}', '${collectionName}', this.checked)" />
                                <label for="${newCheckboxId}">${collectionName}</label>
                            </div>
                        `;
                        collectionContainer.append(newCheckboxHtml);
                    } else {
                        // Se o agente não tiver uma seção de coleções, cria uma nova seção
                        console.warn(`Agente "${agentName}" não encontrado na UI. Criando uma nova seção.`);
                        const newSectionHtml = `
                            <div class="collection-selection">
                                <h4>${agentName}</h4>
                                <div>
                                    <input type="checkbox" id="${agentName}-${collectionName}" value="${collectionName}" ${isActive ? 'checked' : ''} onclick="updateCollectionList('${agentName}', '${collectionName}', this.checked)" />
                                    <label for="${agentName}-${collectionName}">${collectionName}</label>
                                </div>
                            </div>
                        `;
                        $('#agent-management').append(newSectionHtml);
                    }
                }
            }
        }
    }
}

// Função para submeter o formulário e enviar dados ao backend
function submitCollectionForm(event) {
    event.preventDefault(); // Previne o comportamento padrão de submissão do formulário

    // Obtenha os valores dos campos
    const nome_da_colecao = document.getElementById("nome_da_colecao").value;
    const table_common_name = document.getElementById("table_common_name").value || null;
    const curator = document.getElementById("curator").value || null;
    const table_description = document.getElementById("table_description").value || null;
    const gpt_instructions = document.getElementById("gpt_instructions").value || null;

    // Cria o objeto de dados a ser enviado
    const data = {
        nome_da_colecao,
        table_common_name,
        curator,
        table_description,
        gpt_instructions
    };

    // Envia os dados ao backend via AJAX
    $.ajax({
        url: '/create_personal_collection',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function(response) {
            console.log("Coleção criada com sucesso:", response);
            // Fecha o modal e limpa o formulário
            closeCollectionModal();
            document.getElementById("collectionForm").reset();
            // Exibe uma mensagem de sucesso
            showAlert("Coleção criada com sucesso!", "success");
            // Atualiza a lista de coleções dinamicamente
            addCollectionToUI(response.new_collection);
        },
        error: function(xhr, status, error) {
            console.error("Erro ao criar coleção:", error);
            // Exibe uma mensagem de erro
            showAlert("Houve um erro ao criar a coleção. Por favor, tente novamente.", "danger");
        }
    });

    return false; // Previne o envio do formulário padrão
}

// Função para exibir alertas Bootstrap
function showAlert(message, type = 'success', timeout = 3000) {
    const alertContainer = $('#alert-container');
    const alertId = `alert-${Date.now()}`;
    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                <span aria-hidden="true">&times;</span>
            </button>
        </div>
    `;
    alertContainer.append(alertHtml);

    // Remove o alerta após o tempo especificado
    setTimeout(() => {
        $(`#${alertId}`).alert('close');
    }, timeout);
}

// Abre o modal para adicionar documentos
function openAddDocumentModal() {
    document.getElementById("addDocumentModal").style.display = "flex";
}

// Fecha o modal
function closeAddDocumentModal() {
    document.getElementById("addDocumentModal").style.display = "none";
}

// Função para enviar o formulário de adicionar documento
function setFilePathText() {
    const fileInput = document.getElementById("file_path");
    const filePath = fileInput.value;

    // Verifica se o caminho foi obtido
    console.log("Caminho do arquivo selecionado:", filePath);

    // Defina o valor como o caminho completo do arquivo (no Windows, o caminho real não é diretamente acessível por segurança)
    // document.getElementById("file_path_text").value = filePath;
}

// Modifique o envio para usar o caminho
function submitAddDocumentForm(event) {
    event.preventDefault();

    const nome_colecao = document.getElementById("nome_colecao").value;
    const fileInput = document.getElementById("file_for_doc_collection");

    // Verifica se um arquivo foi selecionado
    if (fileInput.files.length === 0) {
        alert("Por favor, selecione um arquivo.");
        return;
    }

    const formData = new FormData();
    formData.append("nome_colecao", nome_colecao);
    formData.append("file_for_doc_collection", fileInput.files[0]); // Adiciona o arquivo selecionado

    $.ajax({
        url: '/add_document',
        type: 'POST',
        data: formData,
        processData: false,  // Impede que o jQuery processe o arquivo
        contentType: false,  // Deixe o jQuery definir o content type automaticamente
        success: function(response) {
            closeAddDocumentModal();
            showAlert(response.message, "success");
        },
        error: function(xhr, status, error) {
            showAlert("Erro ao adicionar o documento. Por favor, tente novamente.", "danger");
        }
    });
}

// Abre o modal de criação de coleção de tabelas
function openTableCollectionModal() {
    document.getElementById("tableCollectionModal").style.display = "flex";
}

// Fecha o modal
function closeTableCollectionModal() {
    document.getElementById("tableCollectionModal").style.display = "none";
}

// Função para submeter o formulário e enviar dados ao backend
function submitTableCollectionForm(event) {
    event.preventDefault(); // Previne o comportamento padrão de submissão do formulário

    // Obtenha os valores dos campos
    const nome_tabela_colecao = document.getElementById("nome_tabela_colecao").value;
    const process_description = document.getElementById("process_description").value || null;
    const relationships       = document.getElementById("relationships").value || null;

    // Cria o objeto de dados a ser enviado
    const data = {
        nome_tabela_colecao,
        process_description,
        relationships
    };

    // Envia os dados ao backend via AJAX
    $.ajax({
        url: '/create_table_collection',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function(response) {
            console.log("Coleção criada com sucesso:", response);
            // Fecha o modal e limpa o formulário
            closeTableCollectionModal();
            document.getElementById("tableCollectionForm").reset();
            // Exibe uma mensagem de sucesso
            showAlert("Coleção criada com sucesso!", "success");
            // Atualiza a lista de coleções dinamicamente
            addCollectionToUI(response.new_collection);
        },
        error: function(xhr, status, error) {
            console.error("Erro ao criar coleção:", error);
            // Exibe uma mensagem de erro
            showAlert("Houve um erro ao criar a coleção. Por favor, tente novamente.", "danger");
        }
    });

    return false; // Previne o envio do formulário padrão
}

// Abre o modal de adicionar tabela
function openAddTableModal() {
    document.getElementById("addTableModal").style.display = "flex";
}

// Fecha o modal
function closeAddTableModal() {
    document.getElementById("addTableModal").style.display = "none";
}

// Envia o formulário de criação de coleção de tabelas
function submitAddTableForm(event) {
    event.preventDefault();

    const tabela_colecao = document.getElementById("tabela_colecao").value;
    const table_name = document.getElementById("table_name").value;
    const column_type = document.getElementById("column_type").value;
    const csv_file = document.getElementById("file_path").files[0];

    // Verifica se um arquivo foi selecionado
    if (!csv_file) {
        alert("Por favor, selecione um arquivo CSV.");
        return;
    }

    // Usar FormData para enviar dados, incluindo o arquivo
    const formData = new FormData();
    formData.append("tabela_colecao", tabela_colecao);
    formData.append("table_name", table_name);
    formData.append("column_type", column_type);
    formData.append("csv_file", csv_file);

    $.ajax({
        url: '/add_table_to_collection',
        type: 'POST',
        data: formData,
        processData: false,  // Impede o jQuery de processar os dados
        contentType: false,  // Deixa o jQuery definir o tipo de conteúdo automaticamente
        success: function(response) {
            console.log("Requisição AJAX bem-sucedida:", response);
            closeAddTableModal();
            showAlert(response.message, "success");
        },
        error: function(xhr, status, error) {
            console.error("Erro na requisição AJAX:", error);
            showAlert("Erro ao adicionar a tabela à coleção.", "danger");
        }
    });
}

function startNewChat() {
    const username = "USERNAME"; // Substitua pelo nome de usuário real, se necessário
    $.ajax({
        url: '/new_chat',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ username }),
        success: function() {
            // Limpa a tela de chat após iniciar um novo chat
            $('#message-container').empty();
            alert("Novo chat iniciado com sucesso!");
        },
        error: function(error) {
            console.error("Erro ao iniciar novo chat:", error);
        }
    });
}

function loadChatList() {
    $.ajax({
        url: '/get_chat_list',
        method: 'GET',
        success: function(chatList) {
            const chatListContainer = $('#chat-list');
            chatListContainer.empty();

            // Adiciona cada chat como um item clicável na lista
            chatList.forEach(chat => {
                const chatItem = `
                    <li class="list-group-item list-group-item-action" onclick="recoverChat('${chat.chat_id}')">
                        ${chat.chat_title}
                    </li>`;
                chatListContainer.append(chatItem);
            });
        },
        error: function(error) {
            console.error("Erro ao carregar lista de chats:", error);
        }
    });
}

function recoverChat(chatId) {
    $.ajax({
        url: '/recover_chat',
        method: 'POST',
        contentType: 'application/json',
        cache: false,
        data: JSON.stringify({ chat_id: chatId }),
        success: function(response) {
            if (response.status === "success") {
                const messageContainer = $('#message-container');
                messageContainer.empty(); // Limpa o contêiner antes de adicionar o novo conteúdo

                response.paired_data.forEach((item, index) => {
                    const answer = item[0];
                    const status = item[1];
                    const attachment = item[2];

                    // Processa o conteúdo de status
                    const statusContent = status.map(step => {
                        const colorStyle = step.color ? `color: ${step.color};` : '';
                        const fontWeightStyle = step.bold ? 'font-weight: bold;' : '';
                        return `<p style="${colorStyle} ${fontWeightStyle}">${step.text || step}</p>`;
                    }).join('');

                    // Processa o conteúdo de anexos
                    let attachmentContent = '';
                    if (attachment && attachment.length > 0) {
                        attachment.forEach(item => {
                            for (const [agent, files] of Object.entries(item)) {
                                attachmentContent += `<p><strong>${agent}:</strong></p><ul>`;
                                files.forEach(fileDict => {
                                    for (const [fileName, fileContent] of Object.entries(fileDict)) {
                                        attachmentContent += `
                                            <li>
                                                <a href="#" data-filename="${fileName}" data-filecontent="${fileContent}" onclick="downloadFile(event, this)">
                                                    ${fileName}
                                                </a>
                                            </li>`;
                                    }
                                });
                                attachmentContent += '</ul>';
                            }
                        });
                    } else {
                        attachmentContent = '<p>Sem anexos disponíveis.</p>';
                    }

                    // Monta e adiciona cada par de pergunta/resposta, status e anexos no contêiner de mensagens
                    messageContainer.append(`
                        <div class="chat-pair">
                            <div class="chat-bubble user-message">${answer.query_input.replace(/\n/g, '<br>')}</div>
                            
                            <button class="btn btn-link text-decoration-none p-0 execution-status-toggle" onclick="toggleStatus(${index})">
                                <i class="fas fa-eye"></i> Mostrar/Ocultar Status de Execução
                            </button>
                            <div class="execution-status" id="status-${index}" style="display: none;">
                                ${statusContent}
                            </div>
                            
                            <button class="btn btn-link text-decoration-none p-0 attachment-toggle" onclick="toggleAttachment(${index})">
                                <i class="fas fa-paperclip"></i> Mostrar/Ocultar Anexos
                            </button>
                            <div class="attachment-section" id="attachment-${index}" style="display: none;">
                                ${attachmentContent}
                            </div>
                            
                            <div class="chat-bubble agent-message" id="answer-${index}">
                                ${answer.answer}
                            </div>
                        </div>
                    `);
                });

                alert("Chat recuperado com sucesso!");
            }
        },
        error: function(error) {
            console.error("Erro ao recuperar chat:", error);
        }
    });
}

function editChatTitle(chatId, currentTitle) {
    // Solicita ao usuário um novo título
    const newTitle = prompt("Editar título do chat:", currentTitle);

    // Verifica se o novo título foi inserido e é diferente do atual
    if (newTitle && newTitle !== currentTitle) {
        $.ajax({
            url: '/edit_chat_title',
            method: 'POST',
            contentType: 'application/json',
            cache: false,
            data: JSON.stringify({ chat_id: chatId, new_title: newTitle }),
            success: function(response) {
                if (response.status === "success") {
                    alert("Título do chat atualizado com sucesso!");
                    location.reload(); // Recarrega a página para atualizar a lista de chats
                } else {
                    alert("Erro ao atualizar o título do chat.");
                }
            },
            error: function(error) {
                console.error("Erro ao atualizar o título do chat:", error);
                alert("Erro ao atualizar o título do chat. Verifique o console para mais detalhes.");
            }
        });
    }
}

function deleteChat(chatId) {
    $.ajax({
        url: '/delete_chat',
        method: 'POST',
        contentType: 'application/json',
        cache: false,
        data: JSON.stringify({ chat_id: chatId }),
        success: function(response) {
            if (response.status === "success") {
                alert("Chat deletado com sucesso!");
                location.reload(); // Recarrega a página para atualizar a lista de chats
            } else {
                alert("Erro ao deletar chat.");
            }
        },
        error: function(error) {
            console.error("Erro ao deletar chat:", error);
            alert("Erro ao deletar chat. Verifique o console para mais detalhes.");
        }
    });
}

// Restaura a seção selecionada ao carregar a página e verifica a conversa
document.addEventListener('DOMContentLoaded', function () {
    restoreSelectedSection();
    checkForCompletion();
    smoothScrollToEnd();
});