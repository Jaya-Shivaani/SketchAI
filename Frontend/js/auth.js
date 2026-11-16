/**
 * Authentication Controller & Modal Management
 */

document.addEventListener('DOMContentLoaded', () => {
  initAuthUI();
});

function initAuthUI() {
  const user = api.getUser();
  updateNavUser(user);

  // Setup modal triggers
  const loginModal = document.getElementById('login-modal');
  const registerModal = document.getElementById('register-modal');

  const openLoginBtns = document.querySelectorAll('.open-login-btn');
  const openRegisterBtns = document.querySelectorAll('.open-register-btn');
  const closeBtns = document.querySelectorAll('.modal-close');

  openLoginBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      closeAllModals();
      if (loginModal) loginModal.classList.add('active');
    });
  });

  openRegisterBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      closeAllModals();
      if (registerModal) registerModal.classList.add('active');
    });
  });

  closeBtns.forEach(btn => {
    btn.addEventListener('click', closeAllModals);
  });

  // Background overlay click closes modal
  [loginModal, registerModal].forEach(modal => {
    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) closeAllModals();
      });
    }
  });

  // Handle Login form
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const uname = document.getElementById('login-username').value.trim();
      const pword = document.getElementById('login-password').value;

      try {
        const res = await api.login(uname, pword);
        showToast(`Welcome back, ${res.user.username}!`, 'success');
        updateNavUser(res.user);
        closeAllModals();
        loginForm.reset();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  // Handle Registration form
  const regForm = document.getElementById('register-form');
  if (regForm) {
    regForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const uname = document.getElementById('reg-username').value.trim();
      const email = document.getElementById('reg-email').value.trim();
      const pword = document.getElementById('reg-password').value;

      try {
        const res = await api.register(uname, email, pword);
        showToast(`Account created! Welcome, ${res.user.username}!`, 'success');
        updateNavUser(res.user);
        closeAllModals();
        regForm.reset();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }
}

function closeAllModals() {
  document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
}

function updateNavUser(user) {
  const userSection = document.getElementById('nav-user-section');
  if (!userSection) return;

  if (user) {
    const isDashboard = window.location.pathname.includes('/dashboard');
    const dashLink = isDashboard ? '' : '<a href="/dashboard" class="nav-item">Dashboard</a>';

    userSection.innerHTML = `
      <div class="user-badge">
        <span>👤</span>
        <span>${user.username}</span>
      </div>
      ${dashLink}
      <button class="btn btn-secondary" onclick="api.logout()">Logout</button>
    `;
  } else {
    userSection.innerHTML = `
      <button class="btn btn-secondary open-login-btn">Log In</button>
      <button class="btn btn-primary open-register-btn">Sign Up</button>
    `;
    // Rebind newly created buttons
    userSection.querySelector('.open-login-btn')?.addEventListener('click', () => {
      document.getElementById('login-modal')?.classList.add('active');
    });
    userSection.querySelector('.open-register-btn')?.addEventListener('click', () => {
      document.getElementById('register-modal')?.classList.add('active');
    });
  }
}

