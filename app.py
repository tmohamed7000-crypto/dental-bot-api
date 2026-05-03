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
    "تبييض": {"price": "6000 جنيه", "link": "https://abdobfpn.setmore.com/"},
    "فينير": {"price": "12000 جنيه", "link": "https://abdobfpn.setmore.com/"},
    "زراعة": {"price": "8000 جنيه", "link": "https://abdobfpn.setmore.com/"},
    "كشف": {"price": "350 جنيه", "link": "https://abdobfpn.setmore.com/"},
    "تقويم": {"price": "400 جنيه", "link": "https://abdobfpn.setmore.com/"},
    "طوارئ": {"price": "1200 جنيه", "link": "https://abdobfpn.setmore.com/"},
    "ابتسامة": {"price": "2000 جنيه", "link": "https://abdobfpn.setmore.com/"},
    "عروسة": {"price": "4000 جنيه", "link": "https://abdobfpn.setmore.com/"}
}

# =========================
# قاعدة بيانات مبسطة جداً
# =========================
def init_db():
    conn = sqlite3.connect("clients.db")
    # نستخدم CREATE TABLE IF NOT EXISTS بدون DROP TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            name TEXT, 
            phone TEXT, 
            service TEXT, 
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def ask_ai(user_text):
    # 1. فلترة التحيات الصريحة أولاً لسرعة الرد
    greetings = ["مساء", "صباح", "اهلا", "أهلا", "نورت", "سلام", "ازيك"]
    if any(word in user_text for word in greetings):
        return {"service": None}

    # 2. ترك الذكاء الاصطناعي يقرر (لأنه الأذكى في فهم الأخطاء الإملائية مثل 'تبيض')
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"أنت خبير تصنيف. حدد الخدمة المطلوبة من القائمة: ({', '.join(SERVICES.keys())}). افهم القصد حتى لو وجدت أخطاء إملائية. إذا كان الكلام بعيداً عن الخدمات أو مجرد تحية أرجع {{'service': null}}. أرجع JSON فقط."},
                {"role": "user", "content": user_text}
            ],
            response_format={ "type": "json_object" } # تضمن لك استلام JSON سليم دائماً
        )
        res = json.loads(completion.choices.message.content)
        
        # التأكد أن الخدمة التي اختارها الـ AI موجودة في قائمتنا فعلاً
        if res.get("service") in SERVICES:
            return res
        return {"service": None}
    except:
        # 3. في حالة فشل الـ AI (مثلاً مشكلة انترنت)، نلجأ للقواعد اليدوية كمحرك احتياطي
        mapping = {"زراعة": "زراعة", "تبييض": "تبييض", "تبيض": "تبييض", "تقويم": "تقويم", "كشف": "كشف"}
        for key in mapping:
            if key in user_text: return {"service": mapping[key]}
        return {"service": None}
    
# =========================
# منطق المحادثة والحجز
# =========================
user_states = {}

@app.route("/")
def home(): return send_from_directory(".", "index.html")

# =========================
# لوحة التحكم (Admin Panel)
# =========================
@app.route("/admin")
def admin():
    try:
        conn = sqlite3.connect("clients.db")
        # ترتيب العملاء من الأحدث للأقدم
        rows = conn.execute("SELECT name, phone, service, created_at FROM clients ORDER BY id DESC").fetchall()
        conn.close()

        # تصميم الجدول بشكل احترافي وبسيط
        html = """
        <html dir='rtl'>
        <head><title>لوحة الحجوزات</title>
        <style>
            body { font-family: sans-serif; padding: 20px; background: #f4f7f6; }
            table { width: 100%; border-collapse: collapse; background: white; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
            th, td { padding: 12px; border: 1px solid #ddd; text-align: center; }
            th { background-color: #008080; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
        </style>
        </head>
        <body>
            <h2 style='text-align:center; color:#008080;'>📋 حجوزات عيادة أوبتمم كير</h2>
            <table>
                <tr><th>الاسم</th><th>الهاتف</th><th>الخدمة</th><th>تاريخ الحجز</th></tr>
        """
        for r in rows:
            html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>"
        
        return html + "</table></body></html>"
    except Exception as e:
        return f"خطأ في الوصول لقاعدة البيانات: {str(e)}"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    msg = data.get("message", "")
    user_id = request.remote_addr

    if isinstance(msg, dict) and msg.get("type") == "final_booking":
        try:
            name, phone, service = msg.get("name"), msg.get("phone"), msg.get("service")
            conn = sqlite3.connect("clients.db")
            conn.execute("INSERT INTO clients (name, phone, service, created_at) VALUES (?,?,?,?)", 
                         (name, phone, service, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            conn.close()

            if ADMIN_CHAT_ID and TELEGRAM_BOT_TOKEN:
                txt = f"🔥 حجز جديد\n👤 {name}\n📞 {phone}\n🦷 {service}"
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                              json={"chat_id": int(ADMIN_CHAT_ID), "text": txt}, timeout=5)
            
            link = SERVICES.get(service, SERVICES["كشف"])["link"]
            reply_html = f"تم تسجيل طلبك بنجاح يا {name}! ✅<br><br>وسيقوم فريق الاستقبال بالتواصل معك قريباً.<br><a href='{link}' target='_blank' style='color: #008080; font-weight: bold;'>اضغط هنا لفتح جدول المواعيد</a>"
            return jsonify({"reply": reply_html})
        except:
            return jsonify({"reply": "عذراً، حدث خطأ في الحفظ."})
        
    if user_id not in user_states: user_states[user_id] = {"step": "ask_service", "service": None}
    state = user_states[user_id]
    msg_text = str(msg)

    # التعديل الجوهري: نسأل الذكاء الاصطناعي أولاً
    if state["step"] == "ask_service":
        ai_res = ask_ai(msg_text)
        service = ai_res.get("service")
        
        if service and service in SERVICES:
            state["service"], state["step"] = service, "collect_data"
            res = SERVICES[service]
            intro = "سلامتك! ألف سلامة عليك. 🌹" if service == "طوارئ" else "اختيار ممتاز! ✨"
            return jsonify({
                "reply": f"{intro}\nبناءً على طلبك، محتاج خدمة {service}.\nالتكلفة التقريبية: {res['price']}.\n\nممكن تشرفني باسمك ورقم موبايلك لنرتب لك الموعد؟ 👇", 
                "current_service": service
            })

        # إذا لم يجد الذكاء الاصطناعي خدمة، نتحقق من التحية
        if any(x in msg_text.lower() for x in ["سلام", "اهلا", "hi", "hello", "مساء", "صباح"]):
            return jsonify({"reply": "وعليكم السلام ورحمة الله وبركاته! نورت عيادة أوبتمم كير. ✨\nأنا سارة، كيف يمكنني مساعدتك اليوم؟", "show_services": True})

    # الرد الافتراضي في حال عدم فهم أي شيء
    return jsonify({"reply": "أهلاً بك! يمكنك اختيار خدمة من الأزرار بالأسفل أو إخباري بمشكلتك وسأساعدك فوراً.", "show_services": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
