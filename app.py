import os
from flask import Flask, request, jsonify
from openai import OpenAI
import requests

app = Flask(__name__)

# =========================
# ENV
# =========================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if TELEGRAM_CHAT_ID:
    TELEGRAM_CHAT_ID = int(TELEGRAM_CHAT_ID)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

# =========================
# SYSTEM PROMPT
# =========================
SYSTEM_PROMPT = """
أنت موظف استقبال محترف في Optimum Care Dental Clinic.

هدفك:
تحويل أي عميل لحجز.

أسلوبك:
- عربي بسيط
- مختصر
- مقنع

الخدمات:
- تبييض الأسنان: 6000 جنيه
- فينير: من 12000 جنيه
- زراعة: من 8000 جنيه

قواعد:
- رد قصير + سعر
- بعدها اطلب:
name:
phone:
"""

# =========================
# HOME
# =========================
@app.route("/")
def home():
    return "Bot is running 🚀"

# =========================
# CHAT API (لـ HTML)
# =========================
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message")

    if not user_message:
        return jsonify({"error": "No message"}), 400

    try:
        reply = ask_ai(user_message)

        # لوج للعيادة
        send_to_telegram(f"💬 User: {user_message}\n🤖 Bot: {reply}")

        return jsonify({"reply": reply})

    except Exception as e:
        print("CHAT ERROR:", e)
        return jsonify({"error": str(e)}), 500

# =========================
# TELEGRAM WEBHOOK
# =========================
@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    data = request.json

    try:
        if "message" not in data:
            return "ok"

        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()

        if not text:
            return "ok"

        lower_text = text.lower()

        # =====================
        # ✅ بيانات حجز
        # =====================
        if "name:" in lower_text and "phone:" in lower_text:

            send_message(chat_id, "تم الحجز ✅ هنكلمك قريب")

            send_to_telegram(
                f"📥 عميل جديد:\n{text}\n\nChat ID: {chat_id}"
            )

            return "ok"

        # =====================
        # 🤖 AI رد
        # =====================
        reply = ask_ai(text)

        send_message(chat_id, reply)

    except Exception as e:
        print("TELEGRAM ERROR:", e)
        send_message(chat_id, "حصل خطأ 😢 حاول تاني")

    return "ok"

# =========================
# AI FUNCTION
# =========================
def ask_ai(user_text):
    completion = client.chat.completions.create(
        model="openai/gpt-4o-mini",  # 🔥 أفضل وأرخص على OpenRouter
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ]
    )

    return completion.choices[0].message.content

# =========================
# SEND TELEGRAM MESSAGE
# =========================
def send_message(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text
            },
            timeout=10
        )
    except Exception as e:
        print("SEND MSG ERROR:", e)

# =========================
# ADMIN LOG
# =========================
def send_to_telegram(text):
    if not TELEGRAM_CHAT_ID:
        return

    send_message(TELEGRAM_CHAT_ID, text)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)