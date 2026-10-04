import importlib
import pkgutil

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models  # noqa: F401  (registers every table)
import routers
from database import Base, engine

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


@app.get("/", tags=["Sistema"], summary="Inicio")
def root():
    return {"mensaje": "API del Portal ATS funcionando"}


@app.get("/health", tags=["Sistema"], summary="Estado del servicio")
def health():
    return {"status": "ok"}
