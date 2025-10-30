from db import get_db

try:
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT DATABASE();")
    result = cursor.fetchone()
    print("✅ Koneksi ke database berhasil!")
    print("📦 Database aktif:", result[0])
    cursor.close()
    db.close()
except Exception as e:
    print("❌ Gagal konek ke database:", e)
