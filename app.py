from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from db import get_db
import os
import datetime

app = Flask(__name__)
CORS(app)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet"
)

# =========================================================
#  ROUTE UTAMA
# =========================================================
@app.route('/')
def home():
    return "🔥 FireServer aktif & siap menerima data IoT."


# =========================================================
#  ENDPOINT RECEIVER DATA SENSOR IoT
# =========================================================
@app.route('/api/sensor', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()

        # RAW sensor values (ADC)
        raw_1 = int(data.get('sensor_1', 1))
        raw_2 = int(data.get('sensor_2', 1))
        raw_3 = int(data.get('sensor_3', 1))

        # Threshold konversi RAW → BINARY
        # Sesuaikan dengan karakteristik sensor IR kamu
        TH = 100

        sensor_1 = 0 if raw_1 <= TH else 1
        sensor_2 = 0 if raw_2 <= TH else 1
        sensor_3 = 0 if raw_3 <= TH else 1

        # Tentukan status sistem
        if sensor_1 == 0 and sensor_2 == 0 and sensor_3 == 0:
            status = "Kebakaran"
            alarm = "ON"
        elif sensor_1 == 0 or sensor_2 == 0 or sensor_3 == 0:
            status = "Bahaya"
            alarm = "ON"
        else:
            status = "Aman"
            alarm = "OFF"

        # Insert ke database (RAW + BINARY)
        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO flame_data (raw_1, raw_2, raw_3, 
                                    sensor_1, sensor_2, sensor_3,
                                    status, alarm)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (raw_1, raw_2, raw_3, sensor_1, sensor_2, sensor_3, status, alarm))

        db.commit()
        cursor.close()
        db.close()

        # Broadcast realtime ke Flutter
        payload = {
            "raw_1": raw_1,
            "raw_2": raw_2,
            "raw_3": raw_3,
            "sensor_1": sensor_1,
            "sensor_2": sensor_2,
            "sensor_3": sensor_3,
            "status": status,
            "alarm": alarm,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        socketio.emit("flame_update", payload)

        print(f"🔥 DATA DITERIMA | RAW=({raw_1},{raw_2},{raw_3}) BINARY=({sensor_1},{sensor_2},{sensor_3}) | {status} / {alarm}")
        return jsonify({"status": "success", **payload}), 200

    except Exception as e:
        print("❌ ERROR:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# =========================================================
#  ENDPOINT HISTORY
# =========================================================
@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
    SELECT id, raw_1, raw_2, raw_3,
           sensor_1, sensor_2, sensor_3,
           status, alarm,
           DATE_FORMAT(created_at, '%Y-%m-%dT%H:%i:%sZ') AS created_at
    FROM flame_data
    ORDER BY id DESC
    LIMIT 200
""")

        data = cursor.fetchall()
        cursor.close()
        db.close()

        return jsonify({"status": "success", "data": data})

    except Exception as e:
        print("❌ History error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# =========================================================
#  KONTROL UNTUK LED / BUZZER / SENSOR (UNTUK IoT)
# =========================================================

@app.route('/api/control/buzzer', methods=['POST'])
def control_buzzer():
    active = request.json.get('active')
    socketio.emit("control_buzzer", {"active": active})
    print(f"📢 BUZZER: {active}")
    return jsonify({"status": "sent", "active": active})

@app.route('/api/control/led', methods=['POST'])
def control_led():
    active = request.json.get('active')
    socketio.emit("control_led", {"active": active})
    print(f"💡 LED: {active}")
    return jsonify({"status": "sent", "active": active})

@app.route('/api/control/sensor', methods=['POST'])
def control_sensor():
    sensor_id = request.json.get('sensor')
    active = request.json.get('active')
    socketio.emit("control_sensor", {"sensor": sensor_id, "active": active})
    print(f"📡 SENSOR {sensor_id} => {active}")
    return jsonify({"status": "sent"})


# =========================================================
# EVENT SOCKET.IO
# =========================================================
@socketio.on('connect')
def on_connect():
    print("📡 Client Flutter/IoT Connected")


# =========================================================
# RUN SERVER
# =========================================================
if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)

