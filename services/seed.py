"""Demo data: 3 jobs, 9 fictional candidates, 10 applications in different statuses and 2 demo accounts."""
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.application import Application
from models.candidate import Candidate
from models.job import Job
from models.user import User
from services.matching import evaluate, system_corpus
from services.profile import extract_education_level, extract_experience_years
from services.security import hash_password
from services.skills import extract_skills

JOBS = [
    {
        "title": "Desarrollador Backend Python Junior",
        "description": "Buscamos un desarrollador para construir y mantener APIs REST de nuestra plataforma de pedidos.",
        "requirements": "Python, FastAPI o Django, PostgreSQL, Git. Deseable Docker. Experiencia mínima de 1 año.",
        "min_experience_years": 1,
        "min_education_level": "technologist",
    },
    {
        "title": "Auxiliar Contable",
        "description": "Apoyo al área contable de una pyme comercial: registro de facturas, conciliaciones y nómina.",
        "requirements": "Contabilidad, Excel avanzado, facturación electrónica, Siigo. 2 años de experiencia.",
        "min_experience_years": 2,
        "min_education_level": "technician",
    },
    {
        "title": "Ejecutivo de Ventas",
        "description": "Responsable de prospectar clientes, negociar y cerrar ventas B2B, con seguimiento en CRM.",
        "requirements": "Ventas, negociación, atención al cliente, CRM, comunicación asertiva y liderazgo. Inglés deseable.",
        "min_experience_years": 3,
        "min_education_level": "professional",
    },
]

CANDIDATES = [
    ("Camila Ortega", "camila.ortega@example.com",
     "Ingeniera de Sistemas con 3 años de experiencia desarrollando APIs REST con Python, FastAPI y PostgreSQL. "
     "Uso Git y Docker a diario. Trabajo en equipo y comunicación efectiva."),
    ("Sebastián Rojas", "sebastian.rojas@example.com",
     "Tecnólogo en desarrollo de software. 1 año de experiencia con Django, MySQL y JavaScript. Manejo de Git."),
    ("Valentina Cruz", "valentina.cruz@example.com",
     "Ingeniera de Sistemas recién egresada. Conocimientos en Java, Spring Boot y SQL. Proyectos con Git y Docker. "
     "Interés en pruebas de software."),
    ("Andrés Molina", "andres.molina@example.com",
     "Contador Público con 5 años de experiencia en contabilidad, facturación electrónica, nómina y conciliaciones "
     "bancarias. Excel avanzado y Siigo. Declaración de renta e impuestos."),
    ("Laura Benavides", "laura.benavides@example.com",
     "Técnica en asistencia administrativa con 2 años de experiencia en facturación y Excel. Atención al cliente."),
    ("Diego Paredes", "diego.paredes@example.com",
     "Administrador de empresas con 6 años de experiencia en ventas consultivas y negociación con clientes corporativos. "
     "CRM HubSpot, liderazgo de equipos comerciales y comunicación asertiva. Inglés B2."),
    ("Mariana Giraldo", "mariana.giraldo@example.com",
     "Profesional en mercadeo con 2 años de experiencia en marketing digital, redes sociales y SEO. Canva y Excel."),
    ("Felipe Zambrano", "felipe.zambrano@example.com",
     "Bachiller con 4 años de experiencia en ventas de mostrador y atención al cliente. Manejo de inventarios."),
    ("Natalia Pinzón", "natalia.pinzon@example.com",
     "Ingeniera industrial con 4 años de experiencia en logística, inventarios y compras. Excel y SAP. Liderazgo."),
]

# (job index, candidate index, final status)
APPLICATIONS = [
    (0, 0, "interview"), (0, 1, "shortlisted"), (0, 2, "new"), (0, 6, "rejected"),
    (1, 3, "offer"), (1, 4, "shortlisted"), (1, 8, "new"),
    (2, 5, "interview"), (2, 7, "new"), (2, 6, "new"),
]


# Accounts to try the app (shown on the login page). Admins are never created here: they come from ADMIN_EMAIL
DEMO_PASSWORD = "Demo1234"
DEMO_RECRUITER = ("Reclutador Demo", "reclutador@demo.com")
# The first demo candidate (Camila Ortega) also gets an account to try the candidate portal
DEMO_CANDIDATE_INDEX = 0


def has_data(db: Session) -> bool:
    return any(db.query(m).first() for m in (Job, Candidate, Application))


def delete_all(db: Session) -> None:
    """Deletes all ATS data and every non-admin account. Admin accounts are kept."""
    db.query(User).filter(User.role != "admin").delete()
    for model in (Application, Candidate, Job):
        db.query(model).delete()
    if db.get_bind().dialect.name == "postgresql":
        # Restart the id counters, so the demo data always gets ids 1, 2, 3...
        for model in (Application, Candidate, Job):
            db.execute(text(f"SELECT setval(pg_get_serial_sequence('{model.__tablename__}', 'id'), 1, false)"))
    db.commit()


def load_demo_data(db: Session) -> dict:
    jobs = []
    for data in JOBS:
        job = Job(**data)
        job.required_skills = extract_skills(f"{data['title']} {data['description']} {data['requirements']}")
        jobs.append(job)
    candidates = [
        Candidate(
            name=name,
            email=email,
            resume_text=resume,
            skills=extract_skills(resume),
            experience_years=extract_experience_years(resume),
            education_level=extract_education_level(resume),
        )
        for name, email, resume in CANDIDATES
    ]
    db.add_all(jobs + candidates)
    db.flush()

    corpus = system_corpus(db)
    for job_index, candidate_index, status in APPLICATIONS:
        result = evaluate(db, jobs[job_index], candidates[candidate_index], corpus)
        db.add(
            Application(
                job_id=jobs[job_index].id,
                candidate_id=candidates[candidate_index].id,
                score=result["score"],
                details=result,
                status=status,
            )
        )

    demo_candidate = candidates[DEMO_CANDIDATE_INDEX]
    accounts = [
        User(name=DEMO_RECRUITER[0], email=DEMO_RECRUITER[1], password_hash=hash_password(DEMO_PASSWORD), role="recruiter"),
        User(name=demo_candidate.name, email=demo_candidate.email, password_hash=hash_password(DEMO_PASSWORD),
             role="candidate", candidate_id=demo_candidate.id),
    ]
    # An account with the same email may already exist (for example an admin): it is left untouched
    existing = {email for (email,) in db.query(User.email).all()}
    db.add_all(a for a in accounts if a.email not in existing)
    db.commit()
    return {
        "jobs": len(jobs),
        "candidates": len(candidates),
        "applications": len(APPLICATIONS),
        "demo_accounts": [{"email": a.email, "role": a.role} for a in accounts],
        "demo_password": DEMO_PASSWORD,
    }
