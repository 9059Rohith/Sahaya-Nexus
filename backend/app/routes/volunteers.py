from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Request, User, VolunteerInterest
from ..schemas import Category, VolunteerInterestIn
from ..security import current_user, staff
from ..services.lifecycle import audit, distance_km
from ..services.notifications import notify

router = APIRouter(prefix="/api/v1", tags=["volunteers"])


def eligible(request: Request, volunteer: User) -> bool:
    return (
        volunteer.role == "VOLUNTEER"
        and volunteer.verified
        and volunteer.available
        and request.status == "MATCHING"
        and request.verification == "VERIFIED"
        and request.category in (volunteer.categories or [])
        and (not request.quantity or volunteer.capacity >= request.quantity)
    )


@router.get("/volunteers/opportunities")
def opportunities(
    category: Category | None = None,
    urgency: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] | None = None,
    max_distance_km: int | None = Query(default=None, ge=1, le=500),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if actor.role != "VOLUNTEER" or not actor.verified:
        raise HTTPException(403, "Verified volunteer access required")
    if not actor.available or not actor.categories:
        return []
    query = select(Request).where(
        Request.status == "MATCHING",
        Request.verification == "VERIFIED",
        Request.category.in_(actor.categories),
        or_(Request.quantity.is_(None), Request.quantity <= actor.capacity),
    )
    if category:
        query = query.where(Request.category == category)
    if urgency:
        query = query.where(Request.urgency == urgency)
    result = []
    skipped = 0
    for request in db.scalars(query.order_by(Request.created_at.desc(), Request.id.desc())).yield_per(100):
        distance = distance_km(actor.latitude, actor.longitude, request.latitude, request.longitude)
        if max_distance_km is not None and (request.privacy_mode or request.location_precision == "PRIVATE" or distance is None or distance > max_distance_km):
            continue
        if skipped < (page - 1) * limit:
            skipped += 1
            continue
        result.append({
            "id": request.id,
            "category": request.category,
            "urgency": request.urgency,
            "quantity": request.quantity,
            "unit": request.unit,
            "distance_km": round(distance / 5) * 5 if distance is not None and not request.privacy_mode and request.location_precision != "PRIVATE" else None,
            "approximate_latitude": round(request.latitude, 1) if request.latitude is not None and request.category != "BLOOD" and not request.privacy_mode and request.location_precision != "PRIVATE" else None,
            "approximate_longitude": round(request.longitude, 1) if request.longitude is not None and request.category != "BLOOD" and not request.privacy_mode and request.location_precision != "PRIVATE" else None,
            "interested": False,
            "created_at": request.created_at,
        })
        if len(result) == limit:
            break
    if result:
        interests = set(db.scalars(select(VolunteerInterest.request_id).where(VolunteerInterest.volunteer_id == actor.id, VolunteerInterest.request_id.in_([item["id"] for item in result]))).all())
        for item in result:
            item["interested"] = item["id"] in interests
    return result


@router.post("/volunteers/opportunities/{request_id}/interest")
def express_interest(request_id: str, data: VolunteerInterestIn, actor: User = Depends(current_user), db: Session = Depends(get_db)):
    request = db.get(Request, request_id)
    if not request or not eligible(request, actor):
        raise HTTPException(404, "Eligible opportunity not found")
    existing = db.scalar(select(VolunteerInterest).where(VolunteerInterest.request_id == request_id, VolunteerInterest.volunteer_id == actor.id))
    if existing:
        return {"interested": True, "id": existing.id}
    interest = VolunteerInterest(request_id=request_id, volunteer_id=actor.id, note=data.note.strip())
    db.add(interest)
    db.flush()
    audit(db, actor, "volunteer.interest", "request", request_id, {"interest_id": interest.id})
    for staff_user in db.scalars(select(User).where(User.role.in_(["OPERATOR", "ADMIN"]))).all():
        notify(db, staff_user.id, "VOLUNTEER_INTEREST", "Volunteer available for a request", "A verified volunteer expressed availability for a matching request.", request_id)
    db.commit()
    return {"interested": True, "id": interest.id}


@router.get("/admin/requests/{request_id}/interests")
def request_interests(request_id: str, actor: User = Depends(staff), db: Session = Depends(get_db)):
    if not db.get(Request, request_id):
        raise HTTPException(404, "Request not found")
    rows = db.execute(select(VolunteerInterest, User).join(User, VolunteerInterest.volunteer_id == User.id).where(VolunteerInterest.request_id == request_id).order_by(VolunteerInterest.created_at)).all()
    return [{"id": interest.id, "volunteer_id": volunteer.id, "name": volunteer.name, "note": interest.note, "created_at": interest.created_at} for interest, volunteer in rows]
