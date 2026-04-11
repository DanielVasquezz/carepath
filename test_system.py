# test_system.py
"""
CarePath — System Diagnostic
Verifica que todos los componentes funcionen correctamente.
"""
import asyncio
import sys


async def check_database():
    print("\n📊 Checking database connection...")
    try:
        from src.core.database import AsyncSessionLocal
        from sqlalchemy import text

        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            print("  ✅ PostgreSQL connection OK")

        # Check tables
        async with AsyncSessionLocal() as session:
            result = await session.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public'"
            ))
            tables = [r[0] for r in result.fetchall()]
            expected = ["patients", "symptoms", "triage_cases", "alembic_version"]

            for t in expected:
                status = "✅" if t in tables else "❌"
                print(f"  {status} Table '{t}': {'exists' if t in tables else 'MISSING'}")

        # Check pgvector
        async with AsyncSessionLocal() as session:
            result = await session.execute(text(
                "SELECT extname FROM pg_extension WHERE extname='vector'"
            ))
            has_vector = result.scalar_one_or_none()
            status = "✅" if has_vector else "⚠️"
            print(f"  {status} pgvector extension: {'installed' if has_vector else 'NOT INSTALLED'}")

    except Exception as e:
        print(f"  ❌ Database error: {e}")


def check_imports():
    print("\n📦 Checking module imports...")
    modules = [
        ("fastapi", "FastAPI"),
        ("sqlalchemy", "SQLAlchemy"),
        ("pydantic", "Pydantic"),
        ("alembic", "Alembic"),
        ("passlib", "Passlib"),
        ("jose", "python-jose"),
        ("langchain", "LangChain"),
        ("langchain_ollama", "LangChain-Ollama"),
        ("pgvector", "pgvector"),
        ("ollama", "Ollama"),
    ]

    for module, name in modules:
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name} — NOT INSTALLED")


def check_services():
    print("\n🔧 Checking CarePath services...")
    services = [
        ("src.core.config", "settings", "Config"),
        ("src.core.database", "Base", "Database"),
        ("src.core.security", "hash_password", "Security"),
        ("src.models.enums", "SeverityLevel", "Enums"),
        ("src.models.patient", "Patient", "Patient model"),
        ("src.models.symptom", "Symptom", "Symptom model"),
        ("src.models.triage", "TriageCase", "Triage model"),
        ("src.models.db.patient_db", "PatientDB", "Patient DB model"),
        ("src.models.db.triage_db", "TriageCaseDB", "Triage DB model"),
        ("src.services.triage_logic", "run_start_triage", "START triage logic"),
        ("src.services.ai_service", "generate_triage_recommendation", "AI service"),
        ("src.api.v1.endpoints.patients", "router", "Patients router"),
        ("src.api.v1.endpoints.cases", "router", "Cases router"),
        ("src.api.v1.endpoints.auth", "router", "Auth router"),
    ]

    for module, attr, name in services:
        try:
            mod = __import__(module, fromlist=[attr])
            getattr(mod, attr)
            print(f"  ✅ {name}")
        except ImportError as e:
            print(f"  ❌ {name} — Import error: {e}")
        except AttributeError as e:
            print(f"  ❌ {name} — Missing attribute: {e}")
        except Exception as e:
            print(f"  ⚠️  {name} — {e}")


def check_ollama():
    print("\n🤖 Checking Ollama...")
    try:
        import requests

        res = requests.get("http://localhost:11434/api/tags")

        if res.status_code != 200:
            print("  ❌ Ollama not responding correctly")
            print("     Run: ollama serve")
            return

        data = res.json()
        models = data.get("models", [])

        if not models:
            print("  ⚠️ Ollama running but no models installed")
            return

        print(f"  ✅ Ollama running — {len(models)} models available")

        model_names = [m.get("name", "") for m in models]

        for name in ["llama3.2", "nomic-embed-text"]:
            found = any(name in m for m in model_names)
            status = "✅" if found else "⚠️"
            print(
                f"  {status} {name}: "
                f"{'available' if found else 'NOT PULLED — run: ollama pull ' + name}"
            )

    except Exception as e:
        print(f"  ❌ Ollama not running: {e}")
        print("     Run: ollama serve")


def check_env():
    print("\n⚙️  Checking environment...")
    import os
    from pathlib import Path

    env_file = Path(".env")

    if env_file.exists():
        print("  ✅ .env file exists")
    else:
        print("  ⚠️  .env file missing — copy .env.example to .env")

    try:
        from src.core.config import settings

        checks = [
            ("DATABASE_URL", settings.DATABASE_URL),
            ("SECRET_KEY", settings.SECRET_KEY),
            ("APP_NAME", settings.APP_NAME),
        ]

        for key, val in checks:
            status = "✅" if val else "❌"
            display = val[:30] + "..." if val and len(val) > 30 else val
            print(f"  {status} {key}: {display}")

    except Exception as e:
        print(f"  ❌ Config error: {e}")


def check_triage_logic():
    print("\n🏥 Testing START triage algorithm...")
    try:
        from src.services.triage_logic import run_start_triage
        from src.models.enums import SeverityLevel, TriagePriority

        class FakeSymptom:
            def __init__(self, severity, worsening=False, duration=None):
                self.severity = severity
                self.is_worsening = worsening
                self.duration_hours = duration

        # Test P1
        s_critical = [FakeSymptom(SeverityLevel.CRITICAL.value)]
        p, score = run_start_triage(s_critical)
        assert p == TriagePriority.P1_IMMEDIATE
        print(f"  ✅ CRITICAL → P1_immediate (score: {score})")

        # Test P4
        s_low = [FakeSymptom(SeverityLevel.LOW.value)]
        p, score = run_start_triage(s_low)
        assert p == TriagePriority.P4_MINIMAL
        print(f"  ✅ LOW → P4_minimal (score: {score})")

        # Test P2
        s_high = [
            FakeSymptom(SeverityLevel.HIGH.value, worsening=True),
            FakeSymptom(SeverityLevel.HIGH.value, worsening=True),
        ]
        p, score = run_start_triage(s_high)
        assert p == TriagePriority.P2_URGENT
        print(f"  ✅ HIGH+worsening → P2_urgent (score: {score})")

    except Exception as e:
        print(f"  ❌ Triage logic error: {e}")


async def main():
    print("=" * 50)
    print("🏥 CarePath — System Diagnostic")
    print("=" * 50)

    check_imports()
    check_env()
    check_services()
    check_triage_logic()
    await check_database()
    check_ollama()

    print("\n" + "=" * 50)
    print("Diagnostic complete.")
    print("=" * 50)


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.getcwd())
    asyncio.run(main())