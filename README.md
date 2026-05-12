# PersonaVLM POC

Proof-of-concept implementation of [PersonaVLM: Long-Term Personalized Multimodal LLMs](https://www.alphaxiv.org/abs/2604.13074).

Demonstrates the 3 core capabilities — **Remembering**, **Reasoning**, **Response Alignment** — as a FastAPI service backed by SQLite.

## Quick Start

```bash
uv venv && source .venv/bin/activate
uv pip install fastapi uvicorn httpx pydantic
uvicorn api:app --port 8090
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Service info + endpoint list |
| `/demo/seed` | POST | Create demo user with realistic memories |
| `/demo/full_pipeline` | POST | Run full Remember → Reason → Align pipeline |
| `/remember` | POST | Store a memory (Capability 1) |
| `/reason` | POST | Query reasoning over accumulated memories (Capability 2) |
| `/align` | POST | Align draft response to user patterns (Capability 3) |
| `/users` | GET | List all users with memory counts |
| `/memories/{user_id}` | GET | Retrieve memories for a user |
