from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "FireServer Flask is running!", 200

@app.route("/api/flame", methods=["POST"])
def flame():
    data = request.get_json()

    print("Data masuk:", data)

    return jsonify({
        "success": True,
        "received": data
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
