import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(24), default="CITIZEN")
    available: Mapped[bool] = mapped_column(Boolean, default=False)
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    categories: Mapped[list] = mapped_column(JSON, default=list)
    languages: Mapped[list] = mapped_column(JSON, default=list)
    transport: Mapped[str | None] = mapped_column(String(80), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="UNDER_REVIEW")
    service_categories: Mapped[list] = mapped_column(JSON, default=list)
    service_area: Mapped[str] = mapped_column(String(240), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_organization_member"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    invited_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="INVITED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Resource(Base):
    __tablename__ = "resources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(48), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    current_workload: Mapped[int] = mapped_column(Integer, default=0)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    available_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    service_radius_km: Mapped[int] = mapped_column(Integer, default=25)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CapacityRecord(Base):
    __tablename__ = "capacity_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    request_id: Mapped[str | None] = mapped_column(ForeignKey("requests.id"), nullable=True)
    previous_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capacity: Mapped[int] = mapped_column(Integer)
    previous_workload: Mapped[int | None] = mapped_column(Integer, nullable=True)
    workload: Mapped[int] = mapped_column(Integer)
    previous_available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    available: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str] = mapped_column(String(180))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Request(Base):
    __tablename__ = "requests"
    __table_args__ = (UniqueConstraint("owner_id", "client_submission_id", name="uq_request_owner_submission"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    client_submission_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    submission_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    category: Mapped[str] = mapped_column(String(48), index=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="SUBMITTED", index=True)
    verification: Mapped[str] = mapped_column(String(24), default="UNVERIFIED")
    urgency: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    priority_reason: Mapped[str] = mapped_column(Text, default="")
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(48), nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    location_text: Mapped[str] = mapped_column(String(240))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_precision: Mapped[str] = mapped_column(String(16), default="APPROXIMATE")
    visibility_scope: Mapped[str] = mapped_column(String(16), default="PRIVATE")
    privacy_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )
    retained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    events: Mapped[list["RequestEvent"]] = relationship(
        back_populates="request", order_by="RequestEvent.created_at"
    )


class RequestEvent(Base):
    __tablename__ = "request_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text)
    evidence_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    system_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    request: Mapped[Request] = relationship(back_populates="events")


class Assignment(Base):
    __tablename__ = "assignments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    request_id: Mapped[str] = mapped_column(
        ForeignKey("requests.id"), unique=True, index=True
    )
    resource_id: Mapped[str | None] = mapped_column(
        ForeignKey("resources.id"), nullable=True
    )
    volunteer_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    rationale: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="OFFERED")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Outcome(Base):
    __tablename__ = "outcomes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"), unique=True)
    summary: Mapped[str] = mapped_column(Text)
    evidence_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    submitted_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    verified_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    impact_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impact_unit: Mapped[str | None] = mapped_column(String(60), nullable=True)


class Evidence(Base):
    __tablename__ = "request_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"), index=True)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    original_name: Mapped[str] = mapped_column(String(180))
    mime_type: Mapped[str] = mapped_column(String(50))
    size: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(36))
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MatchingSetting(Base):
    __tablename__ = "matching_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    weights: Mapped[dict] = mapped_column(JSON)
    updated_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    request_id: Mapped[str | None] = mapped_column(ForeignKey("requests.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"), index=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OutcomeFeedback(Base):
    __tablename__ = "outcome_feedback"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"), unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    answer: Mapped[str] = mapped_column(String(16))
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AbuseReport(Base):
    __tablename__ = "abuse_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    reporter_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    request_id: Mapped[str | None] = mapped_column(ForeignKey("requests.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(48))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="OPEN")
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SavedOrganization(Base):
    __tablename__ = "saved_organizations"
    __table_args__ = (UniqueConstraint("user_id", "organization_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DuplicateLink(Base):
    __tablename__ = "duplicate_links"
    __table_args__ = (UniqueConstraint("request_id", "existing_request_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"), index=True)
    existing_request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"))
    confirmed_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VolunteerInterest(Base):
    __tablename__ = "volunteer_interests"
    __table_args__ = (UniqueConstraint("request_id", "volunteer_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"), index=True)
    volunteer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    note: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PlatformSetting(Base):
    __tablename__ = "platform_settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    updated_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
