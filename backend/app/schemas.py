import json
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator

Category = Literal[
    "FOOD",
    "BLOOD",
    "ACCESSIBILITY",
    "COMMUNITY",
    "VOLUNTEER",
    "RESOURCE",
    "PUBLIC_SERVICE",
]


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class DeleteAccountIn(BaseModel):
    password: str


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    available: bool | None = None
    categories: list[Category] | None = None
    skills: list[str] | None = None
    languages: list[str] | None = None
    transport: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    capacity: int | None = Field(default=None, ge=1, le=1000000)


class InterpretIn(BaseModel):
    text: str = Field(min_length=10, max_length=3000)


class DuplicateIn(BaseModel):
    category: Category
    description: str = Field(min_length=12, max_length=3000)
    location_text: str = Field(min_length=3, max_length=240)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class RequestIn(BaseModel):
    client_submission_id: UUID | None = None
    category: Category
    description: str = Field(min_length=12, max_length=3000)
    location_text: str = Field(min_length=3, max_length=240)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_precision: Literal["EXACT", "APPROXIMATE", "PRIVATE"] = "APPROXIMATE"
    visibility_scope: Literal["PUBLIC", "PRIVATE"] = "PRIVATE"
    privacy_mode: bool = False
    quantity: int | None = Field(default=None, ge=1, le=1000000)
    unit: str | None = Field(default=None, max_length=48)
    deadline: datetime | None = None
    details: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_domain(self):
        if len(json.dumps(self.details)) > 10000:
            raise ValueError("Domain details exceed the size limit")
        if self.category == "BLOOD" and not self.details.get("facility_name"):
            raise ValueError("Blood coordination requires a named medical facility")
        if self.visibility_scope == "PUBLIC" and self.category not in {"COMMUNITY", "ACCESSIBILITY"}:
            raise ValueError("Only community and accessibility reports can opt into public discovery")
        if self.category == "FOOD" and (
            not self.quantity or not self.details.get("safe_until")
        ):
            raise ValueError("Food rescue requires quantity and safe-until time")
        if self.category == "FOOD":
            try:
                safe_until = datetime.fromisoformat(
                    self.details["safe_until"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError, AttributeError) as exc:
                raise ValueError(
                    "Food safe-until must be a valid date and time"
                ) from exc
            if safe_until.tzinfo is None:
                safe_until = safe_until.replace(tzinfo=timezone.utc)
            if safe_until <= datetime.now(timezone.utc):
                raise ValueError("Food safe-until must be in the future")
        if self.deadline:
            deadline = (
                self.deadline
                if self.deadline.tzinfo
                else self.deadline.replace(tzinfo=timezone.utc)
            )
            if deadline <= datetime.now(timezone.utc):
                raise ValueError("Deadline must be in the future")
        return self


class TransitionIn(BaseModel):
    to_status: str
    reason: str = Field(min_length=8, max_length=1000)
    evidence_url: str | None = Field(default=None, max_length=500)


class VerificationIn(BaseModel):
    decision: Literal["VERIFIED", "REJECTED"]
    reason: str = Field(min_length=8, max_length=1000)
    evidence_url: str | None = Field(default=None, max_length=500)


class PriorityIn(BaseModel):
    urgency: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    reason: str = Field(min_length=8, max_length=1000)


class FollowUpIn(BaseModel):
    reason: str = Field(min_length=8, max_length=1000)


class VolunteerInterestIn(BaseModel):
    note: str = Field(default="", max_length=500)


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class OrganizationInviteIn(BaseModel):
    email: EmailStr


class MatchingWeightsIn(BaseModel):
    category_match: float = Field(ge=0, le=1)
    distance: float = Field(ge=0, le=1)
    availability: float = Field(ge=0, le=1)
    reliability: float = Field(ge=0, le=1)
    urgency_fit: float = Field(ge=0, le=1)
    capacity_fit: float = Field(ge=0, le=1)
    response_time: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def sum_to_one(self):
        if abs(sum(self.model_dump().values()) - 1) > 0.001:
            raise ValueError("Matching weights must add up to 1")
        return self


class OrganizationIn(BaseModel):
    name: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=3000)
    service_categories: list[Category] = Field(default_factory=list)
    service_area: str = Field(default="", max_length=240)


class ResourceIn(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    category: Category
    description: str = Field(default="", max_length=3000)
    capacity: int = Field(ge=1, le=1000000)
    current_workload: int = Field(default=0, ge=0, le=1000000)
    available: bool = True
    available_from: datetime | None = None
    available_until: datetime | None = None
    expires_at: datetime | None = None
    service_radius_km: int = Field(default=25, ge=1, le=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def validate_capacity_window(self):
        if self.current_workload > self.capacity:
            raise ValueError("Current workload cannot exceed capacity")
        if self.available_from and self.available_until and self.available_from >= self.available_until:
            raise ValueError("Availability window must end after it begins")
        return self


class ResourcePatchIn(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=180)
    category: Category | None = None
    description: str | None = Field(default=None, max_length=3000)
    capacity: int | None = Field(default=None, ge=1, le=1000000)
    current_workload: int | None = Field(default=None, ge=0, le=1000000)
    available: bool | None = None
    available_from: datetime | None = None
    available_until: datetime | None = None
    expires_at: datetime | None = None
    service_radius_km: int | None = Field(default=None, ge=1, le=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class AssignmentIn(BaseModel):
    resource_id: str | None = None
    volunteer_id: str | None = None
    reason: str = Field(min_length=8, max_length=1000)

    @model_validator(mode="after")
    def one_target(self):
        if bool(self.resource_id) == bool(self.volunteer_id):
            raise ValueError("Provide one resource or one volunteer")
        return self


class OutcomeIn(BaseModel):
    summary: str = Field(min_length=10, max_length=3000)
    evidence_url: str | None = Field(default=None, max_length=500)
    impact_value: int | None = Field(default=None, ge=0)
    impact_unit: str | None = Field(default=None, max_length=60)


class FeedbackIn(BaseModel):
    answer: Literal["YES", "NO", "PARTIALLY"]
    comment: str = Field(default="", max_length=2000)


class AbuseReportIn(BaseModel):
    category: Literal["SPAM", "FRAUD", "SAFETY", "PRIVACY", "OTHER"]
    reason: str = Field(min_length=12, max_length=2000)
    request_id: str | None = None


class AbuseResolutionIn(BaseModel):
    status: Literal["REVIEWED", "ACTIONED", "DISMISSED"]
    resolution: str = Field(min_length=8, max_length=2000)


class FeatureFlagsIn(BaseModel):
    voice: bool
    ai: bool
    maps: bool
    blood_coordination: bool
    advanced_matching: bool


class PolicyIn(BaseModel):
    feature_flags: FeatureFlagsIn
    pilot_enabled: bool
    pilot_categories: list[Category]
    pilot_service_areas: list[str] = Field(max_length=100)
    priority_high_hours: int = Field(ge=1, le=168)
    priority_critical_hours: int = Field(ge=1, le=48)
    verification_evidence_categories: list[Category]
    service_radius_km: int = Field(ge=1, le=500)
    escalation_hours: int = Field(ge=1, le=720)
    retention_days: int | None = Field(default=None, ge=30, le=3650)

    @model_validator(mode="after")
    def validate_policy(self):
        if self.priority_critical_hours > self.priority_high_hours:
            raise ValueError("Critical window must be no longer than high window")
        if self.pilot_enabled and not self.pilot_categories:
            raise ValueError("Pilot mode requires at least one category")
        if any(len(area) < 2 or len(area) > 120 for area in self.pilot_service_areas):
            raise ValueError("Pilot service area names must be 2-120 characters")
        return self
