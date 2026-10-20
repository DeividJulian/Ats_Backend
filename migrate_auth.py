"""Brings an existing database to the email-code login, WITHOUT deleting any data.

create_all only creates tables that don't exist; it never changes existing ones. This script:
- adds users.verified (accounts that already existed are marked as verified, so they can keep entering),
- adds users.last_login,
- makes users.password_hash optional (passwords are no longer used),
- creates the verification_codes table.

It is safe to run many times: it only does what is missing. The app also runs it on startup.

Usage:  python migrate_auth.py
"""
import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger("ats.migrate")


def upgrade_auth_schema(engine: Engine) -> list[str]:
    """Applies the pending changes and returns what it did (empty if everything was up to date)."""
    import models  # noqa: F401  (registers every table)
    from database import Base

    done: list[str] = []
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        Base.metadata.create_all(bind=engine)
        return ["tablas creadas desde cero"]

    columns = {c["name"]: c for c in inspector.get_columns("users")}
    postgres = engine.dialect.name == "postgresql"
    timestamp = "TIMESTAMP WITH TIME ZONE" if postgres else "DATETIME"
    with engine.begin() as conn:
        if "verified" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN verified BOOLEAN NOT NULL DEFAULT FALSE"))
            # Whoever already had an account proved it before: they keep access
            conn.execute(text("UPDATE users SET verified = TRUE"))
            done.append("users.verified agregada (cuentas existentes verificadas)")
        if "last_login" not in columns:
            conn.execute(text(f"ALTER TABLE users ADD COLUMN last_login {timestamp}"))
            done.append("users.last_login agregada")
        # SQLite can't drop NOT NULL, but there the tables are recreated by the tests anyway
        if postgres and "password_hash" in columns and not columns["password_hash"]["nullable"]:
            conn.execute(text("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL"))
            done.append("users.password_hash ahora es opcional")

    if "verification_codes" not in inspector.get_table_names():
        Base.metadata.create_all(bind=engine)
        done.append("tabla verification_codes creada")
    for change in done:
        logger.info("Migración: %s", change)
    return done


if __name__ == "__main__":
    from database import engine

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(f"Base: {engine.url.render_as_string(hide_password=True)}")
    changes = upgrade_auth_schema(engine)
    print("\n".join(f"- {c}" for c in changes) if changes else "Todo estaba al día: no se cambió nada.")
