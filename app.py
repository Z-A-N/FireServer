from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from db import get_db
import os
import datetime

# Inisialisasi Flask & SocketIO
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# 🏠 Route Utama
@app.route('/')
def home():
    return "🔥 FireServer aktif! Menunggu data dari 3 sensor api (WeMos D1 Mini)."

# 🔥 Endpoint untuk menerima data sensor
@app.route('/api/sensor', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()

        # Ambil nilai sensor (digital 0/1)
        sensor_1 = int(data.get('sensor_1', 1))
        sensor_2 = int(data.get('sensor_2', 1))
        sensor_3 = int(data.get('sensor_3', 1))

        # Logika status & alarm
        if sensor_1 == 0 or sensor_2 == 0 or sensor_3 == 0:
            status = "Kebakaran" if all(s == 0 for s in [sensor_1, sensor_2, sensor_3]) else "Bahaya"
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

        # Kirim data realtime ke Flutter
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

# 📡 Event saat Flutter connect
@socketio.on('connect')
def client_connected():
    print("📡 Flutter client tersambung ke SocketIO")

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
