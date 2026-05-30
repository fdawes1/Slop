'use strict';

// ── Colourmap LUT builder ─────────────────────────────────────────────────────

const STOPS = {
  thermal: [
    [0.00, [0,   0,   0  ]],
    [0.15, [80,  0,   60 ]],
    [0.35, [200, 0,   0  ]],
    [0.55, [255, 120, 0  ]],
    [0.75, [255, 230, 0  ]],
    [0.90, [255, 255, 180]],
    [1.00, [255, 255, 255]],
  ],
  night: [
    [0.00, [0,  0,   0  ]],
    [0.25, [0,  30,  0  ]],
    [0.60, [0,  160, 20 ]],
    [0.85, [0,  255, 60 ]],
    [1.00, [180,255, 180]],
  ],
  em: [
    [0.00, [0,  0,   0  ]],
    [0.25, [0,  0,   100]],
    [0.55, [0,  140, 200]],
    [0.85, [0,  255, 255]],
    [1.00, [180,255, 255]],
  ],
};

function buildLUT(stops) {
  const lut = new Uint8Array(256 * 3);
  for (let i = 0; i < 256; i++) {
    const v = i / 255;
    let lo = stops[0], hi = stops[stops.length - 1];
    for (let j = 0; j < stops.length - 1; j++) {
      if (v >= stops[j][0] && v <= stops[j + 1][0]) { lo = stops[j]; hi = stops[j + 1]; break; }
    }
    const t = Math.max(0, Math.min(1, (v - lo[0]) / (hi[0] - lo[0] + 1e-9)));
    lut[i*3]   = Math.round(lo[1][0] + (hi[1][0] - lo[1][0]) * t);
    lut[i*3+1] = Math.round(lo[1][1] + (hi[1][1] - lo[1][1]) * t);
    lut[i*3+2] = Math.round(lo[1][2] + (hi[1][2] - lo[1][2]) * t);
  }
  return lut;
}

const LUTS = { thermal: buildLUT(STOPS.thermal), night: buildLUT(STOPS.night), em: buildLUT(STOPS.em) };

// ── HUD colour palettes ───────────────────────────────────────────────────────

const PALETTE = {
  thermal: { pri: '#FF8800', sec: '#FF3300', txt: '#FFCC44', dim: '#663300' },
  night:   { pri: '#00FF44', sec: '#00DD33', txt: '#88FF88', dim: '#004400' },
  em:      { pri: '#00FFFF', sec: '#0099FF', txt: '#88FFFF', dim: '#004455' },
  normal:  { pri: '#00FF44', sec: '#00DD33', txt: '#88FF88', dim: '#004400' },
};

// ── Main HUD class ────────────────────────────────────────────────────────────

class PredHUD {
  constructor(canvas) {
    this.canvas  = canvas;
    this.ctx     = canvas.getContext('2d');
    this.mode    = 'thermal';
    this.targets = [];
    this.source  = 'NONE';
    this.connected = false;
    this.fps     = 0;
    this._fcount = 0;
    this._ftime  = Date.now();
    this.scanY   = 0;
    this._ages   = new Map();   // target key → frame count
    this._img    = new Image();
    this._off    = document.createElement('canvas');
    this._offCtx = this._off.getContext('2d');

    this._resize();
    window.addEventListener('resize', () => this._resize());
    this._loop();
  }

  _resize() {
    const W = window.innerWidth, H = window.innerHeight;
    this.canvas.width = this._off.width  = W;
    this.canvas.height = this._off.height = H;
  }

  setMode(mode) {
    this.mode = mode;
    document.querySelectorAll('.mode-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.mode === mode);
    });
  }

  // Called by WebSocket handler
  push(payload) {
    this.source  = payload.source || '?';
    this.targets = payload.detections || [];
    this._fcount++;
    const now = Date.now();
    if (now - this._ftime >= 1000) {
      this.fps = this._fcount;
      this._fcount = 0;
      this._ftime = now;
    }

    // Age tracker for lock-on animation
    const next = new Map();
    this.targets.forEach(t => {
      const k = `${Math.round(t.x * 20)}_${Math.round(t.y * 20)}`;
      next.set(k, (this._ages.get(k) || 0) + 1);
    });
    this._ages = next;

    this._img.src = 'data:image/jpeg;base64,' + payload.data;
  }

  // ── Render pipeline ─────────────────────────────────────────────────────────

  _loop() {
    const tick = () => {
      this._drawVideo();
      this._vignette();
      this._scanLine();
      this._cornerFrames();
      this._reticle();
      this._drawTargets();
      this._hudText();
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  _drawVideo() {
    const { ctx, canvas, _off, _offCtx, _img, mode } = this;
    const W = canvas.width, H = canvas.height;
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, W, H);

    if (!_img.complete || !_img.naturalWidth) {
      this._noSignal(); return;
    }

    // Letterbox fit
    const ar = _img.naturalWidth / _img.naturalHeight;
    let dw = W, dh = W / ar;
    if (dh > H) { dh = H; dw = H * ar; }
    const dx = (W - dw) / 2, dy = (H - dh) / 2;

    if (mode === 'normal') {
      ctx.drawImage(_img, dx, dy, dw, dh);
    } else {
      // Draw to offscreen, apply colormap, copy back
      _offCtx.clearRect(0, 0, W, H);
      _offCtx.drawImage(_img, dx, dy, dw, dh);
      const id = _offCtx.getImageData(dx, dy, dw, dh);
      const lut = LUTS[mode];
      const d = id.data;
      for (let i = 0; i < d.length; i += 4) {
        const lum = (0.299 * d[i] + 0.587 * d[i+1] + 0.114 * d[i+2]) | 0;
        d[i]   = lut[lum * 3];
        d[i+1] = lut[lum * 3 + 1];
        d[i+2] = lut[lum * 3 + 2];
      }
      _offCtx.putImageData(id, dx, dy);
      ctx.drawImage(_off, 0, 0);
    }
  }

  _noSignal() {
    const { ctx, canvas, mode } = this;
    const p = PALETTE[mode];
    const W = canvas.width, H = canvas.height;
    // Static noise
    for (let i = 0; i < 600; i++) {
      ctx.fillStyle = `rgba(${Math.random()*255|0},${Math.random()*100|0},0,${Math.random()*0.4})`;
      ctx.fillRect(Math.random() * W, Math.random() * H, 2, 2);
    }
    ctx.fillStyle = p.dim;
    ctx.font = 'bold 20px "Share Tech Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText('NO SIGNAL', W / 2, H / 2);
    ctx.font = '13px "Share Tech Mono", monospace';
    ctx.fillText('AWAITING CAMERA SOURCE', W / 2, H / 2 + 28);
  }

  _vignette() {
    const { ctx, canvas } = this;
    const W = canvas.width, H = canvas.height;
    const g = ctx.createRadialGradient(W/2, H/2, H * 0.25, W/2, H/2, H * 0.85);
    g.addColorStop(0, 'transparent');
    g.addColorStop(1, 'rgba(0,0,0,0.65)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
  }

  _scanLine() {
    const { ctx, canvas, mode } = this;
    const p = PALETTE[mode];
    const W = canvas.width, H = canvas.height;
    this.scanY = (this.scanY + 1.5) % H;

    // Trailing glow
    const g = ctx.createLinearGradient(0, this.scanY - 30, 0, this.scanY + 6);
    g.addColorStop(0, 'transparent');
    g.addColorStop(0.7, p.pri + '18');
    g.addColorStop(1.0, p.pri + '55');
    ctx.fillStyle = g;
    ctx.fillRect(0, this.scanY - 30, W, 36);

    // Bright leading edge
    ctx.save();
    ctx.strokeStyle = p.pri + 'BB';
    ctx.lineWidth = 1;
    ctx.shadowColor = p.pri;
    ctx.shadowBlur = 8;
    ctx.beginPath();
    ctx.moveTo(0, this.scanY);
    ctx.lineTo(W, this.scanY);
    ctx.stroke();
    ctx.restore();
  }

  _cornerFrames() {
    const { ctx, canvas, mode } = this;
    const p = PALETTE[mode];
    const W = canvas.width, H = canvas.height;
    const s = 55;

    ctx.save();
    ctx.strokeStyle = p.pri + 'CC';
    ctx.lineWidth = 2;
    ctx.shadowColor = p.pri;
    ctx.shadowBlur = 8;
    ctx.beginPath();
    ctx.moveTo(0, s);    ctx.lineTo(0, 0);    ctx.lineTo(s, 0);
    ctx.moveTo(W-s, 0);  ctx.lineTo(W, 0);    ctx.lineTo(W, s);
    ctx.moveTo(0, H-s);  ctx.lineTo(0, H);    ctx.lineTo(s, H);
    ctx.moveTo(W-s, H);  ctx.lineTo(W, H);    ctx.lineTo(W, H-s);
    ctx.stroke();
    ctx.restore();
  }

  _reticle() {
    const { ctx, canvas, mode } = this;
    const p = PALETTE[mode];
    const cx = canvas.width / 2, cy = canvas.height / 2;
    const r = 22, gap = r + 10, arm = 18;

    ctx.save();
    ctx.strokeStyle = p.pri + '99';
    ctx.lineWidth = 1;
    ctx.shadowColor = p.pri;
    ctx.shadowBlur = 6;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.moveTo(cx - gap - arm, cy); ctx.lineTo(cx - gap, cy);
    ctx.moveTo(cx + gap,       cy); ctx.lineTo(cx + gap + arm, cy);
    ctx.moveTo(cx, cy - gap - arm); ctx.lineTo(cx, cy - gap);
    ctx.moveTo(cx, cy + gap);       ctx.lineTo(cx, cy + gap + arm);
    ctx.stroke();
    ctx.restore();
  }

  _drawTargets() {
    const { ctx, canvas, targets, mode, _ages } = this;
    const p = PALETTE[mode];
    const W = canvas.width, H = canvas.height;

    targets.forEach((t, i) => {
      const k = `${Math.round(t.x * 20)}_${Math.round(t.y * 20)}`;
      const age = _ages.get(k) || 0;
      const locked = age > 12;
      const prog = Math.min(age / 12, 1);

      const x = t.x * W, y = t.y * H, w = t.w * W, h = t.h * H;
      const inset = (1 - prog) * Math.min(w, h) * 0.18;
      const bx = x + inset, by = y + inset, bw = w - inset*2, bh = h - inset*2;
      const bs = Math.min(bw, bh) * 0.28;

      ctx.save();
      ctx.strokeStyle = locked ? p.sec : p.pri;
      ctx.lineWidth = locked ? 2 : 1.5;
      ctx.shadowColor = locked ? p.sec : p.pri;
      ctx.shadowBlur = locked ? 14 : 6;

      this._bracket(bx, by, bw, bh, bs);

      if (locked) {
        // Pulsing inner box
        const pulse = 0.5 + 0.5 * Math.sin(Date.now() / 150);
        ctx.strokeStyle = p.sec + Math.round(pulse * 99 + 20).toString(16).padStart(2,'0');
        ctx.lineWidth = 1;
        ctx.strokeRect(bx + bs, by + bs, bw - bs*2, bh - bs*2);

        ctx.font = '11px "Share Tech Mono", monospace';
        ctx.fillStyle = p.sec;
        ctx.shadowBlur = 4;
        ctx.textAlign = 'left';
        ctx.fillText(`TGT-${String(i+1).padStart(2,'0')} ▸ LOCKED`, bx, by - 7);
      } else {
        ctx.font = '10px "Share Tech Mono", monospace';
        ctx.fillStyle = p.pri;
        ctx.textAlign = 'left';
        ctx.fillText('SCANNING...', bx, by - 7);
      }

      ctx.restore();
    });
  }

  _bracket(x, y, w, h, s) {
    const ctx = this.ctx;
    ctx.beginPath();
    ctx.moveTo(x+s, y);   ctx.lineTo(x, y);     ctx.lineTo(x, y+s);
    ctx.moveTo(x+w-s, y); ctx.lineTo(x+w, y);   ctx.lineTo(x+w, y+s);
    ctx.moveTo(x, y+h-s); ctx.lineTo(x, y+h);   ctx.lineTo(x+s, y+h);
    ctx.moveTo(x+w-s,y+h);ctx.lineTo(x+w, y+h); ctx.lineTo(x+w, y+h-s);
    ctx.stroke();
  }

  _hudText() {
    const { ctx, canvas, mode, fps, source, targets, connected, scanY } = this;
    const p = PALETTE[mode];
    const W = canvas.width, H = canvas.height;
    const t = new Date();
    const clock = [t.getHours(), t.getMinutes(), t.getSeconds()]
      .map(n => String(n).padStart(2,'0')).join(':');
    const scanPct = String(Math.round(scanY / H * 100)).padStart(3,'0');
    const tgtStr = targets.length ? `TARGETS: ${targets.length}` : 'NO TARGETS';

    ctx.save();
    ctx.font = '13px "Share Tech Mono", monospace';
    ctx.shadowColor = p.pri;
    ctx.shadowBlur = 4;

    // Top-left
    ctx.textAlign = 'left';
    ctx.fillStyle = p.txt;
    ctx.fillText('▸ PREDCAM v1.0', 14, 28);
    ctx.fillStyle = p.dim;
    ctx.fillText(`MODE : ${mode.toUpperCase()}`, 14, 46);
    ctx.fillText(`SRC  : ${source.toUpperCase()}`, 14, 64);

    // Top-right
    ctx.textAlign = 'right';
    ctx.fillStyle = p.txt;
    ctx.fillText(`FPS : ${String(fps).padStart(3,'0')}`, W - 14, 28);
    ctx.fillStyle = targets.length > 0 ? p.sec : p.dim;
    ctx.fillText(tgtStr, W - 14, 46);
    ctx.fillStyle = connected ? p.txt : '#FF4444';
    ctx.fillText(connected ? '● ONLINE' : '◌ OFFLINE', W - 14, 64);

    // Bottom-left
    ctx.textAlign = 'left';
    ctx.fillStyle = p.dim;
    ctx.fillText(`SCAN : ${scanPct}%`, 14, H - 30);
    ctx.fillText('PREDCAM // VISION SYSTEM', 14, H - 14);

    // Bottom-right
    ctx.textAlign = 'right';
    ctx.fillStyle = p.dim;
    ctx.fillText(clock, W - 14, H - 14);

    ctx.restore();
  }
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────

const canvas = document.getElementById('hud-canvas');
const hud = new PredHUD(canvas);
hud.setMode('thermal');

function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/ws/view`);
  ws.onopen  = () => { hud.connected = true; };
  ws.onclose = () => { hud.connected = false; setTimeout(connectWS, 2000); };
  ws.onerror = () => { hud.connected = false; };
  ws.onmessage = e => {
    try { hud.push(JSON.parse(e.data)); } catch {}
  };
}

connectWS();
