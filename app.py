import os
from flask import Flask, request, jsonify
from openai import OpenAI
import requests

app = Flask(__name__)

# OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


@app.route("/")
def home():
    return "Bot is running 🚀"


# =========================
# API للتجربة (ReqBin)
# =========================
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        completion = client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful dental assistant."},
                {"role": "user", "content": user_message}
            ]
        )

        reply = completion.choices[0].message.content

        # إرسال نسخة على تيليجرام
        send_to_telegram(f"💬 User: {user_message}\n🤖 Bot: {reply}")

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# Telegram Webhook
# =========================
@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    data = request.json

    try:
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text")

            if text:
                completion = client.chat.completions.create(
                    model="openai/gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful dental assistant."},
                        {"role": "user", "content": text}
                    ]
                )

                reply = completion.choices[0].message.content

                # الرد على المستخدم
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": reply
                    }
                )

    except Exception as e:
        print("Error:", e)

    return "ok"


# =========================
# إرسال تيليجرام (لوج)
# =========================
def send_to_telegram(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text
            }
        )
    except Exception as e:
        print("Telegram Error:", e)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)