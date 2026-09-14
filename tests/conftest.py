from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path) -> Generator[TestClient, None, None]:
    settings = Settings(
        environment="testing",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        secret_key="test-secret-key-with-more-than-thirty-two-characters",
        storage_dir=tmp_path / "artifacts",
        access_token_minutes=5,
        max_upload_bytes=1024 * 1024,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def register(client: TestClient, username: str, password: str = "correct-horse-battery"):
    return client.post("/api/auth/register", json={"username": username, "password": password})


def login_headers(
    client: TestClient, username: str, password: str = "correct-horse-battery"
) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
