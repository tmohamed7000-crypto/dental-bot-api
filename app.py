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

if ADMIN_CHAT_ID:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

# =========================
# SERVICES (ثابت واحد بس)
# =========================
SERVICES = {
    "تبييض": {"price": "6000 جنيه"},
    "فينير": {"price": "12000 جنيه"},
    "زراعة": {"price": "8000 جنيه"},
    "كشف": {"price": "350 جنيه"},
    "تقويم": {"price": "400 جنيه"},
    "طوارئ": {"price": "1200 جنيه"},
    "ابتسامة": {"price": "2000 جنيه"}
}

# =========================
# DATABASE
# =========================
def init_db():
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        service TEXT,
        tag TEXT,
        status TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

def save_client(name, phone, service, tag):
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    c.execute(
        "INSERT INTO clients (name, phone, service, tag, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (name, phone, service, tag, "جديد", datetime.now().strftime("%Y-%m-%d %H:%M"))
    )

    conn.commit()
    conn.close()

# =========================
# VALIDATION
# =========================
def validate_name(name):
    return len(name.strip()) >= 3

def validate_phone(phone):
    return re.match(r"^\+?\d{10,15}$", phone)

# =========================
# SESSION
# =========================
user_states = {}

# =========================
# AI
# =========================
def ask_ai(user_text):
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
حدد الخدمة فقط من:
تبييض - فينير - زراعة - كشف

ارجع JSON فقط:
{
"service": "اسم الخدمة",
"tag": "ألم أو تجميل أو زراعة"
}
"""
                },
                {"role": "user", "content": user_text}
            ]
        )

        content = completion.choices[0].message.content
        return json.loads(content)

    except:
        return {
            "service": "كشف",
            "tag": "ألم"
        }

# =========================
# SALES
# =========================
def build_sales_reply(service):
    data = SERVICES.get(service)

    if not data:
        service = "كشف"
        data = SERVICES["كشف"]

    return f"""
تمام 👌

الخدمة: {service} 💎  
السعر: {data['price']}  

🔥 الأماكن محدودة اليومين دول  
والحجز بدري بيضمنلك معاد مناسب  

تحب أحجزلك دلوقتي؟  
قولّي اسمك 👇
"""

# =========================
# HOME
# =========================
@app.route("/")
def home():
    return send_from_directory(".", "index.html")

# =========================
# CHAT
# =========================
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    msg = data.get("message")

    if not msg:
        return jsonify({"error": "No message"}), 400

    lower = msg.lower()
    user_id = request.remote_addr

    if user_id not in user_states:
        user_states[user_id] = {
            "step": "start",
            "service": None,
            "name": None,
        }

    state = user_states[user_id]

    # =====================
    # 👋 Greeting
    # =====================
    if state["step"] == "start" and any(x in lower for x in ["السلام", "اهلا", "hi", "hello"]):
        state["step"] = "ask_service"
        return jsonify({"reply": "أهلاً 👋 قولّي المشكلة أو اختار خدمة"})

    # =====================
    # 🧠 تحديد الخدمة
    # =====================
    if state["step"] in ["start", "ask_service"] and state["service"] is None:

        ai = ask_ai(msg)
        service = ai.get("service", "كشف")

        state["service"] = service
        state["step"] = "ask_name"   # 🔥 أهم سطر

        reply = build_sales_reply(service)

        send_to_telegram(f"💬 {msg}\n🦷 {service}")

        return jsonify({"reply": reply})

    # =====================
    # 👤 الاسم
    # =====================
    if state["step"] == "ask_name":

        if not validate_name(msg):
            return jsonify({"reply": "❌ الاسم لازم يكون 3 حروف على الأقل"})

        state["name"] = msg
        state["step"] = "ask_phone"

        return jsonify({"reply": "تمام 👍 ابعت رقمك 📞"})

    # =====================
    # 📞 الهاتف
    # =====================
    if state["step"] == "ask_phone":

        if not validate_phone(msg):
            return jsonify({"reply": "❌ رقم غير صحيح (مثال: 010xxxxxxxx)"})

        name = state["name"]
        phone = msg
        service = state["service"]

        ai = ask_ai(service)
        tag = ai.get("tag", "غير معروف")

        save_client(name, phone, service, tag)

        send_to_telegram(
            f"🔥 عميل جديد\n👤 {name}\n📞 {phone}\n🦷 {service}\n🏷 {tag}"
        )

        # ✅ أهم سطرين
        state["step"] = "done"
        state["service"] = None
        state["name"] = None

        return jsonify({
            "reply": "🔥 تم الحجز! هنتواصل معاك خلال دقائق"
        })
# =========================
# ADMIN
# =========================
@app.route("/admin")
def admin():
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    c.execute("SELECT name, phone, service, tag, status FROM clients ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    html = "<h2>📋 العملاء</h2><table border=1 cellpadding=10>"

    for r in rows:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td></tr>"

    html += "</table>"
    return html

# =========================
# TELEGRAM
# =========================
def send_message(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
    except:
        pass

def send_to_telegram(text):
    if ADMIN_CHAT_ID:
        send_message(ADMIN_CHAT_ID, text)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)