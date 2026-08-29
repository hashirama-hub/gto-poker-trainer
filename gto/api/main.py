"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gto.config import get_settings
from gto.db import init_db, close_db
from gto.api.routes import auth, gto, quiz, hands, health, models, training

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.2.0",
    description="GTO Poker Trainer API for MTT (8-max)",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(gto.router, prefix="/gto", tags=["gto"])
app.include_router(quiz.router, prefix="/quiz", tags=["quiz"])
app.include_router(hands.router, prefix="/hands", tags=["hands"])
app.include_router(models.router, prefix="/models", tags=["models"])
app.include_router(training.router, prefix="/training", tags=["training"])


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/health",
    }


def run():
    import uvicorn
    uvicorn.run("gto.api.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()