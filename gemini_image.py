from __future__ import annotations

from dotenv import load_dotenv
from google import genai
from pathlib import Path
import base64
import os
import time
import uuid

load_dotenv()

STATIC_DIR = Path(__file__).resolve().parent / "static"
GENERATED_DIR = STATIC_DIR / "generated"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise Exception("Missing GEMINI_API_KEY in environment (.env)")

_client = genai.Client(api_key=GEMINI_API_KEY)

GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"


def _ext_from_mime(mime_type: str | None) -> str:
    mime = (mime_type or "").lower().strip()
    if mime in ("image/jpeg", "image/jpg"):
        return "jpg"
    if mime == "image/webp":
        return "webp"
    return "png"


def _extract_parts(response) -> list:
    parts = getattr(response, "parts", None)
    if parts:
        return list(parts)
    try:
        return list(response.candidates[0].content.parts)
    except Exception:
        return []


def _inline_data(part):
    return getattr(part, "inline_data", None) or getattr(part, "inlineData", None)


def _inline_bytes(inline) -> tuple[bytes | None, str | None]:
    if not inline:
        return None, None

    data = getattr(inline, "data", None)
    if data is None:
        return None, None

    if isinstance(data, (bytes, bytearray)):
        payload = bytes(data)
    elif isinstance(data, str):
        payload = base64.b64decode(data)
    else:
        try:
            payload = bytes(data)
        except Exception:
            return None, None

    mime = getattr(inline, "mime_type", None) or getattr(inline, "mimeType", None)
    return payload, mime


def generate_image(prompt: str, *, filename_hint: str | None = None) -> dict:
    """
    Generate an image directly using Gemini 2.5 Flash Image and save it under static/generated.
    Returns: {"url": "/static/generated/<file>"}.
    """
    if not prompt or not isinstance(prompt, str):
        raise Exception("prompt is required")

    response = _client.models.generate_content(
        model=GEMINI_IMAGE_MODEL,
        contents=[prompt.strip()],
    )

    image_bytes: bytes | None = None
    mime_type: str | None = None
    for part in _extract_parts(response):
        inline = _inline_data(part)
        payload, mime = _inline_bytes(inline)
        if payload:
            image_bytes = payload
            mime_type = mime
            break

    if not image_bytes:
        raise Exception("Gemini did not return an image for this prompt")

    ext = _ext_from_mime(mime_type)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    prefix = (filename_hint or "img").strip() or "img"
    safe_prefix = "".join(ch for ch in prefix if ch.isalnum() or ch in ("-", "_"))[:40] or "img"
    filename = f"{safe_prefix}_{int(time.time())}_{uuid.uuid4().hex}.{ext}"
    filepath = GENERATED_DIR / filename
    filepath.write_bytes(image_bytes)
    return {"url": f"/static/generated/{filename}"}

