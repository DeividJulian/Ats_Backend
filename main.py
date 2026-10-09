import importlib
import logging
import pkgutil
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

import models  # noqa: F401  (registers every table)
import routers
from database import Base, engine
from errors import http_message, validation_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ats.api")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Portal ATS para pymes", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Automatically register every module in routers/ that defines `router`
for _, module_name, _ in pkgutil.iter_modules(routers.__path__):
    module = importlib.import_module(f"routers.{module_name}")
    if hasattr(module, "router"):
        app.include_router(module.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    logger.info("%s %s -> %s (%.0f ms)", request.method, request.url.path, response.status_code, ms)
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    messages = []
    for e in exc.errors():
        # For malformed JSON, "loc" holds the character position, not a field name
        field = "" if e["type"] == "json_invalid" else ".".join(
            str(x) for x in e["loc"] if x not in ("body", "query", "path")
        )
        message = validation_message(e)
        messages.append(f"{field}: {message}" if field else message)
    logger.warning("Validación fallida en %s %s: %s", request.method, request.url.path, messages)
    return JSONResponse(status_code=422, content={"detail": "; ".join(messages)})


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": http_message(exc.detail)}, headers=exc.headers)


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, exc: IntegrityError):
    logger.warning("Violación de integridad en %s %s", request.method, request.url.path)
    return JSONResponse(status_code=409, content={"detail": "La operación viola una restricción de la base de datos"})


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    logger.error("Error de base de datos en %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Error interno de base de datos"})


@app.get("/", tags=["Sistema"], summary="Inicio")
def root():
    return {"message": "API del Portal ATS funcionando"}


@app.get("/health", tags=["Sistema"], summary="Estado del servicio")
def health():
    return {"status": "ok"}
