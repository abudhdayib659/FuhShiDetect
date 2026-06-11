import os
import sys
import json
import requests
from flask import Flask, request

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
SIGHTENGINE_API_USER = os.environ.get("SIGHTENGINE_API_USER", "")
SIGHTENGINE_API_SECRET = os.environ.get("SIGHTENGINE_API_SECRET", "")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

app = Flask(__name__)

def tg(method, params=None):
    url = f"{TELEGRAM_API}/{method}"
    r = requests.post(url, json=params or {}, timeout=10)
    return r.json()

def check_nsfw(file_url):
    try:
        print(f"Checking: {file_url[:80]}...", flush=True)
        r = requests.get("https://api.sightengine.com/1.0/check.json", params={
            "api_user": SIGHTENGINE_API_USER,
            "api_secret": SIGHTENGINE_API_SECRET,
            "url": file_url,
            "models": "nudity",
        }, timeout=15)
        data = r.json()
        print(f"Sightengine response: {json.dumps(data)}", flush=True)
        n = data.get("nudity", {})
        result = (
            n.get("sexual_activity", 0) > 0.3
            or n.get("sexual_display", 0) > 0.3
            or n.get("erotica", 0) > 0.5
        )
        print(f"NSFW detected: {result}", flush=True)
        return result
    except Exception as e:
        print(f"Sightengine error: {e}", flush=True)
        return False

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "Bot is running"

    update = request.get_json()
    if not update:
        return "OK"

    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return "OK"

    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    user = msg.get("from", {})
    user_id = user.get("id")

    if chat.get("type") == "private":
        return "OK"

    member_info = tg("getChatMember", {"chat_id": chat_id, "user_id": user_id})
    status = member_info.get("result", {}).get("status")
    if status in ("administrator", "creator"):
        return "OK"

    file_id = None
    if "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]
    elif "document" in msg and msg["document"].get("mime_type", "").startswith("image/"):
        file_id = msg["document"]["file_id"]
    elif "sticker" in msg:
        file_id = msg["sticker"]["file_id"]
    elif "video" in msg:
        file_id = msg["video"]["file_id"]
    elif "animation" in msg:
        file_id = msg["animation"]["file_id"]

    if not file_id:
        print(f"No media found in message", flush=True)
        return "OK"

    print(f"Found file_id: {file_id[:30]}...", flush=True)
    file_info = tg("getFile", {"file_id": file_id})
    file_path = file_info.get("result", {}).get("file_path")
    if not file_path:
        return "OK"
    file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"

    if check_nsfw(file_url):
        print(f"Deleting message {msg['message_id']} and banning user {user_id}", flush=True)
        tg("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        tg("banChatMember", {"chat_id": chat_id, "user_id": user_id})

    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
