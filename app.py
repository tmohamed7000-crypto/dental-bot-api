import os
from flask import Flask, request, jsonify, send_from_directory
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
    return send_from_directory(".", "index.html")

# =========================
# CHAT API
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
# 🔥 BOOKING API (الأهم)
# =========================
@app.route("/book", methods=["POST"])
def book():
    data = request.json

    name = data.get("name")
    phone = data.get("phone")
    service = data.get("service", "غير محدد")

    if not name or not phone:
        return jsonify({"error": "Missing data"}), 400

    # إرسال للعيادة
    send_to_telegram(
        f"📥 حجز جديد:\n👤 الاسم: {name}\n📞 الرقم: {phone}\n🦷 الخدمة: {service}"
    )

    return jsonify({"message": "تم الحجز بنجاح"})

# =========================
# AI FUNCTION
# =========================
def ask_ai(user_text):
    completion = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ]
    )

    return completion.choices[0].message.content

# =========================
# TELEGRAM SEND
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
        print("SEND ERROR:", e)

def send_to_telegram(text):
    if not TELEGRAM_CHAT_ID:
        return

    send_message(TELEGRAM_CHAT_ID, text)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)