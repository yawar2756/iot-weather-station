import os
import psycopg2
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from datetime import datetime
import csv
import io

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
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

    con.commit()
    cur.close()
    con.close()

init_db()


@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/health")
def health():
    return jsonify({"status": "running"})


@app.route("/api/data", methods=["POST"])
def receive_data():
    data = request.get_json(force=True)

    temperature = data["temperature"]
    humidity = data["humidity"]
    rain_value = data["rain_value"]
    rain_status = data["rain_status"]
    wind_speed = data.get("wind_speed")
    wind_direction = data.get("wind_direction")
    visibility = data.get("visibility")

    alert = "Normal"
    if temperature > 40:
        alert = "Heat Alert"

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO weather
        (temperature, humidity, rain_value, rain_status,
         wind_speed, wind_direction, visibility, alert)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        temperature, humidity, rain_value, rain_status,
        wind_speed, wind_direction, visibility, alert
    ))

    con.commit()
    cur.close()
    con.close()

    return jsonify({"status": "stored"})


@app.route("/api/latest")
def latest():
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
        return jsonify({"message": "No data available yet"})

    created_time = row[7]
    now = datetime.utcnow()

    seconds = (now - created_time).total_seconds()
    status = "Offline" if seconds > 30 else "Online"

    if status == "Offline":
        cur.close()
        con.close()
        return jsonify({
            "temperature": None,
            "humidity": None,
            "rain": None,
            "wind_speed": None,
            "wind_direction": None,
            "visibility": None,
            "alert": None,
            "trend": None,
            "min_temp": None,
            "max_temp": None,
            "avg_temp": None,
            "device_status": "Offline"
        })

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
        "trend": "Stable",
        "min_temp": row[0],
        "max_temp": row[0],
        "avg_temp": row[0],
        "device_status": status
    })


@app.route("/api/history")
def history():
    mode = request.args.get("mode", "hourly")

    con = get_db()
    cur = con.cursor()

    if mode == "daily":
        cur.execute("""
            SELECT DATE(created_at),
                   ROUND(AVG(temperature)::numeric, 2)
            FROM weather
            WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(created_at)
            ORDER BY DATE(created_at) ASC
        """)
    else:
        cur.execute("""
            WITH hours AS (
                SELECT generate_series(
                    date_trunc('hour', NOW()) - INTERVAL '11 hours',
                    date_trunc('hour', NOW()),
                    INTERVAL '1 hour'
                ) AS hour
            )
            SELECT h.hour,
                   ROUND(AVG(w.temperature)::numeric, 2)
            FROM hours h
            LEFT JOIN weather w
              ON date_trunc('hour', w.created_at) = h.hour
            GROUP BY h.hour
            ORDER BY h.hour ASC
        """)

    rows = cur.fetchall()
    cur.close()
    con.close()

    return jsonify([
        {"time": str(r[0]), "temperature": float(r[1]) if r[1] else 0}
        for r in rows
    ])
