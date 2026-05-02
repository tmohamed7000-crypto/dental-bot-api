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
# 💰 PRICING
# =========================
PRICES = {
    "تبييض": "6000 جنيه",
    "زراعة": "8000 جنيه",
    "فينير": "12000 جنيه",
    "كشف": "100 جنيه"
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
    return re.match(r"^\+?\d{8,15}$", phone)

# =========================
# SESSION (flow)
# =========================
user_states = {}

# =========================
# 🧠 AI
# =========================
def ask_ai(user_text):
    completion = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """
أنت موظف استقبال محترف في عيادة أسنان.

مهمتك:
- فهم كلام العميل
- تحديد الخدمة المناسبة
- تحديد نوع الحالة

⚠️ ممنوع تذكر أي أسعار نهائيًا

الخدمات:
- تبييض (تجميل)
- فينير (تجميل)
- زراعة (زراعة)
- كشف (ألم أو فحص)

أمثلة:
- "سناني فيها ألم" → كشف
- "عايز ابتسامة حلوة" → تبييض أو فينير
- "سن واقع" → زراعة

ارجع JSON فقط بدون شرح:

{
"service": "اسم الخدمة",
"tag": "ألم أو تجميل أو زراعة",
"confidence": "high أو medium أو low"
}
"""
            },
            {"role": "user", "content": user_text}
        ]
    )

    content = completion.choices[0].message.content

    try:
        return json.loads(content)
    except:
        return {
            "service": "كشف",
            "tag": "ألم",
            "confidence": "low"
        }
# =========================
# 💥 SALES SCRIPT
# =========================
def build_sales_reply(service, confidence="high"):
    price = PRICES.get(service, "يحدد بعد الكشف")

    if confidence == "low":
        return """محتاج تفاصيل أكتر عن حالتك 🤔  
ممكن توضح المشكلة أكتر؟"""

    return f"""تمام 👌

واضح إنك محتاج {service} 🦷  
السعر يبدأ من {price}

🔥 عندنا عرض لفترة محدودة  
والحجز النهارده بيضمنلك أفضل نتيجة

تحب نحجزلك دلوقتي؟ قولي اسمك 👇"""

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
            "last_seen": datetime.now()
        }

    state = user_states[user_id]

    # =====================
    # 👋 Greeting
    # =====================
    greetings = ["السلام", "اهلا", "مرحبا", "hi", "hello"]

    if state["step"] == "start" and any(g in lower for g in greetings):
        state["step"] = "ask_service"

        return jsonify({
            "reply": "أهلاً بيك 👋\nقولّي المشكلة أو اختار خدمة:",
            "show_buttons": True
        })

    # =====================
    # 🧠 تحديد الخدمة
    # =====================
    if state["step"] in ["start", "ask_service"]:

        ai = ask_ai(msg)

        service = ai["service"]
        confidence = ai.get("confidence", "high")

        state["service"] = service
        state["step"] = "ask_name"

        reply = build_sales_reply(service, confidence)

        return jsonify({
            "reply": reply
        })
    # =====================
    # 👤 الاسم
    # =====================
    if state["step"] == "ask_name":

        if not validate_name(msg):
            return jsonify({"reply": "❌ الاسم لازم يكون 3 حروف على الأقل"})

        state["name"] = msg
        state["step"] = "ask_phone"

        return jsonify({
            "reply": "تمام 👍 ابعت رقمك عشان نحجزلك فورًا 📞"
        })

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
        tag = ai["tag"]

        save_client(name, phone, service, tag)

        send_to_telegram(
            f"🔥 عميل جديد\n👤 {name}\n📞 {phone}\n🦷 {service}\n🏷 {tag}"
        )

        state["step"] = "done"

        return jsonify({
            "reply": "🔥 تم الحجز! فريقنا هيكلمك خلال دقائق"
        })

    # =====================
    # 💤 FOLLOW-UP
    # =====================
    if state["step"] == "ask_name":
        return jsonify({
            "reply": "لسه مستني اسمك عشان نحجزلك 😉"
        })

    if state["step"] == "ask_phone":
        return jsonify({
            "reply": "ابعت رقمك بسرعة قبل ما العرض يخلص ⏳"
        })

    return jsonify({"reply": "قولّي محتاج إيه وأنا أساعدك 👌"})

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

    html = "<h2>العملاء</h2><table border=1>"

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