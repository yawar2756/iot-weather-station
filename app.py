from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Global data store
data_store = {
    "temperature": "--",
    "humidity": "--",
    "rain": "--"
}

@app.route('/')
def home():
    return render_template('iot_dashboard_auto.html')

@app.route('/api/data', methods=['POST', 'GET'])
def api_data():
    global data_store

    if request.method == 'POST':
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON received"}), 400

        # Force keys (ESP sometimes sends garbage)
        data_store["temperature"] = data.get("temperature", "--")
        data_store["humidity"] = data.get("humidity", "--")
        data_store["rain"] = data.get("rain", "--")

        print("✅ Data received:", data_store)
        return jsonify({"status": "ok"}), 200

    return jsonify(data_store)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
