/**
 * notifications.js — система всплывающих уведомлений (toast) и счётчика непрочитанных.
 * Подключает WebSocket для real-time уведомлений, если пользователь авторизован.
 * Использует глобальные fetchWithAuth, connectWebSocket.
 */

class NotificationManager {
    constructor() {
        this.unreadCount = 0;
        this.wsConnection = null;
    }

    /**
     * Инициализация: проверка авторизации, загрузка начального счётчика, WebSocket.
     */
    init() {
        const userId = localStorage.getItem('user_id');
        const token = localStorage.getItem('token');
        if (!userId || !token) {
            console.warn('Пользователь не авторизован — уведомления отключены');
            return;
        }

        // Подключаем WebSocket
        this.wsConnection = window.connectWebSocket(userId, (data) => {
            this.handleNewMessage(data);
        });

        // Загружаем количество непрочитанных уведомлений
        this.loadUnreadCount();
    }

    /**
     * Загружает с сервера количество непрочитанных уведомлений.
     */
    async loadUnreadCount() {
        try {
            const notifications = await window.fetchWithAuth('/notifications?unread=true');
            if (Array.isArray(notifications)) {
                this.unreadCount = notifications.length;
            } else {
                this.unreadCount = 0;
            }
            this.updateBadge();
        } catch (err) {
            console.error('Ошибка загрузки unread-счётчика:', err);
        }
    }

    /**
     * Обработка входящего WebSocket-сообщения.
     * @param {object} data — { message, type, ... }
     */
    handleNewMessage(data) {
        this.unreadCount++;
        this.updateBadge();
        this.showToast(data.message || 'Новое уведомление', data.type || 'info');
    }

    /**
     * Показывает всплывающее уведомление в углу экрана.
     * @param {string} message - текст уведомления
     * @param {string} type - 'info', 'error', 'success', 'warning'
     */
    showToast(message, type = 'info') {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-message">${this.escapeHtml(message)}</span>
            <button class="toast-close" aria-label="Закрыть">&times;</button>
        `;
        container.appendChild(toast);

        // Автоматическое удаление через 5 секунд
        const timer = setTimeout(() => {
            if (toast.parentNode) {
                toast.classList.add('toast-hiding');
                toast.addEventListener('animationend', () => {
                    if (toast.parentNode) toast.remove();
                }, { once: true });
            }
        }, 5000);

        // Кнопка закрытия
        toast.querySelector('.toast-close').addEventListener('click', () => {
            clearTimeout(timer);
            toast.remove();
        });
    }

    /**
     * Обновляет бейдж с количеством непрочитанных уведомлений в навигации.
     */
    updateBadge() {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            badge.textContent = this.unreadCount;
            badge.style.display = this.unreadCount > 0 ? 'inline-block' : 'none';
        }
    }

    /**
     * Экранирует HTML-символы для безопасной вставки.
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
}

// Глобальная функция для показа toast из любого модуля
window.showToast = (message, type) => {
    if (window.notificationManager) {
        window.notificationManager.showToast(message, type);
    } else {
        alert(`${type.toUpperCase()}: ${message}`);
    }
};

// Запуск после загрузки DOM
document.addEventListener('DOMContentLoaded', () => {
    window.notificationManager = new NotificationManager();
    window.notificationManager.init();
});