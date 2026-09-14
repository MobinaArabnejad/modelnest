# ModelNest

ModelNest is a self-hosted ML model manager and inference API built with FastAPI. It provides model projects, versioned artifacts, access controls, API keys, and constrained inference without loading executable Python model files.

## Features

- JWT authentication with Argon2 password hashing
- First-user administrator bootstrap and server-side role enforcement
- Public/private model projects and per-user sharing
- Versioned `.json`, `.onnx`, and `.safetensors` artifact storage
- Upload size limits, randomized storage names, and SHA-256 checksums
- Revocable API keys stored only as hashes
- Linear JSON model inference using JWT or API-key authentication
- SQLite for local development and PostgreSQL through Docker Compose
- Automated tests, linting, Dependabot, and a security policy

ModelNest never deserializes pickle, joblib, or arbitrary Python objects. ONNX and Safetensors files can be stored, but automatic inference is limited to the documented linear JSON format.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`. Local development defaults to SQLite.

## Run with Docker

Copy `.env.example` to `.env`, replace both secrets, and then run:

```text
docker compose up --build
```

For a deployment, set `MODELNEST_ENV=production` and replace both secrets with strong values. The bootstrap token is required when registering the first administrator in every environment; it prevents an unauthenticated user from claiming a fresh instance.

## API workflow

1. `POST /api/auth/register` with `bootstrap_token` — the first account becomes an administrator only when the configured bootstrap token is supplied.
2. `POST /api/auth/login` — obtain a bearer token.
3. `POST /api/models` — create a model project.
4. `POST /api/models/{id}/versions` — upload a model artifact as multipart form data.
5. `POST /api/keys` — create an inference API key; the full value is shown once.
6. `POST /api/models/{id}/versions/{version}/infer` — run constrained inference.

A linear JSON model uses this format:

```json
{"weights": [0.5, -1.0], "bias": 0.25}
```

An inference request uses:

```json
{"features": [2.0, 3.0]}
```

## Security

Read [SECURITY.md](SECURITY.md) before testing or reporting an issue. Test only systems and accounts you own or have explicit authorization to assess. Do not commit `.env`, API keys, passwords, private datasets, or model files containing sensitive information.

## Development

```powershell
ruff check .
pytest -q
```

## License

MIT — see [LICENSE](LICENSE).
