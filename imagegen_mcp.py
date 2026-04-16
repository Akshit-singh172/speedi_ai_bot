from __future__ import annotations

from pathlib import Path
import base64
import os
import time
import uuid

from mcp_stdio import mcp_client


STATIC_DIR = Path(__file__).resolve().parent / "static"
GENERATED_DIR = STATIC_DIR / "generated"

GEMINI_IMAGE_TOOL = "image.generate.gemini"
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"


def _ext_from_mime(mime_type: str | None) -> str:
    mime = (mime_type or "").lower().strip()
    if mime in ("image/jpeg", "image/jpg"):
        return "jpg"
    if mime == "image/webp":
        return "webp"
    return "png"


def _toggle_models_prefix(model: str) -> str | None:
    value = (model or "").strip()
    if not value:
        return None
    if value.startswith("models/") and len(value) > len("models/"):
        return value[len("models/") :]
    if "/" not in value:
        return f"models/{value}"
    return None


_TOOL_CHECKED = False


def _ensure_tool_exists() -> None:
    global _TOOL_CHECKED
    if _TOOL_CHECKED:
        return
    tools = mcp_client().list_tools()
    names = {t.get("name") for t in tools}
    if GEMINI_IMAGE_TOOL not in names:
        available = ", ".join(sorted(n for n in names if isinstance(n, str)))
        raise Exception(
            f"ImageGen MCP tool '{GEMINI_IMAGE_TOOL}' not found. Available tools: {available or '(none)'}"
        )
    _TOOL_CHECKED = True


def generate_image(prompt: str, *, filename_hint: str | None = None) -> dict:
    """
    Generate an image using the ImageGen MCP server (Gemini/Nano Banana).
    Returns: {"url": "/static/generated/<file>"}.
    """
    if not prompt or not isinstance(prompt, str):
        raise Exception("prompt is required")

    _ensure_tool_exists()

    arguments: dict = {"prompt": prompt.strip(), "returnBase64": True}
    arguments["model"] = GEMINI_IMAGE_MODEL
    if filename_hint:
        arguments["filenameHint"] = str(filename_hint).strip()

    def _call(args: dict) -> dict:
        return mcp_client().call_tool(GEMINI_IMAGE_TOOL, args)

    result = _call(arguments)
    content = result.get("content") or []
    if bool(result.get("isError")):
        text = next((c.get("text") for c in content if c.get("type") == "text"), None) or ""
        message = text or "Image generation failed"

        if "unexpected model name format" in message.lower():
            alternate = _toggle_models_prefix(GEMINI_IMAGE_MODEL)
            if alternate and alternate != GEMINI_IMAGE_MODEL:
                retry_args = dict(arguments)
                retry_args["model"] = alternate
                retry = _call(retry_args)
                retry_content = retry.get("content") or []
                if not bool(retry.get("isError")):
                    result = retry
                    content = retry_content
                else:
                    retry_text = next(
                        (c.get("text") for c in retry_content if c.get("type") == "text"), None
                    )
                    raise Exception(retry_text or message)
            else:
                raise Exception(message)
        else:
            raise Exception(message)

    image_part = next((c for c in content if c.get("type") == "image" and c.get("data")), None)
    if not image_part:
        raise Exception("ImageGen MCP returned no image data")

    image_bytes = base64.b64decode(image_part["data"])
    ext = _ext_from_mime(image_part.get("mimeType"))

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"img_{int(time.time())}_{uuid.uuid4().hex}.{ext}"
    filepath = GENERATED_DIR / filename
    filepath.write_bytes(image_bytes)
    return {"url": f"/static/generated/{filename}"}
