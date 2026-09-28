from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Notification, User, now
from ..security import current_user
from ..services.lifecycle import audit

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def view(item: Notification) -> dict:
    return {
        "id": item.id,
        "request_id": item.request_id,
        "kind": item.kind,
        "title": item.title,
        "body": item.body,
        "read_at": item.read_at,
        "created_at": item.created_at,
    }


@router.get("")
def list_notifications(
    page: int = Query(1, ge=1),
    unread_only: bool = False,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    rows = db.scalars(
        query.order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * 50)
        .limit(50)
    ).all()
    return [view(item) for item in rows]


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    item = db.get(Notification, notification_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    if item.read_at is None:
        item.read_at = now()
        audit(db, user, "notification.read", "notification", item.id, {})
        db.commit()
    return view(item)
