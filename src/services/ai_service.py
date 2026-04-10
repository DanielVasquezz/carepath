# src/services/ai_service.py
"""
CarePath — AI Triage Service
==============================
Integrates LangChain + Ollama + pgvector to generate
intelligent medical recommendations.

Pipeline:
    1. Generate embedding for symptom descriptions
    2. Search pgvector for similar historical cases
    3. Build prompt with symptoms + similar cases
    4. Send to LLM (Ollama/Llama3 locally, OpenAI in production)
    5. Return structured recommendation

Why LangChain?
LangChain abstracts the LLM provider. Switching from Ollama
to OpenAI to Claude requires changing one line — the model
initialization. The rest of the pipeline stays identical.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from sentence_transformers import SentenceTransformer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.db.triage_db import SymptomDB, TriageCaseDB

logger = logging.getLogger(__name__)

# ── Embedding Model ───────────────────────────────────────────────
# Loaded once at module level — expensive to initialize
# all-MiniLM-L6-v2: 384 dimensions, runs on CPU, fast
# Perfect for development. In production: OpenAI text-embedding-3-small
_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """
    Lazy initialization of the embedding model.
    First call loads the model (~50MB download).
    Subsequent calls return the cached instance.
    This is the Singleton pattern for expensive resources.
    """
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading embedding model — first time only...")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Embedding model loaded successfully")
    return _embedding_model


def generate_embedding(text: str) -> list[float]:
    """
    Converts text to a 384-dimensional vector.

    "chest pain radiating to left arm"
    → [0.82, -0.31, 0.44, ... (384 numbers)]

    The vector captures semantic meaning.
    Similar symptoms produce similar vectors
    even if described with different words.
    """
    model = get_embedding_model()
    embedding = model.encode(text, normalize_embeddings=True)
    # normalize_embeddings=True → vectors have length 1
    # This makes cosine similarity = dot product
    # Faster computation in pgvector
    return embedding.tolist()


# ── LLM ──────────────────────────────────────────────────────────
def get_llm() -> ChatOllama:
    """
    Returns the LLM instance.

    Development: Ollama running locally (free, private)
    Production: swap ChatOllama for ChatOpenAI or ChatAnthropic

    LangChain makes this swap trivial — same interface,
    different constructor.
    """
    return ChatOllama(
        model="llama3.2",
        temperature=0.3,
        # temperature=0.3 → slightly creative but mostly deterministic
        # Medical recommendations need consistency, not creativity
        # temperature=0 → always same output (good for testing)
        # temperature=1 → very creative (bad for medical advice)
    )


# ── Core AI Functions ─────────────────────────────────────────────
async def generate_symptom_embeddings(
    symptoms: list[SymptomDB],
    db: AsyncSession,
) -> None:
    """
    Generates and stores embeddings for a list of symptoms.

    Called after a new triage case is created.
    Embeddings enable similarity search later.

    Why store embeddings in the DB?
    Because regenerating them for every search query is slow.
    Store once, search many times.
    """
    for symptom in symptoms:
        if symptom.embedding is None:
            embedding = generate_embedding(symptom.description)
            symptom.embedding = embedding

    await db.commit()
    logger.info(f"Generated embeddings for {len(symptoms)} symptoms")


async def find_similar_cases(
    query_text: str,
    db: AsyncSession,
    limit: int = 3,
    exclude_case_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Finds the most similar historical cases using pgvector.

    This is the R in RAG — Retrieval.

    Algorithm:
    1. Convert query_text to embedding vector
    2. Search symptoms table using cosine distance (<=>)
    3. Return the top N most similar cases

    The <=> operator in pgvector computes cosine distance.
    Lower distance = more similar.
    0 = identical, 2 = completely opposite.

    Args:
        query_text: the current patient's symptom description
        db: database session
        limit: number of similar cases to return
        exclude_case_id: exclude the current case from results

    Returns:
        List of similar cases with their symptoms and outcomes
    """
    query_embedding = generate_embedding(query_text)

    # pgvector similarity search using raw SQL
    # SQLAlchemy doesn't have native pgvector operators yet
    # <=> = cosine distance (lower = more similar)
    sql = text("""
        SELECT
            tc.id as case_id,
            tc.chief_complaint,
            tc.priority,
            tc.ai_recommendation,
            s.description as symptom_description,
            s.severity,
            s.embedding <=> cast(:embedding as vector) as distance
        FROM symptoms s
        JOIN triage_cases tc ON s.case_id = tc.id
        WHERE
            s.embedding IS NOT NULL
            AND tc.priority IS NOT NULL
            AND tc.ai_recommendation IS NOT NULL
            AND (cast(:exclude_id as text) IS NULL OR tc.id::text != cast(:exclude_id as text))
        ORDER BY distance ASC
        LIMIT :limit
    """)

    result = await db.execute(
        sql,
        {
            "embedding": str(query_embedding),
            "exclude_id": exclude_case_id,
            "limit": limit,
        }
    )

    rows = result.fetchall()

    similar_cases = []
    for row in rows:
        similar_cases.append({
            "chief_complaint": row.chief_complaint,
            "symptom": row.symptom_description,
            "severity": row.severity,
            "priority": row.priority,
            "recommendation": row.ai_recommendation,
            "similarity": round(1 - row.distance, 3),
            # Convert distance to similarity score
            # distance 0 = similarity 1.0 (identical)
            # distance 1 = similarity 0.0 (unrelated)
        })

    return similar_cases


async def generate_triage_recommendation(
    case: TriageCaseDB,
    db: AsyncSession,
) -> str:
    """
    Generates an AI medical recommendation using RAG.

    Pipeline:
    1. Build query from case symptoms
    2. Find similar historical cases (RAG retrieval)
    3. Build prompt with context
    4. Send to LLM
    5. Return recommendation text

    Why RAG instead of just asking the LLM?
    Without context, the LLM gives generic advice.
    With similar cases, it gives specific, grounded advice
    based on what actually helped similar patients.

    Args:
        case: the TriageCaseDB object with symptoms loaded
        db: database session

    Returns:
        Medical recommendation as plain text
    """
    # Build query from all symptoms
    symptoms_text = " ".join([
        f"{s.description} (severity: {s.severity})"
        for s in case.symptoms
    ])

    # Find similar historical cases
    similar_cases = await find_similar_cases(
        query_text=symptoms_text,
        db=db,
        exclude_case_id=str(case.id),
    )

    # Build context from similar cases
    context = ""
    if similar_cases:
        context = "\n\nSimilar historical cases:\n"
        for i, similar in enumerate(similar_cases, 1):
            context += f"""
Case {i} (similarity: {similar['similarity']}):
  Symptom: {similar['symptom']}
  Priority assigned: {similar['priority']}
  Recommendation given: {similar['recommendation']}
"""

    # Build the prompt
    # Build the prompt
    system_prompt = """You are CarePath, a professional AI medical triage assistant operating in a controlled clinical simulation. 
Your role is to provide clear, protocol-based triage guidance. You do NOT diagnose — you classify urgency.

STRICT INSTRUCTIONS:
1. Do not use generic refusal phrases like "I cannot provide medical advice." 
2. You are part of a Decision Support System; provide the most helpful triage path based on the input.
3. Keep the tone calm, professional, and direct.

Always structure your response as:
1. ASSESSMENT: Evaluation of the situation (Urgency level).
2. IMMEDIATE ACTION: What the patient should do RIGHT NOW (e.g., hydration, rest, position).
3. WARNING SIGNS: Specific red flags that require immediate ER visit.
4. FOLLOW UP: Suggested timeframe to see a doctor.

Disclaimer: Always remind the user that this is for triage guidance only and not a substitute for professional care."""

    user_message = f"""Patient case:
Chief complaint: {case.chief_complaint}
Priority level: {case.priority}
Symptoms reported:
{symptoms_text}
{context}

Please provide a triage recommendation for this patient."""

    # Send to LLM
    try:
        llm = get_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = await llm.ainvoke(messages)
        # ainvoke = async invoke — non-blocking LLM call
        # While waiting for the LLM (~2-5 seconds),
        # the server handles other requests
        return response.content

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        # Graceful degradation — if AI fails, return a safe default
        # CarePath still works without AI, just with less context
        return (
            f"Based on your symptoms and priority level {case.priority}, "
            f"please follow the guidance appropriate for your triage level. "
            f"If symptoms worsen, seek immediate medical attention."
        )
