from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import utcnow
from app.models import District, NaryadCounter, Provider


async def next_number(db: AsyncSession, district_id: int) -> str:
    """BTE-2026-00042: xizmat ko'rsatuvchi kodi, yil, tartib raqami.

    Hisoblagich qatori FOR UPDATE bilan qulflanadi, shuning uchun bir vaqtda
    biriktirilgan ikki ariza bir xil raqam olmaydi. Chaqiruvchi commit qiladi.
    """
    district = await db.get(District, district_id)
    provider = (await db.execute(select(Provider).where(Provider.region_id == district.region_id))).scalar_one_or_none()
    if not provider:
        raise AppError(500, "provider_missing", "Bu viloyat uchun xizmat ko'rsatuvchi kompaniya sozlanmagan")
    year = utcnow().year
    q = select(NaryadCounter).where(NaryadCounter.provider_id == provider.id, NaryadCounter.year == year).with_for_update()
    counter = (await db.execute(q)).scalar_one_or_none()
    if not counter:
        counter = NaryadCounter(provider_id=provider.id, year=year, last_value=0)
        db.add(counter)
    counter.last_value += 1
    return f"{provider.code}-{year}-{counter.last_value:05d}"
