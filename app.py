import os
from datetime import datetime

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_socketio import SocketIO

# ======================================================
#  FLASK APP + SOCKETIO + DB
# ======================================================
app = Flask(__name__)
CORS(app)

# ======================================================
#  DATABASE CONFIG (MySQL Railway)
# ======================================================
db_url = os.getenv("MYSQL_URL")

if not db_url:
    raise Exception("MYSQL_URL NOT SET IN RAILWAY")

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---- SOCKET.IO (dipakai Flutter) ----
socketio = SocketIO(app, cors_allowed_origins="*")

# ======================================================
#  MODEL HISTORY (1 device saja)
# ======================================================
class History(db.Model):
    __tablename__ = "history"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    status = db.Column(db.String(20), nullable=False)  # "Aman", "Bahaya", "Kebakaran"
    alarm = db.Column(db.String(5), nullable=False)    # "ON" / "OFF"

    sensor_1 = db.Column(db.Integer, nullable=False)   # 0 = api, 1 = aman
    sensor_2 = db.Column(db.Integer, nullable=False)
    sensor_3 = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "status": self.status,
            "alarm": self.alarm,
            "sensor_1": self.sensor_1,
            "sensor_2": self.sensor_2,
            "sensor_3": self.sensor_3,
        }


with app.app_context():
    db.create_all()

# ======================================================
#  STATE GLOBAL (1 DEVICE)
# ======================================================
current_state = {
    "sensor_1": 1,
    "sensor_2": 1,
    "sensor_3": 1,
    "status": "Aman",
}
alarm_state = False                    # dikontrol dari /api/control/buzzer
sensors_enabled = {1: True, 2: True, 3: True}  # dipakai kalau nanti mau


def build_payload():
    """Payload yang DIHARAPKAN Flutter pada event 'flame_update'."""
    return {
        "sensor_1": current_state["sensor_1"],
        "sensor_2": current_state["sensor_2"],
        "sensor_3": current_state["sensor_3"],
        "status": current_state["status"],
        "alarm": "ON" if alarm_state else "OFF",
    }


# ======================================================
#  ROUTE UTAMA / HEALTHCHECK
# ======================================================
@app.route("/")
def home():
    return jsonify({"message": "FlameGuard API OK"})


# ======================================================
#  ENDPOINT: IoT kirim data sensor
#  URL: POST /api/iot/fire
# ======================================================
@app.route("/api/iot/fire", methods=["POST"])
def iot_fire():
    global current_state

    data = request.get_json(silent=True) or {}

    # ---- Ambil data dari NodeMCU ----
    raw_state = str(data.get("state", "AMAN")).upper()
    s1 = int(data.get("sensor1", 1))
    s2 = int(data.get("sensor2", 1))
    s3 = int(data.get("sensor3", 1))

    # ---- Mapping state IoT -> status untuk Flutter / History ----
    if raw_state == "AMAN":
        status = "Aman"
    elif raw_state in ["BAHAYA", "PERINGATAN"]:
        status = "Bahaya"
    elif raw_state == "KEBAKARAN":
        status = "Kebakaran"
    else:
        status = raw_state  # fallback

    # ---- Update state global ----
    current_state["sensor_1"] = s1
    current_state["sensor_2"] = s2
    current_state["sensor_3"] = s3
    current_state["status"] = status

    # ---- Simpan ke History ----
    history_row = History(
        status=status,
        alarm="ON" if alarm_state else "OFF",
        sensor_1=s1,
        sensor_2=s2,
        sensor_3=s3,
    )
    db.session.add(history_row)
    db.session.commit()

    # ---- Broadcast ke semua client Flutter via Socket.IO ----
    payload = build_payload()
    socketio.emit("flame_update", payload, broadcast=True)

    return jsonify({"status": "ok", "payload": payload})


# ======================================================
#  ENDPOINT: GET HISTORY (untuk HistoryPage)
#  URL: GET /api/history
# ======================================================
@app.route("/api/history", methods=["GET"])
def get_history():
    limit = int(request.args.get("limit", 200))
    logs = History.query.order_by(History.created_at.desc()).limit(limit).all()
    data = [h.to_dict() for h in logs]
    return jsonify({"data": data})


# ======================================================
#  ENDPOINT: CONTROL BUZZER (Alarm)
#  URL: POST /api/control/buzzer {active: bool}
# ======================================================
@app.route("/api/control/buzzer", methods=["POST"])
def control_buzzer():
    global alarm_state

    data = request.get_json(silent=True) or {}
    active = bool(data.get("active", False))

    alarm_state = active

    # Kirim update terbaru ke Flutter
    payload = build_payload()
    socketio.emit("flame_update", payload, broadcast=True)

    return jsonify({"status": "ok", "alarm": "ON" if alarm_state else "OFF"})


# ======================================================
#  ENDPOINT: CONTROL LED
#  URL: POST /api/control/led {active: bool}
#  (Sekarang hanya ACK, nanti bisa diteruskan ke IoT)
# ======================================================
@app.route("/api/control/led", methods=["POST"])
def control_led():
    # Sekarang belum diteruskan ke IoT, hanya return sukses.
    return jsonify({"status": "ok"})


# ======================================================
#  ENDPOINT: CONTROL SENSOR (enable/disable)
#  URL: POST /api/control/sensor {sensor: 1..3, active: bool}
# ======================================================
@app.route("/api/control/sensor", methods=["POST"])
def control_sensor():
    global sensors_enabled

    data = request.get_json(silent=True) or {}
    sensor_id = int(data.get("sensor", 0))
    active = bool(data.get("active", True))

    if sensor_id not in [1, 2, 3]:
        return jsonify({"error": "invalid sensor id"}), 400

    sensors_enabled[sensor_id] = active

    return jsonify({"status": "ok", "sensor": sensor_id, "active": active})


# ======================================================
#  SOCKET.IO EVENT (optional log)
# ======================================================
@socketio.on("connect")
def handle_connect():
    # Kirim state terakhir saat Flutter baru connect
    socketio.emit("flame_update", build_payload())
    print("Client connected")


@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected")


# ======================================================
#  ENTRY POINT
# ======================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # eventlet dipakai oleh Flask-SocketIO untuk WebSocket
    socketio.run(app, host="0.0.0.0", port=port)
