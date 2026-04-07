import os
import psycopg2
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")


# ================= DATABASE =================

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


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

        con.commit()
        cur.close()
        con.close()
        print("✅ DB READY")

    except Exception as e:
        print("❌ DB INIT ERROR:", e)


init_db()


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


@app.route("/health")
def health():
    return jsonify({"status": "running"})


# ================= RECEIVE DATA =================

@app.route("/api/data", methods=["POST"])
def receive_data():
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        temperature = data.get("temperature")
        humidity = data.get("humidity")
        rain_value = data.get("rain_value")
        rain_status = data.get("rain_status", "No Rain")
        wind_speed = data.get("wind_speed", 0)
        wind_direction = data.get("wind_direction", "N/A")
        visibility = data.get("visibility", 0)

        alerts = []

        if wind_speed > 30:
            alerts.append("Storm Warning")

        if temperature and temperature > 40:
            alerts.append("Heat Alert")

        if visibility and visibility < 20:
            alerts.append("Low Visibility")

        if rain_status and rain_status.lower() in ["light rain", "heavy rain"]:
            alerts.append("Rain Alert")
        alert = ", ".join(alerts) if alerts else "Normal"

        try:
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

        except Exception as db_error:
            print("❌ DB ERROR:", db_error)
            return jsonify({"error": "Database Failed"}), 500

        return jsonify({"status": "stored", "alert": alert})

    except Exception as e:
        print("❌ API ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ================= LATEST =================
@app.route("/api/latest")
def latest():
    try:
        con = get_db()
        cur = con.cursor()

        # ===== GET LATEST DATA =====
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

        device_status = "Offline" if seconds > 20 else "Online"

        if device_status == "Offline":
            return jsonify({"device_status": "Offline"})

        # ===== STATS (FIXED → LAST 12 HOURS) =====
        cur.execute("""
            SELECT 
                MIN(temperature),
                MAX(temperature),
                AVG(temperature)
            FROM weather
            WHERE created_at >= NOW() - INTERVAL '12 hours'
        """)

        stats = cur.fetchone()

        min_temp = float(stats[0]) if stats[0] else None
        max_temp = float(stats[1]) if stats[1] else None
        avg_temp = round(float(stats[2]), 2) if stats[2] else None

        # ===== TREND =====
        cur.execute("""
            SELECT temperature
            FROM weather
            ORDER BY id DESC
            LIMIT 5
        """)

        temps = [t[0] for t in cur.fetchall() if t[0] is not None]

        trend = "Stable"

        if len(temps) >= 2:
            if temps[0] > temps[-1]:
                trend = "Rising"
            elif temps[0] < temps[-1]:
                trend = "Falling"

        cur.close()
        con.close()

        # ===== RESPONSE =====
        return jsonify({
            "temperature": row[0],
            "humidity": row[1],
            "rain": row[2],
            "wind_speed": row[3],
            "wind_direction": row[4],
            "visibility": row[5],
            "alert": row[6],
            "min_temp": min_temp,
            "max_temp": max_temp,
            "avg_temp": avg_temp,
            "trend": trend,
            "device_status": device_status
        })

    except Exception as e:
        print("❌ LATEST ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ================= HISTORY =================

@app.route("/api/history")
def history():
    try:
        mode = request.args.get("mode", "hourly")

        con = get_db()
        cur = con.cursor()

        if mode == "daily":
            cur.execute("""
                WITH days AS (
                    SELECT generate_series(
                        CURRENT_DATE - INTERVAL '6 days',
                        CURRENT_DATE,
                        INTERVAL '1 day'
                    ) AS day
                )
                SELECT 
                    d.day,
                    COALESCE(ROUND(AVG(w.temperature)::numeric, 2), 0)
                FROM days d
                LEFT JOIN weather w
                    ON DATE(w.created_at) = d.day
                GROUP BY d.day
                ORDER BY d.day ASC
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
                SELECT 
                    h.hour,
                    COALESCE(ROUND(AVG(w.temperature)::numeric, 2), 0)
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
            {"time": str(r[0]), "temperature": float(r[1])}
            for r in rows
        ])

    except Exception as e:
        print("HISTORY ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ================= EXPORT =================

@app.route("/api/export")
def export_csv():
    try:
        con = get_db()
        cur = con.cursor()

        cur.execute("""
            SELECT created_at, temperature, humidity,
                   rain_status, wind_speed,
                   wind_direction, visibility
            FROM weather
            WHERE created_at >= NOW() - INTERVAL '7 days'
            ORDER BY created_at ASC
        """)

        rows = cur.fetchall()
        cur.close()
        con.close()

        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Date", "Time", "Temperature (°C)", "Humidity (%)",
            "Rain Status", "Wind Speed (km/h)", "Wind Direction", "Visibility (%)"
        ])

        for row in rows:
            timestamp = row[0]
            writer.writerow([
                timestamp.strftime("%d-%m-%Y"),
                timestamp.strftime("%I:%M %p"),
                f"{row[1]} °C",
                f"{row[2]} %",
                row[3],
                f"{row[4]} km/h" if row[4] else "",
                row[5] if row[5] else "",
                f"{row[6]} %" if row[6] else ""
            ])

        from flask import Response

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=weather_data_last_7_days.csv"}
        )

    except Exception as e:
        print("EXPORT ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ================= RUN =================

if __name__ == "__main__":
    app.run(debug=True)
