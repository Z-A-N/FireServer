from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
from db import get_db
import os
import datetime
import logging

# 🔇 Biar log bawaan engineio/socketio nggak spam "emitting event..."
logging.getLogger('engineio').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)

# ⚙️ Inisialisasi Flask & SocketIO
app = Flask(__name__)
CORS(app)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_interval=25,
    ping_timeout=120,
    logger=True,
    engineio_logger=True
)

# 🏠 Halaman utama
@app.route('/')
def home():
    return "🔥 FireServer aktif! Menunggu data dari 3 sensor api (WeMos D1 Mini)."

# 🔍 Endpoint tes koneksi
@app.route('/api/ping', methods=['GET'])
def ping():
    print(f"[PING] Flutter/Web cek koneksi - {datetime.datetime.now()}")
    return jsonify({
        "status": "alive",
        "time": datetime.datetime.now().isoformat()
    })

# 🔥 Endpoint untuk menerima data dari Wemos
@app.route('/api/sensor', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()
        s1 = int(data.get('sensor_1', 1))
        s2 = int(data.get('sensor_2', 1))
        s3 = int(data.get('sensor_3', 1))

        # Logika status & alarm
        if s1 == 0 or s2 == 0 or s3 == 0:
            if s1 == 0 and s2 == 0 and s3 == 0:
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
        """, (s1, s2, s3, status, alarm))
        db.commit()
        cursor.close()
        db.close()

        # Payload ke Flutter
        payload = {
            "sensor_1": s1,
            "sensor_2": s2,
            "sensor_3": s3,
            "status": status,
            "alarm": alarm,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 🚀 Kirim data realtime
        socketio.emit('flame_update', payload)

        # Hitung berapa client yang aktif di namespace "/"
        connected_clients = 0
        if hasattr(socketio.server.manager, 'rooms') and '/' in socketio.server.manager.rooms:
            connected_clients = len(socketio.server.manager.rooms['/'])

        print(f"[SEND] flame_update → dikirim ke {connected_clients} client ({datetime.datetime.now().strftime('%H:%M:%S')})")
        print(f"[DATA] S1={s1}, S2={s2}, S3={s3} | Status={status} | Alarm={alarm}")
        return jsonify({"status": "success", **payload}), 200

    except Exception as e:
        print(f"[❌ ERROR] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# 📡 Saat Flutter connect
@socketio.on('connect')
def on_connect():
    print(f"[CONNECT] Flutter client tersambung ke SocketIO ({datetime.datetime.now()})")

# ❌ Saat Flutter disconnect
@socketio.on('disconnect')
def on_disconnect():
    print(f"[DISCONNECT] Flutter client terputus ({datetime.datetime.now()})")

# ▶️ Run Server
if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    print(f"[START] FireServer berjalan di port {port}")
    socketio.run(app, host='0.0.0.0', port=port)
