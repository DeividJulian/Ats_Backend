import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "Falta DATABASE_URL. Crea el archivo .env (puedes copiar .env.example) "
        "con una línea como: DATABASE_URL=postgresql://usuario:clave@host:5432/base"
    )

# Providers like Neon hand out "postgresql://..." or "postgres://..."; SQLAlchemy needs the psycopg (v3) driver
for prefix in ("postgresql://", "postgres://"):
    if DATABASE_URL.startswith(prefix):
        DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len(prefix):]

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
