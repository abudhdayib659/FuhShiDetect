import os
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CommandHandler
from telegram.constants import MessageLimit

# ─── CONFIG ─────────────────────────────────────────────────────────
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
SIGHTENGINE_API_USER = "YOUR_SIGHTENGINE_API_USER"
SIGHTENGINE_API_SECRET = "YOUR_SIGHTENGINE_API_SECRET"
# ─────────────────────────────────────────────────────────────────────

async def start(update: Update, context):
    await update.message.reply_text(
        "Bot is running. Add me to a group as admin and I'll auto-delete NSFW content and ban the sender."
    )

async def handle_media(update: Update, context):
    if not update.effective_chat or update.effective_chat.type == "private":
        return

    user = update.effective_user
    if not user:
        return

    # Skip admins
    chat = update.effective_chat
    member = await chat.get_member(user.id)
    if member.status in ("administrator", "creator"):
        return

    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document and update.message.document.mime_type and update.message.document.mime_type.startswith("image/"):
        file_id = update.message.document.file_id
    elif update.message.sticker:
        file_id = update.message.sticker.file_id
    elif update.message.video:
        file_id = update.message.video.file_id
    elif update.message.animation:
        file_id = update.message.animation.file_id

    if not file_id:
        return

    file = await context.bot.get_file(file_id)
    file_url = file.file_path

    try:
        resp = requests.get("https://api.sightengine.com/1.0/check.json", params={
            "api_user": SIGHTENGINE_API_USER,
            "api_secret": SIGHTENGINE_API_SECRET,
            "media": file_url,
            "models": "nudity",
        }, timeout=15)
        data = resp.json()
    except Exception as e:
        print(f"Sightengine error: {e}")
        return

    nudity = data.get("nudity", {})
    # If nudity is detected as likely or very likely, delete and ban
    if nudity.get("sexual_activity", 0) > 0.5 or nudity.get("sexual_display", 0) > 0.5 or nudity.get("erotica", 0) > 0.7:
        try:
            await update.message.delete()
            await context.bot.ban_chat_member(chat.id, user.id)
        except Exception as e:
            print(f"Action failed: {e}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.Sticker.ALL | filters.ANIMATION | filters.Document.IMAGE,
        handle_media
    ))

    print("Bot started polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
