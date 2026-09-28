from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    Assignment,
    MatchingSetting,
    Outcome,
    Request,
    RequestEvent,
    Resource,
    User,
)
from .lifecycle import distance_km

DEFAULT_WEIGHTS = {
    "category_match": 0.24,
    "distance": 0.18,
    "availability": 0.14,
    "reliability": 0.14,
    "urgency_fit": 0.12,
    "capacity_fit": 0.10,
    "response_time": 0.08,
}


def get_weights(db: Session) -> dict:
    setting = db.get(MatchingSetting, 1)
    return setting.weights if setting else DEFAULT_WEIGHTS.copy()


def _history(db: Session, resource_id: str | None, volunteer_id: str | None):
    query = select(Assignment)
    if resource_id:
        query = query.where(Assignment.resource_id == resource_id)
    else:
        query = query.where(Assignment.volunteer_id == volunteer_id)
    rows = db.scalars(query).all()
    if not rows:
        return 0.5, 0.5, 0
    verified_count = 0
    response_scores = []
    for assignment in rows:
        outcome = db.scalar(
            select(Outcome).where(Outcome.request_id == assignment.request_id)
        )
        if outcome and outcome.verified_at:
            verified_count += 1
        start = db.scalar(
            select(RequestEvent).where(
                RequestEvent.request_id == assignment.request_id,
                RequestEvent.to_status == "IN_PROGRESS",
            )
        )
        if start:
            created = assignment.created_at.replace(tzinfo=timezone.utc)
            started = start.created_at.replace(tzinfo=timezone.utc)
            hours = max(0.0, (started - created).total_seconds() / 3600)
            response_scores.append(max(0.0, 1 - hours / 24))
    reliability = (verified_count + 1) / (len(rows) + 2)
    response_time = (
        sum(response_scores) / len(response_scores) if response_scores else 0.5
    )
    return reliability, response_time, len(rows)


def score_candidate(
    db: Session,
    request: Request,
    *,
    resource: Resource | None = None,
    volunteer: User | None = None,
    weights_override: dict[str, float] | None = None,
) -> dict:
    weights = weights_override or get_weights(db)
    target_lat = resource.latitude if resource else volunteer.latitude
    target_lon = resource.longitude if resource else volunteer.longitude
    distance = distance_km(request.latitude, request.longitude, target_lat, target_lon)
    capacity = max(0, resource.capacity - resource.current_workload) if resource else volunteer.capacity
    reliability, response_time, history_count = _history(
        db, resource.id if resource else None, volunteer.id if volunteer else None
    )
    components = {
        "category_match": 1.0,
        "distance": max(0.0, 1 - distance / 50) if distance is not None else 0.5,
        "availability": 1.0,
        "reliability": reliability,
        "urgency_fit": 1.0
        if request.urgency not in {"HIGH", "CRITICAL"}
        or (distance is not None and distance <= 10)
        else 0.5,
        "capacity_fit": min(1.0, capacity / request.quantity)
        if request.quantity
        else 1.0,
        "response_time": response_time,
    }
    score = round(sum(weights[key] * components[key] for key in weights) * 100)
    why = [
        "serves this category",
        "available",
        "identity/service verified",
        f"capacity {capacity} {request.unit or 'units'}",
    ]
    why.append(
        f"{distance:.1f} km away" if distance is not None else "distance not supplied"
    )
    why.append(
        f"{history_count} prior assignment(s)"
        if history_count
        else "no verified performance history yet"
    )
    return {
        "score": score,
        "distance_km": distance,
        "why": why,
        "components": components,
        "weights": weights,
    }
