from flask import Flask, request, jsonify, render_template, Response
import psycopg2
import os
from datetime import datetime
import csv
import io

app = Flask(__name__)

print("🔥 SERVER STARTED")

DATABASE_URL = os.environ.get("DATABASE_URL")

# ================= DB =================
def get_db():
    try:
        return psycopg2.connect(DATABASE_URL, sslmode="require")
    except Exception as e:
        print("DB ERROR:", e)
        return None

def init_db():
    con = get_db()
    if con:
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS weather (
            id SERIAL PRIMARY KEY,
            temperature FLOAT,
            humidity FLOAT,
            rain_value FLOAT,
            rain_status TEXT,
            wind_speed FLOAT,
            wind_direction TEXT,
            visibility FLOAT,
            alert TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        con.commit()
        cur.close()
        con.close()
        print("✅ DB READY")

if DATABASE_URL:
    try:
        init_db()
    except Exception as e:
        print("DB INIT SKIPPED:", e)
else:
    print("NO DATABASE URL")

# ================= PAGES =================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/ping")
def ping():
    return "ok"

@app.route("/health")
def health():
    return "ok"

# ================= ALERT SYSTEM =================
def generate_alert(temp, wind, visibility, rain):
    alerts = []

    if temp is not None and temp > 40:
        alerts.append("Heat Alert")

    if wind is not None and wind > 30:
        alerts.append("Storm Warning")

    if visibility is not None and visibility != -1 and visibility < 20:
        alerts.append("Low Visibility")

    if rain and str(rain).lower() in ["light rain", "heavy rain"]:
        alerts.append("Rain Alert")

    return ", ".join(alerts) if alerts else "Normal"

# ================= API =================
@app.route("/api/data", methods=["POST"])
def receive_data():
    data = request.json

    con = get_db()
    if not con:
        return jsonify({"error": "DB failed"}), 500

    try:
        temp = data.get("temperature")
        humidity = data.get("humidity")
        rain_value = data.get("rain_value")
        rain_status = data.get("rain_status")
        wind_speed = data.get("wind_speed")
        wind_direction = data.get("wind_direction")
        visibility = data.get("visibility")

        # handle not connected
        if visibility == "Not Connected":
            visibility = -1

        alert = generate_alert(temp, wind_speed, visibility, rain_status)

        cur = con.cursor()

        cur.execute("""
        INSERT INTO weather
        (temperature, humidity, rain_value, rain_status,
         wind_speed, wind_direction, visibility, alert)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            temp, humidity, rain_value, rain_status,
            wind_speed, wind_direction, visibility, alert
        ))

        con.commit()
        cur.close()
        con.close()

        return jsonify({"status": "ok", "alert": alert})

    except Exception as e:
        print("INSERT ERROR:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/latest")
def latest():
    con = get_db()
    if not con:
        return jsonify({"error": "DB failed"}), 500

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
        return jsonify({"message": "No data yet"})

    created_time = row[7]
    now = datetime.utcnow()

    seconds = (now - created_time).total_seconds()
    device_status = "Offline" if seconds > 40 else "Online"

    if device_status == "Offline":
        return jsonify({"device_status": "Offline"})

    # ================= STATS =================
    cur.execute("""
    SELECT MIN(temperature), MAX(temperature), AVG(temperature)
    FROM weather
    WHERE created_at >= NOW() - INTERVAL '12 hours'
    """)

    stats = cur.fetchone()

    min_temp = float(stats[0]) if stats[0] else None
    max_temp = float(stats[1]) if stats[1] else None
    avg_temp = round(float(stats[2]), 2) if stats[2] else None

    # ================= TREND =================
    cur.execute("""
    SELECT temperature FROM weather
    ORDER BY id DESC
    LIMIT 6
    """)

    temps = [t[0] for t in cur.fetchall() if t[0] is not None]

    trend = "Stable"

    if len(temps) >= 3:
        changes = [(temps[i] - temps[i+1]) for i in range(len(temps)-1)]
        avg_change = sum(changes) / len(changes)

        if avg_change > 0.5:
            trend = "Rising"
        elif avg_change < -0.5:
            trend = "Falling"

    cur.close()
    con.close()

    return jsonify({
        "temperature": row[0],
        "humidity": row[1],
        "rain": row[2],
        "wind_speed": row[3],
        "wind_direction": row[4],
        "visibility": row[5],
        "visibility_status": "Not Connected" if row[5] == -1 else "OK",
        "alert": row[6],
        "min_temp": min_temp,
        "max_temp": max_temp,
        "avg_temp": avg_temp,
        "trend": trend,
        "device_status": device_status
    })


@app.route("/api/history")
def history():
    con = get_db()
    if not con:
        return jsonify([])

    cur = con.cursor()

    cur.execute("""
    SELECT created_at, temperature
    FROM weather
    ORDER BY id DESC
    LIMIT 12
    """)

    rows = cur.fetchall()

    cur.close()
    con.close()

    return jsonify([
        {"time": str(r[0]), "temperature": r[1]} for r in rows[::-1]
    ])


# ================= EXPORT =================
@app.route("/api/export")
def export():
    con = get_db()
    if not con:
        return "Error"

    cur = con.cursor()

    cur.execute("""
    SELECT created_at, temperature, humidity,
           rain_status, wind_speed,
           wind_direction, visibility
    FROM weather
    ORDER BY created_at DESC
    LIMIT 100
    """)

    rows = cur.fetchall()

    cur.close()
    con.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Date", "Time", "Temp", "Humidity",
        "Rain", "Wind", "Direction", "Visibility"
    ])

    for r in rows:
        ts = r[0]
        writer.writerow([
            ts.strftime("%d-%m-%Y"),
            ts.strftime("%I:%M %p"),
            r[1], r[2], r[3], r[4], r[5], r[6]
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=weather.csv"}
    )


if __name__ == "__main__":
    app.run()
