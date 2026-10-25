from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import AppSetting

GPS_RADIUS = "gps_radius_m"


async def gps_radius(db: AsyncSession) -> int:
    row = await db.get(AppSetting, GPS_RADIUS)
    value = int(row.value) if row else get_settings().gps_radius_default_m
    return max(100, min(300, value))  # TZ: 100–300 m


async def radius_for_district(db: AsyncSession, district_id: int) -> int:
    """Tumanning o'z radiusi bo'lsa — shu, bo'lmasa umumiy."""
    from app.models import District
    d = await db.get(District, district_id)
    if d and d.gps_radius_m:
        return max(100, min(300, d.gps_radius_m))
    return await gps_radius(db)
