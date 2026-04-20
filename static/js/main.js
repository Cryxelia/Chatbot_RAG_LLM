import { getDomElements } from './dom.js';
import { state } from './state.js';
import {
    initSidebarResponsiveness,
    initDropdownMenu,
    loadConversations,
    loadArchivedConversationsList
} from './sidebar.js';
import {
    loadConversation,
    resetToNewConversation,
    submitMessage
} from './chat.js';

document.addEventListener('DOMContentLoaded', () => {
    const dom = getDomElements();

    const refreshConversations = async (autoLoadLatest = true) => {
        await loadConversations({
            dom,
            state,
            autoLoadLatest,
            onConversationSelect: (chatId) => loadConversation({ dom, state, chatId })
        });
    };

    const refreshArchived = async () => {
        await loadArchivedConversationsList({
            dom,
            state,
            onConversationSelect: (chatId) => loadConversation({ dom, state, chatId })
        });
    };

    const refreshLists = async () => {
        await refreshConversations(true);
        await refreshArchived();
    };

    initSidebarResponsiveness(dom);

    initDropdownMenu({
        state,
        dom,
        refreshLists
    });

    if (dom.newConversationBtn) {
        dom.newConversationBtn.addEventListener('click', () => {
            resetToNewConversation({ dom, state });
        });
    }

    if (dom.messageInput) {
        dom.messageInput.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = `${Math.min(this.scrollHeight, 100)}px`;
        });

        dom.messageInput.addEventListener('keydown', async function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                await submitMessage({
                    dom,
                    state,
                    refreshConversations
                });
                this.style.height = 'auto';
            }
        });
    }

    if (dom.messageForm) {
        dom.messageForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await submitMessage({
                dom,
                state,
                refreshConversations
            });
        });
    }

    document.addEventListener('click', async (e) => {
        const target = e.target;
        if (!target.classList.contains('question')) return;

        e.preventDefault();

        const questionButtons = document.querySelectorAll('.question');
        questionButtons.forEach((btn) => (btn.disabled = true));

        const overlay = target.closest('#question-container');
        if (overlay) {
            overlay.style.opacity = '0';
            setTimeout(() => overlay.classList.add('hidden'), 150);
        }

        dom.messageInput.value = target.dataset.question || target.innerText;
        dom.messageForm.action = state.currentChatId
            ? `/chat/${state.currentChatId}/`
            : '/chat/';

        await submitMessage({
            dom,
            state,
            refreshConversations
        });
    });

    refreshConversations(true);
    refreshArchived();
});