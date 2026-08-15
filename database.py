import sqlite3
from datetime import date

DB_NAME = "gems.db"

MISSIONS = [
    {"id": "join_channel", "title": "عضویت در کانال", "reward": 15},
    {"id": "invite_1", "title": "دعوت ۱ نفر", "reward": 20},
    {"id": "tap_50", "title": "۵۰ بار تپ کن", "reward": 10},
]

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            gems INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            tap_count INTEGER DEFAULT 0,
            referrer_id INTEGER,
            last_claim TEXT,
            referral_count INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_missions (
            user_id INTEGER,
            mission_id TEXT,
            completed INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, mission_id)
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(user_id, username, referrer_id=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)",
              (user_id, username, referrer_id))
    conn.commit()
    conn.close()

def calc_level(xp):
    return xp // 100 + 1

def add_gems(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET gems = gems + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def add_xp(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET xp = xp + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

    user = get_user(user_id)
    new_level = calc_level(user["xp"])
    if new_level != user["level"]:
        conn2 = sqlite3.connect(DB_NAME)
        c2 = conn2.cursor()
        c2.execute("UPDATE users SET level=? WHERE user_id=?", (new_level, user_id))
        conn2.commit()
        conn2.close()

def register_tap(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET tap_count = tap_count + 1, gems = gems + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    add_xp(user_id, 1)

def can_claim_daily(user_id):
    user = get_user(user_id)
    if not user:
        return True
    today = str(date.today())
    return user["last_claim"] != today

def set_last_claim(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET last_claim=? WHERE user_id=?", (str(date.today()), user_id))
    conn.commit()
    conn.close()

def increment_referral_count(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_missions_status(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT mission_id, completed FROM user_missions WHERE user_id=?", (user_id,))
    done = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    result = []
    for m in MISSIONS:
        result.append({
            "id": m["id"],
            "title": m["title"],
            "reward": m["reward"],
            "completed": bool(done.get(m["id"], 0))
        })
    return result

def complete_mission(user_id, mission_id):
    mission = next((m for m in MISSIONS if m["id"] == mission_id), None)
    if not mission:
        return False, 0

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT completed FROM user_missions WHERE user_id=? AND mission_id=?", (user_id, mission_id))
    row = c.fetchone()
    if row and row[0] == 1:
        conn.close()
        return False, 0

    c.execute("INSERT OR REPLACE INTO user_missions (user_id, mission_id, completed) VALUES (?, ?, 1)",
               (user_id, mission_id))
    conn.commit()
    conn.close()
    add_gems(user_id, mission["reward"])
    add_xp(user_id, mission["reward"])
    return True, mission["reward"]
