from flask import Flask, request, jsonify
from flask_socketio import SocketIO
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
#  STATE COMMAND UNTUK IOT (SIMPLE: 1 DEVICE)
# =========================================================
# field-field ini akan dikirim balik ke Wemos lewat /api/sensor
device_command = {
    "sensor1_enabled": True,
    "sensor2_enabled": True,
    "sensor3_enabled": True,
    "test_alarm": False,   # dipakai buat TES ALARM dari Flutter
    "mute_alarm": False,   # saat ini belum dipakai aktif, selalu False
}

# =========================================================
#  ROUTE UTAMA
# =========================================================
@app.route('/')
def home():
    return "🔥 FireServer aktif & siap menerima data IoT."


# =========================================================
#  ENDPOINT RECEIVER DATA SENSOR IoT
#  (dipanggil Wemos tiap 1 detik)
# =========================================================
@app.route('/api/sensor', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json(force=True)

        device_id = data.get("device_id", "default")

        sensor_1 = int(data.get('sensor_1', 1))
        sensor_2 = int(data.get('sensor_2', 1))
        sensor_3 = int(data.get('sensor_3', 1))

        raw_1 = sensor_1
        raw_2 = sensor_2
        raw_3 = sensor_3

        iot_state = data.get("state")

        if iot_state in ("Aman", "Bahaya", "Peringatan", "Kebakaran"):
            status = iot_state
        else:
            triggered = [sensor_1, sensor_2, sensor_3].count(0)
            if triggered == 0:
                status = "Aman"
            elif triggered == 1:
                status = "Bahaya"
            elif triggered == 2:
                status = "Peringatan"
            else:
                status = "Kebakaran"

        # ⚠ NOTE: ini logika alarmmu sekarang (aku komentari di bawah)
        if status in ("Bahaya", "Peringatan", "Kebakaran"):
            alarm = "ON"
        else:
            alarm = "OFF"

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        payload = {
            "device_id": device_id,
            "sensor_1": sensor_1,
            "sensor_2": sensor_2,
            "sensor_3": sensor_3,
            "status": status,
            "alarm": alarm,
            "time": now_str,
            "active_sensors": data.get("active_sensors"),
            "first_triggered": data.get("first_triggered"),
        }

        # 1) LANGSUNG broadcast ke Flutter
        socketio.emit("flame_update", payload)

        # 2) Simpan ke DB di background (tidak menghambat response)
        socketio.start_background_task(
            save_flame_to_db, # type: ignore
            raw_1, raw_2, raw_3,
            sensor_1, sensor_2, sensor_3,
            status, alarm
        )

        print(
            f"🔥 DATA DITERIMA | "
            f"s1={sensor_1} s2={sensor_2} s3={sensor_3} | "
            f"{status} / {alarm}"
        )

        response = {
            "status": "success",
            **payload,
            "sensor1_enabled": device_command["sensor1_enabled"],
            "sensor2_enabled": device_command["sensor2_enabled"],
            "sensor3_enabled": device_command["sensor3_enabled"],
            "test_alarm": device_command["test_alarm"],
            "mute_alarm": device_command["mute_alarm"],
        }

        return jsonify(response), 200

    except Exception as e:
        print("❌ ERROR /api/sensor:", e)
        return jsonify({"status": "error", "message": str(e)}), 500



# =========================================================
#  ENDPOINT HISTORY (dipakai Flutter /api/history)
# =========================================================
@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, 
                   raw_1, raw_2, raw_3,
                   sensor_1, sensor_2, sensor_3,
                   status, alarm, created_at
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
#  KONTROL UNTUK BUZZER / LED / SENSOR (DARI FLUTTER)
# =========================================================

@app.route('/api/control/buzzer', methods=['POST'])
def control_buzzer():
    """
    Dipakai tombol 'Tes Alarm / Matikan Alarm' di Flutter.
    Kita pakai untuk set flag 'test_alarm' yang dibaca Wemos.
    """
    try:
        active = bool(request.json.get('active'))

        # tes alarm untuk IoT
        device_command["test_alarm"] = active

        socketio.emit("control_buzzer", {"active": active})
        print(f"📢 BUZZER (test_alarm) = {active}")

        return jsonify({"status": "sent", "active": active}), 200
    except Exception as e:
        print("❌ ERROR /api/control/buzzer:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/control/led', methods=['POST'])
def control_led():
    """
    Sekarang fungsinya lebih ke notifikasi / log.
    Kalau mau, nanti bisa dipakai sebagai 'mute_alarm' global.
    """
    try:
        active = bool(request.json.get('active'))

        # kalau mau pakai sebagai mute_alarm:
        # device_command["mute_alarm"] = not active

        socketio.emit("control_led", {"active": active})
        print(f"💡 LED CONTROL (from app): {active}")

        return jsonify({"status": "sent", "active": active}), 200
    except Exception as e:
        print("❌ ERROR /api/control/led:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/control/sensor', methods=['POST'])
def control_sensor():
    """
    Aktif/nonaktif tiap sensor 1/2/3 dari Flutter.
    Nilai disimpan ke device_command dan dikirim ke IoT via /api/sensor.
    """
    try:
        sensor_id = int(request.json.get('sensor'))
        active    = bool(request.json.get('active'))

        if sensor_id == 1:
            device_command["sensor1_enabled"] = active
        elif sensor_id == 2:
            device_command["sensor2_enabled"] = active
        elif sensor_id == 3:
            device_command["sensor3_enabled"] = active

        socketio.emit("control_sensor", {"sensor": sensor_id, "active": active})
        print(f"📡 SENSOR {sensor_id} => {active}")

        return jsonify({"status": "sent"}), 200

    except Exception as e:
        print("❌ ERROR /api/control/sensor:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


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
    # eventlet sudah dipakai di requirements, jadi langsung run via socketio
    socketio.run(app, host='0.0.0.0', port=port)
