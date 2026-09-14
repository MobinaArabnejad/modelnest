# ModelNest

ModelNest is a self-hosted ML model manager and inference API built with FastAPI.

## Planned capabilities

- User accounts and role-based access control
- Private and public model projects
- Model files and version metadata
- API keys for inference requests
- Dataset upload and export
- Optional remote model import with strict URL validation
- Docker-based local deployment

## Development status

This repository is an initial scaffold. The first milestone is authentication and model metadata CRUD; inference and file storage will be added only after the basic security tests are in place.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The health endpoint is available at `http://127.0.0.1:8000/health`.

## Security

Please read [SECURITY.md](SECURITY.md). Never commit passwords, API keys, model files containing sensitive data, or production secrets.

## License

MIT. Add your name and year before the first public release.
