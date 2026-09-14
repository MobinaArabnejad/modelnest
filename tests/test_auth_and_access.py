from conftest import login_headers, register
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_registration_roles_and_admin_boundary(client: TestClient) -> None:
    admin = register(client, "AdminUser")
    regular = register(client, "RegularUser")

    assert admin.status_code == 201
    assert admin.json()["role"] == "admin"
    assert regular.status_code == 201
    assert regular.json()["role"] == "user"
    assert register(client, "regularuser").status_code == 409

    regular_headers = login_headers(client, "regularuser")
    assert client.get("/api/admin/users", headers=regular_headers).status_code == 403

    admin_headers = login_headers(client, "adminuser")
    users = client.get("/api/admin/users", headers=admin_headers)
    assert users.status_code == 200
    assert len(users.json()) == 2


def test_private_project_requires_owner_or_share(client: TestClient) -> None:
    register(client, "owner")
    register(client, "viewer")
    owner_headers = login_headers(client, "owner")
    viewer_headers = login_headers(client, "viewer")

    created = client.post(
        "/api/models",
        headers=owner_headers,
        json={"name": "private-model", "visibility": "private"},
    )
    project_id = created.json()["id"]

    assert client.get(f"/api/models/{project_id}", headers=viewer_headers).status_code == 404
    shared = client.post(
        f"/api/models/{project_id}/share",
        headers=owner_headers,
        json={"username": "viewer", "can_infer": True},
    )
    assert shared.status_code == 200
    assert client.get(f"/api/models/{project_id}", headers=viewer_headers).status_code == 200
    assert (
        client.patch(
            f"/api/models/{project_id}", headers=viewer_headers, json={"name": "stolen"}
        ).status_code
        == 403
    )


def test_production_requires_bootstrap_token(tmp_path) -> None:
    settings = Settings(
        environment="production",
        database_url=f"sqlite:///{tmp_path / 'production.db'}",
        secret_key="production-secret-key-with-more-than-thirty-two-characters",
        bootstrap_token="one-time-bootstrap-token",
        storage_dir=tmp_path / "artifacts",
    )
    with TestClient(create_app(settings)) as production_client:
        denied = production_client.post(
            "/api/auth/register", json={"username": "owner", "password": "secure-password"}
        )
        assert denied.status_code == 403

        created = production_client.post(
            "/api/auth/register",
            json={
                "username": "owner",
                "password": "secure-password",
                "bootstrap_token": "one-time-bootstrap-token",
            },
        )
        assert created.status_code == 201
        assert created.json()["role"] == "admin"


def test_default_environment_requires_bootstrap_token(tmp_path) -> None:
    settings = Settings(
        environment="development",
        database_url=f"sqlite:///{tmp_path / 'development.db'}",
        secret_key="development-secret-key-with-more-than-thirty-two-characters",
        bootstrap_token="development-bootstrap-token-12345",
        storage_dir=tmp_path / "artifacts",
    )
    with TestClient(create_app(settings)) as development_client:
        denied = development_client.post(
            "/api/auth/register", json={"username": "owner", "password": "secure-password"}
        )
        assert denied.status_code == 403

        created = development_client.post(
            "/api/auth/register",
            json={
                "username": "owner",
                "password": "secure-password",
                "bootstrap_token": "development-bootstrap-token-12345",
            },
        )
        assert created.status_code == 201
        assert created.json()["role"] == "admin"
