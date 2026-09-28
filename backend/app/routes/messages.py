from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Assignment, Message, Organization, Request, Resource, User
from ..schemas import MessageIn
from ..security import current_user
from ..services.lifecycle import audit
from ..services.notifications import notify
from ..services.organizations import active_member_ids
from .requests import can_access

router = APIRouter(prefix="/api/v1/requests/{request_id}/messages", tags=["messages"])


def accessible_request(db: Session, request_id: str, user: User) -> Request:
    request = db.get(Request, request_id)
    if not request or not can_access(db, request, user):
        raise HTTPException(404, "Request not found")
    return request


def view(db: Session, item: Message) -> dict:
    sender = db.get(User, item.sender_id)
    return {
        "id": item.id,
        "request_id": item.request_id,
        "sender_id": item.sender_id,
        "sender_name": sender.name if sender else "Former participant",
        "body": item.body,
        "created_at": item.created_at,
    }


@router.get("")
def list_messages(
    request_id: str,
    page: int = Query(1, ge=1),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    accessible_request(db, request_id, user)
    rows = db.scalars(
        select(Message)
        .where(Message.request_id == request_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .offset((page - 1) * 50)
        .limit(50)
    ).all()
    return [view(db, row) for row in reversed(rows)]


@router.post("", status_code=201)
def send_message(
    request_id: str,
    data: MessageIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    request = accessible_request(db, request_id, user)
    body = data.body.strip()
    if not body:
        raise HTTPException(422, "Message cannot be blank")
    item = Message(request_id=request.id, sender_id=user.id, body=body)
    db.add(item)
    db.flush()
    recipients = {request.owner_id}
    assignment = db.scalar(select(Assignment).where(Assignment.request_id == request.id))
    if assignment:
        if assignment.volunteer_id:
            recipients.add(assignment.volunteer_id)
        if assignment.resource_id:
            resource = db.get(Resource, assignment.resource_id)
            organization = db.get(Organization, resource.organization_id) if resource else None
            if organization:
                recipients.add(organization.owner_id)
                recipients.update(active_member_ids(db, organization.id))
    for recipient_id in recipients - {user.id}:
        notify(db, recipient_id, "REQUEST_MESSAGE", "New request message", "A participant sent a message about your request.", request.id)
    audit(db, user, "message.create", "request", request.id, {"message_id": item.id})
    db.commit()
    return view(db, item)
