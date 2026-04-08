# CarePath

> Intelligent medical triage and follow-up system powered by AI

CarePath helps patients determine the urgency of their symptoms and
connects them with the right level of medical care — reducing emergency
room overcrowding and improving response times.

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| API | FastAPI + Python 3.12 | Core backend |
| Database | PostgreSQL + pgvector | Data + semantic search |
| ORM | SQLAlchemy 2.0 async | Database layer |
| Migrations | Alembic | Schema version control |
| Validation | Pydantic v2 | Data validation + serialization |
| AI Engine | LangChain + Ollama/OpenAI | Intelligent triage |
| Security | JWT + OAuth2 | Patient authentication |
| Infrastructure | Docker + AWS + Terraform | Deployment & scalability |
| CI/CD | GitHub Actions | Automated deployment |

## Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/your-username/carepath.git
cd carepath

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your values

# 5. Start PostgreSQL and pgAdmin
docker compose up postgres pgadmin -d

# 6. Run database migrations
export PYTHONPATH=$PYTHONPATH:$(pwd)
alembic upgrade head

# 7. Start the API
uvicorn src.main:app --reload --port 8000

# 8. Open interactive API docs
# http://localhost:8000/docs
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Server health check |
| POST | `/api/v1/patients/` | Register a new patient |
| GET | `/api/v1/patients/{id}` | Get patient by ID |
| GET | `/api/v1/patients/` | List all active patients |
| POST | `/api/v1/cases/` | Open a new triage case |
| GET | `/api/v1/cases/{id}` | Get case details |
| POST | `/api/v1/cases/{id}/evaluate` | Run START triage algorithm |
| POST | `/api/v1/cases/{id}/resolve` | Resolve with recommendation |

## Triage Algorithm

CarePath implements the international **START triage protocol**:

| Priority | Condition | Action |
|---|---|---|
| P1 Immediate | Any CRITICAL symptom | Emergency room now |
| P2 Urgent | Risk score ≥ 8 | Urgent care within 1 hour |
| P3 Delayed | Risk score ≥ 4 | Can wait 1-2 hours |
| P4 Minimal | Risk score < 4 | Self-care appropriate |

**Risk score per symptom:**
- Severity: LOW=1, MODERATE=2, HIGH=3, CRITICAL=4
- Worsening: +2
- Duration > 24h: +1

## Project Status

- [x] Phase 1 — Repository structure & architecture decisions
- [x] Phase 2 — Domain models with OOP (Patient, Symptom, TriageCase)
- [x] Phase 3 — REST API with FastAPI + automatic OpenAPI docs
- [x] Phase 4 — PostgreSQL persistence with Docker + Alembic migrations
- [ ] Phase 5 — Security: JWT + bcrypt + RBAC
- [ ] Phase 6 — AWS infrastructure with Terraform
- [ ] Phase 7 — AI triage engine with LangChain + pgvector

## Project Structure
carepath/
├── src/
│   ├── main.py                  # FastAPI app entry point
│   ├── core/
│   │   ├── config.py            # Centralized settings
│   │   └── database.py          # Async SQLAlchemy engine + sessions
│   ├── models/
│   │   ├── enums.py             # SeverityLevel, TriagePriority, CaseStatus
│   │   ├── patient.py           # Pydantic schemas (DTO pattern)
│   │   ├── symptom.py           # Symptom model + risk_score logic
│   │   ├── triage.py            # TriageCase + START protocol algorithm
│   │   └── db/
│   │       ├── patient_db.py    # SQLAlchemy patients table
│   │       └── triage_db.py     # SQLAlchemy triage_cases + symptoms
│   └── api/
│       └── v1/
│           ├── router.py        # Combines all routers
│           └── endpoints/
│               ├── patients.py  # Patient CRUD endpoints
│               └── cases.py     # Triage case lifecycle endpoints
├── alembic/                     # Database migrations
│   └── versions/                # Migration history (versioned in Git)
├── tests/                       # Automated test suite
├── docs/
│   ├── adr/                     # Architecture Decision Records
│   ├── deployment/              # Deployment guides
│   └── diagrams/                # Architecture diagrams
├── infra/                       # Terraform infrastructure as code
├── .github/
│   └── workflows/               # CI/CD pipelines
├── docker-compose.yml           # PostgreSQL + pgAdmin + API
├── Dockerfile                   # API container definition
├── alembic.ini                  # Alembic configuration
├── .env.example                 # Environment variables template
└── requirements.txt             # Python dependencies

## Local Services

| Service | URL | Credentials |
|---|---|---|
| FastAPI API | http://localhost:8000 | — |
| Swagger UI | http://localhost:8000/docs | — |
| ReDoc | http://localhost:8000/redoc | — |
| pgAdmin | http://localhost:5050 | admin@carepath.dev / admin |
| PostgreSQL | localhost:5432 | postgres / postgres |

## Architecture Decision Records

| ADR | Decision | Status |
|---|---|---|
| [ADR-001](./docs/adr/001-stack-decision.md) | Tech stack selection | Accepted |

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development guidelines
and commit message conventions.

## License

MIT — see [LICENSE](./LICENSE) for details.
