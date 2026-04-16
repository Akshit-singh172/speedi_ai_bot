# Speedi AI Bot

This repo runs a Flask server that exposes a chat API **and** serves a local web UI at the same localhost port.

## Quick start

1) Create a `.env` file (copy from `.env.example`) and set:
- `GEMINI_API_KEY` (required)
- Image generation is done via **ImageGen MCP Server** (Gemini/Nano Banana) (see `.env.example`):
  - Configure how to run the MCP server (`IMAGEGEN_MCP_COMMAND`, `IMAGEGEN_MCP_ARGS`, optional `IMAGEGEN_MCP_CWD`)
  - Image model used: `gemini-2.5-flash-image`
  - If the MCP server can’t be started, the app falls back to direct Gemini image generation (no Node needed)

2) Install deps (Windows):
- Run `setup.bat`

3) (For images) Install ImageGen MCP server (Node.js + npm required):
- `npm install -g imagegen-mcp-server`
  - Then set `IMAGEGEN_MCP_COMMAND=imagegen-mcp-server` in `.env`

4) Start the server:
- `python main.py`

5) Open the UI:
- `http://localhost:5000/`

## API (for other projects)

- `POST /chat` (kept for backwards compatibility)
- `POST /api/chat` (preferred alias)
- `GET /api/health`
- `POST /api/reset`

### Request body

```json
{ "message": "hello", "user_id": "any-stable-id" }
```

### Response

```json
{ "reply": { "type": "message", "data": "..." } }
```

If an image is generated, the reply type is `image` and `data` contains URLs under `/static/generated/...`.
