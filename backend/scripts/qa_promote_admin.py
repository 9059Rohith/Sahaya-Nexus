"""Promote one isolated browser-test account. Never runs against the normal database."""

import sys

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import User


def main() -> None:
    if settings.app_mode != "test" or settings.database_url != "sqlite:///./qa-e2e.db":
        raise SystemExit("Refusing admin promotion outside the isolated browser-test database")
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m scripts.qa_promote_admin EMAIL")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == sys.argv[1].strip().lower()))
        if user is None:
            raise SystemExit("Browser-test account not found")
        user.role = "ADMIN"
        user.verified = True
        db.commit()


if __name__ == "__main__":
    main()
