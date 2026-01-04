// app.js

// State
let authToken = localStorage.getItem('authToken');
let currentKeys = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    if (authToken) {
        showDashboard();
    } else {
        showLogin();
    }

    // Event listeners
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
    document.getElementById('createKeyBtn').addEventListener('click', openCreateKeyModal);
    document.getElementById('createKeyForm').addEventListener('submit', handleCreateKey);
    document.getElementById('editLimitForm').addEventListener('submit', handleEditLimit);
    document.getElementById('searchKeys').addEventListener('input', handleSearch);
});

// Authentication
async function handleLogin(e) {
    e.preventDefault();

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorEl = document.getElementById('loginError');

    try {
        const response = await fetch('/admin/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            throw new Error('Invalid credentials');
        }

        const data = await response.json();
        authToken = data.access_token;
        localStorage.setItem('authToken', authToken);

        showDashboard();
    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.classList.add('active');
    }
}

function handleLogout() {
    localStorage.removeItem('authToken');
    authToken = null;
    showLogin();
}

function showLogin() {
    document.getElementById('loginScreen').classList.add('active');
    document.getElementById('dashboardScreen').classList.remove('active');
    document.getElementById('loginForm').reset();
    document.getElementById('loginError').classList.remove('active');
}

function showDashboard() {
    document.getElementById('loginScreen').classList.remove('active');
    document.getElementById('dashboardScreen').classList.add('active');
    loadKeys();
}

// API Key Management
async function loadKeys() {
    try {
        const response = await fetch('/admin/keys', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.status === 401) {
            handleLogout();
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to load keys');
        }

        const data = await response.json();
        currentKeys = data.keys;
        renderKeys(currentKeys);
        updateStats();
    } catch (error) {
        console.error('Error loading keys:', error);
    }
}

function renderKeys(keys) {
    const tbody = document.getElementById('keysTableBody');

    if (keys.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                    No API keys found. Create your first key to get started.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = keys.map(key => `
        <tr>
            <td><strong>${escapeHtml(key.name)}</strong></td>
            <td><code class="key-preview">${escapeHtml(key.key_preview)}</code></td>
            <td>${key.rate_limit.toLocaleString()} / day</td>
            <td>${formatDate(key.created_at)}</td>
            <td>${key.last_used ? formatDate(key.last_used) : 'Never'}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-primary btn-small" onclick="viewUsage(${key.id}, '${escapeHtml(key.name)}')">
                        Usage
                    </button>
                    <button class="btn btn-secondary btn-small" onclick="editKeyLimit(${key.id}, ${key.rate_limit})">
                        Edit Limit
                    </button>
                    <button class="btn btn-danger btn-small" onclick="deleteKey(${key.id}, '${escapeHtml(key.name)}')">
                        Revoke
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function updateStats() {
    document.getElementById('totalKeys').textContent = currentKeys.length;
}

// Create Key Modal
function openCreateKeyModal() {
    document.getElementById('createKeyModal').classList.add('active');
    document.getElementById('createKeyForm').reset();
    document.getElementById('createKeyError').classList.remove('active');
}

function closeCreateKeyModal() {
    document.getElementById('createKeyModal').classList.remove('active');
}

async function handleCreateKey(e) {
    e.preventDefault();

    const name = document.getElementById('keyName').value;
    const rateLimit = parseInt(document.getElementById('rateLimit').value);
    const errorEl = document.getElementById('createKeyError');

    try {
        const response = await fetch('/admin/keys', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ name, rate_limit: rateLimit })
        });

        if (response.status === 401) {
            handleLogout();
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to create API key');
        }

        const data = await response.json();

        // Show generated key
        document.getElementById('generatedKey').textContent = data.key;
        closeCreateKeyModal();
        document.getElementById('keyGeneratedModal').classList.add('active');

        // Reload keys
        loadKeys();
    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.classList.add('active');
    }
}

function closeKeyGeneratedModal() {
    document.getElementById('keyGeneratedModal').classList.remove('active');
}

function copyGeneratedKey(event) {
    const key = document.getElementById('generatedKey').textContent;
    const btn = event.currentTarget;  // Store reference BEFORE async operation
    const originalHTML = btn.innerHTML;

    navigator.clipboard.writeText(key).then(() => {
        btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg> Copied!';
        setTimeout(() => {
            btn.innerHTML = originalHTML;
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy to clipboard');
    });
}

// Edit Key Limit Modal
function editKeyLimit(keyId, currentLimit) {
    document.getElementById('editKeyId').value = keyId;
    document.getElementById('newRateLimit').value = currentLimit;
    document.getElementById('editLimitModal').classList.add('active');
    document.getElementById('editLimitError').classList.remove('active');
}

function closeEditLimitModal() {
    document.getElementById('editLimitModal').classList.remove('active');
}

async function handleEditLimit(e) {
    e.preventDefault();

    const keyId = document.getElementById('editKeyId').value;
    const newLimit = parseInt(document.getElementById('newRateLimit').value);
    const errorEl = document.getElementById('editLimitError');

    try {
        const response = await fetch(`/admin/keys/${keyId}?rate_limit=${newLimit}`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.status === 401) {
            handleLogout();
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to update rate limit');
        }

        closeEditLimitModal();
        loadKeys();
    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.classList.add('active');
    }
}

// Delete Key - Show Confirmation Modal
function deleteKey(keyId, keyName) {
    document.getElementById('deleteKeyId').value = keyId;
    document.getElementById('deleteKeyName').textContent = keyName;
    document.getElementById('deleteConfirmModal').classList.add('active');
}

function closeDeleteConfirmModal() {
    document.getElementById('deleteConfirmModal').classList.remove('active');
}

async function confirmDeleteKey() {
    const keyId = document.getElementById('deleteKeyId').value;

    try {
        const response = await fetch(`/admin/keys/${keyId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.status === 401) {
            handleLogout();
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to revoke API key');
        }

        closeDeleteConfirmModal();
        loadKeys();
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Usage Modal
async function viewUsage(keyId, keyName) {
    document.getElementById('usageKeyName').textContent = keyName;
    document.getElementById('usageModal').classList.add('active');
    document.getElementById('usageTableBody').innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 2rem;">Loading usage data...</td></tr>';

    try {
        const response = await fetch(`/admin/usage/${keyId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.status === 401) {
            handleLogout();
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to load usage data');
        }

        const data = await response.json();
        renderUsage(data.usage);
    } catch (error) {
        document.getElementById('usageTableBody').innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 2rem; color: var(--error);">${error.message}</td></tr>`;
    }
}

function renderUsage(usage) {
    const tbody = document.getElementById('usageTableBody');

    if (usage.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 2rem; color: var(--text-secondary);">No usage recorded in the last 30 days.</td></tr>';
        return;
    }

    tbody.innerHTML = usage.map(day => `
        <tr>
            <td>${day.date}</td>
            <td>${day.request_count.toLocaleString()}</td>
            <td>${day.total_shifts.toLocaleString()}</td>
            <td>${day.total_volunteers.toLocaleString()}</td>
        </tr>
    `).join('');
}

function closeUsageModal() {
    document.getElementById('usageModal').classList.remove('active');
}

// Search
function handleSearch(e) {
    const query = e.target.value.toLowerCase();
    const filteredKeys = currentKeys.filter(key =>
        key.name.toLowerCase().includes(query) ||
        key.key_preview.toLowerCase().includes(query)
    );
    renderKeys(filteredKeys);
}

// Utility Functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}
