"""
CarePath — API v1 Router
=========================
Combines all endpoint routers into one v1 router.
This is mounted on the main app in main.py.

Adding a new resource (e.g. doctors):
    1. Create src/api/v1/endpoints/doctors.py
    2. Import and include the router here
    3. Done — no changes needed in main.py
"""

from fastapi import APIRouter

from src.api.v1.endpoints import cases, patients

api_router = APIRouter()

api_router.include_router(patients.router)
api_router.include_router(cases.router)
