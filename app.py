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
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

# =========================
# 🔥 SYSTEM PROMPT (بيع + حجز)
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
- تبييض الأسنان: 6000 جنيه (تفتيح حتى 7 درجات)
- فينير: من 12000 جنيه
- زراعة: من 8000 جنيه

قواعد مهمة:
- أي عميل يسأل عن خدمة → رد مختصر + السعر
- بعدها مباشرة اطلب بياناته
- لازم تطلب:
name:
phone:

مثال:
تبييض الأسنان عندنا يبدأ من 6000 جنيه ✨

احجزلك معاد؟ ابعتلي:
name:
phone:
"""

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
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ]
        )

        reply = completion.choices[0].message.content

        # إرسال لوج للعيادة
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
        if "message" not in data:
            return "ok"

        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        if not text:
            return "ok"

        lower_text = text.lower()

        # 🔥 لو العميل بعت بياناته
        if "name:" in lower_text and "phone:" in lower_text:

            # رد للعميل
            send_message(chat_id, "تم الحجز ✅ هنكلمك قريب")

            # إرسال للعيادة
            send_message(
                ADMIN_CHAT_ID,
                f"📥 عميل جديد:\n{text}\n\nChat ID: {chat_id}"
            )

            return "ok"

        # 🤖 رد AI
        completion = client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ]
        )

        reply = completion.choices[0].message.content

        send_message(chat_id, reply)

    except Exception as e:
        print("Error:", e)
        send_message(chat_id, "حصل خطأ 😢 حاول تاني")

    return "ok"


# =========================
# إرسال رسالة تيليجرام
# =========================
def send_message(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text
            }
        )
    except Exception as e:
        print("Telegram Error:", e)


# =========================
# لوج للعيادة
# =========================
def send_to_telegram(text):
    if not ADMIN_CHAT_ID:
        return

    send_message(ADMIN_CHAT_ID, text)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)