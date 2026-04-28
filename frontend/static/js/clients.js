/**
 * clients.js — CRUD-операции для клиентов на странице /clients.
 * Использует глобальные fetchWithAuth и showToast.
 * Ожидает: #clients-page, форму #client-form и таблицу #clients-table tbody.
 */

class ClientsManager {
    constructor() {
        this.clients = [];
        this.currentEditId = null;
        this.form = document.getElementById('client-form');
        this.tableBody = document.querySelector('#clients-table tbody');
        this.cancelEditBtn = document.getElementById('cancel-edit');
        if (this.form && this.tableBody) {
            this.init();
        } else {
            console.warn('ClientsManager: form or table not found');
        }
    }

    init() {
        this.loadClients();
        this.form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        this.cancelEditBtn?.addEventListener('click', () => this.resetForm());
    }

    async loadClients() {
        try {
            this.clients = await window.fetchWithAuth('/clients');
            this.renderTable();
        } catch (error) {
            // ошибка показана через handleApiError
        }
    }

    renderTable() {
        this.tableBody.innerHTML = '';
        this.clients.forEach(client => {
            const row = document.createElement('tr');
            row.dataset.id = client.id;
            row.innerHTML = `
                <td>${this.escapeHtml(client.first_name)}</td>
                <td>${this.escapeHtml(client.last_name)}</td>
                <td>${this.escapeHtml(client.email)}</td>
                <td>${this.escapeHtml(client.phone)}</td>
                <td>${this.escapeHtml(client.company || '')}</td>
                <td class="actions">
                    <button class="btn-edit" data-id="${client.id}">✏️</button>
                    <button class="btn-delete" data-id="${client.id}">🗑️</button>
                </td>
            `;
            this.tableBody.appendChild(row);
        });

        // Навешиваем обработчики на кнопки
        this.tableBody.querySelectorAll('.btn-edit').forEach(btn =>
            btn.addEventListener('click', (e) => this.editClient(e.target.dataset.id))
        );
        this.tableBody.querySelectorAll('.btn-delete').forEach(btn =>
            btn.addEventListener('click', (e) => this.deleteClient(e.target.dataset.id))
        );
    }

    async handleFormSubmit(e) {
        e.preventDefault();
        const formData = new FormData(this.form);
        const clientData = {
            first_name: formData.get('first_name'),
            last_name: formData.get('last_name'),
            email: formData.get('email'),
            phone: formData.get('phone'),
            company: formData.get('company')
        };

        try {
            if (this.currentEditId) {
                await window.fetchWithAuth(`/clients/${this.currentEditId}`, {
                    method: 'PUT',
                    body: JSON.stringify(clientData)
                });
                window.showToast('Клиент обновлён', 'success');
            } else {
                await window.fetchWithAuth('/clients', {
                    method: 'POST',
                    body: JSON.stringify(clientData)
                });
                window.showToast('Клиент добавлен', 'success');
            }
            this.resetForm();
            this.loadClients();
        } catch (error) {
            // Ошибка уже показана
        }
    }

    editClient(id) {
        const client = this.clients.find(c => c.id == id);
        if (!client) return;

        this.currentEditId = id;
        document.getElementById('first_name').value = client.first_name || '';
        document.getElementById('last_name').value = client.last_name || '';
        document.getElementById('email').value = client.email || '';
        document.getElementById('phone').value = client.phone || '';
        document.getElementById('company').value = client.company || '';

        document.getElementById('form-title').textContent = 'Редактировать клиента';
        document.getElementById('submit-btn').textContent = 'Сохранить';
        this.cancelEditBtn.style.display = 'inline-block';
    }

    async deleteClient(id) {
        if (!confirm('Вы уверены, что хотите удалить клиента?')) return;
        try {
            await window.fetchWithAuth(`/clients/${id}`, { method: 'DELETE' });
            window.showToast('Клиент удалён', 'success');
            this.loadClients();
        } catch (error) {
            // ошибка показана
        }
    }

    resetForm() {
        this.form.reset();
        this.currentEditId = null;
        document.getElementById('form-title').textContent = 'Добавить клиента';
        document.getElementById('submit-btn').textContent = 'Добавить';
        this.cancelEditBtn.style.display = 'none';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
}

// Инициализация только на странице клиентов
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('clients-page')) {
        window.clientsManager = new ClientsManager();
    }
});