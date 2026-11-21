from flask import Flask, request, jsonify, render_template, Response
import psycopg2
import os
from datetime import datetime
import csv
import io
import json
import time

app = Flask(__name__)

print("🔥 SERVER STARTED")

DATABASE_URL = os.environ.get("DATABASE_URL")
SERVER_API_KEY = os.environ.get("API_KEY", "gpcaweatherstation25")

if not DATABASE_URL:
    print("⚠️  WARNING: DATABASE_URL is not set. The database will be unavailable.")

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
            device TEXT DEFAULT 'GPCA-STATION-01',
            created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # Add device column if it doesn't exist (migration)
        cur.execute("""
        ALTER TABLE weather ADD COLUMN IF NOT EXISTS device TEXT DEFAULT 'GPCA-STATION-01'
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

    # TEMP
    try:
        if temp is not None and temp >= 40:
            alerts.append("Heat Alert")

        elif temp is not None and temp <= 5:
            alerts.append("Cold Alert")
    except:
        pass

    # WIND
    try:
        if wind not in [None, -1]:
            if float(wind) >= 30:
                alerts.append("Storm Warning")
    except:
        pass

    # VISIBILITY
    try:
        if visibility not in [None, -1, 101]:
            if float(visibility) < 50:
                alerts.append("Low Visibility")
    except:
        pass

    # RAIN
    try:
        rain_text = str(rain).lower().strip()

        if rain_text in [
            "rain detected",
            "light rain",
            "heavy rain",
            "drizzle",
            "storm"
        ]:
            alerts.append("Rain Alert")

    except:
        pass

    if not alerts:
        return "Normal"

    priority = [
        "Storm Warning",
        "Heat Alert",
        "Cold Alert",
        "Low Visibility",
        "Rain Alert"
    ]

    for p in priority:
        if p in alerts:
            return p

    return alerts[0]
# ================= API =================
@app.route("/api/data", methods=["POST"])
def receive_data():
    # Enforce API Key security
    client_key = request.headers.get("x-api-key")
    if not client_key or client_key != SERVER_API_KEY:
        return jsonify({"error": "Unauthorized: Invalid or missing API key"}), 401

    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    print("📥 Incoming Data:", data)
    con = get_db()
    if not con:
        return jsonify({"error": "DB failed"}), 500

    try:
        temp = data.get("temperature")
        try:
            temp = float(temp)
            # Physical range validation for DHT11 (-40°C to 80°C)
            if temp < -40 or temp > 80:
                temp = None
        except:
            temp = None

        humidity = data.get("humidity")
        try:
            humidity = float(humidity)
            # Valid percentage range (0% to 100%)
            if humidity < 0 or humidity > 100:
                humidity = None
        except:
            humidity = None

        print("RAW DATA:", data)
        print("HUMIDITY:", humidity)
        print("TEMP:", temp)
        rain_value = data.get("rain_value")
        try:
            rain_value = float(rain_value)
        except:
            rain_value = -1
        rain_status = data.get("rain_status")
        wind_speed = data.get("wind_speed")

        try:
            wind_speed = float(wind_speed)
        except:
            wind_speed = -1
        wind_direction = data.get("wind_direction")
        visibility = data.get("visibility")
        device_id = data.get("device", "GPCA-STATION-01")
        print("RAIN:", rain_status)
        print("VISIBILITY:", visibility)

        try:
            visibility = float(visibility)
        except:
            visibility = -1

        if visibility in (-1, 101):
            visibility = -1

        alert = generate_alert(temp, wind_speed, visibility, rain_status)

        cur = con.cursor()

        cur.execute("""
        INSERT INTO weather
        (temperature, humidity, rain_value, rain_status,
         wind_speed, wind_direction, visibility, alert, device)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            temp, humidity, rain_value, rain_status,
            wind_speed, wind_direction, visibility, alert, device_id
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
           alert, created_at, device
    FROM weather
    ORDER BY id DESC
    LIMIT 1
    """)

    row = cur.fetchone()

    if not row:
        cur.close()
        con.close()
        return jsonify({"message": "No data yet"})

    # ✅ MAJORITY VOTE — stable visibility (fixes 25/101 flickering)
    cur.execute("""
    SELECT visibility FROM weather
    ORDER BY id DESC
    LIMIT 3
    """)
    vis_rows = cur.fetchall()
    vis_vals = [r[0] for r in vis_rows if r[0] is not None]
    not_connected_count = sum(1 for v in vis_vals if v in (-1, 101))
    stable_visibility = -1 if not_connected_count >= 2 else row[5]
    # ✅ END MAJORITY VOTE

    created_time = row[7]
    now = datetime.utcnow()

    seconds = (now - created_time).total_seconds()
    device_status = "Offline" if seconds > 35 else "Online"

    if device_status == "Offline":
        cur.close()
        con.close()
        # ✅ CORRECTED
        return jsonify({
            "device_status": "Offline",
            "temperature": None,
            "humidity": None,
            "rain": None,
            "wind_speed": None,
            "wind_direction": None,
            "visibility": None,
            "alert": "Offline",
            "device": row[8] if row[8] else "GPCA-STATION-01"
        })
    # stats
    cur.execute("""
    SELECT
    MIN(temperature),
    MAX(temperature),
    AVG(temperature)
    FROM weather
    WHERE created_at >= NOW() - INTERVAL '12 hours'
    AND temperature != -1
    """)
    stats = cur.fetchone()

    # trend
    cur.execute("""
    SELECT temperature FROM weather
    WHERE temperature != -1
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

    device_id = row[8] if row[8] else "GPCA-STATION-01"

    cur.close()
    con.close()

    return jsonify({
        "temperature": row[0],
        "humidity": row[1],
        "rain": row[2],
        "wind_speed": row[3],
        "wind_direction": row[4],
        "visibility": stable_visibility,
        "visibility_status":
            "Not Connected" if stable_visibility in (-1, 101)
            else ("Low" if stable_visibility < 50 else "Good"),
        "alert": row[6],
        "min_temp": float(stats[0]) if stats[0] else None,
        "max_temp": float(stats[1]) if stats[1] else None,
        "avg_temp": round(float(stats[2]), 2) if stats[2] else None,
        "trend": trend,
        "device_status": device_status,
        "device": device_id
    })


# ================= HISTORY (FINAL FIXED) =================
@app.route("/api/history")
def history():

    mode = request.args.get("mode", "hourly")

    con = get_db()

    if not con:
        return jsonify([])

    cur = con.cursor()

    # ================= DAILY =================
    if mode == "daily":

        cur.execute("""
        SELECT
            d.day,
            ROUND(AVG(w.temperature)::numeric, 2) AS temperature,
            to_char(d.day, 'DD Mon') AS label

        FROM generate_series(
            date_trunc(
                'day',
                NOW() AT TIME ZONE 'Asia/Kolkata'
            ) - INTERVAL '6 days',

            date_trunc(
                'day',
                NOW() AT TIME ZONE 'Asia/Kolkata'
            ),

            INTERVAL '1 day'
        ) AS d(day)

        LEFT JOIN weather w
        ON date_trunc(
            'day',
            w.created_at + INTERVAL '5 hours 30 minutes'
        ) = d.day

        AND w.temperature != -1

        GROUP BY d.day
        ORDER BY d.day ASC
        """)

    # ================= HOURLY =================
    else:

        cur.execute("""
        SELECT
            t.hour,
            ROUND(AVG(w.temperature)::numeric, 2) AS temperature,
            to_char(t.hour, 'HH24:MI') AS label

        FROM generate_series(
            date_trunc(
                'hour',
                NOW() AT TIME ZONE 'Asia/Kolkata'
            ) - INTERVAL '11 hours',
        
            date_trunc(
                'hour',
                NOW() AT TIME ZONE 'Asia/Kolkata'
            ),
        
            INTERVAL '1 hour'
        ) AS t(hour)
        
        LEFT JOIN weather w
        ON date_trunc(
            'hour',
            w.created_at + INTERVAL '5 hours 30 minutes'
        ) = t.hour
        
        AND w.temperature != -1
        
        GROUP BY t.hour
        ORDER BY t.hour ASC
        """)
    rows = cur.fetchall()

    cur.close()
    con.close()

    return jsonify([
        {
            "time": r[0].isoformat() if r[0] else None,
            "temperature": float(r[1]) if r[1] is not None else None,
            "label": str(r[2]) if r[2] else None
        }
        for r in rows
    ])

# ================= EXPORT =================
@app.route("/api/export")
def export():
    con = get_db()
    if not con:
        # Return empty CSV with headers when DB unavailable
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Date", "Time", "Temperature (°C)", "Humidity (%)",
            "Rain", "Wind Speed (km/h)", "Direction", "Visibility (%)", "Device"
        ])
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=weather_last_7_days.csv"
            }
        )

    cur = con.cursor()

    # ✅ FIX: last 7 days instead of LIMIT
    cur.execute("""
    SELECT
        date_trunc(
        'hour',
        created_at + INTERVAL '5 hours 30 minutes'
        ) AS hour,

        ROUND(AVG(temperature)::numeric,2) AS temperature,

        ROUND(AVG(humidity)::numeric,2) AS humidity,

        MAX(rain_status) AS rain_status,

        ROUND(AVG(wind_speed)::numeric,2) AS wind_speed,

        MAX(wind_direction) AS wind_direction,

        ROUND(AVG(visibility)::numeric,2) AS visibility,

        MAX(device) AS device

    FROM weather

    WHERE
    created_at >= NOW() - INTERVAL '7 days'

    AND temperature != -1

    GROUP BY hour

    ORDER BY hour ASC
    """)

    rows = cur.fetchall()

    cur.close()
    con.close()

   
    output = io.StringIO()
    writer = csv.writer(output)

    # ✅ clean headers
    writer.writerow([
        "Date", "Time", "Temperature (°C)", "Humidity (%)",
        "Rain", "Wind Speed (km/h)", "Direction", "Visibility (%)", "Device"
    ])

    for r in rows:
        ts = r[0]

        writer.writerow([
            ts.strftime("%d-%m-%Y") if ts else "",
            ts.strftime("%I:%M %p") if ts else "",
            r[1] if r[1] is not None else "",
            r[2] if r[2] is not None else "",
            r[3] or "",
            "" if r[4] in (None, -1) else r[4],
            r[5] or "",
            "" if r[6] in (None, -1, 101) else r[6],
            r[7] or "GPCA-STATION-01",
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=weather_last_7_days.csv"
        }
    )

# Removed SSE /api/stream endpoint — polling is used instead for reliability on cloud hosts


# =============================================
# PRODUCTION DEPLOYMENT: WSGI ENTRY POINT
# =============================================
# Render uses WSGI servers. Create Procfile with:
#   web: gunicorn app:app --workers 1 --bind 0.0.0.0:8000
# and add this to your Render service settings.
# =============================================
if __name__ == "__main__":
    app.run()
