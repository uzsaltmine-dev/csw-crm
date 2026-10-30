from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, get_storage, require_roles
from app.models import User
from app.models.enums import FileKind, Role
from app.repositories import requests as req_repo
from app.schemas import ActOut, CompleteIn, CompleteOut, DriverTaskOut, FailIn, FileOut, LocationIn, RequestOut
from app.services import driver_service, schedule
from app.services.files import read_image
from app.services.storage import Storage

router = APIRouter(prefix="/driver", tags=["driver"])
Driver = Depends(require_roles(Role.driver))


@router.get("/today")
async def today(user: User = Driver, db: AsyncSession = DB) -> dict:
    """Smenasiz: bugungi ish jadvalidagi mashina (bo'lsa)."""
    plan = await schedule.for_driver_today(db, user.id)
    return {"day": schedule.today(), "vehicle": {"id": plan.vehicle.id, "plate": plan.vehicle.plate, "model": plan.vehicle.model}
            if plan else None, "service": plan.service if plan else None}


@router.get("/done", response_model=list[RequestOut])
async def done(user: User = Driver, db: AsyncSession = DB):
    """Bajarilganlar (yashil)."""
    return await req_repo.done_for_driver(db, user.id)


@router.get("/tasks", response_model=list[DriverTaskOut])
async def tasks(user: User = Driver, db: AsyncSession = DB):
    out = []
    for r in await req_repo.active_for_driver(db, user.id):
        item = DriverTaskOut.model_validate(r)
        item.files = list((await req_repo.files_for(db, r.id)).keys())
        out.append(item)
    return out


@router.post("/requests/{request_id}/enroute", response_model=RequestOut)
async def enroute(request_id: int, user: User = Driver, db: AsyncSession = DB):
    return await driver_service.set_enroute(db, user, request_id)


@router.post("/requests/{request_id}/files", response_model=FileOut)
async def upload(request_id: int, kind: FileKind = Form(...), file: UploadFile = File(...),
                 lat: float | None = Form(None), lng: float | None = Form(None), accuracy: float | None = Form(None, ge=0),
                 user: User = Driver, db: AsyncSession = DB, storage: Storage = Depends(get_storage)):
    image = await read_image(file)
    return await driver_service.upload_file(db, storage, user, request_id, kind, image, lat, lng,
                                            round(accuracy) if accuracy is not None else None)


@router.post("/location", status_code=204)
async def location(body: LocationIn, user: User = Driver, db: AsyncSession = DB):
    await driver_service.report_location(db, user, body.lat, body.lng)


@router.post("/requests/{request_id}/complete", response_model=CompleteOut)
async def complete(request_id: int, body: CompleteIn, user: User = Driver, db: AsyncSession = DB):
    req, act = await driver_service.complete(db, user, request_id, driver_service.CompleteInput(**body.model_dump()))
    return CompleteOut(request=RequestOut.model_validate(req), act=ActOut.model_validate(act))


@router.post("/requests/{request_id}/fail", response_model=RequestOut)
async def fail(request_id: int, body: FailIn, user: User = Driver, db: AsyncSession = DB):
    return await driver_service.fail(db, user, request_id, body.reason, body.note)
