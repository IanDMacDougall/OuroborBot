/* ============================================================
   socket.js — SocketIO client for OroborBot
   Responsibilities:
     · Connect to the Flask-SocketIO server
     · Handle Start / Stop / Reset button interactions
     · Receive game_update events → pass state to GameRenderer
     · Receive stats_update events → update all stat DOM elements
     · Manage panel status badges and death overlays
   ============================================================ */

(() => {
    'use strict';

    // ── SocketIO connection ───────────────────────────────────
    const socket = io();

    // ── DOM references ────────────────────────────────────────
    const btnStart  = document.getElementById('btn-start');
    const btnStop   = document.getElementById('btn-stop');
    const btnReset  = document.getElementById('btn-reset');
    const algoSel1  = document.getElementById('algo-1');
    const algoSel2  = document.getElementById('algo-2');
    const tickSel   = document.getElementById('tick-rate');

    // Status badges
    const status1   = document.getElementById('status-1');
    const status2   = document.getElementById('status-2');

    // Death overlays
    const overlay1  = document.getElementById('death-overlay-1');
    const overlay2  = document.getElementById('death-overlay-2');
    const cause1    = document.getElementById('death-cause-1');
    const cause2    = document.getElementById('death-cause-2');

    // Algorithm badges in stats panel
    const algoBadge1 = document.getElementById('algo-badge-1');
    const algoBadge2 = document.getElementById('algo-badge-2');

    // ── Stat element map ──────────────────────────────────────
    // Keyed by player number → stat key → element id
    const STAT_IDS = {
        1: {
            score:       's1-score',
            length:      's1-length',
            steps:       's1-steps',
            best_score:  's1-best-score',
            best_length: 's1-best-length',
            avg_score:   's1-avg-score',
            games:       's1-games',
            wall:        's1-wall',
            self:        's1-self',
            starve:      's1-starve',
            // head-to-head
            cmp_score:   'cmp-score-1',
            cmp_len:     'cmp-len-1',
            cmp_avg:     'cmp-avg-1',
            cmp_games:   'cmp-games-1',
        },
        2: {
            score:       's2-score',
            length:      's2-length',
            steps:       's2-steps',
            best_score:  's2-best-score',
            best_length: 's2-best-length',
            avg_score:   's2-avg-score',
            games:       's2-games',
            wall:        's2-wall',
            self:        's2-self',
            starve:      's2-starve',
            // head-to-head
            cmp_score:   'cmp-score-2',
            cmp_len:     'cmp-len-2',
            cmp_avg:     'cmp-avg-2',
            cmp_games:   'cmp-games-2',
        },
    };

    // ── Session state ─────────────────────────────────────────
    let gameRunning = false;

    // Track last-known best scores for the comparison bar
    const sessionBest = { 1: 0, 2: 0 };

    // Overlay auto-hide timers
    const overlayTimers = { 1: null, 2: null };

    // ── Button handlers ───────────────────────────────────────
    btnStart.addEventListener('click', () => {
        const payload = {
            algo1:     algoSel1.value,
            algo2:     algoSel2.value,
            tick_rate: parseInt(tickSel.value, 10),
            grid_size: 20,
        };
        socket.emit('start_game', payload);
    });

    btnStop.addEventListener('click', () => {
        socket.emit('stop_game');
    });

    btnReset.addEventListener('click', () => {
        const payload = {
            algo1:     algoSel1.value,
            algo2:     algoSel2.value,
            tick_rate: parseInt(tickSel.value, 10),
            grid_size: 20,
        };
        socket.emit('reset_game', payload);
        // Reset session bests for a fresh comparison
        sessionBest[1] = 0;
        sessionBest[2] = 0;
    });

    // ── SocketIO event handlers ───────────────────────────────

    socket.on('connect', () => {
        console.log('[OroborBot] connected', socket.id);
    });

    socket.on('disconnect', () => {
        console.log('[OroborBot] disconnected');
        _setRunning(false);
        _setStatus(1, 'idle');
        _setStatus(2, 'idle');
    });

    socket.on('game_started', (data) => {
        console.log('[OroborBot] game started', data);
        _setRunning(true);
        _setStatus(1, 'running');
        _setStatus(2, 'running');
        _hideOverlay(1, true);
        _hideOverlay(2, true);

        // Update algorithm badges in stats panel
        algoBadge1.textContent = data.algo1.toUpperCase();
        algoBadge2.textContent = data.algo2.toUpperCase();
    });

    socket.on('game_stopped', () => {
        _setRunning(false);
        _setStatus(1, 'idle');
        _setStatus(2, 'idle');
        GameRenderer.drawIdle(1);
        GameRenderer.drawIdle(2);
    });

    socket.on('error', (data) => {
        console.error('[OroborBot] server error:', data.message);
        alert(`Server error: ${data.message}`);
    });

    // ── Core: game state update ───────────────────────────────
    socket.on('game_update', (data) => {
        const { game1, game2, restarted1, restarted2 } = data;

        // ---- Board 1 ----
        if (restarted1) {
            _showOverlay(1, game1.cause_of_death ?? 'unknown');
            _scheduleHideOverlay(1);
            _setStatus(1, 'dead');
        } else {
            GameRenderer.draw(1, game1, false);
            if (game1.alive) _setStatus(1, 'running');
        }

        // ---- Board 2 ----
        if (restarted2) {
            _showOverlay(2, game2.cause_of_death ?? 'unknown');
            _scheduleHideOverlay(2);
            _setStatus(2, 'dead');
        } else {
            GameRenderer.draw(2, game2, false);
            if (game2.alive) _setStatus(2, 'running');
        }
    });

    // ── Stats update ─────────────────────────────────────────
    socket.on('stats_update', (data) => {
        _updateStatCard(1, data.game1);
        _updateStatCard(2, data.game2);
        _updateCompareBar(data.game1.best_score, data.game2.best_score);
    });

    // ── Stat card renderer ────────────────────────────────────
    function _updateStatCard(player, s) {
        const ids = STAT_IDS[player];

        _setText(ids.score,       s.current_score);
        _setText(ids.length,      s.current_length);
        _setText(ids.steps,       s.current_steps);
        _setText(ids.best_score,  s.best_score);
        _setText(ids.best_length, s.best_length);
        _setText(ids.avg_score,   s.avg_score.toFixed(2));
        _setText(ids.games,       s.games_played);
        _setText(ids.wall,        s.wall_deaths);
        _setText(ids.self,        s.self_deaths);
        _setText(ids.starve,      s.starvations);

        // Head-to-head column
        _setText(ids.cmp_score,   s.best_score);
        _setText(ids.cmp_len,     s.best_length);
        _setText(ids.cmp_avg,     s.avg_score.toFixed(2));
        _setText(ids.cmp_games,   s.games_played);

        // Track session best for the compare bar
        sessionBest[player] = s.best_score;

        // Highlight leader values in compare panel
        _refreshLeaderHighlight();
    }

    // ── Head-to-head compare bar ──────────────────────────────
    function _updateCompareBar(score1, score2) {
        const bar   = document.getElementById('compare-bar');
        const total = score1 + score2;

        if (total === 0) {
            bar.style.left  = '50%';
            bar.style.width = '0%';
            bar.classList.remove('p2-leads');
            return;
        }

        const p1Share = score1 / total;   // 0..1
        const lead    = Math.abs(p1Share - 0.5) * 100;  // how far from centre

        if (score1 >= score2) {
            // P1 leads — bar grows leftward from centre
            bar.style.left  = `${(p1Share * 100 - lead)}%`;
            bar.style.width = `${lead}%`;
            bar.classList.remove('p2-leads');
        } else {
            // P2 leads — bar grows rightward from centre
            bar.style.left  = '50%';
            bar.style.width = `${lead}%`;
            bar.classList.add('p2-leads');
        }
    }

    // Highlight whichever player is leading in the compare rows
    function _refreshLeaderHighlight() {
        const s1 = sessionBest[1];
        const s2 = sessionBest[2];

        ['cmp-score-1','cmp-len-1','cmp-avg-1','cmp-games-1'].forEach(id => {
            document.getElementById(id)?.classList.toggle('leading', s1 >= s2);
        });
        ['cmp-score-2','cmp-len-2','cmp-avg-2','cmp-games-2'].forEach(id => {
            document.getElementById(id)?.classList.toggle('leading', s2 > s1);
        });
    }

    // ── UI helpers ────────────────────────────────────────────
    function _setRunning(running) {
        gameRunning  = running;
        btnStart.disabled = running;
        btnStop.disabled  = !running;
        btnReset.disabled = !running;
        algoSel1.disabled = running;
        algoSel2.disabled = running;
    }

    function _setStatus(player, state) {
        // state: 'idle' | 'running' | 'dead'
        const el = player === 1 ? status1 : status2;
        el.textContent = state.toUpperCase();
        el.className   = `panel-status ${state}`;
    }

    function _showOverlay(player, cause) {
        const overlay = player === 1 ? overlay1 : overlay2;
        const causeEl = player === 1 ? cause1   : cause2;
        causeEl.textContent = _formatCause(cause);
        overlay.classList.add('visible');
    }

    function _hideOverlay(player, immediate = false) {
        const overlay = player === 1 ? overlay1 : overlay2;
        if (immediate) {
            overlay.classList.remove('visible');
        } else {
            overlay.classList.remove('visible');
        }
    }

    function _scheduleHideOverlay(player) {
        // Clear any existing timer for this board
        if (overlayTimers[player]) clearTimeout(overlayTimers[player]);

        // Show overlay briefly then hide and resume rendering
        overlayTimers[player] = setTimeout(() => {
            _hideOverlay(player);
            _setStatus(player, 'running');
        }, 900);
    }

    function _setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    function _formatCause(cause) {
        switch (cause) {
            case 'wall':        return '// HIT WALL';
            case 'self':        return '// HIT SELF';
            case 'starvation':  return '// STARVATION';
            default:            return `// ${cause.toUpperCase()}`;
        }
    }

})();