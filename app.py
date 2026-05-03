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
    conn.execute("DROP TABLE IF EXISTS clients") # إعادة إنشاء الجدول لتجنب تعارض الأعمدة
    conn.execute("CREATE TABLE clients (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, service TEXT, created_at TEXT)")
    conn.commit()
    conn.close()

init_db()

# =========================
# الذكاء الاصطناعي
# =========================
def ask_ai(user_text):
    # 1. قاعدة الألم الصارمة (للحالات الطارئة فقط)
    pain_keywords = ["الم", "ألم", "وجع", "تعب", "بيوجع", "درسي", "سنتي", "مكسور"]
    
    # 2. قاعدة التجميل الصارمة (لمنع الخلط مع الكشف)
    cosmetic_keywords = ["تبييض", "تفتيح", "فينير", "تقويم", "ابتسامة", "عروسة"]

    # فحص يدوي سريع قبل الـ AI لضمان الدقة 100%
    if any(x in user_text for x in cosmetic_keywords):
        for key in cosmetic_keywords:
            if key in user_text: return {"service": key}
            
    if any(x in user_text for x in pain_keywords):
        return {"service": "طوارئ"}
    
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": "أنت مصنف خدمات عيادة أسنان. الخدمات: (تبييض، فينير، زراعة، كشف، تقويم، طوارئ، ابتسامة، عروسة). أرجع JSON فقط: {'service': 'اسم الخدمة'}"},
                {"role": "user", "content": user_text}
            ]
        )
        content = completion.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except:
        return {"service": "كشف"}

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

    # --- استلام الحجز من الفورم ---
    if isinstance(msg, dict) and msg.get("type") == "final_booking":
        try:
            name = msg.get("name")
            phone = msg.get("phone")
            service = msg.get("service")
            
            # حفظ في قاعدة البيانات
            conn = sqlite3.connect("clients.db")
            conn.execute("INSERT INTO clients (name, phone, service, created_at) VALUES (?,?,?,?)", 
                         (name, phone, service, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            conn.close()

            # ✅ تصحيح رابط تليجرام لضمان وصول الرسالة
            if ADMIN_CHAT_ID and TELEGRAM_BOT_TOKEN:
                txt = f"🔥 حجز جديد\n👤 {name}\n📞 {phone}\n🦷 {service}"
                # الرابط الصحيح يبدأ بـ api.telegram.org/bot
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                              json={"chat_id": int(ADMIN_CHAT_ID), "text": txt}, timeout=5)
            
            link = SERVICES.get(service, SERVICES["كشف"])["link"]
            
            # ✅ جعل الرابط قابل للضغط باستخدام HTML
            reply_html = f"تم تسجيل طلبك بنجاح يا {name}! ✅<br><br>وسيقوم فريق الاستقبال بالتواصل معك قريباً.<br>يمكنك تأكيد الحجز واختيار الساعة المناسبة من هنا:<br><a href='{link}' target='_blank' style='color: #008080; font-weight: bold;'>اضغط هنا لفتح جدول المواعيد</a>"
            
            return jsonify({"reply": reply_html})
        except:
            return jsonify({"reply": "عذراً، حدث خطأ في النظام."})
        
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
