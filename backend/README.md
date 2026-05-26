# Backend (FastAPI)

AI-powered Kubernetes log analyzer + remediation actions.

## Running locally
- Requires a Kubernetes config (for log access) OR mock mode.

Commands (recommended with uv/poetry):
- `poetry install`
- `poetry run uvicorn ai_self_healing_backend.app.main:app --reload --port 9000`

