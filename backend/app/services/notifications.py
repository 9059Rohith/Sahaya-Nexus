from sqlalchemy.orm import Session

from ..models import Notification


def notify(
    db: Session,
    user_id: str,
    kind: str,
    title: str,
    body: str,
    request_id: str | None = None,
) -> None:
    db.add(
        Notification(
            user_id=user_id,
            request_id=request_id,
            kind=kind,
            title=title,
            body=body,
        )
    )
