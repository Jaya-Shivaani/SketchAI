/**
 * SketchAI Visual Celebrations, Sound Synthesizer & Live Reactions
 * Pure Vanilla JS with Web Audio API and HTML5 Canvas Confetti (Zero external dependencies)
 */

// --- 1. Web Audio API Sound Synthesizer ---
class SoundEffects {
  constructor() {
    this.ctx = null;
    this.isMuted = localStorage.getItem('sketchai_sound_muted') === 'true';
  }

  _initContext() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    localStorage.setItem('sketchai_sound_muted', this.isMuted ? 'true' : 'false');
    return this.isMuted;
  }

  ding() {
    if (this.isMuted) return;
    this._initContext();
    if (!this.ctx) return;

    const now = this.ctx.currentTime;
    // Pleasant two-tone chime (E5 -> G5)
    [659.25, 783.99].forEach((freq, idx) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, now + idx * 0.08);

      gain.gain.setValueAtTime(0.001, now + idx * 0.08);
      gain.gain.exponentialRampToValueAtTime(0.25, now + idx * 0.08 + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + idx * 0.08 + 0.45);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(now + idx * 0.08);
      osc.stop(now + idx * 0.08 + 0.5);
    });
  }

  tick() {
    if (this.isMuted) return;
    this._initContext();
    if (!this.ctx) return;

    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = 'triangle';
    osc.frequency.setValueAtTime(950, now);

    gain.gain.setValueAtTime(0.12, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);

    osc.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start(now);
    osc.stop(now + 0.05);
  }

  pop() {
    if (this.isMuted) return;
    this._initContext();
    if (!this.ctx) return;

    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(320, now);
    osc.frequency.exponentialRampToValueAtTime(740, now + 0.08);

    gain.gain.setValueAtTime(0.18, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);

    osc.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start(now);
    osc.stop(now + 0.13);
  }

  fanfare() {
    if (this.isMuted) return;
    this._initContext();
    if (!this.ctx) return;

    const now = this.ctx.currentTime;
    // Victory arpeggio (C4, E4, G4, C5 sustained)
    const notes = [261.63, 329.63, 392.00, 523.25];
    notes.forEach((freq, idx) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(freq, now + idx * 0.12);

      const isLast = (idx === notes.length - 1);
      const duration = isLast ? 1.4 : 0.25;

      gain.gain.setValueAtTime(0.001, now + idx * 0.12);
      gain.gain.exponentialRampToValueAtTime(0.3, now + idx * 0.12 + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + idx * 0.12 + duration);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(now + idx * 0.12);
      osc.stop(now + idx * 0.12 + duration + 0.1);
    });
  }
}

// --- 2. Lightweight HTML5 Canvas Confetti Engine ---
class ConfettiEngine {
  constructor() {
    this.canvas = null;
    this.ctx = null;
    this.particles = [];
    this.animationId = null;
    this.colors = ['#f43f5e', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4'];
    this._initCanvas();
  }

  _initCanvas() {
    this.canvas = document.createElement('canvas');
    this.canvas.id = 'confetti-canvas';
    this.canvas.style.position = 'fixed';
    this.canvas.style.top = '0';
    this.canvas.style.left = '0';
    this.canvas.style.width = '100vw';
    this.canvas.style.height = '100vh';
    this.canvas.style.pointerEvents = 'none';
    this.canvas.style.zIndex = '99999';
    document.body.appendChild(this.canvas);
    this.ctx = this.canvas.getContext('2d');

    this._resize();
    window.addEventListener('resize', () => this._resize());
  }

  _resize() {
    if (this.canvas) {
      this.canvas.width = window.innerWidth;
      this.canvas.height = window.innerHeight;
    }
  }

  burst(originX = null, originY = null, count = 70) {
    const x = originX !== null ? originX : window.innerWidth * 0.5;
    const y = originY !== null ? originY : window.innerHeight * 0.4;

    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = Math.random() * 8 + 3;
      this.particles.push({
        x: x,
        y: y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 4, // initial upward lift
        size: Math.random() * 8 + 5,
        color: this.colors[Math.floor(Math.random() * this.colors.length)],
        rotation: Math.random() * 360,
        rotationSpeed: (Math.random() - 0.5) * 12,
        opacity: 1.0,
        gravity: 0.18,
        drag: 0.96
      });
    }

    if (!this.animationId) {
      this._loop();
    }
  }

  celebration(durationMs = 3500) {
    const start = Date.now();
    const interval = setInterval(() => {
      const leftX = Math.random() * window.innerWidth * 0.4;
      const rightX = window.innerWidth * 0.6 + Math.random() * window.innerWidth * 0.4;
      this.burst(leftX, window.innerHeight * 0.8, 35);
      this.burst(rightX, window.innerHeight * 0.8, 35);

      if (Date.now() - start > durationMs) {
        clearInterval(interval);
      }
    }, 300);
  }

  _loop() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];

      p.vx *= p.drag;
      p.vy = (p.vy + p.gravity) * p.drag;
      p.x += p.vx;
      p.y += p.vy;
      p.rotation += p.rotationSpeed;
      p.opacity -= 0.009;

      if (p.opacity <= 0 || p.y > this.canvas.height + 50) {
        this.particles.splice(i, 1);
        continue;
      }

      this.ctx.save();
      this.ctx.translate(p.x, p.y);
      this.ctx.rotate((p.rotation * Math.PI) / 180);
      this.ctx.globalAlpha = Math.max(0, p.opacity);
      this.ctx.fillStyle = p.color;
      this.ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
      this.ctx.restore();
    }

    if (this.particles.length > 0) {
      this.animationId = requestAnimationFrame(() => this._loop());
    } else {
      this.animationId = null;
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
  }
}

// --- 3. Live Floating Emoji Reactions ---
class FloatingEmojiEngine {
  constructor() {
    this.container = null;
    this._initContainer();
  }

  _initContainer() {
    let el = document.getElementById('floating-emoji-container');
    if (!el) {
      el = document.createElement('div');
      el.id = 'floating-emoji-container';
      el.className = 'floating-emoji-container';
      const canvasWrapper = document.querySelector('.canvas-wrapper') || document.body;
      canvasWrapper.appendChild(el);
    }
    this.container = el;
  }

  spawn(emoji, sender = '') {
    if (!this.container) this._initContainer();

    const bubble = document.createElement('div');
    bubble.className = 'floating-emoji-bubble';

    // Random start horizontal position (20% to 80% across canvas)
    const randomX = Math.floor(Math.random() * 60 + 20);
    bubble.style.left = `${randomX}%`;

    bubble.innerHTML = `
      <span class="emoji-char">${emoji}</span>
      ${sender ? `<span class="emoji-sender">${escapeHTML(sender)}</span>` : ''}
    `;

    this.container.appendChild(bubble);

    // Auto-remove after animation completes (1.7s)
    setTimeout(() => {
      bubble.remove();
    }, 1700);
  }
}

// Global instances
window.SoundFX = new SoundEffects();
window.Confetti = new ConfettiEngine();
window.FloatingEmojis = new FloatingEmojiEngine();

// First user interaction unlocks AudioContext on modern browsers
document.addEventListener('pointerdown', () => {
  if (window.SoundFX) {
    window.SoundFX._initContext();
  }
}, { once: true });

