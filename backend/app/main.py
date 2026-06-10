from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine, wait_for_database
from app.routers import admin, auth, miniapp, teacher
from app.seed import seed_initial_data


logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="高中教务管理系统 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3810", "http://127.0.0.1:3810"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(teacher.router)
app.include_router(admin.router)
app.include_router(miniapp.router)


@app.on_event("startup")
def on_startup() -> None:
    logger.info("waiting for database...")
    wait_for_database()
    Base.metadata.create_all(bind=engine)
    Path(settings.backup_dir).mkdir(parents=True, exist_ok=True)

    db: Session = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()

    logger.info("startup complete")


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "message": "请求参数校验失败",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"message": exc.detail})


@app.exception_handler(Exception)
async def global_exception_handler(_: Request, exc: Exception) -> JSONResponse:  # noqa: BLE001
    logger.exception("unexpected error: %s", exc)
    return JSONResponse(status_code=500, content={"message": "服务器内部错误，请联系管理员"})


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
