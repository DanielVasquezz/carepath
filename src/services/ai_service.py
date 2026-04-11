import logging
import openai
from uuid import UUID
from typing import Any, List, Dict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models.enums import TriagePriority

logger = logging.getLogger(__name__)

client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

EMBEDDING_DIM = 768


# =========================
# EMBEDDINGS
# =========================
async def generate_query_embedding(text_input: str) -> List[float]:
    try:
        response = await client.embeddings.create(
            input=[text_input],
            model="text-embedding-3-small",
            dimensions=EMBEDDING_DIM,
        )
        return response.data[0].embedding

    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return [0.0] * EMBEDDING_DIM


async def generate_symptom_embeddings(db_symptoms: List[Any]) -> None:
    """
    Genera embeddings sin romper flujo si OpenAI falla.
    """
    for symptom in db_symptoms:
        try:
            symptom.embedding = await generate_query_embedding(symptom.description)
        except Exception as e:
            logger.warning(f"Embedding failed for {symptom.id}: {e}")


# =========================
# RAG SEARCH (SAFE)
# =========================
async def find_similar_cases(
    session: AsyncSession,
    query_text: str,
    limit: int = 3,
    exclude_case_id: str | UUID | None = None,
) -> List[Dict[str, Any]]:
    try:
        query_embedding = await generate_query_embedding(query_text)

        sql = text("""
            SELECT
                tc.id as case_id,
                tc.chief_complaint,
                s.embedding <=> CAST(:emb AS vector) AS distance
            FROM symptoms s
            JOIN triage_cases tc ON tc.id = s.case_id
            WHERE
                s.embedding IS NOT NULL
                AND (:case_id IS NULL OR tc.id != CAST(:case_id AS UUID))
            ORDER BY distance ASC
            LIMIT :limit
        """)

        result = await session.execute(sql, {
            "emb": str(query_embedding),
            "case_id": str(exclude_case_id) if exclude_case_id else None,
            "limit": limit,
        })

        rows = result.fetchall()

        return [
            {
                "case_id": str(r.case_id),
                "chief_complaint": r.chief_complaint,
                "similarity": round(1 - (r.distance or 0), 3),
            }
            for r in rows
        ]

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []


# =========================
# TRIAGE AI ENGINE
# =========================
async def generate_triage_recommendation(
    db_case: Any,
    session: AsyncSession,
) -> Dict[str, Any]:
    """
    IA completamente aislada del estado de SQLAlchemy.
    """
    try:
        logger.info(f"Evaluando caso {db_case.id}")

        symptoms_text = "\n".join(
            f"- {s.description} (Severidad: {s.severity})"
            for s in db_case.symptoms
        )

        similar_cases = await find_similar_cases(
            session=session,
            query_text=db_case.chief_complaint,
            limit=2,
            exclude_case_id=db_case.id,
        )

        rag_context = ""
        if similar_cases:
            rag_context = "\nCasos similares:\n" + "\n".join(
                f"- {c['chief_complaint']} (similitud: {c['similarity']})"
                for c in similar_cases
            )

        prompt = f"""
Eres un médico experto en triaje.

Motivo: {db_case.chief_complaint}

Síntomas:
{symptoms_text}

{rag_context}

Da una recomendación clínica breve y clara.
"""

        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )

        ai_text = response.choices[0].message.content

        return {
            "recommendation": ai_text,
            "status": "success",
        }

    except Exception as e:
        logger.error(f"Triage AI error: {e}")
        return {
            "recommendation": "Error en evaluación. Revisión médica manual.",
            "status": "error",
        }