from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import Request, User
from app.services.maintenance import run_maintenance


@pytest.fixture
def setup(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as db:
            yield db

    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    def register(name, email, admin=False):
        response = client.post("/api/v1/auth/register", json={"name": name, "email": email, "password": "strong-password-123"})
        assert response.status_code == 201, response.text
        if admin:
            with Session(engine) as db:
                account = db.scalar(select(User).where(User.email == email))
                account.role = "ADMIN"
                db.commit()
        return {"Authorization": f"Bearer {response.json()['token']}"}

    yield client, register, engine
    app.dependency_overrides.clear()
    engine.dispose()


def advance_to_verification(client, admin, request_id):
    for status in ("UNDERSTANDING", "VALIDATION", "VERIFICATION"):
        response = client.post(f"/api/v1/admin/requests/{request_id}/transition", headers=admin, json={"to_status": status, "reason": "Operator reviewed the report"})
        assert response.status_code == 200, response.text


def test_logout_revokes_only_the_current_session(setup):
    client, register, _ = setup
    first = register("Session Citizen", "session@example.org")
    second_response = client.post("/api/v1/auth/login", json={"email": "session@example.org", "password": "strong-password-123"})
    assert second_response.status_code == 200
    second = {"Authorization": f"Bearer {second_response.json()['token']}"}
    assert first != second
    assert client.post("/api/v1/auth/logout", headers=first).status_code == 200
    assert client.get("/api/v1/auth/me", headers=first).status_code == 401
    assert client.get("/api/v1/auth/me", headers=second).status_code == 200


def test_private_search_public_sanitization_and_policy(setup):
    client, register, _ = setup
    owner = register("Issue Owner", "owner2@example.org")
    stranger = register("Other Citizen", "other2@example.org")
    admin = register("Policy Admin", "admin2@example.org", admin=True)
    private = client.post("/api/v1/requests", headers=owner, json={"category": "COMMUNITY", "description": "A broken streetlight by the bridge", "location_text": "North bridge area", "latitude": 10.12345, "longitude": 76.12345, "details": {"issue_type": "streetlight"}})
    assert private.status_code == 201, private.text
    public = client.post("/api/v1/requests", headers=owner, json={"category": "COMMUNITY", "description": "Overflowing garbage beside the station", "location_text": "Central station", "latitude": 10.12345, "longitude": 76.12345, "visibility_scope": "PUBLIC", "details": {"issue_type": "garbage"}})
    assert public.status_code == 201, public.text
    assert client.get("/api/v1/public/issues").json() == []
    assert client.get("/api/v1/public/summary").json()["verified_public_issues"] == 0
    public_id = public.json()["id"]
    advance_to_verification(client, admin, public_id)
    approved = client.post(f"/api/v1/admin/requests/{public_id}/verify", headers=admin, json={"decision": "VERIFIED", "reason": "Checked with the request owner"})
    assert approved.status_code == 200, approved.text
    items = client.get("/api/v1/public/issues").json()
    assert len(items) == 1 and items[0]["issue_type"] == "garbage"
    assert client.get("/api/v1/public/summary").json()["verified_public_issues"] == 1
    assert items[0]["latitude"] == 10.1 and "description" not in items[0] and "location_text" not in items[0]
    assert client.get(f"/api/v1/requests/{private.json()['id']}", headers=stranger).status_code == 404
    search = client.get("/api/v1/search?q=streetlight", headers=stranger)
    assert search.status_code == 200 and search.json()["requests"] == []
    candidate = client.post("/api/v1/requests/duplicates", headers=stranger, json={"category": "COMMUNITY", "description": "Overflowing garbage beside the station again", "location_text": "Central station", "latitude": 10.12, "longitude": 76.12})
    assert candidate.status_code == 200 and candidate.json()["count"] == 1
    assert candidate.json()["matches"][0]["id"] == public_id
    similar = client.post("/api/v1/requests", headers=stranger, json={"category": "COMMUNITY", "description": "Overflowing garbage beside the station again", "location_text": "Central station", "latitude": 10.12, "longitude": 76.12})
    assert similar.status_code == 201, similar.text
    confirmed = client.post(f"/api/v1/requests/{similar.json()['id']}/duplicates/{public_id}/confirm", headers=stranger)
    assert confirmed.status_code == 200 and confirmed.json()["status"] == "DUPLICATE"
    config = client.get("/api/v1/admin/config", headers=admin).json()
    config["pilot_enabled"] = True
    config["pilot_categories"] = ["FOOD"]
    assert client.put("/api/v1/admin/config", headers=admin, json=config).status_code == 200
    denied = client.post("/api/v1/requests", headers=owner, json={"category": "COMMUNITY", "description": "A second issue near the station", "location_text": "Central station"})
    assert denied.status_code == 409
    assert client.put("/api/v1/admin/config", headers=owner, json=config).status_code == 403


def test_resource_patch_and_evidence_strips_exif(setup):
    client, register, _ = setup
    owner = register("Resource Owner", "resource2@example.org")
    citizen = register("Evidence Citizen", "evidence2@example.org")
    org = client.post("/api/v1/organizations", headers=owner, json={"name": "Community Support Office", "service_area": "South district", "service_categories": ["COMMUNITY"]})
    assert org.status_code == 201, org.text
    resource = client.post(f"/api/v1/organizations/{org.json()['id']}/resources", headers=owner, json={"title": "Repair team", "category": "COMMUNITY", "capacity": 10, "current_workload": 3, "service_radius_km": 35})
    assert resource.status_code == 201, resource.text
    resource_id = resource.json()["id"]
    patched = client.patch(f"/api/v1/resources/{resource_id}", headers=owner, json={"available": False})
    assert patched.status_code == 200, patched.text
    assert patched.json()["current_workload"] == 3 and patched.json()["service_radius_km"] == 35
    assert client.patch(f"/api/v1/resources/{resource_id}", headers=owner, json={"capacity": 2}).status_code == 422
    assert client.patch(f"/api/v1/resources/{resource_id}", headers=citizen, json={"available": True}).status_code == 404
    request = client.post("/api/v1/requests", headers=citizen, json={"category": "COMMUNITY", "description": "Unsafe pothole beside the library", "location_text": "Library road"})
    assert request.status_code == 201, request.text
    request_id = request.json()["id"]
    assert client.post(f"/api/v1/requests/{request_id}/evidence", headers=citizen, files={"file": ("bad.jpg", b"not-an-image", "image/jpeg")}).status_code == 415
    assert client.post(f"/api/v1/requests/{request_id}/evidence", headers=citizen, files={"file": ("unscanned.pdf", b"%PDF-1.7\n", "application/pdf")}).status_code == 415
    image = Image.new("RGB", (10, 10), "blue")
    exif = Image.Exif()
    exif[271] = "Sensitive Camera"
    original = BytesIO()
    image.save(original, format="JPEG", exif=exif)
    uploaded = client.post(f"/api/v1/requests/{request_id}/evidence", headers=citizen, files={"file": ("photo.jpg", original.getvalue(), "image/jpeg")})
    assert uploaded.status_code == 201, uploaded.text
    downloaded = client.get(f"/api/v1/requests/{request_id}/evidence/{uploaded.json()['id']}", headers=citizen)
    assert downloaded.status_code == 200
    assert Image.open(BytesIO(downloaded.content)).getexif().get(271) is None
    assert client.get(f"/api/v1/requests/{request_id}/evidence/{uploaded.json()['id']}", headers=owner).status_code == 404


def test_overdue_requests_escalate_with_audit_and_notification(setup):
    client, register, engine = setup
    citizen = register("Overdue Citizen", "overdue@example.org")
    admin = register("Escalation Admin", "escalation-admin@example.org", admin=True)
    response = client.post("/api/v1/requests", headers=citizen, json={"category": "COMMUNITY", "description": "Blocked drainage beside the market", "location_text": "Central market"})
    assert response.status_code == 201, response.text
    request_id = response.json()["id"]
    with Session(engine) as db:
        need = db.get(Request, request_id)
        need.created_at = datetime.now(timezone.utc) - timedelta(days=2)
        db.commit()
    with Session(engine) as db:
        result = run_maintenance(db)
    assert result == {"expired": 0, "escalated": 1, "retained": 0}
    assert client.get(f"/api/v1/requests/{request_id}", headers=citizen).json()["status"] == "ESCALATED"
    notices = client.get("/api/v1/notifications", headers=citizen).json()
    assert any(item["request_id"] == request_id for item in notices)
    queue = client.get("/api/v1/admin/escalations", headers=admin)
    assert queue.status_code == 200 and queue.json()[0]["request_id"] == request_id
    follow_up = client.post(f"/api/v1/admin/requests/{request_id}/follow-up", headers=admin, json={"reason": "Issue remains unresolved after review"})
    assert follow_up.status_code == 200, follow_up.text
    assert follow_up.json()["status"] == "SUBMITTED" and follow_up.json()["owner_id"] == response.json()["owner_id"]
    repeated = client.post(f"/api/v1/admin/requests/{request_id}/follow-up", headers=admin, json={"reason": "Issue remains unresolved after review"})
    assert repeated.status_code == 200 and repeated.json()["id"] == follow_up.json()["id"]
    with Session(engine) as db:
        assert run_maintenance(db) == {"expired": 0, "escalated": 0, "retained": 0}


def test_configured_retention_scrubs_closed_request_content(setup):
    client, register, engine = setup
    citizen = register("Retention Citizen", "retention@example.org")
    admin = register("Retention Admin", "retention-admin@example.org", admin=True)
    policy = client.get("/api/v1/admin/config", headers=admin).json()
    assert policy["retention_days"] is None
    policy["retention_days"] = 30
    assert client.put("/api/v1/admin/config", headers=admin, json=policy).status_code == 200
    response = client.post("/api/v1/requests", headers=citizen, json={
        "category": "COMMUNITY", "description": "Drainage overflow near my address",
        "location_text": "Private street address", "latitude": 10.0, "longitude": 76.0,
    })
    assert response.status_code == 201, response.text
    request_id = response.json()["id"]
    image = BytesIO()
    Image.new("RGB", (8, 8), "blue").save(image, format="PNG")
    upload = client.post(f"/api/v1/requests/{request_id}/evidence", headers=citizen, files={"file": ("photo.png", image.getvalue(), "image/png")})
    assert upload.status_code == 201, upload.text
    evidence_path = Path(settings.data_dir) / "evidence" / f"{upload.json()['id']}.png"
    assert evidence_path.exists()
    assert client.post(f"/api/v1/requests/{request_id}/messages", headers=citizen, json={"body": "Private update about the location"}).status_code == 201
    assert client.post(f"/api/v1/requests/{request_id}/cancel", headers=citizen).status_code == 200
    with Session(engine) as db:
        request = db.get(Request, request_id)
        request.updated_at = datetime.now(timezone.utc) - timedelta(days=31)
        db.commit()
        assert run_maintenance(db)["retained"] == 1
        assert run_maintenance(db)["retained"] == 0
        db.refresh(request)
        assert request.retained_at is not None and request.latitude is None
    assert not evidence_path.exists()
    detail = client.get(f"/api/v1/requests/{request_id}", headers=citizen).json()
    assert detail["description"] == "[Removed under retention policy]"
    assert detail["evidence"] == []
    assert "Private update" not in str(client.get(f"/api/v1/requests/{request_id}/messages", headers=citizen).json())


def test_closed_account_can_be_anonymized_but_active_account_cannot(setup):
    client, register, _ = setup
    citizen = register("Privacy Citizen", "privacy@example.org")
    admin = register("Privacy Operator", "privacy-admin@example.org", admin=True)
    response = client.post("/api/v1/requests", headers=citizen, json={"category": "COMMUNITY", "description": "Private drainage issue behind my home", "location_text": "Specific private address", "latitude": 10.123, "longitude": 76.123})
    assert response.status_code == 201, response.text
    request_id = response.json()["id"]
    assert client.post(f"/api/v1/requests/{request_id}/messages", headers=citizen, json={"body": "My personal phone is 555-1234"}).status_code == 201
    assert client.request("DELETE", "/api/v1/auth/me", headers=citizen, json={"password": "strong-password-123"}).status_code == 409
    assert client.post(f"/api/v1/requests/{request_id}/cancel", headers=citizen).status_code == 200
    assert client.request("DELETE", "/api/v1/auth/me", headers=citizen, json={"password": "wrong-password"}).status_code == 403
    deleted = client.request("DELETE", "/api/v1/auth/me", headers=citizen, json={"password": "strong-password-123"})
    assert deleted.status_code == 200 and deleted.json()["anonymized"]
    assert client.get("/api/v1/auth/me", headers=citizen).status_code == 401
    scrubbed = client.get(f"/api/v1/requests/{request_id}", headers=admin).json()
    assert scrubbed["latitude"] is None and scrubbed["location_text"] == "Location withheld"
    assert "private drainage" not in scrubbed["description"].lower()
    messages = client.get(f"/api/v1/requests/{request_id}/messages", headers=admin).json()
    assert all("555-1234" not in item["body"] for item in messages)


def test_verified_volunteer_sees_sanitized_opportunity_and_can_express_interest(setup):
    client, register, _ = setup
    citizen = register("Opportunity Citizen", "opportunity-citizen@example.org")
    volunteer = register("Opportunity Volunteer", "opportunity-volunteer@example.org")
    admin = register("Opportunity Admin", "opportunity-admin@example.org", admin=True)
    volunteer_id = client.get("/api/v1/auth/me", headers=volunteer).json()["id"]
    assert client.post("/api/v1/auth/volunteer/apply", headers=volunteer).status_code == 200
    profile = client.patch("/api/v1/auth/me", headers=volunteer, json={"categories": ["COMMUNITY"], "available": True, "capacity": 10, "latitude": 10.0, "longitude": 76.0})
    assert profile.status_code == 200, profile.text
    need = client.post("/api/v1/requests", headers=citizen, json={"category": "COMMUNITY", "description": "Private drainage overflow beside my home", "location_text": "Exact personal address", "latitude": 10.01, "longitude": 76.01, "privacy_mode": True, "location_precision": "PRIVATE"})
    assert need.status_code == 201, need.text
    request_id = need.json()["id"]
    assert client.get("/api/v1/volunteers/opportunities", headers=volunteer).status_code == 403
    review = client.post(f"/api/v1/admin/volunteers/{volunteer_id}/verify", headers=admin, json={"decision": "VERIFIED", "reason": "Identity and capability confirmed"})
    assert review.status_code == 200, review.text
    advance_to_verification(client, admin, request_id)
    assert client.post(f"/api/v1/admin/requests/{request_id}/verify", headers=admin, json={"decision": "VERIFIED", "reason": "Owner and location confirmed"}).status_code == 200
    for stage in ("PRIORITIZATION", "MATCHING"):
        response = client.post(f"/api/v1/admin/requests/{request_id}/transition", headers=admin, json={"to_status": stage, "reason": "Verified need is ready for matching"})
        assert response.status_code == 200, response.text
    assert client.get("/api/v1/volunteers/opportunities?max_distance_km=25", headers=volunteer).json() == []
    available = client.get("/api/v1/volunteers/opportunities", headers=volunteer)
    assert available.status_code == 200 and len(available.json()) == 1
    assert client.get("/api/v1/volunteers/opportunities?page=2&limit=1", headers=volunteer).json() == []
    assert client.get("/api/v1/volunteers/opportunities?category=FOOD", headers=volunteer).json() == []
    assert client.get("/api/v1/volunteers/opportunities?urgency=NOT_VALID", headers=volunteer).status_code == 422
    assert "description" not in available.json()[0] and "location_text" not in available.json()[0]
    assert available.json()[0]["distance_km"] is None
    assert available.json()[0]["approximate_latitude"] is None
    assert available.json()[0]["approximate_longitude"] is None
    assert client.get("/api/v1/volunteers/opportunities", headers=citizen).status_code == 403
    interest = client.post(f"/api/v1/volunteers/opportunities/{request_id}/interest", headers=volunteer, json={"note": "Can attend this afternoon"})
    assert interest.status_code == 200 and interest.json()["interested"]
    assert client.post(f"/api/v1/volunteers/opportunities/{request_id}/interest", headers=volunteer, json={}).json()["id"] == interest.json()["id"]
    staff_interests = client.get(f"/api/v1/admin/requests/{request_id}/interests", headers=admin)
    assert staff_interests.status_code == 200 and staff_interests.json()[0]["volunteer_id"] == volunteer_id
    matches = client.get(f"/api/v1/matching/{request_id}", headers=admin)
    assert matches.status_code == 200 and any(item.get("interested") for item in matches.json())
