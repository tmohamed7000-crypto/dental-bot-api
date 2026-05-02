from flask import Flask
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "HELLO", 200

# شغل السيرفر مباشرة بدون شرط
port = int(os.environ.get("PORT", 8080))
app.run(host="0.0.0.0", port=port)