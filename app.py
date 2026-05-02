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

def save_client(name, phone, service):
    conn = sqlite3.connect("clients.db")
    conn.execute("INSERT INTO clients (name, phone, service, status, created_at) VALUES (?, ?, ?, ?, ?)",
                 (name, phone, service, "جديد", datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

# =========================
# AI LOGIC
# =========================
def ask_ai(user_text):
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": "صنف نية المستخدم لخدمة واحدة: (تبييض، فينير، زراعة، كشف، تقويم، طوارئ، ابتسامة، عروسة). إذا كان هناك ألم اختر طوارئ. أرجع JSON فقط: {'service': 'اسم الخدمة'}"},
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
    if user_id not in user_states: user_states[user_id] = {"step": "ask_service", "service": None, "name": None}
    state = user_states[user_id]
    
    # التحقق من التحية
    if any(x in msg.lower() for x in ["سلام", "اهلا", "hi", "hello"]):
        return jsonify({"reply": "وعليكم السلام! نورت عيادة أوبتمم كير. أنا سارة، كيف يمكنني مساعدتك؟", "show_services": True})

    # معالجة الخدمة
    if state["step"] == "ask_service":
        service = msg if msg in SERVICES else ask_ai(msg).get("service")
        if service in SERVICES:
            state["service"] = service
            state["step"] = "ask_name"
            res = SERVICES[service]
            return jsonify({"reply": f"خدمة {service} ممتازة! السعر: {res['price']}.\nمن فضلك اكتب اسمك الثلاثي لنحجز لك استشارة 👇"})
        return jsonify({"reply": "سلامتك! هل تريد حجز كشف طوارئ أم استفسار عن تجميل الأسنان؟", "show_services": True})

    # معالجة الحجز النهائي (الاسم والهاتف يتم استلامهم من الفورم في الـ HTML)
    if "phone:" in msg and "name:" in msg:
        parts = msg.split(" ")
        name = parts[1]
        phone = parts[3]
        save_client(name, phone, state["service"])
        # إرسال تليجرام هنا (اختياري)
        link = SERVICES[state["service"]]["link"]
        user_states[user_id] = {"step": "ask_service", "service": None, "name": None}
        return jsonify({"reply": f"تم الحجز بنجاح يا {name}! ✅\nيمكنك تأكيد الموعد الآن: {link}"})

    return jsonify({"reply": "عذراً، هل يمكنك توضيح طلبك؟"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
