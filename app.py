import os
from flask import Flask, request
from openai import OpenAI
import requests

app = Flask(__name__)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

@app.route("/")
def home():
    return "Bot is running 🚀"

@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    data = request.json

    message = data.get("message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]
    user_text = message.get("text", "")

    if not user_text:
        return "ok"

    try:
        completion = client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful dental assistant."},
                {"role": "user", "content": user_text}
            ]
        )

        reply = completion.choices[0].message.content

        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": reply
            }
        )

    except Exception as e:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": f"Error: {str(e)}"
            }
        )

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)