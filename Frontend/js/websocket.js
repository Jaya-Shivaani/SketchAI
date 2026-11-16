/**
 * WebSocket Multiplayer Client
 * Handles real-time bi-directional events, heartbeats, and message routing.
 */

class GameWebSocket {
  constructor(roomCode, username, token = null) {
    this.roomCode = roomCode.toUpperCase();
    this.username = username;
    this.token = token;
    this.ws = null;
    this.eventHandlers = {};
    this.isConnected = false;
    this.pingInterval = null;
  }

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    let url = `${protocol}//${host}/ws/room/${this.roomCode}?username=${encodeURIComponent(this.username)}`;
    if (this.token) {
      url += `&token=${encodeURIComponent(this.token)}`;
    }

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.isConnected = true;
      console.log(`[WS] Connected to room ${this.roomCode}`);
      this.trigger('connect', {});

      // Keepalive heartbeat every 25 seconds
      this.pingInterval = setInterval(() => {
        if (this.isConnected) {
          this.send('ping', {});
        }
      }, 25000);
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const type = msg.type || 'message';
        this.trigger(type, msg);
      } catch (err) {
        console.error('[WS] Failed to parse message:', event.data, err);
      }
    };

    this.ws.onclose = (event) => {
      this.isConnected = false;
      clearInterval(this.pingInterval);
      console.log(`[WS] Disconnected from room ${this.roomCode} (code: ${event.code})`);
      this.trigger('disconnect', { code: event.code, reason: event.reason });
    };

    this.ws.onerror = (err) => {
      console.error('[WS] Error:', err);
      this.trigger('error', err);
    };
  }

  send(type, payload = {}) {
    if (!this.isConnected || !this.ws) {
      console.warn('[WS] Cannot send message: not connected');
      return;
    }
    const message = { type, ...payload };
    this.ws.send(JSON.stringify(message));
  }

  on(eventType, callback) {
    if (!this.eventHandlers[eventType]) {
      this.eventHandlers[eventType] = [];
    }
    this.eventHandlers[eventType].push(callback);
  }

  off(eventType, callback) {
    if (!this.eventHandlers[eventType]) return;
    this.eventHandlers[eventType] = this.eventHandlers[eventType].filter(cb => cb !== callback);
  }

  trigger(eventType, data) {
    const handlers = this.eventHandlers[eventType];
    if (handlers) {
      handlers.forEach(cb => {
        try {
          cb(data);
        } catch (err) {
          console.error(`[WS] Error in handler for '${eventType}':`, err);
        }
      });
    }
  }

  disconnect() {
    clearInterval(this.pingInterval);
    if (this.ws) {
      this.ws.close();
    }
    this.isConnected = false;
  }
}

