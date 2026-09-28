from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import (
    Assignment,
    AuditLog,
    Organization,
    Request,
    RequestEvent,
    Resource,
    User,
)
from .capacity import record_capacity, snapshot
from .notifications import notify

STEPS = [
    "SUBMITTED",
    "UNDERSTANDING",
    "VALIDATION",
    "VERIFICATION",
    "PRIORITIZATION",
    "MATCHING",
    "ASSIGNED",
    "IN_PROGRESS",
    "ACTION_COMPLETED",
    "OUTCOME_VERIFIED",
    "IMPACT_RECORDED",
]
SIDE = {"CANCELLED", "REJECTED", "EXPIRED", "DUPLICATE", "ESCALATED"}


def audit(
    db: Session, actor: User, action: str, entity_type: str, entity_id: str, data: dict
):
    db.add(
        AuditLog(
            actor_id=actor.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            data=data,
        )
    )


def move(
    db: Session,
    request: Request,
    actor: User,
    to_status: str,
    reason: str,
    evidence_url: str | None = None,
    system_notes: str | None = None,
    confidence: float | None = None,
):
    prior = request.status
    if to_status not in STEPS + list(SIDE):
        raise HTTPException(422, "Unknown status")
    if to_status in STEPS:
        if prior not in STEPS or STEPS.index(to_status) != STEPS.index(prior) + 1:
            raise HTTPException(409, "Lifecycle steps cannot be skipped")
        if to_status == "PRIORITIZATION" and request.verification != "VERIFIED":
            raise HTTPException(409, "Request must be verified first")
    elif prior in {"CANCELLED", "REJECTED", "EXPIRED", "DUPLICATE", "IMPACT_RECORDED"} or prior == to_status:
        raise HTTPException(409, "Request is closed")
    if to_status in SIDE | {"ACTION_COMPLETED"} and prior in {"ASSIGNED", "IN_PROGRESS"}:
        assignment = db.query(Assignment).filter_by(request_id=request.id).first()
        if assignment and assignment.resource_id:
            resource = db.get(Resource, assignment.resource_id)
            if resource:
                before = snapshot(resource)
                resource.current_workload = max(0, resource.current_workload - (request.quantity or 1))
                record_capacity(db, resource, actor, "Capacity released after request transition", before, request.id)
        if assignment and to_status in SIDE:
            assignment.status = to_status
    request.status = to_status
    request.updated_at = datetime.now(timezone.utc)
    db.add(
        RequestEvent(
            request_id=request.id,
            actor_id=actor.id,
            from_status=prior,
            to_status=to_status,
            reason=reason,
            evidence_url=evidence_url,
            system_notes=system_notes,
            confidence=confidence,
        )
    )
    audit(
        db,
        actor,
        "request.transition",
        "request",
        request.id,
        {"from": prior, "to": to_status, "reason": reason},
    )
    if actor.id != request.owner_id:
        notify(
            db,
            request.owner_id,
            "REQUEST_STATUS",
            "Request status updated",
            f"Your {request.category.lower()} request moved to {to_status.replace('_', ' ').lower()}.",
            request.id,
        )
    if to_status == "ASSIGNED":
        assignment = db.query(Assignment).filter_by(request_id=request.id).first()
        if assignment:
            recipient = assignment.volunteer_id
            if assignment.resource_id:
                resource = db.get(Resource, assignment.resource_id)
                org = db.get(Organization, resource.organization_id) if resource else None
                recipient = org.owner_id if org else None
            if recipient:
                notify(
                    db,
                    recipient,
                    "ASSIGNMENT",
                    "New assignment",
                    "A verified request has been assigned to you. Review it before accepting.",
                    request.id,
                )


def milestone(db: Session, request: Request, actor: User, reason: str) -> None:
    db.add(
        RequestEvent(
            request_id=request.id,
            actor_id=actor.id,
            from_status=request.status,
            to_status=request.status,
            reason=reason,
        )
    )
    audit(db, actor, "assignment.milestone", "request", request.id, {"reason": reason})
    if actor.id != request.owner_id:
        notify(db, request.owner_id, "ASSIGNMENT_PROGRESS", "Response update", reason, request.id)


def priority_for(request: Request, policy: dict | None = None):
    policy = policy or {"priority_high_hours": 6, "priority_critical_hours": 2}
    reasons = []
    priority = "MEDIUM"
    deadline = request.deadline
    if deadline and deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if request.category == "FOOD" and request.details.get("safe_until"):
        try:
            safe_until = datetime.fromisoformat(request.details["safe_until"].replace("Z", "+00:00"))
            if safe_until.tzinfo is None:
                safe_until = safe_until.replace(tzinfo=timezone.utc)
            if deadline is None or safe_until < deadline:
                deadline = safe_until
        except (ValueError, TypeError, AttributeError):
            pass
    if deadline:
        hours = (deadline - datetime.now(timezone.utc)).total_seconds() / 3600
        if hours <= policy["priority_critical_hours"]:
            priority = "CRITICAL"
            reasons.append(f"verified time limit within {policy['priority_critical_hours']} hours")
        elif hours <= policy["priority_high_hours"]:
            priority = "HIGH"
            reasons.append(f"verified time limit within {policy['priority_high_hours']} hours")
    if request.category == "BLOOD":
        priority = "HIGH"
        reasons.append(
            "medical coordination request; clinical urgency requires facility review"
        )
    if request.quantity and request.quantity >= 50:
        if priority == "MEDIUM" and request.category == "FOOD":
            priority = "HIGH"
        reasons.append(f"{request.quantity} {request.unit or 'units'} reported")
    if not reasons:
        reasons.append("standard review order; no verified time constraint")
    return priority, "; ".join(reasons)


def distance_km(a_lat, a_lon, b_lat, b_lon):
    if None in (a_lat, a_lon, b_lat, b_lon):
        return None
    lat1, lon1, lat2, lon2 = map(radians, (a_lat, a_lon, b_lat, b_lon))
    x = (
        sin((lat2 - lat1) / 2) ** 2
        + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    )
    return 6371 * 2 * asin(sqrt(x))
