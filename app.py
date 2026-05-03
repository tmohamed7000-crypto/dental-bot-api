import os, re, json, sqlite3, requests
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# =========================
# الإعدادات
# =========================
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

# =========================
# قاعدة بيانات مبسطة جداً
# =========================
def init_db():
    conn = sqlite3.connect("clients.db")
    conn.execute("DROP TABLE IF EXISTS clients") # إعادة إنشاء الجدول لتجنب تعارض الأعمدة
    conn.execute("CREATE TABLE clients (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, service TEXT, created_at TEXT)")
    conn.commit()
    conn.close()

init_db()

# =========================
# الذكاء الاصطناعي
# =========================
def ask_ai(user_text):
    pain_keywords = ["الم", "ألم", "وجع", "تعب", "بيوجع", "درسي", "سنتي", "مكسور", "حساسية"]
    if any(x in user_text for x in pain_keywords):
        return {"service": "طوارئ"}
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[{"role": "system", "content": "صنف لخدمة واحدة فقط: (تبييض، فينير، زراعة، كشف، تقويم، طوارئ، ابتسامة، عروسة). أرجع JSON فقط: {'service': 'اسم الخدمة'}"},
                      {"role": "user", "content": user_text}]
        )
        return json.loads(completion.choices[0].message.content.replace("```json", "").replace("```", "").strip())
    except: return {"service": "كشف"}

# =========================
# منطق المحادثة والحجز
# =========================
user_states = {}

@app.route("/")
def home(): return send_from_directory(".", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    msg = data.get("message", "")
    user_id = request.remote_addr

    # --- استلام الحجز من الفورم ---
    if isinstance(msg, dict):
        name = msg.get("name", "غير معروف")
        phone = msg.get("phone", "بدون رقم")
        service = msg.get("service", "كشف")
        
        try:
            # 1. حفظ في قاعدة البيانات
            conn = sqlite3.connect("clients.db")
            conn.execute("INSERT INTO clients (name, phone, service, created_at) VALUES (?,?,?,?)", 
                         (name, phone, service, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            conn.close()

            # 2. إرسال تليجرام (في بلوك محمي لعدم تعطيل الحجز)
            try:
                if ADMIN_CHAT_ID and TELEGRAM_BOT_TOKEN:
                    txt = f"🔥 حجز جديد\n👤 الاسم: {name}\n📞 الهاتف: {phone}\n🦷 الخدمة: {service}"
                    requests.post(f"https://telegram.org{TELEGRAM_BOT_TOKEN}/sendMessage", 
                                  json={"chat_id": int(ADMIN_CHAT_ID), "text": txt}, timeout=3)
            except: pass 

            link = SERVICES.get(service, SERVICES["كشف"])["link"]
            return jsonify({"reply": f"تم تسجيل طلبك بنجاح يا {name}! ✅\nوسيقوم فريق الاستقبال بالتواصل معك قريباً.\nيمكنك تأكيد الحجز فوراً من هنا: {link}"})
        
        except Exception as e:
            return jsonify({"reply": f"عذراً، حدث خطأ تقني: {str(e)}"})

    # --- منطق الشات العادي ---
    if user_id not in user_states: user_states[user_id] = {"step": "ask_service", "service": None}
    state = user_states[user_id]
    
    if any(x in str(msg).lower() for x in ["سلام", "اهلا", "hi", "بكام"]):
        return jsonify({"reply": "وعليكم السلام! نورت عيادة أوبتمم كير. أنا سارة، كيف يمكنني مساعدتك؟", "show_services": True})

    if state["step"] == "ask_service":
        ai_res = ask_ai(str(msg))
        service = ai_res.get("service")
        if service in SERVICES:
            state["service"] = service
            state["step"] = "collect_data"
            return jsonify({"reply": f"سلامتك! ألف سلامة عليك. 🌹\nبناءً على كلامك، حضرتك محتاج خدمة {service}.\nالتكلفة التقريبية: {SERVICES[service]['price']}.\n\nممكن تشرفني باسمك الثلاثي ورقم موبايلك؟ 👇", "current_service": service})
    
    return jsonify({"reply": "نحن هنا لخدمتك! هل تود حجز كشف طوارئ أم تجميل؟", "show_services": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
