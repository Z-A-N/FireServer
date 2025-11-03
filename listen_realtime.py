import socketio

sio = socketio.Client(logger=True, engineio_logger=True)

@sio.event
def connect():
    print("✅ Terhubung ke FireServer (SocketIO)")

@sio.on('flame_update')
def on_flame_update(data):
    print("🔥 Data baru dari server:", data)

@sio.event
def disconnect():
    print("❌ Terputus dari FireServer")

try:
    sio.connect(
        'https://fireserver.up.railway.app',
        transports=['websocket', 'polling'],  # coba websocket dulu, fallback polling
        wait_timeout=10
    )
    sio.wait()
except Exception as e:
    print("❌ Gagal connect:", e)
