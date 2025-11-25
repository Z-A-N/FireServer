from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
from db import get_db, init_tables
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# -------------------------------
# INIT DATABASE
# -------------------------------
init_tables()

def save_to_db(data):
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        INSERT INTO fire_history (status, sensor1, sensor2, sensor3, alarm)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        data["state"],
        data["sensor1"],
        data["sensor2"],
        data["sensor3"],
        "ON" if data["state"] != "AMAN" else "OFF"
    ))

    db.commit()
    db.close()


# -------------------------------
# HOME
# -------------------------------
@app.route("/")
def home():
    return {"msg": "FireServer OK – MySQL + SocketIO ready!"}


# ----------------------------------------------------------
#  API DARI IOT → KIRIM DATA & BROADCAST REALTIME
# ----------------------------------------------------------
@app.route("/api/iot/fire", methods=["POST"])
def fire_data():
    data = request.get_json()

    # simpan ke database
    save_to_db(data)

    # broadcast ke aplikasi flutter
    socketio.emit("flame_update", {
        "status": data["state"].capitalize(),
        "sensor_1": data["sensor1"],
        "sensor_2": data["sensor2"],
        "sensor_3": data["sensor3"],
        "first_triggered": data["first_triggered"],
        "active_sensors": data["active_sensors"]
    })

    return {"status": "OK"}, 200


# ----------------------------------------------------------
# GET HISTORY (untuk halaman histori Flutter)
# ----------------------------------------------------------
@app.route("/api/history")
def get_history():
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM fire_history ORDER BY id DESC LIMIT 300")
    rows = cur.fetchall()

    db.close()
    return jsonify({"data": rows})


# ----------------------------------------------------------
# CONTROL BUZZER
# ----------------------------------------------------------
@app.route("/api/control/buzzer", methods=["POST"])
def control_buzzer():
    data = request.get_json()
    active = data["active"]

    socketio.emit("control_buzzer", {"active": active})
    return {"status": "OK"}, 200


# ----------------------------------------------------------
# CONTROL LED
# ----------------------------------------------------------
@app.route("/api/control/led", methods=["POST"])
def control_led():
    data = request.get_json()
    active = data["active"]

    socketio.emit("control_led", {"active": active})
    return {"status": "OK"}, 200


# ----------------------------------------------------------
# CONTROL SENSOR ON/OFF
# ----------------------------------------------------------
@app.route("/api/control/sensor", methods=["POST"])
def control_sensor():
    data = request.get_json()
    sensor = data["sensor"]
    active = data["active"]

    socketio.emit("control_sensor", {
        "sensor": sensor,
        "active": active
    })
    return {"status": "OK"}, 200


# ----------------------------------------------------------
# SOCKET.IO HANDLER
# ----------------------------------------------------------
@socketio.on("connect")
def conn():
    print("Flutter Connected")

@socketio.on("disconnect")
def disc():
    print("Flutter Disconnected")

# ----------------------------------------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
