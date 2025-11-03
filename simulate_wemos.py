import requests
import random
import time

# URL endpoint dari server Railway kamu
URL = "https://fireserver-production.up.railway.app/api/sensor"

while True:
    # Simulasi nilai sensor (0–1023)
    sensor_1 = random.randint(100, 1000)
    sensor_2 = random.randint(100, 1000)
    sensor_3 = random.randint(100, 1000)

    data = {
        "sensor_1": sensor_1,
        "sensor_2": sensor_2,
        "sensor_3": sensor_3
    }

    try:
        response = requests.post(URL, json=data)
        print(f"📡 Data dikirim: {data}")
        print(f"💬 Response: {response.json()}")
    except Exception as e:
        print(f"❌ Gagal kirim data: {e}")

    time.sleep(5)  # kirim tiap 5 detik
