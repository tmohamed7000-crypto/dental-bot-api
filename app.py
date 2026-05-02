import os
import re
import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
import requests

app = Flask(__name__)

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
# AI (SMART)
# =========================
def ask_ai(user_text):
    completion = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """
أنت موظف استقبال في عيادة أسنان.

افهم كلام العميل وحدد الخدمة المناسبة.

ارجع JSON فقط:

{
"reply": "رد مقنع فيه سعر + طلب الحجز",
"service": "اسم الخدمة",
"tag": "ألم أو تجميل أو زراعة"
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
        # 🔥 fallback ذكي
        return {
            "reply": f"""
واضح إن عندك مشكلة في الأسنان 😣

ممكن تحتاج كشف أو علاج مناسب للحالة  
الكشف عندنا 350 جنيه 🦷

تحب أحجزلك؟ ابعت:
name:
phone:
""",
            "service": "كشف",
            "tag": "ألم"
        }
# =========================
# HOME
# =========================
@app.route("/")
def home():
    return send_from_directory(".", "index.html")

# =========================
# CHAT API
# =========================
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    msg = data.get("message")

    if not msg:
        return jsonify({"error": "No message"}), 400

    lower = msg.lower()

    try:
        # =====================
        # 📥 حجز
        # =====================
        if "name:" in lower and "phone:" in lower:

            name = msg.split("name:")[1].split("phone:")[0].strip()
            phone = msg.split("phone:")[1].split("service:")[0].strip()

            service = "غير محدد"
            tag = "غير معروف"

            if "service:" in lower:
                service = msg.split("service:")[1].strip()

            # ✅ Validation
            if not validate_name(name):
                return jsonify({"reply": "❌ الاسم لازم يكون 3 حروف على الأقل"})

            if not validate_phone(phone):
                return jsonify({"reply": "❌ رقم الهاتف غير صحيح"})

            # 🧠 AI يحلل آخر رسالة (اختياري تحسين)
            ai = ask_ai(service)
            tag = ai.get("tag", "غير معروف")

            save_client(name, phone, service, tag)

            send_to_telegram(
                f"📥 عميل جديد:\n👤 {name}\n📞 {phone}\n🦷 {service}\n🏷 {tag}"
            )

            return jsonify({
                "reply": "تم الحجز ✅ هنكلمك قريب"
            })

        # =====================
        # 🤖 AI رد
        # =====================
        ai = ask_ai(msg)

        reply = ai["reply"]
        service = ai["service"]
        tag = ai["tag"]

        send_to_telegram(
            f"💬 {msg}\n🤖 {reply}\n🦷 {service}\n🏷 {tag}"
        )

        return jsonify({"reply": reply})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500

# =========================
# ADMIN PANEL
# =========================
@app.route("/admin")
def admin():
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    c.execute("SELECT id, name, phone, service, tag, status, created_at FROM clients ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    html = """
    <h2>📋 العملاء</h2>
    <table border=1 cellpadding=10>
    <tr>
    <th>الاسم</th>
    <th>الرقم</th>
    <th>الخدمة</th>
    <th>النوع</th>
    <th>الحالة</th>
    <th>تغيير</th>
    </tr>
    """

    for r in rows:
        html += f"""
        <tr>
        <td>{r[1]}</td>
        <td>{r[2]}</td>
        <td>{r[3]}</td>
        <td>{r[4]}</td>
        <td>{r[5]}</td>
        <td>
            <a href="/update/{r[0]}/تم التواصل">تم التواصل</a> |
            <a href="/update/{r[0]}/تم الحجز">تم الحجز</a>
        </td>
        </tr>
        """

    html += "</table>"
    return html

# =========================
# UPDATE STATUS
# =========================
@app.route("/update/<int:id>/<status>")
def update_status(id, status):
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    c.execute("UPDATE clients SET status=? WHERE id=?", (status, id))

    conn.commit()
    conn.close()

    return f"تم التحديث إلى {status} ✅ <br><a href='/admin'>رجوع</a>"

# =========================
# STATS API
# =========================
@app.route("/stats")
def stats():
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    c.execute("SELECT service, COUNT(*) FROM clients GROUP BY service")
    services = c.fetchall()

    c.execute("SELECT tag, COUNT(*) FROM clients GROUP BY tag")
    tags = c.fetchall()

    conn.close()

    return jsonify({
        "services": services,
        "tags": tags
    })

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
    except Exception as e:
        print("Telegram Error:", e)

def send_to_telegram(text):
    if ADMIN_CHAT_ID:
        send_message(ADMIN_CHAT_ID, text)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)