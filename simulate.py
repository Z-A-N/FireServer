import PySimpleGUI as sg
import requests
import random
import threading
import time
import socketio

# ======================================================
# CONFIG
# ======================================================
REST_URL = "https://fireserver.up.railway.app/api/sensor"
SOCKET_URL = "https://fireserver.up.railway.app"

sio = socketio.Client()

try:
    sio.connect(SOCKET_URL, transports=['websocket'])
    print("SOCKET CONNECTED")
except Exception as e:
    print("SOCKET ERROR:", e)


# ======================================================
# FUNCTION: SEND RAW SENSOR DATA
# ======================================================
def send_data(raw1, raw2, raw3, window=None):
    payload = {
        "sensor_1": raw1,
        "sensor_2": raw2,
        "sensor_3": raw3
    }

    # REST API
    try:
        res = requests.post(REST_URL, json=payload)
        log = f"API RESP: {res.text}"
    except:
        log = "API ERROR"

    # SOCKET
    try:
        sio.emit("flame_update", payload)
        log += " | SOCKET SENT"
    except:
        log += " | SOCKET FAILED"

    # Tampilkan log di GUI
    if window:
        window["log"].print(f"Mengirim RAW: {payload}")
        window["log"].print(log)
        window["log"].print("-" * 40)

    return payload


# ======================================================
# GENERATE RAW VALUE UNTUK MODE
# ======================================================
def make_raw_value(mode):
    if mode == "aman":
        # Nilai raw normal (sensor mendeteksi tidak ada api)
        return (
            random.randint(400, 900),
            random.randint(400, 900),
            random.randint(400, 900)
        )

    if mode == "bahaya":
        # Satu sensor mendeteksi api
        return (
            random.randint(0, 80),        # sensor 1 bahaya
            random.randint(300, 900),
            random.randint(300, 900)
        )

    if mode == "kebakaran":
        # Semua sensor mendeteksi api
        return (
            random.randint(0, 60),
            random.randint(0, 60),
            random.randint(0, 60)
        )


# ======================================================
# AUTO RANDOM THREADING
# ======================================================
running = False

def auto_random(interval, window):
    global running
    while running:
        mode = random.choice(["aman", "bahaya", "kebakaran"])
        raw_vals = make_raw_value(mode)
        send_data(*raw_vals, window)
        time.sleep(interval)


# ======================================================
# GUI DEFINITION
# ======================================================
layout = [
    [sg.Text("🔥 FLAME SIMULATOR GUI (RAW SENSOR)", font=("Arial", 16, "bold"))],
    [sg.HorizontalSeparator()],

    [sg.Button("Aman", size=(12, 2), button_color=("white", "green")),
     sg.Button("Bahaya", size=(12, 2), button_color=("white", "orange")),
     sg.Button("Kebakaran", size=(12, 2), button_color=("white", "red"))],

    [sg.Text("Auto Random:"), sg.Checkbox("Aktifkan", key="auto")],
    [sg.Text("Interval (detik):"),
     sg.Input("3", key="interval", size=(5,1))],

    [sg.Frame("Log Output", [
        [sg.Multiline(size=(70, 20), key="log", autoscroll=True)]
    ])],

    [sg.Button("Keluar")]
]

window = sg.Window("Flame Simulator", layout)


# ======================================================
# MAIN LOOP
# ======================================================
while True:
    event, values = window.read(timeout=100)

    if event in (sg.WINDOW_CLOSED, "Keluar"):
        running = False
        break

    # Manual mode buttons
    if event == "Aman":
        send_data(*make_raw_value("aman"), window)

    elif event == "Bahaya":
        send_data(*make_raw_value("bahaya"), window)

    elif event == "Kebakaran":
        send_data(*make_raw_value("kebakaran"), window)

    # Auto-random ON
    if values["auto"] and not running:
        try:
            interval = float(values["interval"])
        except:
            interval = 3

        running = True
        threading.Thread(target=auto_random, args=(interval, window), daemon=True).start()

    # Auto-random OFF
    if not values["auto"] and running:
        running = False

window.close()
