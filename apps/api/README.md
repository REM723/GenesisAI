# apps/api — GenesisAI backend

FastAPI service: auth, request validation, rate limiting, run lifecycle (per SRS §2).
Phase 0 ships only `/health`; features land in later phases.

## Run

```bash
pip install -e apps/api -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000   # from apps/api/
```

## Test

```bash
pytest            # from repo root; config in root pyproject.toml
```
