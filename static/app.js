// Global state
let authToken = localStorage.getItem('authToken');
let currentUser = null;
let pendingTotpToken = null;   // short-lived token held during 2FA login step (never in localStorage)
let pendingResetToken = null;  // password-reset token from ?reset_token= URL param
let inviteOnlyMode = false;    // set by loadAppConfig()

const API_BASE = '/api';

// ─── Initialization ───────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    // On first deployment, redirect to the setup wizard before anything else
    try {
        const firstRunRes = await fetch(`${API_BASE}/admin/check-first-run`);
        if (firstRunRes.ok) {
            const firstRunData = await firstRunRes.json();
            if (firstRunData.is_first_run) {
                window.location.href = '/static/setup.html';
                return;
            }
        }
    } catch (_) {}

    await loadAppConfig();
    checkUrlParams();       // ?verify_token= and ?reset_token=
    checkOAuthCallback();   // #oauth_token= fragment
    loadOAuthProviders();   // render social-login buttons

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
            // Invite-only mode
            inviteOnlyMode = !!data.invite_only;
            const inviteRow = document.getElementById('invite-token-row');
            if (inviteRow) inviteRow.style.display = inviteOnlyMode ? '' : 'none';
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
        updateTotpUI();
    } catch (_) {
        logout();
    }
}

// ─── Auth screens ─────────────────────────────────────────────────────────────

function showAuth() {
    document.getElementById('auth-container').style.display = 'flex';
    document.getElementById('app-container').style.display = 'none';
}

function showApp() {
    document.getElementById('auth-container').style.display = 'none';
    document.getElementById('app-container').style.display = '';

    const usernameEl = document.getElementById('username-display');
    if (usernameEl) usernameEl.textContent = currentUser.username;

    const adminLink = document.getElementById('admin-link');
    const hasAdminAccess = currentUser.is_admin ||
        (currentUser.permissions_effective && currentUser.permissions_effective.length > 0);
    if (adminLink && hasAdminAccess) adminLink.style.display = 'inline-block';

    // Show display_name in header if set
    if (usernameEl && currentUser.display_name) {
        usernameEl.textContent = currentUser.display_name;
    }

    // Show email verification banner when email is not yet verified
    const banner = document.getElementById('email-verify-banner');
    if (banner && currentUser.email_verified === false) {
        banner.style.cssText = 'display: flex !important;';
    }

    renderDashboard();
}

function showLogin() {
    _hideAllAuthForms();
    document.getElementById('login-form').style.display = 'block';
}

function showRegister() {
    _hideAllAuthForms();
    document.getElementById('register-form').style.display = 'block';
}

function showTotpForm() {
    _hideAllAuthForms();
    document.getElementById('totp-form').style.display = 'block';
}

function showForgotPassword() {
    _hideAllAuthForms();
    document.getElementById('forgot-password-form').style.display = 'block';
}

function showResetPassword() {
    _hideAllAuthForms();
    document.getElementById('reset-password-form').style.display = 'block';
}

function _hideAllAuthForms() {
    ['login-form', 'register-form', 'totp-form', 'forgot-password-form', 'reset-password-form']
        .forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
}

// ─── URL param and fragment handling ─────────────────────────────────────────

function checkUrlParams() {
    const params = new URLSearchParams(window.location.search);

    // Invitation link: ?invite=<token>
    const inviteToken = params.get('invite');
    if (inviteToken) {
        history.replaceState(null, '', window.location.pathname);
        const inviteField = document.getElementById('register-invite-token');
        if (inviteField) inviteField.value = inviteToken;
        const inviteRow = document.getElementById('invite-token-row');
        if (inviteRow) inviteRow.style.display = '';  // always show when token is present
        showRegister();
        return;
    }

    const verifyToken = params.get('verify_token');
    if (verifyToken) {
        history.replaceState(null, '', window.location.pathname);
        _verifyEmail(verifyToken);
        return;
    }

    const resetToken = params.get('reset_token');
    if (resetToken) {
        history.replaceState(null, '', window.location.pathname);
        pendingResetToken = resetToken;
        showAuth();
        showResetPassword();
    }
}

async function _verifyEmail(token) {
    try {
        const res = await fetch(`${API_BASE}/auth/verify-email?token=${encodeURIComponent(token)}`, {
            method: 'POST'
        });
        const data = await res.json();
        showAuth();
        showLogin();
        const errEl = document.getElementById('login-error');
        if (errEl) {
            errEl.style.color = res.ok ? 'green' : '';
            errEl.textContent = res.ok
                ? 'Email verified! You can now log in.'
                : (data.detail || 'Email verification failed.');
        }
    } catch (_) {}
}

function checkOAuthCallback() {
    const hash = window.location.hash;
    if (hash.startsWith('#oauth_token=')) {
        const token = hash.slice('#oauth_token='.length);
        history.replaceState(null, '', window.location.pathname);
        authToken = token;
        localStorage.setItem('authToken', authToken);
        initApp();
    }
}

async function loadOAuthProviders() {
    try {
        const res = await fetch(`${API_BASE}/auth/oauth/providers`);
        if (!res.ok) return;
        const data = await res.json();
        const container = document.getElementById('oauth-buttons');
        if (!container || !data.providers || data.providers.length === 0) return;

        const divider = document.createElement('div');
        divider.className = 'text-center text-muted small my-2';
        divider.textContent = '— or continue with —';
        container.appendChild(divider);

        const ICONS = { google: 'bi-google', github: 'bi-github' };
        data.providers.forEach(provider => {
            const btn = document.createElement('a');
            btn.href = `${API_BASE}/auth/oauth/${provider}`;
            btn.className = 'btn btn-outline-secondary w-100 mb-2 d-flex align-items-center justify-content-center gap-2';
            const icon = ICONS[provider] || 'bi-box-arrow-in-right';
            btn.innerHTML = `<i class="bi ${icon}"></i> Continue with ${provider.charAt(0).toUpperCase() + provider.slice(1)}`;
            container.appendChild(btn);
        });
    } catch (_) {}
}

// ─── Login ────────────────────────────────────────────────────────────────────

async function handleLogin(event) {
    event.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    const errorEl = document.getElementById('login-error');
    errorEl.textContent = '';
    errorEl.style.color = '';

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

        if (data.totp_required) {
            pendingTotpToken = data.access_token; // held in memory only
            showTotpForm();
            return;
        }

        authToken = data.access_token;
        localStorage.setItem('authToken', authToken);
        await initApp();
    } catch (_) {
        errorEl.textContent = 'Network error. Please try again.';
    }
}

// ─── Register ─────────────────────────────────────────────────────────────────

async function handleRegister(event) {
    event.preventDefault();
    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const errorEl = document.getElementById('register-error');
    errorEl.textContent = '';

    try {
        const inviteToken = document.getElementById('register-invite-token')?.value?.trim() || null;
        const res = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password, invite_token: inviteToken })
        });
        if (!res.ok) {
            const data = await res.json();
            const detail = Array.isArray(data.detail)
                ? data.detail.join(' ')
                : (data.detail || 'Registration failed');
            errorEl.textContent = detail;
            return;
        }
        // Auto-login after registration
        document.getElementById('login-username').value = username;
        document.getElementById('login-password').value = password;
        showLogin();
        await handleLogin({ preventDefault: () => {} });
    } catch (_) {
        errorEl.textContent = 'Network error. Please try again.';
    }
}

// ─── TOTP verification during login ──────────────────────────────────────────

async function handleTotpVerify(event) {
    event.preventDefault();
    const code = document.getElementById('totp-code').value.trim();
    const errorEl = document.getElementById('totp-error');
    errorEl.textContent = '';

    if (!pendingTotpToken) { showLogin(); return; }

    try {
        const res = await fetch(`${API_BASE}/auth/totp/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: pendingTotpToken, code })
        });
        if (!res.ok) {
            const data = await res.json();
            errorEl.textContent = data.detail || 'Invalid code';
            return;
        }
        const data = await res.json();
        pendingTotpToken = null;
        authToken = data.access_token;
        localStorage.setItem('authToken', authToken);
        await initApp();
    } catch (_) {
        errorEl.textContent = 'Network error. Please try again.';
    }
}

// ─── Forgot password ──────────────────────────────────────────────────────────

async function handleForgotPassword(event) {
    event.preventDefault();
    const email = document.getElementById('forgot-email').value;
    const errorEl = document.getElementById('forgot-error');
    const successEl = document.getElementById('forgot-success');
    errorEl.textContent = '';
    successEl.style.display = 'none';

    try {
        const res = await fetch(`${API_BASE}/auth/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (res.ok) {
            successEl.textContent = data.message;
            successEl.style.display = 'block';
        } else {
            errorEl.textContent = data.detail || 'Request failed';
        }
    } catch (_) {
        errorEl.textContent = 'Network error. Please try again.';
    }
}

// ─── Reset password ───────────────────────────────────────────────────────────

async function handleResetPassword(event) {
    event.preventDefault();
    const newPassword = document.getElementById('reset-new-password').value;
    const confirmPassword = document.getElementById('reset-confirm-password').value;
    const errorEl = document.getElementById('reset-error');
    const successEl = document.getElementById('reset-success');
    errorEl.textContent = '';
    successEl.style.display = 'none';

    if (newPassword !== confirmPassword) {
        errorEl.textContent = 'Passwords do not match';
        return;
    }
    if (!pendingResetToken) {
        errorEl.textContent = 'Reset token missing. Use the link from your email.';
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/auth/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: pendingResetToken, new_password: newPassword })
        });
        const data = await res.json();
        if (res.ok) {
            pendingResetToken = null;
            successEl.textContent = data.message;
            successEl.style.display = 'block';
            setTimeout(() => showLogin(), 2000);
        } else {
            const detail = Array.isArray(data.detail)
                ? data.detail.join(' ')
                : (data.detail || 'Reset failed');
            errorEl.textContent = detail;
        }
    } catch (_) {
        errorEl.textContent = 'Network error. Please try again.';
    }
}

// ─── Email verification resend ────────────────────────────────────────────────

async function resendVerification() {
    try {
        const res = await fetch(`${API_BASE}/auth/resend-verification`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${authToken}` }
        });
        const data = await res.json();
        alert(res.ok ? data.message : (data.detail || 'Failed to resend'));
    } catch (_) {
        alert('Network error.');
    }
}

// ─── TOTP setup & management ──────────────────────────────────────────────────

function updateTotpUI() {
    if (!currentUser) return;
    const badge = document.getElementById('totp-status-badge');
    const setupBtn = document.getElementById('totp-setup-btn');
    const disableBtn = document.getElementById('totp-disable-btn');

    if (currentUser.totp_enabled) {
        if (badge) { badge.textContent = 'Enabled'; badge.className = 'badge bg-success'; }
        if (setupBtn) setupBtn.style.display = 'none';
        if (disableBtn) disableBtn.style.display = 'inline-block';
    } else {
        if (badge) { badge.textContent = 'Not set up'; badge.className = 'badge bg-secondary'; }
        if (setupBtn) setupBtn.style.display = 'inline-block';
        if (disableBtn) disableBtn.style.display = 'none';
    }
}

async function setupTotp() {
    try {
        const res = await fetch(`${API_BASE}/auth/totp/setup`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${authToken}` }
        });
        if (!res.ok) { alert('Failed to initiate TOTP setup'); return; }
        const data = await res.json();
        document.getElementById('totp-qr-img').src = data.qr_code;
        document.getElementById('totp-secret-text').textContent = data.secret;
        document.getElementById('totp-enable-code').value = '';
        document.getElementById('totp-setup-error').textContent = '';
        new bootstrap.Modal(document.getElementById('totpSetupModal')).show();
    } catch (_) {
        alert('Network error.');
    }
}

async function handleTotpEnable() {
    const code = document.getElementById('totp-enable-code').value.trim();
    const errorEl = document.getElementById('totp-setup-error');
    errorEl.textContent = '';
    try {
        const res = await fetch(`${API_BASE}/auth/totp/enable`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });
        const data = await res.json();
        if (res.ok) {
            bootstrap.Modal.getInstance(document.getElementById('totpSetupModal')).hide();
            currentUser.totp_enabled = true;
            updateTotpUI();
            alert('Two-factor authentication enabled!');
        } else {
            errorEl.textContent = data.detail || 'Invalid code';
        }
    } catch (_) {
        errorEl.textContent = 'Network error.';
    }
}

function showDisableTotp() {
    document.getElementById('totp-disable-code').value = '';
    document.getElementById('totp-disable-error').textContent = '';
    new bootstrap.Modal(document.getElementById('totpDisableModal')).show();
}

async function handleTotpDisable() {
    const code = document.getElementById('totp-disable-code').value.trim();
    const errorEl = document.getElementById('totp-disable-error');
    errorEl.textContent = '';
    try {
        const res = await fetch(`${API_BASE}/auth/totp/disable`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });
        const data = await res.json();
        if (res.ok) {
            bootstrap.Modal.getInstance(document.getElementById('totpDisableModal')).hide();
            currentUser.totp_enabled = false;
            updateTotpUI();
            alert('Two-factor authentication disabled.');
        } else {
            errorEl.textContent = data.detail || 'Invalid code';
        }
    } catch (_) {
        errorEl.textContent = 'Network error.';
    }
}

// ─── Session management ───────────────────────────────────────────────────────

async function showSessions() {
    await loadSessions();
    new bootstrap.Modal(document.getElementById('sessionsModal')).show();
}

async function loadSessions() {
    const container = document.getElementById('sessions-list');
    container.innerHTML = '<p class="text-muted text-center">Loading...</p>';
    try {
        const res = await fetch(`${API_BASE}/auth/sessions`, {
            headers: { Authorization: `Bearer ${authToken}` }
        });
        if (!res.ok) { container.innerHTML = '<p class="text-danger">Failed to load sessions.</p>'; return; }
        const sessions = await res.json();
        if (sessions.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">No active sessions.</p>';
            return;
        }
        container.innerHTML = sessions.map(s => `
            <div class="d-flex align-items-center border rounded p-2 mb-2 gap-2">
                <i class="bi bi-laptop fs-4 text-muted"></i>
                <div class="flex-grow-1 small">
                    <div class="fw-semibold">${_escHtml(s.device_info || 'Unknown device')}</div>
                    <div class="text-muted">IP: ${_escHtml(s.ip_address || '—')} &bull; Last used: ${_fmtDate(s.last_used)}</div>
                    <div class="text-muted">Created: ${_fmtDate(s.created_at)}</div>
                </div>
                <button class="btn btn-sm btn-outline-danger" onclick="revokeSession('${s.id}')">
                    <i class="bi bi-x-lg"></i>
                </button>
            </div>`).join('');
    } catch (_) {
        container.innerHTML = '<p class="text-danger">Network error.</p>';
    }
}

async function revokeSession(sessionId) {
    if (!confirm('Revoke this session?')) return;
    try {
        const res = await fetch(`${API_BASE}/auth/sessions/${sessionId}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${authToken}` }
        });
        if (res.ok) await loadSessions();
        else alert('Failed to revoke session.');
    } catch (_) { alert('Network error.'); }
}

async function revokeAllSessions() {
    if (!confirm('Revoke all sessions? You will be logged out everywhere.')) return;
    try {
        const res = await fetch(`${API_BASE}/auth/sessions/all`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${authToken}` }
        });
        if (res.ok) logout();
        else alert('Failed to revoke sessions.');
    } catch (_) { alert('Network error.'); }
}

// ─── Logout ───────────────────────────────────────────────────────────────────

function handleLogout() { logout(); }

function logout() {
    authToken = null;
    currentUser = null;
    pendingTotpToken = null;
    localStorage.removeItem('authToken');
    showAuth();
    showLogin();
}

// ─── Dashboard Customization ──────────────────────────────────────────────────

let _editingCardId = null;

function _dashboardKey() {
    return 'dashboardPrefs_' + (currentUser?.username || '_anon');
}

function _getDashboardPrefs() {
    try {
        return JSON.parse(localStorage.getItem(_dashboardKey())) || { hidden: [], customCards: [] };
    } catch { return { hidden: [], customCards: [] }; }
}

function _saveDashboardPrefs(prefs) {
    localStorage.setItem(_dashboardKey(), JSON.stringify(prefs));
}

function renderDashboard() {
    const prefs = _getDashboardPrefs();

    // Apply built-in card visibility
    document.querySelectorAll('[data-card-wrapper]').forEach(el => {
        el.style.display = prefs.hidden.includes(el.dataset.cardWrapper) ? 'none' : '';
    });

    // Remove stale custom cards then re-render
    document.querySelectorAll('[data-custom-card]').forEach(el => el.remove());
    const row = document.getElementById('dashboard-cards-row');
    if (row) prefs.customCards.forEach(card => row.insertAdjacentHTML('beforeend', _buildCustomCardCol(card)));

    // Load API keys into the card
    loadApiKeys();
}

function _buildCustomCardCol(card) {
    const icon = card.icon ? `<i class="bi ${_escHtml(card.icon)} me-2"></i>` : '';
    const body = card.body ? `<p class="card-text mb-2">${_escHtml(card.body)}</p>` : '';
    const link = card.link
        ? `<a href="${_escHtml(card.link)}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-outline-primary">${_escHtml(card.linkText || 'Open Link')}</a>`
        : '';
    const empty = !body && !link ? `<p class="text-muted small mb-0">No content.</p>` : '';
    return `
        <div class="col-md-6" data-custom-card="${_escHtml(card.id)}">
            <div class="card shadow-sm h-100">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span>${icon}${_escHtml(card.title)}</span>
                    <div class="d-flex gap-1">
                        <button class="btn btn-sm btn-outline-secondary py-0 px-2" title="Edit"
                                onclick="openEditCard('${_escHtml(card.id)}')"><i class="bi bi-pencil"></i></button>
                        <button class="btn btn-sm btn-outline-danger py-0 px-2" title="Delete"
                                onclick="deleteCustomCard('${_escHtml(card.id)}')"><i class="bi bi-trash"></i></button>
                    </div>
                </div>
                <div class="card-body">${body}${link}${empty}</div>
            </div>
        </div>`;
}

function openCustomizePanel() {
    const prefs = _getDashboardPrefs();
    // Sync toggle checkboxes
    ['welcome', 'account-security', 'api-keys'].forEach(id => {
        const el = document.getElementById('toggle-' + id);
        if (el) el.checked = !prefs.hidden.includes(id);
    });
    _renderManageList(prefs);
    cancelEditCard();
    const modalEl = document.getElementById('customizeModal');
    (bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl)).show();
}

function _renderManageList(prefs) {
    const list = document.getElementById('custom-cards-manage-list');
    if (!list) return;
    if (!prefs.customCards.length) {
        list.innerHTML = '<p class="text-muted small mb-0">No custom cards yet. Add one below.</p>';
        return;
    }
    list.innerHTML = prefs.customCards.map(c => `
        <div class="d-flex justify-content-between align-items-center border rounded px-3 py-2 mb-2 bg-white">
            <span class="small">${c.icon ? `<i class="bi ${_escHtml(c.icon)} me-2 text-muted"></i>` : ''}<strong>${_escHtml(c.title)}</strong></span>
            <div class="d-flex gap-1">
                <button class="btn btn-sm btn-outline-secondary py-0" onclick="openEditCard('${_escHtml(c.id)}')"><i class="bi bi-pencil"></i></button>
                <button class="btn btn-sm btn-outline-danger py-0" onclick="deleteCustomCard('${_escHtml(c.id)}')"><i class="bi bi-trash"></i></button>
            </div>
        </div>`).join('');
}

function toggleBuiltinCard(cardId, visible) {
    const prefs = _getDashboardPrefs();
    if (visible) {
        prefs.hidden = prefs.hidden.filter(id => id !== cardId);
    } else {
        if (!prefs.hidden.includes(cardId)) prefs.hidden.push(cardId);
    }
    _saveDashboardPrefs(prefs);
    renderDashboard();
}

function saveCustomCard() {
    const title = document.getElementById('card-form-title-input').value.trim();
    const body  = document.getElementById('card-form-body').value.trim();
    const icon  = document.getElementById('card-form-icon').value;
    const link  = document.getElementById('card-form-link').value.trim();
    const linkText = document.getElementById('card-form-link-text').value.trim();
    const errEl = document.getElementById('card-form-error');

    errEl.style.display = 'none';
    if (!title) {
        errEl.textContent = 'Title is required.';
        errEl.style.display = 'block';
        return;
    }

    const prefs = _getDashboardPrefs();
    if (_editingCardId) {
        const card = prefs.customCards.find(c => c.id === _editingCardId);
        if (card) Object.assign(card, { title, body, icon, link, linkText });
    } else {
        prefs.customCards.push({ id: 'card_' + Date.now(), title, body, icon, link, linkText });
    }
    _saveDashboardPrefs(prefs);
    renderDashboard();
    _renderManageList(prefs);
    cancelEditCard();
}

function openEditCard(cardId) {
    const prefs = _getDashboardPrefs();
    const card = prefs.customCards.find(c => c.id === cardId);
    if (!card) return;
    _editingCardId = cardId;
    document.getElementById('card-form-title-input').value = card.title || '';
    document.getElementById('card-form-body').value        = card.body  || '';
    document.getElementById('card-form-icon').value        = card.icon  || '';
    document.getElementById('card-form-link').value        = card.link  || '';
    document.getElementById('card-form-link-text').value   = card.linkText || '';
    document.getElementById('card-form-link-text-row').style.display = card.link ? '' : 'none';
    document.getElementById('card-form-heading').textContent = 'Edit Card';
    document.getElementById('save-card-btn').innerHTML = '<i class="bi bi-check-lg me-1"></i>Save Changes';
    document.getElementById('cancel-edit-btn').style.display = '';
    document.getElementById('card-form-error').style.display = 'none';
    document.getElementById('card-form-heading').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function cancelEditCard() {
    _editingCardId = null;
    ['card-form-title-input', 'card-form-body', 'card-form-icon', 'card-form-link', 'card-form-link-text']
        .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    document.getElementById('card-form-link-text-row').style.display = 'none';
    document.getElementById('card-form-heading').textContent = 'Add New Card';
    document.getElementById('save-card-btn').innerHTML = '<i class="bi bi-plus-lg me-1"></i>Add Card';
    document.getElementById('cancel-edit-btn').style.display = 'none';
    const errEl = document.getElementById('card-form-error');
    if (errEl) errEl.style.display = 'none';
}

function deleteCustomCard(cardId) {
    if (!confirm('Delete this card?')) return;
    const prefs = _getDashboardPrefs();
    prefs.customCards = prefs.customCards.filter(c => c.id !== cardId);
    _saveDashboardPrefs(prefs);
    renderDashboard();
    const modal = document.getElementById('customizeModal');
    if (modal?.classList.contains('show')) _renderManageList(prefs);
}

// ─── Utilities ────────────────────────────────────────────────────────────────

function _escHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function _fmtDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleString();
}

// ─── Profile ──────────────────────────────────────────────────────────────────

async function openProfile() {
    try {
        const res = await fetch(`${API_BASE}/auth/profile`, {
            headers: { Authorization: `Bearer ${authToken}` }
        });
        if (!res.ok) return;
        const p = await res.json();
        document.getElementById('profile-display-name').value = p.display_name || '';
        document.getElementById('profile-bio').value = p.bio || '';
        const tzEl = document.getElementById('profile-timezone');
        if (tzEl) tzEl.value = p.timezone || 'UTC';
        const langEl = document.getElementById('profile-language');
        if (langEl) langEl.value = p.language || 'en';

        const avatarImg = document.getElementById('profile-avatar-img');
        const avatarPlaceholder = document.getElementById('profile-avatar-placeholder');
        if (p.avatar_path) {
            avatarImg.src = p.avatar_path + '?t=' + Date.now();
            avatarImg.classList.remove('d-none');
            avatarPlaceholder.classList.add('d-none');
        } else {
            avatarImg.classList.add('d-none');
            avatarPlaceholder.classList.remove('d-none');
        }

        const el = document.getElementById('profileOffcanvas');
        if (el) (bootstrap.Offcanvas.getInstance(el) || new bootstrap.Offcanvas(el)).show();
    } catch (_) {}
}

async function handleProfileUpdate(event) {
    event.preventDefault();
    const msgEl = document.getElementById('profile-msg');
    msgEl.textContent = '';
    const body = {
        display_name: document.getElementById('profile-display-name').value.trim() || null,
        bio: document.getElementById('profile-bio').value.trim() || null,
        timezone: document.getElementById('profile-timezone').value,
        language: document.getElementById('profile-language').value,
    };
    try {
        const res = await fetch(`${API_BASE}/auth/profile`, {
            method: 'PUT',
            headers: { Authorization: `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await res.json();
        if (res.ok) {
            msgEl.className = 'text-success small mb-2';
            msgEl.textContent = 'Profile saved.';
            // Update header display name
            const usernameEl = document.getElementById('username-display');
            if (usernameEl) {
                usernameEl.textContent = data.display_name || currentUser.username;
            }
        } else {
            msgEl.className = 'text-danger small mb-2';
            msgEl.textContent = data.detail || 'Save failed.';
        }
    } catch (_) {
        msgEl.className = 'text-danger small mb-2';
        msgEl.textContent = 'Network error.';
    }
}

async function handleAvatarUpload(input) {
    if (!input.files || !input.files[0]) return;
    const formData = new FormData();
    formData.append('file', input.files[0]);
    try {
        const res = await fetch(`${API_BASE}/auth/profile/avatar`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${authToken}` },
            body: formData
        });
        const data = await res.json();
        if (res.ok) {
            const avatarImg = document.getElementById('profile-avatar-img');
            avatarImg.src = data.avatar_path + '?t=' + Date.now();
            avatarImg.classList.remove('d-none');
            document.getElementById('profile-avatar-placeholder').classList.add('d-none');
        } else {
            alert(data.detail || 'Avatar upload failed.');
        }
    } catch (_) {
        alert('Network error during upload.');
    }
    // Reset the file input so the same file can be re-selected
    input.value = '';
}

// ─── API Keys ─────────────────────────────────────────────────────────────────

async function loadApiKeys() {
    const listEl = document.getElementById('api-keys-list');
    if (!listEl || !authToken) return;
    try {
        const res = await fetch(`${API_BASE}/auth/api-keys`, {
            headers: { Authorization: `Bearer ${authToken}` }
        });
        if (!res.ok) { listEl.innerHTML = '<div class="list-group-item text-danger small">Failed to load.</div>'; return; }
        const keys = await res.json();
        if (keys.length === 0) {
            listEl.innerHTML = '<div class="list-group-item text-muted small py-2">No API keys yet.</div>';
            return;
        }
        listEl.innerHTML = keys.map(k => `
            <div class="list-group-item d-flex justify-content-between align-items-center py-2">
                <div>
                    <div class="fw-semibold">${_escHtml(k.name)}${k.is_active ? '' : ' <span class="badge bg-secondary">Inactive</span>'}</div>
                    <div class="text-muted font-monospace" style="font-size:0.75rem;">${_escHtml(k.key_prefix)}…</div>
                    <div class="text-muted" style="font-size:0.75rem;">${k.last_used ? 'Used ' + _fmtDate(k.last_used) : 'Never used'}${k.expires_at ? ' · Exp: ' + _fmtDate(k.expires_at) : ''}</div>
                </div>
                <button class="btn btn-sm btn-outline-danger ms-2 flex-shrink-0" onclick="revokeApiKey('${_escHtml(k.id)}')">
                    <i class="bi bi-trash"></i>
                </button>
            </div>`).join('');
    } catch (_) {
        listEl.innerHTML = '<div class="list-group-item text-danger small">Network error.</div>';
    }
}

function showCreateApiKeyModal() {
    document.getElementById('api-key-name').value = '';
    document.getElementById('api-key-expires').value = '';
    document.getElementById('api-key-create-error').textContent = '';
    document.getElementById('api-key-create-form').style.display = '';
    document.getElementById('api-key-created-result').style.display = 'none';
    document.getElementById('api-key-modal-footer').innerHTML =
        '<button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Cancel</button>' +
        '<button type="button" class="btn btn-primary btn-sm" onclick="handleCreateApiKey()">Create Key</button>';
    const el = document.getElementById('apiKeyModal');
    if (el) (bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el)).show();
}

async function handleCreateApiKey() {
    const name = document.getElementById('api-key-name').value.trim();
    const errEl = document.getElementById('api-key-create-error');
    errEl.textContent = '';
    if (!name) { errEl.textContent = 'Key name is required.'; return; }
    const expiresIn = document.getElementById('api-key-expires').value;
    const body = { name, scopes: [], expires_in_days: expiresIn ? parseInt(expiresIn) : null };
    try {
        const res = await fetch(`${API_BASE}/auth/api-keys`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await res.json();
        if (!res.ok) { errEl.textContent = data.detail || 'Failed to create key.'; return; }

        document.getElementById('api-key-value').value = data.key;
        document.getElementById('api-key-create-form').style.display = 'none';
        document.getElementById('api-key-created-result').style.display = '';
        document.getElementById('api-key-modal-footer').innerHTML =
            '<button type="button" class="btn btn-primary btn-sm" data-bs-dismiss="modal" onclick="loadApiKeys()">Done</button>';
    } catch (_) {
        errEl.textContent = 'Network error.';
    }
}

async function revokeApiKey(keyId) {
    if (!confirm('Revoke this API key? It will stop working immediately.')) return;
    try {
        const res = await fetch(`${API_BASE}/auth/api-keys/${keyId}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${authToken}` }
        });
        if (res.ok) await loadApiKeys();
        else alert('Failed to revoke key.');
    } catch (_) {
        alert('Network error.');
    }
}

function copyApiKey() {
    const val = document.getElementById('api-key-value').value;
    const btn = document.getElementById('api-key-copy-btn');
    navigator.clipboard.writeText(val).then(() => {
        if (btn) { btn.innerHTML = '<i class="bi bi-check-lg"></i>'; setTimeout(() => { btn.innerHTML = '<i class="bi bi-clipboard"></i>'; }, 2000); }
    }).catch(() => {
        // Fallback: select the text
        document.getElementById('api-key-value').select();
    });
}
