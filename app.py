@app.route("/api/data", methods=["POST", "GET"])
def api_data():
    if request.method == "POST":
        data = request.get_json(force=True)
        print("RECEIVED JSON:", data)

        try:
            temperature = float(data.get("temperature"))
            humidity = float(data.get("humidity"))
            rain_value = int(data.get("rain_value"))
            rain_status = str(data.get("rain_status"))
        except Exception as e:
            print("DATA ERROR:", e)
            return jsonify({"error": "Bad data format"}), 400

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
        return jsonify({"temperature": None, "humidity": None, "rain": None, "time": None})

    return jsonify({
        "temperature": row[0],
        "humidity": row[1],
        "rain": row[2],
        "time": row[3]
    })
