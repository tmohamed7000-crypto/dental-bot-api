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
    base_url="https://openrouter.ai",
    api_key=OPENROUTER_API_KEY
)

# =========================
# SERVICES (بيانات عيادة أوبتمم كير)
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
# DATABASE INIT
# =========================
def init_db():
    conn = sqlite3.connect("clients.db")
    conn.execute("CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, service TEXT, tag TEXT, status TEXT, created_at TEXT)")
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
# AI LOGIC (فهم المعنى السياقي)
# =========================
def ask_ai(user_text):
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": """أنت مصنف ذكي لعيادة أسنان. مهمتك فهم نية المستخدم.
                - إذا اشتكى من (ألم، وجع، سنة مكسورة، ضرس، تعب) -> service: "طوارئ".
                - إذا سأل عن (تبييض، تفتيح) -> service: "تبييض".
                - إذا سأل عن (تقويم، سلك) -> service: "تقويم".
                - أرجع JSON فقط: {"service": "اسم الخدمة"}
                الخدمات المتاحة فقط: (تبييض، فينير، زراعة، كشف، تقويم، طوارئ، ابتسامة، عروسة)."""},
                {"role": "user", "content": user_text}
            ]
        )
        content = completion.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except:
        return {"service": "كشف"}

def build_sales_reply(service):
    data = SERVICES.get(service, SERVICES["كشف"])
    return f"بكل سرور! في عيادة أوبتمم كير نوفر خدمة {service}.\n💰 السعر: {data['price']}\n📍 مدينة نصر، أرض الجولف.\nتحب أحجزلك موعد استشارة؟ من فضلك اكتب اسمك الثلاثي 👇"

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
    lower = msg.lower()

    # الترحيب الذكي
    greetings = ["السلام عليكم", "اهلا", "صباح", "مساء", "سلام", "hi", "hello"]
    if any(x in lower for x in greetings):
        reply = "وعليكم السلام ورحمة الله وبركاته! نورت عيادة أوبتمم كير (د. هبة عمار). ✨\nأنا سارة، مساعدة الاستقبال. كيف يمكنني مساعدتك اليوم؟"
        return jsonify({"reply": reply})

    # تحليل الخدمة/الشكوى
    if state["step"] == "ask_service":
        ai_res = ask_ai(msg)
        service = ai_res.get("service")
        if service in SERVICES:
            state["service"] = service
            state["step"] = "ask_name"
            return jsonify({"reply": build_sales_reply(service)})
        return jsonify({"reply": "سلامتك! هل تود الاستفسار عن خدمات التجميل (تبييض/تقويم) أم حجز كشف طوارئ للألم؟"})

    # الاسم
    if state["step"] == "ask_name":
        if len(msg.strip()) < 3: return jsonify({"reply": "من فضلك اكتب الاسم الثلاثي بشكل صحيح."})
        state["name"] = msg
        state["step"] = "ask_phone"
        return jsonify({"reply": f"تشرفنا يا {msg}! ممكن رقم موبايلك للتواصل؟ 📞"})

    # الهاتف
    if state["step"] == "ask_phone":
        if not re.match(r"^\+?\d{10,15}$", msg): return jsonify({"reply": "رقم الهاتف غير صحيح، يرجى كتابته بشكل صحيح."})
        save_client(state["name"], msg, state["service"])
        link = SERVICES[state["service"]]["link"]
        reply = f"تم تسجيل طلبك بنجاح يا {state['name']}! ✅\nيمكنك تأكيد الحجز فوراً من هنا: {link}\nوسنتصل بك قريباً."
        user_states[user_id] = {"step": "ask_service", "service": None, "name": None}
        return jsonify({"reply": reply})

    return jsonify({"reply": "عذراً، هل يمكنك توضيح طلبك؟"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
