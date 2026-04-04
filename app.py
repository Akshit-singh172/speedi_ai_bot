from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def load_prompt():
    with open("prompt.txt", "r", encoding="utf-8") as file:
        return file.read()

System_prompt = load_prompt()

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "Message is required"}), 400

    user_message = data["message"]

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
               contents=[
                {
                    "role": "user",
                    "parts": [{"text": user_message}]
                }
            ],
            config={
                "system_instruction": System_prompt,
                "max_output_tokens": 300
            }
        )

        reply = response.text

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