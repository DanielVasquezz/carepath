# src/main.py
"""
CarePath — Application Entry Point
====================================
This is the file that starts the entire CarePath server.
Run with: uvicorn src.main:app --reload

Everything starts here:
- FastAPI app is created
- Middleware is configured (CORS, logging)
- Routers are mounted
- Health check is defined
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.router import api_router
from src.core.config import settings

# ── Create the FastAPI application ───────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",     # ReDoc alternative docs
    openapi_url="/openapi.json",  # raw OpenAPI schema
)

# ── CORS Middleware ───────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing
# Browsers block JavaScript from calling APIs on different domains
# by default. CORS middleware tells the browser: "these domains
# are allowed to call our API."
#
# Without this: your React frontend (localhost:3000) cannot call
# your FastAPI backend (localhost:8000). Browser blocks it.
# With this: the allowed origins can make API calls freely.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],     # GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],     # Authorization, Content-Type, etc.
)

# ── Mount API routes ──────────────────────────────────────────────
app.include_router(
    api_router,
    prefix=settings.API_V1_PREFIX,  # /api/v1
)

# ── Health check ─────────────────────────────────────────────────
@app.get(
    "/health",
    tags=["system"],
    summary="Health check",
    description="Returns OK if the server is running. Used by AWS load balancer.",
)
async def health_check() -> dict[str, str]:
    """
    GET /health

    Every production system needs a health check endpoint.
    AWS load balancers ping this every 30 seconds.
    If it returns non-200, AWS marks the instance as unhealthy
    and stops sending traffic to it.

    It's also the first thing you check when something is wrong:
    curl https://api.carepath.app/health
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
    
@app.get("/")
def root():
    return {"message": "CarePath API is running"}