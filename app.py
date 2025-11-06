from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
from db import get_db
import os
import datetime

# Inisialisasi Flask
app = Flask(__name__)
CORS(app)

# Konfigurasi SocketIO agar stabil di Railway
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',          # Penting agar support WebSocket penuh
    ping_interval=25,               # Kirim ping tiap 25 detik
    ping_timeout=120,               # Timeout 2 menit
    logger=True,                    # Tampilkan log koneksi
    engineio_logger=True
)

# Halaman utama (cek server)
@app.route('/')
def home():
    return "🔥 FireServer aktif! Menunggu data dari 3 sensor api (WeMos D1 Mini)."

# Endpoint untuk tes koneksi Flutter/HTTP
@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({
        "status": "alive",
        "time": datetime.datetime.now().isoformat()
    })

# Endpoint untuk menerima data dari WeMos
@app.route('/api/sensor', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()

        # Ambil data dari JSON (digital 0/1)
        sensor_1 = int(data.get('sensor_1', 1))
        sensor_2 = int(data.get('sensor_2', 1))
        sensor_3 = int(data.get('sensor_3', 1))

        # Logika status dan alarm
        if sensor_1 == 0 or sensor_2 == 0 or sensor_3 == 0:
            if sensor_1 == 0 and sensor_2 == 0 and sensor_3 == 0:
                status = "Kebakaran"
            else:
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

        # Payload realtime untuk Flutter
        payload = {
            "sensor_1": sensor_1,
            "sensor_2": sensor_2,
            "sensor_3": sensor_3,
            "status": status,
            "alarm": alarm,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Broadcast ke Flutter via SocketIO
        socketio.emit('flame_update', payload)

        print(f"🔥 Data diterima | S1={sensor_1}, S2={sensor_2}, S3={sensor_3} | Status={status} | Alarm={alarm}")
        return jsonify({"status": "success", **payload}), 200

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# Event saat Flutter connect ke SocketIO
@socketio.on('connect')
def client_connected():
    print("📡 Flutter client tersambung ke SocketIO")


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
