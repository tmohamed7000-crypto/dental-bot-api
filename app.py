from flask import Flask, request, jsonify, send_file
import csv
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def home():
    return send_file("index.html")   # 👈 دي المهمة

def get_reply(msg):
    msg = (msg or "").lower()

    if "تبييض" in msg:
        return "تبييض يبدأ من 6000 جنيه 🦷"
    if "زراعة" in msg:
        return "زراعة تبدأ من 8000 جنيه 💰"
    if "فينير" in msg:
        return "فينير يبدأ من 12000 جنيه ✨"

    return "ممكن تقولي نوع الخدمة؟"

def save_lead(name, phone):
    try:
        with open("leads.csv", "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([name, phone, datetime.now()])
    except Exception as e:
        print("Save error:", e)

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        msg = data.get("message", "")

        if "name:" in msg and "phone:" in msg:
            name = msg.split("name:")[1].split(",")[0].strip()
            phone = msg.split("phone:")[1].strip()

            save_lead(name, phone)
            return jsonify({"reply": "تم الحجز ✅"})

        return jsonify({"reply": get_reply(msg)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500