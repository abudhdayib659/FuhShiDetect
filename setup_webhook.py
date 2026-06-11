import sys
import requests

TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
# Replace 'yourusername' with your actual PythonAnywhere username
WEBHOOK_URL = "https://yourusername.pythonanywhere.com/"

if "YOUR" in TOKEN:
    print("ERROR: Edit setup_webhook.py first — paste your bot token and PythonAnywhere username.")
    sys.exit(1)

r = requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook", params={
    "url": WEBHOOK_URL
})
print(r.json())
