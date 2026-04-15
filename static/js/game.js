/* ============================================================
   game.js — Canvas rendering for both Snake boards
   Draws grid, food, snake body, head, and idle screen.
   Called by socket.js whenever a game_update event arrives.
   ============================================================ */

(() => {
    'use strict';

    // ── Render constants ──────────────────────────────────────
    const COLORS = {
        bg:          '#080c08',
        gridLine:    'rgba(57, 255, 20, 0.04)',

        // Snake body gradient stops (tail → neck)
        bodyTail:    '#0d3b0a',
        bodyMid:     '#145c09',
        bodyNeck:    '#1a8c0a',

        // Head
        headFill:    '#39ff14',
        headGlow:    'rgba(57, 255, 20, 0.6)',

        // Eye
        eyeFill:     '#080c08',

        // Food
        foodFill:    '#ffb800',
        foodGlow:    'rgba(255, 184, 0, 0.7)',
        foodPulse:   'rgba(255, 184, 0, 0.15)',

        // Border flash on food eaten
        flashColor:  'rgba(57, 255, 20, 0.5)',
    };

    // Pixels added around each cell so body segments look connected
    const CELL_PADDING = 1;

    // ── Canvas references ─────────────────────────────────────
    const canvases = {
        1: document.getElementById('canvas-1'),
        2: document.getElementById('canvas-2'),
    };
    const contexts = {
        1: canvases[1].getContext('2d'),
        2: canvases[2].getContext('2d'),
    };

    // Per-board animation state
    const boardState = {
        1: { foodPulse: 0, flashAlpha: 0, lastFood: null },
        2: { foodPulse: 0, flashAlpha: 0, lastFood: null },
    };

    // ── Public API (attached to window for socket.js) ─────────
    window.GameRenderer = {
        draw,
        drawIdle,
    };

    // ── Draw a full game state ────────────────────────────────
    /**
     * @param {1|2}    boardId   which canvas to draw on
     * @param {object} state     SnakeGame.get_state() dict from server
     * @param {boolean} ateFood  whether the snake ate food this tick
     */
    function draw(boardId, state, ateFood = false) {
        const ctx       = contexts[boardId];
        const bs        = boardState[boardId];
        const canvas    = canvases[boardId];
        const gridSize  = state.grid_size;
        const cellSize  = canvas.width / gridSize;

        // Trigger effects
        if (ateFood) {
            bs.flashAlpha = 1.0;
        }
        bs.foodPulse = (bs.foodPulse + 0.12) % (Math.PI * 2);

        // 1 — Background
        ctx.fillStyle = COLORS.bg;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // 2 — Grid lines
        _drawGrid(ctx, canvas.width, canvas.height, gridSize, cellSize);

        // 3 — Food
        _drawFood(ctx, bs, state.food, cellSize);

        // 4 — Snake body (tail → head, so head draws on top)
        const snake = state.snake;
        for (let i = snake.length - 1; i >= 1; i--) {
            const t = i / snake.length;              // 1 at tail → 0 at neck
            _drawSegment(ctx, snake[i], snake[i - 1], snake[i + 1] ?? null,
                         cellSize, t);
        }

        // 5 — Head
        _drawHead(ctx, snake, state.direction, cellSize);

        // 6 — Border flash on food eaten
        if (bs.flashAlpha > 0) {
            ctx.strokeStyle = COLORS.flashColor;
            ctx.lineWidth   = 4;
            ctx.globalAlpha = bs.flashAlpha;
            ctx.strokeRect(2, 2, canvas.width - 4, canvas.height - 4);
            ctx.globalAlpha = 1;
            bs.flashAlpha   = Math.max(0, bs.flashAlpha - 0.08);
        }
    }

    // ── Draw the idle/waiting screen ─────────────────────────
    function drawIdle(boardId) {
        const ctx    = contexts[boardId];
        const canvas = canvases[boardId];
        const w      = canvas.width;
        const h      = canvas.height;

        ctx.fillStyle = COLORS.bg;
        ctx.fillRect(0, 0, w, h);

        // Subtle grid
        _drawGrid(ctx, w, h, 20, w / 20);

        // Centred prompt
        ctx.fillStyle   = 'rgba(57, 255, 20, 0.18)';
        ctx.font        = '10px "Press Start 2P"';
        ctx.textAlign   = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('SELECT', w / 2, h / 2 - 16);
        ctx.fillText('ALGORITHM', w / 2, h / 2);
        ctx.fillText('& START', w / 2, h / 2 + 16);
        ctx.textBaseline = 'alphabetic';
    }

    // ── Grid ─────────────────────────────────────────────────
    function _drawGrid(ctx, w, h, gridSize, cellSize) {
        ctx.strokeStyle = COLORS.gridLine;
        ctx.lineWidth   = 0.5;
        ctx.beginPath();
        for (let i = 0; i <= gridSize; i++) {
            const x = i * cellSize;
            const y = i * cellSize;
            ctx.moveTo(x, 0); ctx.lineTo(x, h);
            ctx.moveTo(0, y); ctx.lineTo(w, y);
        }
        ctx.stroke();
    }

    // ── Food ─────────────────────────────────────────────────
    function _drawFood(ctx, bs, food, cellSize) {
        if (!food || food[0] < 0) return;

        const [fr, fc] = food;
        const x  = fc * cellSize;
        const y  = fr * cellSize;
        const cx = x + cellSize / 2;
        const cy = y + cellSize / 2;
        const r  = (cellSize / 2) * 0.55;

        // Pulse halo
        const pulseR = r + Math.sin(bs.foodPulse) * 2.5;
        ctx.beginPath();
        ctx.arc(cx, cy, pulseR + 4, 0, Math.PI * 2);
        ctx.fillStyle = COLORS.foodPulse;
        ctx.fill();

        // Glow
        const grd = ctx.createRadialGradient(cx, cy, 0, cx, cy, r * 1.6);
        grd.addColorStop(0, COLORS.foodGlow);
        grd.addColorStop(1, 'transparent');
        ctx.beginPath();
        ctx.arc(cx, cy, r * 1.6, 0, Math.PI * 2);
        ctx.fillStyle = grd;
        ctx.fill();

        // Core diamond
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(Math.PI / 4);
        ctx.fillStyle = COLORS.foodFill;
        ctx.fillRect(-r * 0.65, -r * 0.65, r * 1.3, r * 1.3);
        ctx.restore();
    }

    // ── Body segment ─────────────────────────────────────────
    /**
     * Draws one body cell as a slightly padded rectangle so
     * adjacent cells visually merge into a continuous tube.
     *
     * t = 1 (tail) → dim colour   t = 0 (neck) → bright colour
     */
    function _drawSegment(ctx, pos, nextPos, prevPos, cellSize, t) {
        const [r, c] = pos;

        // Lerp colour from tail-dim to neck-bright
        const color = _lerpColor(COLORS.bodyNeck, COLORS.bodyTail, t);

        const pad = CELL_PADDING;
        let x = c * cellSize + pad;
        let y = r * cellSize + pad;
        let w = cellSize - pad * 2;
        let h = cellSize - pad * 2;

        // Extend the rectangle toward neighbours so there's no gap
        if (nextPos) {
            const dr = nextPos[0] - pos[0];
            const dc = nextPos[1] - pos[1];
            if (dr === -1) { y -= pad; h += pad; }
            if (dr ===  1) { h += pad; }
            if (dc === -1) { x -= pad; w += pad; }
            if (dc ===  1) { w += pad; }
        }
        if (prevPos) {
            const dr = prevPos[0] - pos[0];
            const dc = prevPos[1] - pos[1];
            if (dr === -1) { y -= pad; h += pad; }
            if (dr ===  1) { h += pad; }
            if (dc === -1) { x -= pad; w += pad; }
            if (dc ===  1) { w += pad; }
        }

        ctx.fillStyle = color;
        ctx.fillRect(x, y, w, h);
    }

    // ── Head ──────────────────────────────────────────────────
    function _drawHead(ctx, snake, direction, cellSize) {
        if (!snake || snake.length === 0) return;

        const [r, c]  = snake[0];
        const x       = c * cellSize;
        const y       = r * cellSize;
        const s       = cellSize;

        // Glow
        const grd = ctx.createRadialGradient(
            x + s / 2, y + s / 2, 0,
            x + s / 2, y + s / 2, s * 0.9
        );
        grd.addColorStop(0, COLORS.headGlow);
        grd.addColorStop(1, 'transparent');
        ctx.fillStyle = grd;
        ctx.fillRect(x - s * 0.4, y - s * 0.4, s * 1.8, s * 1.8);

        // Head block
        ctx.fillStyle = COLORS.headFill;
        ctx.fillRect(x + CELL_PADDING, y + CELL_PADDING,
                     s - CELL_PADDING * 2, s - CELL_PADDING * 2);

        // Eyes (two small dark squares offset by direction)
        _drawEyes(ctx, x, y, s, direction);
    }

    // ── Eyes ─────────────────────────────────────────────────
    function _drawEyes(ctx, hx, hy, s, direction) {
        // Direction: 0=UP 1=RIGHT 2=DOWN 3=LEFT
        const eyeSize = Math.max(2, s * 0.12);
        const inset   = s * 0.22;
        const forward = s * 0.68;

        let eyes;
        switch (direction) {
            case 0: // UP
                eyes = [
                    [hx + inset,          hy + s - forward],
                    [hx + s - inset - eyeSize, hy + s - forward],
                ]; break;
            case 1: // RIGHT
                eyes = [
                    [hx + forward - eyeSize, hy + inset],
                    [hx + forward - eyeSize, hy + s - inset - eyeSize],
                ]; break;
            case 2: // DOWN
                eyes = [
                    [hx + inset,          hy + forward - eyeSize],
                    [hx + s - inset - eyeSize, hy + forward - eyeSize],
                ]; break;
            case 3: // LEFT
                eyes = [
                    [hx + s - forward, hy + inset],
                    [hx + s - forward, hy + s - inset - eyeSize],
                ]; break;
            default:
                return;
        }

        ctx.fillStyle = COLORS.eyeFill;
        for (const [ex, ey] of eyes) {
            ctx.fillRect(ex, ey, eyeSize, eyeSize);
        }
    }

    // ── Colour lerp helper ────────────────────────────────────
    /**
     * Linearly interpolate between two hex colours.
     * t = 0 → colA,  t = 1 → colB
     */
    function _lerpColor(colA, colB, t) {
        const a = _hexToRgb(colA);
        const b = _hexToRgb(colB);
        const r = Math.round(a.r + (b.r - a.r) * t);
        const g = Math.round(a.g + (b.g - a.g) * t);
        const bl = Math.round(a.b + (b.b - a.b) * t);
        return `rgb(${r},${g},${bl})`;
    }

    function _hexToRgb(hex) {
        const n = parseInt(hex.replace('#', ''), 16);
        return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
    }

    // ── Init both canvases to idle on page load ───────────────
    drawIdle(1);
    drawIdle(2);

})();