from fastapi.testclient import TestClient

from app.main import app


def test_http_and_validation_errors_share_an_envelope():
    client = TestClient(app)
    missing = client.get("/api/v1/does-not-exist")
    assert missing.status_code == 404
    assert missing.json() == {"error": {"code": "NOT_FOUND", "message": "Not Found"}}

    invalid = client.post("/api/v1/requests/interpret", json={"text": "short"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
    assert invalid.json()["error"]["details"]
