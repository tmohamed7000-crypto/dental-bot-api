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

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = OpenAI(base_url="https://openrouter.ai", api_key=OPENROUTER_API_KEY)

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

def init_db():
    conn = sqlite3.connect("clients.db")
    conn.execute("CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, service TEXT, created_at TEXT)")
    conn.commit()
    conn.close()

init_db()

def ask_ai(user_text):
    # قاعدة برمجية صارمة قبل الـ AI: أي ألم = طوارئ
    pain_keywords = ["الم", "ألم", "وجع", "تعب", "بيوجع", "درسي", "سنتي", "مكسور"]
    if any(x in user_text for x in pain_keywords):
        return {"service": "طوارئ"}
    
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": "صنف الطلب لخدمة واحدة فقط: (تبييض، فينير، زراعة، كشف، تقويم، طوارئ، ابتسامة، عروسة). أرجع JSON: {'service': 'اسم الخدمة'}"},
                {"role": "user", "content": user_text}
            ]
        )
        return json.loads(completion.choices[0].message.content.replace("```json", "").replace("```", "").strip())
    except:
        return {"service": "كشف"}

user_states = {}

@app.route("/")
def home(): return send_from_directory(".", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    msg = data.get("message", "")
    user_id = request.remote_addr
    
    # التحقق إذا كانت البيانات قادمة من "فورم الحجز" كـ JSON
    if isinstance(msg, dict) and msg.get("type") == "final_booking":
        try:
            name = msg.get("name")
            phone = msg.get("phone")
            service = msg.get("service")
            
            conn = sqlite3.connect("clients.db")
            conn.execute("INSERT INTO clients (name, phone, service, created_at) VALUES (?,?,?,?)", 
                         (name, phone, service, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            conn.close()

            if ADMIN_CHAT_ID and TELEGRAM_BOT_TOKEN:
                requests.post(f"https://telegram.org{TELEGRAM_BOT_TOKEN}/sendMessage", 
                              json={"chat_id": ADMIN_CHAT_ID, "text": f"🔥 حجز جديد\n👤 {name}\n📞 {phone}\n🦷 {service}"})
            
            link = SERVICES.get(service, SERVICES["كشف"])["link"]
            return jsonify({"reply": f"تم تسجيل طلبك بنجاح يا {name}! ✅\nوسيقوم فريق الاستقبال بالتواصل معك قريباً.\nيمكنك تأكيد الحجز فوراً من هنا: {link}"})
        except:
            return jsonify({"reply": "عذراً، حدث خطأ في النظام. حاول مرة أخرى."})

    # باقي منطق المحادثة العادي (الذكاء الاصطناعي والتحية)
    if user_id not in user_states: user_states[user_id] = {"step": "ask_service", "service": None}
    state = user_states[user_id]
    
    if any(x in msg.lower() for x in ["سلام", "اهلا", "hi"]):
        return jsonify({"reply": "وعليكم السلام! نورت عيادة أوبتمم كير. أنا سارة، كيف يمكنني مساعدتك؟", "show_services": True})

    if state["step"] == "ask_service":
        ai_res = ask_ai(msg)
        service = ai_res.get("service")
        if service in SERVICES:
            state["service"] = service
            state["step"] = "collect_data"
            res = SERVICES[service]
            return jsonify({"reply": f"سلامتك! ألف سلامة عليك. 🌹\nبناءً على كلامك، حضرتك محتاج خدمة {service}.\nالتكلفة: {res['price']}.\n\nممكن تشرفني باسمك ورقم موبايلك؟ 👇", "current_service": service})
    
    return jsonify({"reply": "نحن هنا لخدمتك! هل تود حجز كشف طوارئ أم تجميل؟", "show_services": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
