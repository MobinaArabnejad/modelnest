from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str
    secret_key: str
    storage_dir: Path
    bootstrap_token: str | None = None
    access_token_minutes: int = 60
    max_upload_bytes: int = 10 * 1024 * 1024

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            environment=os.getenv("MODELNEST_ENV", "development"),
            database_url=os.getenv("MODELNEST_DATABASE_URL", "sqlite:///./modelnest.db"),
            secret_key=os.getenv("MODELNEST_SECRET_KEY") or secrets.token_urlsafe(48),
            storage_dir=Path(os.getenv("MODELNEST_STORAGE_DIR", "./data/artifacts")),
            bootstrap_token=os.getenv("MODELNEST_BOOTSTRAP_TOKEN"),
            access_token_minutes=int(os.getenv("MODELNEST_ACCESS_TOKEN_MINUTES", "60")),
            max_upload_bytes=int(os.getenv("MODELNEST_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))),
        )

    def validate(self) -> None:
        if self.environment.lower() == "production":
            if len(self.secret_key) < 32:
                raise RuntimeError(
                    "MODELNEST_SECRET_KEY must be a random value of at least 32 characters "
                    "in production"
                )
            if self.bootstrap_token is None or len(self.bootstrap_token) < 20:
                raise RuntimeError(
                    "MODELNEST_BOOTSTRAP_TOKEN must contain at least 20 characters in production"
                )
