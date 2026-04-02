# CarePath

> Intelligent medical triage and follow-up system powered by AI

CarePath helps patients determine the urgency of their symptoms and
connects them with the right level of medical care — reducing emergency
room overcrowding and improving response times.

## Tech Stack

1. Layer 2. Technology 3. Purpose |

API : FastAPI + Python 3.12 | Core backend |
Database : PostgreSQL + pgvector | Data + semantic search |
AI Engine : LangChain + Ollama/OpenAI | Intelligent triage |
Security : JWT + OAuth2 | Patient authentication |
Infrastructure : Docker + AWS + Terraform | Deployment & scalability |
CI/CD : GitHub Actions | Automated deployment |

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

# 5. Start services
docker compose up -d

# 6. Run the API
uvicorn src.main:app --reload

# 7. Open interactive API docs
# http://localhost:8000/docs
```

## Project Status

- [x] Phase 1 — Repository structure & architecture decisions
- [ ] Phase 2 — Data models & business logic (OOP)
- [ ] Phase 3 — REST API with FastAPI
- [ ] Phase 4 — Security & authentication
- [ ] Phase 5 — AWS infrastructure
- [ ] Phase 6 — AI triage engine with LLMs

## Project Structure
```
carepath/
├── src/
│   ├── api/          # FastAPI route handlers
│   ├── models/       # Pydantic schemas + SQLAlchemy models
│   ├── services/     # Business logic
│   └── core/         # Config, security, dependencies
├── tests/            # Automated test suite
├── docs/
│   ├── adr/          # Architecture Decision Records
│   ├── deployment/   # Deployment guides
│   └── diagrams/     # Architecture diagrams
├── infra/            # Terraform infrastructure as code
└── .github/
    └── workflows/    # CI/CD pipelines
```

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full system diagram
and design decisions.

## Architecture Decision Records

| ADR | Decision | Status |
|---|---|---|
| [ADR-001](./docs/adr/001-stack-decision.md) | Tech stack selection | Accepted |

## API Documentation

Once running, interactive API docs are available at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development guidelines
and commit message conventions.

## License

MIT — see [LICENSE](./LICENSE) for details.