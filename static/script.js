const getCSRFToken = () => {    // Retrieves CSRF token from page (Django default)
    const tokenEl = document.querySelector('[name=csrfmiddlewaretoken]');
    return tokenEl ? tokenEl.value : '';
};

// Creates HTML for user message
const generateUserMessage = (message) => `  
    <div class="message-block message-user">
        <div class="message-component message-head">
            <span class="message-source">Du</span>
            <span class="message-timestamp">${new Date().toLocaleString()}</span>
        </div>
        <div class="message-component message-content">${message}</div>
    </div>
`;

// Use as a placeholder until the backend response arrives
const generateAiMessage = (id) => `
    <div class="message-block message-assistant ai-temp" id="ai-temp-${id}">
        <div class="message-component message-head">
            <span class="message-source">Lexicompis</span>
            <span class="message-timestamp">${new Date().toLocaleString()}</span>
        </div>
        <div class="message-component message-content">
            <em>Jag funderar och formulerar ett svar till dig...</em>
        </div>
    </div>
`;

document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById("conversation-sidebar");
    const toggleBtn = document.getElementById("toggle-sidebar");

    const messageForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const messageContainer = document.getElementById('chat-container');
    const sendButton = document.getElementById('send-button');
    const conversationList = document.getElementById("conversation-list");
    const questionContainer = document.getElementById('question-container');
    const newConversationBtn = document.getElementById("new-conversation");
    
    // states
    let currentChatId = null;
    let activeDropdown = null;


    // sidebar responsiveness
    if (window.innerWidth <= 768) {
        sidebar.classList.add('collapsed');
    }

    toggleBtn.addEventListener("click", () => {
        sidebar.classList.toggle("collapsed");
    });

    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
            sidebar.classList.remove('collapsed'); 
        } else {
            sidebar.classList.add('collapsed'); 
        }
    });

    function clearAllActiveConversations() {
        document.querySelectorAll(".conversation-item.active").forEach(c => c.classList.remove("active"));
        }

    // Scrolling the chat to the bottom
    const scrollToBottom = () => {
        if (messageContainer) messageContainer.scrollTop = messageContainer.scrollHeight;
    };

    // Remove HTML taggs
    function stripHtml(html) {
        const div = document.createElement('div');
        div.innerHTML = html;
        return div.textContent || div.innerText || "";
    }

    // Scrolls the selected conversation 
    function scrollConversationIntoView(li) {
        li.scrollIntoView({
            behavior: "smooth",
            behavior: "auto",
            block: "nearest"
        });
    }

    // Retrieves and renders the user's conversations
    async function loadConversations(autoLoadLatest = true) {
        if (!conversationList) return;
        const response = await fetch("/chat/get_user_conversations/");
        const data = await response.json();
        conversationList.innerHTML = "";

        // order by latest
        data.conversations.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));

        data.conversations.forEach((conv, index) => {
            const li = document.createElement("li");
            li.className = "conversation-item";
            li.dataset.chatId = conv.id;

            // Dropdown menu
            const menuHtml = `
                <button class="menu-btn" aria-label="Öppna meny">⋮</button>
                <div class="menu-dropdown hidden">
                    ${window.IS_AUTHENTICATED ? `<button class="archive-btn" data-chat-id="${conv.id}">Arkivera</button>` : ''}
                    <button class="delete-btn" data-chat-id="${conv.id}">Radera</button>
                </div>
            `;

            
            li.innerHTML = `
                <span class="conversation-title">
                    ${conv.last_message ? stripHtml(conv.last_message).substring(0, 50) + "…" : "Ny konversation"}
                </span>
                ${menuHtml}
            `;

            // Mark first as active
            if (index === 0 && autoLoadLatest) {
                li.classList.add("active");
            }

            li.addEventListener("click", (e) => {
                if (e.target.closest(".menu-btn") || e.target.closest(".menu-dropdown")) {
                    return;
                }

                if (currentChatId === conv.id) return;

                currentChatId = conv.id;
                loadConversation(conv.id);
                
                clearAllActiveConversations();
                li.classList.add("active");
            });

            conversationList.appendChild(li);
        });

        // Autoload latest conversation
        if (autoLoadLatest && data.conversations.length > 0) {
            currentChatId = data.conversations[0].id;
            loadConversation(currentChatId);
        }

        // show pre defined questions if no converastion exists
        if (data.conversations.length === 0 && questionContainer) {
            questionContainer.classList.remove('hidden');
            questionContainer.classList.add('visible');
        } else if (questionContainer) {
            questionContainer.classList.add('hidden');
            questionContainer.classList.remove('visible');
        }

    }

    // Retrieving archived conversations
    const loadArchivedConversations = async () => {
        const archivedList = document.getElementById("archived-list");
        if (!archivedList || !window.IS_AUTHENTICATED) return;

        const response = await fetch("/chat/get_archived_conversations/");
        const data = await response.json();

        archivedList.innerHTML = "";

        data.conversations.forEach(conv => {

            const li = document.createElement("li");
            li.className = "conversation-item archived";
            li.dataset.chatId = conv.id;

            const menuHtml = `
                <button class="menu-btn" aria-label="Öppna meny">⋮</button>
                <div class="menu-dropdown hidden">
                    <button class="unarchive-btn" data-chat-id="${conv.id}">Återaktivera</button>
                    <button class="delete-btn" data-chat-id="${conv.id}">Radera</button>
                </div>
            `;
            li.innerHTML = `
                <span class="conversation-title">
                    ${conv.last_message ? stripHtml(conv.last_message).substring(0, 50) + "…" : "Ny konversation"}
                </span>
                ${menuHtml}
            `;
                li.addEventListener("click", (e) => {
                if (e.target.closest(".menu-btn") || e.target.closest(".menu-dropdown")) return;

                if (currentChatId === conv.id) return;

                currentChatId = conv.id;
                loadConversation(conv.id);

                
                clearAllActiveConversations();
                li.classList.add("active");
            });

            archivedList.appendChild(li);
        });
    };
    
    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".menu-btn");

        if (!btn) {
            if (activeDropdown) {
                activeDropdown.classList.remove("show");
                activeDropdown.remove();
                activeDropdown = null;
            }
            return;
        }

        e.stopPropagation();

        const item = btn.closest(".conversation-item");
        const originalDropdown = item.querySelector(".menu-dropdown");

        if (activeDropdown && activeDropdown.dataset.chatId === item.dataset.chatId) {
            activeDropdown.classList.toggle("show");

            if (!activeDropdown.classList.contains("show")) {
                activeDropdown.remove();
                activeDropdown = null;
            }

            return;
        }
        
        if (activeDropdown) {
            activeDropdown.remove();
            activeDropdown = null;
        }

        const clone = originalDropdown.cloneNode(true);
        clone.classList.remove("hidden");
        clone.classList.add("show");
        clone.dataset.chatId = item.dataset.chatId; 

        document.body.appendChild(clone);
        activeDropdown = clone;

        const btnRect = btn.getBoundingClientRect();
        const dropdownHeight = clone.offsetHeight;
        const viewportHeight = window.innerHeight;

        const spaceBelow = viewportHeight - btnRect.bottom;
        const spaceAbove = btnRect.top;

        let top;
        if (spaceBelow < dropdownHeight && spaceAbove > dropdownHeight) {
            top = btnRect.top - dropdownHeight - 6;
        } else {
            top = btnRect.bottom + 6;
        }

        clone.style.top = `${top}px`;
        clone.style.left = `${btnRect.left + btnRect.width / 2 - clone.offsetWidth / 2}px`;
    });

    document.addEventListener("click", async (e) => {
        const archiveBtn = e.target.closest(".archive-btn");
        const deleteBtn = e.target.closest(".delete-btn");
        const unarchiveBtn = e.target.closest(".unarchive-btn");

        if (!archiveBtn && !unarchiveBtn && !deleteBtn) return;

        e.stopPropagation();

        const chatId = archiveBtn?.dataset.chatId || unarchiveBtn?.dataset.chatId || deleteBtn?.dataset.chatId;
        const csrfToken = getCSRFToken();

        if (deleteBtn) {
            const confirmed = confirm("Vill du verkligen radera konversationen?");
            if (!confirmed) return;

            await fetch(`/chat/${chatId}/delete/`, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken,
                    "X-Requested-With": "XMLHttpRequest"
                },
                credentials: "same-origin"
            });
        }

        if (archiveBtn) {
            await fetch(`/chat/${chatId}/archive/`, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken,
                    "X-Requested-With": "XMLHttpRequest"
                },
                credentials: "same-origin"
            });
        }
        if (unarchiveBtn) {
            await fetch(`/chat/${chatId}/unarchive/`, {
                method: "POST",
                headers: {"X-CSRFToken": csrfToken, "X-Requested-With": "XMLHttpRequest"},
                credentials: "same-origin"
            });
        }
        
        if (currentChatId === chatId) {
            currentChatId = null;
            messageContainer.innerHTML = "";
        }

        loadConversations(true);
        loadArchivedConversations();
    });

    // Loading messages for a specific conversation
    async function loadConversation(chatId) {
        if (!messageContainer || !messageForm) return;
        messageForm.action = `/chat/${chatId}/`;
        messageContainer.innerHTML = '';

        try {
            const response = await fetch(`/chat/${chatId}/messages/`);
            const data = await response.json();

            data.messages.forEach(msg => {
                if (msg.user === "user") {
                    messageContainer.insertAdjacentHTML('beforeend', generateUserMessage(msg.message));
                } else {
                    messageContainer.insertAdjacentHTML('beforeend', `
                        <div class="message-block message-assistant">
                            <div class="message-component message-head">
                                <span class="message-source">Lexicompis</span>
                                <span class="message-timestamp">${msg.created_at}</span>
                            </div>
                            <div class="message-component message-content">
                                ${msg.message}
                            </div>
                        </div>
                    `);
                }
            });

            // If archived – can't write in the conversation
            if (data.is_archived) {
                messageForm.style.display = 'none';
                questionContainer?.classList.add('hidden');
            } else {
                messageForm.style.display = 'flex';
            }
        } catch (err) {
            console.error("Kunde inte ladda konversation:", err);
        }
    }

    if (newConversationBtn) {
        newConversationBtn.addEventListener('click', () => {
            currentChatId = null;
            messageForm.action = `/chat/`;
            messageContainer.innerHTML = '';

            if (questionContainer) {
                questionContainer.classList.remove('hidden');
                questionContainer.style.opacity = "1";
                questionContainer.querySelectorAll('button.question').forEach(btn => btn.disabled = false);
            }

            messageInput.value = '';
            messageInput.focus();
            scrollToBottom();
        });
    }

    //  Send message
    const submitMessage = async () => {
        if (sendButton.disabled) return;
        if (messageForm.style.display === 'none') return;
        
        const message = messageInput?.value.trim();
        if (!message) return;

        sendButton.disabled = true;
        messageInput.disabled = true;

        const questionButtons = document.querySelectorAll(".question");
        questionButtons.forEach(btn => btn.disabled = true);

        const uniqueId = `${currentChatId}-${crypto.randomUUID()}`;

        if (messageContainer) {
            messageContainer.classList.remove('hidden');
            messageContainer.insertAdjacentHTML('beforeend', generateUserMessage(message));
            messageContainer.insertAdjacentHTML('beforeend', generateAiMessage(uniqueId));
            scrollToBottom();
        }

        if (questionContainer) {
            questionContainer.style.opacity = "0";
            setTimeout(() => questionContainer.classList.add('hidden'), 150);
        }

        const formData = new FormData(messageForm);
        formData.append('csrfmiddlewaretoken', getCSRFToken());
        formData.append('message', message);

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000);

        try {
            const response = await fetch(messageForm.action, {
                method: messageForm.method,
                body: formData,
                headers: { "X-Requested-With": "XMLHttpRequest" },
                credentials: 'same-origin',
                signal: controller.signal
            });

            clearTimeout(timeoutId);
            const data = await response.json();

            if (!currentChatId && data.chat_id) {
                currentChatId = data.chat_id;
                messageForm.action = `/chat/${currentChatId}/`;

                loadConversations(false);
            }

            // Replaces the placeholder with a real awnser
            const aiPlaceholder = document.getElementById(`ai-temp-${uniqueId}`);
            if (aiPlaceholder) {
                aiPlaceholder.outerHTML = `
                    <div class="message-block message-assistant">
                        <div class="message-component message-head">
                            <span class="message-source">Lexicompis</span>
                            <span class="message-timestamp">${data.ai_message.created_at}</span>
                        </div>
                        <div class="message-component message-content">
                            ${data.ai_message.content}
                        </div>
                    </div>
                `;
                scrollToBottom();
            }
            if (conversationList && currentChatId) {
                const li = conversationList.querySelector(`li[data-chat-id='${currentChatId}']`);
                if (li) {
                    conversationList.prepend(li);
                    clearAllActiveConversations(); 
                    li.classList.add("active");
                    scrollConversationIntoView(li); 
                }
            }
        } catch (error) {
            console.error("Fetch error:", error);
            const aiPlaceholder = document.getElementById(`ai-temp-${uniqueId}`);
            if (aiPlaceholder) aiPlaceholder.innerHTML = "Något gick fel med AI-svaret. Försök igen.";
        } finally {
            sendButton.disabled = false;
            messageInput.disabled = false;
            questionButtons.forEach(btn => btn.disabled = false);
            if (messageInput) messageInput.value = '';
            scrollToBottom();
            setTimeout(() => messageInput?.focus(), 0);
        }
    };

    // Limit max height for input field and resets it
    if (messageInput) {
        messageInput.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 100) + 'px';
        });

        // permit shift + enter to line break
        messageInput.addEventListener('keydown', function (e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submitMessage();
                this.style.height = 'auto';
            }
        });
    }

    // sends message via AJAX
    if (messageForm) {
        messageForm.addEventListener('submit', async e => {
            e.preventDefault();
            await submitMessage();
        });
    }

    // Pre defined questions
    document.addEventListener("click", async function(e) {
        const target = e.target;
        if (!target.classList.contains("question")) return;

        e.preventDefault();
        const questionButtons = document.querySelectorAll(".question");
        questionButtons.forEach(btn => btn.disabled = true);

        const overlay = target.closest("#question-container");
        if (overlay) {
            overlay.style.opacity = "0";
            setTimeout(() => overlay.classList.add("hidden"), 150);
        }

        messageInput.value = target.dataset.question || target.innerText;
        messageForm.action = currentChatId
            ? `/chat/${currentChatId}/`
            : `/chat/`;

        await submitMessage();
    });

    loadConversations(true);
    loadArchivedConversations();
});
