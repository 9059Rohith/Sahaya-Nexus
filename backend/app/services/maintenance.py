"""Database backed operational expiry and escalation checks."""

import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import (
    AbuseReport,
    Assignment,
    AuditLog,
    Evidence,
    Message,
    Notification,
    Outcome,
    OutcomeFeedback,
    Request,
    User,
)
from ..security import hash_password
from .lifecycle import audit, move
from .policy import get_policy

ACTIVE = {
    "SUBMITTED", "UNDERSTANDING", "VALIDATION", "VERIFICATION", "PRIORITIZATION",
    "MATCHING", "ASSIGNED", "IN_PROGRESS", "ACTION_COMPLETED",
}
CLOSED = {"CANCELLED", "REJECTED", "EXPIRED", "DUPLICATE", "IMPACT_RECORDED"}


def redact_request(db: Session, request: Request, actor: User, retention_days: int, instant: datetime) -> None:
    """Remove request content while preserving statuses and measured aggregate impact."""
    evidence = db.scalars(select(Evidence).where(Evidence.request_id == request.id)).all()
    for item in evidence:
        suffix = {"image/jpeg": ".jpg", "image/png": ".png", "application/pdf": ".pdf"}.get(item.mime_type)
        if suffix:
            (Path(settings.data_dir) / "evidence" / f"{item.id}{suffix}").unlink(missing_ok=True)
        db.delete(item)
    request.description = "[Removed under retention policy]"
    request.location_text = "Location withheld"
    request.latitude = None
    request.longitude = None
    request.visibility_scope = "PRIVATE"
    request.privacy_mode = True
    request.details = {}
    request.priority_reason = ""
    request.retained_at = instant
    for event in request.events:
        event.reason = "[Removed under retention policy]"
        event.system_notes = None
        event.evidence_url = None
    outcome = db.scalar(select(Outcome).where(Outcome.request_id == request.id))
    if outcome:
        outcome.summary = "[Removed under retention policy]"
        outcome.evidence_url = None
    assignment = db.scalar(select(Assignment).where(Assignment.request_id == request.id))
    if assignment:
        assignment.rationale = "[Removed under retention policy]"
    feedback = db.scalar(select(OutcomeFeedback).where(OutcomeFeedback.request_id == request.id))
    if feedback:
        feedback.comment = ""
    for item in db.scalars(select(Message).where(Message.request_id == request.id)).all():
        item.body = "[Removed under retention policy]"
    for item in db.scalars(select(Notification).where(Notification.request_id == request.id)).all():
        db.delete(item)
    for item in db.scalars(select(AbuseReport).where(AbuseReport.request_id == request.id)).all():
        item.reason = "[Removed under retention policy]"
        item.resolution = None
    for item in db.scalars(select(AuditLog).where(AuditLog.entity_type == "request", AuditLog.entity_id == request.id)).all():
        item.data = {}
    audit(db, actor, "request.retention", "request", request.id, {"retention_days": retention_days})


def run_maintenance(db: Session) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    policy = get_policy(db)
    overdue = now - timedelta(hours=policy["escalation_hours"])
    rows = db.scalars(select(Request).where(Request.status.in_(ACTIVE))).all()
    expired = []
    escalated = []
    for request in rows:
        if request.category == "FOOD" and request.details.get("safe_until"):
            try:
                safe_until = datetime.fromisoformat(request.details["safe_until"].replace("Z", "+00:00"))
                if safe_until.tzinfo is None:
                    safe_until = safe_until.replace(tzinfo=timezone.utc)
                if safe_until <= now:
                    expired.append(request)
                    continue
            except (ValueError, TypeError, AttributeError):
                pass
        if request.created_at.replace(tzinfo=timezone.utc) <= overdue:
            escalated.append(request)
    retention_days = policy["retention_days"]
    retained = []
    if retention_days is not None:
        cutoff = now - timedelta(days=retention_days)
        retained = db.scalars(select(Request).where(
            Request.status.in_(CLOSED), Request.updated_at <= cutoff, Request.retained_at.is_(None),
            ~exists(select(AbuseReport.id).where(AbuseReport.request_id == Request.id, AbuseReport.status == "OPEN")),
        ).order_by(Request.updated_at.asc()).limit(50)).all()
    if not expired and not escalated and not retained:
        return {"expired": 0, "escalated": 0, "retained": 0}
    actor = db.scalar(select(User).where(User.email == "system@sahaya.internal"))
    if actor is None:
        actor = User(
            name="Sahaya automation",
            email="system@sahaya.internal",
            password_hash=hash_password(secrets.token_urlsafe(48)),
            role="SYSTEM",
            verified=True,
        )
        db.add(actor)
        db.flush()
    for request in expired:
        move(db, request, actor, "EXPIRED", "Food safe-until time passed without a verified outcome")
    for request in escalated:
        move(db, request, actor, "ESCALATED", f"Unresolved for more than {policy['escalation_hours']} hours; platform operator review required")
    for request in retained:
        redact_request(db, request, actor, retention_days, now)
    db.commit()
    return {"expired": len(expired), "escalated": len(escalated), "retained": len(retained)}
