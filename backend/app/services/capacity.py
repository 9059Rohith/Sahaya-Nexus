from sqlalchemy.orm import Session

from ..models import CapacityRecord, Resource, User


def snapshot(resource: Resource) -> tuple[int, int, bool]:
    return resource.capacity, resource.current_workload, resource.available


def record_capacity(
    db: Session,
    resource: Resource,
    actor: User,
    reason: str,
    before: tuple[int, int, bool] | None = None,
    request_id: str | None = None,
) -> None:
    after = snapshot(resource)
    if before == after:
        return
    db.add(CapacityRecord(
        resource_id=resource.id,
        actor_id=actor.id,
        request_id=request_id,
        previous_capacity=before[0] if before else None,
        capacity=after[0],
        previous_workload=before[1] if before else None,
        workload=after[1],
        previous_available=before[2] if before else None,
        available=after[2],
        reason=reason,
    ))
