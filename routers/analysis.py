from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.stats import compute_statistics

router = APIRouter(tags=["Análisis"])


@router.get("/stats", summary="Estadísticas del proceso de selección")
def statistics(db: Session = Depends(get_db)):
    """Embudo de selección, puntaje promedio por vacante, habilidades más pedidas y brechas de talento."""
    return compute_statistics(db)
