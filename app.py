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

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")

    try:
        completion = client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful dental assistant."},
                {"role": "user", "content": user_message}
            ]
        )

        reply = completion.choices[0].message.content

        # إرسال تيليجرام
        send_to_telegram(f"💬 User: {user_message}\n🤖 Bot: {reply}")

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)