import os
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
        status TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

def save_client(name, phone, service):
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()

    c.execute(
        "INSERT INTO clients (name, phone, service, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, phone, service, "جديد", datetime.now().strftime("%Y-%m-%d %H:%M"))
    )

    conn.commit()
    conn.close()

# =========================
# SYSTEM PROMPT
# =========================
SYSTEM_PROMPT = """
أنت موظف استقبال محترف في Optimum Care Dental Clinic.

هدفك:
تحويل أي عميل لحجز.

أسلوبك:
- عربي بسيط
- مختصر
- مقنع

الخدمات:
- تبييض الأسنان: 6000 جنيه
- فينير: من 12000 جنيه
- زراعة: من 8000 جنيه

اطلب:
name:
phone:
"""

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
        # ===== حجز =====
        if "name:" in lower and "phone:" in lower:

            name = msg.split("name:")[1].split("phone:")[0].strip()
            phone = msg.split("phone:")[1].split("service:")[0].strip()

            service = "غير محدد"
            if "service:" in lower:
                service = msg.split("service:")[1].strip()

            save_client(name, phone, service)

            send_to_telegram(f"📥 عميل جديد:\n{name}\n{phone}\n{service}")

            return jsonify({
                "reply": "تم الحجز ✅ هنكلمك قريب"
            })

        # ===== AI =====
        reply = ask_ai(msg)

        send_to_telegram(f"💬 {msg}\n🤖 {reply}")

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

    c.execute("SELECT id, name, phone, service, status, created_at FROM clients ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    html = """
    <h2>📋 العملاء</h2>
    <table border=1 cellpadding=10>
    <tr>
    <th>الاسم</th>
    <th>الرقم</th>
    <th>الخدمة</th>
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
# AI
# =========================
def ask_ai(text):
    res = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ]
    )
    return res.choices[0].message.content

# =========================
# TELEGRAM
# =========================
def send_message(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text}
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