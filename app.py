from flask import Flask, request, jsonify
import os
import requests
from openai import OpenAI
import csv

app = Flask(__name__)

# OpenRouter (بنفس طريقة OpenAI)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

@app.route("/")
def home():
    return "Dental Bot Running 🚀", 200


# ✅ حفظ العملاء
def save_lead(name, phone):
    file_exists = os.path.isfile("leads.csv")

    with open("leads.csv", "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(["Name", "Phone"])

        writer.writerow([name, phone])


# ✅ إرسال تيليجرام
def send_telegram(name, phone):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    message = f"🔥 عميل جديد!\n👤 {name}\n📞 {phone}"

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        requests.post(url, data={
            "chat_id": chat_id,
            "text": message
        })
    except Exception as e:
        print("Telegram Error:", e)


# 🤖 الرد من AI
def get_reply(msg):
    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
أنت موظف استقبال في Optimum Care Dental Clinic.

رد بطريقة:
- بسيطة
- قصيرة
- مقنعة

الخدمات:
- تبييض: يبدأ من 6000 جنيه
- زراعة: تبدأ من 8000 جنيه
- فينير: يبدأ من 12000 جنيه

هدفك: تحويل أي عميل إلى حجز

لو العميل مهتم → اطلب منه:
name: , phone:
"""
                },
                {
                    "role": "user",
                    "content": msg
                }
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        print("AI Error:", e)
        return "حصل مشكلة بسيطة، حاول تاني"


# 💬 endpoint
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        msg = data.get("message", "")

        # ✅ لو المستخدم بعت بياناته
        if "name:" in msg and "phone:" in msg:
            try:
                parts = msg.split(",")
                name = parts[0].replace("name:", "").strip()
                phone = parts[1].replace("phone:", "").strip()

                save_lead(name, phone)
                send_telegram(name, phone)  # 🔥 إشعار

                return jsonify({
                    "reply": "تم الحجز ✅ هنكلمك خلال دقائق"
                })
            except:
                return jsonify({
                    "reply": "في مشكلة في البيانات، ابعتها تاني 🙏"
                })

        reply = get_reply(msg)

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500