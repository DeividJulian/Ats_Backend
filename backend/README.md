# Portal ATS para pymes — Backend

API que permite publicar vacantes, registrar candidatos y **ordenarlos automáticamente según su ajuste al cargo** usando procesamiento de lenguaje natural (NLP) implementado desde cero.

Proyecto final de Programación Orientada a la Web — Universidad Cooperativa de Colombia.

- **Frontend:** `<URL del repositorio del frontend>` (Angular)
- **API desplegada:** `<URL del backend desplegado>`

## Tecnologías

- Python + FastAPI
- SQLAlchemy 2 + PostgreSQL en [Neon](https://neon.com) (psycopg v3)
- Pydantic v2 para validación
- pypdf para leer hojas de vida en PDF
- pytest para pruebas

## Estructura

El código está en inglés; las rutas, los campos JSON y todos los mensajes que ve el usuario están en español.

```
backend/
├── main.py              # App, CORS, logging, errores; registra los routers automáticamente
├── database.py          # Conexión y sesión de base de datos
├── errors.py            # Mensajes de error en español
├── models/              # Tablas: jobs (vacantes), candidates (candidatos), applications (postulaciones)
├── schemas/             # Validación de entrada y salida (alias en español)
├── routers/             # Endpoints agrupados por recurso
├── services/
│   ├── nlp.py           # Normalización y tokenización en español
│   ├── skills.py        # Catálogo de habilidades y extracción
│   ├── profile.py       # Años de experiencia y nivel educativo
│   ├── similarity.py    # TF-IDF + similitud coseno
│   ├── scoring.py       # Puntaje de ajuste explicable
│   ├── matching.py      # Une base de datos y puntaje
│   ├── resume.py        # Lectura de hojas de vida en PDF
│   ├── pipeline.py      # Flujo de estados de la postulación
│   ├── stats.py         # Embudo y brechas de talento
│   └── seed.py          # Datos de demostración
└── tests/               # 44 pruebas automatizadas
```

## Instalación y ejecución

```
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Crea un archivo `.env` (puedes copiar `.env.example`) con la cadena de conexión de tu base:

```
DATABASE_URL=postgresql+psycopg://usuario:clave@host:5432/base
```

Si copias la cadena desde Neon, cambia el inicio `postgresql://` por `postgresql+psycopg://` y deja los parámetros del final (`?sslmode=require...`). Para desarrollo local también sirve SQLite: `DATABASE_URL=sqlite:///./ats.db`.

```
uvicorn main:app --reload
```

Documentación interactiva: `http://127.0.0.1:8000/docs`. Para ver el sistema con datos, ejecuta `POST /seed`.

## Cómo funciona la IA

El ranking de candidatos usa NLP implementado sin librerías externas:

1. **Extracción de perfil:** del texto de la hoja de vida se detectan habilidades (catálogo con sinónimos), años de experiencia y nivel educativo.
2. **Similitud TF-IDF:** se compara el texto del perfil con el de la vacante usando TF-IDF y similitud coseno.
3. **Puntaje de ajuste (0–100):** habilidades 50 %, similitud de texto 20 %, experiencia 20 % y educación 10 %. Solo se evalúa lo que la vacante exige y los pesos se reparten entre esos criterios.
4. **Explicabilidad:** cada puntaje incluye el desglose, las habilidades que cumple y las que le faltan, y una explicación en texto.
5. **Sin sesgos personales:** el puntaje nunca usa el nombre, el correo ni datos personales del candidato.

Clasificación: alto (≥ 75), medio (≥ 50), bajo (< 50).

## Endpoints

| Recurso | Endpoints |
|---|---|
| Vacantes | `POST /vacantes`, `GET /vacantes`, `GET /vacantes/{id}`, `PUT /vacantes/{id}`, `PATCH /vacantes/{id}/estado`, `DELETE /vacantes/{id}` |
| Candidatos | `POST /candidatos`, `GET /candidatos`, `GET /candidatos/{id}`, `PUT /candidatos/{id}`, `DELETE /candidatos/{id}`, `POST /candidatos/{id}/cv` (PDF) |
| Postulaciones | `POST /postulaciones`, `GET /postulaciones`, `GET /postulaciones/{id}`, `PATCH /postulaciones/{id}/estado`, `DELETE /postulaciones/{id}` |
| Ranking | `GET /vacantes/{id}/ranking`, `GET /vacantes/{id}/candidatos-sugeridos`, `POST /postulaciones/{id}/recalcular`, `POST /vacantes/{id}/recalcular-ranking` |
| NLP | `POST /nlp/analizar-texto`, `POST /nlp/similitud` |
| Análisis | `GET /estadisticas` |
| Utilidades | `POST /seed`, `GET /health` |

### Flujo de estados

`nuevo → preseleccionado → entrevista → oferta → contratado`. Desde cualquier estado activo se puede pasar a `rechazado`. Los estados `contratado` y `rechazado` son finales.

### Códigos de error

Todos responden `{"detail": "mensaje"}` en español:

| Código | Significado |
|---|---|
| `404` | El recurso no existe |
| `409` | Conflicto: correo duplicado, postulación repetida, vacante cerrada, cambio de estado no permitido o datos ya cargados en `/seed` |
| `422` | Datos inválidos; el mensaje indica cada campo, por ejemplo `nombre: debe tener al menos 2 caracteres` |
| `500` | Error interno de base de datos |

`POST /seed?reiniciar=true` **borra todos los datos del ATS** antes de cargar los de demostración.

## Pruebas

Las pruebas usan su propia base SQLite (`test_ats.db`), así que nunca tocan la base real:

```
pip install -r requirements-dev.txt
python -m pytest -q
```
