/**
 * REST API Client & Utilities
 * Handles all backend HTTP communications, authorization tokens, and toast notifications.
 */

const API_BASE = (window.location.origin && window.location.origin.startsWith('http') && !window.location.origin.includes('file:')) 
  ? window.location.origin 
  : 'https://sketchai-idfq.onrender.com';

class APIClient {
  constructor() {
    this.tokenKey = 'drawing_game_jwt';
    this.userKey = 'drawing_game_user';
  }

  getToken() {
    return localStorage.getItem(this.tokenKey);
  }

  setToken(token) {
    if (token) {
      localStorage.setItem(this.tokenKey, token);
    } else {
      localStorage.removeItem(this.tokenKey);
    }
  }

  getUser() {
    const raw = localStorage.getItem(this.userKey);
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  setUser(user) {
    if (user) {
      localStorage.setItem(this.userKey, JSON.stringify(user));
    } else {
      localStorage.removeItem(this.userKey);
    }
  }

  logout() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
    window.location.href = '/';
  }

  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, { ...options, headers });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        let errorMsg = `Request failed with status ${response.status}`;
        if (typeof data.detail === 'string') {
          errorMsg = data.detail;
        } else if (Array.isArray(data.detail) && data.detail.length > 0) {
          errorMsg = data.detail.map(d => d.msg || d.message || JSON.stringify(d)).join(', ');
        } else if (data.message) {
          errorMsg = data.message;
        }
        throw new Error(errorMsg);
      }

      return data;
    } catch (err) {
      console.error(`API Error on [${url}]:`, err);
      throw err;
    }
  }

  // --- Auth Endpoints ---
  async register(username, email, password) {
    const res = await this.request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, email, password })
    });
    this.setToken(res.access_token);
    this.setUser(res.user);
    return res;
  }

  async login(username, password) {
    const res = await this.request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    this.setToken(res.access_token);
    this.setUser(res.user);
    return res;
  }

  async getProfile() {
    const user = await this.request('/api/auth/me');
    this.setUser(user);
    return user;
  }

  // --- Room Endpoints ---
  async createRoom(config = {}) {
    return this.request('/api/rooms/create', {
      method: 'POST',
      body: JSON.stringify(config)
    });
  }

  async joinRoom(roomCode, playerName = null) {
    return this.request('/api/rooms/join', {
      method: 'POST',
      body: JSON.stringify({ room_code: roomCode, player_name: playerName })
    });
  }

  async listRooms() {
    return this.request('/api/rooms/list');
  }

  async getRoom(roomCode) {
    return this.request(`/api/rooms/${roomCode}`);
  }

  // --- ML & GenAI Endpoints ---
  async predictSketch(strokes, imageBase64 = null) {
    return this.request('/api/game/predict', {
      method: 'POST',
      body: JSON.stringify({ strokes, image_base64: imageBase64 })
    });
  }

  async generatePrompt(category = 'Random', difficulty = 'medium') {
    return this.request('/api/game/prompt', {
      method: 'POST',
      body: JSON.stringify({ category, difficulty })
    });
  }

  async getGameDescription() {
    return this.request('/api/game/description');
  }

  // --- History & Leaderboard ---
  async getHistory(username = null) {
    const query = username ? `?username=${encodeURIComponent(username)}` : '';
    return this.request(`/api/game/history${query}`);
  }

  async getLeaderboard(limit = 15) {
    return this.request(`/api/game/leaderboard?limit=${limit}`);
  }
}

// Global API instance
const api = new APIClient();

/**
 * Toast Notification Utility
 */
function showToast(message, type = 'info', duration = 3500) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/**
 * Global Theme Management (Dark / Light)
 */
function initTheme() {
  const urlTheme = new URLSearchParams(window.location.search).get('theme');
  const savedTheme = urlTheme || localStorage.getItem('sketchai_theme') || 'dark';
  applyTheme(savedTheme);

  document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const isLight = document.body.classList.contains('light-theme');
      applyTheme(isLight ? 'dark' : 'light');
    });
  });
}

function applyTheme(theme) {
  if (theme === 'light') {
    document.body.classList.add('light-theme');
    document.documentElement.setAttribute('data-theme', 'light');
    localStorage.setItem('sketchai_theme', 'light');
    document.querySelectorAll('.theme-toggle-icon').forEach(el => el.textContent = '☀️');
    document.querySelectorAll('.theme-toggle-text').forEach(el => el.textContent = 'Light');
  } else {
    document.body.classList.remove('light-theme');
    document.documentElement.setAttribute('data-theme', 'dark');
    localStorage.setItem('sketchai_theme', 'dark');
    document.querySelectorAll('.theme-toggle-icon').forEach(el => el.textContent = '🌙');
    document.querySelectorAll('.theme-toggle-text').forEach(el => el.textContent = 'Dark');
  }
}

document.addEventListener('DOMContentLoaded', initTheme);

