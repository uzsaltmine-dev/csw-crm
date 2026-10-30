from sqlalchemy.ext.asyncio import AsyncSession

from app import realtime
from app.models import Request, RequestEvent


def record(db: AsyncSession, req: Request, actor_id: int | None, note: str | None = None) -> None:
    db.add(RequestEvent(request_id=req.id, status=req.status, actor_id=actor_id, note=note))


async def broadcast(req: Request) -> None:
    """Commit'dan keyin chaqiriladi: Manager, GPS xodimi va haydovchi ekranlari yangilanadi."""
    await realtime.emit_request_updated({
        "id": req.id, "number": req.number, "status": req.status.value,
        "district_id": req.district_id, "driver_id": req.driver_id, "naryad_no": req.naryad_no, "stage": req.stage,
    })
