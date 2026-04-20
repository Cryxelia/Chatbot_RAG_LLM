import { getCSRFToken } from './utils.js';

const defaultHeaders = {
    'X-Requested-With': 'XMLHttpRequest'
};

export const fetchJson = async (url, options = {}) => {
    const response = await fetch(url, {
        credentials: 'same-origin',
        ...options,
        headers: {
            ...defaultHeaders,
            ...(options.headers || {})
        }
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }

    return response.json();
};

export const getUserConversations = () => fetchJson('/chat/get_user_conversations/');

export const getArchivedConversations = () => fetchJson('/chat/get_archived_conversations/');

export const getConversationMessages = (chatId) =>
    fetchJson(`/chat/${chatId}/messages/`);

export const archiveConversation = (chatId) =>
    fetchJson(`/chat/${chatId}/archive/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken()
        }
    });

export const unarchiveConversation = (chatId) =>
    fetchJson(`/chat/${chatId}/unarchive/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken()
        }
    });

export const deleteConversation = (chatId) =>
    fetchJson(`/chat/${chatId}/delete/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken()
        }
    });

export const sendMessage = async (url, method, formData, signal) => {
    return fetchJson(url, {
        method,
        body: formData,
        signal
    });
};