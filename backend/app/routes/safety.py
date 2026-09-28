from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AbuseReport, Request, User
from ..schemas import AbuseReportIn, AbuseResolutionIn
from ..security import current_user, staff
from ..services.lifecycle import audit

router = APIRouter(prefix="/api/v1", tags=["safety"])


def view(report: AbuseReport) -> dict:
    return {
        "id": report.id,
        "request_id": report.request_id,
        "category": report.category,
        "reason": report.reason,
        "status": report.status,
        "resolution": report.resolution,
        "created_at": report.created_at,
    }


@router.post("/reports/abuse", status_code=201)
def report_abuse(
    data: AbuseReportIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if data.request_id:
        request = db.get(Request, data.request_id)
        if not request or not (
            request.owner_id == user.id
            or user.role in {"OPERATOR", "ADMIN"}
            or (request.visibility_scope == "PUBLIC" and request.verification == "VERIFIED")
        ):
            raise HTTPException(404, "Request not found")
    report = AbuseReport(reporter_id=user.id, **data.model_dump())
    db.add(report)
    db.flush()
    audit(db, user, "abuse.report", "abuse_report", report.id, {"category": report.category})
    db.commit()
    return view(report)


@router.get("/admin/reports/abuse")
def abuse_queue(
    status: str | None = Query(default=None, max_length=24),
    actor: User = Depends(staff),
    db: Session = Depends(get_db),
):
    query = select(AbuseReport)
    if status:
        query = query.where(AbuseReport.status == status)
    return [view(item) for item in db.scalars(query.order_by(AbuseReport.created_at.desc()).limit(100)).all()]


@router.post("/admin/reports/abuse/{report_id}/resolve")
def resolve_abuse(
    report_id: str,
    data: AbuseResolutionIn,
    actor: User = Depends(staff),
    db: Session = Depends(get_db),
):
    report = db.get(AbuseReport, report_id)
    if not report:
        raise HTTPException(404, "Report not found")
    report.status = data.status
    report.resolution = data.resolution
    audit(db, actor, "abuse.resolve", "abuse_report", report.id, data.model_dump())
    db.commit()
    return view(report)
