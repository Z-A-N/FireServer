import os
from datetime import datetime

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_socketio import SocketIO


# ======================================================
#  MYSQL CONFIG (MANUAL, RECOMMENDED)
# ======================================================
MYSQL_HOST = os.getenv("MYSQLHOST") or os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQLPORT") or os.getenv("MYSQL_PORT")
MYSQL_USER = os.getenv("MYSQLUSER") or os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQLPASSWORD") or os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQLDATABASE") or os.getenv("MYSQL_DB")

# Validate
missing = [k for k, v in {
    "MYSQLHOST": MYSQL_HOST,
    "MYSQLPORT": MYSQL_PORT,
    "MYSQLUSER": MYSQL_USER,
    "MYSQLPASSWORD": MYSQL_PASSWORD,
    "MYSQLDATABASE": MYSQL_DB
}.items() if not v]

if missing:
    raise Exception("Missing ENV vars: " + ", ".join(missing))

# Build SQLAlchemy URL
DB_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"


# ======================================================
#  INIT APP
# ======================================================
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


# ======================================================
#  HISTORY MODEL
# ======================================================
class History(db.Model):
    __tablename__ = "history"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    status = db.Column(db.String(20), nullable=False)
    alarm = db.Column(db.String(5), nullable=False)

    sensor_1 = db.Column(db.Integer, nullable=False)
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


# Auto create tables
with app.app_context():
    db.create_all()


# ======================================================
#  GLOBAL STATE (1 device)
# ======================================================
device_state = {
    "sensor_1": 1,
    "sensor_2": 1,
    "sensor_3": 1,
    "status": "Aman",
}
alarm_state = False


def build_payload():
    return {
        "sensor_1": device_state["sensor_1"],
        "sensor_2": device_state["sensor_2"],
        "sensor_3": device_state["sensor_3"],
        "status": device_state["status"],
        "alarm": "ON" if alarm_state else "OFF"
    }


# ======================================================
#  ROUTES
# ======================================================
@app.route("/")
def home():
    return jsonify({"msg": "FlameGuard Backend Running"})


# ======================================================
#  IOT SEND DATA
# ======================================================
@app.route("/api/iot/fire", methods=["POST"])
def iot_fire():
    global device_state

    data = request.get_json(force=True)

    raw = str(data.get("state", "AMAN")).upper()
    s1 = int(data.get("sensor1", 1))
    s2 = int(data.get("sensor2", 1))
    s3 = int(data.get("sensor3", 1))

    if raw == "AMAN":
        status = "Aman"
    elif raw in ["BAHAYA", "PERINGATAN"]:
        status = "Bahaya"
    else:
        status = "Kebakaran"

    device_state.update({
        "sensor_1": s1,
        "sensor_2": s2,
        "sensor_3": s3,
        "status": status
    })

    row = History(
        status=status,
        alarm="ON" if alarm_state else "OFF",
        sensor_1=s1, sensor_2=s2, sensor_3=s3
    )
    db.session.add(row)
    db.session.commit()

    socketio.emit("flame_update", build_payload(), broadcast=True)

    return jsonify({"ok": True})


# ======================================================
#  GET HISTORY (Flutter uses)
# ======================================================
@app.route("/api/history", methods=["GET"])
def get_history():
    logs = History.query.order_by(History.created_at.desc()).limit(200).all()
    return jsonify({"data": [r.to_dict() for r in logs]})


# ======================================================
#  CONTROL: BUZZER
# ======================================================
@app.route("/api/control/buzzer", methods=["POST"])
def control_buzzer():
    global alarm_state

    data = request.get_json(force=True)
    alarm_state = bool(data.get("active", False))

    socketio.emit("flame_update", build_payload(), broadcast=True)
    return jsonify({"ok": True})


# ======================================================
#  CONTROL: LED
# ======================================================
@app.route("/api/control/led", methods=["POST"])
def control_led():
    return jsonify({"ok": True})


# ======================================================
#  CONTROL: SENSOR
# ======================================================
@app.route("/api/control/sensor", methods=["POST"])
def control_sensor():
    return jsonify({"ok": True})


# ======================================================
#  SOCKET.IO HANDLERS
# ======================================================
@socketio.on("connect")
def on_connect():
    socketio.emit("flame_update", build_payload())
    print("Flutter connected!")


# ======================================================
#  RUN SERVER
# ======================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
