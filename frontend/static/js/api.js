/**
 * api.js — единая утилита для взаимодействия с API.
 * Все запросы автоматически подставляют JWT-токен из localStorage.
 * Экспортирует глобальные функции: fetchWithAuth, handleApiError, connectWebSocket.
 */

const API_BASE = '/api/v1';

/**
 * Возвращает JWT-токен из localStorage.
 * @returns {string|null}
 */
function getToken() {
    return localStorage.getItem('token');
}

/**
 * Обёртка над fetch с автоматической авторизацией.
 * @param {string} url — путь относительно /api/v1 (например, '/clients')
 * @param {object} options — стандартные опции fetch (метод, тело и т.д.)
 * @returns {Promise<any>}
 */
async function fetchWithAuth(url, options = {}) {
    const token = getToken();
    if (!token) {
        // Если токена нет, просто делаем обычный запрос (для публичных эндпоинтов)
        // или пробрасываем ошибку при необходимости
        // В нашем случае почти все запросы требуют токен, поэтому ошибка.
        throw new Error('Токен авторизации не найден');
    }

    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
        'Authorization': `Bearer ${token}`
    };

    const fullUrl = url.startsWith('http') ? url : `${window.location.origin}${API_BASE}${url}`;

    try {
        const response = await fetch(fullUrl, { ...options, headers });

        if (response.status === 401) {
            // Токен истёк или невалиден — разлогиниваем
            localStorage.removeItem('token');
            localStorage.removeItem('user_id');
            window.location.href = '/login';
            throw new Error('Сессия истекла. Пожалуйста, войдите снова.');
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            const message = errorData?.detail || `Ошибка HTTP ${response.status}`;
            throw new Error(message);
        }

        if (response.status === 204) return null; // No Content
        return await response.json();
    } catch (error) {
        handleApiError(error);
        throw error; // пробрасываем дальше, если вызывающий код хочет обработать
    }
}

/**
 * Стандартная обработка ошибок API – логирование + toast (если доступен).
 * @param {Error} error
 */
function handleApiError(error) {
    console.error('API Error:', error);
    if (window.showToast) {
        window.showToast(error.message, 'error');
    } else {
        alert(error.message);
    }
}

/**
 * Управление WebSocket-соединением с автоматическим переподключением.
 * @param {number|string} userId - идентификатор пользователя
 * @param {function} onMessageCallback - колбэк при получении сообщения (данные JSON)
 * @returns {{ close: function }} объект с методом close для ручного закрытия
 */
function connectWebSocket(userId, onMessageCallback) {
    if (!userId) {
        console.error('connectWebSocket: userId не указан');
        return { close: () => {} };
    }

    // Можно использовать переменную окружения или фиксированный адрес
    const WS_URL = `ws://localhost:8000/ws/${userId}`;
    let ws = null;
    let reconnectAttempts = 0;
    const maxAttempts = 10;
    const delay = 3000;

    function connect() {
        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            console.log('WebSocket подключён');
            reconnectAttempts = 0;
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                onMessageCallback(data);
            } catch (e) {
                console.error('Ошибка парсинга WebSocket-сообщения', e);
            }
        };

        ws.onclose = (event) => {
            console.warn('WebSocket закрыт:', event.reason);
            if (reconnectAttempts < maxAttempts) {
                reconnectAttempts++;
                console.log(`Повторное подключение через ${delay}ms (попытка ${reconnectAttempts})`);
                setTimeout(connect, delay);
            } else {
                console.error('Достигнут лимит попыток переподключения WebSocket');
            }
        };

        ws.onerror = (err) => {
            console.error('WebSocket ошибка:', err);
            // Закрытие вызовет onclose и запустит переподключение
        };
    }

    connect();

    return {
        close: () => {
            if (ws) ws.close();
        }
    };
}

// Глобальное экспонирование
window.fetchWithAuth = fetchWithAuth;
window.handleApiError = handleApiError;
window.connectWebSocket = connectWebSocket;