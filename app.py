import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from db import get_db   # db.py punyamu

# ==========================================================
# APP & SOCKET.IO SETUP
# ==========================================================
app = Flask(__name__)
CORS(app)

# gunakan eventlet / gevent kalau tersedia
socketio = SocketIO(app, cors_allowed_origins="*")

# ==========================================================
# HELPER: DB QUERY
# ==========================================================
def fetchone_dict(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


def fetchall_dict(cursor):
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, r)) for r in rows]


# ==========================================================
# ROOT (cek server hidup)
# ==========================================================
@app.route("/")
def index():
    return jsonify({"message": "FlameGuard server aktif"})


# ==========================================================
# IOT -> SERVER : KIRIM DATA SENSOR
# ==========================================================
@app.route("/api/sensor", methods=["POST"])
def api_sensor():
    """
    Body JSON yang diharapkan dari IoT:
    {
      "sensor_1": 0/1,
      "sensor_2": 0/1,
      "sensor_3": 0/1,
      "status": "Aman" | "Bahaya" | "Kebakaran",
      "alarm": "ON" | "OFF",
      "raw_1": int (opsional),
      "raw_2": int (opsional),
      "raw_3": int (opsional)
    }
    """
    data = request.get_json(silent=True) or {}
    try:
        sensor_1 = int(data.get("sensor_1", 1))
        sensor_2 = int(data.get("sensor_2", 1))
        sensor_3 = int(data.get("sensor_3", 1))

        status = data.get("status", "Aman")
        alarm = data.get("alarm", "OFF")

        raw_1 = int(data.get("raw_1", 0) or 0)
        raw_2 = int(data.get("raw_2", 0) or 0)
        raw_3 = int(data.get("raw_3", 0) or 0)

    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "invalid payload"}), 400

    # simpan ke database
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO flame_data (sensor_1, sensor_2, sensor_3,
                                status, alarm,
                                raw_1, raw_2, raw_3)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (sensor_1, sensor_2, sensor_3, status, alarm, raw_1, raw_2, raw_3),
    )
    cur.close()
    conn.close()

    # kirim realtime ke Flutter
    payload = {
        "sensor_1": sensor_1,
        "sensor_2": sensor_2,
        "sensor_3": sensor_3,
        "status": status,
        "alarm": alarm,
    }
    socketio.emit("flame_update", payload, broadcast=True)

    return jsonify({"success": True}), 200


# ==========================================================
# IOT -> SERVER : AMBIL COMMAND
# ==========================================================
@app.route("/api/command", methods=["GET"])
def api_command():
    """
    Dipanggil IoT secara periodik.
    Ambil 1 baris dari device_command.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT buzzer, led, sensor_1, sensor_2, sensor_3 FROM device_command ORDER BY id ASC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        # fallback kalau belum ada row sama sekali
        return jsonify({
            "buzzer": False,
            "led": False,
            "sensor_1": True,
            "sensor_2": True,
            "sensor_3": True,
        })

    buzzer, led, s1, s2, s3 = row
    return jsonify({
        "buzzer": bool(buzzer),
        "led": bool(led),
        "sensor_1": bool(s1),
        "sensor_2": bool(s2),
        "sensor_3": bool(s3),
    })


# ==========================================================
# FLUTTER -> SERVER : CONTROL BUZZER
# ==========================================================
@app.route("/api/control/buzzer", methods=["POST"])
def api_control_buzzer():
    data = request.get_json(silent=True) or {}
    active = bool(data.get("active", False))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE device_command SET buzzer = %s WHERE id = 1",
        (1 if active else 0,),
    )
    cur.close()
    conn.close()

    return jsonify({"success": True})


# ==========================================================
# FLUTTER -> SERVER : CONTROL LED
# ==========================================================
@app.route("/api/control/led", methods=["POST"])
def api_control_led():
    data = request.get_json(silent=True) or {}
    active = bool(data.get("active", False))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE device_command SET led = %s WHERE id = 1",
        (1 if active else 0,),
    )
    cur.close()
    conn.close()

    return jsonify({"success": True})


# ==========================================================
# FLUTTER -> SERVER : CONTROL SENSOR (ENABLE / DISABLE)
# ==========================================================
@app.route("/api/control/sensor", methods=["POST"])
def api_control_sensor():
    """
    Body:
    { "sensor": 1, "active": true }
    """
    data = request.get_json(silent=True) or {}
    sensor_id = int(data.get("sensor", 1))
    active = bool(data.get("active", True))

    if sensor_id not in (1, 2, 3):
        return jsonify({"success": False, "error": "sensor id must be 1,2,3"}), 400

    field = f"sensor_{sensor_id}"

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE device_command SET {field} = %s WHERE id = 1",
        (1 if active else 0,),
    )
    cur.close()
    conn.close()

    return jsonify({"success": True})


# ==========================================================
# FLUTTER -> SERVER : GET HISTORY
# ==========================================================
@app.route("/api/history", methods=["GET"])
def api_history():
    """
    Mengembalikan list data untuk halaman HistoryPage.
    Flutter mengharapkan:
      { "data": [ {...}, {...} ] }
    """
    limit = int(request.args.get("limit", 500))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT id, sensor_1, sensor_2, sensor_3,
               status, alarm, created_at,
               raw_1, raw_2, raw_3
        FROM flame_data
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (limit,),
    )
    rows = fetchall_dict(cur)
    cur.close()
    conn.close()

    # format created_at jadi string yang mudah di-parse flutter
    for r in rows:
        dt = r.get("created_at")
        if dt is not None:
            r["created_at"] = dt.strftime("%Y-%m-%d %H:%M:%S")

    return jsonify({"data": rows})


# ==========================================================
# MAIN
# ==========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # gunakan 0.0.0.0 supaya bisa diakses Railway
    socketio.run(app, host="0.0.0.0", port=port)
