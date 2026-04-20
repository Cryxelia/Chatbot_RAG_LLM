const getCSRFToken = () => {
  return document.querySelector('[name=csrfmiddlewaretoken]').value;
};

const generateUserMessage = (message)=> ` 
    <div class="message-block message-user">
      <div class="message-component message-head ">
        <p class="message-source">Du</p>
        <p class="message-timestamp">${new Date().toLocaleString()}</p>
      </div>
      <p class="message-component message-content">${message}</p>
    </div>
  `;

const generateAiMessage = (id) => `
  <p class="ai-temp" id="ai-temp-${id}">
    <em>Jag funderar och formulerar ett svar till dig...</em>
  </p>
`;


document.addEventListener('DOMContentLoaded', function () {
  const messageForm = document.getElementById('chat-form');
  const messageInput = document.getElementById('message-input');
  const questionOptions = document.getElementsByClassName('question');
  const messageContainer = document.getElementById('chat-container');
  const questionContainer = document.getElementById('question-container');
  const sendButton = document.getElementById('send-button');

  if (messageContainer && messageContainer.lastElementChild) {
    messageContainer.lastElementChild.scrollIntoView({ behavior: 'auto' });
  }

  const submitMessage = async () => {
    const message = messageInput.value.trim();
    if (!message) return;

    sendButton.disabled = true;
    messageInput.disabled = true;
    if (questionContainer) {
      questionContainer.classList.add('hidden');
    }

    const uniqueId = crypto.randomUUID();

    messageContainer.classList.remove('hidden');

    const formData = new FormData(messageForm);
    formData.append('csrfmiddlewaretoken', getCSRFToken());
    formData.append('message', message);

    messageContainer.insertAdjacentHTML('beforeend', generateUserMessage(message));
    messageContainer.insertAdjacentHTML('beforeend', generateAiMessage(uniqueId));
    messageContainer.scrollTop = messageContainer.scrollHeight;
    messageInput.value = '';

    document.getElementById('chat-page-num').value = 2;
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 20000);

      const response = await fetch(messageForm.action, {
        method: messageForm.method,
        body: formData,
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: 'same-origin',
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.redirected) {
        window.location.href = response.url;
        return;
      }
      const data = await response.json();

      const aiPlaceholder = document.getElementById(`ai-temp-${uniqueId}`);
      if (aiPlaceholder) {
        aiPlaceholder.outerHTML = `
          <div class="message-block message-assistant">
            <div class="message-component message-head">
              <p class="message-source">Lexicompis</p>
              <p class="message-timestamp">${data.ai_message.created_at}</p>
            </div>
            <div class="message-component message-content">
              ${data.ai_message.content}
            </div>
          </div>
        `;
        messageContainer.scrollTop = messageContainer.scrollHeight;
      }
    } catch (error) {
      console.error("Fetch error:", error);
      const aiPlaceholder = document.getElementById(`ai-temp-${uniqueId}`);
      if (aiPlaceholder) {
        aiPlaceholder.innerHTML = "Något gick fel med AI-svaret. Försök igen.";
      }
    } finally {
      sendButton.disabled = false;
      messageInput.disabled = false;
      messageContainer.scrollTop = messageContainer.scrollHeight;
    }
  };

  messageForm.addEventListener('submit', async e => {
    e.preventDefault();
    await submitMessage();
  });

  Array.from(questionOptions).forEach(option => {
    option.addEventListener('click', async e => {
      e.preventDefault();
      messageInput.value = option.innerText;
      await submitMessage();
    });
  });
  window.addEventListener("beforeunload", function() { 
    const params = new URLSearchParams();
    params.append("csrfmiddlewaretoken", getCSRFToken());
    navigator.sendBeacon(`/chat/${currentChatId}/clear_history/`, params);
  });
});



