"""
Main FastAPI Application for GTA 6 Automated Clipping Platform.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from packages.shared.config import settings
from packages.shared.database import init_db, AsyncSessionLocal
from apps.api.auth import seed_initial_admin
from apps.api.routes import (
    auth, streamers, permissions, sessions,
    candidates, clips, publishing, storage,
    metrics, audit, health, settings_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database schema and default admin
    await init_db()
    async with AsyncSessionLocal() as db:
        await seed_initial_admin(db)
    yield
    # Shutdown logic if any


app = FastAPI(
    title=settings.APP_NAME,
    description="Automated GTA 6 livestream capture, AI highlights, vertical video editing, and publishing.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router)
app.include_router(streamers.router)
app.include_router(permissions.router)
app.include_router(sessions.router)
app.include_router(candidates.router)
app.include_router(clips.router)
app.include_router(publishing.router)
app.include_router(storage.router)
app.include_router(metrics.router)
app.include_router(audit.router)
app.include_router(health.router)
app.include_router(settings_router.router)

# Serve web dashboard build if it exists
web_dist = Path(__file__).parent.parent / "web" / "dist"
if web_dist.exists():
    app.mount("/", StaticFiles(directory=str(web_dist), html=True), name="web")


@app.get("/api")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_url": "/api/health"
    }
