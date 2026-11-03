# Company X Feedback API

Django REST API for the Company X customer feedback system. It accepts web and
SMS feedback, scores responses, provides dashboard and alert data, and supports
staff authentication and follow-up workflows. The API also integrates with
email, SMS, and configurable AI providers.

## Requirements

- Python 3.12
- pip
- SQLite for a simple local setup, or PostgreSQL for a shared/production-like
  setup

## Local development

From this directory, create and activate a virtual environment, then install
dependencies:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux:        source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

For a basic local run, Django uses SQLite when no database URL or PostgreSQL
settings are supplied:

```bash
python manage.py migrate
python manage.py seed_user
python manage.py seed
python manage.py runserver 8000
```

The API is at <http://localhost:8000>, health check at
<http://localhost:8000/health>, and interactive API documentation at
<http://localhost:8000/api/docs/>. Demo data can be loaded with `seed`; use
`python manage.py help seed` to see the command options.

To run the full stack with PostgreSQL, use the workspace-level
`docker-compose.yml` from the project root.

## Configuration

Settings are loaded from environment variables. For local development, the
important options are:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection URL. If unset, local SQLite is used. |
| `DJANGO_SECRET_KEY` | Django signing key; set a private value outside local development. |
| `DJANGO_DEBUG` | Enables Django debug mode; disable in deployed environments. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hostnames. |
| `CORS_ORIGINS` | Comma-separated frontend origins allowed to call the API. |
| `JWT_SECRET` | Signing key for staff authentication tokens. |
| `AI_PROVIDER` / `AI_MODEL` | Select the AI provider and model; mock mode is the default. |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` | Optional hosted AI credentials. |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` | Optional email transport settings. |
| `AFRICASTALKING_USERNAME`, `AFRICASTALKING_API_KEY` | Optional SMS gateway settings. |
| `SEED_ON_START` | Whether the container entrypoint seeds demo data at startup. |

Do not commit secret values. Production and staging use separate environment
files on the host; see [`CI_CD.md`](CI_CD.md) for the complete deployment
configuration.

## API areas

- `POST /api/feedback` — submit a scored customer response
- `/api/feedback` and `/api/feedback/page` — list and paginate responses
- `/api/dashboard/summary` — dashboard totals, score split, and trend
- `/api/alerts` — list, inspect, acknowledge, and send alert follow-ups
- `/api/ai/ask` — ask a natural-language question about dashboard data
- `/api/sms/invite` and `/api/sms/inbound` — SMS invitation and inbound reply
- `/api/auth/` — staff login and session endpoints
- `/api/docs/` — Swagger UI; `/api/schema/` — OpenAPI schema

See the generated API documentation for request and response schemas.

## Tests and checks

```bash
ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
pytest -q
```

CI runs these checks against PostgreSQL 16.

## Docker

Build and run the API image from this directory:

```bash
docker build -t riana-backend:local .
docker run --rm -p 8000:8000 \
  -e DJANGO_SECRET_KEY=local-only-change-me \
  riana-backend:local
```

For a useful full-stack run, provide PostgreSQL and the environment settings, or
use the workspace Compose configuration. The container entrypoint applies
migrations, ensures a care-rep login exists, optionally seeds demo data, and
starts Gunicorn.

## CI and deployment

The workflow in `.github/workflows/deploy.yml` runs Ruff, Django checks,
migration checks, and pytest against PostgreSQL. It then builds and scans a
Docker image, packages the checked-out source with resolved Python dependencies
and a SHA-256 checksum, and uploads that release artifact. A push to `main`
deploys the exact artifact to staging. Production uses the same
staging-tested artifact after approval through the production GitHub
Environment.

The Docker image is built and scanned by CI but is not the server runtime. The
EC2 host installs the release into a versioned directory and runs Gunicorn as a
`systemd` service. Backend deployment checks configuration and applies
migrations before switching releases; a failed health check restores the
previous application release when available. Database migrations are not
automatically rolled back.

See [`CI_CD.md`](CI_CD.md) for GitHub Environment setup, server configuration,
and release operations.
