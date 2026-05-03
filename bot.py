import json
import os
import re
from datetime import datetime, timedelta
from groq import Groq
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ==================== CONFIG ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

ADMIN_IDS = [7287792422]
DATA_FILE = "bot_data.json"

client = Groq(api_key=GROQ_API_KEY)

# ==================== DATA ====================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"warns": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

bot_data = load_data()

# ==================== HELPERS ====================
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in ADMIN_IDS:
        return True
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, user.id)
        return member.status in ["creator", "administrator"]
    except:
        return False

def parse_time(time_str):
    match = re.match(r"(\d+)([dhm])", time_str)
    if not match:
        return timedelta(hours=1)
    value, unit = int(match.group(1)), match.group(2)
    if unit == "d":
        return timedelta(days=value)
    if unit == "h":
        return timedelta(hours=value)
    if unit == "m":
        return timedelta(minutes=value)
    return timedelta(hours=1)

# ==================== AI ====================
async def ask_ai(question):
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a smart, friendly and helpful Telegram group assistant."},
            {"role": "user", "content": question},
        ],
        model="llama-3.1-8b-instant",
    )
    return chat_completion.choices[0].message.content

async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: /talk your question")

    question = " ".join(context.args)

    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    try:
        response = await ask_ai(question)
        await update.message.reply_text(response)
    except:
        await update.message.reply_text("AI error occurred.")

async def auto_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    is_private = update.message.chat.type == "private"
    is_mention = f"@{context.bot.username}" in update.message.text
    is_reply = update.message.reply_to_message and \
               update.message.reply_to_message.from_user.id == context.bot.id

    if is_private or is_mention or is_reply:
        text = update.message.text.replace(f"@{context.bot.username}", "")
        await context.bot.send_chat_action(update.effective_chat.id, "typing")
        try:
            response = await ask_ai(text)
            await update.message.reply_text(response)
        except:
            pass

# ==================== COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 AI Group Manager is Online! Use /help")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🔧 Admin:
/promote (reply)
/demote (reply)
/ban (reply)
/kick (reply)
/mute 1h (reply)
/unmute (reply)
/warn (reply)

📌 Messages:
/pin (reply)
/unpin
/purge (reply)
/del (reply)

🤖 AI:
/talk question
Mention or reply to me

🆔 Utility:
/id
""")

async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return
    user = update.message.reply_to_message.from_user
    await context.bot.promote_chat_member(update.effective_chat.id, user.id,
        can_delete_messages=True, can_restrict_members=True)
    await update.message.reply_text("✅ Promoted")

async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return
    user = update.message.reply_to_message.from_user
    await context.bot.promote_chat_member(update.effective_chat.id, user.id,
        can_delete_messages=False, can_restrict_members=False)
    await update.message.reply_text("✅ Demoted")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    user = update.message.reply_to_message.from_user
    await context.bot.ban_chat_member(update.effective_chat.id, user.id)
    await update.message.reply_text("🚫 Banned")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    user = update.message.reply_to_message.from_user
    await context.bot.ban_chat_member(update.effective_chat.id, user.id)
    await context.bot.unban_chat_member(update.effective_chat.id, user.id)
    await update.message.reply_text("👢 Kicked")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    user = update.message.reply_to_message.from_user
    duration = parse_time(context.args[0]) if context.args else timedelta(hours=1)
    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        user.id,
        ChatPermissions(can_send_messages=False),
        until_date=datetime.now() + duration
    )
    await update.message.reply_text("🔇 Muted")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    user = update.message.reply_to_message.from_user
    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        user.id,
        ChatPermissions(can_send_messages=True)
    )
    await update.message.reply_text("🔊 Unmuted")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    user = update.message.reply_to_message.from_user
    cid = str(update.effective_chat.id)
    uid = str(user.id)

    bot_data["warns"].setdefault(cid, {})
    bot_data["warns"][cid][uid] = bot_data["warns"][cid].get(uid, 0) + 1

    count = bot_data["warns"][cid][uid]

    if count >= 3:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text("🚫 Banned (3 warns)")
        bot_data["warns"][cid][uid] = 0
    else:
        await update.message.reply_text(f"⚠ Warned ({count}/3)")

    save_data(bot_data)

async def pin_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    msg = update.message.reply_to_message
    await context.bot.pin_chat_message(update.effective_chat.id, msg.message_id)
    await update.message.reply_text("📌 Pinned")

async def unpin_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    await context.bot.unpin_chat_message(update.effective_chat.id)
    await update.message.reply_text("📌 Unpinned")

async def purge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    start = update.message.reply_to_message.message_id
    end = update.message.message_id
    for i in range(start, end + 1):
        try:
            await context.bot.delete_message(update.effective_chat.id, i)
        except:
            pass

async def delete_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    await update.message.reply_to_message.delete()
    await update.message.delete()

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"User ID: {update.effective_user.id}\nChat ID: {update.effective_chat.id}"
    )

# ==================== MESSAGE HANDLER ====================
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()

    # Anti-link protection
    if not await is_admin(update, context):
        if "t.me/" in text or "telegram.me/" in text:
            await update.message.delete()
            return

    await auto_ai(update, context)

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("talk", talk))

    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(CommandHandler("demote", demote))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("pin", pin_msg))
    app.add_handler(CommandHandler("unpin", unpin_msg))
    app.add_handler(CommandHandler("purge", purge))
    app.add_handler(CommandHandler("del", delete_msg))
    app.add_handler(CommandHandler("id", get_id))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    print("🚀 Bot Running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()