from flask import Flask, request, jsonify
import csv
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def home():
    return "Dental Bot Running 🚀", 200


def get_reply(msg):
    msg = (msg or "").lower()

    if any(x in msg for x in ["تبييض", "white", "bleach"]):
        return "تبييض يبدأ من 6000 جنيه 🦷"

    if any(x in msg for x in ["زراعة", "implant"]):
        return "زراعة تبدأ من 8000 جنيه 💰"

    if any(x in msg for x in ["فينير", "veneer"]):
        return "فينير يبدأ من 12000 جنيه ✨"

    if "حجز" in msg or "book" in msg:
        return "تمام 👌 ابعت:\nname: محمد, phone: 010..."

    return "ممكن تقولي نوع الخدمة؟ (تبييض - زراعة - فينير)"


def save_lead(name, phone):
    try:
        with open("leads.csv", "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([name, phone, datetime.now()])
    except Exception as e:
        print("Save error:", e)


def extract_data(msg):
    try:
        parts = msg.split(",")
        name = ""
        phone = ""

        for part in parts:
            if "name:" in part:
                name = part.split("name:")[1].strip()
            if "phone:" in part:
                phone = part.split("phone:")[1].strip()

        if name and phone:
            return name, phone
        return None, None
    except:
        return None, None


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        msg = data.get("message", "")

        name, phone = extract_data(msg)

        if name and phone:
            save_lead(name, phone)
            return jsonify({"reply": "تم الحجز ✅ هنتواصل معاك قريب"})

        return jsonify({"reply": get_reply(msg)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500