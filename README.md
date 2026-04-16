# Speedi AI Bot

This repo runs a Flask server that exposes a chat API **and** serves a local web UI at the same localhost port.

## Quick start

1) Create a `.env` file (copy from `.env.example`) and set:
- `GEMINI_API_KEY` (required)
- Image generation uses **Pollinations** (free, no key). Optional tuning in `.env.example`.

2) Install deps (Windows):
- Run `setup.bat`

3) Start the server:
- `python main.py`

4) Open the UI:
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
