"""
chat.py — The Query / Retrieval-Generation Endpoint

Two endpoints live here:

  POST /api/v1/chat/query
      Full RAG pipeline: retrieve → generate → return complete JSON.
      This is a standard synchronous endpoint — FastAPI runs it in a
      thread pool, so Ollama's blocking generation doesn't freeze the server.

  POST /api/v1/chat/stream   (Phase 5 — already wired, used by React)
      Same pipeline but streams tokens back as Server-Sent Events (SSE).
      The React frontend connects to this for the live "typing" effect.

ARCHITECTURAL NOTE:
  This file is again intentionally thin. It:
    1. Validates the incoming QueryRequest (Pydantic does this automatically)
    2. Calls search_similar_chunks() from vector_store.py
    3. Calls generate_answer() or stream_answer() from llm.py
    4. Returns a QueryResponse

  Zero business logic lives here.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import settings
from app.core.llm import generate_answer, stream_answer
from app.core.vector_store import search_similar_chunks
from app.models.schemas import QueryRequest, QueryResponse, SourceChunk

router = APIRouter()


# ================================================================== #
#  POST /api/v1/chat/query — Full (non-streaming) RAG pipeline        #
# ================================================================== #

@router.post(
    "/chat/query",
    response_model=QueryResponse,
    summary="Ask a question about uploaded documents",
    description=(
        "Full RAG pipeline:\n"
        "1. Embeds the question using all-MiniLM-L6-v2\n"
        "2. Retrieves top-k similar chunks from Qdrant\n"
        "3. Builds a grounded prompt with the retrieved context\n"
        "4. Calls Ollama (Llama 3) to generate the answer\n"
        "5. Returns the answer + source citations\n\n"
        "**Note:** First response may take 5–30 seconds depending on hardware. "
        "Ollama runs the LLM entirely on your local machine."
    ),
)
def query_documents(request: QueryRequest) -> QueryResponse:
    """
    Answer a question using the RAG pipeline.

    WHY `def` (not `async def`)?
    The generate_answer() call to Ollama is a blocking operation — it
    takes 5–30 seconds and cannot be awaited. In FastAPI:
      - `async def` endpoints run on the event loop (must not block)
      - `def` endpoints automatically run in a thread pool (blocking is fine)

    Since generate_answer() is synchronous and slow, using plain `def`
    here is the correct FastAPI pattern. The server remains responsive
    to other requests while Llama 3 is generating.
    """

    # ── Step 1: Retrieve similar chunks from Qdrant ───────────────────
    # search_similar_chunks() embeds the question, queries Qdrant,
    # and returns [(Document, similarity_score), ...] tuples.
    results = search_similar_chunks(
        query=request.question,
        top_k=request.top_k,
        document_id=request.document_id,
    )

    if not results:
        raise HTTPException(
            status_code=404,
            detail=(
                "No relevant document chunks found. "
                "Please upload a PDF first using POST /api/v1/documents/upload."
            ),
        )

    # ── Step 2: Unpack results, attach scores to metadata ─────────────
    # results is a list of (Document, float) tuples.
    # We attach the float score to each Document's metadata so that
    # _build_user_message() in llm.py can include it in the prompt,
    # and so we can include it in the SourceChunk response.
    chunks = []
    for doc, score in results:
        doc.metadata["score"] = round(float(score), 4)
        chunks.append(doc)

    # Log what was retrieved (visible in uvicorn terminal during testing)
    print(f"\n📥 Query: '{request.question}'")
    print(f"   Retrieved {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks, 1):
        score = chunk.metadata.get("score", 0)
        page = chunk.metadata.get("page", "?")
        print(f"   [{i}] page={page+1}, score={score:.4f}")

    # ── Step 3: Generate the answer with Llama 3 ──────────────────────
    # This is the blocking call. FastAPI is running this def function
    # in a thread pool, so other requests can still be served.
    try:
        answer = generate_answer(chunks=chunks, question=request.question)
    except ConnectionRefusedError:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Cannot connect to Ollama at {settings.ollama_base_url}. "
                "Make sure the Ollama desktop app is running."
            ),
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("LLM generation error: %s", e)
        raise HTTPException(
            status_code=500,
            detail="LLM generation failed. Check server logs for details.",
        )

    print(f"   ✓ Answer generated ({len(answer)} chars)")

    # ── Step 4: Build source citations ────────────────────────────────
    # We return the source chunks alongside the answer so the frontend
    # can show "This answer is based on pages 7, 12, and 15 of your PDF."
    # This is critical for enterprise trust — users can verify the AI
    # didn't hallucinate by clicking through to the source.
    sources = [
        SourceChunk(
            page_content=chunk.page_content,
            page=chunk.metadata.get("page", 0),
            source_filename=chunk.metadata.get("source_filename", "unknown"),
            start_index=chunk.metadata.get("start_index", 0),
            score=chunk.metadata.get("score", 0.0),
        )
        for chunk in chunks
    ]

    return QueryResponse(
        answer=answer,
        sources=sources,
        question=request.question,
    )


# ================================================================== #
#  POST /api/v1/chat/stream — Streaming RAG pipeline (Phase 5)        #
# ================================================================== #

@router.post(
    "/chat/stream",
    summary="Ask a question and stream the response token by token",
    description=(
        "Same RAG pipeline as /chat/query but streams the answer using "
        "Server-Sent Events (SSE). The React frontend connects to this "
        "endpoint to display the live typing effect.\n\n"
        "Response format: plain text stream (each chunk is a token)."
    ),
    response_class=StreamingResponse,
)
def stream_query_documents(request: QueryRequest) -> StreamingResponse:
    """Stream a RAG-generated answer token by token."""
    import logging
    log = logging.getLogger(__name__)

    try:
        results = search_similar_chunks(
            query=request.question,
            top_k=request.top_k,
            document_id=request.document_id,
        )
    except Exception as e:
        log.error("Vector search error: %s", e)
        raise HTTPException(status_code=503, detail="Vector search unavailable.")

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No relevant document chunks found. Please upload a document first.",
        )

    chunks = []
    for doc, score in results:
        doc.metadata["score"] = round(float(score), 4)
        chunks.append(doc)

    return StreamingResponse(
        content=stream_answer(chunks=chunks, question=request.question),
        media_type="text/plain",
    )
