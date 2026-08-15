from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import database as db

app = Flask(__name__)
CORS(app)

db.init_db()


def ensure_user(user_id, username=""):
    user = db.get_user(user_id)
    if not user:
        db.create_user(user_id, username)
        user = db.get_user(user_id)
    return user


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/user/<int:user_id>")
def api_user(user_id):
    username = request.args.get("username", "")
    user = ensure_user(user_id, username)
    return jsonify(user)


@app.route("/api/tap", methods=["POST"])
def api_tap():
    data = request.json
    user_id = data.get("user_id")
    ensure_user(user_id)
    db.register_tap(user_id)
    user = db.get_user(user_id)
    return jsonify(user)


@app.route("/api/daily", methods=["POST"])
def api_daily():
    data = request.json
    user_id = data.get("user_id")
    ensure_user(user_id)
    if db.can_claim_daily(user_id):
        db.add_gems(user_id, 10)
        db.add_xp(user_id, 10)
        db.set_last_claim(user_id)
        claimed = True
    else:
        claimed = False
    user = db.get_user(user_id)
    return jsonify({"claimed": claimed, "user": user})


@app.route("/api/missions/<int:user_id>")
def api_missions(user_id):
    ensure_user(user_id)
    missions = db.get_missions_status(user_id)
    return jsonify(missions)


@app.route("/api/missions/complete", methods=["POST"])
def api_complete_mission():
    data = request.json
    user_id = data.get("user_id")
    mission_id = data.get("mission_id")
    ensure_user(user_id)
    success, reward = db.complete_mission(user_id, mission_id)
    user = db.get_user(user_id)
    return jsonify({"success": success, "reward": reward, "user": user})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
