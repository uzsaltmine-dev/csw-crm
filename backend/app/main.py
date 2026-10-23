import logging
from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, driver, gps
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.middleware import CsrfHeaderMiddleware, RequestContextMiddleware
from app.realtime import sio
from app.services.storage import MemoryStorage, MinioStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def create_app(storage=None) -> FastAPI:
    s = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.storage = storage or (MemoryStorage() if s.storage_backend == "memory" else MinioStorage(s))
        yield

    app = FastAPI(title="CSW Chiqindi CRM API", version="0.1.0", lifespan=lifespan)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_middleware(CsrfHeaderMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_list, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Request-ID"])
    for r in (auth.router, driver.router, gps.router):
        app.include_router(r, prefix="/api/v1")

    @app.get("/api/health", tags=["system"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
# uvicorn app.main:asgi_app — Socket.IO /socket.io yo'lida, qolgani FastAPI
asgi_app = socketio.ASGIApp(sio, other_asgi_app=app)
