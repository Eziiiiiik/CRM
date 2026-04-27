const token = localStorage.getItem('token');

function updateUI() {
    const navButtons = document.getElementById('nav-buttons');
    if (!navButtons) return;
    if (token) {
        navButtons.innerHTML = `
            <a href="/profile" class="btn-glow">ПРОФИЛЬ</a>
            <button onclick="logout()" class="btn-outline">ВЫЙТИ</button>
            <a href="/chat" class="chat-nav-button">ЧАТЫ</a>
        `;
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
    window.location.href = '/';
}

// Функция открытия модального окна (определяется отдельно на каждой странице, где есть модалка)
// Функция handleLogin будет переопределена в HTML, где есть форма входа

updateUI();