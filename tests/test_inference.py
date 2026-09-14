import json

from conftest import login_headers, register
from fastapi.testclient import TestClient


def test_upload_and_infer_with_api_key(client: TestClient) -> None:
    register(client, "modelowner")
    headers = login_headers(client, "modelowner")
    project = client.post(
        "/api/models",
        headers=headers,
        json={"name": "linear-demo", "visibility": "private"},
    ).json()

    artifact = json.dumps({"weights": [0.5, -1.0], "bias": 0.25}).encode()
    uploaded = client.post(
        f"/api/models/{project['id']}/versions",
        headers=headers,
        data={"version": "1.0.0"},
        files={"artifact": ("model.json", artifact, "application/json")},
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["artifact_format"] == "linear-json"

    created_key = client.post("/api/keys", headers=headers, json={"name": "test-key"})
    assert created_key.status_code == 201
    raw_key = created_key.json()["key"]

    result = client.post(
        f"/api/models/{project['id']}/versions/1.0.0/infer",
        headers={"X-API-Key": raw_key},
        json={"features": [2.0, 3.0]},
    )
    assert result.status_code == 200
    assert result.json()["output"] == -1.75

    wrong_shape = client.post(
        f"/api/models/{project['id']}/versions/1.0.0/infer",
        headers={"X-API-Key": raw_key},
        json={"features": [2.0]},
    )
    assert wrong_shape.status_code == 422

    key_id = created_key.json()["id"]
    assert client.delete(f"/api/keys/{key_id}", headers=headers).status_code == 204
    assert (
        client.post(
            f"/api/models/{project['id']}/versions/1.0.0/infer",
            headers={"X-API-Key": raw_key},
            json={"features": [2.0, 3.0]},
        ).status_code
        == 401
    )


def test_rejects_invalid_and_oversized_artifacts(client: TestClient) -> None:
    register(client, "uploader")
    headers = login_headers(client, "uploader")
    project_id = client.post(
        "/api/models",
        headers=headers,
        json={"name": "validation-demo", "visibility": "private"},
    ).json()["id"]

    invalid = client.post(
        f"/api/models/{project_id}/versions",
        headers=headers,
        data={"version": "invalid-json"},
        files={"artifact": ("model.json", b'{"weights": [NaN]}', "application/json")},
    )
    assert invalid.status_code == 422

    oversized = client.post(
        f"/api/models/{project_id}/versions",
        headers=headers,
        data={"version": "too-large"},
        files={
            "artifact": (
                "model.onnx",
                b"x" * (1024 * 1024 + 1),
                "application/octet-stream",
            )
        },
    )
    assert oversized.status_code == 413
