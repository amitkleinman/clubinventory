# Club Equipment Management — Backend

## Quick start

```bash
# 1. Copy and edit environment file
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY and a strong SECRET_KEY

# 2. Start services
docker compose up -d

# 3. Wait for DB, then run migrations
docker compose exec backend alembic upgrade head

# 4. Seed departments + default users
docker compose exec backend python -m app.seed

# 5. API is live
open http://localhost:8000/api/docs
```

## Default credentials (change immediately)

| Role | Email | Password |
|---|---|---|
| COO | coo@club.local | changeme123 |
| Equipment Manager | equipment@club.local | changeme123 |

## pgAdmin

Open http://localhost:5050  
Login: admin@club.local / admin  
Add server: host=db, port=5432, user=club, password=clubpass

## Migration commands

```bash
# Create a new migration after model changes
docker compose exec backend alembic revision --autogenerate -m "description"

# Apply
docker compose exec backend alembic upgrade head

# Rollback one step
docker compose exec backend alembic downgrade -1
```

## Project structure

```
backend/
├── app/
│   ├── models/         SQLAlchemy ORM models (all tables)
│   ├── schemas/        Pydantic request/response schemas  ← next step
│   ├── api/v1/         FastAPI routers                    ← next step
│   ├── services/       Business logic                     ← next step
│   ├── core/
│   │   ├── config.py   Settings (pydantic-settings)
│   │   ├── db.py       Async engine + session
│   │   └── security.py JWT utils                         ← next step
│   ├── main.py         FastAPI app
│   └── seed.py         Seed departments + users
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial.py   Full schema migration
├── alembic.ini
├── requirements.txt
└── Dockerfile.dev
```
