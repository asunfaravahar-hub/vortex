"""
اسکریپت خودکار ساخت پروژه بات جم با Mini App گرافیکی
فقط کافیه این فایل رو داخل پوشه gem-bot بذاری و اجرا کنی:
    python setup_game.py
همه پوشه‌ها و فایل‌های لازم رو خودش می‌سازه.
"""

import os

# ---------- محتوای فایل‌ها ----------

DATABASE_PY = '''import sqlite3
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
'''

APP_PY = '''from flask import Flask, request, jsonify, render_template
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
'''

INDEX_HTML = '''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Gem Quest</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>

<div class="app">
  <div class="top-bar">
    <div class="level-box">
      <span id="level">1</span>
      <small>Level</small>
    </div>
    <div class="xp-bar-container">
      <div class="xp-bar" id="xpBar"></div>
    </div>
  </div>

  <div class="gems-display">
    <img src="https://cdn-icons-png.flaticon.com/512/2933/2933116.png" class="gem-icon" alt="gem">
    <span id="gemsCount">0</span>
  </div>

  <div class="tap-area">
    <button id="tapButton" class="tap-button">
      <img src="https://cdn-icons-png.flaticon.com/512/2933/2933116.png" alt="tap">
    </button>
    <div id="floatingTexts"></div>
  </div>

  <div class="actions">
    <button id="dailyBtn" class="action-btn">🎁 جایزه روزانه</button>
    <button id="inviteBtn" class="action-btn">🔗 دعوت دوستان</button>
  </div>

  <div class="missions-panel">
    <h3>🎯 ماموریت‌ها</h3>
    <div id="missionsList"></div>
  </div>
</div>

<script src="{{ url_for('static', filename='app.js') }}"></script>
</body>
</html>
'''

STYLE_CSS = '''* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  font-family: 'Segoe UI', Tahoma, sans-serif;
  user-select: none;
  -webkit-user-select: none;
}

body {
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  color: #fff;
  min-height: 100vh;
  overflow-x: hidden;
}

.app {
  max-width: 480px;
  margin: 0 auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.top-bar {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
}

.level-box {
  background: linear-gradient(135deg, #ffd700, #ff8c00);
  border-radius: 12px;
  padding: 6px 14px;
  text-align: center;
  font-weight: bold;
  font-size: 20px;
  color: #1a1a2e;
  min-width: 60px;
}
.level-box small {
  display: block;
  font-size: 10px;
  font-weight: normal;
}

.xp-bar-container {
  flex: 1;
  height: 14px;
  background: rgba(255,255,255,0.15);
  border-radius: 8px;
  overflow: hidden;
}
.xp-bar {
  height: 100%;
  width: 0%;
  background: linear-gradient(90deg, #00c9ff, #92fe9d);
  transition: width 0.4s ease;
}

.gems-display {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 32px;
  font-weight: bold;
}
.gem-icon {
  width: 32px;
  height: 32px;
}

.tap-area {
  position: relative;
  margin: 10px 0;
}

.tap-button {
  width: 220px;
  height: 220px;
  border-radius: 50%;
  border: 6px solid #ffd700;
  background: radial-gradient(circle at 35% 30%, #6a5cff, #2d1e6f);
  box-shadow: 0 0 40px rgba(106,92,255,0.6), inset 0 0 30px rgba(255,255,255,0.2);
  cursor: pointer;
  transition: transform 0.08s ease;
}
.tap-button img {
  width: 100px;
  height: 100px;
}
.tap-button:active {
  transform: scale(0.92);
}

#floatingTexts {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.floating-text {
  position: absolute;
  font-size: 22px;
  font-weight: bold;
  color: #ffd700;
  animation: floatUp 0.9s ease-out forwards;
}
@keyframes floatUp {
  0% { opacity: 1; transform: translateY(0); }
  100% { opacity: 0; transform: translateY(-80px); }
}

.actions {
  display: flex;
  gap: 10px;
  width: 100%;
}
.action-btn {
  flex: 1;
  padding: 14px;
  border: none;
  border-radius: 14px;
  background: rgba(255,255,255,0.08);
  color: #fff;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s;
}
.action-btn:active {
  background: rgba(255,255,255,0.2);
}

.missions-panel {
  width: 100%;
  background: rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 14px;
}
.missions-panel h3 {
  margin-bottom: 10px;
}
.mission-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  border-radius: 10px;
  background: rgba(255,255,255,0.05);
  margin-bottom: 8px;
}
.mission-item.completed {
  opacity: 0.5;
}
.mission-reward {
  color: #ffd700;
  font-weight: bold;
}
.mission-btn {
  background: linear-gradient(135deg, #00c9ff, #92fe9d);
  border: none;
  color: #111;
  padding: 6px 12px;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
}
'''

APP_JS = '''const tg = window.Telegram.WebApp;
tg.expand();

const user = tg.initDataUnsafe?.user || { id: 123456, username: "test_user" };
const userId = user.id;
const username = user.username || "";

const gemsCountEl = document.getElementById("gemsCount");
const levelEl = document.getElementById("level");
const xpBarEl = document.getElementById("xpBar");
const tapButton = document.getElementById("tapButton");
const floatingTexts = document.getElementById("floatingTexts");
const dailyBtn = document.getElementById("dailyBtn");
const inviteBtn = document.getElementById("inviteBtn");
const missionsList = document.getElementById("missionsList");

let currentUser = null;

async function loadUser() {
  const res = await fetch(`/api/user/${userId}?username=${username}`);
  currentUser = await res.json();
  updateUI();
}

function updateUI() {
  gemsCountEl.textContent = currentUser.gems;
  levelEl.textContent = currentUser.level;
  const xpInLevel = currentUser.xp % 100;
  xpBarEl.style.width = xpInLevel + "%";
}

function spawnFloatingText(text, x, y) {
  const el = document.createElement("div");
  el.className = "floating-text";
  el.textContent = text;
  el.style.left = x + "px";
  el.style.top = y + "px";
  floatingTexts.appendChild(el);
  setTimeout(() => el.remove(), 900);
}

tapButton.addEventListener("click", async (e) => {
  tg.HapticFeedback?.impactOccurred("light");

  const rect = tapButton.getBoundingClientRect();
  const x = (e.clientX || rect.width / 2) - rect.left;
  const y = (e.clientY || rect.height / 2) - rect.top;
  spawnFloatingText("+1", x, y);

  const res = await fetch("/api/tap", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId })
  });
  currentUser = await res.json();
  updateUI();
});

dailyBtn.addEventListener("click", async () => {
  const res = await fetch("/api/daily", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId })
  });
  const data = await res.json();
  currentUser = data.user;
  updateUI();
  if (data.claimed) {
    tg.showAlert("🎁 ۱۰ جم گرفتی!");
  } else {
    tg.showAlert("⏳ امروز قبلاً گرفتی، فردا بیا.");
  }
});

inviteBtn.addEventListener("click", () => {
  tg.showAlert("لینک دعوت رو با دستور /invite توی چت بات بگیر.");
});

async function loadMissions() {
  const res = await fetch(`/api/missions/${userId}`);
  const missions = await res.json();
  missionsList.innerHTML = "";
  missions.forEach(m => {
    const div = document.createElement("div");
    div.className = "mission-item" + (m.completed ? " completed" : "");
    div.innerHTML = `
      <span>${m.title}</span>
      <span class="mission-reward">+${m.reward} 💎</span>
      ${m.completed ? "" : `<button class="mission-btn" data-id="${m.id}">دریافت</button>`}
    `;
    missionsList.appendChild(div);
  });

  document.querySelectorAll(".mission-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const missionId = btn.getAttribute("data-id");
      const res = await fetch("/api/missions/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, mission_id: missionId })
      });
      const data = await res.json();
      currentUser = data.user;
      updateUI();
      loadMissions();
    });
  });
}

loadUser();
loadMissions();
'''

BOT_PY = '''import os
from dotenv import load_dotenv
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import database as db

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com")  # لینک ngrok یا هاست رو اینجا میذاری

REFERRAL_REWARD_FOR_INVITER = 20
REFERRAL_REWARD_FOR_NEWCOMER = 5

db.init_db()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    existing = db.get_user(user.id)
    if not existing:
        referrer_id = None
        if args and args[0].isdigit():
            ref_id = int(args[0])
            if ref_id != user.id:
                referrer_id = ref_id

        db.create_user(user.id, user.username or user.first_name, referrer_id)

        if referrer_id:
            db.add_gems(referrer_id, REFERRAL_REWARD_FOR_INVITER)
            db.add_gems(user.id, REFERRAL_REWARD_FOR_NEWCOMER)
            db.increment_referral_count(referrer_id)
            try:
                await context.bot.send_message(
                    referrer_id,
                    f"🎉 یه نفر با لینک تو اومد! {REFERRAL_REWARD_FOR_INVITER} جم گرفتی."
                )
            except Exception:
                pass

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 بازی کن", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])

    await update.message.reply_text(
        f"سلام {user.first_name}! به بازی جم‌ها خوش اومدی 💎\\n"
        "برای بازی روی دکمه پایین بزن، یا از دستورات زیر استفاده کن:\\n"
        "/invite - گرفتن لینک دعوت\\n"
        "/balance - موجودی",
        reply_markup=keyboard
    )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("اول /start رو بزن.")
        return
    await update.message.reply_text(
        f"💎 جم‌های تو: {user['gems']}\\n⭐ لول: {user['level']}\\n👥 زیرمجموعه: {user['referral_count']}"
    )


async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_username = (await context.bot.get_me()).username
    user_id = update.effective_user.id
    link = f"https://t.me/{bot_username}?start={user_id}"
    await update.message.reply_text(
        f"🔗 لینک دعوت تو:\\n{link}\\n\\n"
        f"به ازای هر نفر که با این لینک بیاد، {REFERRAL_REWARD_FOR_INVITER} جم می‌گیری."
    )


app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("balance", balance))
app.add_handler(CommandHandler("invite", invite))

print("Bot is running...")
app.run_polling()
'''

ENV_EXAMPLE = '''BOT_TOKEN=توکن_ربات_خودتو_اینجا_بذار
WEBAPP_URL=https://your-ngrok-or-host-url.com
'''

# ---------- ساخت پوشه‌ها و فایل‌ها ----------

def write_file(path, content):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    if os.path.exists(path):
        print(f"⚠️  رد شد (از قبل هست، دست نخورد): {path}")
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ ساخته شد: {path}")


def main():
    write_file("database.py", DATABASE_PY)
    write_file("app.py", APP_PY)
    write_file("templates/index.html", INDEX_HTML)
    write_file("static/style.css", STYLE_CSS)
    write_file("static/app.js", APP_JS)
    write_file("bot_new.py", BOT_PY)  # اسمش رو new گذاشتیم که bot.py فعلیت پاک نشه
    write_file(".env.example", ENV_EXAMPLE)

    print("\\n🎉 تمام فایل‌ها ساخته شدن!")
    print("مراحل بعدی:")
    print("1) اگه فایل .env نداری، از .env.example یه کپی بساز و توکن واقعیت رو بذار")
    print("2) فایل bot_new.py رو چک کن و اگه اوکی بود جایگزین bot.py کن")
    print("3) pip install flask flask-cors pyngrok")
    print("4) اول 'python app.py' رو اجرا کن (سرور گرافیکی)")
    print("5) بعد با ngrok یه لینک HTTPS بگیر و بذارش تو .env جلوی WEBAPP_URL")
    print("6) در ترمینال دوم 'python bot.py' رو اجرا کن")


if __name__ == "__main__":
    main()
