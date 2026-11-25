from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import psycopg2
import os
import csv
import io
import math
import random
import time
import hmac

app = Flask(__name__)

# Only the read-only GET endpoints are open to other origins.
# The dashboard is same-origin and the ESP8266 is not a browser, so POST needs no CORS.
CORS(app, resources={r"/api/(latest|history|export)": {"origins": "*", "methods": ["GET"]}})

print("🔥 SERVER STARTED")

# ================= CONFIG =================
DATABASE_URL = os.environ.get("DATABASE_URL")
SERVER_API_KEY = os.environ.get("API_KEY")
if not SERVER_API_KEY:
    print("❌ FATAL: API_KEY environment variable not set")
    raise RuntimeError("API_KEY not configured")

if not DATABASE_URL:
    print("⚠️  WARNING: DATABASE_URL is not set. The database will be unavailable.")

# Demo seeding is OFF unless explicitly enabled (set ENABLE_SEED=1 on the server).
ENABLE_SEED = os.environ.get("ENABLE_SEED", "").lower() in ("1", "true", "yes")
# Rows older than this are pruned automatically. 0 disables pruning.
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "90"))
# The LDR is a day/night switch, not a visibility sensor, so this alert is opt-in.
VISIBILITY_ALERT_ENABLED = os.environ.get("VISIBILITY_ALERT_ENABLED", "").lower() in ("1", "true", "yes")
OFFLINE_AFTER_SECONDS = 35

DEMO_DEVICE = "DEMO-SIM"
DEFAULT_DEVICE = "GPCA-STATION-01"
UTC_NOW = "(NOW() AT TIME ZONE 'UTC')"


@app.context_processor
def inject_globals():
    return {"current_year": datetime.now().year}


# ================= DB =================
@contextmanager
def db_cursor(commit=False):
    """Open a connection, always close it, roll back on error."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")
    con = psycopg2.connect(DATABASE_URL, sslmode="require", connect_timeout=5)
    try:
        with con.cursor() as cur:
            yield cur
        if commit:
            con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db():
    with db_cursor(commit=True) as cur:
        cur.execute(f"""
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
            device TEXT DEFAULT '{DEFAULT_DEVICE}',
            created_at TIMESTAMP DEFAULT {UTC_NOW}
        )
        """)
        cur.execute(f"ALTER TABLE weather ADD COLUMN IF NOT EXISTS device TEXT DEFAULT '{DEFAULT_DEVICE}'")
        # created_at is always stored as naive UTC, regardless of the DB session time zone
        cur.execute(f"ALTER TABLE weather ALTER COLUMN created_at SET DEFAULT {UTC_NOW}")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_weather_created_at ON weather (created_at)")

        # One-time cleanup of the old "-1 means missing" convention. Missing is NULL now.
        cur.execute("UPDATE weather SET wind_speed = NULL WHERE wind_speed < 0")
        cur.execute("UPDATE weather SET rain_value = NULL WHERE rain_value < 0")
        cur.execute("UPDATE weather SET visibility = NULL WHERE visibility < 0 OR visibility > 100")
        # Old firmware sent temp = -1 AND humidity = -1 (stored as NULL) on a DHT failure.
        # A real -1 °C reading always has a humidity value, so this pair is unambiguous.
        cur.execute("UPDATE weather SET temperature = NULL WHERE temperature = -1 AND humidity IS NULL")
    print("✅ DB READY")


if DATABASE_URL:
    try:
        init_db()
    except Exception as e:
        print("DB INIT SKIPPED:", e)


_last_prune = 0.0


def maybe_prune(cur):
    """Delete rows past the retention window, at most once per hour."""
    global _last_prune
    if RETENTION_DAYS <= 0 or time.time() - _last_prune < 3600:
        return
    _last_prune = time.time()
    cur.execute(
        f"DELETE FROM weather WHERE created_at < {UTC_NOW} - make_interval(days => %s)",
        (RETENTION_DAYS,),
    )


def key_ok(candidate):
    return bool(candidate) and hmac.compare_digest(str(candidate), SERVER_API_KEY)


def to_number(value, lo, hi):
    """Return a float inside [lo, hi], otherwise None (missing/invalid)."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or not (lo <= f <= hi):
        return None
    return f


def clean_text(value, max_len):
    if not isinstance(value, str):
        return None
    value = value.strip()[:max_len]
    return value or None


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
RAIN_WORDS = {"rain detected", "light rain", "heavy rain", "drizzle", "storm"}


def generate_alert(temp, wind, visibility, rain):
    alerts = []

    if temp is not None:
        if temp >= 40:
            alerts.append("Heat Alert")
        elif temp <= 5:
            alerts.append("Cold Alert")

    if wind is not None and wind >= 30:
        alerts.append("Storm Warning")

    if VISIBILITY_ALERT_ENABLED and visibility is not None and visibility < 50:
        alerts.append("Low Visibility")

    if str(rain).lower().strip() in RAIN_WORDS:
        alerts.append("Rain Alert")

    for p in ("Storm Warning", "Heat Alert", "Cold Alert", "Low Visibility", "Rain Alert"):
        if p in alerts:
            return p
    return "Normal"


# ================= API: INGEST =================
@app.route("/api/data", methods=["POST"])
def receive_data():
    if not key_ok(request.headers.get("x-api-key")):
        return jsonify({"error": "Unauthorized: Invalid or missing API key"}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400

    temp = to_number(data.get("temperature"), -40, 80)
    humidity = to_number(data.get("humidity"), 0, 100)
    rain_value = to_number(data.get("rain_value"), 0, 10000)
    wind_speed = to_number(data.get("wind_speed"), 0, 250)
    visibility = to_number(data.get("visibility"), 0, 100)
    rain_status = clean_text(data.get("rain_status"), 32)
    wind_direction = clean_text(data.get("wind_direction"), 16)
    device_id = clean_text(data.get("device"), 64) or DEFAULT_DEVICE

    alert = generate_alert(temp, wind_speed, visibility, rain_status)

    try:
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO weather
                (temperature, humidity, rain_value, rain_status,
                 wind_speed, wind_direction, visibility, alert, device)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (temp, humidity, rain_value, rain_status,
                  wind_speed, wind_direction, visibility, alert, device_id))
            maybe_prune(cur)
    except Exception as e:
        print("INSERT ERROR:", e)
        return jsonify({"error": "DB failed"}), 503

    return jsonify({"status": "ok", "alert": alert})


# ================= API: LATEST =================
@app.route("/api/latest")
def latest():
    try:
        with db_cursor() as cur:
            cur.execute(f"""
                SELECT temperature, humidity, rain_status, wind_speed, wind_direction,
                       visibility, alert, device,
                       EXTRACT(EPOCH FROM ({UTC_NOW} - created_at)) AS age_seconds
                FROM weather
                ORDER BY id DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            if not row:
                return jsonify({"device_status": "Offline", "message": "No data yet"})

            # Stable visibility: if 2 of the last 3 readings are "missing", report missing
            cur.execute("SELECT visibility FROM weather ORDER BY id DESC LIMIT 3")
            recent_vis = [r[0] for r in cur.fetchall()]
            missing = sum(1 for v in recent_vis if v is None)
            visibility = None if missing >= 2 else row[5]

            cur.execute(f"""
                SELECT MIN(temperature), MAX(temperature), AVG(temperature)
                FROM weather
                WHERE created_at >= {UTC_NOW} - INTERVAL '12 hours'
                  AND temperature IS NOT NULL
            """)
            lo, hi, avg = cur.fetchone()

            cur.execute("""
                SELECT temperature FROM weather
                WHERE temperature IS NOT NULL
                ORDER BY id DESC LIMIT 6
            """)
            temps = [t[0] for t in cur.fetchall()]
    except Exception as e:
        print("LATEST ERROR:", e)
        return jsonify({"error": "DB failed", "device_status": "Offline"}), 503

    trend = "Stable"
    if len(temps) >= 3:
        diff = temps[0] - temps[-1]
        if diff > 1:
            trend = "Rising"
        elif diff < -1:
            trend = "Falling"

    age = max(0, int(row[8] or 0))
    online = age <= OFFLINE_AFTER_SECONDS

    if visibility is None:
        visibility_status = "Not Connected"
    else:
        visibility_status = "Low" if visibility < 50 else "Good"

    # When offline we still return the last known reading, flagged as stale by device_status.
    return jsonify({
        "device_status": "Online" if online else "Offline",
        "last_seen_seconds": age,
        "temperature": row[0],
        "humidity": row[1],
        "rain": row[2],
        "wind_speed": row[3],
        "wind_direction": row[4],
        "visibility": visibility,
        "visibility_status": visibility_status,
        "alert": row[6] if online else "Offline",
        "min_temp": float(lo) if lo is not None else None,
        "max_temp": float(hi) if hi is not None else None,
        "avg_temp": round(float(avg), 2) if avg is not None else None,
        "trend": trend,
        "device": row[7] or DEFAULT_DEVICE,
    })


# ================= API: HISTORY =================
@app.route("/api/history")
def history():
    mode = request.args.get("mode", "hourly")

    if mode == "daily":
        sql = """
        SELECT d.day,
               ROUND(AVG(w.temperature)::numeric, 2) AS temperature,
               to_char(d.day, 'DD Mon') AS label
        FROM generate_series(
            date_trunc('day', NOW() AT TIME ZONE 'Asia/Kolkata') - INTERVAL '6 days',
            date_trunc('day', NOW() AT TIME ZONE 'Asia/Kolkata'),
            INTERVAL '1 day'
        ) AS d(day)
        LEFT JOIN weather w
          ON date_trunc('day', w.created_at + INTERVAL '5 hours 30 minutes') = d.day
         AND w.temperature IS NOT NULL
        GROUP BY d.day
        ORDER BY d.day ASC
        """
    else:
        sql = """
        SELECT t.hour,
               ROUND(AVG(w.temperature)::numeric, 2) AS temperature,
               to_char(t.hour, 'HH24:MI') AS label
        FROM generate_series(
            date_trunc('hour', NOW() AT TIME ZONE 'Asia/Kolkata') - INTERVAL '11 hours',
            date_trunc('hour', NOW() AT TIME ZONE 'Asia/Kolkata'),
            INTERVAL '1 hour'
        ) AS t(hour)
        LEFT JOIN weather w
          ON date_trunc('hour', w.created_at + INTERVAL '5 hours 30 minutes') = t.hour
         AND w.temperature IS NOT NULL
        GROUP BY t.hour
        ORDER BY t.hour ASC
        """

    try:
        with db_cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    except Exception as e:
        print("HISTORY ERROR:", e)
        return jsonify({"error": "DB failed"}), 503

    return jsonify([
        {
            "time": r[0].isoformat() if r[0] else None,
            "temperature": float(r[1]) if r[1] is not None else None,
            "label": str(r[2]) if r[2] else None,
        }
        for r in rows
    ])


# ================= API: EXPORT =================
CSV_HEADER = ["Date", "Time (IST)", "Temperature (°C)", "Humidity (%)", "Rain",
              "Wind Speed (km/h)", "Direction", "Light Level (%)", "Device"]


def csv_safe(value):
    """Stop spreadsheet apps from treating device-supplied text as a formula."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


@app.route("/api/export")
def export():
    rows = []
    try:
        with db_cursor() as cur:
            cur.execute(f"""
                SELECT
                    date_trunc('hour', created_at + INTERVAL '5 hours 30 minutes') AS hour,
                    ROUND(AVG(temperature)::numeric, 2),
                    ROUND(AVG(humidity)::numeric, 2),
                    COALESCE(
                        MAX(CASE WHEN rain_status IS NOT NULL
                                  AND lower(rain_status) <> 'no rain' THEN rain_status END),
                        MAX(rain_status)),
                    ROUND(AVG(wind_speed)::numeric, 2),
                    MAX(wind_direction),
                    ROUND(AVG(visibility)::numeric, 2),
                    string_agg(DISTINCT device, '/')
                FROM weather
                WHERE created_at >= {UTC_NOW} - INTERVAL '7 days'
                GROUP BY hour
                ORDER BY hour ASC
            """)
            rows = cur.fetchall()
    except Exception as e:
        print("EXPORT ERROR:", e)
        return jsonify({"error": "DB failed"}), 503

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADER)
    for r in rows:
        ts = r[0]
        writer.writerow([
            ts.strftime("%d-%m-%Y") if ts else "",
            ts.strftime("%I:%M %p") if ts else "",
            "" if r[1] is None else r[1],
            "" if r[2] is None else r[2],
            csv_safe(r[3] or ""),
            "" if r[4] is None else r[4],
            csv_safe(r[5] or ""),
            "" if r[6] is None else r[6],
            csv_safe(r[7] or ""),
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=weather_last_7_days.csv",
            "Cache-Control": "no-store",
        },
    )


# ================= DEMO DATA SEEDING (disabled unless ENABLE_SEED=1) =================
#   POST   /api/seed?days=7   header x-api-key  -> backfill demo rows (device = DEMO-SIM)
#   POST   /api/seed?live=1   header x-api-key  -> one fresh demo reading at "now"
#   DELETE /api/seed          header x-api-key  -> remove every demo row
WIND_DIRECTIONS = ["North", "North-East", "East", "South-East",
                   "South", "South-West", "West", "North-West"]


def demo_reading(ts):
    """One plausible reading for a naive-UTC timestamp."""
    ist_hour = (ts.hour + 5.5) % 24
    day_wave = math.sin((ist_hour - 9.0) / 24.0 * 2 * math.pi)

    temperature = round(11.0 + 6.5 * day_wave + random.uniform(-1.0, 1.0), 1)
    humidity = round(min(96.0, max(32.0, 70.0 - 20.0 * day_wave + random.uniform(-4, 4))), 1)

    if random.random() < 0.08:
        rain_status = random.choice(["Light Rain", "Drizzle", "Rain Detected"])
        rain_value = 150.0
    else:
        rain_status = "No Rain"
        rain_value = 0.0

    wind_speed = round(4.0 + 14.0 * random.random(), 1)
    wind_direction = random.choice(WIND_DIRECTIONS)
    visibility = None if random.random() < 0.05 else round(random.uniform(45, 100), 1)

    alert = generate_alert(temperature, wind_speed, visibility, rain_status)
    return (temperature, humidity, rain_value, rain_status,
            wind_speed, wind_direction, visibility, alert, DEMO_DEVICE, ts)


@app.route("/api/seed", methods=["POST", "DELETE"])
def seed():
    if not ENABLE_SEED:
        return jsonify({"error": "Not found"}), 404
    # Header only: keys in query strings end up in server logs and browser history.
    if not key_ok(request.headers.get("x-api-key")):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        with db_cursor(commit=True) as cur:
            if request.method == "DELETE":
                cur.execute("DELETE FROM weather WHERE device = %s", (DEMO_DEVICE,))
                return jsonify({"deleted": cur.rowcount, "demo_device": DEMO_DEVICE})

            now = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
            live_only = "live" in request.args
            try:
                days = int(request.args.get("days", 7))
            except (TypeError, ValueError):
                days = 7
            days = 0 if live_only else max(0, min(days, 7))

            deleted = 0
            readings = []
            if days > 0:
                start = (now - timedelta(days=days)).replace(minute=0, second=0)
                cur.execute("DELETE FROM weather WHERE device = %s AND created_at >= %s",
                            (DEMO_DEVICE, start))
                deleted = cur.rowcount
                step = timedelta(minutes=30) if days <= 1 else timedelta(hours=1)
                ts = start
                while ts < now:
                    readings.append(demo_reading(ts))
                    ts += step
            readings.append(demo_reading(now))

            cur.executemany("""
                INSERT INTO weather
                (temperature, humidity, rain_value, rain_status,
                 wind_speed, wind_direction, visibility, alert, device, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, readings)
    except Exception as e:
        print("SEED ERROR:", e)
        return jsonify({"error": "DB failed"}), 503

    return jsonify({
        "status": "ok",
        "inserted": len(readings),
        "deleted": deleted,
        "demo_device": DEMO_DEVICE,
        "mode": "live" if days == 0 else f"{days}d backfill",
    })


if __name__ == "__main__":
    app.run()
