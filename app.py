import os
import re
import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# =========================
# ENV
# =========================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = OpenAI(base_url="https://openrouter.ai", api_key=OPENROUTER_API_KEY)

# =========================
# SERVICES
# =========================
SERVICES = {
    "تبييض": {"price": "6000 جنيه", "link": "https://setmore.com"},
    "فينير": {"price": "12000 جنيه", "link": "https://setmore.com"},
    "زراعة": {"price": "8000 جنيه", "link": "https://setmore.com"},
    "كشف": {"price": "350 جنيه", "link": "https://setmore.com"},
    "تقويم": {"price": "400 جنيه", "link": "https://setmore.com"},
    "طوارئ": {"price": "1200 جنيه", "link": "https://setmore.com"},
    "ابتسامة": {"price": "2000 جنيه", "link": "https://setmore.com"},
    "عروسة": {"price": "4000 جنيه", "link": "https://setmore.com"}
}

# =========================
# DATABASE
# =========================
def init_db():
    conn = sqlite3.connect("clients.db")
    conn.execute("CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, service TEXT, status TEXT, created_at TEXT)")
    conn.commit()
    conn.close()

init_db()

# =========================
# AI CORE (الفهم السياقي العميق)
# =========================
def ask_ai(user_text):
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": """أنت مساعد استقبال ذكي في عيادة أسنان. مهمتك تحليل كلام المريض أياً كانت لغته أو ثقافته.
                - إذا كان المريض يشتكي من أي (ألم، وجع، حساسية، كسر، عدم راحة، نزيف، ورم) -> صنفها 'طوارئ'.
                - إذا كان المريض يسأل عن (تجميل، تحسين شكل، تفتيح لون، ابتسامة، هوليوود سمايل) -> صنفها 'تبييض' أو 'فينير' أو 'ابتسامة'.
                - إذا كان الكلام غير واضح طبياً -> صنفها 'كشف'.
                يجب أن تعيد JSON فقط: {"service": "اسم الخدمة باللغة العربية حصراً"}"""},
                {"role": "user", "content": user_text}
            ]
        )
        content = completion.choices.message.content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except:
        return {"service": "كشف"}

# =========================
# ROUTES
# =========================
user_states = {}

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    msg = data.get("message", "")
    user_id = request.remote_addr
    if user_id not in user_states: user_states[user_id] = {"step": "ask_service", "service": None}
    state = user_states[user_id]

    # منطق التحية الذكي
    if any(x in msg.lower() for x in ["سلام", "اهلا", "صباح", "مساء", "hi", "hello"]):
        return jsonify({"reply": "وعليكم السلام ورحمة الله وبركاته! نورت عيادة أوبتمم كير (د. هبة عمار). ✨\nأنا سارة، كيف يمكنني مساعدتك اليوم؟", "show_services": True})

    # منطق الحجز النهائي
    if "final_booking:" in msg:
        # استخراج البيانات من الرسالة المنسقة القادمة من الـ HTML
        match = re.search(r"name: (.*) phone: (.*) service: (.*)", msg)
        if match:
            name, phone, service = match.groups()
            conn = sqlite3.connect("clients.db")
            conn.execute("INSERT INTO clients (name, phone, service, created_at) VALUES (?,?,?,?)", (name, phone, service, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            conn.close()
            # تنبيه تليجرام
            if ADMIN_CHAT_ID:
                requests.post(f"https://telegram.org{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": ADMIN_CHAT_ID, "text": f"🔥 حجز جديد\n👤 {name}\n📞 {phone}\n🦷 {service}"})
            
            link = SERVICES.get(service, SERVICES["كشف"])["link"]
            user_states[user_id] = {"step": "ask_service", "service": None} # ريست للحالة
            return jsonify({"reply": f"تم تسجيل طلبك بنجاح يا {name}! ✅\nوسيقوم فريق الاستقبال بالتواصل معك قريباً.\nيمكنك تأكيد الحجز فوراً من هنا: {link}"})

    # منطق الفهم السياقي
    if state["step"] == "ask_service":
        ai_res = ask_ai(msg)
        service = ai_res.get("service")
        if service in SERVICES:
            state["service"] = service
            state["step"] = "collect_data"
            res = SERVICES[service]
            return jsonify({"reply": f"سلامتك! ألف سلامة عليك. 🌹\nبناءً على كلامك، حضرتك محتاج خدمة {service}.\n💰 التكلفة التقريبية: {res['price']}.\n\nممكن تشرفني باسمك الثلاثي ورقم موبايلك لنرتب لك الموعد؟ 👇"})
        return jsonify({"reply": "نحن هنا لخدمتك! هل تود حجز كشف طوارئ أم استفسار عن خدمات التجميل؟", "show_services": True})

    return jsonify({"reply": "عذراً، هل يمكنك توضيح طلبك؟"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
