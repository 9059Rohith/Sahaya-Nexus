from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Organization, OrganizationMember, User


def can_manage_organization(db: Session, organization: Organization, user: User) -> bool:
    if organization.owner_id == user.id:
        return True
    return db.scalar(select(OrganizationMember.id).where(
        OrganizationMember.organization_id == organization.id,
        OrganizationMember.user_id == user.id,
        OrganizationMember.status == "ACTIVE",
    )) is not None


def active_member_ids(db: Session, organization_id: str) -> list[str]:
    return list(db.scalars(select(OrganizationMember.user_id).where(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.status == "ACTIVE",
    )).all())
