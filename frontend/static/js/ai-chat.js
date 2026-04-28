/**
 * ai-chat.js — интеграция AI-ассистента в страницу /chat.
 * Ожидает элементы: #chat-messages, #chat-input, #send-btn.
 * Отправляет сообщения на POST /api/v1/ai/ask через fetchWithAuth.
 */

class AIChat {
    constructor() {
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.sendButton = document.getElementById('send-btn');
        this.typingElement = null;
        this.userId = localStorage.getItem('user_id');
        this.init();
    }

    init() {
        if (!this.chatMessages || !this.chatInput) {
            console.warn('AI Chat: необходимые элементы не найдены на странице.');
            return;
        }

        this.sendButton?.addEventListener('click', () => this.sendMessage());
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message) return;
        if (!this.userId) {
            window.showToast('Необходимо авторизоваться', 'error');
            return;
        }

        // Сообщение пользователя
        this.addMessage('user', message);
        this.chatInput.value = '';

        // Показать индикатор печатания
        this.showTyping();

        try {
            const data = await window.fetchWithAuth('/ai/ask', {
                method: 'POST',
                body: JSON.stringify({ message, user_id: this.userId })
            });
            this.removeTyping();
            const responseText = data.response || data.message || 'Пустой ответ';
            this.addMessage('ai', responseText);
        } catch (error) {
            this.removeTyping();
            this.addMessage('ai', `Ошибка: ${error.message}`, 'error');
        }
    }

    /**
     * Добавляет сообщение в чат.
     * @param {'user'|'ai'} sender
     * @param {string} text
     * @param {string} [extraClass] - дополнительный CSS-класс ('error')
     */
    addMessage(sender, text, extraClass = '') {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', `message-${sender}`);
        if (extraClass) msgDiv.classList.add(`message-${extraClass}`);
        msgDiv.innerHTML = `<div class="message-content">${this.escapeHtml(text)}</div>`;
        this.chatMessages.appendChild(msgDiv);
        this.scrollToBottom();
    }

    showTyping() {
        if (this.typingElement) return;
        this.typingElement = document.createElement('div');
        this.typingElement.classList.add('message', 'message-ai', 'typing-indicator');
        this.typingElement.innerHTML = `
            <div class="typing-dots">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
            </div>
        `;
        this.chatMessages.appendChild(this.typingElement);
        this.scrollToBottom();
    }

    removeTyping() {
        if (this.typingElement?.parentNode) {
            this.typingElement.remove();
            this.typingElement = null;
        }
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
}

// Инициализация только на странице чата
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('chat-messages')) {
        window.aiChat = new AIChat();
    }
});