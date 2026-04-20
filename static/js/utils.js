export const getCSRFToken = () => {
    const tokenEl = document.querySelector('[name=csrfmiddlewaretoken]');
    return tokenEl ? tokenEl.value : '';
};

export const escapeHtml = (value = '') => {
    const div = document.createElement('div');
    div.textContent = value;
    return div.innerHTML;
};

export const stripHtml = (html = '') => {
    const div = document.createElement('div');
    div.innerHTML = html;
    return div.textContent || div.innerText || '';
};

export const truncateText = (text = '', maxLength = 50) => {
    if (text.length <= maxLength) return text;
    return `${text.substring(0, maxLength)}…`;
};

export const formatNow = () => new Date().toLocaleString();

export const scrollToBottom = (element) => {
    if (!element) return;
    element.scrollTop = element.scrollHeight;
};

export const scrollConversationIntoView = (element) => {
    if (!element) return;
    element.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest'
    });
};