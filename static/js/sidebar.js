import { renderConversationItem } from './render.js';
import { scrollConversationIntoView } from './utils.js';
import {
    getUserConversations,
    getArchivedConversations,
    archiveConversation,
    unarchiveConversation,
    deleteConversation
} from './api.js';

export const initSidebarResponsiveness = (dom) => {
    const { sidebar, toggleBtn } = dom;
    if (!sidebar || !toggleBtn) return;

    if (window.innerWidth <= 768) {
        sidebar.classList.add('collapsed');
    }

    toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
    });

    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
            sidebar.classList.remove('collapsed');
        } else {
            sidebar.classList.add('collapsed');
        }
    });
};

export const clearActiveConversation = () => {
    document
        .querySelectorAll('.conversation-item.active')
        .forEach((item) => item.classList.remove('active'));
};

export const loadConversations = async ({ dom, state, onConversationSelect, autoLoadLatest = true }) => {
    const { conversationList, questionContainer } = dom;
    if (!conversationList) return;

    const data = await getUserConversations();
    conversationList.innerHTML = '';

    data.conversations.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));

    data.conversations.forEach((conv, index) => {
        const li = document.createElement('li');
        li.className = 'conversation-item';
        li.dataset.chatId = conv.id;
        li.innerHTML = renderConversationItem(conv, window.APP_CONFIG?.isAuthenticated, false);

        if (index === 0 && autoLoadLatest) {
            li.classList.add('active');
        }

        li.addEventListener('click', (e) => {
            if (e.target.closest('.menu-btn') || e.target.closest('.menu-dropdown')) return;
            if (state.currentChatId === conv.id) return;

            state.currentChatId = conv.id;
            clearActiveConversation();
            li.classList.add('active');
            onConversationSelect(conv.id);
        });

        conversationList.appendChild(li);
    });

    if (autoLoadLatest && data.conversations.length > 0) {
        state.currentChatId = data.conversations[0].id;
        onConversationSelect(state.currentChatId);
    }

    if (questionContainer) {
        if (data.conversations.length === 0) {
            questionContainer.classList.remove('hidden');
            questionContainer.classList.add('visible');
        } else {
            questionContainer.classList.add('hidden');
            questionContainer.classList.remove('visible');
        }
    }
};

export const loadArchivedConversationsList = async ({ dom, state, onConversationSelect }) => {
    const { archivedList } = dom;
    if (!archivedList || !window.APP_CONFIG?.isAuthenticated) return;

    const data = await getArchivedConversations();
    archivedList.innerHTML = '';

    data.conversations.forEach((conv) => {
        const li = document.createElement('li');
        li.className = 'conversation-item archived';
        li.dataset.chatId = conv.id;
        li.innerHTML = renderConversationItem(conv, true, true);

        li.addEventListener('click', (e) => {
            if (e.target.closest('.menu-btn') || e.target.closest('.menu-dropdown')) return;
            if (state.currentChatId === conv.id) return;

            state.currentChatId = conv.id;
            clearActiveConversation();
            li.classList.add('active');
            onConversationSelect(conv.id);
        });

        archivedList.appendChild(li);
    });
};

export const initDropdownMenu = ({ state, dom, refreshLists }) => {
    document.addEventListener('click', async (e) => {
        const btn = e.target.closest('.menu-btn');

        if (!btn) {
            if (state.activeDropdown) {
                state.activeDropdown.remove();
                state.activeDropdown = null;
            }
            return;
        }

        e.stopPropagation();

        const item = btn.closest('.conversation-item');
        const originalDropdown = item.querySelector('.menu-dropdown');

        if (state.activeDropdown && state.activeDropdown.dataset.chatId === item.dataset.chatId) {
            state.activeDropdown.classList.toggle('show');

            if (!state.activeDropdown.classList.contains('show')) {
                state.activeDropdown.remove();
                state.activeDropdown = null;
            }
            return;
        }

        if (state.activeDropdown) {
            state.activeDropdown.remove();
            state.activeDropdown = null;
        }

        const clone = originalDropdown.cloneNode(true);
        clone.classList.remove('hidden');
        clone.classList.add('show');
        clone.dataset.chatId = item.dataset.chatId;

        document.body.appendChild(clone);
        state.activeDropdown = clone;

        const btnRect = btn.getBoundingClientRect();
        const dropdownHeight = clone.offsetHeight;
        const viewportHeight = window.innerHeight;

        const spaceBelow = viewportHeight - btnRect.bottom;
        const spaceAbove = btnRect.top;

        const top =
            spaceBelow < dropdownHeight && spaceAbove > dropdownHeight
                ? btnRect.top - dropdownHeight - 6
                : btnRect.bottom + 6;

        clone.style.top = `${top}px`;
        clone.style.left = `${btnRect.left + btnRect.width / 2 - clone.offsetWidth / 2}px`;
    });

    document.addEventListener('click', async (e) => {
        const archiveBtn = e.target.closest('.archive-btn');
        const deleteBtn = e.target.closest('.delete-btn');
        const unarchiveBtn = e.target.closest('.unarchive-btn');

        if (!archiveBtn && !deleteBtn && !unarchiveBtn) return;

        e.stopPropagation();

        const chatId =
            archiveBtn?.dataset.chatId ||
            deleteBtn?.dataset.chatId ||
            unarchiveBtn?.dataset.chatId;

        if (deleteBtn) {
            const confirmed = confirm('Vill du verkligen radera konversationen?');
            if (!confirmed) return;
            await deleteConversation(chatId);
        }

        if (archiveBtn) {
            await archiveConversation(chatId);
        }

        if (unarchiveBtn) {
            await unarchiveConversation(chatId);
        }

        if (state.currentChatId === chatId) {
            state.currentChatId = null;
            if (dom.messageContainer) {
                dom.messageContainer.innerHTML = '';
            }
        }

        await refreshLists();
    });
};

export const moveConversationToTop = ({ dom, state }) => {
    const { conversationList } = dom;
    if (!conversationList || !state.currentChatId) return;

    const li = conversationList.querySelector(`li[data-chat-id='${state.currentChatId}']`);
    if (!li) return;

    conversationList.prepend(li);
    clearActiveConversation();
    li.classList.add('active');
    scrollConversationIntoView(li);
};