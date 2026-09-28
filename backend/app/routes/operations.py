import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, or_, select, text
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import (
    Assignment,
    AuditLog,
    Evidence,
    MatchingSetting,
    Organization,
    OrganizationMember,
    Outcome,
    PlatformSetting,
    Request,
    RequestEvent,
    Resource,
    User,
    VolunteerInterest,
)
from ..schemas import (
    AssignmentIn,
    Category,
    FollowUpIn,
    MatchingWeightsIn,
    OutcomeIn,
    PolicyIn,
    PriorityIn,
    TransitionIn,
    VerificationIn,
)
from ..security import current_user, staff
from ..services.capacity import record_capacity, snapshot
from ..services.lifecycle import audit, milestone, move, priority_for
from ..services.matching import get_weights, score_candidate
from ..services.notifications import notify
from ..services.organizations import can_manage_organization
from ..services.policy import get_policy
from ..services.rate_limit import shared_limiter_status
from .requests import can_access, detail

router = APIRouter(prefix="/api/v1", tags=["operations"])


@router.get("/config")
def public_config(db: Session = Depends(get_db)):
    policy = get_policy(db)
    return {"feature_flags": policy["feature_flags"], "pilot_enabled": policy["pilot_enabled"]}


@router.get("/admin/config")
def admin_config(actor: User = Depends(staff), db: Session = Depends(get_db)):
    return get_policy(db)


@router.get("/admin/health")
def admin_health(actor: User = Depends(staff), db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    storage = Path(settings.data_dir)
    storage.mkdir(parents=True, exist_ok=True)
    speech_cache = storage / "models"
    heartbeat = storage / "worker-heartbeat"
    worker_age = round(time.time() - heartbeat.stat().st_mtime) if heartbeat.exists() else None
    return {
        "backend": "available",
        "database": "available",
        "storage": "available" if storage.is_dir() else "unavailable",
        "ai": "local_ollama_configured" if settings.ollama_url else "rule_based_fallback",
        "speech": "model_cache_present" if speech_cache.is_dir() and any(speech_cache.iterdir()) else "model_not_prepared",
        "map": "optional_openstreetmap",
        "queue": "database_polled_worker",
        "worker": "healthy" if worker_age is not None and worker_age < 180 else "stale",
        "worker_last_success_seconds_ago": worker_age,
        "rate_limit": shared_limiter_status(),
        "mode": settings.app_mode,
    }


@router.put("/admin/config")
def update_config(data: PolicyIn, actor: User = Depends(staff), db: Session = Depends(get_db)):
    if actor.role != "ADMIN":
        raise HTTPException(403, "Admin access required")
    before = get_policy(db)
    row = db.get(PlatformSetting, "policy")
    if row:
        row.value = data.model_dump()
        row.updated_by = actor.id
    else:
        db.add(PlatformSetting(key="policy", value=data.model_dump(), updated_by=actor.id))
    audit(db, actor, "platform.config", "platform_setting", "policy", {"before": before, "after": data.model_dump()})
    db.commit()
    return data.model_dump()


@router.get("/admin/matching-settings")
def matching_settings(actor: User = Depends(staff), db: Session = Depends(get_db)):
    return {"weights": get_weights(db)}


@router.post("/admin/matching-settings")
def update_matching_settings(
    data: MatchingWeightsIn, actor: User = Depends(staff), db: Session = Depends(get_db)
):
    if actor.role != "ADMIN":
        raise HTTPException(403, "Admin access required")
    setting = db.get(MatchingSetting, 1)
    before = get_weights(db)
    if setting:
        setting.weights = data.model_dump()
        setting.updated_by = actor.id
    else:
        db.add(MatchingSetting(id=1, weights=data.model_dump(), updated_by=actor.id))
    audit(
        db,
        actor,
        "matching.weights",
        "matching_settings",
        "1",
        {"before": before, "after": data.model_dump()},
    )
    db.commit()
    return {"weights": data.model_dump()}


@router.get("/admin/audit")
def audit_log(
    page: int = Query(1, ge=1),
    actor: User = Depends(staff),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * 50)
        .limit(50)
    ).all()
    return [
        {
            "id": row.id,
            "actor_id": row.actor_id,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "data": row.data,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/admin/queue")
def queue(
    status: str | None = None,
    category: Category | None = None,
    urgency: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] | None = None,
    sort: Literal["newest", "oldest", "urgency"] = "newest",
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    actor: User = Depends(staff),
):
    query = select(Request)
    if status:
        query = query.where(Request.status == status)
    if category:
        query = query.where(Request.category == category)
    if urgency:
        query = query.where(Request.urgency == urgency)
    urgency_order = case((Request.urgency == "CRITICAL", 0), (Request.urgency == "HIGH", 1), (Request.urgency == "MEDIUM", 2), else_=3)
    order = {
        "newest": (Request.created_at.desc(), Request.id.desc()),
        "oldest": (Request.created_at.asc(), Request.id.asc()),
        "urgency": (urgency_order.asc(), Request.created_at.desc(), Request.id.desc()),
    }[sort]
    rows = db.scalars(
        query.order_by(*order).offset((page - 1) * limit).limit(limit)
    ).all()
    return [detail(db, row, actor) for row in rows]


@router.get("/admin/escalations")
def escalations(actor: User = Depends(staff), db: Session = Depends(get_db)):
    threshold = get_policy(db)["escalation_hours"]
    rows = db.scalars(select(Request).where(Request.status == "ESCALATED").order_by(Request.updated_at.desc()).limit(100)).all()
    now = datetime.now(timezone.utc)
    return [{
        "request_id": row.id,
        "category": row.category,
        "age_hours": round((now - row.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600, 1),
        "threshold_hours": threshold,
        "reason": row.events[-1].reason if row.events else "Operational review required",
        "previous_actions": [{"status": event.to_status, "reason": event.reason, "created_at": event.created_at} for event in row.events],
        "next_action": "Review the evidence and create a follow-up request if the need remains active",
        "follow_up_id": row.details.get("follow_up_id"),
    } for row in rows]


@router.post("/admin/requests/{request_id}/follow-up")
def create_follow_up(request_id: str, data: FollowUpIn, actor: User = Depends(staff), db: Session = Depends(get_db)):
    source = db.get(Request, request_id)
    if not source:
        raise HTTPException(404, "Request not found")
    if source.status != "ESCALATED":
        raise HTTPException(409, "Only escalated requests can create a follow-up")
    existing = source.details.get("follow_up_id")
    if existing:
        follow_up = db.get(Request, existing)
        if follow_up:
            return detail(db, follow_up, actor)
    if source.category == "FOOD" and source.details.get("safe_until"):
        safe_until = datetime.fromisoformat(source.details["safe_until"].replace("Z", "+00:00"))
        if (safe_until if safe_until.tzinfo else safe_until.replace(tzinfo=timezone.utc)) <= datetime.now(timezone.utc):
            raise HTTPException(409, "Food offer has expired; the owner must submit a fresh offer")
    deadline = source.deadline
    if deadline and (deadline if deadline.tzinfo else deadline.replace(tzinfo=timezone.utc)) <= datetime.now(timezone.utc):
        deadline = None
    follow_up = Request(
        owner_id=source.owner_id, category=source.category, description=source.description,
        location_text=source.location_text, latitude=source.latitude, longitude=source.longitude,
        location_precision=source.location_precision, visibility_scope=source.visibility_scope,
        privacy_mode=source.privacy_mode, quantity=source.quantity, unit=source.unit,
        deadline=deadline, details={**source.details, "follow_up_to": source.id},
    )
    db.add(follow_up)
    db.flush()
    source.details = {**source.details, "follow_up_id": follow_up.id}
    db.add(RequestEvent(request_id=follow_up.id, actor_id=actor.id, from_status=None, to_status="SUBMITTED", reason=f"Operator created follow-up: {data.reason}"))
    milestone(db, source, actor, f"Follow-up request {follow_up.id} created: {data.reason}")
    audit(db, actor, "request.follow_up", "request", follow_up.id, {"source_request_id": source.id, "reason": data.reason})
    notify(db, source.owner_id, "FOLLOW_UP", "Follow-up request opened", "An operator opened a new request to continue the unresolved need.", follow_up.id)
    db.commit()
    db.refresh(follow_up)
    return detail(db, follow_up, actor)


@router.post("/admin/requests/{request_id}/transition")
def transition(
    request_id: str,
    data: TransitionIn,
    actor: User = Depends(staff),
    db: Session = Depends(get_db),
):
    request = db.get(Request, request_id)
    if not request:
        raise HTTPException(404, "Request not found")
    if data.to_status in {
        "ASSIGNED",
        "IN_PROGRESS",
        "ACTION_COMPLETED",
        "OUTCOME_VERIFIED",
        "IMPACT_RECORDED",
    }:
        raise HTTPException(409, "Use the dedicated action for this stage")
    if data.to_status == "PRIORITIZATION":
        request.urgency, request.priority_reason = priority_for(request, get_policy(db))
    move(db, request, actor, data.to_status, data.reason, data.evidence_url)
    db.commit()
    return detail(db, request, actor)


@router.post("/admin/requests/{request_id}/verify")
def verify_request(
    request_id: str,
    data: VerificationIn,
    actor: User = Depends(staff),
    db: Session = Depends(get_db),
):
    request = db.get(Request, request_id)
    if not request:
        raise HTTPException(404, "Request not found")
    if request.status != "VERIFICATION":
        raise HTTPException(409, "Request is not at verification stage")
    if data.decision == "VERIFIED" and request.category in get_policy(db)["verification_evidence_categories"]:
        if not db.scalar(select(Evidence).where(Evidence.request_id == request.id)):
            raise HTTPException(409, "Evidence is required for this category by platform policy")
    request.verification = data.decision
    audit(
        db,
        actor,
        "request.verify",
        "request",
        request.id,
        {
            "decision": data.decision,
            "reason": data.reason,
            "evidence_url": data.evidence_url,
        },
    )
    if data.decision == "REJECTED":
        move(db, request, actor, "REJECTED", data.reason, data.evidence_url)
    db.commit()
    return detail(db, request, actor)


@router.post("/admin/requests/{request_id}/priority")
def override_priority(
    request_id: str,
    data: PriorityIn,
    actor: User = Depends(staff),
    db: Session = Depends(get_db),
):
    request = db.get(Request, request_id)
    if not request:
        raise HTTPException(404, "Request not found")
    if request.status not in {"PRIORITIZATION", "MATCHING", "ASSIGNED", "IN_PROGRESS"}:
        raise HTTPException(409, "Priority can only be changed after verification")
    original = request.urgency
    request.urgency = data.urgency
    request.priority_reason = f"Operator override: {data.reason}"
    audit(
        db,
        actor,
        "request.priority_override",
        "request",
        request.id,
        {"original": original, "new": data.urgency, "reason": data.reason},
    )
    db.commit()
    return detail(db, request, actor)


@router.get("/matching/{request_id}")
def candidates(
    request_id: str, actor: User = Depends(staff), db: Session = Depends(get_db)
):
    request = db.get(Request, request_id)
    if not request:
        raise HTTPException(404, "Request not found")
    if request.status not in {"MATCHING", "PRIORITIZATION"}:
        raise HTTPException(409, "Request is not ready for matching")
    advanced_matching = get_policy(db)["feature_flags"]["advanced_matching"]
    basic_weights = {"category_match": 0.5, "distance": 0.25, "availability": 0.25, "reliability": 0.0, "urgency_fit": 0.0, "capacity_fit": 0.0, "response_time": 0.0}
    result = []
    resource_query = (
        select(Resource, Organization)
        .join(Organization, Resource.organization_id == Organization.id)
        .where(
            Resource.category == request.category,
            Resource.available.is_(True),
            Organization.status == "VERIFIED",
        )
    )
    has_postgis = False
    if db.bind and db.bind.dialect.name == "postgresql":
        has_postgis = bool(db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'postgis'")).scalar())
    if has_postgis and request.latitude is not None and request.longitude is not None:
        resource_query = resource_query.where(text("(resources.geom IS NULL OR ST_DWithin(resources.geom::geography, ST_SetSRID(ST_MakePoint(:request_lon, :request_lat), 4326)::geography, resources.service_radius_km * 1000))")).params(request_lon=request.longitude, request_lat=request.latitude)
    rows = db.execute(resource_query).all()
    interested_volunteers = set(db.scalars(select(VolunteerInterest.volunteer_id).where(VolunteerInterest.request_id == request_id)).all())
    for resource, org in rows:
        instant = datetime.now(timezone.utc)
        if resource.current_workload >= resource.capacity:
            continue
        if request.quantity and resource.capacity - resource.current_workload < request.quantity:
            continue
        if resource.expires_at and resource.expires_at.replace(tzinfo=timezone.utc) <= instant:
            continue
        if resource.available_from and resource.available_from.replace(tzinfo=timezone.utc) > instant:
            continue
        if resource.available_until and resource.available_until.replace(tzinfo=timezone.utc) <= instant:
            continue
        scored = score_candidate(db, request, resource=resource, weights_override=None if advanced_matching else basic_weights)
        if scored["distance_km"] is not None and scored["distance_km"] > resource.service_radius_km:
            continue
        result.append(
            {
                "type": "resource",
                "id": resource.id,
                "name": resource.title,
                "organization": org.name,
                **scored,
            }
        )
    for volunteer in db.scalars(
        select(User).where(
            User.role == "VOLUNTEER", User.verified.is_(True), User.available.is_(True)
        )
    ).all():
        if request.category not in (volunteer.categories or []):
            continue
        if request.quantity and volunteer.capacity < request.quantity:
            continue
        scored = score_candidate(db, request, volunteer=volunteer, weights_override=None if advanced_matching else basic_weights)
        result.append(
            {
                "type": "volunteer",
                "id": volunteer.id,
                "name": volunteer.name,
                "interested": volunteer.id in interested_volunteers,
                **scored,
            }
        )
    return sorted(result, key=lambda item: item["score"], reverse=True)


@router.post("/admin/requests/{request_id}/assign")
def assign(
    request_id: str,
    data: AssignmentIn,
    actor: User = Depends(staff),
    db: Session = Depends(get_db),
):
    request = db.get(Request, request_id)
    if not request:
        raise HTTPException(404, "Request not found")
    if request.status != "MATCHING":
        raise HTTPException(409, "Request is not ready for assignment")
    if db.scalar(select(Assignment).where(Assignment.request_id == request_id)):
        raise HTTPException(409, "Request already assigned")
    candidates_for_request = candidates(request_id, actor, db)
    candidate = next(
        (
            c
            for c in candidates_for_request
            if c["id"] == (data.resource_id or data.volunteer_id)
            and c["type"] == ("resource" if data.resource_id else "volunteer")
        ),
        None,
    )
    if not candidate:
        raise HTTPException(422, "Target is not an eligible, verified, available match")
    assignment = Assignment(
        request_id=request_id,
        resource_id=data.resource_id,
        volunteer_id=data.volunteer_id,
        actor_id=actor.id,
        rationale=data.reason + "; " + "; ".join(candidate["why"]),
    )
    db.add(assignment)
    if data.resource_id:
        resource = db.get(Resource, data.resource_id)
        before = snapshot(resource)
        resource.current_workload += request.quantity or 1
        record_capacity(db, resource, actor, "Capacity reserved for assignment", before, request.id)
    move(db, request, actor, "ASSIGNED", assignment.rationale)
    db.commit()
    return detail(db, request, actor)


@router.get("/assignments/mine")
def my_assignments(actor: User = Depends(current_user), db: Session = Depends(get_db)):
    active_orgs = select(OrganizationMember.organization_id).where(OrganizationMember.user_id == actor.id, OrganizationMember.status == "ACTIVE")
    owned_resources = select(Resource.id).join(Organization, Resource.organization_id == Organization.id).where(or_(Organization.owner_id == actor.id, Organization.id.in_(active_orgs)))
    assignments = db.scalars(select(Assignment).where(or_(Assignment.volunteer_id == actor.id, Assignment.resource_id.in_(owned_resources)))).all()
    rows = []
    for assignment in assignments:
        request = db.get(Request, assignment.request_id)
        if request and can_access(db, request, actor) and actor.id != request.owner_id:
            rows.append(detail(db, request, actor))
    return rows


def assigned_to(db: Session, request: Request, actor: User):
    assignment = db.scalar(
        select(Assignment).where(Assignment.request_id == request.id)
    )
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    if assignment.volunteer_id == actor.id:
        return assignment
    if assignment.resource_id:
        resource = db.get(Resource, assignment.resource_id)
        org = db.get(Organization, resource.organization_id) if resource else None
        if org and can_manage_organization(db, org, actor):
            return assignment
    raise HTTPException(404, "Assignment not found")


@router.post("/assignments/{request_id}/accept")
def accept(
    request_id: str, actor: User = Depends(current_user), db: Session = Depends(get_db)
):
    request = db.get(Request, request_id)
    if not request:
        raise HTTPException(404, "Request not found")
    assignment = assigned_to(db, request, actor)
    if request.status != "ASSIGNED" or assignment.status != "OFFERED":
        raise HTTPException(409, "Assignment is not awaiting acceptance")
    assignment.status = "ACCEPTED"
    from ..models import now

    assignment.accepted_at = now()
    milestone(db, request, actor, "Responder accepted the assignment")
    db.commit()
    return detail(db, request, actor)


@router.post("/assignments/{request_id}/start")
def start_assignment(
    request_id: str, actor: User = Depends(current_user), db: Session = Depends(get_db)
):
    request = db.get(Request, request_id)
    if not request:
        raise HTTPException(404, "Request not found")
    assignment = assigned_to(db, request, actor)
    if request.status != "ASSIGNED" or assignment.status != "ACCEPTED":
        raise HTTPException(409, "Assignment must be accepted first")
    from ..models import now

    assignment.status = "IN_PROGRESS"
    assignment.started_at = now()
    move(db, request, actor, "IN_PROGRESS", "Responder started the assignment")
    db.commit()
    return detail(db, request, actor)


@router.post("/assignments/{request_id}/arrive")
def arrive(
    request_id: str, actor: User = Depends(current_user), db: Session = Depends(get_db)
):
    request = db.get(Request, request_id)
    if not request:
        raise HTTPException(404, "Request not found")
    assignment = assigned_to(db, request, actor)
    if request.status != "IN_PROGRESS" or assignment.status != "IN_PROGRESS":
        raise HTTPException(409, "Assignment must be in progress first")
    from ..models import now

    assignment.status = "ARRIVED"
    assignment.arrived_at = now()
    milestone(db, request, actor, "Responder arrived at the service location")
    db.commit()
    return detail(db, request, actor)


@router.post("/assignments/{request_id}/complete")
def complete(
    request_id: str,
    data: OutcomeIn,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    request = db.get(Request, request_id)
    if not request:
        raise HTTPException(404, "Request not found")
    assignment = assigned_to(db, request, actor)
    if request.status != "IN_PROGRESS" or assignment.status != "ARRIVED":
        raise HTTPException(409, "Responder must mark arrival before completion")
    db.add(Outcome(request_id=request_id, submitted_by=actor.id, **data.model_dump()))
    assignment.status = "COMPLETED"
    from ..models import now

    assignment.completed_at = now()
    move(
        db,
        request,
        actor,
        "ACTION_COMPLETED",
        "Responder submitted an outcome for citizen verification",
        data.evidence_url,
    )
    db.commit()
    return detail(db, request, actor)


@router.post("/admin/requests/{request_id}/record-impact")
def record_impact(
    request_id: str, actor: User = Depends(staff), db: Session = Depends(get_db)
):
    request = db.get(Request, request_id)
    outcome = db.scalar(select(Outcome).where(Outcome.request_id == request_id))
    if not request or not outcome or request.status != "OUTCOME_VERIFIED":
        raise HTTPException(409, "Verified outcome required")
    move(
        db,
        request,
        actor,
        "IMPACT_RECORDED",
        "Verified outcome entered into impact totals",
    )
    db.commit()
    return detail(db, request, actor)


@router.get("/impact")
def impact(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Request, Outcome)
        .join(Outcome, Outcome.request_id == Request.id)
        .where(Request.status == "IMPACT_RECORDED")
    ).all()
    by_category = {}
    for request, outcome in rows:
        item = by_category.setdefault(
            request.category, {"verified_outcomes": 0, "units": {}}
        )
        item["verified_outcomes"] += 1
        if outcome.impact_value is not None and outcome.impact_unit:
            item["units"][outcome.impact_unit] = (
                item["units"].get(outcome.impact_unit, 0) + outcome.impact_value
            )
    return {
        "verified_outcomes": len(rows),
        "by_category": by_category,
        "source": "verified platform outcomes only",
    }


@router.post("/admin/organizations/{organization_id}/verify")
def verify_org(
    organization_id: str,
    data: VerificationIn,
    actor: User = Depends(staff),
    db: Session = Depends(get_db),
):
    org = db.get(Organization, organization_id)
    if not org:
        raise HTTPException(404, "Organization not found")
    org.status = data.decision
    audit(
        db,
        actor,
        "organization.verify",
        "organization",
        org.id,
        {"decision": data.decision, "reason": data.reason},
    )
    db.commit()
    return {"id": org.id, "status": org.status}


@router.get("/admin/organizations")
def org_queue(actor: User = Depends(staff), db: Session = Depends(get_db)):
    return [
        {
            "id": o.id,
            "name": o.name,
            "description": o.description,
            "status": o.status,
            "owner_id": o.owner_id,
        }
        for o in db.scalars(select(Organization)).all()
    ]


@router.get("/admin/volunteers")
def volunteer_queue(actor: User = Depends(staff), db: Session = Depends(get_db)):
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "verified": u.verified,
            "available": u.available,
            "categories": u.categories,
        }
        for u in db.scalars(select(User).where(User.role == "VOLUNTEER")).all()
    ]


@router.post("/admin/volunteers/{volunteer_id}/verify")
def verify_volunteer(
    volunteer_id: str,
    data: VerificationIn,
    actor: User = Depends(staff),
    db: Session = Depends(get_db),
):
    volunteer = db.get(User, volunteer_id)
    if not volunteer or volunteer.role != "VOLUNTEER":
        raise HTTPException(404, "Volunteer not found")
    volunteer.verified = data.decision == "VERIFIED"
    audit(
        db,
        actor,
        "volunteer.verify",
        "user",
        volunteer.id,
        {"decision": data.decision, "reason": data.reason},
    )
    db.commit()
    return {"id": volunteer.id, "verified": volunteer.verified}
