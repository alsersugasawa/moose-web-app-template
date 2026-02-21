// Global state
let authToken = localStorage.getItem('authToken');
let currentUser = null;

const API_BASE = '/api';

// ─── Initialization ───────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    await loadAppConfig();
    if (authToken) {
        await initApp();
    } else {
        showAuth();
    }
});

async function loadAppConfig() {
    try {
        const res = await fetch(`${API_BASE}/admin/config`);
        if (res.ok) {
            const data = await res.json();
            const name = data.app_name || 'Web Platform';
            document.title = name;
            const titleEl = document.getElementById('app-title');
            const headerEl = document.getElementById('header-app-title');
            if (titleEl) titleEl.textContent = name;
            if (headerEl) headerEl.textContent = name;
        }
    } catch (_) {}
}

async function initApp() {
    try {
        const res = await fetch(`${API_BASE}/auth/me`, {
            headers: { Authorization: `Bearer ${authToken}` }
        });
        if (!res.ok) throw new Error('Unauthorized');
        currentUser = await res.json();
        showApp();
    } catch (_) {
        logout();
    }
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

function showAuth() {
    document.getElementById('auth-container').style.display = 'flex';
    document.getElementById('app-container').style.display = 'none';
}

function showApp() {
    document.getElementById('auth-container').style.display = 'none';
    document.getElementById('app-container').style.display = 'flex';

    const usernameEl = document.getElementById('username-display');
    if (usernameEl) usernameEl.textContent = currentUser.username;

    const adminLink = document.getElementById('admin-link');
    if (adminLink && currentUser.is_admin) {
        adminLink.style.display = 'inline-block';
    }
}

function showLogin() {
    document.getElementById('login-form').style.display = 'block';
    document.getElementById('register-form').style.display = 'none';
}

function showRegister() {
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('register-form').style.display = 'block';
}

async function handleLogin(event) {
    event.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    const errorEl = document.getElementById('login-error');
    errorEl.textContent = '';

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        if (!res.ok) {
            const data = await res.json();
            errorEl.textContent = data.detail || 'Login failed';
            return;
        }
        const data = await res.json();
        authToken = data.access_token;
        localStorage.setItem('authToken', authToken);
        await initApp();
    } catch (_) {
        errorEl.textContent = 'Network error. Please try again.';
    }
}

async function handleRegister(event) {
    event.preventDefault();
    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const errorEl = document.getElementById('register-error');
    errorEl.textContent = '';

    try {
        const res = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });
        if (!res.ok) {
            const data = await res.json();
            errorEl.textContent = data.detail || 'Registration failed';
            return;
        }
        // Auto-login after registration
        document.getElementById('login-username').value = username;
        document.getElementById('login-password').value = password;
        showLogin();
        await handleLogin({ preventDefault: () => {}, target: null });
    } catch (_) {
        errorEl.textContent = 'Network error. Please try again.';
    }
}

function handleLogout() {
    logout();
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    showAuth();
}
