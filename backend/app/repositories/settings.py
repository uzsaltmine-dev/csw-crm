from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import AppSetting

GPS_RADIUS = "gps_radius_m"


async def gps_radius(db: AsyncSession) -> int:
    row = await db.get(AppSetting, GPS_RADIUS)
    value = int(row.value) if row else get_settings().gps_radius_default_m
    return max(100, min(300, value))  # TZ: 100–300 m
