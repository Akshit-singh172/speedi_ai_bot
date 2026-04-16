from __future__ import annotations

from pathlib import Path
from urllib.parse import quote
import os
import time
import uuid

import requests


STATIC_DIR = Path(__file__).resolve().parent / "static"
GENERATED_DIR = STATIC_DIR / "generated"

POLLINATIONS_BASE_URL = "https://gen.pollinations.ai/image"
POLLINATIONS_MODEL = os.getenv("POLLINATIONS_IMAGE_MODEL", "flux").strip() or "flux"
POLLINATIONS_TIMEOUT_S = float(os.getenv("POLLINATIONS_TIMEOUT_S", "60"))


def _ext_from_mime(mime_type: str | None) -> str:
    mime = (mime_type or "").split(";", 1)[0].lower().strip()
    if mime in ("image/jpeg", "image/jpg"):
        return "jpg"
    if mime == "image/webp":
        return "webp"
    return "png"


def generate_image(prompt: str, *, filename_hint: str | None = None) -> dict:
    """
    Generate an image using the free Pollinations API and save it under static/generated.
    Returns: {"url": "/static/generated/<file>"}.
    """
    if not prompt or not isinstance(prompt, str):
        raise Exception("prompt is required")

    url = f"{POLLINATIONS_BASE_URL}/{quote(prompt.strip())}"
    params = {
        "model": POLLINATIONS_MODEL,
        "seed": -1,
        "width": 1024,
        "height": 1024,
        "safe": "true",
    }

    response = requests.get(url, params=params, timeout=POLLINATIONS_TIMEOUT_S)
    if not response.ok:
        raise Exception(f"Pollinations image request failed (HTTP {response.status_code})")

    content_type = response.headers.get("Content-Type")
    ext = _ext_from_mime(content_type)

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    prefix = (filename_hint or "img").strip() or "img"
    safe_prefix = "".join(ch for ch in prefix if ch.isalnum() or ch in ("-", "_"))[:40] or "img"
    filename = f"{safe_prefix}_{int(time.time())}_{uuid.uuid4().hex}.{ext}"
    filepath = GENERATED_DIR / filename
    filepath.write_bytes(response.content)
    return {"url": f"/static/generated/{filename}"}
