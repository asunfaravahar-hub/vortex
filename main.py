"""
فایل ترکیبی: سرور Flask (برای Mini App) + بات تلگرام (polling)
هر دو با هم توی یک پروسه اجرا میشن، مناسب برای هاست رایگان Render.

برای اجرا:
    python main.py
"""

import os
import threading
import asyncio

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import database as db

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com")

REFERRAL_REWARD_FOR_INVITER = 20
REFERRAL_REWARD_FOR_NEWCOMER = 5

db.init_db()

# ---------------- Flask App ----------------

flask_app = Flask(__name__)
CORS(flask_app)


def ensure_user(user_id, username=""):
    user = db.get_user(user_id)
    if not user:
        db.create_user(user_id, username)
        user = db.get_user(user_id)
    return user


@flask_app.route("/")
def index():
    return render_template("index.html")


@flask_app.route("/api/user/<int:user_id>")
def api_user(user_id):
    username = request.args.get("username", "")
    user = ensure_user(user_id, username)
    return jsonify(user)


@flask_app.route("/api/tap", methods=["POST"])
def api_tap():
    data = request.json
    user_id = data.get("user_id")
    ensure_user(user_id)
    db.register_tap(user_id)
    user = db.get_user(user_id)
    return jsonify(user)


@flask_app.route("/api/daily", methods=["POST"])
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


@flask_app.route("/api/missions/<int:user_id>")
def api_missions(user_id):
    ensure_user(user_id)
    missions = db.get_missions_status(user_id)
    return jsonify(missions)


@flask_app.route("/api/missions/complete", methods=["POST"])
def api_complete_mission():
    data = request.json
    user_id = data.get("user_id")
    mission_id = data.get("mission_id")
    ensure_user(user_id)
    success, reward = db.complete_mission(user_id, mission_id)
    user = db.get_user(user_id)
    return jsonify({"success": success, "reward": reward, "user": user})


# ---------------- Telegram Bot ----------------

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
        f"سلام {user.first_name}! به بازی جم‌ها خوش اومدی 💎\n"
        "برای بازی روی دکمه پایین بزن، یا از دستورات زیر استفاده کن:\n"
        "/invite - گرفتن لینک دعوت\n"
        "/balance - موجودی",
        reply_markup=keyboard
    )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("اول /start رو بزن.")
        return
    await update.message.reply_text(
        f"💎 جم‌های تو: {user['gems']}\n⭐ لول: {user['level']}\n👥 زیرمجموعه: {user['referral_count']}"
    )


async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_username = (await context.bot.get_me()).username
    user_id = update.effective_user.id
    link = f"https://t.me/{bot_username}?start={user_id}"
    await update.message.reply_text(
        f"🔗 لینک دعوت تو:\n{link}\n\n"
        f"به ازای هر نفر که با این لینک بیاد، {REFERRAL_REWARD_FOR_INVITER} جم می‌گیری."
    )


def run_bot():
    """بات رو توی یه event loop مخصوص همین Thread اجرا می‌کنه."""
    asyncio.set_event_loop(asyncio.new_event_loop())

    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("balance", balance))
    bot_app.add_handler(CommandHandler("invite", invite))

    print("Bot polling started...")
        bot_app.run_polling(close_loop=False, stop_signals=None)


# ---------------- اجرای همزمان ----------------

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    port = int(os.environ.get("PORT", 5000))
    print(f"Flask server starting on port {port}...")
    flask_app.run(host="0.0.0.0", port=port)
