from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import datetime

# ✅ APP MUST BE DEFINED FIRST
app = Flask(__name__)
CORS(app)

DB_NAME = "weather.db"

def get_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

# ✅ DB INIT
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

# ✅ HOME ROUTE
@app.route("/")
def home():
    return render_template("dashboard.html")

# ✅ API ROUTE (RELAXED + DEBUG)
@app.route("/api/data", methods=["POST", "GET"])
def api_data():
    if request.method == "POST":
        data = request.get_json(force=True)
        print("RECEIVED JSON:", data)

        try:
            temperature = float(data["temperature"])
            humidity = float(data["humidity"])
            rain_value = int(data["rain_value"])
            rain_status = str(data["rain_status"])
        except Exception as e:
            print("DATA ERROR:", e)
            return jsonify({"error": "Bad data"}), 400

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

        return jsonify({"status": "ok"}), 200

    # GET latest data
    con = get_db()
    cur = con.execute(
        "SELECT temperature, humidity, rain_status, time FROM weather ORDER BY id DESC LIMIT 1"
    )
    row = cur.fetchone()
    con.close()

    if not row:
        return jsonify({
            "temperature": None,
            "humidity": None,
            "rain": None,
            "time": None
        })

    return jsonify({
        "temperature": row[0],
        "humidity": row[1],
        "rain": row[2],
        "time": row[3]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
