/**
 * Dashboard & Leaderboard Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  initDashboard();
});

async function initDashboard() {
  console.log('🎯 Dashboard v2.5 loading...');
  const user = api.getUser();
  console.log('📦 Cached user from localStorage:', JSON.stringify(user));
  console.log('🔑 Token present:', !!api.getToken());
  if (!user) {
    showToast('Please log in to view your complete profile history.', 'info');
  }

  // Load User Stats & Profile
  await loadUserProfile(user);

  // Load Global Leaderboard (and use it to fix profile stats if needed)
  await loadLeaderboard(user);

  // Load User Game History
  if (user) {
    await loadGameHistory(user.username);
  }
}

async function loadUserProfile(cachedUser) {
  try {
    let profile = null;

    // Always try to fetch fresh profile from server first
    if (api.getToken()) {
      try {
        profile = await api.getProfile(); // This also calls api.setUser() to update localStorage
        console.log('✅ Fresh profile loaded from server:', profile);
      } catch (e) {
        console.warn('⚠️ Could not fetch fresh profile, using cached:', e.message);
        profile = cachedUser;
      }
    } else {
      profile = cachedUser;
    }

    if (profile) {
      document.getElementById('profile-name').textContent = profile.username;
      document.getElementById('profile-avatar').textContent = profile.username.charAt(0).toUpperCase();

      const stats = profile.stats || {};
      const played = stats.games_played || 0;
      const won = stats.games_won || 0;
      const rate = played > 0 ? Math.round((won / played) * 100) : 0;

      document.getElementById('stat-total-score').textContent = stats.total_score || 0;
      document.getElementById('stat-games-played').textContent = played;
      document.getElementById('stat-games-won').textContent = won;
      document.getElementById('stat-win-rate').textContent = `${rate}%`;
      document.getElementById('stat-correct-guesses').textContent = stats.correct_guesses || 0;
    } else {
      // Not logged in — show zeroes with a login prompt
      ['stat-total-score', 'stat-games-played', 'stat-games-won', 'stat-correct-guesses'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '--';
      });
      const rateEl = document.getElementById('stat-win-rate');
      if (rateEl) rateEl.textContent = '--%';
    }
  } catch (err) {
    console.error('Failed to load profile:', err);
  }
}

async function loadLeaderboard(currentUser) {
  const tableBody = document.getElementById('leaderboard-body');
  if (!tableBody) return;

  try {
    const leaderboard = await api.getLeaderboard(15);
    tableBody.innerHTML = '';

    if (leaderboard.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="5" class="empty-state">No leaderboard records yet. Play a game to rank up!</td></tr>';
      return;
    }

    leaderboard.forEach((entry, idx) => {
      const rank = idx + 1;
      let badgeClass = '';
      if (rank === 1) badgeClass = 'rank-1';
      else if (rank === 2) badgeClass = 'rank-2';
      else if (rank === 3) badgeClass = 'rank-3';

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><span class="rank-badge ${badgeClass}">${rank}</span></td>
        <td style="font-weight:600;">${entry.username}</td>
        <td style="color:#38bdf8; font-weight:700;">${entry.total_score}</td>
        <td>${entry.games_won} / ${entry.games_played}</td>
        <td>${entry.win_rate}%</td>
      `;
      tableBody.appendChild(tr);

      // If this leaderboard entry matches current user, fix profile stats from leaderboard
      if (currentUser && entry.username.toLowerCase() === currentUser.username.toLowerCase()) {
        const totalEl = document.getElementById('stat-total-score');
        if (totalEl && (totalEl.textContent === '0' || totalEl.textContent === '--')) {
          console.log('🔧 Fixing profile stats from leaderboard data:', entry);
          document.getElementById('stat-total-score').textContent = entry.total_score || 0;
          document.getElementById('stat-games-played').textContent = entry.games_played || 0;
          document.getElementById('stat-games-won').textContent = entry.games_won || 0;
          const rate = entry.games_played > 0 ? Math.round((entry.games_won / entry.games_played) * 100) : 0;
          document.getElementById('stat-win-rate').textContent = `${rate}%`;
          document.getElementById('stat-correct-guesses').textContent = entry.correct_guesses || 0;
        }
      }
    });
  } catch (err) {
    console.error('Failed to load leaderboard:', err);
    tableBody.innerHTML = '<tr><td colspan="5" class="empty-state">Could not load leaderboard data.</td></tr>';
  }
}

async function loadGameHistory(username) {
  const tableBody = document.getElementById('history-body');
  if (!tableBody) return;

  try {
    const history = await api.getHistory(username);
    tableBody.innerHTML = '';

    if (history.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="4" class="empty-state">No games played yet. Join or create a room to get started!</td></tr>';
      return;
    }

    history.forEach((h) => {
      const playedDate = h.played_at ? new Date(h.played_at).toLocaleDateString() : 'Recent';
      // Case-insensitive username match for player score lookup
      const myScoreObj = (h.players || []).find(p => p.username.toLowerCase() === username.toLowerCase());
      const score = myScoreObj ? myScoreObj.score : 0;
      const rank = myScoreObj ? `#${myScoreObj.rank}` : '-';

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="font-weight:600; color:#c4b5fd;">${h.room_code}</td>
        <td>${playedDate}</td>
        <td style="color:#ffd700; font-weight:600;">${h.winner}</td>
        <td style="color:#38bdf8; font-weight:700;">${score} pts (${rank})</td>
      `;
      tableBody.appendChild(tr);
    });
  } catch (err) {
    console.error('Failed to load game history:', err);
    tableBody.innerHTML = '<tr><td colspan="4" class="empty-state">Could not load history.</td></tr>';
  }
}

