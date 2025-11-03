import requests
import random
import time

URL = "https://fireserver.up.railway.app/api/sensor"  # ✅ domain kamu

while True:
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

    time.sleep(5)
