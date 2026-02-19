import os
import psycopg2
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        con = get_db()
        cur = con.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS weather (
                id SERIAL PRIMARY KEY,
                temperature FLOAT,
                humidity FLOAT,
                rain_value INT,
                rain_status TEXT,
                wind_speed FLOAT,
                wind_direction TEXT,
                visibility FLOAT,
                alert TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("ALTER TABLE weather ADD COLUMN IF NOT EXISTS alert TEXT;")

        con.commit()
        cur.close()
        con.close()
        print("Database initialized successfully")

    except Exception as e:
        print("Database init failed:", e)

init_db()


@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/health")
def health():
    return jsonify({"status": "running"})


@app.route("/api/data", methods=["POST"])
def receive_data():
    try:
        data = request.get_json(force=True)

        required = ["temperature", "humidity", "rain_value", "rain_status"]
        if not data or not all(k in data for k in required):
            return jsonify({"error": "Invalid data"}), 400

        temperature = data["temperature"]
        humidity = data["humidity"]
        rain_value = data["rain_value"]
        rain_status = data["rain_status"]
        wind_speed = data.get("wind_speed")
        wind_direction = data.get("wind_direction")
        visibility = data.get("visibility")

        # ALERT LOGIC
        alert_message = "Normal"

        if temperature > 40:
            alert_message = "Heat Alert"
        elif wind_speed is not None and wind_speed > 30:
            alert_message = "Storm Warning"
        elif visibility is not None and visibility < 20:
            alert_message = "Low Visibility Warning"
        elif rain_status.lower() != "no rain":
            alert_message = "Rain Alert"

        con = get_db()
        cur = con.cursor()

        cur.execute("""
            INSERT INTO weather
            (temperature, humidity, rain_value, rain_status,
             wind_speed, wind_direction, visibility, alert)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            temperature,
            humidity,
            rain_value,
            rain_status,
            wind_speed,
            wind_direction,
            visibility,
            alert_message
        ))

        con.commit()
        cur.close()
        con.close()

        return jsonify({"status": "stored", "alert": alert_message}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/latest", methods=["GET"])
def latest_data():
    try:
        con = get_db()
        cur = con.cursor()

        cur.execute("""
            SELECT temperature, humidity, rain_status,
                   wind_speed, wind_direction, visibility,
                   alert, created_at
            FROM weather
            ORDER BY id DESC
            LIMIT 1
        """)
        row = cur.fetchone()

        if not row:
            cur.close()
            con.close()
            return jsonify({"message": "No data available yet"})

        # DEVICE STATUS
        created_time = row[7].replace(tzinfo=timezone.utc)
        current_time = datetime.now(timezone.utc)
        seconds_diff = (current_time - created_time).total_seconds()
        device_status = "Offline" if seconds_diff > 30 else "Online"

        # TREND
        cur.execute("""
            SELECT temperature
            FROM weather
            ORDER BY id DESC
            LIMIT 5
        """)
        temps = cur.fetchall()

        trend = "Stable"
        if len(temps) >= 5:
            temps_list = [t[0] for t in temps]
            first_avg = sum(temps_list[3:5]) / 2
            last_avg = sum(temps_list[0:2]) / 2

            if last_avg > first_avg:
                trend = "Rising"
            elif last_avg < first_avg:
                trend = "Falling"

        # MIN MAX AVG
        cur.execute("""
            SELECT temperature
            FROM weather
            ORDER BY id DESC
            LIMIT 24
        """)
        stats = cur.fetchall()
        temps_stats = [t[0] for t in stats]

        min_temp = min(temps_stats) if temps_stats else None
        max_temp = max(temps_stats) if temps_stats else None
        avg_temp = round(sum(temps_stats)/len(temps_stats), 2) if temps_stats else None

        cur.close()
        con.close()

        return jsonify({
            "temperature": row[0],
            "humidity": row[1],
            "rain": row[2],
            "wind_speed": row[3],
            "wind_direction": row[4],
            "visibility": row[5],
            "alert": row[6],
            "trend": trend,
            "min_temp": min_temp,
            "max_temp": max_temp,
            "avg_temp": avg_temp,
            "device_status": device_status,
            "time": row[7]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history", methods=["GET"])
def history():
    try:
        con = get_db()
        cur = con.cursor()

        cur.execute("""
            SELECT temperature, humidity, rain_status,
                   wind_speed, wind_direction, visibility,
                   alert, created_at
            FROM weather
            ORDER BY id DESC
            LIMIT 20
        """)

        rows = cur.fetchall()
        cur.close()
        con.close()

        data = []
        for row in rows:
            data.append({
                "temperature": row[0],
                "humidity": row[1],
                "rain": row[2],
                "wind_speed": row[3],
                "wind_direction": row[4],
                "visibility": row[5],
                "alert": row[6],
                "time": row[7]
            })

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
