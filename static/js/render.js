import { escapeHtml, formatNow, stripHtml, truncateText } from './utils.js';

export const renderUserMessage = (message) => `
    <div class="message-block message-user">
        <div class="message-component message-head">
            <span class="message-source">Du</span>
            <span class="message-timestamp">${formatNow()}</span>
        </div>
        <div class="message-component message-content">${escapeHtml(message)}</div>
    </div>
`;

export const renderAiPlaceholder = (id) => `
    <div class="message-block message-assistant ai-temp" id="ai-temp-${id}">
        <div class="message-component message-head">
            <span class="message-source">Lexicompis</span>
            <span class="message-timestamp">${formatNow()}</span>
        </div>
        <div class="message-component message-content">
            <em>Jag funderar och formulerar ett svar till dig...</em>
        </div>
    </div>
`;

export const renderAiMessage = (content, createdAt) => `
    <div class="message-block message-assistant">
        <div class="message-component message-head">
            <span class="message-source">Lexicompis</span>
            <span class="message-timestamp">${createdAt}</span>
        </div>
        <div class="message-component message-content">
            ${content}
        </div>
    </div>
`;

export const renderConversationItem = (conv, isAuthenticated, archived = false) => {
    const safeTitle = conv.last_message
        ? truncateText(stripHtml(conv.last_message), 50)
        : 'Ny konversation';

    const menuHtml = archived
        ? `
            <button class="menu-btn" aria-label="Öppna meny">⋮</button>
            <div class="menu-dropdown hidden">
                <button class="unarchive-btn" data-chat-id="${conv.id}">Återaktivera</button>
                <button class="delete-btn" data-chat-id="${conv.id}">Radera</button>
            </div>
        `
        : `
            <button class="menu-btn" aria-label="Öppna meny">⋮</button>
            <div class="menu-dropdown hidden">
                ${isAuthenticated ? `<button class="archive-btn" data-chat-id="${conv.id}">Arkivera</button>` : ''}
                <button class="delete-btn" data-chat-id="${conv.id}">Radera</button>
            </div>
        `;

    return `
        <span class="conversation-title">${safeTitle}</span>
        ${menuHtml}
    `;
};