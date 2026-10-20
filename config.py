"""Settings read from environment variables (.env file locally, Render dashboard in production)."""
import logging
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ats.config")

# Signs the session tokens. JWT_SECRET is the old name and still works.
# Without either, a random key is generated: sessions are lost on every restart.
SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or ""
if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(48)
    logger.warning("SECRET_KEY no está configurada: se generó una temporal (las sesiones se cierran al reiniciar)")
TOKEN_HOURS = float(os.getenv("TOKEN_HORAS", "12"))

# One-time codes sent by email
CODE_MINUTES = int(os.getenv("CODIGO_MINUTOS", "10"))
CODE_ATTEMPTS = int(os.getenv("CODIGO_INTENTOS", "5"))
CODE_WAIT_SECONDS = int(os.getenv("CODIGO_ESPERA_SEGUNDOS", "30"))

# Email delivery: consola | memoria | smtp | brevo
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "consola").strip().lower()
EMAIL_FROM = os.getenv("EMAIL_FROM", "no-reply@portal-ats.local")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Portal ATS")
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
