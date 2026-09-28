from sqlalchemy.orm import Session

from ..models import PlatformSetting

DEFAULT_POLICY = {
    "feature_flags": {
        "voice": True,
        "ai": True,
        "maps": True,
        "blood_coordination": True,
        "advanced_matching": True,
    },
    "pilot_enabled": False,
    "pilot_categories": ["FOOD", "BLOOD", "ACCESSIBILITY", "COMMUNITY", "VOLUNTEER", "RESOURCE", "PUBLIC_SERVICE"],
    "pilot_service_areas": [],
    "priority_high_hours": 6,
    "priority_critical_hours": 2,
    "verification_evidence_categories": [],
    "service_radius_km": 25,
    "escalation_hours": 24,
    "retention_days": None,
}


def get_policy(db: Session) -> dict:
    row = db.get(PlatformSetting, "policy")
    if row is None:
        return {**DEFAULT_POLICY, "feature_flags": DEFAULT_POLICY["feature_flags"].copy()}
    return {**DEFAULT_POLICY, **row.value, "feature_flags": {**DEFAULT_POLICY["feature_flags"], **row.value.get("feature_flags", {})}}
