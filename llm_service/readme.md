# llm_service (Gemini) — Esqueleto

Servicio FastAPI con endpoints:
- `GET  /health`
- `POST /llm/to-grammar`
- `POST /llm/recurrence`
- `POST /llm/classify`
- `POST /llm/compare`

> **Sin lógica**: los métodos del proveedor levantan `NotImplementedError`.

## Local
```bash
uvicorn app.routes:app --reload --port 8003
