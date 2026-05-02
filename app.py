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
# SERVICES (بيانات عيادة أوبتمم كير الحقيقية)
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
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, phone TEXT, service TEXT, tag TEXT, status TEXT, created_at TEXT
    )""")
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
# AI (شخصية أوبتمم كير)
# =========================
def ask_ai(user_text):
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """أنت مساعد عيادة Optimum Care Dental Clinic (د. هبة عمار). 
                    حدد الخدمة فقط من: تبييض - فينير - زراعة - كشف - تقويم - طوارئ - ابتسامة - عروسة.
                    أرجع JSON فقط: {"service": "اسم الخدمة", "tag": "تجميل أو علاج"}"""
                },
                {"role": "user", "content": user_text}
            ]
        )
        return json.loads(completion.choices[0].message.content)
    except:
        return {"service": "كشف", "tag": "علاج"}

# =========================
# SALES REPLY
# =========================
def build_sales_reply(service):
    data = SERVICES.get(service, SERVICES["كشف"])
    
    reply = f"بكل سرور! في عيادة أوبتمم كير (د. هبة عمار) نقدم خدمة {service} بأعلى معايير التعقيم.\n\n"
    reply += f"💰 السعر: {data['price']}\n"
    reply += "📍 مدينة نصر، أرض الجولف.\n"
    reply += "🕒 مواعيدنا: الأحد للأربعاء (3:30م - 9:30م).\n\n"
    reply += "تحب أحجزلك ميعاد استشارة؟ قولّي اسمك الثلاثي 👇"
    return reply

# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    msg = data.get("message", "")
    user_id = request.remote_addr

    if user_id not in user_states:
        user_states[user_id] = {"step": "start", "service": None, "name": None}

    state = user_states[user_id]
    lower = msg.lower()

    # 1. الترحيب الذكي (كما فعلنا سابقاً)
    greeting_keywords = ["السلام عليكم", "سلام", "اهلا", "صباح الخير", "مساء الخير", "hi", "hello"]
    if state["step"] == "start" and any(x in lower for x in greeting_keywords):
        state["step"] = "ask_service"
        reply_intro = "وعليكم السلام ورحمة الله وبركاته! أهلاً بك في عيادة أوبتمم كير. ✨" if "السلام عليكم" in lower else "أهلاً بك في عيادة أوبتمم كير! 😊"
        return jsonify({"reply": f"{reply_intro}\nأنا مساعدك الذكي، موجود هنا للإجابة على أسعارنا وخدماتنا. كيف يمكنني مساعدتك اليوم؟"})

    # 2. فهم "الشكوى" أو "الخدمة" باستخدام الذكاء الاصطناعي (حل مشكلة الصورة)
    if state["step"] == "ask_service":
        ai = ask_ai(msg)
        service = ai.get("service")
        
        # إذا فهم الـ AI أن هناك ألم أو خدمة معينة
        if service and service in SERVICES:
            state["service"] = service
            state["step"] = "ask_name"
            return jsonify({"reply": build_sales_reply(service)})
        else:
            # إذا لم يفهم الـ AI، بدلاً من "عذراً"، نسأله بطريقة ألطف
            return jsonify({"reply": "سلامتك! هل تقصد أنك تعاني من ألم وتريد حجز (كشف طوارئ) أم تستفسر عن خدمات التجميل مثل التبييض والتقويم؟"})

    # 3. إكمال مسار الاسم والهاتف (كما هو في الكود السابق)
    if state["step"] == "ask_name":
        if not validate_name(msg):
            return jsonify({"reply": "❌ يرجى كتابة الاسم بشكل صحيح (3 حروف فأكثر)."})
        state["name"] = msg
        state["step"] = "ask_phone"
        return jsonify({"reply": f"تشرفنا يا {msg}! ممكن رقم موبايلك ليتواصل معك فريق الاستقبال؟ 📞"})

    if state["step"] == "ask_phone":
        if not validate_phone(msg):
            return jsonify({"reply": "❌ رقم الهاتف غير صحيح. يرجى إدخاله بشكل صحيح."})
        # ... تكملة كود الحفظ وإرسال تليجرام ...

    # =====================
    # 👋 الترحيب الذكي (Human-like Greeting)
    # =====================

    # مصفوفة للتحيات الشائعة
    greeting_keywords = ["السلام عليكم", "سلام", "اهلا", "صباح الخير", "مساء الخير", "hi", "hello"]
    
    if any(x in lower for x in greeting_keywords):
        # الرد الإنساني بناءً على التحية
        if "السلام عليكم" in lower:
            reply_intro = "وعليكم السلام ورحمة الله وبركاته! أهلاً بك في عيادة أوبتمم كير. ✨"
        elif "صباح" in lower:
            reply_intro = "صباح النور والجمال! أهلاً بك في عيادتنا. ☀️"
        else:
            reply_intro = "أهلاً بك! نورت عيادة أوبتمم كير (د. هبة عمار). 😊"

        # إذا كانت هذه أول مرة يتكلم فيها، نغير الحالة ونعرض الخدمات
        if state["step"] == "start":
            state["step"] = "ask_service"
            return jsonify({"reply": f"{reply_intro}\nأنا مساعدك الذكي، موجود هنا للإجابة على أسعارنا وخدماتنا. كيف يمكنني مساعدتك اليوم؟"})
        else:
            # إذا كان سلم مرة تانية في نص الكلام، نرد عليه بذوق ونذكره بالخطوة الحالية
            return jsonify({"reply": f"{reply_intro} كيف يمكنني مساعدتك الآن؟"})

    # 🧠 تحديد الخدمة
    if state["step"] == "ask_service":
        ai = ask_ai(msg)
        state["service"] = ai.get("service", "كشف")
        state["step"] = "ask_name"
        return jsonify({"reply": build_sales_reply(state["service"])})

    # 👤 الاسم
    if state["step"] == "ask_name":
        if not validate_name(msg):
            return jsonify({"reply": "❌ يرجى كتابة الاسم الثلاثي بشكل صحيح."})
        state["name"] = msg
        state["step"] = "ask_phone"
        return jsonify({"reply": f"تشرفنا يا {msg}! ممكن رقم موبايلك للتواصل؟ 📞"})

    # 📞 الهاتف والحجز النهائي
    if state["step"] == "ask_phone":
        if not validate_phone(msg):
            return jsonify({"reply": "❌ عذراً، رقم الهاتف غير صحيح. (مثال: 010xxxxxxxx)"})
        
        service_data = SERVICES.get(state["service"], SERVICES["كشف"])
        save_client(state["name"], msg, state["service"], "AI_Lead")
        
        send_to_telegram(f"🔥 حجز جديد!\n👤 {state['name']}\n📞 {msg}\n🦷 {state['service']}")

        final_reply = f"تم تسجيل طلبك بنجاح يا {state['name']}! ✅\n\n"
        final_reply += f"يمكنك تأكيد حجزك فوراً من خلال رابط العيادة المباشر: \n{service_data['link']}\n\n"
        final_reply += "وسيقوم فريق الاستقبال بالتواصل معك قريباً."
        
        user_states[user_id] = {"step": "start", "service": None, "name": None} # Reset
        return jsonify({"reply": final_reply})

    return jsonify({"reply": "عذراً، هل يمكنك توضيح طلبك؟"})

# =========================
# TELEGRAM & ADMIN
# =========================
def send_to_telegram(text):
    if ADMIN_CHAT_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                          json={"chat_id": ADMIN_CHAT_ID, "text": text}, timeout=5)
        except: pass

@app.route("/admin")
def admin():
    conn = sqlite3.connect("clients.db")
    rows = conn.execute("SELECT name, phone, service, created_at FROM clients ORDER BY id DESC").fetchall()
    conn.close()
    html = "<h2>📋 حجوزات عيادة أوبتمم كير</h2><table border=1 cellpadding=10><tr><th>الاسم</th><th>الهاتف</th><th>الخدمة</th><th>التاريخ</th></tr>"
    for r in rows: html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>"
    return html + "</table>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
