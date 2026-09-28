import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from io import BytesIO
from math import cos, radians
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import (
    Assignment,
    DuplicateLink,
    Evidence,
    Organization,
    Outcome,
    OutcomeFeedback,
    Request,
    RequestEvent,
    Resource,
    User,
)
from ..schemas import Category, DuplicateIn, FeedbackIn, InterpretIn, RequestIn
from ..security import current_user
from ..services.interpretation import interpret
from ..services.lifecycle import audit, distance_km, move
from ..services.notifications import notify
from ..services.organizations import can_manage_organization
from ..services.policy import get_policy

router = APIRouter(prefix="/api/v1/requests", tags=["requests"])


def can_access(db: Session, request: Request, user: User):
    if user.id == request.owner_id or user.role in {"OPERATOR", "ADMIN"}:
        return True
    assignment = db.scalar(
        select(Assignment).where(Assignment.request_id == request.id)
    )
    if not assignment:
        return False
    if assignment.volunteer_id == user.id:
        return True
    if assignment.resource_id:
        resource = db.get(Resource, assignment.resource_id)
        org = db.get(Organization, resource.organization_id) if resource else None
        return bool(org and can_manage_organization(db, org, user))
    return False


def detail(db: Session, request: Request, user: User):
    if not can_access(db, request, user):
        raise HTTPException(404, "Request not found")
    assignment = db.scalar(
        select(Assignment).where(Assignment.request_id == request.id)
    )
    outcome = db.scalar(select(Outcome).where(Outcome.request_id == request.id))
    evidence = db.scalars(
        select(Evidence)
        .where(Evidence.request_id == request.id)
        .order_by(Evidence.created_at)
    ).all()
    return {
        "id": request.id,
        "owner_id": request.owner_id,
        "category": request.category,
        "description": request.description,
        "status": request.status,
        "verification": request.verification,
        "urgency": request.urgency,
        "priority_reason": request.priority_reason,
        "quantity": request.quantity,
        "unit": request.unit,
        "deadline": request.deadline,
        "location_text": request.location_text,
        "latitude": request.latitude,
        "longitude": request.longitude,
        "location_precision": request.location_precision,
        "visibility_scope": request.visibility_scope,
        "privacy_mode": request.privacy_mode,
        "details": request.details,
        "created_at": request.created_at,
        "updated_at": request.updated_at,
        "events": [
            {
                "id": e.id,
                "from_status": e.from_status,
                "to_status": e.to_status,
                "reason": e.reason,
                "evidence_url": e.evidence_url,
                "system_notes": e.system_notes,
                "confidence": e.confidence,
                "created_at": e.created_at,
            }
            for e in request.events
        ],
        "assignment": {
            "id": assignment.id,
            "resource_id": assignment.resource_id,
            "volunteer_id": assignment.volunteer_id,
            "status": assignment.status,
            "rationale": assignment.rationale,
        }
        if assignment
        else None,
        "outcome": {
            "summary": outcome.summary,
            "evidence_url": outcome.evidence_url,
            "verified_at": outcome.verified_at,
            "impact_value": outcome.impact_value,
            "impact_unit": outcome.impact_unit,
        }
        if outcome
        else None,
        "feedback": (
            lambda item: {"answer": item.answer, "comment": item.comment, "created_at": item.created_at} if item else None
        )(db.scalar(select(OutcomeFeedback).where(OutcomeFeedback.request_id == request.id))),
        "evidence": [
            {
                "id": e.id,
                "name": e.original_name,
                "mime_type": e.mime_type,
                "size": e.size,
                "url": f"/api/v1/requests/{request.id}/evidence/{e.id}",
            }
            for e in evidence
        ],
    }


@router.post("/interpret")
def interpret_request(data: InterpretIn, db: Session = Depends(get_db)):
    if not get_policy(db)["feature_flags"]["ai"]:
        from ..services.interpretation import RuleBasedProvider

        return RuleBasedProvider().interpret(data)
    return interpret(data)


@router.post("/duplicates")
def find_duplicates(
    data: DuplicateIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    if data.category != "COMMUNITY":
        return {"count": 0, "matches": [], "method": "community reports only"}
    rows = similar_community_reports(db, data, user)
    return {
        "count": len(rows),
        "matches": [{"id": row.id, "issue_type": row.details.get("issue_type") if row.details.get("issue_type") in {"garbage", "streetlight", "pothole", "drainage"} else "other", "status": row.status, "created_at": row.created_at} for row in rows],
        "method": "similar description and area within 30 days",
        "privacy": "only opted-in verified public reports or your own reports are shown",
    }


def similar_community_reports(db: Session, data: DuplicateIn, user: User, exclude_id: str | None = None) -> list[Request]:
    words = set(re.findall(r"\w+", data.description.lower()))
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    area = func.lower(func.trim(Request.location_text)) == data.location_text.strip().lower()
    if data.latitude is not None and data.longitude is not None:
        latitude_span = 2 / 111 + 0.001
        longitude_span = 2 / (111 * max(0.01, abs(cos(radians(data.latitude))))) + 0.001
        nearby = and_(
            Request.latitude.between(data.latitude - latitude_span, data.latitude + latitude_span),
            or_(
                Request.longitude.between(data.longitude - longitude_span, data.longitude + longitude_span),
                Request.longitude.between(data.longitude - longitude_span - 360, data.longitude + longitude_span - 360),
                Request.longitude.between(data.longitude - longitude_span + 360, data.longitude + longitude_span + 360),
            ),
        )
        area = or_(area, nearby)
    rows = db.scalars(select(Request).where(
        Request.category == "COMMUNITY",
        Request.created_at >= cutoff,
        Request.status.notin_(["CANCELLED", "REJECTED", "DUPLICATE"]),
        area,
        or_(Request.owner_id == user.id, and_(Request.visibility_scope == "PUBLIC", Request.verification == "VERIFIED", Request.privacy_mode.is_(False))),
    ).order_by(Request.created_at.desc(), Request.id.desc())).all()
    matches = []
    for row in rows:
        if row.id == exclude_id or not (row.owner_id == user.id or (row.visibility_scope == "PUBLIC" and row.verification == "VERIFIED" and not row.privacy_mode)):
            continue
        row_words = set(re.findall(r"\w+", row.description.lower()))
        overlap = len(words & row_words) / max(1, len(words | row_words))
        distance = distance_km(
            data.latitude, data.longitude, row.latitude, row.longitude
        )
        same_area = (distance is not None and distance <= 2) or (
            data.location_text.strip().lower() == row.location_text.strip().lower()
        )
        if same_area and overlap >= 0.4:
            matches.append(row)
    return matches


@router.post("/{request_id}/duplicates/{existing_id}/confirm")
def confirm_duplicate(request_id: str, existing_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    request = db.get(Request, request_id)
    if not request or request.owner_id != user.id:
        raise HTTPException(404, "Request not found")
    if request.status not in {"SUBMITTED", "UNDERSTANDING", "VALIDATION"} or request.category != "COMMUNITY":
        raise HTTPException(409, "Duplicate confirmation is unavailable at this stage")
    data = DuplicateIn(category="COMMUNITY", description=request.description, location_text=request.location_text, latitude=request.latitude, longitude=request.longitude)
    eligible = similar_community_reports(db, data, user, exclude_id=request.id)
    existing = next((row for row in eligible if row.id == existing_id), None)
    if existing is None:
        raise HTTPException(404, "Similar public or owned report not found")
    db.add(DuplicateLink(request_id=request.id, existing_request_id=existing.id, confirmed_by=user.id))
    move(db, request, user, "DUPLICATE", f"Citizen confirmed this as the same issue as report {existing.id}")
    if existing.owner_id != user.id:
        notify(db, existing.owner_id, "DUPLICATE_CONFIRMATION", "Another person confirmed your issue", "A nearby report was confirmed as the same public issue.", existing.id)
    db.commit()
    return detail(db, request, user)


@router.post("", status_code=201)
def create_request(
    data: RequestIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    submission_id = str(data.client_submission_id) if data.client_submission_id else None
    payload = data.model_dump(mode="json", exclude={"client_submission_id"})
    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if submission_id:
        existing = db.scalar(select(Request).where(Request.owner_id == user.id, Request.client_submission_id == submission_id))
        if existing:
            if existing.submission_hash != payload_hash:
                raise HTTPException(409, "Submission ID was already used for a different request")
            return detail(db, existing, user)
    policy = get_policy(db)
    if data.category == "BLOOD" and not policy["feature_flags"]["blood_coordination"]:
        raise HTTPException(409, "Blood coordination is unavailable in this installation")
    if policy["pilot_enabled"]:
        if data.category not in policy["pilot_categories"]:
            raise HTTPException(409, "This category is outside the active pilot")
        areas = policy["pilot_service_areas"]
        if areas and not any(area.casefold() in data.location_text.casefold() for area in areas):
            raise HTTPException(409, "This location is outside the active pilot")
    request = Request(owner_id=user.id, client_submission_id=submission_id, submission_hash=payload_hash if submission_id else None, **data.model_dump(exclude={"client_submission_id"}))
    db.add(request)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        if submission_id:
            existing = db.scalar(select(Request).where(Request.owner_id == user.id, Request.client_submission_id == submission_id))
            if existing and existing.submission_hash == payload_hash:
                return detail(db, existing, user)
        raise HTTPException(409, "Submission ID was already used") from None
    db.add(
        RequestEvent(
            request_id=request.id,
            actor_id=user.id,
            from_status=None,
            to_status="SUBMITTED",
            reason="Citizen submitted and confirmed the request",
        )
    )
    audit(
        db,
        user,
        "request.create",
        "request",
        request.id,
        {"category": request.category},
    )
    db.commit()
    db.refresh(request)
    return detail(db, request, user)


@router.get("")
def list_requests(
    mine: bool = True,
    status: str | None = None,
    category: Category | None = None,
    urgency: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] | None = None,
    sort: Literal["newest", "oldest", "updated", "urgency"] = "newest",
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = select(Request)
    if mine or user.role not in {"OPERATOR", "ADMIN"}:
        query = query.where(Request.owner_id == user.id)
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
        "updated": (Request.updated_at.desc(), Request.id.desc()),
        "urgency": (urgency_order.asc(), Request.created_at.desc(), Request.id.desc()),
    }[sort]
    rows = db.scalars(
        query.order_by(*order)
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return [detail(db, row, user) for row in rows]


@router.get("/{request_id}")
def get_request(
    request_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    request = db.get(Request, request_id)
    if not request:
        raise HTTPException(404, "Request not found")
    return detail(db, request, user)


@router.post("/{request_id}/cancel")
def cancel_request(
    request_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    request = db.get(Request, request_id)
    if not request or request.owner_id != user.id:
        raise HTTPException(404, "Request not found")
    if request.status in {
        "IN_PROGRESS",
        "ACTION_COMPLETED",
        "OUTCOME_VERIFIED",
        "IMPACT_RECORDED",
    }:
        raise HTTPException(409, "Contact an operator to cancel an active response")
    move(db, request, user, "CANCELLED", "Citizen cancelled the request")
    db.commit()
    return detail(db, request, user)


@router.post("/{request_id}/outcome/confirm")
def confirm_outcome(
    request_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    request = db.get(Request, request_id)
    outcome = db.scalar(select(Outcome).where(Outcome.request_id == request_id))
    if not request or request.owner_id != user.id:
        raise HTTPException(404, "Request not found")
    if request.status != "ACTION_COMPLETED" or not outcome:
        raise HTTPException(409, "A responder must record the completed action first")
    outcome.verified_by = user.id
    from ..models import now

    outcome.verified_at = now()
    move(
        db,
        request,
        user,
        "OUTCOME_VERIFIED",
        "Citizen confirmed the recorded outcome",
        outcome.evidence_url,
    )
    db.commit()
    return detail(db, request, user)


@router.post("/{request_id}/feedback")
def submit_feedback(
    request_id: str,
    data: FeedbackIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    request = db.get(Request, request_id)
    outcome = db.scalar(select(Outcome).where(Outcome.request_id == request_id))
    if not request or request.owner_id != user.id:
        raise HTTPException(404, "Request not found")
    if request.status != "ACTION_COMPLETED" or not outcome:
        raise HTTPException(409, "Feedback requires a completed action")
    if db.scalar(select(OutcomeFeedback).where(OutcomeFeedback.request_id == request_id)):
        raise HTTPException(409, "Feedback has already been submitted")
    db.add(OutcomeFeedback(request_id=request_id, user_id=user.id, **data.model_dump()))
    if data.answer == "YES":
        from ..models import now

        outcome.verified_by = user.id
        outcome.verified_at = now()
        move(db, request, user, "OUTCOME_VERIFIED", "Citizen confirmed: resolved", outcome.evidence_url)
    else:
        move(db, request, user, "ESCALATED", f"Citizen reported {data.answer.lower()}: {data.comment or 'follow-up required'}")
    db.commit()
    return detail(db, request, user)


@router.post("/{request_id}/evidence", status_code=201)
async def upload_evidence(
    request_id: str,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    request = db.get(Request, request_id)
    if not request or not can_access(db, request, user):
        raise HTTPException(404, "Request not found")
    if request.status in {"CANCELLED", "REJECTED", "EXPIRED", "DUPLICATE", "IMPACT_RECORDED"}:
        raise HTTPException(409, "Request no longer accepts evidence")
    payload = await file.read(5 * 1024 * 1024 + 1)
    if len(payload) > 5 * 1024 * 1024:
        raise HTTPException(413, "File exceeds 5 MB")
    if payload.startswith(b"\xff\xd8\xff"):
        mime, suffix = "image/jpeg", ".jpg"
    elif payload.startswith(b"\x89PNG\r\n\x1a\n"):
        mime, suffix = "image/png", ".png"
    else:
        raise HTTPException(415, "Only JPEG and PNG image evidence is accepted")
    if mime.startswith("image/"):
        try:
            Image.MAX_IMAGE_PIXELS = 20_000_000
            with Image.open(BytesIO(payload)) as image:
                if image.width * image.height > 20_000_000:
                    raise HTTPException(413, "Image dimensions exceed 20 megapixels")
                image.load()
                cleaned = ImageOps.exif_transpose(image)
                output = BytesIO()
                if mime == "image/jpeg":
                    cleaned.convert("RGB").save(output, format="JPEG", quality=85, optimize=True)
                else:
                    cleaned.save(output, format="PNG", optimize=True)
                payload = output.getvalue()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            raise HTTPException(415, "Image evidence is invalid") from exc
        if len(payload) > 5 * 1024 * 1024:
            raise HTTPException(413, "Processed image exceeds 5 MB")
    evidence = Evidence(
        request_id=request_id,
        uploaded_by=user.id,
        original_name=Path(file.filename or "evidence").name[:180],
        mime_type=mime,
        size=len(payload),
    )
    db.add(evidence)
    db.flush()
    storage = Path(settings.data_dir) / "evidence"
    storage.mkdir(parents=True, exist_ok=True)
    (storage / f"{evidence.id}{suffix}").write_bytes(payload)
    audit(
        db,
        user,
        "request.evidence",
        "request",
        request_id,
        {"evidence_id": evidence.id, "mime_type": mime},
    )
    db.commit()
    return {
        "id": evidence.id,
        "name": evidence.original_name,
        "mime_type": mime,
        "size": len(payload),
    }


@router.get("/{request_id}/evidence/{evidence_id}")
def get_evidence(
    request_id: str,
    evidence_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    request = db.get(Request, request_id)
    evidence = db.get(Evidence, evidence_id)
    if (
        not request
        or not evidence
        or evidence.request_id != request_id
        or not can_access(db, request, user)
    ):
        raise HTTPException(404, "Evidence not found")
    suffix = {"image/jpeg": ".jpg", "image/png": ".png", "application/pdf": ".pdf"}[
        evidence.mime_type
    ]
    path = Path(settings.data_dir) / "evidence" / f"{evidence.id}{suffix}"
    if not path.is_file():
        raise HTTPException(503, "Evidence storage unavailable")
    return FileResponse(
        path,
        media_type=evidence.mime_type,
        filename=evidence.original_name,
        content_disposition_type="attachment",
    )
