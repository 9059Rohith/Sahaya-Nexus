from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Assignment,
    CapacityRecord,
    Organization,
    OrganizationMember,
    Outcome,
    Request,
    Resource,
    SavedOrganization,
    User,
    now,
)
from ..schemas import (
    Category,
    OrganizationIn,
    OrganizationInviteIn,
    ResourceIn,
    ResourcePatchIn,
)
from ..security import current_user
from ..services.capacity import record_capacity, snapshot
from ..services.lifecycle import audit
from ..services.notifications import notify
from ..services.organizations import can_manage_organization

router = APIRouter(prefix="/api/v1", tags=["organizations", "resources"])


def org_view(org: Organization):
    return {
        "id": org.id,
        "name": org.name,
        "description": org.description,
        "status": org.status,
        "service_categories": org.service_categories,
        "service_area": org.service_area,
        "created_at": org.created_at,
    }


def resource_view(resource: Resource, org: Organization):
    return {
        "id": resource.id,
        "organization_id": org.id,
        "organization_name": org.name,
        "title": resource.title,
        "description": resource.description,
        "category": resource.category,
        "capacity": resource.capacity,
        "current_workload": resource.current_workload,
        "remaining_capacity": max(0, resource.capacity - resource.current_workload),
        "available": resource.available,
        "available_from": resource.available_from,
        "available_until": resource.available_until,
        "expires_at": resource.expires_at,
        "service_radius_km": resource.service_radius_km,
        "latitude": resource.latitude,
        "longitude": resource.longitude,
    }


@router.post("/organizations", status_code=201)
def create_organization(
    data: OrganizationIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role not in {"CITIZEN", "ORGANIZATION"}:
        raise HTTPException(403, "Organization application unavailable for this role")
    org = Organization(owner_id=user.id, **data.model_dump())
    db.add(org)
    db.flush()
    user.role = "ORGANIZATION"
    audit(db, user, "organization.apply", "organization", org.id, {})
    db.commit()
    return org_view(org)


@router.get("/organizations")
def list_organizations(
    search: str | None = Query(None, max_length=120),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=100),
    sort: Literal["name", "newest"] = "name",
    db: Session = Depends(get_db),
):
    query = select(Organization).where(Organization.status == "VERIFIED")
    if search:
        query = query.where(Organization.name.ilike(f"%{search.strip()}%"))
    order = (Organization.name.asc(), Organization.id.asc()) if sort == "name" else (Organization.created_at.desc(), Organization.id.desc())
    return [
        org_view(o)
        for o in db.scalars(
            query.order_by(*order).offset((page - 1) * limit).limit(limit)
        ).all()
    ]


@router.get("/organizations/mine")
def my_organizations(user: User = Depends(current_user), db: Session = Depends(get_db)):
    memberships = select(OrganizationMember.organization_id).where(OrganizationMember.user_id == user.id, OrganizationMember.status == "ACTIVE")
    rows = db.scalars(select(Organization).where(or_(Organization.owner_id == user.id, Organization.id.in_(memberships))).order_by(Organization.name)).all()
    return [{**org_view(org), "membership_role": "OWNER" if org.owner_id == user.id else "MEMBER"} for org in rows]


@router.get("/organizations/invitations")
def my_invitations(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(OrganizationMember, Organization).join(Organization, OrganizationMember.organization_id == Organization.id).where(OrganizationMember.user_id == user.id, OrganizationMember.status == "INVITED").order_by(OrganizationMember.created_at.desc())).all()
    return [{"id": membership.id, "organization_id": org.id, "organization_name": org.name, "created_at": membership.created_at} for membership, org in rows]


@router.post("/organizations/invitations/{invitation_id}/accept")
def accept_invitation(invitation_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    membership = db.get(OrganizationMember, invitation_id)
    if not membership or membership.user_id != user.id or membership.status != "INVITED":
        raise HTTPException(404, "Invitation not found")
    membership.status = "ACTIVE"
    membership.accepted_at = now()
    audit(db, user, "organization.invitation.accept", "organization", membership.organization_id, {})
    db.commit()
    return {"organization_id": membership.organization_id, "status": membership.status}


@router.get("/organizations/{organization_id}/members")
def list_members(organization_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    org = db.get(Organization, organization_id)
    if not org or org.owner_id != user.id:
        raise HTTPException(404, "Organization not found")
    rows = db.execute(select(OrganizationMember, User).join(User, OrganizationMember.user_id == User.id).where(OrganizationMember.organization_id == organization_id, OrganizationMember.status.in_(["INVITED", "ACTIVE"])).order_by(OrganizationMember.created_at.desc())).all()
    return [{"id": membership.id, "user_id": member.id, "name": member.name, "email": member.email, "status": membership.status} for membership, member in rows]


@router.post("/organizations/{organization_id}/members", status_code=201)
def invite_member(organization_id: str, data: OrganizationInviteIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    org = db.get(Organization, organization_id)
    if not org or org.owner_id != user.id:
        raise HTTPException(404, "Organization not found")
    if org.status != "VERIFIED":
        raise HTTPException(409, "Organization must be verified before inviting members")
    target = db.scalar(select(User).where(User.email == data.email.lower()))
    if not target or target.role not in {"CITIZEN", "ORGANIZATION"} or target.id == user.id:
        raise HTTPException(404, "Eligible account not found")
    membership = db.scalar(select(OrganizationMember).where(OrganizationMember.organization_id == org.id, OrganizationMember.user_id == target.id))
    if membership and membership.status == "ACTIVE":
        raise HTTPException(409, "Account is already a member")
    if not membership:
        membership = OrganizationMember(organization_id=org.id, user_id=target.id, invited_by=user.id)
        db.add(membership)
    else:
        membership.status = "INVITED"
        membership.invited_by = user.id
        membership.accepted_at = None
    db.flush()
    notify(db, target.id, "ORGANIZATION_INVITATION", "Organization invitation", f"{org.name} invited you to join its team.")
    audit(db, user, "organization.invite", "organization", org.id, {"invitee_id": target.id})
    db.commit()
    return {"id": membership.id, "organization_id": org.id, "user_id": target.id, "status": membership.status}


@router.delete("/organizations/{organization_id}/members/{member_id}")
def revoke_member(organization_id: str, member_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    org = db.get(Organization, organization_id)
    if not org or org.owner_id != user.id:
        raise HTTPException(404, "Organization not found")
    membership = db.scalar(select(OrganizationMember).where(OrganizationMember.organization_id == org.id, OrganizationMember.user_id == member_id, OrganizationMember.status.in_(["INVITED", "ACTIVE"])))
    if not membership:
        raise HTTPException(404, "Member not found")
    membership.status = "REVOKED"
    audit(db, user, "organization.member.revoke", "organization", org.id, {"member_id": member_id})
    db.commit()
    return {"status": "REVOKED"}


@router.get("/organizations/saved")
def saved_organizations(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Organization).join(SavedOrganization, SavedOrganization.organization_id == Organization.id).where(SavedOrganization.user_id == user.id, Organization.status == "VERIFIED")).all()
    return [org_view(row) for row in rows]


@router.post("/organizations/{organization_id}/save")
def save_organization(organization_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    org = db.get(Organization, organization_id)
    if not org or org.status != "VERIFIED":
        raise HTTPException(404, "Organization not found")
    existing = db.scalar(select(SavedOrganization).where(SavedOrganization.user_id == user.id, SavedOrganization.organization_id == org.id))
    if not existing:
        db.add(SavedOrganization(user_id=user.id, organization_id=org.id))
        audit(db, user, "organization.save", "organization", org.id, {})
        db.commit()
    return org_view(org)


@router.delete("/organizations/{organization_id}/save")
def unsave_organization(organization_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    saved = db.scalar(select(SavedOrganization).where(SavedOrganization.user_id == user.id, SavedOrganization.organization_id == organization_id))
    if saved:
        db.delete(saved)
        audit(db, user, "organization.unsave", "organization", organization_id, {})
        db.commit()
    return {"saved": False}


@router.post("/organizations/{organization_id}/resources", status_code=201)
def add_resource(
    organization_id: str,
    data: ResourceIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    org = db.get(Organization, organization_id)
    if not org or not can_manage_organization(db, org, user):
        raise HTTPException(404, "Organization not found")
    resource = Resource(organization_id=organization_id, **data.model_dump())
    db.add(resource)
    db.flush()
    record_capacity(db, resource, user, "Resource created")
    audit(db, user, "resource.create", "resource", resource.id, {})
    db.commit()
    return resource_view(resource, org)


@router.get("/organizations/{organization_id}/resources")
def own_resources(organization_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    org = db.get(Organization, organization_id)
    if not org or not can_manage_organization(db, org, user):
        raise HTTPException(404, "Organization not found")
    rows = db.scalars(select(Resource).where(Resource.organization_id == organization_id).order_by(Resource.created_at.desc())).all()
    return [resource_view(resource, org) for resource in rows]


@router.get("/organizations/{organization_id}/performance")
def organization_performance(organization_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    org = db.get(Organization, organization_id)
    if not org or (not can_manage_organization(db, org, user) and user.role not in {"OPERATOR", "ADMIN"}):
        raise HTTPException(404, "Organization not found")
    rows = db.execute(select(Assignment, Request).join(Resource, Assignment.resource_id == Resource.id).join(Request, Assignment.request_id == Request.id).where(Resource.organization_id == organization_id)).all()
    verified = 0
    units: dict[str, int] = {}
    for _, request in rows:
        if request.status != "IMPACT_RECORDED":
            continue
        outcome = db.scalar(select(Outcome).where(Outcome.request_id == request.id))
        if not outcome or not outcome.verified_at:
            continue
        verified += 1
        if outcome.impact_value is not None and outcome.impact_unit:
            units[outcome.impact_unit] = units.get(outcome.impact_unit, 0) + outcome.impact_value
    return {
        "organization_id": org.id,
        "assignments": len(rows),
        "active": sum(1 for _, request in rows if request.status in {"ASSIGNED", "IN_PROGRESS"}),
        "verified_outcomes": verified,
        "impact_units": units,
        "source": "verified platform records only",
    }


@router.get("/resources")
def list_resources(
    category: Category | None = None,
    search: str | None = Query(None, max_length=120),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=100),
    sort: Literal["newest", "oldest", "capacity"] = "newest",
    db: Session = Depends(get_db),
):
    instant = datetime.now(timezone.utc)
    query = (
        select(Resource, Organization)
        .join(Organization, Resource.organization_id == Organization.id)
        .where(
            Organization.status == "VERIFIED", Resource.available.is_(True),
            Resource.current_workload < Resource.capacity,
            or_(Resource.expires_at.is_(None), Resource.expires_at > instant),
            or_(Resource.available_from.is_(None), Resource.available_from <= instant),
            or_(Resource.available_until.is_(None), Resource.available_until > instant),
        )
    )
    if category:
        query = query.where(Resource.category == category)
    if search:
        query = query.where(or_(Resource.title.ilike(f"%{search.strip()}%"), Organization.name.ilike(f"%{search.strip()}%")))
    order = {
        "newest": (Resource.created_at.desc(), Resource.id.desc()),
        "oldest": (Resource.created_at.asc(), Resource.id.asc()),
        "capacity": ((Resource.capacity - Resource.current_workload).desc(), Resource.id.desc()),
    }[sort]
    return [resource_view(r, o) for r, o in db.execute(query.order_by(*order).offset((page - 1) * limit).limit(limit)).all()]


@router.get("/resources/{resource_id}/capacity-history")
def capacity_history(
    resource_id: str,
    page: int = Query(1, ge=1),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resource = db.get(Resource, resource_id)
    org = db.get(Organization, resource.organization_id) if resource else None
    if not org or (not can_manage_organization(db, org, user) and user.role not in {"OPERATOR", "ADMIN"}):
        raise HTTPException(404, "Resource not found")
    records = db.scalars(select(CapacityRecord).where(CapacityRecord.resource_id == resource_id).order_by(CapacityRecord.created_at.desc(), CapacityRecord.id.desc()).offset((page - 1) * 50).limit(50)).all()
    return [{
        "id": row.id,
        "request_id": row.request_id,
        "previous_capacity": row.previous_capacity,
        "capacity": row.capacity,
        "previous_workload": row.previous_workload,
        "workload": row.workload,
        "previous_available": row.previous_available,
        "available": row.available,
        "reason": row.reason,
        "created_at": row.created_at,
    } for row in records]


@router.patch("/resources/{resource_id}")
def update_resource(
    resource_id: str,
    data: ResourcePatchIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resource = db.get(Resource, resource_id)
    org = db.get(Organization, resource.organization_id) if resource else None
    if not org or not can_manage_organization(db, org, user):
        raise HTTPException(404, "Resource not found")
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(422, "At least one resource field is required")
    if any(changes.get(key, object()) is None for key in ("title", "category", "description", "capacity", "current_workload", "available", "service_radius_km")):
        raise HTTPException(422, "Required resource fields cannot be empty")
    before = snapshot(resource)
    for key, value in changes.items():
        setattr(resource, key, value)
    if resource.current_workload > resource.capacity:
        raise HTTPException(422, "Current workload cannot exceed capacity")
    if resource.available_from and resource.available_until and resource.available_from.replace(tzinfo=timezone.utc) >= resource.available_until.replace(tzinfo=timezone.utc):
        raise HTTPException(422, "Availability window must end after it begins")
    record_capacity(db, resource, user, "Organization updated resource", before)
    audit(db, user, "resource.update", "resource", resource.id, {"fields": list(changes)})
    db.commit()
    return resource_view(resource, org)
