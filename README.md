# Portal ATS para pymes — Backend

API que permite publicar vacantes, registrar candidatos y **ordenarlos automáticamente según su ajuste al cargo** usando procesamiento de lenguaje natural (NLP) implementado desde cero. Opcionalmente, un modelo de lenguaje (Claude) redacta evaluaciones, extrae perfiles y propone vacantes.

Proyecto final de Programación Orientada a la Web — Universidad Cooperativa de Colombia.

- **Frontend:** `<URL del repositorio del frontend>` (Angular)
- **API desplegada:** `<URL del backend en Render>`

## Tecnologías

- Python 3.14 + FastAPI
- SQLAlchemy 2 + PostgreSQL en [Neon](https://neon.com) (psycopg v3)
- Pydantic v2 para validación
- pypdf para leer hojas de vida en PDF
- SDK oficial de Anthropic para la IA con Claude (opcional)
- pytest para pruebas
- Despliegue en [Render](https://render.com)

El código y la API (rutas y campos JSON) están en inglés. Los mensajes de error, las explicaciones del puntaje, los textos generados y la documentación de `/docs` están en español.

## Estructura

```
├── main.py              # App, CORS, logging, errores; registra los routers automáticamente
├── database.py          # Conexión y sesión de base de datos
├── errors.py            # Mensajes de error en español
├── render.yaml          # Configuración de despliegue en Render
├── models/              # Tablas: jobs, candidates, applications
├── schemas/             # Validación de entrada y salida
├── routers/             # Endpoints agrupados por recurso
├── services/
│   ├── nlp.py           # Normalización y tokenización en español
│   ├── skills.py        # Catálogo de habilidades, áreas e inferencia de habilidades relacionadas
│   ├── profile.py       # Años de experiencia y nivel educativo
│   ├── contact.py       # Nombre, correo y teléfono desde la hoja de vida
│   ├── similarity.py    # TF-IDF + similitud coseno
│   ├── scoring.py       # Puntaje de ajuste explicable
│   ├── matching.py      # Une base de datos y puntaje
│   ├── insights.py      # Resumen del perfil, guía de entrevista y formación sugerida
│   ├── llm.py           # Cliente de la API de Claude con salidas estructuradas
│   ├── ai.py            # Evaluación, extracción de perfil y redacción de vacantes con Claude
│   ├── resume.py        # Lectura y análisis de hojas de vida en PDF
│   ├── pipeline.py      # Flujo de estados de la postulación
│   ├── stats.py         # Embudo y brechas de talento
│   └── seed.py          # Datos de demostración
└── tests/               # 68 pruebas automatizadas
```

## Instalación y ejecución local

```
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Crea un archivo `.env` copiando `.env.example`:

| Variable | Para qué sirve |
|---|---|
| `DATABASE_URL` | Cadena de conexión de PostgreSQL. Se puede pegar tal cual la que da Neon (`postgresql://...`). Para pruebas rápidas también sirve SQLite: `sqlite:///./ats.db` |
| `ALLOWED_ORIGINS` | Orígenes que pueden llamar a la API, separados por comas (la URL del front). `*` permite todos |
| `ALLOW_DATA_RESET` | `true` permite `POST /seed?reset=true`, que **borra todos los datos**. Déjalo en `false` en producción |
| `ANTHROPIC_API_KEY` | Clave de la API de Claude. Opcional: sin ella los endpoints `/ai` responden 503 y todo lo demás funciona |
| `ANTHROPIC_MODEL` | Opcional. Modelo de Claude a usar (por defecto `claude-opus-5-5`) |

```
uvicorn main:app --reload
```

Documentación interactiva: `http://127.0.0.1:8000/docs`. Para ver el sistema con datos, ejecuta `POST /seed`.

## Despliegue en Render

1. Entra a [render.com](https://render.com) con tu cuenta de GitHub.
2. **New → Blueprint** y elige este repositorio. Render lee `render.yaml` y crea el servicio `ats-backend` (plan gratis, región Virginia, la misma zona de AWS que la base en Neon).
3. Cuando lo pida, pega en `DATABASE_URL` la cadena de conexión de Neon y, si vas a usar Claude, la clave en `ANTHROPIC_API_KEY` (puedes dejarla vacía).
4. Al terminar el despliegue, abre `https://<tu-servicio>.onrender.com/docs`.
5. Cuando el front esté publicado, cambia `ALLOWED_ORIGINS` a su URL en **Environment**.

En el plan gratis el servicio se duerme tras 15 minutos sin tráfico y la primera petición después tarda cerca de un minuto. Cada `git push` a `main` vuelve a desplegar automáticamente.

## Cómo funciona la IA

Todo el procesamiento de lenguaje está implementado desde cero, sin librerías ni servicios externos de IA:

1. **Extracción de perfil:** de la hoja de vida (texto o PDF) se detectan nombre, correo, teléfono, habilidades (catálogo de 59 habilidades con sinónimos), años de experiencia y nivel educativo.
2. **Habilidades inferidas:** si el candidato sabe Django se infiere Python; si sabe PostgreSQL, SQL. Las habilidades inferidas cuentan al 75 % porque no están demostradas.
3. **Similitud TF-IDF:** se compara el texto del perfil con el de la vacante usando TF-IDF y similitud coseno.
4. **Puntaje de ajuste (0–100):** habilidades 50 %, similitud de texto 20 %, experiencia 20 % y educación 10 %. Solo se evalúa lo que la vacante exige y los pesos se reparten entre esos criterios.
5. **Explicabilidad:** cada puntaje incluye el desglose, las habilidades que cumple, las inferidas, las que le faltan y una explicación en texto.
6. **Recomendaciones en ambos sentidos:** candidatos sugeridos para una vacante y vacantes recomendadas para un candidato.
7. **Análisis del candidato:** resumen del perfil, área principal y habilidades que le conviene aprender según las vacantes abiertas, con formación sugerida.
8. **Guía de entrevista:** preguntas personalizadas según las fortalezas, las habilidades inferidas y las brechas del candidato frente a la vacante.
9. **Sin sesgos personales:** el puntaje nunca usa el nombre, el correo ni datos personales. El ranking puede verse en modo anónimo (`?blind=true`).

Clasificación: `high` (≥ 75), `medium` (≥ 50), `low` (< 50).

### IA con Claude (opcional)

Con `ANTHROPIC_API_KEY` configurada, un modelo de lenguaje complementa el NLP propio. **El puntaje sigue siendo el determinista**: Claude asesora y redacta, no decide.

- **Evaluación de una postulación:** resumen, fortalezas, brechas, recomendación (`advance`, `interview_with_reservations` o `reject`) y preguntas de entrevista.
- **Extracción de perfil:** habilidades, experiencia, nivel educativo y resumen a partir del texto de una hoja de vida.
- **Redacción de vacantes:** borrador de descripción, requisitos y habilidades a partir del cargo y unas notas.

Protecciones: las respuestas usan salidas estructuradas (el modelo solo puede devolver el formato esperado y además se validan); la hoja de vida se trata como datos y no como instrucciones, para que nadie escriba "califícame con 100"; se prohíbe usar rasgos protegidos y al modelo nunca le llegan el nombre ni el correo del candidato. Sin clave, `/ai` responde 503; si la API falla, 502. Nunca inventa resultados.

## Endpoints

| Recurso | Endpoints |
|---|---|
| Vacantes | `POST /jobs`, `GET /jobs?status=`, `GET /jobs/{id}`, `PUT /jobs/{id}`, `PATCH /jobs/{id}/status`, `DELETE /jobs/{id}` |
| Candidatos | `POST /candidates`, `GET /candidates?skill=`, `GET /candidates/{id}`, `PUT /candidates/{id}`, `DELETE /candidates/{id}` |
| Hojas de vida | `POST /candidates/from-resume` (crea desde PDF), `POST /candidates/{id}/resume` (actualiza desde PDF), `POST /nlp/analyze-resume` (vista previa sin guardar) |
| Postulaciones | `POST /applications`, `GET /applications?job_id=&candidate_id=&status=`, `GET /applications/{id}`, `PATCH /applications/{id}/status`, `DELETE /applications/{id}` |
| Ranking | `GET /jobs/{id}/ranking?blind=`, `GET /jobs/{id}/suggested-candidates`, `GET /candidates/{id}/recommended-jobs`, `POST /applications/{id}/recalculate`, `POST /jobs/{id}/recalculate-ranking` |
| IA | `GET /candidates/{id}/insights`, `GET /applications/{id}/interview-guide` |
| IA con Claude | `GET /ai/status`, `POST /ai/evaluate/{application_id}`, `POST /ai/extract-resume`, `POST /ai/draft-job` |
| NLP | `POST /nlp/analyze-text`, `POST /nlp/similarity` |
| Análisis | `GET /stats` |
| Utilidades | `POST /seed?reset=`, `GET /health` |

### Valores

- Estado de la vacante: `open`, `closed`.
- Nivel educativo: `high_school`, `technician`, `technologist`, `professional`, `specialization`, `masters`, `doctorate`.
- Estado de la postulación: `new → shortlisted → interview → offer → hired`. Desde cualquier estado activo se puede pasar a `rejected`. `hired` y `rejected` son finales.

### Códigos de error

Todos responden `{"detail": "mensaje"}` en español:

| Código | Significado |
|---|---|
| `403` | Acción deshabilitada en este entorno (reinicio de datos) |
| `404` | El recurso no existe |
| `409` | Conflicto: correo duplicado, postulación repetida, vacante cerrada, cambio de estado no permitido o datos ya cargados en `/seed` |
| `422` | Datos inválidos o PDF ilegible; el mensaje indica el problema, por ejemplo `name: debe tener al menos 2 caracteres` |
| `500` | Error interno de base de datos |
| `502` | La API de Claude falló o devolvió una respuesta inválida |
| `503` | La IA con Claude no está configurada (falta `ANTHROPIC_API_KEY`) |

## Pruebas

Las pruebas usan su propia base SQLite (`test_ats.db`) y simulan la API de Claude, así que nunca tocan la base real ni gastan saldo:

```
pip install -r requirements-dev.txt
python -m pytest -q
```
