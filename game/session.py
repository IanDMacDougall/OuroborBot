import threading
import time
from game.snake import SnakeGame, Direction

# How long (in steps) a snake can go without eating before it is
# considered to be looping and is killed.
STARVATION_LIMIT_MULTIPLIER = 2   # grid_size * grid_size * multiplier


class GameSession:
    """
    Manages a full two-snake session for one connected browser client.

    Parameters
    ----------
    sid        : SocketIO session ID of the owning client.
    agent1/2   : Instantiated algorithm objects (subclass of BaseAgent).
    grid_size  : Board dimension (grid_size x grid_size cells).
    tick_rate  : Game steps per second.
    socketio   : The Flask-SocketIO server instance.
    """

    def __init__(self, sid, agent1, agent2, grid_size, tick_rate, socketio):
        self.sid       = sid
        self.agent1    = agent1
        self.agent2    = agent2
        self.grid_size = grid_size
        self.tick_rate = tick_rate
        self.socketio  = socketio

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        # Per-game cumulative stats (persist across restarts within a session)
        self._session_stats = {
            1: _blank_session_stats(),
            2: _blank_session_stats(),
        }

        self._starvation_limit = grid_size * grid_size * STARVATION_LIMIT_MULTIPLIER

    """
    Lifecycle of game
    """


    #
    # Spawn the game thread
    #
    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    #
    # Signal to the game thread to stop
    # - wait for exit 
    #
    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

    #
    # Main loop
    #

    def _loop(self):
        game1 = SnakeGame(self.grid_size)
        game2 = SnakeGame(self.grid_size)

        # Per-game run stats (reset each time a game restarts)
        run1 = _blank_run_stats()
        run2 = _blank_run_stats()

        # Steps since last food for starvation detection
        steps_since_food1 = 0
        steps_since_food2 = 0

        tick_interval = 1.0 / self.tick_rate

        while not self._stop_event.is_set():
            tick_start = time.monotonic()

            # Game 1
            if game1.alive:
                state1  = game1.get_state()
                action1 = self._safe_get_action(self.agent1, state1, game1)
                result1 = game1.step(action1)

                if result1.ate_food:
                    steps_since_food1 = 0
                else:
                    steps_since_food1 += 1

                # Starvation check
                if steps_since_food1 >= self._starvation_limit:
                    game1.alive = False
                    game1.cause_of_death = "starvation"

                run1["steps"]    = result1.steps
                run1["score"]    = result1.score
                run1["max_len"]  = max(run1["max_len"], result1.length)

            # Game 2
            if game2.alive:
                state2  = game2.get_state()
                action2 = self._safe_get_action(self.agent2, state2, game2)
                result2 = game2.step(action2)

                if result2.ate_food:
                    steps_since_food2 = 0
                else:
                    steps_since_food2 += 1

                if steps_since_food2 >= self._starvation_limit:
                    game2.alive = False
                    game2.cause_of_death = "starvation"

                run2["steps"]   = result2.steps
                run2["score"]   = result2.score
                run2["max_len"] = max(run2["max_len"], result2.length)

            # Handle deaths & auto-restart
            restarted1 = restarted2 = False

            if not game1.alive:
                self._record_death(player=1, game=game1, run=run1)
                game1 = SnakeGame(self.grid_size)
                self.agent1.reset()
                run1 = _blank_run_stats()
                steps_since_food1 = 0
                restarted1 = True

            if not game2.alive:
                self._record_death(player=2, game=game2, run=run2)
                game2 = SnakeGame(self.grid_size)
                self.agent2.reset()
                run2 = _blank_run_stats()
                steps_since_food2 = 0
                restarted2 = True

            # Push state to browser
            self.socketio.emit(
                "game_update",
                {
                    "game1": game1.get_state(),
                    "game2": game2.get_state(),
                    "restarted1": restarted1,
                    "restarted2": restarted2,
                },
                to=self.sid,
            )

            self.socketio.emit(
                "stats_update",
                {
                    "game1": _build_stats_payload(run1, self._session_stats[1]),
                    "game2": _build_stats_payload(run2, self._session_stats[2]),
                },
                to=self.sid,
            )

            # ---------- Pace the loop ----------
            elapsed = time.monotonic() - tick_start
            sleep_for = tick_interval - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

    #
    # Helpers
    #

    def _safe_get_action(self, agent, state: dict, game: SnakeGame) -> Direction:
        """
        Call the agent's get_action(), defaulting to the current heading
        if the agent raises or returns an invalid value.
        """
        try:
            action = agent.get_action(state, game)
            if not isinstance(action, Direction):
                action = Direction(int(action))
            return action
        except Exception as exc:
            print(f"[session] agent {type(agent).__name__} error: {exc}")
            return Direction(state["direction"])

    def _record_death(self, player: int, game: SnakeGame, run: dict):
        """Fold completed-run stats into the session totals."""
        s = self._session_stats[player]
        s["games"]        += 1
        s["total_score"]  += run["score"]
        s["total_steps"]  += run["steps"]
        s["best_score"]    = max(s["best_score"],  run["score"])
        s["best_length"]   = max(s["best_length"], run["max_len"])
        s["wall_deaths"]  += 1 if game.cause_of_death == "wall"        else 0
        s["self_deaths"]  += 1 if game.cause_of_death == "self"        else 0
        s["starvations"]  += 1 if game.cause_of_death == "starvation"  else 0


#
# Stat-dict factories
#

def _blank_run_stats() -> dict:
    """Stats tracked for the current (active) game run."""
    return {
        "score":   0,
        "steps":   0,
        "max_len": 3,   # snake starts with length 3
    }

def _blank_session_stats() -> dict:
    """Cumulative stats across all completed runs this session."""
    return {
        "games":        0,
        "total_score":  0,
        "total_steps":  0,
        "best_score":   0,
        "best_length":  3,
        "wall_deaths":  0,
        "self_deaths":  0,
        "starvations":  0,
    }

def _build_stats_payload(run: dict, session: dict) -> dict:
    """
    Merge the live run stats with session totals into a single dict
    that the browser's stats panel can render directly.
    """
    games_played = session["games"]  # completed games only
    total_score  = session["total_score"] + run["score"]
    avg_score    = round(total_score / (games_played + 1), 2)

    return {
        # Live run
        "current_score":  run["score"],
        "current_steps":  run["steps"],
        "current_length": run["max_len"],
        # Session bests
        "best_score":     max(session["best_score"],  run["score"]),
        "best_length":    max(session["best_length"], run["max_len"]),
        # Averages (include the current run in the denominator)
        "games_played":   games_played + 1,
        "avg_score":      avg_score,
        # Death breakdown
        "wall_deaths":    session["wall_deaths"],
        "self_deaths":    session["self_deaths"],
        "starvations":    session["starvations"],
    }
