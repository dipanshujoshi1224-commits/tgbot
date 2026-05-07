import json
import os
import re
import requests

from datetime import datetime, timedelta
from groq import Groq

from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# ==================== CONFIG ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

ADMIN_IDS = [7287792422]
DATA_FILE = "bot_data.json"

client = Groq(api_key=GROQ_API_KEY)

MAX_TELEGRAM_LIMIT = 4096

# ==================== RATE LIMIT ====================
user_cooldowns = {}

COOLDOWN_SECONDS = 15

# ==================== DATA ====================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)

    return {
        "warns": {},
        "memory": {}
    }

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
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            user.id
        )

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
async def ask_ai(question, user_id, chat_id):

    cid = str(chat_id)
    uid = str(user_id)

    bot_data.setdefault("memory", {})
    bot_data["memory"].setdefault(cid, {})
    bot_data["memory"][cid].setdefault(uid, [])

    history = bot_data["memory"][cid][uid]

    # OWNER MODEL
    if user_id in ADMIN_IDS:
        model = "llama-3.3-70b-versatile"

        system_prompt = (
            "You are an expert AI assistant. "
            "Reply shortly, clearly, intelligently. "
            "Maximum 8 short lines."
        )

    else:
        model = "llama-3.1-8b-instant"

        system_prompt = (
            "You are a smart Telegram assistant. "
            "Reply briefly and clearly. "
            "Maximum 6 short lines."
        )

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    # MEMORY
    for msg in history[-6:]:
        messages.append(msg)

    messages.append({
        "role": "user",
        "content": question
    })

    chat_completion = client.chat.completions.create(
        model=model,
        messages=messages
    )

    reply = chat_completion.choices[0].message.content

    # SAVE MEMORY
    history.append({
        "role": "user",
        "content": question
    })

    history.append({
        "role": "assistant",
        "content": reply
    })

    if len(history) > 20:
        history[:] = history[-20:]

    save_data(bot_data)

    return reply[:MAX_TELEGRAM_LIMIT]

# ==================== TALK ====================
async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    now = datetime.now()

    # COOLDOWN
    if user_id in user_cooldowns:

        remaining = (
            user_cooldowns[user_id] - now
        ).total_seconds()

        if remaining > 0:
            return await update.message.reply_text(
                f"⏳ Wait {int(remaining)} sec."
            )

    user_cooldowns[user_id] = (
        now + timedelta(seconds=COOLDOWN_SECONDS)
    )

    # REPLY IMAGE SUPPORT
    question = ""

    if context.args:
        question = " ".join(context.args)

    elif update.message.reply_to_message:
        replied = update.message.reply_to_message

        if replied.text:
            question = replied.text

        elif replied.caption:
            question = replied.caption

        else:
            question = "Explain this."

    else:
        return await update.message.reply_text(
            "Usage:\n/talk question\nor reply with /talk"
        )

    if len(question) > 500:
        return await update.message.reply_text("❌ Too long.")

    await context.bot.send_chat_action(
        update.effective_chat.id,
        "typing"
    )

    try:
        response = await ask_ai(
            question,
            user_id,
            update.effective_chat.id
        )

        await update.message.reply_text(response)

    except Exception as e:
        print(e)

        await update.message.reply_text(
            f"AI error:\n{e}"
        )

# ==================== RESET ====================
async def reset_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)

    if "memory" in bot_data:
        if chat_id in bot_data["memory"]:
            bot_data["memory"][chat_id][user_id] = []

    save_data(bot_data)

    await update.message.reply_text(
        "🧠 Memory cleared!"
    )

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 AI Group Manager Online!"
    )

# ==================== HELP ====================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("""
🔧 Admin:
/promote
/demote
/ban
/kick
/mute 1h
/unmute
/warn

📌 Messages:
/pin
/unpin
/purge
/del

🤖 AI:
/talk question
/waifu
/reset

🆔 Utility:
/id
""")

# ==================== ADMIN ====================
async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        return

    if not update.message.reply_to_message:
        return

    user = update.message.reply_to_message.from_user

    await context.bot.promote_chat_member(
        update.effective_chat.id,
        user.id,
        can_delete_messages=True,
        can_restrict_members=True
    )

    await update.message.reply_text("✅ Promoted")

async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        return

    if not update.message.reply_to_message:
        return

    user = update.message.reply_to_message.from_user

    await context.bot.promote_chat_member(
        update.effective_chat.id,
        user.id,
        can_delete_messages=False,
        can_restrict_members=False
    )

    await update.message.reply_text("✅ Demoted")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        return

    user = update.message.reply_to_message.from_user

    await context.bot.ban_chat_member(
        update.effective_chat.id,
        user.id
    )

    await update.message.reply_text("🚫 Banned")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        return

    user = update.message.reply_to_message.from_user

    await context.bot.ban_chat_member(
        update.effective_chat.id,
        user.id
    )

    await context.bot.unban_chat_member(
        update.effective_chat.id,
        user.id
    )

    await update.message.reply_text("👢 Kicked")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        return

    user = update.message.reply_to_message.from_user

    duration = (
        parse_time(context.args[0])
        if context.args
        else timedelta(hours=1)
    )

    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        user.id,
        ChatPermissions(can_send_messages=False),
        until_date=datetime.now() + duration
    )

    await update.message.reply_text("🔇 Muted")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        return

    user = update.message.reply_to_message.from_user

    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        user.id,
        ChatPermissions(can_send_messages=True)
    )

    await update.message.reply_text("🔊 Unmuted")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        return

    user = update.message.reply_to_message.from_user

    cid = str(update.effective_chat.id)
    uid = str(user.id)

    bot_data["warns"].setdefault(cid, {})

    bot_data["warns"][cid][uid] = (
        bot_data["warns"][cid].get(uid, 0) + 1
    )

    count = bot_data["warns"][cid][uid]

    if count >= 3:

        await context.bot.ban_chat_member(
            update.effective_chat.id,
            user.id
        )

        await update.message.reply_text(
            "🚫 Banned (3 warns)"
        )

        bot_data["warns"][cid][uid] = 0

    else:
        await update.message.reply_text(
            f"⚠ Warned ({count}/3)"
        )

    save_data(bot_data)

# ==================== PIN ====================
async def pin_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        return

    msg = update.message.reply_to_message

    await context.bot.pin_chat_message(
        update.effective_chat.id,
        msg.message_id
    )

    await update.message.reply_text("📌 Pinned")

async def unpin_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        return

    await context.bot.unpin_chat_message(
        update.effective_chat.id
    )

    await update.message.reply_text("📌 Unpinned")

# ==================== DELETE ====================
async def purge(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        return

    start = update.message.reply_to_message.message_id
    end = update.message.message_id

    for i in range(start, end + 1):

        try:
            await context.bot.delete_message(
                update.effective_chat.id,
                i
            )

        except:
            pass

async def delete_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        return

    await update.message.reply_to_message.delete()
    await update.message.delete()

# ==================== ID ====================
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        f"User ID: {update.effective_user.id}\n"
        f"Chat ID: {update.effective_chat.id}"
    )

# ==================== WAIFU ====================
async def waifu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message.reply_to_message:
        return await update.message.reply_text(
            "Reply to anime image with /waifu"
        )

    photo = update.message.reply_to_message.photo

    if not photo:
        return await update.message.reply_text(
            "❌ Reply to photo only."
        )

    await update.message.reply_text("👀 Detecting waifu...")

    try:
        import base64

        # Download telegram image
        file = await context.bot.get_file(photo[-1].file_id)

        downloaded = await file.download_as_bytearray()

        # Convert image to base64
        image_base64 = base64.b64encode(downloaded).decode("utf-8")

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "google/gemini-2.5-flash",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Identify this anime character. Reply only with character name and anime."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data
        )

        result = response.json()

        print(result)

        answer = result["choices"][0]["message"]["content"]

        await update.message.reply_text(answer)

    except Exception as e:
        print(e)
        await update.message.reply_text(
            f"❌ Failed:\n{e}"
        )

# ==================== MAIN ====================
def main():

    app = Application.builder().token(BOT_TOKEN).build()

    # BASIC
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", get_id))

    # AI
    app.add_handler(CommandHandler("talk", talk))
    app.add_handler(CommandHandler("reset", reset_memory))
    app.add_handler(CommandHandler("waifu", waifu))

    # ADMIN
    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(CommandHandler("demote", demote))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("warn", warn))

    # MESSAGE
    app.add_handler(CommandHandler("pin", pin_msg))
    app.add_handler(CommandHandler("unpin", unpin_msg))
    app.add_handler(CommandHandler("purge", purge))
    app.add_handler(CommandHandler("del", delete_msg))

    print("🚀 Bot Running...")

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

