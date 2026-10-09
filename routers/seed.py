import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.seed import delete_all, has_data, load_demo_data

router = APIRouter(tags=["Datos de demostración"])


@router.post("/seed", summary="Cargar datos de demostración")
def load_seed(reset: bool = False, db: Session = Depends(get_db)):
    """Carga 3 vacantes, 9 candidatos y 10 postulaciones. Con reset=true BORRA antes todos los datos del ATS."""
    if has_data(db):
        if not reset:
            raise HTTPException(
                status_code=409,
                detail="Ya hay datos cargados. Usa /seed?reset=true para borrarlos y cargar los de demostración.",
            )
        # Deleting everything must be explicitly enabled, so nobody can wipe a deployed API
        if os.getenv("ALLOW_DATA_RESET", "false").lower() != "true":
            raise HTTPException(status_code=403, detail="El reinicio de datos está deshabilitado en este entorno.")
        delete_all(db)
    return {"message": "Datos de demostración cargados", "summary": load_demo_data(db)}
