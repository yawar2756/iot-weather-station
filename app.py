from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import datetime

app = Flask(__name__)
CORS(app)

DB_NAME = "weather.db"

def get_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

# Create DB safely
def init_db():
    con = get_db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            temperature REAL,
            humidity REAL,
            rain_value INTEGER,
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
    if request.method == "POST":
        data = request.get_json(force=True, silent=True)
        print("RAW DATA:", data)

        temperature = float(data.get("temperature", 0))
        humidity = float(data.get("humidity", 0))
        rain_value = int(data.get("rain_value", 0))
        rain_status = data.get("rain_status") or "Unknown"

        con = get_db()
        con.execute(
            "INSERT INTO weather (temperature, humidity, rain_value, rain_status, time) VALUES (?,?,?,?,?)",
            (
                temperature,
                humidity,
                rain_value,
                rain_status,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        con.commit()
        con.close()

        return jsonify({"status": "stored"}), 200

    # GET latest data
    con = get_db()
    cur = con.execute(
        "SELECT temperature, humidity, rain_status, time FROM weather ORDER BY id DESC LIMIT 1"
    )
    row = cur.fetchone()
    con.close()

    return jsonify({
        "temperature": row[0] if row else None,
        "humidity": row[1] if row else None,
        "rain": row[2] if row else None,
        "time": row[3] if row else None
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
