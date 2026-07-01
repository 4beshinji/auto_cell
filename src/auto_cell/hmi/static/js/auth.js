const AUTH_TOKEN_KEY = 'auto_cell_hmi_token';
const AUTH_USER_KEY = 'auto_cell_hmi_user';

function getToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

function getAuthHeaders() {
  const token = getToken();
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

async function apiFetch(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...(options.headers || {}),
    },
  });
  if (res.status === 401) {
    clearToken();
    if (window.location.pathname !== '/hmi/login') {
      window.location.href = '/hmi/login';
    }
    throw new Error('unauthorized');
  }
  return res;
}

async function initLoginPage() {
  const form = document.getElementById('login-form');
  const errorEl = document.getElementById('error');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorEl.textContent = '';
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);

    try {
      const res = await fetch('/hmi/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params.toString(),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        errorEl.textContent = data.detail || `Login failed (${res.status})`;
        return;
      }
      const data = await res.json();
      setToken(data.access_token);
      window.location.href = '/hmi';
    } catch (err) {
      errorEl.textContent = String(err);
    }
  });
}

async function fetchCurrentUser() {
  const res = await apiFetch('/hmi/auth/me');
  if (!res.ok) return null;
  const user = await res.json();
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
  return user;
}

function logout() {
  clearToken();
  window.location.href = '/hmi/login';
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initLoginPage);
} else {
  initLoginPage();
}
