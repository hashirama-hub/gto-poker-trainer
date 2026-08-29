"""API routes for health checks."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from gto.api.schemas import HealthResponse
from gto.config import get_settings
from gto.db import get_session

router = APIRouter(prefix="/health", tags=["health"])

settings = get_settings()


@router.get("", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_session)):
    db_status = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
    
    redis_status = "ok"
    try:
        import redis.asyncio as redis
        r = redis.from_url(settings.redis_url)
        await r.ping()
        await r.close()
    except Exception:
        redis_status = "error"
    
    return HealthResponse(
        status="ok" if db_status == "ok" and redis_status == "ok" else "degraded",
        database=db_status,
        redis=redis_status,
        version="0.2.0",
    )