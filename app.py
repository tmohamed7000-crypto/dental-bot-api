import os
from flask import Flask, request
from openai import OpenAI
import requests

app = Flask(__name__)

# تأكد إن المفتاح موجود
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY is missing")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing")

# OpenRouter Client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

@app.route("/")
def home():
    return "Bot is running 🚀"


@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    data = request.json

    # تأكد إن فيه رسالة
    if "message" not in data:
        return "ok"

    message = data["message"]
    chat_id = message["chat"]["id"]
    user_text = message.get("text")

    # لو مفيش نص (مثلاً صورة)
    if not user_text:
        send_message(chat_id, "ابعتلي رسالة نصية بس 🙏")
        return "ok"

    try:
        completion = client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional dental assistant. Reply in Arabic in a friendly helpful tone."
                },
                {"role": "user", "content": user_text}
            ]
        )

        reply = completion.choices[0].message.content

    except Exception as e:
        reply = "حصل خطأ مؤقت 😢 حاول تاني بعد شوية"

    send_message(chat_id, reply)

    return "ok"


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    try:
        requests.post(url, json={
            "chat_id": chat_id,
            "text": text
        })
    except:
        pass


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)