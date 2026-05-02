from flask import Flask, request, jsonify
import csv
from datetime import datetime
import os

app = Flask(__name__)

# ----------------------------
# Home Route
# ----------------------------
@app.route("/")
def home():
    return "API is running", 200

# ----------------------------
# Health Check (مهم)
# ----------------------------
@app.route("/health")
def health():
    return {"status": "ok"}, 200

# ----------------------------
# Knowledge Base
# ----------------------------
def get_reply(msg):
    msg = msg.lower()

    if any(word in msg for word in ["تبييض", "white", "bleach"]):
        return "تبييض الاسنان يبدأ من 6000 جنيه 🦷"
    
    if any(word in msg for word in ["زراعة", "implant"]):
        return "زراعة الاسنان تبدأ من 8000 جنيه 💰"
    
    if any(word in msg for word in ["فينير", "veneer"]):
        return "الفينير يبدأ من 12000 جنيه ✨"
    
    if "حجز" in msg or "book" in msg:
        return "تمام 👌 ابعت اسمك ورقمك بالشكل ده:\nname: محمد, phone: 010..."

    return "ممكن تقولي نوع الخدمة؟"

# ----------------------------
# Save Leads (safe)
# ----------------------------
def save_lead(name, phone):
    try:
        with open("leads.csv", "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([name, phone, datetime.now()])
    except Exception as e:
        print("Save error:", e)

# ----------------------------
# Chat API
# ----------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        msg = data.get("message", "")

        if "name:" in msg and "phone:" in msg:
            try:
                name = msg.split("name:")[1].split(",")[0].strip()
                phone = msg.split("phone:")[1].strip()
                save_lead(name, phone)

                return jsonify({"reply": "تم الحجز ✅"})
            except:
                return jsonify({"reply": "اكتب كده:\nname: محمد, phone: 010..."})

        return jsonify({"reply": get_reply(msg)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500