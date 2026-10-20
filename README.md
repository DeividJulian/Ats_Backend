# Portal ATS para pymes — Backend

API que permite publicar vacantes, registrar candidatos y **ordenarlos automáticamente según su ajuste al cargo** usando procesamiento de lenguaje natural (NLP) implementado desde cero. Opcionalmente, un modelo de lenguaje (Gemini por defecto, gratis; también Groq o Claude) redacta evaluaciones, extrae perfiles y propone vacantes.

- **Frontend:** https://github.com/DeividJulian/Ats_Front (Angular) · https://ats-front-six.vercel.app
- **API desplegada:** https://ats-backend-xtp7.onrender.com

Proyecto final de Programación Orientada a la Web — Universidad Cooperativa de Colombia.

## Tecnologías

- Python 3.14 + FastAPI
- SQLAlchemy 2 + PostgreSQL en [Neon](https://neon.com) (psycopg v3)
- Pydantic v2 para validación
- pypdf para leer hojas de vida en PDF
- Modelo de lenguaje opcional e intercambiable: Gemini o Groq (por su endpoint compatible con OpenAI, vía httpx2) o Claude (SDK oficial de Anthropic)
- pytest para pruebas
- Despliegue en [Render](https://render.com)

El código y la API (rutas y campos JSON) están en inglés. Los mensajes de error, las explicaciones del puntaje, los textos generados y la documentación de `/docs` están en español.

## Estructura

```
├── main.py              # App, CORS, logging, errores; registra los routers automáticamente
├── database.py          # Conexión y sesión de base de datos
├── errors.py            # Mensajes de error en español
├── render.yaml          # Configuración de despliegue en Render
├── models/              # Tablas: users, jobs, candidates, applications
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
│   ├── llm.py           # Cliente de IA independiente del proveedor (Gemini, Groq o Claude) con salidas estructuradas
│   ├── ai.py            # Evaluación, extracción de perfil y redacción de vacantes con IA
│   ├── privacy.py       # Oculta nombre, correo y teléfono antes de enviar texto a la IA
│   ├── resume.py        # Lectura y análisis de hojas de vida en PDF
│   ├── security.py      # Contraseñas (scrypt) y tokens de sesión (JWT)
│   ├── auth.py          # Usuario de la petición y permisos por rol
│   ├── bootstrap.py     # Crea el primer administrador desde variables de entorno
│   ├── pipeline.py      # Flujo de estados de la postulación
│   ├── stats.py         # Embudo y brechas de talento
│   └── seed.py          # Datos de demostración
└── tests/               # 129 pruebas automatizadas
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
| `SECRET_KEY` | Clave para firmar las sesiones y los códigos (32 caracteres o más). También se acepta el nombre viejo `JWT_SECRET`. Si falta, se genera una temporal y las sesiones se cierran al reiniciar |
| `TOKEN_HORAS` | Duración de la sesión en horas (por defecto 12) |
| `EMAIL_BACKEND` | Cómo se envían los códigos: `consola` (local, el código sale en la terminal), `memoria` (pruebas), `smtp` o `brevo` (producción) |
| `EMAIL_FROM` / `EMAIL_FROM_NAME` | Remitente de los correos. Con Brevo debe ser un remitente verificado en tu cuenta |
| `BREVO_API_KEY` | Clave de la API de Brevo (Settings → SMTP & API → API Keys) |
| `CODIGO_MINUTOS` / `CODIGO_INTENTOS` / `CODIGO_ESPERA_SEGUNDOS` | Vigencia del código (10), intentos permitidos (5) y espera entre envíos (30) |
| `ALLOW_DEMO_LOGIN` | `true` deja entrar sin código a las dos cuentas de demostración (sus correos son falsos). Solo para mostrar el proyecto |
| `ADMIN_EMAIL` | Primer administrador: se crea al arrancar si no existe y entra con el código que le llega a ese correo (debe ser real) |
| `AI_PROVIDER` | Proveedor de IA: `gemini` (por defecto), `groq` o `anthropic` |
| `AI_API_KEY` | Clave de ese proveedor. Opcional: sin ella los endpoints `/ai` responden 503 y todo lo demás funciona |
| `AI_MODEL` | Opcional. Modelo a usar (por defecto `gemini-3.8-flash`, `openai/gpt-oss-20b` en Groq o `claude-opus-5-5` en Anthropic) |
| `AI_BASE_URL` | Opcional. Otra dirección para el endpoint (por defecto la oficial de cada proveedor) |

```
uvicorn main:app --reload
```

Documentación interactiva: `http://127.0.0.1:8000/docs`. Para ver el sistema con datos, ejecuta `POST /seed`.

## Despliegue en Render

1. Entra a [render.com](https://render.com) con tu cuenta de GitHub.
2. **New → Blueprint** y elige este repositorio. Render lee `render.yaml` y crea el servicio `ats-backend` (plan gratis, región Virginia, la misma zona de AWS que la base en Neon).
3. Cuando lo pida, pega en `DATABASE_URL` la cadena de conexión de Neon, tu correo en `ADMIN_EMAIL`, el remitente verificado en Brevo en `EMAIL_FROM`, la clave de Brevo en `BREVO_API_KEY` y, si vas a usar IA, la clave en `AI_API_KEY` (puedes dejarla vacía). `EMAIL_BACKEND` ya viene en `brevo`, `AI_PROVIDER` y `AI_MODEL` con `gemini` y `gemini-3.8-flash`, y `SECRET_KEY` la genera Render sola.
4. Al terminar el despliegue, abre `https://<tu-servicio>.onrender.com/docs`.
5. Cuando el front esté publicado, cambia `ALLOWED_ORIGINS` a su URL en **Environment**.

En el plan gratis el servicio se duerme tras 15 minutos sin tráfico y la primera petición después tarda cerca de un minuto. Cada `git push` a `main` vuelve a desplegar automáticamente.

## Usuarios y roles

### Inicio de sesión sin contraseña

1. `POST /auth/register {name, email, phone?}` crea la cuenta de candidato sin verificar y envía un código de 6 dígitos (201). Si la cuenta ya está verificada responde 409; si existe sin verificar, reenvía el código. Si un reclutador ya había creado el perfil con ese correo, se vincula a la cuenta (el código demuestra que el correo es suyo).
2. `POST /auth/login {email}` envía un código nuevo; si no hay cuenta responde 404.
3. `POST /auth/verify {email, code}` valida el código y devuelve `{access_token, user}`. La primera vez marca la cuenta como verificada.
4. Las demás peticiones llevan `Authorization: Bearer <token>` (JWT HS256, dura `TOKEN_HORAS`). `GET /auth/me` devuelve el usuario actual.

Reglas del código: se genera con `secrets`, se guarda solo su HMAC-SHA256 (nunca en texto plano), vence en 10 minutos, sirve una sola vez, admite 5 intentos, exige 30 segundos entre envíos (429) y un código nuevo anula los anteriores. Si el correo no sale responde 502 y no queda nada guardado. Sin token, con un token vencido o inválido, o con una cuenta sin verificar, la API responde 401.

Los correos se envían con [Brevo](https://www.brevo.com) por su API HTTP (gratis, 300 correos al día), porque el plan gratis de Render bloquea los puertos SMTP. En local, con `EMAIL_BACKEND=consola`, el código aparece en la terminal.

Si ya tenías una base en Neon de la versión con contraseña, al arrancar se agregan las columnas nuevas sin borrar nada (`migrate_auth.py`, que también se puede ejecutar a mano con `python migrate_auth.py`). Las cuentas que ya existían quedan verificadas.

| Rol | Qué puede hacer |
|---|---|
| `admin` | Todo, incluida la gestión de usuarios y la carga de datos de demostración |
| `recruiter` | Vacantes, candidatos, postulaciones, ranking, estadísticas e IA |
| `candidate` | Se registra solo, ve las vacantes abiertas, se postula, sube su hoja de vida y sigue sus postulaciones (sin ver el puntaje) |

Los candidatos se registran solos. Las cuentas de reclutador y administrador las crea un administrador desde `POST /users` (sin contraseña: la persona entra con el código que le llega). El primer administrador sale de `ADMIN_EMAIL`. Cada candidato ve y modifica solo su perfil y sus postulaciones; las vacantes y los candidatos los comparte todo el equipo de selección.

`POST /seed` crea dos cuentas de prueba: `reclutador@demo.com` (reclutador) y `camila.ortega@example.com` (candidata). Como sus correos son falsos, entran con `POST /auth/demo` solo si `ALLOW_DEMO_LOGIN=true`.

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

### IA con un modelo de lenguaje (opcional)

**El núcleo funciona sin IA externa**: la lectura de PDF, la extracción del perfil, el puntaje y el ranking son del NLP propio. Con `AI_API_KEY` configurada, un modelo de lenguaje lo complementa. **El puntaje sigue siendo el determinista**: el modelo asesora y redacta, no decide.

- **Evaluación de una postulación:** resumen, fortalezas, brechas, recomendación (`advance`, `interview_with_reservations` o `reject`) y preguntas de entrevista.
- **Extracción de perfil:** habilidades, experiencia, nivel educativo y resumen a partir del texto de una hoja de vida.
- **Redacción de vacantes:** borrador de descripción, requisitos y habilidades a partir del cargo y unas notas.

Protecciones: las respuestas usan salidas estructuradas (el modelo solo puede devolver el formato esperado y además se validan); la hoja de vida se trata como datos y no como instrucciones, para que nadie escriba "califícame con 100"; se prohíbe usar rasgos protegidos y al modelo nunca le llegan el nombre, el correo ni el teléfono del candidato (se reemplazan por `[candidato]`, `[correo]` y `[teléfono]`, incluso dentro del texto de la hoja de vida). Sin clave, `/ai` responde 503; si se alcanza el límite de uso del proveedor, 429; si el proveedor falla o tarda más de 30 s, 502. Nunca inventa resultados.

#### Obtener una clave gratuita de Gemini

1. Entra a [Google AI Studio](https://aistudio.google.com) con tu cuenta de Google.
2. Haz clic en **Get API key** y crea una clave. El nivel gratuito no pide tarjeta; sus límites por minuto y por día se ven en AI Studio.
3. Ponla en `AI_API_KEY` (en tu `.env` local y en Render → **Environment**). Nunca la subas al repositorio.

#### Cambiar de proveedor

Solo cambian las variables, no el código:

| Proveedor | `AI_PROVIDER` | `AI_MODEL` por defecto | Clave |
|---|---|---|---|
| Google Gemini | `gemini` | `gemini-3.8-flash` | [aistudio.google.com](https://aistudio.google.com) |
| Groq | `groq` | `openai/gpt-oss-20b` | [console.groq.com](https://console.groq.com) |
| Anthropic | `anthropic` | `claude-opus-5-5` | [platform.claude.com](https://platform.claude.com) (de pago) |

`GET /ai/status` responde `configured`, `provider` y `model`. Por compatibilidad, si solo existe `ANTHROPIC_API_KEY` se usa Anthropic como antes.

## Endpoints

| Recurso | Endpoints |
|---|---|
| Vacantes | `POST /jobs`, `GET /jobs?status=`, `GET /jobs/{id}`, `PUT /jobs/{id}`, `PATCH /jobs/{id}/status`, `DELETE /jobs/{id}` |
| Candidatos | `POST /candidates`, `GET /candidates?skill=`, `GET /candidates/{id}`, `PUT /candidates/{id}`, `DELETE /candidates/{id}` |
| Hojas de vida | `POST /candidates/from-resume` (crea desde PDF), `POST /candidates/{id}/resume` (actualiza desde PDF), `POST /nlp/analyze-resume` (vista previa sin guardar) |
| Postulaciones | `POST /applications`, `GET /applications?job_id=&candidate_id=&status=`, `GET /applications/{id}`, `PATCH /applications/{id}/status`, `DELETE /applications/{id}` |
| Ranking | `GET /jobs/{id}/ranking?blind=`, `GET /jobs/{id}/suggested-candidates`, `GET /candidates/{id}/recommended-jobs`, `POST /applications/{id}/recalculate`, `POST /jobs/{id}/recalculate-ranking` |
| IA | `GET /candidates/{id}/insights`, `GET /applications/{id}/interview-guide` |
| IA con modelo de lenguaje | `GET /ai/status`, `POST /ai/evaluate/{application_id}`, `POST /ai/extract-resume`, `POST /ai/draft-job` |
| NLP | `POST /nlp/analyze-text`, `POST /nlp/similarity` |
| Análisis | `GET /stats` |
| Autenticación | `POST /auth/register` (candidatos), `POST /auth/login`, `POST /auth/verify`, `GET /auth/me`, `GET /auth/options`, `POST /auth/demo` |
| Usuarios (admin) | `GET /users`, `POST /users`, `PATCH /users/{id}`, `DELETE /users/{id}` |
| Portal del candidato | `GET/PUT /me/profile`, `POST /me/resume`, `GET /me/insights`, `GET /me/recommended-jobs`, `GET/POST /me/applications`, `DELETE /me/applications/{id}` |
| Público (sin sesión) | `GET /public/jobs`, `GET /public/jobs/{id}`, `GET /public/summary` |
| Utilidades | `POST /seed?reset=` (admin), `GET /health` |

### Valores

- Estado de la vacante: `open`, `closed`.
- Nivel educativo: `high_school`, `technician`, `technologist`, `professional`, `specialization`, `masters`, `doctorate`.
- Estado de la postulación: `new → shortlisted → interview → offer → hired`. Desde cualquier estado activo se puede pasar a `rejected`. `hired` y `rejected` son finales.

### Códigos de error

Todos responden `{"detail": "mensaje"}` en español:

| Código | Significado |
|---|---|
| `401` | Falta iniciar sesión, o el token no es válido o expiró |
| `403` | El rol no tiene permiso, el usuario está desactivado o la acción está deshabilitada en este entorno |
| `404` | El recurso no existe |
| `409` | Conflicto: correo duplicado, postulación repetida, vacante cerrada, cambio de estado no permitido o datos ya cargados en `/seed` |
| `422` | Datos inválidos o PDF ilegible; el mensaje indica el problema, por ejemplo `name: debe tener al menos 2 caracteres` |
| `500` | Error interno de base de datos |
| `429` | Se alcanzó el límite de uso del proveedor de IA (incluye `Retry-After` si el proveedor lo indica) |
| `502` | El proveedor de IA falló, tardó demasiado o devolvió una respuesta inválida |
| `503` | La IA no está configurada (falta `AI_API_KEY` o `AI_PROVIDER` no es válido) |

## Pruebas

Las pruebas usan su propia base SQLite (`test_ats.db`) y simulan el HTTP de cada proveedor de IA (ignoran las claves del `.env`), así que nunca tocan la base real ni gastan cuota:

```
pip install -r requirements-dev.txt
python -m pytest -q
```
