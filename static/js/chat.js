import { getConversationMessages, sendMessage as sendMessageRequest } from './api.js';
import { renderAiMessage, renderAiPlaceholder, renderUserMessage } from './render.js';
import { getCSRFToken, scrollToBottom } from './utils.js';
import { moveConversationToTop } from './sidebar.js';

export const loadConversation = async ({ dom, state, chatId }) => {
    const { messageContainer, messageForm, questionContainer } = dom;
    if (!messageContainer || !messageForm) return;

    messageForm.action = `/chat/${chatId}/`;
    messageContainer.innerHTML = '';

    try {
        const data = await getConversationMessages(chatId);

        data.messages.forEach((msg) => {
            if (msg.user === 'user') {
                messageContainer.insertAdjacentHTML('beforeend', renderUserMessage(msg.message));
            } else {
                messageContainer.insertAdjacentHTML(
                    'beforeend',
                    renderAiMessage(msg.message, msg.created_at)
                );
            }
        });

        if (data.is_archived) {
            messageForm.style.display = 'none';
            questionContainer?.classList.add('hidden');
        } else {
            messageForm.style.display = 'flex';
        }

        scrollToBottom(messageContainer);
    } catch (error) {
        console.error('Kunde inte ladda konversation:', error);
    }
};

export const resetToNewConversation = ({ dom, state }) => {
    const { messageForm, messageContainer, questionContainer, messageInput } = dom;

    state.currentChatId = null;
    messageForm.action = '/chat/';
    messageContainer.innerHTML = '';

    if (questionContainer) {
        questionContainer.classList.remove('hidden');
        questionContainer.style.opacity = '1';
        questionContainer.querySelectorAll('button.question').forEach((btn) => {
            btn.disabled = false;
        });
    }

    messageInput.value = '';
    messageInput.focus();
    scrollToBottom(messageContainer);
};

export const submitMessage = async ({ dom, state, refreshConversations }) => {
    const { sendButton, messageForm, messageInput, messageContainer, questionContainer, conversationList } = dom;

    if (sendButton.disabled) return;
    if (messageForm.style.display === 'none') return;

    const message = messageInput?.value.trim();
    if (!message) return;

    sendButton.disabled = true;
    messageInput.disabled = true;

    const questionButtons = document.querySelectorAll('.question');
    questionButtons.forEach((btn) => (btn.disabled = true));

    const uniqueId = `${state.currentChatId || 'new'}-${crypto.randomUUID()}`;

    if (messageContainer) {
        messageContainer.classList.remove('hidden');
        messageContainer.insertAdjacentHTML('beforeend', renderUserMessage(message));
        messageContainer.insertAdjacentHTML('beforeend', renderAiPlaceholder(uniqueId));
        scrollToBottom(messageContainer);
    }

    if (questionContainer) {
        questionContainer.style.opacity = '0';
        setTimeout(() => questionContainer.classList.add('hidden'), 150);
    }

    const formData = new FormData(messageForm);
    formData.set('csrfmiddlewaretoken', getCSRFToken());
    formData.set('message', message);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);

    try {
        const data = await sendMessageRequest(
            messageForm.action,
            messageForm.method,
            formData,
            controller.signal
        );

        clearTimeout(timeoutId);

        if (!state.currentChatId && data.chat_id) {
            state.currentChatId = data.chat_id;
            messageForm.action = `/chat/${state.currentChatId}/`;
            await refreshConversations(false);
        }

        const aiPlaceholder = document.getElementById(`ai-temp-${uniqueId}`);
        if (aiPlaceholder) {
            aiPlaceholder.outerHTML = renderAiMessage(
                data.ai_message.content,
                data.ai_message.created_at
            );
        }

        if (conversationList && state.currentChatId) {
            moveConversationToTop({ dom, state });
        }
    } catch (error) {
        console.error('Fetch error:', error);
        const aiPlaceholder = document.getElementById(`ai-temp-${uniqueId}`);
        if (aiPlaceholder) {
            aiPlaceholder.innerHTML = 'Något gick fel med AI-svaret. Försök igen.';
        }
    } finally {
        clearTimeout(timeoutId);
        sendButton.disabled = false;
        messageInput.disabled = false;
        questionButtons.forEach((btn) => (btn.disabled = false));
        messageInput.value = '';
        scrollToBottom(messageContainer);
        setTimeout(() => messageInput?.focus(), 0);
    }
};