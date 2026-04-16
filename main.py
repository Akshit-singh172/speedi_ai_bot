from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from agent import run_agent, reset_chat

load_dotenv()

app = Flask(__name__)
CORS(app)


def _handle_chat_payload(data):
    if not data or "message" not in data or "user_id" not in data:
        return jsonify({"error": "message and user_id are required"}), 400

    user_message = data["message"]
    user_id = data["user_id"]

    try:
        reply = run_agent(user_message, user_id)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/chat", methods=["POST"])
def chat():
    return _handle_chat_payload(request.get_json())


@app.route("/api/chat", methods=["POST"])
def api_chat():
    return _handle_chat_payload(request.get_json())

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/reset", methods=["POST"])
def reset():
    data = request.get_json() or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    reset_chat(str(user_id))
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
