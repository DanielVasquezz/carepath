"""
CarePath — Application Entry Point
===================================
✔ Monitoring middleware (latency + errors)
✔ CORS safe config (FIXED)
✔ Custom OpenAPI (OAuth2 Swagger fix)
✔ Clean architecture
✔ Health + root endpoints
✔ DEBUG AUTH 401 IMPROVEMENT
"""

import time
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from src.api.v1.router import api_router
from src.core.config import settings


# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("CarePath-System")


# ─────────────────────────────────────────────
# APP INIT
# ─────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ─────────────────────────────────────────────
# CORS (FIXED + SAFE)
# ─────────────────────────────────────────────
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ─────────────────────────────────────────────
# MIDDLEWARE (MONITORING + AUTH DEBUG)
# ─────────────────────────────────────────────
@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start = time.time()

    auth_header = request.headers.get("authorization")

    # 🔥 SOLO DEBUG CASOS
    if "cases" in request.url.path:
        logger.info(f"AUTH HEADER: {auth_header}")

    try:
        response = await call_next(request)

        duration = time.time() - start

        logger.info(
            f"{request.method} {request.url.path} "
            f"| status={response.status_code} "
            f"| latency={duration:.4f}s"
        )

        return response

    except Exception as e:
        duration = time.time() - start

        logger.error(
            f"{request.method} {request.url.path} "
            f"| ERROR | latency={duration:.4f}s | {str(e)}"
        )
        raise


# ─────────────────────────────────────────────
# OPENAPI (SWAGGER AUTH FIX)
# ─────────────────────────────────────────────
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title="CarePath — Inteligencia Médica",
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": f"{settings.API_V1_PREFIX}/auth/login",
                    "scopes": {},
                }
            },
        }
    }

    schema["security"] = [{"OAuth2PasswordBearer": []}]

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
app.include_router(
    api_router,
    prefix=settings.API_V1_PREFIX,
)


# ─────────────────────────────────────────────
# HEALTH CHECKS
# ─────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "timestamp": time.time(),
    }


@app.get("/")
async def root():
    return {
        "message": "CarePath API running",
        "version": settings.APP_VERSION,
    }