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
    return "Dental Bot API is running 🚀"

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

    return "ممكن تقولي نوع الخدمة؟ (تبييض - زراعة - فينير)"

# ----------------------------
# Save Lead (Safe)
# ----------------------------
def save_lead(name, phone):
    try:
        with open("leads.csv", mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([name, phone, datetime.now()])
    except Exception as e:
        print("Error saving lead:", e)

# ----------------------------
# API
# ----------------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    msg = data.get("message", "")

    if "name:" in msg and "phone:" in msg:
        try:
            name = msg.split("name:")[1].split(",")[0].strip()
            phone = msg.split("phone:")[1].strip()

            save_lead(name, phone)

            return jsonify({"reply": "تم الحجز ✅ هنتواصل معاك قريب"})
        except:
            return jsonify({"reply": "حصل خطأ، ابعت البيانات بالشكل ده:\nname: محمد, phone: 010..."})

    reply = get_reply(msg)
    return jsonify({"reply": reply})

# ----------------------------
# Run
# ----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)