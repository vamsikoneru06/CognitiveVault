"""
main.py — FastAPI application entry point.

Run with:  uvicorn app.main:app --reload
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat
from app.api.routes import documents
from app.config import settings


# ------------------------------------------------------------------ #
#  Lifespan — startup / shutdown logic                                 #
# ------------------------------------------------------------------ #

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup (before yield) and shutdown (after yield)."""
    # Ensure the upload directory exists
    upload_path = settings.upload_path
    upload_path.mkdir(parents=True, exist_ok=True)
    print(f"✓ {settings.app_name} v{settings.app_version} started.")
    print(f"✓ Upload directory: {upload_path.resolve()}")
    print(f"✓ Debug mode: {settings.debug}")

    # Pre-warm the embedding model so the first upload is not slow.
    # Run in a thread-pool executor because model loading is synchronous.
    from app.core.embeddings import get_embedding_model
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, get_embedding_model)
    print("✓ All systems ready. CognitiveVault is accepting requests.")

    yield  # server runs here

    # Shutdown — nothing to clean up currently.


# ------------------------------------------------------------------ #
#  FastAPI Application                                                 #
# ------------------------------------------------------------------ #

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "An enterprise-grade, fully local RAG platform. "
        "Chat with your private documents. Zero data leaves your machine."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ------------------------------------------------------------------ #
#  CORS — allow the Vite dev server to talk to FastAPI                #
# ------------------------------------------------------------------ #

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # CRA fallback
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ #
#  Routers                                                             #
# ------------------------------------------------------------------ #

app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
app.include_router(chat.router,      prefix="/api/v1", tags=["Chat"])


# ------------------------------------------------------------------ #
#  Health check                                                        #
# ------------------------------------------------------------------ #

@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """Liveness probe — returns app name and version only."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }
