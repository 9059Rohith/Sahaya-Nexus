"""Isolated PostgreSQL/PostGIS lifecycle check. Requires a sahaya_qa database."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models import Resource, User


def main():
    if not settings.database_url.endswith("/sahaya_qa"):
        raise SystemExit("Refusing to write outside the isolated sahaya_qa database")
    with SessionLocal() as db:
        assert db.scalar(text("SELECT PostGIS_Version()"))
    client = TestClient(app)

    def register(name, email):
        response = client.post("/api/v1/auth/register", json={"name": name, "email": email, "password": "qa-only-password-123"})
        assert response.status_code == 201, response.text
        return {"Authorization": f"Bearer {response.json()['token']}"}

    citizen = register("QA Citizen", "qa-citizen@example.org")
    organization = register("QA Organization", "qa-organization@example.org")
    operator = register("QA Operator", "qa-operator@example.org")
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == "qa-operator@example.org"))
        admin.role = "ADMIN"
        db.commit()
    org = client.post("/api/v1/organizations", headers=organization, json={"name": "QA Food Team", "service_categories": ["FOOD"]})
    assert org.status_code == 201, org.text
    resource = client.post(f"/api/v1/organizations/{org.json()['id']}/resources", headers=organization, json={"title": "QA Meal Pickup", "category": "FOOD", "capacity": 100, "service_radius_km": 10, "latitude": 10.0, "longitude": 76.0})
    assert resource.status_code == 201, resource.text
    resource_id = resource.json()["id"]
    with SessionLocal() as db:
        assert db.scalar(text("SELECT ST_AsText(geom) FROM resources WHERE id = :id"), {"id": resource_id}) == "POINT(76 10)"
    assert client.post(f"/api/v1/admin/organizations/{org.json()['id']}/verify", headers=operator, json={"decision": "VERIFIED", "reason": "QA identity review complete"}).status_code == 200
    need = client.post("/api/v1/requests", headers=citizen, json={"category": "FOOD", "description": "I have 60 meals available for collection", "quantity": 60, "unit": "meals", "location_text": "QA collection point", "latitude": 10.01, "longitude": 76.01, "details": {"safe_until": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}})
    assert need.status_code == 201, need.text
    request_id = need.json()["id"]
    for stage in ("UNDERSTANDING", "VALIDATION", "VERIFICATION"):
        response = client.post(f"/api/v1/admin/requests/{request_id}/transition", headers=operator, json={"to_status": stage, "reason": "QA operator reviewed evidence"})
        assert response.status_code == 200, response.text
    assert client.post(f"/api/v1/admin/requests/{request_id}/verify", headers=operator, json={"decision": "VERIFIED", "reason": "QA request owner confirmed"}).status_code == 200
    for stage in ("PRIORITIZATION", "MATCHING"):
        response = client.post(f"/api/v1/admin/requests/{request_id}/transition", headers=operator, json={"to_status": stage, "reason": "QA verified request advanced"})
        assert response.status_code == 200, response.text
    matches = client.get(f"/api/v1/matching/{request_id}", headers=operator)
    assert matches.status_code == 200, matches.text
    assert matches.json()[0]["id"] == resource_id
    assigned = client.post(f"/api/v1/admin/requests/{request_id}/assign", headers=operator, json={"resource_id": resource_id, "reason": "QA spatial and capacity match"})
    assert assigned.status_code == 200, assigned.text
    with SessionLocal() as db:
        assert db.get(Resource, resource_id).current_workload == 60
    for action in ("accept", "start", "arrive"):
        response = client.post(f"/api/v1/assignments/{request_id}/{action}", headers=organization)
        assert response.status_code == 200, response.text
    completed = client.post(f"/api/v1/assignments/{request_id}/complete", headers=organization, json={"summary": "QA meals collected and distributed", "impact_value": 60, "impact_unit": "meals"})
    assert completed.status_code == 200, completed.text
    with SessionLocal() as db:
        assert db.get(Resource, resource_id).current_workload == 0
    assert client.post(f"/api/v1/requests/{request_id}/feedback", headers=citizen, json={"answer": "YES"}).status_code == 200
    assert client.post(f"/api/v1/admin/requests/{request_id}/record-impact", headers=operator).status_code == 200
    assert client.get("/api/v1/impact").json()["verified_outcomes"] == 1
    print("PostGIS and full lifecycle passed in the isolated sahaya_qa database")


if __name__ == "__main__":
    main()
