"""
documents.py — The HTTP Layer for Document Management

ARCHITECTURAL PRINCIPLE:
This file is intentionally "dumb". Its only job is:
  1. Accept an HTTP request
  2. Validate the input (via security.py)
  3. Call the appropriate function from app/core/
  4. Return the result as an HTTP response

Notice what is NOT here:
  - No PDF parsing logic
  - No chunking logic
  - No embedding logic
  - No database logic

All of that lives in app/core/. If you ever need to process PDFs from
a CLI script, a cron job, or a different API version, you just call the
same core functions. The HTTP layer is irrelevant to the logic.

This separation is called "Separation of Concerns" and it's what makes
code maintainable as a project grows.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.core.ingestion import load_and_chunk_pdf
from app.core.vector_store import store_chunks   # Phase 3: embed + store
from app.models.schemas import DocumentUploadResponse
from app.utils.security import sanitize_filename, validate_pdf

# APIRouter is like a mini FastAPI app.
# We define routes on it, then "mount" it to the main app in main.py
# with a prefix like "/api/v1". This keeps routes modular.
router = APIRouter()


@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=200,
    summary="Upload and index a PDF document",
    description=(
        "Upload a PDF file (max 50MB). "
        "The system will:\n"
        "1. Validate the file (extension, magic bytes, size)\n"
        "2. Save it securely with a sanitized filename\n"
        "3. Parse the PDF and split it into overlapping text chunks\n"
        "4. Return chunk statistics\n\n"
        "**Note:** Phase 3 will add embedding and vector storage."
    ),
)
async def upload_document(
    file: UploadFile = File(
        ...,  # The "..." means this field is REQUIRED (no default)
        description="A PDF file to upload and index (max 50MB)",
    ),
) -> DocumentUploadResponse:
    """
    Handle a PDF upload.

    FastAPI parses the multipart/form-data request for us and provides
    the file as an UploadFile object. We never write the multipart
    parsing code ourselves.

    The `async def` is critical here: while we're waiting for the file
    to be read from the network or written to disk, FastAPI can serve
    other requests. Without async, each upload would freeze the server.
    """

    # ── Phase 1: Validate ─────────────────────────────────────────────
    # This either passes silently or raises an HTTPException.
    # If it raises, FastAPI immediately returns the error JSON to the
    # client and the code below NEVER executes.
    await validate_pdf(file)

    # ── Phase 2: Generate IDs and Paths ───────────────────────────────
    # uuid4() generates a random UUID like "3f7a1c2d-8e4b-4f6a-..."
    # We use this as the document's permanent identity in Qdrant.
    document_id = str(uuid.uuid4())

    # Produce a safe filename that can't escape the uploads directory
    safe_filename = sanitize_filename(file.filename)

    # Build the full path where we'll save the file.
    # settings.upload_path is a Path object (e.g. Path("uploads"))
    # The / operator on Path objects joins paths safely:
    #   Path("uploads") / "3a1b_file.pdf" → Path("uploads/3a1b_file.pdf")
    save_path: Path = settings.upload_path / safe_filename

    # ── Phase 3: Save the File to Disk ────────────────────────────────
    # WHY aiofiles?
    # The normal Python way to write a file is:
    #   with open(path, "wb") as f:
    #       f.write(content)
    #
    # But open() and f.write() are SYNCHRONOUS — they block until done.
    # In an async FastAPI server, blocking = freezing the whole server.
    # aiofiles provides async versions:
    #   async with aiofiles.open(path, "wb") as f:
    #       await f.write(content)
    # This yields control back to FastAPI while the disk write happens.
    try:
        async with aiofiles.open(save_path, "wb") as out_file:
            content = await file.read()  # read the entire uploaded file into memory
            await out_file.write(content)  # write it to disk asynchronously
    except OSError as e:
        # OSError covers: permission denied, disk full, path doesn't exist, etc.
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file to disk: {e}",
        )

    # ── Phase 4: Parse and Chunk the PDF ──────────────────────────────
    # Call our core ingestion logic. This runs synchronously (no await)
    # because pypdf and LangChain are not async libraries.
    # For production, this would be moved to a background task (Phase 5+).
    try:
        chunks, total_pages = load_and_chunk_pdf(
            file_path=save_path,
            document_id=document_id,
            original_filename=file.filename,
        )
    except ValueError as e:
        # ValueError = we understood the error (empty PDF, no text, etc.)
        # Clean up the file we saved — don't leave orphan files on disk
        save_path.unlink(missing_ok=True)  # missing_ok=True: don't crash if file is already gone
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # Unexpected error (corrupted PDF, pypdf bug, etc.)
        save_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"PDF processing failed: {e}",
        )

    # ── Phase 4: Embed Chunks and Store in Qdrant ─────────────────────
    # store_chunks() calls the embedding model on every chunk's text,
    # then bulk-inserts the resulting vectors + metadata into Qdrant.
    #
    # ⚠  FIRST RUN WARNING:
    # The first time this runs, all-MiniLM-L6-v2 (~90MB) will be
    # downloaded from HuggingFace Hub. The request will appear to hang
    # for 30–90 seconds. This is normal. Watch the uvicorn terminal
    # for progress messages. Every subsequent request is fast (~1–3s).
    try:
        vectors_stored = store_chunks(chunks)
    except ConnectionRefusedError:
        save_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=503,
            detail=(
                "Cannot connect to Qdrant on "
                f"{settings.qdrant_host}:{settings.qdrant_port}. "
                "Is Docker running? Try: docker compose up -d"
            ),
        )
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Embedding/storage step failed: {e}",
        )

    # ── Phase 5: Return the Response ──────────────────────────────────
    return DocumentUploadResponse(
        document_id=document_id,
        filename=file.filename,
        total_pages=total_pages,
        total_chunks=len(chunks),
        chunk_size=1000,
        chunk_overlap=200,
        vectors_stored=vectors_stored,
        embedding_model=settings.embedding_model,
        message=(
            f"Successfully processed '{file.filename}': "
            f"{total_pages} pages → {len(chunks)} chunks → "
            f"{vectors_stored} vectors stored in Qdrant. "
            f"Ready for chat queries."
        ),
        uploaded_at=datetime.now(timezone.utc),
    )
