from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import datetime

app = Flask(__name__)
CORS(app)

DB_NAME = "weather.db"

def get_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

# DB init
def init_db():
    con = get_db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            temperature REAL,
            humidity REAL,
            rain_status TEXT,
            time TEXT
        )
    """)
    con.commit()
    con.close()

init_db()

@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/api/data", methods=["POST", "GET"])
def api_data():

    # ===== ESP POST =====
    if request.method == "POST":
        data = request.get_json(force=True, silent=True)

        temperature = float(data.get("temperature", 0))
        humidity = float(data.get("humidity", 0))
        rain = data.get("rain_status", "Unknown")

        now = datetime.datetime.utcnow()

        con = get_db()
        con.execute(
            "INSERT INTO weather (temperature, humidity, rain_status, time) VALUES (?,?,?,?)",
            (
                temperature,
                humidity,
                rain,
                now.strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        con.commit()
        con.close()

        return jsonify({"status": "ok"}), 200

    # ===== DASHBOARD GET =====
    con = get_db()
    cur = con.execute(
        "SELECT temperature, humidity, rain_status, time FROM weather ORDER BY id DESC LIMIT 1"
    )
    row = cur.fetchone()
    con.close()

    if not row:
        return jsonify({"online": False})

    last_time = datetime.datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S")
    diff = (datetime.datetime.utcnow() - last_time).total_seconds()

    online = diff <= 10   # 🔥 10 sec threshold

    return jsonify({
        "online": online,
        "temperature": row[0],
        "humidity": row[1],
        "rain": row[2],
        "time": row[3]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
