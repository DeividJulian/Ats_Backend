from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from services.seed import delete_all, has_data, load_demo_data

router = APIRouter(tags=["Datos de demostración"])


@router.post("/seed", summary="Cargar datos de demostración")
def load_seed(reset: bool = Query(False, alias="reiniciar"), db: Session = Depends(get_db)):
    """Carga 3 vacantes, 9 candidatos y 10 postulaciones. Con reiniciar=true BORRA antes todos los datos del ATS."""
    if has_data(db):
        if not reset:
            raise HTTPException(
                status_code=409,
                detail="Ya hay datos cargados. Usa /seed?reiniciar=true para borrarlos y cargar los de demostración.",
            )
        delete_all(db)
    return {"mensaje": "Datos de demostración cargados", "resumen": load_demo_data(db)}
