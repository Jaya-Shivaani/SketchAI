/**
 * Game Room Orchestrator & UI Controller
 */

let canvas = null;
let wsClient = null;
let currentRoomCode = null;
let currentUser = null;
let isCurrentDrawer = false;
let isHost = false;
let currentRoomStatus = 'lobby';

window.startGameNow = async function() {
  console.log('[Game] Starting Round 1...');
  showToast('🚀 Starting Round 1...', 'info');

  const startBtn = document.getElementById('start-game-btn');
  if (startBtn) startBtn.disabled = true;

  if (wsClient && wsClient.isConnected) {
    wsClient.send('start_game', {});
  } else {
    // Fallback to REST trigger only if websocket is not connected
    try {
      const res = await fetch(`/api/rooms/${currentRoomCode}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      console.log('[Game] REST start response:', data);
    } catch (err) {
      console.debug('[Game] REST start error:', err);
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  initGameRoom();
});

async function initGameRoom() {
  const urlParams = new URLSearchParams(window.location.search);
  currentRoomCode = urlParams.get('room');

  if (!currentRoomCode) {
    showToast('No room code specified. Returning to lobby...', 'error');
    setTimeout(() => { window.location.href = '/'; }, 1500);
    return;
  }

  currentRoomCode = currentRoomCode.toUpperCase();
  document.getElementById('room-code-badge').textContent = currentRoomCode;

  // Get current user or prompt for guest name
  currentUser = api.getUser();
  let username = currentUser ? currentUser.username : null;
  if (!username) {
    username = prompt('Enter your player nickname:') || `Player_${Math.floor(Math.random() * 9000 + 1000)}`;
    api.setUser({ username, stats: {} });
    currentUser = { username };
  }

  // Initialize Canvas
  const canvasElement = document.getElementById('drawing-canvas');
  canvas = new DrawingCanvas(canvasElement, {
    onStrokeEnd: async (strokeData) => {
      if (wsClient) {
        wsClient.send('draw_stroke', { stroke: strokeData });
      }
      // Instant client-side AI prediction update
      try {
        const strokes = canvas.getSerializedStrokes();
        if (strokes.length > 0) {
          const res = await api.predictSketch(strokes);
          if (res && res.predicted_category) {
            updateAIPredictionBadge(res);
          }
        }
      } catch (err) {
        console.debug('Local predict error:', err);
      }
    },
    onClear: () => {
      if (wsClient) {
        wsClient.send('clear_canvas', {});
      }
      updateAIPredictionBadge({
        predicted_category: 'Canvas cleared',
        confidence: 0,
        probabilities: {}
      });
    }
  });

  // Setup toolbar interactions
  setupToolbar();

  // Setup Chat & Guess Input
  setupChat();

  // Setup Sound & Emoji Reactions
  setupEffects();

  // Connect WebSocket
  const token = api.getToken();
  wsClient = new GameWebSocket(currentRoomCode, username, token);
  setupWebSocketHandlers();
  wsClient.connect();
}

function setupToolbar() {
  const brushBtn = document.getElementById('tool-brush');
  const eraserBtn = document.getElementById('tool-eraser');
  const undoBtn = document.getElementById('tool-undo');
  const clearBtn = document.getElementById('tool-clear');
  const sizeSlider = document.getElementById('brush-size');
  const sizeValue = document.getElementById('size-value');
  const activeBadge = document.getElementById('active-tool-badge');
  const colorPicker = document.getElementById('custom-color-picker');
  const swatches = document.querySelectorAll('.color-swatch');

  const updateBadge = () => {
    if (!activeBadge) return;
    if (canvas.currentTool === 'eraser') {
      activeBadge.textContent = `🧹 Eraser (${canvas.currentSize * 2.5}px)`;
      activeBadge.style.color = '#ef4444';
      activeBadge.style.background = 'rgba(239, 68, 68, 0.15)';
    } else {
      activeBadge.textContent = `✏️ Brush (${canvas.currentSize}px)`;
      activeBadge.style.color = 'var(--text-main)';
      activeBadge.style.background = 'rgba(255, 255, 255, 0.08)';
    }
  };

  if (brushBtn && eraserBtn) {
    brushBtn.addEventListener('click', () => {
      canvas.setTool('brush');
      brushBtn.classList.add('active');
      eraserBtn.classList.remove('active');
      updateBadge();
    });

    eraserBtn.addEventListener('click', () => {
      canvas.setTool('eraser');
      eraserBtn.classList.add('active');
      brushBtn.classList.remove('active');
      updateBadge();
      showToast('Eraser selected. Click & drag to erase.', 'info');
    });
  }

  if (undoBtn) {
    undoBtn.addEventListener('click', async () => {
      const canDraw = (isCurrentDrawer || currentRoomStatus === 'lobby');
      if (canDraw && canvas) {
        const removed = canvas.undo();
        if (removed && wsClient) {
          // Send dedicated undo action to the server
          wsClient.send('undo_stroke', {});

          // Update AI prediction locally for remaining strokes
          try {
            const strokes = canvas.getSerializedStrokes();
            if (strokes.length > 0) {
              const res = await api.predictSketch(strokes);
              if (res && res.predicted_category) {
                updateAIPredictionBadge(res);
              }
            } else {
              updateAIPredictionBadge({
                predicted_category: 'Waiting for strokes...',
                confidence: 0,
                probabilities: {}
              });
            }
          } catch (e) {
            console.debug('Undo prediction refresh error:', e);
          }
        }
      }
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      const canDraw = (isCurrentDrawer || currentRoomStatus === 'lobby');
      if (canDraw && canvas) {
        canvas.clear();
      }
    });
  }

  if (sizeSlider) {
    sizeSlider.addEventListener('input', (e) => {
      const val = e.target.value;
      canvas.setSize(val);
      if (sizeValue) sizeValue.textContent = `${val}px`;
      updateBadge();
    });
  }

  swatches.forEach(swatch => {
    swatch.addEventListener('click', () => {
      swatches.forEach(s => s.classList.remove('active'));
      swatch.classList.add('active');
      const color = swatch.getAttribute('data-color');
      canvas.setColor(color);
      if (brushBtn && eraserBtn) {
        brushBtn.classList.add('active');
        eraserBtn.classList.remove('active');
      }
      updateBadge();
    });
  });

  if (colorPicker) {
    colorPicker.addEventListener('input', (e) => {
      canvas.setColor(e.target.value);
      swatches.forEach(s => s.classList.remove('active'));
      if (brushBtn && eraserBtn) {
        brushBtn.classList.add('active');
        eraserBtn.classList.remove('active');
      }
      updateBadge();
    });
  }
}

function setupChat() {
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');

  if (form && input) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = input.value.trim();
      if (!text) return;

      if (wsClient) {
        wsClient.send('chat_guess', { message: text });
      }
      input.value = '';
    });
  }
}

function setupWebSocketHandlers() {
  // Initial state synchronization
  wsClient.on('init_state', (data) => {
    handleRoomState(data.state);
    if (data.canvas_history && data.canvas_history.length > 0) {
      canvas.clearLocal();
      data.canvas_history.forEach(stroke => canvas.drawRemoteStroke(stroke));
    }
  });

  // Round start event
  wsClient.on('round_start', (data) => {
    // Hide any overlays FIRST so canvas is visible
    hideOverlays();
    // Clear canvas for new round
    if (canvas) {
      canvas.clearLocal();
    }
    // Update room state (drawer, word, timer, etc.)
    handleRoomState(data.state);
    // Update timer display
    updateTimer(data.state.remaining_time || data.state.round_duration || 60);
    showToast(`🎨 Round ${data.state.current_round + 1} started!`, 'success');
  });

  // Timer countdown & progressive letter hint reveal
  wsClient.on('timer_tick', (data) => {
    updateTimer(data.remaining_time);

    // Dynamic progressive letter hint reveal for guessers
    if (!isCurrentDrawer && data.word_hint) {
      const wordVal = document.getElementById('word-value');
      if (wordVal) {
        wordVal.textContent = data.word_hint;
      }
    }

    // Audio tick in final 10 seconds of round
    if (data.remaining_time <= 10 && data.remaining_time > 0) {
      if (window.SoundFX) window.SoundFX.tick();
    }
  });

  // Remote stroke draw
  wsClient.on('stroke_broadcast', (data) => {
    if (!isCurrentDrawer && canvas) {
      canvas.drawRemoteStroke(data.stroke);
    }
  });

  // Remote canvas cleared
  wsClient.on('canvas_cleared', () => {
    if (canvas) {
      canvas.clearLocal();
    }
  });

  // Remote undo broadcast
  wsClient.on('undo_broadcast', (data) => {
    if (!isCurrentDrawer && canvas) {
      canvas.clearLocal();
      if (data.canvas_history && data.canvas_history.length > 0) {
        data.canvas_history.forEach(stroke => canvas.drawRemoteStroke(stroke));
      }
    }
    if (data.ai_prediction) {
      updateAIPredictionBadge(data.ai_prediction);
    }
  });

  // AI Prediction Update
  wsClient.on('ai_prediction_update', (data) => {
    updateAIPredictionBadge(data.prediction);
  });

  // Chat message
  wsClient.on('chat_message', (data) => {
    appendChatMessage(data.username, data.message, data.is_system ? 'msg-system' : '');
  });

  // Correct guess
  wsClient.on('correct_guess', (data) => {
    appendChatMessage('System', data.message, 'msg-correct');
    updatePlayersList(data.players);
    showToast(data.message, 'success');

    // Chime & Confetti Burst on correct guess
    if (window.SoundFX) window.SoundFX.ding();
    if (window.Confetti) window.Confetti.burst();
  });

  // Anti-Cheat Violation Event (Word written on canvas)
  wsClient.on('anti_cheat_violation', (data) => {
    if (canvas) {
      canvas.clearLocal();
    }
    if (data.players) {
      updatePlayersList(data.players);
    }
    appendChatMessage('🚨 AI Referee', data.message, 'msg-system msg-penalty');
    showToast(`🚨 ${data.cheater} wrote the word on the board! (-50 pts)`, 'error');

    const wrapper = document.querySelector('.canvas-wrapper');
    if (wrapper) {
      wrapper.classList.add('canvas-cheat-flash');
      setTimeout(() => wrapper.classList.remove('canvas-cheat-flash'), 1200);
    }
  });

  // Live Floating Emoji Reaction from other players
  wsClient.on('emoji_reaction', (data) => {
    if (window.FloatingEmojis) {
      window.FloatingEmojis.spawn(data.emoji, data.sender);
    }
    if (window.SoundFX) {
      window.SoundFX.pop();
    }
  });

  // Player joined / left
  wsClient.on('player_joined', (data) => {
    updatePlayersList(data.players);
    appendChatMessage('System', `${data.username} joined the room.`, 'msg-system');
  });

  wsClient.on('player_left', (data) => {
    updatePlayersList(data.players);
    appendChatMessage('System', `${data.username} left the room.`, 'msg-system');
  });

  // Round ended summary
  wsClient.on('round_ended', (data) => {
    showRoundSummaryOverlay(data);
  });

  // Intermission countdown between rounds
  wsClient.on('intermission_tick', (data) => {
    const cdownEl = document.getElementById('round-cdown-num');
    if (cdownEl) {
      cdownEl.textContent = data.seconds_remaining;
    }
  });

  // Game over
  wsClient.on('game_over', (data) => {
    showGameOverOverlay(data);
    if (window.SoundFX) window.SoundFX.fanfare();
    if (window.Confetti) window.Confetti.celebration(4000);
  });

  // Connection errors
  wsClient.on('error', (err) => {
    showToast('Multiplayer connection error. Check your network.', 'error');
  });
}

function handleRoomState(state) {
  currentRoomStatus = state.status || 'lobby';
  isCurrentDrawer = state.is_drawer;
  // ALWAYS treat the connected user as host in lobby (simplifies single-player flow)
  // Also check username match, alone in room, or placeholder Host_XXX host name
  isHost = (state.status === 'lobby') ||
           (currentUser && currentUser.username === state.host) ||
           (!state.players || state.players.length <= 1) ||
           (state.host && state.host.startsWith('Host_'));

  // Update round indicator
  const roundEl = document.getElementById('round-indicator');
  if (roundEl) {
    if (state.status === 'lobby') {
      roundEl.textContent = `Lobby | Waiting to start (${state.players ? state.players.length : 1} players)`;
    } else {
      roundEl.textContent = `Round ${state.current_round + 1} / ${state.max_rounds}`;
    }
  }

  // Update Word to Draw & Prompt Display with clear labels
  const wordLabel = document.querySelector('.word-label');
  const wordVal = document.getElementById('word-value');
  const promptDetails = document.getElementById('prompt-details');

  if (state.status === 'lobby') {
    if (wordLabel) wordLabel.textContent = 'Mode:';
    if (wordVal) {
      wordVal.textContent = 'FREE DRAW / PRACTICE';
      wordVal.style.fontSize = '1.1rem';
      wordVal.style.letterSpacing = '1px';
    }
    if (promptDetails) {
      if (isHost) {
        promptDetails.innerHTML = '🎨 <strong>Practice Mode:</strong> Draw to test AI classifier, or click <strong>"▶ Start Game"</strong> above to begin!';
      } else {
        promptDetails.innerHTML = `🎨 <strong>Practice Mode:</strong> Warm up on the canvas! Waiting for host (<strong>${escapeHTML(state.host || 'host')}</strong>) to start the game...`;
      }
    }
  } else if (state.is_drawer) {
    if (wordLabel) wordLabel.textContent = '🎨 Word to Draw:';
    if (wordVal) {
      wordVal.textContent = state.word || 'WAITING...';
      wordVal.style.fontSize = '1.4rem';
      wordVal.style.letterSpacing = '2px';
    }
    if (promptDetails) {
      promptDetails.innerHTML = `<span class="category-pill-label">Category:</span> <strong style="color:var(--accent-cyan);">${state.category}</strong> (${state.difficulty})<br><span style="font-size:0.85rem; color:var(--text-muted);">💡 <em>${state.prompt}</em></span>`;
    }
  } else {
    if (wordLabel) wordLabel.textContent = '🔍 Word to Guess:';
    if (wordVal) {
      wordVal.textContent = state.word || '_ _ _ _';
      wordVal.style.fontSize = '1.4rem';
      wordVal.style.letterSpacing = '3px';
    }
    if (promptDetails) {
      promptDetails.innerHTML = `<span class="category-pill-label">Category:</span> <strong style="color:var(--accent-cyan);">${state.category}</strong><br><span style="font-size:0.85rem; color:var(--text-muted);">💡 <em>Type your guess in the chat box!</em></span>`;
    }
  }

  // Update chat bar placeholder and button label based on drawer vs guesser role
  const chatInput = document.getElementById('chat-input');
  const chatBtn = document.querySelector('#chat-form button[type="submit"]');
  if (state.status === 'playing') {
    if (state.is_drawer) {
      if (chatInput) chatInput.placeholder = '🎨 You are drawing! Chat with guessers...';
      if (chatBtn) chatBtn.textContent = 'Chat';
    } else {
      if (chatInput) chatInput.placeholder = 'Type your guess here...';
      if (chatBtn) chatBtn.textContent = 'Guess';
    }
  } else {
    if (chatInput) chatInput.placeholder = 'Type a message...';
    if (chatBtn) chatBtn.textContent = 'Send';
  }

  // Update canvas interactivity: allow drawing in lobby or when user is drawer
  if (canvas) {
    const canDraw = (state.is_drawer || state.status === 'lobby');
    canvas.setInteractive(canDraw);
  }

  // Update players list
  updatePlayersList(state.players);

  // Update AI prediction
  if (state.ai_prediction) {
    updateAIPredictionBadge(state.ai_prediction);
  }

  // Update Host Controls (Header Start Game button)
  const hostBtn = document.getElementById('start-game-btn');
  const showStartBtn = (state.status === 'lobby' || state.status === 'game_over');
  if (hostBtn) {
    hostBtn.style.display = showStartBtn ? 'inline-flex' : 'none';
    hostBtn.textContent = state.status === 'game_over' ? '▶ Play Again' : '▶ Start Game';
    hostBtn.onclick = () => window.startGameNow();
  }
}

function updateTimer(seconds) {
  const timerCircle = document.getElementById('timer-circle');
  if (!timerCircle) return;

  timerCircle.textContent = seconds;
  timerCircle.classList.remove('timer-warning', 'timer-critical');

  if (seconds <= 10 && seconds > 5) {
    timerCircle.classList.add('timer-warning');
  } else if (seconds <= 5) {
    timerCircle.classList.add('timer-critical');
  }
}

function updateAIPredictionBadge(pred) {
  const catPill = document.getElementById('ai-category-pill');
  const confBar = document.getElementById('ai-confidence-fill');
  const confText = document.getElementById('ai-confidence-text');

  if (catPill) {
    catPill.textContent = pred.predicted_category || 'Predicting...';
  }

  const confPercent = Math.round((pred.confidence || 0) * 100);
  if (confBar) {
    confBar.style.width = `${confPercent}%`;
  }
  if (confText) {
    confText.textContent = `${confPercent}%`;
  }
}

function updatePlayersList(players) {
  const listEl = document.getElementById('players-list');
  if (!listEl || !players) return;

  listEl.innerHTML = '';
  // Sort players by score
  players.sort((a, b) => b.score - a.score);

  players.forEach((p, idx) => {
    const li = document.createElement('li');
    li.className = `player-item ${p.is_drawer ? 'is-drawer' : ''} ${p.has_guessed ? 'has-guessed' : ''}`;

    const initial = p.username ? p.username.charAt(0).toUpperCase() : '?';
    const statusIcon = p.is_drawer ? '✏️' : (p.has_guessed ? '✅' : '');

    li.innerHTML = `
      <div class="player-info">
        <span class="player-avatar">${initial}</span>
        <span>${p.username} ${statusIcon}</span>
      </div>
      <div class="player-score">${p.score} pts</div>
    `;
    listEl.appendChild(li);
  });
}

function appendChatMessage(sender, message, extraClass = '') {
  const msgContainer = document.getElementById('chat-messages');
  if (!msgContainer) return;

  const div = document.createElement('div');
  div.className = `chat-msg ${extraClass}`;
  div.innerHTML = `<span class="sender">${sender}:</span> <span class="text">${escapeHTML(message)}</span>`;

  msgContainer.appendChild(div);
  msgContainer.scrollTop = msgContainer.scrollHeight;
}

function escapeHTML(str) {
  const p = document.createElement('p');
  p.textContent = str;
  return p.innerHTML;
}

function showRoundSummaryOverlay(data) {
  let overlay = document.getElementById('round-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'round-overlay';
    overlay.className = 'round-overlay';
    const wrapper = document.querySelector('.canvas-wrapper');
    if (wrapper) wrapper.appendChild(overlay);
  }

  const aiFeedback = data.ai_matched_category
    ? `<span style="color:#10b981;">🎯 AI Correctly Recognized: <strong>${data.ai_predicted_category}</strong> (${Math.round(data.ai_confidence * 100)}%)</span>`
    : `<span style="color:#f59e0b;">🤖 AI Thought: <strong>${data.ai_predicted_category}</strong> (${Math.round(data.ai_confidence * 100)}%)</span>`;

  const commentaryHtml = data.ai_commentary ? `
    <div class="ai-commentary-banner">
      <span class="commentary-icon">🤖</span>
      <span class="commentary-text">${escapeHTML(data.ai_commentary)}</span>
    </div>
  ` : '';

  overlay.innerHTML = `
    <h2>🏁 Round Finished!</h2>
    <p>The secret word was:</p>
    <div class="secret-word-reveal">${escapeHTML(data.secret_word || '')}</div>
    <p style="margin-bottom:0.4rem;">Drawn by <strong>${escapeHTML(data.drawer || 'Unknown')}</strong></p>
    <div class="round-feedback-card">
      ${aiFeedback}
    </div>
    ${commentaryHtml}
    <p id="round-countdown" style="color:#94a3b8; font-size:0.85rem; margin-top:0.35rem;">Next round starts in <strong id="round-cdown-num">7</strong> seconds...</p>
  `;
  overlay.style.display = 'flex';

  // Live countdown so user sees it ticking
  let countdown = 7;
  const cdownEl = overlay.querySelector('#round-cdown-num');
  const cdownP = overlay.querySelector('#round-countdown');
  const cdownInterval = setInterval(() => {
    countdown--;
    if (cdownEl) cdownEl.textContent = countdown;
    if (countdown <= 0) {
      clearInterval(cdownInterval);
      if (cdownP) cdownP.innerHTML = '🚀 Starting next round now...';
      setTimeout(() => {
        hideOverlays();
      }, 1500);
    }
  }, 1000);
}

function showGameOverOverlay(data) {
  let overlay = document.getElementById('round-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'round-overlay';
    overlay.className = 'round-overlay';
    document.querySelector('.canvas-wrapper').appendChild(overlay);
  }

  let rankingsHtml = '<div style="display:flex; flex-direction:column; gap:0.5rem; margin:1.25rem 0; width:100%; max-width:320px;">';
  data.rankings.forEach(r => {
    const medal = r.rank === 1 ? '🥇' : (r.rank === 2 ? '🥈' : (r.rank === 3 ? '🥉' : `#${r.rank}`));
    rankingsHtml += `
      <div style="display:flex; justify-content:space-between; padding:0.5rem 1rem; background:rgba(255,255,255,0.08); border-radius:6px; font-weight:600;">
        <span>${medal} ${r.username}</span>
        <span style="color:#38bdf8;">${r.score} pts</span>
      </div>
    `;
  });
  rankingsHtml += '</div>';

  overlay.innerHTML = `
    <h2>🏆 Game Over!</h2>
    <p style="font-size:1.2rem; color:#ffd700; font-weight:700;">Winner: ${data.winner}!</p>
    ${rankingsHtml}
    <div style="display:flex; gap:1rem; margin-top:1rem;">
      <a href="/dashboard" class="btn btn-primary">View Dashboard</a>
      <a href="/" class="btn btn-secondary">Back to Lobby</a>
    </div>
  `;
  overlay.style.display = 'flex';
}

function hideOverlays() {
  const overlay = document.getElementById('round-overlay');
  if (overlay) {
    overlay.style.display = 'none';
    overlay.innerHTML = ''; // clear inner content to stop any countdown timers
  }
  // Reset AI prediction badge to waiting state
  updateAIPredictionBadge({
    predicted_category: 'Waiting for strokes...',
    confidence: 0,
    probabilities: {}
  });
}

function setupEffects() {
  // Sound FX toggle button
  const soundBtn = document.getElementById('sound-toggle-btn');
  const soundIcon = document.getElementById('sound-icon');
  const soundText = document.getElementById('sound-text');

  if (soundBtn) {
    const isMuted = window.SoundFX && window.SoundFX.isMuted;
    if (soundIcon) soundIcon.textContent = isMuted ? '🔇' : '🔊';
    if (soundText) soundText.textContent = isMuted ? 'Muted' : 'Sound';

    soundBtn.addEventListener('click', () => {
      if (window.SoundFX) {
        const muted = window.SoundFX.toggleMute();
        if (soundIcon) soundIcon.textContent = muted ? '🔇' : '🔊';
        if (soundText) soundText.textContent = muted ? 'Muted' : 'Sound';
        showToast(muted ? 'Sound effects muted 🔇' : 'Sound effects enabled 🔊', 'info');
      }
    });
  }

  // Live floating emoji reaction buttons
  const emojiButtons = document.querySelectorAll('.emoji-btn');
  emojiButtons.forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const emoji = btn.getAttribute('data-emoji');
      if (!emoji) return;

      // Broadcast reaction via WebSocket
      if (wsClient) {
        wsClient.send('emoji_reaction', { emoji: emoji });
      }

      // Local immediate feedback
      if (window.FloatingEmojis) {
        window.FloatingEmojis.spawn(emoji, 'You');
      }
      if (window.SoundFX) {
        window.SoundFX.pop();
      }

      btn.classList.add('pop-active');
      setTimeout(() => btn.classList.remove('pop-active'), 200);
    });
  });
}

