import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import database as db

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

DAILY_REWARD = 10
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

    await update.message.reply_text(
        f"سلام {user.first_name}! به بازی جم‌ها خوش اومدی 💎\n"
        "دستورات:\n"
        "/daily - جایزه روزانه\n"
        "/balance - موجودی و زیرمجموعه‌ها\n"
        "/invite - گرفتن لینک دعوت"
    )

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.get_user(user_id):
        db.create_user(user_id, update.effective_user.username or "")

    if db.can_claim_daily(user_id):
        db.add_gems(user_id, DAILY_REWARD)
        db.set_last_claim(user_id)
        await update.message.reply_text(f"✅ {DAILY_REWARD} جم گرفتی! فردا دوباره بیا.")
    else:
        await update.message.reply_text("⏳ امروز جایزه‌ت رو گرفتی، فردا بیا.")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("اول /start رو بزن.")
        return
    await update.message.reply_text(
        f"💎 جم‌های تو: {user[2]}\n👥 تعداد زیرمجموعه: {user[5]}"
    )

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_username = (await context.bot.get_me()).username
    user_id = update.effective_user.id
    link = f"https://t.me/{bot_username}?start={user_id}"
    await update.message.reply_text(
        f"🔗 لینک دعوت تو:\n{link}\n\n"
        f"به ازای هر نفر که با این لینک بیاد، {REFERRAL_REWARD_FOR_INVITER} جم می‌گیری."
    )

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("daily", daily))
app.add_handler(CommandHandler("balance", balance))
app.add_handler(CommandHandler("invite", invite))

print("Bot is running...")
app.run_polling()