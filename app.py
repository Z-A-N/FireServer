import eventlet
eventlet.monkey_patch()    # WAJIB PALING ATAS!!

from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from db import get_db, init_tables
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Init table MySQL
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


@app.route("/")
def home():
    return {"msg": "FireServer OK"}


@app.route("/api/iot/fire", methods=["POST"])
def fire_update():
    data = request.get_json()

    save_to_db(data)

    socketio.emit("flame_update", {
        "status": data["state"].capitalize(),
        "sensor_1": data["sensor1"],
        "sensor_2": data["sensor2"],
        "sensor_3": data["sensor3"],
        "first_triggered": data["first_triggered"],
        "active_sensors": data["active_sensors"]
    })

    return {"status": "OK"}, 200


@app.route("/api/history")
def history():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM fire_history ORDER BY id DESC LIMIT 300")
    rows = cur.fetchall()
    db.close()
    return jsonify({"data": rows})


@socketio.on("connect")
def connected():
    print("Flutter Connected")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
