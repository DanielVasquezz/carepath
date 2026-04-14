import logging
import openai
import traceback
import json
from uuid import UUID
from typing import Any, List, Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings

logger = logging.getLogger(__name__)

client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

EMBEDDING_DIM = 768

# =========================
# RED FLAGS (BILINGÜE)
# =========================
RED_FLAGS = [
    "chest", "pecho", "corazón", "heart",
    "breathing", "respirar", "aire", "breath",
    "unconscious", "inconsciente", "desmayo", "faint",
    "stroke", "derrame", "parálisis",
    "head", "cabeza", "fuerte dolor"
]

def validate_risk_score(symptoms: str, current_score: int) -> int:
    symptoms_lower = symptoms.lower()

    if any(flag in symptoms_lower for flag in RED_FLAGS):
        logger.info("🚩 Red Flag detectada → elevando riesgo mínimo a 7")
        return max(current_score, 7)

    return current_score


# =========================
# JSON PARSER ROBUSTO 🔥
# =========================
def safe_parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)

    except json.JSONDecodeError:
        logger.warning("⚠️ JSON inválido, intentando limpiar respuesta IA")

        cleaned = raw.strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1

        if start != -1 and end != -1:
            cleaned = cleaned[start:end]

        try:
            return json.loads(cleaned)
        except Exception:
            logger.error(f"❌ JSON imposible de parsear:\n{raw}")
            raise


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
        logger.error(f"Embedding error: {e}")
        return [0.0] * EMBEDDING_DIM


async def generate_symptom_embeddings(db_symptoms: List[Any]) -> None:
    for symptom in db_symptoms:
        try:
            symptom.embedding = await generate_query_embedding(symptom.description)
        except Exception as e:
            logger.warning(f"Embedding falló para {symptom.id}: {e}")


# =========================
# RAG SEARCH
# =========================
async def find_similar_cases(
    session: Optional[AsyncSession],
    query_text: str,
    limit: int = 3,
    exclude_case_id: str | UUID | None = None,
) -> List[Dict[str, Any]]:

    if not session:
        return []

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
        logger.error(f"Vector search error: {e}")
        return []


# =========================
# TRIAGE AI ENGINE FINAL (FIXED)
# =========================
async def generate_triage_recommendation(
    case_data: dict,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:

    try:
        logger.info(f"🧠 Evaluando caso IA: {case_data.get('id')}")

        # =========================
        # SÍNTOMAS
        # =========================
        symptoms_text = "\n".join(
            f"- {s['description']} (Severidad: {s['severity']})"
            for s in case_data["symptoms"]
        )

        # =========================
        # VALIDACIÓN INICIAL
        # =========================
        validated_score = validate_risk_score(symptoms_text, 0)

        # =========================
        # RAG
        # =========================
        rag_context = ""
        if session:
            similar_cases = await find_similar_cases(
                session=session,
                query_text=case_data["chief_complaint"],
                limit=2,
                exclude_case_id=case_data.get("id"),
            )

            if similar_cases:
                rag_context = "\nCasos similares:\n" + "\n".join(
                    f"- {c['chief_complaint']} ({c['similarity']})"
                    for c in similar_cases
                )

        # =========================
        # PROMPT MEJORADO
        # =========================
        prompt = f"""
Eres un médico experto en triaje clínico.

Motivo: {case_data['chief_complaint']}

Síntomas:
{symptoms_text}

{rag_context}

Evalúa el riesgo del paciente.

IMPORTANTE:
- El risk_score debe ser un ENTERO del 1 al 10 (sin comillas).
- Si hay síntomas críticos, el score NO puede ser menor a {validated_score}.
- Responde SOLO en JSON válido.
- NO incluyas texto fuera del JSON.

Formato EXACTO:
{{
  "risk_score": 7,
  "recommendation": "explicación breve en español"
}}
"""

        # =========================
        # IA (FIX REAL)
        # =========================
        response = await client.responses.create(
            model=settings.LLM_MODEL,
            input=[
                {"role": "system", "content": "Eres un sistema médico. Responde SOLO JSON válido."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        raw = response.output[0].content[0].text

        logger.info(f"🧾 RAW IA RESPONSE:\n{raw}")

        # =========================
        # PARSEO
        # =========================
        ai_data = safe_parse_json(raw)

        # =========================
        # VALIDACIÓN SEGURA DEL SCORE
        # =========================
        try:
            ai_score = int(ai_data.get("risk_score", 5))
        except Exception:
            logger.warning("⚠️ Score inválido desde IA, usando fallback")
            ai_score = 5

        # =========================
        # VALIDACIÓN FINAL
        # =========================
        final_score = validate_risk_score(symptoms_text, ai_score)

        return {
            "recommendation": ai_data.get(
                "recommendation",
                "Se recomienda evaluación médica."
            ),
            "risk_score": final_score,
            "status": "success",
        }

    except Exception as e:
        print("\n" + "=" * 50)
        print("❌ ERROR REAL EN IA:")
        print(str(e))
        traceback.print_exc()
        print("=" * 50 + "\n")

        logger.error(f"🔥 AI failure: {e}")

        # =========================
        # FALLBACK INTELIGENTE
        # =========================
        fallback_score = validate_risk_score(
            case_data.get("chief_complaint", ""), 5
        )

        return {
            "recommendation": "⚠️ IA no disponible. Evaluación manual aplicada.",
            "risk_score": fallback_score,
            "status": "fallback",
        }