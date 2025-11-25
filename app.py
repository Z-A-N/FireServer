from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return {"msg": "FireServer OK – API is running!"}

@app.route("/api/iot/fire", methods=["POST"])
def fire_data():
    data = request.get_json()
    print("DATA MASUK:", data)   # tampil di log Railway
    return {"status": "received", "data": data}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
