"""
main.py — The FastAPI Application Entry Point

This is the file that uvicorn loads when you run:
    uvicorn app.main:app --reload

  "app.main" = the Python module path (app/main.py)
  ":app"     = the FastAPI instance variable named `app` inside that module
  "--reload" = restart the server automatically when you save a file (dev only)

In later phases, we will add routes (endpoints) to this file by importing
the routers defined in app/api/routes/.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat       # Phase 4: query/generation route
from app.api.routes import documents  # Phase 2: document upload route
from app.config import settings


# ------------------------------------------------------------------ #
#  Create the FastAPI Application                                      #
# ------------------------------------------------------------------ #
# These metadata values power the auto-generated Swagger UI at
# http://localhost:8000/docs — very useful for testing your API.
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "An enterprise-grade, fully local RAG platform. "
        "Chat with your private PDFs. Zero data leaves your machine."
    ),
    docs_url="/docs",      # Swagger UI
    redoc_url="/redoc",    # ReDoc UI (alternative documentation view)
)


# ------------------------------------------------------------------ #
#  CORS Middleware — Critical for React to Talk to FastAPI             #
# ------------------------------------------------------------------ #
# WHAT IS CORS?
# Your browser has a security rule: JavaScript on page A (e.g. localhost:5173)
# is NOT allowed to fetch data from page B (localhost:8000) unless page B
# explicitly says it's OK. That permission is called CORS.
#
# Without this middleware, every API call from your React app would be
# silently blocked by the browser with a "CORS error".
#
# allow_origins: list of frontend URLs we trust. Vite (React) runs on 5173.
# allow_methods: which HTTP verbs are allowed (GET, POST, etc.).
# allow_headers: which HTTP headers can be sent (Content-Type, etc.).
# allow_credentials: allow cookies/auth headers to be included in requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Create-React-App fallback
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ #
#  Startup Event — Runs ONCE when the server first starts             #
# ------------------------------------------------------------------ #
@app.on_event("startup")
async def on_startup() -> None:
    """
    Runs once when uvicorn starts. Sets up directories and pre-loads
    the embedding model so the first upload request isn't slow.
    """
    import asyncio

    # ── Uploads directory ─────────────────────────────────────────────
    upload_path = settings.upload_path
    upload_path.mkdir(parents=True, exist_ok=True)

    print(f"✓ {settings.app_name} v{settings.app_version} started.")
    print(f"✓ Upload directory: {upload_path.resolve()}")
    print(f"✓ Debug mode: {settings.debug}")

    # ── Pre-warm the embedding model ──────────────────────────────────
    # WHY: Loading the model the first time takes 30–90 seconds (download)
    # or ~2 seconds (from cache). If we don't pre-load it here, the first
    # PDF upload request will appear to hang without explanation.
    # By loading it at startup, the server prints progress and the user
    # sees that something is happening.
    #
    # get_embedding_model() is synchronous (it's a regular Python function,
    # not async). We use run_in_executor to run it in a thread pool so it
    # doesn't block uvicorn's event loop during startup.
    from app.core.embeddings import get_embedding_model
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, get_embedding_model)

    print("✓ All systems ready. CognitiveVault is accepting requests.")


# ------------------------------------------------------------------ #
#  Routes                                                              #
# ------------------------------------------------------------------ #
# include_router() "mounts" all the endpoints defined in documents.py
# under the /api/v1 prefix with a "Documents" tag in Swagger UI.
#
# So @router.post("/documents/upload") in documents.py becomes:
#     POST http://localhost:8000/api/v1/documents/upload
#
# The prefix keeps API versioning clean — if we ever need to make
# breaking changes, we add a /api/v2 prefix without touching v1.
app.include_router(
    documents.router,
    prefix="/api/v1",
    tags=["Documents"],
)
app.include_router(
    chat.router,
    prefix="/api/v1",
    tags=["Chat"],
)


@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """
    Confirms the API is running and returns current configuration.

    Visit http://localhost:8000/health in your browser to verify
    Phase 1 is working correctly.
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }
