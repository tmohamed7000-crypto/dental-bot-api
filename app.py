from flask import Flask, request, jsonify
import csv
from datetime import datetime

app = Flask(__name__)

# ----------------------------
# Knowledge Base
# ----------------------------
def get_reply(msg):
    msg = msg.lower()

    if "تبييض" in msg:
        return "تبييض الاسنان يبدأ من 6000 جنيه 🦷"
    
    if "زراعة" in msg:
        return "زراعة الاسنان تبدأ من 8000 جنيه 💰"
    
    if "فينير" in msg:
        return "الفينير يبدأ من 12000 جنيه ✨"
    
    if "حجز" in msg:
        return "تمام 👌 ابعت اسمك ورقمك علشان نحجز لك"

    return "ممكن تقولي نوع الخدمة؟ (تبييض - زراعة - فينير)"

# ----------------------------
# حفظ البيانات
# ----------------------------
def save_lead(name, phone):
    with open("leads.csv", mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([name, phone, datetime.now()])

# ----------------------------
# API
# ----------------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    msg = data.get("message")

    # لو المستخدم بعت بياناته
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


if __name__ == "__main__":
    app.run(debug=True)