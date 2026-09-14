from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings
from app.database import Base, create_session_factory
from app.routes import admin, api_keys, auth, inference, projects


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        active_settings.validate()
        active_settings.storage_dir.mkdir(parents=True, exist_ok=True)
        engine, session_factory = create_session_factory(active_settings.database_url)
        Base.metadata.create_all(engine)
        application.state.settings = active_settings
        application.state.session_factory = session_factory
        yield
        engine.dispose()

    application = FastAPI(
        title="ModelNest API",
        version="0.1.0",
        description="Secure, self-hosted model storage and constrained inference.",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    application.include_router(auth.router)
    application.include_router(admin.router)
    application.include_router(api_keys.router)
    application.include_router(projects.router)
    application.include_router(inference.router)

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "modelnest"}

    return application


app = create_app()
