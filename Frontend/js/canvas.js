/**
 * Collaborative Canvas Drawing Engine
 * Supports smooth Bézier / line strokes, brush, eraser, color swatches,
 * size sliders, coordinate normalization (500x500 virtual canvas), and real-time synchronization.
 */

class DrawingCanvas {
  constructor(canvasElement, options = {}) {
    this.canvas = canvasElement;
    this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });

    this.virtualWidth = 500;
    this.virtualHeight = 500;

    this.currentColor = '#1e293b';
    this.currentSize = 4;
    this.currentTool = 'brush'; // 'brush' or 'eraser'
    this.isDrawing = false;
    this.isInteractive = false; // Enabled only when user is current drawer

    this.currentStrokePoints = [];
    this.strokesHistory = [];

    // Callbacks
    this.onStrokeEnd = options.onStrokeEnd || null;
    this.onClear = options.onClear || null;

    this.initCanvasSize();
    this.bindEvents();
    this.clearLocal();
  }

  initCanvasSize() {
    // Set internal resolution
    this.canvas.width = this.virtualWidth;
    this.canvas.height = this.virtualHeight;
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';
  }

  setInteractive(enable) {
    this.isInteractive = enable;
    const wrapper = this.canvas.parentElement;
    if (wrapper) {
      if (enable) {
        wrapper.classList.remove('disabled');
      } else {
        wrapper.classList.add('disabled');
      }
    }

    const toolbar = document.getElementById('drawing-toolbar');
    if (toolbar) {
      toolbar.style.opacity = enable ? '1' : '0.4';
      toolbar.style.pointerEvents = enable ? 'auto' : 'none';
    }
  }

  getCanvasCoordinates(e) {
    const rect = this.canvas.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;

    const scaleX = this.virtualWidth / rect.width;
    const scaleY = this.virtualHeight / rect.height;

    return {
      x: Math.round((clientX - rect.left) * scaleX),
      y: Math.round((clientY - rect.top) * scaleY)
    };
  }

  bindEvents() {
    const startDraw = (e) => {
      if (!this.isInteractive) return;
      e.preventDefault();
      this.isDrawing = true;

      const coords = this.getCanvasCoordinates(e);
      this.currentStrokePoints = [[coords.x, coords.y]];

      this.ctx.beginPath();
      this.ctx.moveTo(coords.x, coords.y);
      this.ctx.strokeStyle = this.currentTool === 'eraser' ? '#ffffff' : this.currentColor;
      this.ctx.lineWidth = this.currentTool === 'eraser' ? this.currentSize * 2.5 : this.currentSize;

      // Draw dot on click
      this.ctx.lineTo(coords.x + 0.1, coords.y + 0.1);
      this.ctx.stroke();
    };

    const drawMove = (e) => {
      if (!this.isDrawing || !this.isInteractive) return;
      e.preventDefault();

      const coords = this.getCanvasCoordinates(e);
      this.currentStrokePoints.push([coords.x, coords.y]);

      this.ctx.lineTo(coords.x, coords.y);
      this.ctx.stroke();
    };

    const endDraw = (e) => {
      if (!this.isDrawing) return;
      this.isDrawing = false;
      this.ctx.closePath();

      if (this.currentStrokePoints.length > 0) {
        const strokeData = {
          points: this.currentStrokePoints,
          color: this.currentTool === 'eraser' ? '#ffffff' : this.currentColor,
          size: this.currentTool === 'eraser' ? this.currentSize * 2.5 : this.currentSize,
          tool: this.currentTool
        };

        this.strokesHistory.push(strokeData);

        if (this.onStrokeEnd) {
          this.onStrokeEnd(strokeData);
        }
      }
      this.currentStrokePoints = [];
    };

    // Mouse listeners
    this.canvas.addEventListener('mousedown', startDraw);
    window.addEventListener('mousemove', drawMove);
    window.addEventListener('mouseup', endDraw);

    // Touch listeners for mobile / stylus support
    this.canvas.addEventListener('touchstart', startDraw, { passive: false });
    window.addEventListener('touchmove', drawMove, { passive: false });
    window.addEventListener('touchend', endDraw);
  }

  drawRemoteStroke(strokeData) {
    const points = strokeData.points;
    if (!points || points.length === 0) return;

    this.ctx.save();
    this.ctx.beginPath();
    this.ctx.strokeStyle = strokeData.color || '#1e293b';
    this.ctx.lineWidth = strokeData.size || 4;
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';

    this.ctx.moveTo(points[0][0], points[0][1]);
    for (let i = 1; i < points.length; i++) {
      this.ctx.lineTo(points[i][0], points[i][1]);
    }

    if (points.length === 1) {
      this.ctx.lineTo(points[0][0] + 0.1, points[0][1] + 0.1);
    }

    this.ctx.stroke();
    this.ctx.closePath();
    this.ctx.restore();

    this.strokesHistory.push(strokeData);
  }

  renderStroke(strokeData) {
    const points = strokeData.points;
    if (!points || points.length === 0) return;

    this.ctx.save();
    this.ctx.beginPath();
    this.ctx.strokeStyle = strokeData.color || '#1e293b';
    this.ctx.lineWidth = strokeData.size || 4;
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';

    this.ctx.moveTo(points[0][0], points[0][1]);
    for (let i = 1; i < points.length; i++) {
      this.ctx.lineTo(points[i][0], points[i][1]);
    }

    if (points.length === 1) {
      this.ctx.lineTo(points[0][0] + 0.1, points[0][1] + 0.1);
    }

    this.ctx.stroke();
    this.ctx.closePath();
    this.ctx.restore();
  }

  redrawAll() {
    this.ctx.fillStyle = '#ffffff';
    this.ctx.fillRect(0, 0, this.virtualWidth, this.virtualHeight);
    for (const s of this.strokesHistory) {
      this.renderStroke(s);
    }
  }

  undo() {
    if (this.strokesHistory.length === 0) return null;
    const removed = this.strokesHistory.pop();
    this.redrawAll();
    return removed;
  }

  clearLocal() {
    this.ctx.fillStyle = '#ffffff';
    this.ctx.fillRect(0, 0, this.virtualWidth, this.virtualHeight);
    this.strokesHistory = [];
  }

  clear() {
    this.clearLocal();
    if (this.onClear) {
      this.onClear();
    }
  }

  setColor(color) {
    this.currentColor = color;
    this.currentTool = 'brush';
  }

  setSize(size) {
    this.currentSize = parseInt(size, 10);
  }

  setTool(tool) {
    this.currentTool = tool;
  }

  getSerializedStrokes() {
    // Converts strokesHistory into [[[x0, x1..], [y0, y1..]], ...]
    const result = [];
    for (const stroke of this.strokesHistory) {
      if (stroke.tool === 'eraser') continue; // exclude eraser strokes from ML features
      const xs = [];
      const ys = [];
      for (const pt of stroke.points) {
        xs.push(pt[0]);
        ys.push(pt[1]);
      }
      if (xs.length > 0) {
        result.push([xs, ys]);
      }
    }
    return result;
  }

  getImageBase64() {
    return this.canvas.toDataURL('image/png');
  }
}

