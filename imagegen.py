from __future__ import annotations

from imagegen_mcp import generate_image as _generate_image_mcp
from gemini_image import generate_image as _generate_image_gemini


def generate_image(prompt: str, *, filename_hint: str | None = None) -> dict:
    """
    Prefer ImageGen MCP server. If it can't be started, fall back to direct Gemini image generation.
    """
    try:
        return _generate_image_mcp(prompt, filename_hint=filename_hint)
    except Exception as e:
        message = str(e).lower()
        if (
            "imagegen mcp server not found" in message
            or "mcp tool" in message
            or "access is denied" in message
            or "permission denied" in message
        ):
            return _generate_image_gemini(prompt, filename_hint=filename_hint)
        raise

