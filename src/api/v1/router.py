# router.py — versión corregida
from fastapi import APIRouter
from src.api.v1.endpoints import auth, cases, patients

api_router = APIRouter()

api_router.include_router(patients.router)
api_router.include_router(cases.router)
api_router.include_router(auth.router)