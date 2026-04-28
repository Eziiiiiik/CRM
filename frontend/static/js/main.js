const token = localStorage.getItem('token');

function updateUI() {
    const navButtons = document.getElementById('nav-buttons');
    if (!navButtons) return;

    if (token) {
        navButtons.innerHTML = `
            <a href="/profile" class="btn-glow">ПРОФИЛЬ</a>
            <a href="/clients" class="btn-glow">КЛИЕНТЫ</a>
            <span id="notification-badge" class="badge" style="display:none;">0</span>
            <button onclick="logout()" class="btn-outline">ВЫЙТИ</button>
            <a href="/chat" class="chat-nav-button">ЧАТЫ</a>
        `;
        // Инициализируем счётчик, если менеджер уведомлений ещё не запущен
        if (window.notificationManager) {
            window.notificationManager.loadUnreadCount();
        }
    } else {
        navButtons.innerHTML = `
            <button class="btn-glow" onclick="openLoginModal()">ВОЙТИ</button>
            <a href="/register" class="btn-primary">РЕГИСТРАЦИЯ</a>
            <a href="/chat" class="chat-nav-button">ЧАТЫ</a>
        `;
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user_id');
    window.location.href = '/';
}

updateUI();