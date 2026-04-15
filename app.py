import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
import time

app = Flask(__name__)
app.config["SECRET_KEY"] = "oroborbot-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")


ALGORITHM_MAP = {}


# '''
# Popualtes the Algorithm map using the imports from algortihms.
# 
# Returns the algorithm map.
# '''
def load_algorithms():
    global ALGORITHM_MAP
    try:
        from algorithms.random_agent import RandomAgent
        from algorithms.astar import AStarAgent
        from algorithms.bfs import BFSAgent
        from algorithms.csp import CSPAgent
        from algorithms.dfs import DFSAgent
        ALGORITHM_MAP = {
            "random":      RandomAgent,
            "astar":       AStarAgent,
            "bfs":         BFSAgent,
            "csp":         CSPAgent,
            "dsf":         DFSAgent,
        }
    except ImportError:
        # Modules not yet created - safe for now
        ALGORITHM_MAP = {}

#
# Active game sessions  {sid: GameSession}
#
active_sessions = {}

#
# Routes
#
@app.route("/")
def index():
    algorithms = list(ALGORITHM_MAP.keys()) if ALGORITHM_MAP else []
    return render_template("index.html", algorithms=algorithms)

#
# SocketIO events
#
@socketio.on("connect")
def on_connect():
    print(f"[connect] client {request_sid()}")

@socketio.on("disconnect")
def on_disconnect():
    sid = request_sid()
    print(f"[disconnect] client {sid}")
    session = active_sessions.pop(sid, None)
    if session:
        session.stop()

@socketio.on("start_game")
def on_start_game(data):
    """
    Expected payload:
        {
            "algo1": "random",
            "algo2": "random",
            "grid_size": 20,   # optional, default 20
            "tick_rate": 10    # optional, steps per second, default 10
        }
    """
    from game.session import GameSession

    sid = request_sid()

    # Stop any existing session for this client
    old = active_sessions.pop(sid, None)
    if old:
        old.stop()

    algo1_key = data.get("algo1", "random")
    algo2_key = data.get("algo2", "random")
    grid_size  = int(data.get("grid_size", 20))
    tick_rate  = int(data.get("tick_rate", 10))

    load_algorithms()

    AgentClass1 = ALGORITHM_MAP.get(algo1_key)
    AgentClass2 = ALGORITHM_MAP.get(algo2_key)

    if not AgentClass1 or not AgentClass2:
        emit("error", {"message": f"Unknown algorithm: '{algo1_key}' or '{algo2_key}'"})
        return

    session = GameSession(
        sid=sid,
        agent1=AgentClass1(grid_size),
        agent2=AgentClass2(grid_size),
        grid_size=grid_size,
        tick_rate=tick_rate,
        socketio=socketio,
    )
    active_sessions[sid] = session
    session.start()
    emit("game_started", {"algo1": algo1_key, "algo2": algo2_key, "grid_size": grid_size})



@socketio.on("stop_game")
def on_stop_game():
    sid = request_sid()
    session = active_sessions.pop(sid, None)
    if session:
        session.stop()
    emit("game_stopped", {})



@socketio.on("reset_game")
def on_reset_game(data):
    """Reset and restart with the same or updated algorithm choices."""
    on_stop_game()
    on_start_game(data)



# '''
# Helper
# '''
def request_sid():
    from flask import request
    return request.sid



# '''
# Entry point
# '''
if __name__ == "__main__":
    load_algorithms()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)