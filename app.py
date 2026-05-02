from flask import Flask, request, jsonify
import csv
from datetime import datetime
import os

app = Flask(__name__)

print("APP STARTED...")

# ----------------------------
# Home Route (مهم جداً)
# ----------------------------
@app.route("/")
def home():
    return "Dental API is running 🚀", 200


# ----------------------------
# Health Check (Railway بيحبها)
# ----------------------------
@app.route("/health")
def health():
    return {"status": "ok"}, 200


# ----------------------------
# Knowledge Base
# ----------------------------
def get_reply(msg):
    msg = (msg or "").lower()

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
# Save Leads (SAFE - بدون كراش)
# ----------------------------
def save_lead(name, phone):
    try:
        file_path = "leads.csv"

        # لو الملف مش موجود ينشئه
        if not os.path.exists(file_path):
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["name", "phone", "date"])

        # يضيف البيانات
        with open(file_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([name, phone, datetime.now()])

    except Exception as e:
        print("Save error:", e)


# ----------------------------
# API
# ----------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        # حماية من crash لو مش JSON
        data = request.get_json(silent=True) or {}
        msg = data.get("message", "")

        # لو المستخدم بعت بيانات
        if "name:" in msg and "phone:" in msg:
            try:
                name = msg.split("name:")[1].split(",")[0].strip()
                phone = msg.split("phone:")[1].strip()

                save_lead(name, phone)

                return jsonify({"reply": "تم الحجز ✅ هنتواصل معاك قريب"})
            except:
                return jsonify({"reply": "ابعت كده:\nname: محمد, phone: 010..."})

        return jsonify({"reply": get_reply(msg)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------------------
# تشغيل السيرفر
# ----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)