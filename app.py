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
            created_at TIMESTAMP DEFAULT NOW()        )
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
    return jsonify({"status": "running"})

# ================= ALERT =================
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
    print("📥 Incoming Data:", data)
    con = get_db()
    if not con:
        return jsonify({"error": "DB failed"}), 500

    try:
        temp = data.get("temperature")
        humidity = data.get("humidity")
        
        # ✅ FIX
        if humidity is None or humidity == "null":
            humidity = None
        else:
            humidity = float(humidity)
        rain_value = data.get("rain_value")
        rain_status = data.get("rain_status")
        wind_speed = data.get("wind_speed")
        wind_direction = data.get("wind_direction")
        visibility = data.get("visibility")

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


# ================= LATEST =================
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
    device_status = "Offline" if seconds > 60 else "Online"

    if device_status == "Offline":
        return jsonify({"device_status": "Offline"})

    # stats
    cur.execute("""
    SELECT MIN(temperature), MAX(temperature), AVG(temperature)
    FROM weather
    WHERE created_at >= NOW() - INTERVAL '12 hours'
    """)
    stats = cur.fetchone()

    # trend
    cur.execute("""
    SELECT temperature FROM weather
    ORDER BY id DESC
    LIMIT 6
    """)
    temps = [t[0] for t in cur.fetchall() if t[0] is not None]

    trend = "Stable"
    if len(temps) >= 3:
        diff = temps[0] - temps[-1]
        if diff > 1:
            trend = "Rising"
        elif diff < -1:
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
        "min_temp": float(stats[0]) if stats[0] else None,
        "max_temp": float(stats[1]) if stats[1] else None,
        "avg_temp": round(float(stats[2]), 2) if stats[2] else None,
        "trend": trend,
        "device_status": device_status
    })


# ================= HISTORY (FINAL FIXED) =================
@app.route("/api/history")
def history():
    mode = request.args.get("mode", "hourly")

    con = get_db()
    if not con:
        return jsonify([])

    cur = con.cursor()

    if mode == "daily":
        cur.execute("""
        SELECT 
            t.day,
            ROUND(AVG(w.temperature)::numeric, 2) as temperature
        FROM generate_series(
            date_trunc('day', NOW() - INTERVAL '6 days'),
            date_trunc('day', NOW()),
            INTERVAL '1 day'
        ) as t(day)
        
        LEFT JOIN weather w
        ON DATE(w.created_at) = t.day
        
        GROUP BY t.day
        ORDER BY t.day ASC
        """)
    else:
        cur.execute("""
        SELECT 
            t.hour,
            ROUND(AVG(w.temperature)::numeric, 2) as temperature
        FROM generate_series(
            date_trunc('hour', NOW() - INTERVAL '11 hours'),
            date_trunc('hour', NOW()),
            INTERVAL '1 hour'
        ) as t(hour)
        
        LEFT JOIN weather w
        ON date_trunc('hour', w.created_at) = t.hour
        
        GROUP BY t.hour
        ORDER BY t.hour ASC
        """)

    rows = cur.fetchall()

    cur.close()
    con.close()

    return jsonify([
        {"time": str(r[0]), "temperature": r[1] if r[1] else None}
        for r in rows
    ])


# ================= EXPORT =================
@app.route("/api/export")
def export():
    con = get_db()
    if not con:
        return "Database Error"

    cur = con.cursor()

    # ✅ FIX: last 7 days instead of LIMIT
    cur.execute("""
    SELECT created_at, temperature, humidity,
           rain_status, wind_speed,
           wind_direction, visibility
    FROM weather
    WHERE created_at >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '7 days'
    ORDER BY created_at ASC
    """)

    rows = cur.fetchall()

    cur.close()
    con.close()

    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)

    # ✅ clean headers
    writer.writerow([
        "Date", "Time", "Temperature (°C)", "Humidity (%)",
        "Rain", "Wind Speed (km/h)", "Direction", "Visibility (%)"
    ])

    for r in rows:
        ts = r[0]

        writer.writerow([
            ts.strftime("%d-%m-%Y") if ts else "",
            ts.strftime("%I:%M %p") if ts else "",
            r[1] if r[1] is not None else "",
            r[2] if r[2] is not None else "",
            r[3] or "",
            r[4] if r[4] is not None else "",
            r[5] or "",
            r[6] if r[6] not in (None, -1) else ""
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=weather_last_7_days.csv"
        }
    )

if __name__ == "__main__":
    app.run()
