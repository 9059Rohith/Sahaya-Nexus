from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Resource, User


def test_food_request_to_verified_impact():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    def register(name, email):
        response = client.post(
            "/api/v1/auth/register",
            json={"name": name, "email": email, "password": "long-password-123"},
        )
        assert response.status_code == 201, response.text
        return {"Authorization": f"Bearer {response.json()['token']}"}

    try:
        citizen = register("Citizen One", "citizen@example.org")
        org_owner = register("Food Team", "food@example.org")
        admin = register("Operator One", "admin@example.org")
        stranger = register("Other Person", "other@example.org")
        member = register("Collection Member", "member@example.org")
        with Session(engine) as db:
            account = db.scalar(select(User).where(User.email == "admin@example.org"))
            account.role = "ADMIN"
            db.commit()

        org = client.post(
            "/api/v1/organizations",
            headers=org_owner,
            json={"name": "Actual Food Group", "description": "Collects surplus meals"},
        ).json()
        assert org["status"] == "UNDER_REVIEW"
        resource = client.post(
            f"/api/v1/organizations/{org['id']}/resources",
            headers=org_owner,
            json={
                "title": "Meal pickup",
                "category": "FOOD",
                "capacity": 100,
                "available": True,
                "latitude": 10.0,
                "longitude": 76.0,
            },
        ).json()
        history_path = f"/api/v1/resources/{resource['id']}/capacity-history"
        assert len(client.get(history_path, headers=org_owner).json()) == 1
        assert client.get(history_path, headers=stranger).status_code == 404
        assert client.get("/api/v1/resources").json() == []
        response = client.post(
            f"/api/v1/admin/organizations/{org['id']}/verify",
            headers=admin,
            json={"decision": "VERIFIED", "reason": "Identity and service checked"},
        )
        assert response.status_code == 200, response.text
        invitation = client.post(f"/api/v1/organizations/{org['id']}/members", headers=org_owner, json={"email": "member@example.org"})
        assert invitation.status_code == 201, invitation.text
        invitation_id = invitation.json()["id"]
        assert client.get(f"/api/v1/organizations/{org['id']}/resources", headers=member).status_code == 404
        assert client.post(f"/api/v1/organizations/invitations/{invitation_id}/accept", headers=stranger).status_code == 404
        assert client.post(f"/api/v1/organizations/invitations/{invitation_id}/accept", headers=member).status_code == 200
        assert client.get(f"/api/v1/organizations/{org['id']}/resources", headers=member).status_code == 200
        assert client.get("/api/v1/organizations/mine", headers=member).json()[0]["membership_role"] == "MEMBER"
        public_resources = client.get("/api/v1/resources?category=FOOD&sort=capacity&limit=1")
        assert public_resources.status_code == 200 and public_resources.json()[0]["id"] == resource["id"]
        assert client.get("/api/v1/resources?sort=invalid").status_code == 422
        assert client.get("/api/v1/search?q=Meal", headers=citizen).json()["resources"][0]["id"] == resource["id"]
        assert client.patch(f"/api/v1/resources/{resource['id']}", headers=org_owner, json={"available": False}).status_code == 200
        assert client.get("/api/v1/search?q=Meal", headers=citizen).json()["resources"] == []
        assert client.patch(f"/api/v1/resources/{resource['id']}", headers=org_owner, json={"available": True}).status_code == 200

        interpreted = client.post(
            "/api/v1/requests/interpret",
            json={"text": "I have 60 meals available until tonight"},
        ).json()
        assert interpreted["category"] == "FOOD" and interpreted["quantity"] == 60
        submission = {
                "client_submission_id": "41ebf1cb-77ac-4bb2-a93a-1a41af4554b3",
                "category": "FOOD",
                "description": "I have 60 meals available until tonight",
                "quantity": 60,
                "unit": "meals",
                "location_text": "Central Kochi",
                "latitude": 10.01,
                "longitude": 76.01,
                "details": {"safe_until": "2027-01-01T20:00:00"},
            }
        response = client.post("/api/v1/requests", headers=citizen, json=submission)
        assert response.status_code == 201, response.text
        need = response.json()
        request_id = need["id"]
        retry = client.post("/api/v1/requests", headers=citizen, json=submission)
        assert retry.status_code == 201 and retry.json()["id"] == request_id
        assert len(retry.json()["events"]) == 1
        changed = client.post("/api/v1/requests", headers=citizen, json={**submission, "description": "A different food request for 60 people"})
        assert changed.status_code == 409
        filtered = client.get("/api/v1/requests?category=FOOD&sort=urgency&limit=1", headers=citizen)
        assert filtered.status_code == 200 and filtered.json()[0]["id"] == request_id
        assert client.get("/api/v1/requests?sort=invalid", headers=citizen).status_code == 422
        staff_queue = client.get("/api/v1/admin/queue?category=FOOD&sort=oldest&limit=1", headers=admin)
        assert staff_queue.status_code == 200 and staff_queue.json()[0]["id"] == request_id
        sent = client.post(f"/api/v1/requests/{request_id}/messages", headers=citizen, json={"body": "The meals are ready at the collection desk."})
        assert sent.status_code == 201, sent.text
        assert client.get(f"/api/v1/requests/{request_id}/messages", headers=stranger).status_code == 404
        assert client.post(f"/api/v1/requests/{request_id}/messages", headers=stranger, json={"body": "Unauthorized message"}).status_code == 404
        assert (
            client.get(f"/api/v1/requests/{request_id}", headers=stranger).status_code
            == 404
        )
        assert client.get("/api/v1/impact").json()["verified_outcomes"] == 0
        for stage in ("UNDERSTANDING", "VALIDATION", "VERIFICATION"):
            response = client.post(
                f"/api/v1/admin/requests/{request_id}/transition",
                headers=admin,
                json={"to_status": stage, "reason": "Reviewed request information"},
            )
            assert response.status_code == 200, response.text
        assert (
            client.post(
                f"/api/v1/admin/requests/{request_id}/transition",
                headers=admin,
                json={"to_status": "PRIORITIZATION", "reason": "Premature transition"},
            ).status_code
            == 409
        )
        assert (
            client.post(
                f"/api/v1/admin/requests/{request_id}/verify",
                headers=admin,
                json={"decision": "VERIFIED", "reason": "Confirmed with request owner"},
            ).status_code
            == 200
        )
        for stage in ("PRIORITIZATION", "MATCHING"):
            response = client.post(
                f"/api/v1/admin/requests/{request_id}/transition",
                headers=admin,
                json={"to_status": stage, "reason": "Reviewed available evidence"},
            )
            assert response.status_code == 200, response.text
        original_weights = client.get(
            "/api/v1/admin/matching-settings", headers=admin
        ).json()["weights"]
        assert abs(sum(original_weights.values()) - 1) < 0.001
        assert (
            client.post(
                "/api/v1/admin/matching-settings",
                headers=citizen,
                json=original_weights,
            ).status_code
            == 403
        )
        changed_weights = {**original_weights, "distance": 0.20, "category_match": 0.22}
        assert (
            client.post(
                "/api/v1/admin/matching-settings", headers=admin, json=changed_weights
            ).status_code
            == 200
        )
        override = client.post(
            f"/api/v1/admin/requests/{request_id}/priority",
            headers=admin,
            json={
                "urgency": "HIGH",
                "reason": "Collection must happen before food expires",
            },
        )
        assert override.status_code == 200 and override.json()["urgency"] == "HIGH"
        matches = client.get(f"/api/v1/matching/{request_id}", headers=admin).json()
        assert matches[0]["id"] == resource["id"]
        assert matches[0]["weights"] == changed_weights
        response = client.post(
            f"/api/v1/admin/requests/{request_id}/assign",
            headers=admin,
            json={
                "resource_id": resource["id"],
                "reason": "Verified capacity and service area",
            },
        )
        assert response.status_code == 200, response.text
        with Session(engine) as db:
            assert db.get(Resource, resource["id"]).current_workload == 60
        assert client.get(f"/api/v1/requests/{request_id}", headers=member).status_code == 200
        assert client.request("DELETE", f"/api/v1/organizations/{org['id']}/members/{invitation.json()['user_id']}", headers=org_owner).status_code == 200
        assert client.get(f"/api/v1/requests/{request_id}", headers=member).status_code == 404
        reserved = client.get(history_path, headers=org_owner).json()
        assert reserved[0]["workload"] == 60 and reserved[0]["previous_workload"] == 0
        reply = client.post(f"/api/v1/requests/{request_id}/messages", headers=org_owner, json={"body": "Our collection team is on the way."})
        assert reply.status_code == 201, reply.text
        conversation = client.get(f"/api/v1/requests/{request_id}/messages", headers=citizen)
        assert conversation.status_code == 200 and len(conversation.json()) == 2
        notices = client.get("/api/v1/notifications", headers=citizen).json()
        assert any(item["kind"] == "REQUEST_MESSAGE" and item["request_id"] == request_id for item in notices)
        assert (
            client.post(
                f"/api/v1/assignments/{request_id}/accept", headers=org_owner
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/v1/assignments/{request_id}/start", headers=org_owner
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/v1/assignments/{request_id}/arrive", headers=org_owner
            ).status_code
            == 200
        )
        response = client.post(
            f"/api/v1/assignments/{request_id}/complete",
            headers=org_owner,
            json={
                "summary": "Collected and distributed meals",
                "impact_value": 60,
                "impact_unit": "meals",
            },
        )
        assert response.status_code == 200, response.text
        assert client.get("/api/v1/impact").json()["verified_outcomes"] == 0
        with Session(engine) as db:
            assert db.get(Resource, resource["id"]).current_workload == 0
        released = client.get(history_path, headers=org_owner).json()
        assert released[0]["workload"] == 0 and released[0]["previous_workload"] == 60
        assert (
            client.post(
                f"/api/v1/requests/{request_id}/outcome/confirm", headers=stranger
            ).status_code
            == 404
        )
        feedback = client.post(
            f"/api/v1/requests/{request_id}/feedback",
            headers=citizen,
            json={"answer": "YES", "comment": "Meals collected"},
        )
        assert feedback.status_code == 200 and feedback.json()["feedback"]["answer"] == "YES"
        assert (
            client.post(
                f"/api/v1/admin/requests/{request_id}/record-impact", headers=admin
            ).status_code
            == 200
        )
        totals = client.get("/api/v1/impact").json()
        assert totals["verified_outcomes"] == 1
        assert totals["by_category"]["FOOD"]["units"]["meals"] == 60
        performance = client.get(
            f"/api/v1/organizations/{org['id']}/performance", headers=org_owner
        )
        assert performance.status_code == 200, performance.text
        assert performance.json()["assignments"] == 1
        assert performance.json()["verified_outcomes"] == 1
        assert performance.json()["impact_units"] == {"meals": 60}
        assert client.get(
            f"/api/v1/organizations/{org['id']}/performance", headers=stranger
        ).status_code == 404
        notices = client.get("/api/v1/notifications", headers=citizen).json()
        assert notices and all(item["request_id"] == request_id for item in notices)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
