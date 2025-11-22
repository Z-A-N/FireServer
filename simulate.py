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
# FUNCTION: SEND TO API + SOCKET
# ======================================================
def send_data(s1, s2, s3, window=None):
    payload = {
        "sensor_1": s1,
        "sensor_2": s2,
        "sensor_3": s3
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
        window["log"].print(f"Mengirim: {payload}")
        window["log"].print(log)
        window["log"].print("-" * 40)

    return payload


# ======================================================
# AUTO RANDOM THREADING
# ======================================================
running = False

def auto_random(interval, window):
    global running
    while running:
        mode = random.choice(["aman", "bahaya", "kebakaran"])

        if mode == "aman":
            send_data(1, 1, 1, window)
        elif mode == "bahaya":
            send_data(0, 1, 1, window)
        else:
            send_data(0, 0, 0, window)

        time.sleep(interval)


# ======================================================
# GUI DEFINITION
# ======================================================
layout = [
    [sg.Text("🔥 FLAME SIMULATOR GUI", font=("Arial", 16, "bold"))],
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

    # Manual control buttons
    if event == "Aman":
        send_data(1, 1, 1, window)

    elif event == "Bahaya":
        send_data(0, 1, 1, window)

    elif event == "Kebakaran":
        send_data(0, 0, 0, window)

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
