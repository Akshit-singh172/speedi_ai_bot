from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "Message is required"}), 400

    user_message = data["message"]

    try:
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )

        reply = response.content[0].text

        return jsonify({
            "reply": reply
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def home():
    return "Claude Chatbot Backend Running 🚀"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)