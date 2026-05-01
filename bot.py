from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
from datetime import datetime, timedelta
import json
import os
import re

# ==================== CONFIGURATION ====================
BOT_TOKEN = "7979137564:AAGYW0_jS9UQOkKswLgH-JKFL2uMYfyWrKo"  # Get from @BotFather
ADMIN_IDS = [7287792422]  # Your Telegram user ID
DATA_FILE = "bot_data.json"

# ==================== DATA MANAGEMENT ====================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"warns": {}, "filters": {}, "notes": {}, "welcome": {}, "rules": {}}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

bot_data = load_data()

# ==================== HELPER FUNCTIONS ====================
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is admin"""
    user = update.effective_user
    chat = update.effective_chat
    
    if user.id in ADMIN_IDS:
        return True
    
    member = await context.bot.get_chat_member(chat.id, user.id)
    return member.status in ['creator', 'administrator']

def time_parser(time_string: str):
    """Parse time strings like 1d, 2h, 30m"""
    match = re.match(r'(\d+)([dhm])', time_string.lower())
    if not match:
        return None
    
    value, unit = int(match.group(1)), match.group(2)
    if unit == 'd':
        return timedelta(days=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'm':
        return timedelta(minutes=value)

# ==================== START & HELP ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **Advanced Group Manager Bot**\n\n"
        "Use /help to see all commands!",
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🔧 **ADMIN COMMANDS**

**Moderation:**
/ban [reply/username] - Ban a user
/unban [username/ID] - Unban a user
/kick [reply/username] - Kick a user
/mute [reply] [time] - Mute user (1d, 2h, 30m)
/unmute [reply] - Unmute user
/warn [reply] [reason] - Warn user (3 = ban)
/resetwarns [reply] - Reset warnings
/purge [reply] - Delete messages up to replied message
/del [reply] - Delete replied message

**Restrictions:**
/lock [type] - Lock: messages, media, stickers, polls, links
/unlock [type] - Unlock permissions
/setflood [number] - Set flood limit
/setantiflood [on/off] - Toggle anti-flood

**Filters & Auto-reply:**
/filter [word] [response] - Auto-reply to word
/stop [word] - Remove filter
/filters - List all filters

**Notes:**
/save [name] [content] - Save a note
/get [name] - Get saved note
/notes - List all notes
/clear [name] - Delete note

**Welcome/Goodbye:**
/setwelcome [message] - Set welcome message
/welcome on/off - Toggle welcome
/setgoodbye [message] - Set goodbye message

**Info & Rules:**
/setrules [rules] - Set group rules
/rules - Show rules
/info [reply] - User information
/adminlist - List admins

**Pins:**
/pin [reply] - Pin message
/unpin - Unpin message
/unpinall - Unpin all messages

**Misc:**
/id - Get user/chat ID
/report [reply] - Report message to admins
/stats - Group statistics
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

# ==================== MODERATION ====================
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ You need admin rights!")
        return
    
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"🚫 {user.first_name} has been banned!")
    elif context.args:
        await update.message.reply_text("Reply to a message or use username")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    
    if context.args:
        try:
            user_id = int(context.args[0]) if context.args[0].isdigit() else context.args[0]
            await context.bot.unban_chat_member(update.effective_chat.id, user_id)
            await update.message.reply_text(f"✅ User unbanned!")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await context.bot.unban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"👢 {user.first_name} has been kicked!")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        duration = time_parser(context.args[0]) if context.args else timedelta(hours=1)
        
        permissions = ChatPermissions(can_send_messages=False)
        await context.bot.restrict_chat_member(
            update.effective_chat.id, 
            user.id, 
            permissions,
            until_date=datetime.now() + duration
        )
        await update.message.reply_text(f"🔇 {user.first_name} muted for {context.args[0] if context.args else '1h'}!")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        permissions = ChatPermissions(
    can_send_messages=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
    can_send_polls=True
)
        await context.bot.restrict_chat_member(update.effective_chat.id, user.id, permissions)
        await update.message.reply_text(f"🔊 {user.first_name} can speak now!")

# ==================== WARNING SYSTEM ====================
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        chat_id = str(update.effective_chat.id)
        user_id = str(user.id)
        
        if chat_id not in bot_data["warns"]:
            bot_data["warns"][chat_id] = {}
        
        if user_id not in bot_data["warns"][chat_id]:
            bot_data["warns"][chat_id][user_id] = 0
        
        bot_data["warns"][chat_id][user_id] += 1
        warn_count = bot_data["warns"][chat_id][user_id]
        
        reason = ' '.join(context.args) if context.args else "No reason"
        
        if warn_count >= 3:
            await context.bot.ban_chat_member(update.effective_chat.id, user.id)
            await update.message.reply_text(f"🚫 {user.first_name} banned after 3 warnings!")
            bot_data["warns"][chat_id][user_id] = 0
        else:
            await update.message.reply_text(
                f"⚠️ {user.first_name} warned ({warn_count}/3)\n"
                f"Reason: {reason}"
            )
        
        save_data(bot_data)

async def resetwarns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        chat_id = str(update.effective_chat.id)
        user_id = str(user.id)
        
        if chat_id in bot_data["warns"] and user_id in bot_data["warns"][chat_id]:
            bot_data["warns"][chat_id][user_id] = 0
            save_data(bot_data)
            await update.message.reply_text(f"✅ Warnings reset for {user.first_name}")

# ==================== PURGE & DELETE ====================
async def purge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    
    if update.message.reply_to_message:
        start_id = update.message.reply_to_message.message_id
        end_id = update.message.message_id
        
        for msg_id in range(start_id, end_id + 1):
            try:
                await context.bot.delete_message(update.effective_chat.id, msg_id)
            except:
                pass
        
        await update.message.reply_text(f"🗑️ Purged {end_id - start_id + 1} messages!")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    
    if update.message.reply_to_message:
        await update.message.reply_to_message.delete()
        await update.message.delete()

# ==================== FILTERS ====================
async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /filter [word] [response]")
        return
    
    keyword = context.args[0].lower()
    response = ' '.join(context.args[1:])
    chat_id = str(update.effective_chat.id)
    
    if chat_id not in bot_data["filters"]:
        bot_data["filters"][chat_id] = {}
    
    bot_data["filters"][chat_id][keyword] = response
    save_data(bot_data)
    await update.message.reply_text(f"✅ Filter added for '{keyword}'")

async def stop_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    
    if not context.args:
        return
    
    keyword = context.args[0].lower()
    chat_id = str(update.effective_chat.id)
    
    if chat_id in bot_data["filters"] and keyword in bot_data["filters"][chat_id]:
        del bot_data["filters"][chat_id][keyword]
        save_data(bot_data)
        await update.message.reply_text(f"✅ Filter removed for '{keyword}'")

async def list_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    if chat_id in bot_data["filters"] and bot_data["filters"][chat_id]:
        filters = "\n".join([f"• {k}" for k in bot_data["filters"][chat_id].keys()])
        await update.message.reply_text(f"**Active Filters:**\n{filters}", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("No filters set!")

async def check_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        chat_id = str(update.effective_chat.id)
        
        if chat_id in bot_data["filters"]:
            text = update.message.text.lower()
            for keyword, response in bot_data["filters"][chat_id].items():
                if keyword in text:
                    await update.message.reply_text(response)
                    break

# ==================== NOTES ====================
async def save_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /save [name] [content]")
        return
    
    note_name = context.args[0].lower()
    note_content = ' '.join(context.args[1:])
    chat_id = str(update.effective_chat.id)
    
    if chat_id not in bot_data["notes"]:
        bot_data["notes"][chat_id] = {}
    
    bot_data["notes"][chat_id][note_name] = note_content
    save_data(bot_data)
    await update.message.reply_text(f"✅ Note '{note_name}' saved!")

async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return
    
    note_name = context.args[0].lower()
    chat_id = str(update.effective_chat.id)
    
    if chat_id in bot_data["notes"] and note_name in bot_data["notes"][chat_id]:
        await update.message.reply_text(bot_data["notes"][chat_id][note_name])

async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    if chat_id in bot_data["notes"] and bot_data["notes"][chat_id]:
        notes = "\n".join([f"• #{k}" for k in bot_data["notes"][chat_id].keys()])
        await update.message.reply_text(f"**Saved Notes:**\n{notes}", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("No notes saved!")

# ==================== RULES ====================
async def set_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /setrules [your rules]")
        return
    
    rules = ' '.join(context.args)
    chat_id = str(update.effective_chat.id)
    bot_data["rules"][chat_id] = rules
    save_data(bot_data)
    await update.message.reply_text("✅ Rules updated!")

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    if chat_id in bot_data["rules"]:
        await update.message.reply_text(f"📜 **Group Rules:**\n\n{bot_data['rules'][chat_id]}", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("No rules set!")

# ==================== INFO ====================
async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
    else:
        user = update.effective_user
    
    info = f"""
👤 **User Information**

Name: {user.first_name} {user.last_name or ''}
ID: `{user.id}`
Username: @{user.username or 'None'}
Is Bot: {user.is_bot}
"""
    await update.message.reply_text(info, parse_mode=ParseMode.MARKDOWN)

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    
    text = f"👤 Your ID: `{user.id}`\n"
    if chat.type != "private":
        text += f"💬 Chat ID: `{chat.id}`"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = await context.bot.get_chat_administrators(update.effective_chat.id)
    admin_list = "\n".join([f"• {admin.user.first_name}" for admin in admins])
    await update.message.reply_text(f"👥 **Admins:**\n{admin_list}", parse_mode=ParseMode.MARKDOWN)

# ==================== PINS ====================
async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    
    if update.message.reply_to_message:
        await context.bot.pin_chat_message(
            update.effective_chat.id, 
            update.message.reply_to_message.message_id
        )
        await update.message.reply_text("📌 Message pinned!")

async def unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    
    await context.bot.unpin_chat_message(update.effective_chat.id)
    await update.message.reply_text("📌 Message unpinned!")

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("resetwarns", resetwarns))
    app.add_handler(CommandHandler("purge", purge))
    app.add_handler(CommandHandler("del", delete))
    app.add_handler(CommandHandler("filter", add_filter))
    app.add_handler(CommandHandler("stop", stop_filter))
    app.add_handler(CommandHandler("filters", list_filters))
    app.add_handler(CommandHandler("save", save_note))
    app.add_handler(CommandHandler("get", get_note))
    app.add_handler(CommandHandler("notes", list_notes))
    app.add_handler(CommandHandler("setrules", set_rules))
    app.add_handler(CommandHandler("rules", show_rules))
    app.add_handler(CommandHandler("info", user_info))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(CommandHandler("adminlist", admin_list))
    app.add_handler(CommandHandler("pin", pin))
    app.add_handler(CommandHandler("unpin", unpin))
    
    # Message handler for filters
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_filters))
    
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()