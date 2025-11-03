import socketio

sio = socketio.Client()

@sio.event
def connect():
    print("✅ Terhubung ke FireServer")

@sio.on('flame_update')
def on_flame_update(data):
    print("🔥 Data baru dari server:", data)

@sio.event
def disconnect():
    print("❌ Terputus")

sio.connect('https://fireserver.up.railway.app')
sio.wait()
