import os
import psycopg2
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

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

        con = get_db()
        cur = con.cursor()

        # Create table if not exists (safe location)
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            INSERT INTO weather 
            (temperature, humidity, rain_value, rain_status, wind_speed, wind_direction, visibility)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            data["temperature"],
            data["humidity"],
            data["rain_value"],
            data["rain_status"],
            data.get("wind_speed"),
            data.get("wind_direction"),
            data.get("visibility")
        ))

        con.commit()
        cur.close()
        con.close()

        return jsonify({"status": "stored"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/latest", methods=["GET"])
def latest_data():
    try:
        con = get_db()
        cur = con.cursor()

        cur.execute("""
            SELECT temperature, humidity, rain_status,
                   wind_speed, wind_direction, visibility, created_at
            FROM weather
            ORDER BY id DESC
            LIMIT 1
        """)

        row = cur.fetchone()
        cur.close()
        con.close()

        if not row:
            return jsonify({"message": "No data available yet"})

        return jsonify({
            "temperature": row[0],
            "humidity": row[1],
            "rain": row[2],
            "wind_speed": row[3],
            "wind_direction": row[4],
            "visibility": row[5],
            "time": row[6]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
