from fastapi import FastAPI


app = FastAPI(
    title="ModelNest API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Return a minimal liveness response."""
    return {"status": "ok", "service": "modelnest"}
