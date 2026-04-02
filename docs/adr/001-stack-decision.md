# ADR-001: Technology Stack Decision — CarePath

Date: 2025-04-01
Status: Accepted
Author: Daniel Alejandro Vasquez Orellana

## Context

CarePath needs to process patient symptoms in real time, integrate language models for intelligent triage, and scale to multiple concurrent users without degrading response time.

## Decisions and rationale

## Python 3.12 as the main language

Chosen over: Node.js, Go
Reason: The AI/ML ecosystem (LangChain, scikit-learn, transformers) is native to Python. A healthcare system with AI built in another language would require unnecessary bridges and data conversions.

## FastAPI over Django or Flask

Chosen over: Django REST Framework, Flask
Reason: FastAPI is async-native (critical for LLM calls that take 1–3 seconds), automatically generates OpenAPI documentation (a requirement for hospital system integration), and has one of the best performance levels in the Python ecosystem according to TechEmpower benchmarks.

## PostgreSQL + pgvector over MongoDB or pure vector databases

Chosen over: MongoDB, Pinecone, Weaviate
Reason: Patient data has a strong relational structure (patient → consultations → diagnoses → medications). pgvector provides semantic search capabilities without sacrificing ACID guarantees, which are required for regulated medical data.

## AWS over Azure or GCP

Chosen over: Microsoft Azure, Google Cloud
Reason: 80% of healthtech startups use AWS. The Python/ML ecosystem has native support (SageMaker, Bedrock). The Free Tier allows full development without initial cost.

## Consequences
The team must be familiar with Python async programming (asyncio, await)
Database migrations are handled with Alembic
Tests must cover both REST endpoints and triage logic