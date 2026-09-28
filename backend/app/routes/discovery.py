from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Assignment,
    Organization,
    Outcome,
    Request,
    RequestEvent,
    Resource,
    User,
)
from ..security import current_user, staff

router = APIRouter(prefix="/api/v1", tags=["discovery", "analytics"])


def text_match(db: Session, column, term: str):
    if db.bind and db.bind.dialect.name == "postgresql":
        return func.to_tsvector("simple", column).op("@@")(
            func.plainto_tsquery("simple", term)
        )
    return column.ilike(f"%{term}%")


@router.get("/search")
def search(
    q: str = Query(min_length=2, max_length=100),
    page: int = Query(1, ge=1),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    term = q.strip()
    offset = (page - 1) * 20
    instant = datetime.now(timezone.utc)
    staff_access = user.role in {"OPERATOR", "ADMIN"}
    rq = select(Request).where(
        or_(
            text_match(db, Request.description, term),
            text_match(db, Request.location_text, term),
        )
    )
    if not staff_access:
        rq = rq.where(Request.owner_id == user.id)
    requests = db.scalars(rq.order_by(Request.created_at.desc(), Request.id.desc()).offset(offset).limit(20)).all()
    resources = db.scalars(
        select(Resource)
        .join(Organization, Resource.organization_id == Organization.id)
        .where(
            Organization.status == "VERIFIED",
            Resource.available.is_(True),
            Resource.capacity > Resource.current_workload,
            or_(Resource.expires_at.is_(None), Resource.expires_at > instant),
            or_(Resource.available_from.is_(None), Resource.available_from <= instant),
            or_(Resource.available_until.is_(None), Resource.available_until > instant),
            or_(text_match(db, Resource.title, term), text_match(db, Resource.description, term)),
        )
        .order_by(Resource.created_at.desc(), Resource.id.desc())
        .offset(offset)
        .limit(20)
    ).all()
    organizations = db.scalars(
        select(Organization)
        .where(
            Organization.status == "VERIFIED",
            or_(text_match(db, Organization.name, term), text_match(db, Organization.service_area, term)),
        )
        .order_by(Organization.name.asc(), Organization.id.asc())
        .offset(offset)
        .limit(20)
    ).all()
    volunteers = []
    if staff_access:
        volunteers = db.scalars(
            select(User)
            .where(User.role == "VOLUNTEER", text_match(db, User.name, term))
            .order_by(User.name.asc(), User.id.asc())
            .offset(offset)
            .limit(20)
        ).all()
    return {
        "requests": [{"id": r.id, "category": r.category, "status": r.status, "description": r.description[:180]} for r in requests],
        "resources": [{"id": r.id, "title": r.title, "category": r.category, "capacity": r.capacity} for r in resources],
        "organizations": [{"id": o.id, "name": o.name, "service_area": o.service_area} for o in organizations],
        "volunteers": [{"id": v.id, "name": v.name, "verified": v.verified} for v in volunteers],
        "page": page,
    }


def approximate(value: float | None) -> float | None:
    return round(value, 1) if value is not None else None


@router.get("/public/issues")
def public_issues(
    category: str | None = Query(default=None, pattern="^(COMMUNITY|ACCESSIBILITY)$"),
    status: str | None = Query(default=None, max_length=32),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    query = select(Request).where(
        Request.visibility_scope == "PUBLIC",
        Request.privacy_mode.is_(False),
        Request.verification == "VERIFIED",
        Request.category.in_(["COMMUNITY", "ACCESSIBILITY"]),
        Request.status.notin_(["REJECTED", "CANCELLED", "DUPLICATE"]),
    )
    if category:
        query = query.where(Request.category == category)
    if status:
        query = query.where(Request.status == status)
    rows = db.scalars(query.order_by(Request.created_at.desc(), Request.id.desc()).offset((page - 1) * 30).limit(30)).all()
    return [
        {
            "id": row.id,
            "category": row.category,
            "issue_type": (
                row.details.get("issue_type") if row.details.get("issue_type") in {"garbage", "streetlight", "pothole", "drainage"} else
                row.details.get("barrier_type") if row.details.get("barrier_type") in {"ramp", "pathway", "entrance", "transport", "other"} else "other"
            ),
            "status": row.status,
            "urgency": row.urgency,
            "latitude": approximate(row.latitude),
            "longitude": approximate(row.longitude),
            "created_at": row.created_at,
            "data_label": "REAL",
        }
        for row in rows
    ]


@router.get("/public/summary")
def public_summary(db: Session = Depends(get_db)):
    issue_count = db.scalar(select(func.count(Request.id)).where(
        Request.visibility_scope == "PUBLIC",
        Request.privacy_mode.is_(False),
        Request.verification == "VERIFIED",
        Request.category.in_(["COMMUNITY", "ACCESSIBILITY"]),
        Request.status.notin_(["REJECTED", "CANCELLED", "DUPLICATE"]),
    )) or 0
    return {"verified_public_issues": issue_count, "data_label": "REAL"}


@router.get("/public/impact-map")
def public_impact_map(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Request.category, Request.latitude, Request.longitude)
        .join(Outcome, Outcome.request_id == Request.id)
        .where(Request.status == "IMPACT_RECORDED", Request.category != "BLOOD", Request.privacy_mode.is_(False))
    ).all()
    cells: dict[tuple[float, float], int] = defaultdict(int)
    for _, lat, lon in rows:
        if lat is not None and lon is not None:
            cells[(approximate(lat), approximate(lon))] += 1
    visible = [{"latitude": lat, "longitude": lon, "verified_outcomes": count} for (lat, lon), count in cells.items() if count >= 3]
    return {"cells": visible, "suppressed_cells": sum(1 for count in cells.values() if count < 3), "precision": "0.1 degree grid; cells below three outcomes suppressed", "data_label": "REAL"}


@router.get("/admin/analytics")
def admin_analytics(
    days: int = Query(30, ge=1, le=365),
    actor: User = Depends(staff),
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    requests = db.scalars(select(Request).where(Request.created_at >= cutoff)).all()
    ids = [row.id for row in requests]
    events = db.scalars(select(RequestEvent).where(RequestEvent.request_id.in_(ids))).all() if ids else []
    event_times: dict[str, dict[str, datetime]] = defaultdict(dict)
    for event in events:
        event_times[event.request_id].setdefault(event.to_status, event.created_at)
    def average_hours(stage: str) -> float | None:
        durations = []
        for row in requests:
            when = event_times[row.id].get(stage)
            if when:
                start = row.created_at.replace(tzinfo=timezone.utc)
                end = when.replace(tzinfo=timezone.utc)
                durations.append((end - start).total_seconds() / 3600)
        return round(sum(durations) / len(durations), 2) if durations else None
    categories: dict[str, int] = defaultdict(int)
    daily: dict[str, int] = defaultdict(int)
    for row in requests:
        categories[row.category] += 1
        daily[row.created_at.date().isoformat()] += 1
    completed = sum(1 for row in requests if row.status in {"OUTCOME_VERIFIED", "IMPACT_RECORDED"})
    assignment_count = db.scalar(select(func.count()).select_from(Assignment).where(Assignment.request_id.in_(ids))) if ids else 0
    return {
        "period_days": days,
        "requests": len(requests),
        "requests_by_day": dict(sorted(daily.items())),
        "category_distribution": dict(categories),
        "resolution_rate": round(completed / len(requests), 3) if requests else 0,
        "mean_hours_to_verification": average_hours("PRIORITIZATION"),
        "mean_hours_to_assignment": average_hours("ASSIGNED"),
        "mean_hours_to_action": average_hours("ACTION_COMPLETED"),
        "assignments": assignment_count,
        "data_label": "REAL",
    }
