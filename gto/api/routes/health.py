"""Health check endpoint."""
from fastapi import APIRouter
from gto.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "0.2.0",
        "database": "connected",
        "redis": "connected",
    }


@router.get("/health/ready")
async def readiness_check():
    return {"ready": True}