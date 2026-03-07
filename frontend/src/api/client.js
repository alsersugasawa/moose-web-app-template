/**
 * Typed fetch wrapper around the Web Platform REST API.
 *
 * The base URL is read from VITE_API_BASE (defaults to '' which means
 * same-origin — useful when built and served by FastAPI, or when Vite's
 * dev server proxy is active).
 */

const BASE = import.meta.env.VITE_API_BASE || '';

function getToken() {
  return localStorage.getItem('authToken');
}

async function request(method, path, body) {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const api = {
  auth: {
    login: (username, password) =>
      request('POST', '/api/auth/login', { username, password }),

    register: (username, email, password, invite_token) =>
      request('POST', '/api/auth/register', { username, email, password, invite_token }),

    me: () => request('GET', '/api/auth/me'),

    updateProfile: (data) => request('PUT', '/api/auth/profile', data),

    forgotPassword: (email) =>
      request('POST', '/api/auth/forgot-password', { email }),

    resetPassword: (token, new_password) =>
      request('POST', '/api/auth/reset-password', { token, new_password }),

    logout: () => {
      localStorage.removeItem('authToken');
    },
  },

  // ── Notifications ─────────────────────────────────────────────────────────
  notifications: {
    list: () => request('GET', '/api/notifications'),
    markRead: (id) => request('PATCH', `/api/notifications/${id}/read`),
    markAllRead: () => request('POST', '/api/notifications/read-all'),
  },

  // ── Files ─────────────────────────────────────────────────────────────────
  files: {
    list: () => request('GET', '/api/files'),
    getUrl: (id, thumbnail = false) =>
      request('GET', `/api/files/${id}/url${thumbnail ? '?thumbnail=true' : ''}`),
    delete: (id) => request('DELETE', `/api/files/${id}`),

    upload: async (file) => {
      const token = getToken();
      const form = new FormData();
      form.append('file', file);
      const res = await fetch(`${BASE}/api/files/upload`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      return res.json();
    },
  },

  // ── API Keys ──────────────────────────────────────────────────────────────
  apiKeys: {
    list: () => request('GET', '/api/api-keys'),
    create: (name, expires_in_days) =>
      request('POST', '/api/api-keys', { name, expires_in_days }),
    revoke: (id) => request('DELETE', `/api/api-keys/${id}`),
  },
};
