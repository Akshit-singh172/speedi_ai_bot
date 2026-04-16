from __future__ import annotations

from imagegen import generate_image


def handle_tool_call(tool_name: str, args: dict | None) -> dict:
    args = args or {}

    if tool_name == "generate_image":
        prompt = args.get("prompt")
        filename_hint = args.get("filename_hint") or args.get("filenameHint")

        image = generate_image(prompt, filename_hint=filename_hint)
        return {
            "type": "image",
            "message": "Generated an image.",
            "data": [image],
        }

    raise Exception(f"Unknown tool: {tool_name}")
