from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from agent import run_agent

load_dotenv()

app = Flask(__name__)
CORS(app)

def load_prompt():
    with open("prompt.txt", "r", encoding="utf-8") as file:
        return file.read()

SYSTEM_PROMPT = load_prompt()


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()

    if not data or "message" not in data or "user_id" not in data:
        return jsonify({"error": "message and user_id are required"}), 400

    user_message = data["message"]
    user_id = data["user_id"]

    try:
        reply = run_agent(user_message, user_id)

        return jsonify({
            "reply": reply
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    return "Gemini Chatbot Backend Running 🚀"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)