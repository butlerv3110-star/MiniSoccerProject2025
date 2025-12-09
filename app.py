from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime
import json
import os
import random

app = Flask(__name__)
app.secret_key = "L@ra4Dan!1l@K!3r@nR3dBr!g8"

LEADERBOARD_FILE = "leaderboard.json"

# ----------------------
# Leaderboard helpers
# ----------------------
def load_leaderboard():
    if not os.path.exists(LEADERBOARD_FILE):
        return []
    with open(LEADERBOARD_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return []

def save_result(entry):
    lb = load_leaderboard()
    lb.append(entry)
    lb = lb[-50:]
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(lb, f, indent=2)

# ----------------------
# Main routes
# ----------------------
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/start_game", methods=["POST"])
def start_game():
    chosen_player = request.form.get("player")
    custom_name = request.form.get("custom_name", "").strip()

    if chosen_player == "custom" and custom_name:
        player_name = custom_name
        chosen = "Myself"
    else:
        player_name = chosen_player
        chosen = chosen_player

    health = int(request.form.get("health"))

    # Save player in session
    session["player"] = {"name": player_name, "chosen": chosen, "health": health}
    session["game"] = {
        "player_name": player_name,
        "chosen_player": chosen,
        "health": health,
        "score": {"player": 0, "opponent": 0},
        "events": []
    }

    return render_template("kick.html", game=session["game"])

@app.route("/kick")
def kick():
    if "game" not in session:
        return redirect(url_for("index"))
    return render_template("kick.html", game=session["game"])

# ----------------------
# Update health & score
# ----------------------
@app.route("/update_health", methods=["POST"])
def update_health():
    amount = int(request.json.get("amount", 0))
    player = session.get("player", {})
    player.setdefault("health", 100)
    player["health"] = max(0, player["health"] + amount)
    session["player"] = player
    session["game"]["health"] = player["health"]
    return jsonify({"health": player["health"]})

@app.route("/score_event", methods=["POST"])
def score_event():
    data = request.json or {}
    who = data.get("who")
    inc = int(data.get("inc", 1))
    game = session.get("game", {})
    game.setdefault("score", {"player": 0, "opponent": 0})
    if who in game["score"]:
        game["score"][who] += inc
    session["game"] = game
    return jsonify(game["score"])

# ----------------------
# Tackles / fouls
# ----------------------
@app.route("/tackle_event", methods=["POST"])
def tackle_event():
    ref_sees = random.random() < 0.6
    player = session.get("player", {})
    message = ""
    if ref_sees:
        message = "Foul! Ref saw the tackle, penalty awarded."
    else:
        message = "Opponent tackled you, ref did not see. Health reduced."
        player["health"] = max(0, player.get("health", 100) - 10)
        session["player"] = player
        if "game" in session:
            session["game"]["health"] = player["health"]

    if "game" in session:
        session["game"].setdefault("events", []).append({
            "tackle": True,
            "ref_sees": ref_sees,
            "time": datetime.utcnow().isoformat()
        })

    # If ref sees foul, send flag to client
    return jsonify({"message": message, "health": player.get("health", 0), "ref_sees": ref_sees})

@app.route("/ref_sees", methods=["POST"])
def ref_sees():
    sees = random.random() < 0.6
    session["game"].setdefault("events", []).append({"ref_sees": sees})
    return jsonify({"ref_sees": sees})

@app.route("/in_game_penalty")
def in_game_penalty():
    """Called when a foul in box is seen by ref; redirect player to penalty kicks."""
    game = session.get("game", {})
    return render_template("penalty_kicks.html", game=game)

# ----------------------
# End of play & penalties
# ----------------------
@app.route("/end_of_play")
def end_of_play():
    game = session.get("game", {})
    score = game.get("score", {"player": 0, "opponent": 0})
    if score["player"] == score["opponent"]:
        return render_template("end_of_play.html", game=game, score=score)
    else:
        return redirect(url_for("game_over"))

@app.route("/penalty_kicks")
def penalty_kicks():
    return render_template("penalty_kicks.html", game=session.get("game", {}))

@app.route("/penalty/<side>", methods=["POST"])
def penalty_side(side):
    keeper = random.choice(["left", "middle", "right"])
    scored = (side != keeper)
    game = session.get("game")
    player = session.get("player")

    if scored:
        game["score"]["player"] += 1
    else:
        player["health"] = max(0, player["health"] - 5)

    # Save session
    session["player"] = player
    session["game"] = game

    # Return JSON including flag to go back to in-game
    return jsonify({
        "scored": scored,
        "keeper": keeper,
        "score": game["score"],
        "health": player["health"]
    })

# ----------------------
# Game over & leaderboard
# ----------------------
@app.route("/game_over")
def game_over():
    player = session.get("player", {})
    game = session.get("game", {})
    entry = {
        "name": player.get("name", "Unknown"),
        "chosen": player.get("chosen", "Self"),
        "score": game.get("score", {}),
        "health": player.get("health", 0),
        "time": datetime.utcnow().isoformat()
    }
    save_result(entry)
    return render_template("game_over.html", entry=entry)

@app.route("/results")
def results():
    return render_template("results.html", player=session.get("player", {}), game=session.get("game", {}))

@app.route("/all_results")
def all_results():
    return render_template("all_results.html", leaderboard=reversed(load_leaderboard()))

@app.route("/reset")
def reset():
    session.clear()
    return redirect(url_for("index"))

# ----------------------
# Run server
# ----------------------
if __name__ == "__main__":
    app.run(debug=True)
