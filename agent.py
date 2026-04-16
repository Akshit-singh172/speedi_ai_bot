from google import genai
from google.genai import types # Use types for strict schema support
from dotenv import load_dotenv
from pathlib import Path
from dataclasses import dataclass
import os
from typing import Any, Optional

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHAT_MODEL = "gemini-2.5-flash"

# Use the Client with the appropriate API version if needed
if not GEMINI_API_KEY:
    raise Exception("Missing GEMINI_API_KEY in environment (.env)")

client = genai.Client(api_key=GEMINI_API_KEY)

# TOOL DEFINITIONS
generate_image_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="generate_image",
            description="Generate an image from a text prompt and return a URL that can be displayed in the UI.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "prompt": types.Schema(type="STRING"),
                    "filenameHint": types.Schema(type="STRING"),
                },
                required=["prompt"],
            ),
        )
    ]
)

def load_prompt():
    prompt_path = Path(__file__).resolve().parent / "prompt.txt"
    with open(prompt_path, "r", encoding="utf-8") as file:
        return file.read()

SYSTEM_PROMPT = load_prompt()

@dataclass
class _ChatSession:
    chat: Any
    model: str


_chats: dict[str, _ChatSession] = {}


def reset_chat(user_id: str) -> None:
    if not user_id:
        return
    _chats.pop(user_id, None)


def _first_function_call_part(response: Any) -> Optional[Any]:
    try:
        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            return None
        for part in candidate.content.parts:
            if getattr(part, "function_call", None):
                return part
        return None
    except Exception:
        return None


def _chat_model_variants() -> list[str]:
    # Keep a single model ("2.5 flash") but try both naming formats.
    return [CHAT_MODEL, f"models/{CHAT_MODEL}"]


def _looks_like_model_error(exc: Exception) -> bool:
    message = str(exc).lower()
    if "unexpected model name format" in message:
        return True
    if "model" in message and "not found" in message:
        return True
    if "model" in message and "no longer available" in message:
        return True
    return False


def _create_chat(config: types.GenerateContentConfig) -> _ChatSession:
    last_error: Exception | None = None
    for model_name in _chat_model_variants():
        try:
            chat = client.chats.create(model=model_name, config=config)
            return _ChatSession(chat=chat, model=model_name)
        except Exception as e:
            last_error = e
            continue

    raise Exception(
        "Failed to create Gemini chat session. "
        f"Tried: {_chat_model_variants()}. "
        f"Last error: {last_error}"
    )


def run_agent(user_prompt: str, user_id: str):
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[generate_image_tool],
    )

    session = _chats.get(user_id)
    if session is None:
        session = _create_chat(config)
        _chats[user_id] = session

    try:
        response = session.chat.send_message(user_prompt)
    except Exception as e:
        # If the SDK deferred model validation until the first request, retry with the alternate naming format.
        if _looks_like_model_error(e):
            alternate = next((m for m in _chat_model_variants() if m != session.model), None)
            if alternate:
                session = _ChatSession(chat=client.chats.create(model=alternate, config=config), model=alternate)
                _chats[user_id] = session
                response = session.chat.send_message(user_prompt)
            else:
                raise
        else:
            raise

    last_image_payload = None

    # Manual Tool Loop
    while True:
        part = _first_function_call_part(response)
        if not part:
            break

        fc = part.function_call
        tool_name = fc.name

        args = dict(fc.args) if getattr(fc, "args", None) else {}

        from tools import handle_tool_call
        result = handle_tool_call(tool_name, args)

        if tool_name == "generate_image":
            last_image_payload = result

        response = session.chat.send_message(
            types.Part.from_function_response(
                name=tool_name,
                response=result,
            )
        )

    text = response.text or ""

    if last_image_payload:
        return {
            "type": "image",
            "message": text.strip() or last_image_payload.get("message") or "Here you go.",
            "data": last_image_payload.get("data", []),
        }

    return {"type": "message", "data": text}
