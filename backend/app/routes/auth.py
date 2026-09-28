import secrets
from datetime import datetime, timezone
from pathlib import Path

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request as HttpRequest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import (
    AbuseReport,
    Assignment,
    AuditLog,
    Evidence,
    Message,
    Notification,
    Organization,
    OrganizationMember,
    Outcome,
    OutcomeFeedback,
    Request,
    RevokedToken,
    SavedOrganization,
    User,
)
from ..schemas import DeleteAccountIn, LoginIn, ProfileIn, RegisterIn
from ..security import current_user, hash_password, token_for, verify_password
from ..services.lifecycle import audit

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def public_user(user: User):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "verified": user.verified,
        "available": user.available,
        "capacity": user.capacity,
        "skills": user.skills,
        "categories": user.categories,
        "languages": user.languages,
        "transport": user.transport,
        "latitude": user.latitude,
        "longitude": user.longitude,
    }


@router.post("/register", status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email.lower())):
        raise HTTPException(409, "Email already registered")
    user = User(
        name=data.name.strip(),
        email=data.email.lower(),
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.flush()
    audit(db, user, "user.register", "user", user.id, {})
    db.commit()
    return {"token": token_for(user), "user": public_user(user)}


@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or user.role == "SYSTEM" or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {"token": token_for(user), "user": public_user(user)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return public_user(user)


@router.post("/logout")
def logout(request: HttpRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    payload = jwt.decode(request.headers["Authorization"][7:], settings.secret_key, algorithms=["HS256"])
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < datetime.now(timezone.utc)))
    db.add(RevokedToken(jti=payload["jti"], user_id=user.id, expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc)))
    audit(db, user, "user.logout", "user", user.id, {})
    db.commit()
    return {"ok": True}


@router.delete("/me")
def anonymize_me(data: DeleteAccountIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(403, "Password confirmation failed")
    if user.role in {"ADMIN", "OPERATOR"}:
        raise HTTPException(409, "Staff accounts require an administrative offboarding process")
    if db.scalar(select(Organization).where(Organization.owner_id == user.id)):
        raise HTTPException(409, "Transfer or close owned organizations before deleting the account")
    owned = db.scalars(select(Request).where(Request.owner_id == user.id)).all()
    closed = {"CANCELLED", "REJECTED", "EXPIRED", "DUPLICATE", "IMPACT_RECORDED"}
    if any(request.status not in closed for request in owned):
        raise HTTPException(409, "Close active requests before deleting the account")
    if db.scalar(select(Assignment).where(Assignment.volunteer_id == user.id, Assignment.status.notin_(["COMPLETED", "CANCELLED", "REJECTED", "EXPIRED", "DUPLICATE", "ESCALATED"]))):
        raise HTTPException(409, "Finish active assignments before deleting the account")
    request_ids = {request.id for request in owned}
    uploaded = db.scalars(select(Evidence).where(Evidence.uploaded_by == user.id)).all()
    if any(evidence.request_id not in request_ids and (other := db.get(Request, evidence.request_id)) and other.status not in closed for evidence in uploaded):
        raise HTTPException(409, "Evidence on an active request needs operator review before deletion")
    reports = db.scalars(select(AbuseReport).where(AbuseReport.reporter_id == user.id)).all()
    if any(report.status == "OPEN" for report in reports):
        raise HTTPException(409, "Open safety reports need operator review before deletion")
    attached = db.scalars(select(Evidence).where(Evidence.request_id.in_(request_ids))).all() if request_ids else []
    for evidence in {row.id: row for row in [*uploaded, *attached]}.values():
        suffix = {"image/jpeg": ".jpg", "image/png": ".png", "application/pdf": ".pdf"}.get(evidence.mime_type)
        if suffix:
            (Path(settings.data_dir) / "evidence" / f"{evidence.id}{suffix}").unlink(missing_ok=True)
        db.delete(evidence)
    for request in owned:
        request.description = "[Removed at account owner's request]"
        request.location_text = "Location withheld"
        request.latitude = None
        request.longitude = None
        request.visibility_scope = "PRIVATE"
        request.privacy_mode = True
        request.details = {}
        for event in request.events:
            event.reason = "[Removed at account owner's request]"
            event.system_notes = None
            event.evidence_url = None
        outcome = db.scalar(select(Outcome).where(Outcome.request_id == request.id))
        if outcome:
            outcome.summary = "[Removed at account owner's request]"
            outcome.evidence_url = None
        feedback = db.scalar(select(OutcomeFeedback).where(OutcomeFeedback.request_id == request.id))
        if feedback:
            feedback.comment = ""
    for message in db.scalars(select(Message).where((Message.sender_id == user.id) | Message.request_id.in_(request_ids))).all():
        message.body = "[Removed at account owner's request]"
    for log in db.scalars(select(AuditLog).where((AuditLog.actor_id == user.id) | ((AuditLog.entity_type == "request") & AuditLog.entity_id.in_(request_ids)))).all():
        log.data = {}
    for notification in db.scalars(select(Notification).where(Notification.user_id == user.id)).all():
        db.delete(notification)
    for saved in db.scalars(select(SavedOrganization).where(SavedOrganization.user_id == user.id)).all():
        db.delete(saved)
    for membership in db.scalars(select(OrganizationMember).where(OrganizationMember.user_id == user.id)).all():
        db.delete(membership)
    db.execute(delete(RevokedToken).where(RevokedToken.user_id == user.id))
    for report in reports:
        report.reason = "[Removed at reporter's request]"
    user.name = "Deleted account"
    user.email = f"deleted-{user.id}@sahaya.invalid"
    user.password_hash = hash_password(secrets.token_urlsafe(48))
    user.role = "DELETED"
    user.available = False
    user.verified = False
    user.skills = []
    user.categories = []
    user.languages = []
    user.transport = None
    user.latitude = None
    user.longitude = None
    db.commit()
    return {"anonymized": True}


@router.patch("/me")
def update_me(
    data: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    audit(
        db, user, "user.profile", "user", user.id, data.model_dump(exclude_unset=True)
    )
    db.commit()
    return public_user(user)


@router.post("/volunteer/apply")
def apply_volunteer(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role != "CITIZEN":
        raise HTTPException(409, "Application only available to citizens")
    user.role = "VOLUNTEER"
    user.verified = False
    user.available = False
    audit(db, user, "volunteer.apply", "user", user.id, {})
    db.commit()
    return public_user(user)
