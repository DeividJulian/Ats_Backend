import os

# IMPORTANT: set BEFORE importing the app so the tests never touch the real database
os.environ["DATABASE_URL"] = "sqlite:///./test_ats.db"
os.environ["ALLOW_DATA_RESET"] = "true"
os.environ["JWT_SECRET"] = "test-secret-for-pytest-only-0123456789abcdef"
# Tests never call a real AI provider: blank values win over a developer's .env (load_dotenv doesn't override)
for _name in ("AI_PROVIDER", "AI_API_KEY", "AI_MODEL", "AI_BASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"):
    os.environ[_name] = ""

import pytest
from fastapi.testclient import TestClient

from database import Base, SessionLocal, engine
from main import app
from models.user import User
from services.security import create_token, hash_password

assert str(engine.url).startswith("sqlite"), "Tests must only run against SQLite"


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


ADMIN = {"name": "Admin Pruebas", "email": "admin@test.com", "password": "Admin1234"}


@pytest.fixture
def admin_id():
    with SessionLocal() as db:
        user = User(name=ADMIN["name"], email=ADMIN["email"], password_hash=hash_password(ADMIN["password"]), role="admin")
        db.add(user)
        db.commit()
        return user.id


def client_for(user_id: int, role: str) -> TestClient:
    return TestClient(app, headers={"Authorization": f"Bearer {create_token(user_id, role)}"})


@pytest.fixture
def client(admin_id):
    """Logged in as an administrator, who can use every endpoint."""
    return client_for(admin_id, "admin")


@pytest.fixture
def anon():
    """No session at all."""
    return TestClient(app)


def login(email: str, password: str) -> TestClient:
    r = TestClient(app).post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return TestClient(app, headers={"Authorization": f"Bearer {r.json()['access_token']}"})


@pytest.fixture
def demo_data(client):
    r = client.post("/seed")
    assert r.status_code == 200
    return r.json()["summary"]


def make_pdf(text: str) -> bytes:
    """Minimal one-page PDF with text (one line per newline), to test resume reading without extra libraries."""
    lines = " T* ".join(f"({line}) Tj" for line in text.split("\n"))
    content = f"BT /F1 12 Tf 14 TL 50 750 Td {lines} ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return pdf
