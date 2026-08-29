"""FastAPI application for GTO Poker Trainer API."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gto.api.routes import auth, gto, health, quiz
from gto.config import get_settings
from gto.db import close as close_db, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    await init_db()
    yield
    logger.info("Shutting down...")
    await close_db()


app = FastAPI(
    title="GTO Poker Trainer API",
    description="GTO Wizard mini - Poker GTO training and analysis API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(quiz.router)
app.include_router(gto.router)


@app.get("/")
async def root():
    return {
        "name": "GTO Poker Trainer API",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/health",
    }


def run():
    import uvicorn
    uvicorn.run(
        "gto.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=True,
    )


if __name__ == "__main__":
    run()