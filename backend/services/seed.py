"""Demo data: 3 jobs, 9 fictional candidates and 10 applications in different statuses."""
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.application import Application
from models.candidate import Candidate
from models.job import Job
from services.matching import evaluate, system_corpus
from services.profile import extract_education_level, extract_experience_years
from services.skills import extract_skills

JOBS = [
    {
        "title": "Desarrollador Backend Python Junior",
        "description": "Buscamos un desarrollador para construir y mantener APIs REST de nuestra plataforma de pedidos.",
        "requirements": "Python, FastAPI o Django, PostgreSQL, Git. Deseable Docker. Experiencia mínima de 1 año.",
        "min_experience_years": 1,
        "min_education_level": "tecnologo",
    },
    {
        "title": "Auxiliar Contable",
        "description": "Apoyo al área contable de una pyme comercial: registro de facturas, conciliaciones y nómina.",
        "requirements": "Contabilidad, Excel avanzado, facturación electrónica, Siigo. 2 años de experiencia.",
        "min_experience_years": 2,
        "min_education_level": "tecnico",
    },
    {
        "title": "Ejecutivo de Ventas",
        "description": "Responsable de prospectar clientes, negociar y cerrar ventas B2B, con seguimiento en CRM.",
        "requirements": "Ventas, negociación, atención al cliente, CRM, comunicación asertiva y liderazgo. Inglés deseable.",
        "min_experience_years": 3,
        "min_education_level": "profesional",
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
    (0, 0, "entrevista"), (0, 1, "preseleccionado"), (0, 2, "nuevo"), (0, 6, "rechazado"),
    (1, 3, "oferta"), (1, 4, "preseleccionado"), (1, 8, "nuevo"),
    (2, 5, "entrevista"), (2, 7, "nuevo"), (2, 6, "nuevo"),
]


def has_data(db: Session) -> bool:
    return any(db.query(m).first() for m in (Job, Candidate, Application))


def delete_all(db: Session) -> None:
    if db.get_bind().dialect.name == "postgresql":
        # Also restarts the id counters, so the demo data always gets ids 1, 2, 3...
        tables = ", ".join(m.__tablename__ for m in (Application, Candidate, Job))
        db.execute(text(f"TRUNCATE {tables} RESTART IDENTITY"))
    else:
        for model in (Application, Candidate, Job):
            db.query(model).delete()
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
    db.commit()
    # Summary keys are shown to the client, so they stay in Spanish
    return {"vacantes": len(jobs), "candidatos": len(candidates), "postulaciones": len(APPLICATIONS)}
