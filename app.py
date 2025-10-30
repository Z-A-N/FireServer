from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
from db import get_db
import os
import datetime

# Inisialisasi Flask
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Halaman utama
@app.route('/')
def home():
    return "🔥 FireServer aktif! Menunggu data dari 3 sensor api (WeMos D1 Mini)."

# Endpoint untuk menerima data dari WeMos
@app.route('/api/sensor', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()

        # Ambil data dari JSON
        sensor_1 = float(data.get('sensor_1', 0))
        sensor_2 = float(data.get('sensor_2', 0))
        sensor_3 = float(data.get('sensor_3', 0))

        # Logika penentuan status dan alarm
        if sensor_1 < 200 or sensor_2 < 200 or sensor_3 < 200:
            status = "Kebakaran"
            alarm = "ON"
        elif sensor_1 < 500 or sensor_2 < 500 or sensor_3 < 500:
            status = "Bahaya"
            alarm = "ON"
        else:
            status = "Aman"
            alarm = "OFF"

        # Simpan ke database
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO flame_data (sensor_1, sensor_2, sensor_3, status, alarm)
            VALUES (%s, %s, %s, %s, %s)
        """, (sensor_1, sensor_2, sensor_3, status, alarm))
        db.commit()
        cursor.close()
        db.close()

        # Kirim data realtime ke Flutter lewat SocketIO
        payload = {
            "sensor_1": sensor_1,
            "sensor_2": sensor_2,
            "sensor_3": sensor_3,
            "status": status,
            "alarm": alarm,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        socketio.emit('flame_update', payload)

        print(f"🔥 Data diterima | S1={sensor_1}, S2={sensor_2}, S3={sensor_3} | Status={status} | Alarm={alarm}")
        return jsonify({"status": "success", **payload}), 200

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# Event kalau Flutter connect ke server
@socketio.on('connect')
def client_connected():
    print("📡 Flutter client tersambung ke SocketIO")

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
