from dataclasses import dataclass

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import invalid

ALLOWED = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


@dataclass
class UploadedImage:
    data: bytes
    content_type: str
    ext: str


async def read_image(file: UploadFile) -> UploadedImage:
    if file.content_type not in ALLOWED:
        raise invalid("bad_file_type", "Faqat JPEG, PNG yoki WEBP rasm qabul qilinadi")
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise invalid("file_too_large", f"Fayl {get_settings().max_upload_mb} MB dan katta")
    if not data:
        raise invalid("empty_file", "Fayl bo'sh")
    return UploadedImage(data=data, content_type=file.content_type, ext=ALLOWED[file.content_type])
