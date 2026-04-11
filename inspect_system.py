import asyncio
from sqlalchemy import text
from src.database.session import AsyncSessionLocal
from src.services.ai_service import get_llm

async def check():
    print("🚀 --- CAREPATH SYSTEM INSPECTOR ---")
    
    # DB Check
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
            print("✅ Postgres: Conectado")
            v = await db.execute(text("SELECT count(*) FROM triage_cases"))
            print(f"📊 Casos en DB: {v.scalar()}")
    except Exception as e: print(f"❌ Postgres: {e}")

    # Ollama Check
    try:
        llm = get_llm()
        await asyncio.wait_for(llm.ainvoke("hi"), timeout=5)
        print("✅ Ollama (Llama 3.2): Respondiendo")
    except Exception as e: print(f"❌ Ollama: {e}")

if __name__ == "__main__":
    asyncio.run(check())