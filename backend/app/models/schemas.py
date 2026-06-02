"""
schemas.py — Pydantic Models: The Typed Contracts of Your API

WHY PYDANTIC MODELS MATTER:
FastAPI uses these classes to do three things automatically:
  1. VALIDATE incoming requests — if the client sends the wrong type or
     a missing field, FastAPI returns a 422 Unprocessable Entity error
     with a clear description of what was wrong. You write zero validation code.
  2. SERIALISE outgoing responses — Python objects (like datetimes, UUIDs)
     are automatically converted to JSON.
  3. DOCUMENT the API — the Swagger UI at /docs is generated entirely from
     these classes. Every field, type, and description shows up there.

Think of each class as a "shape" that data must conform to.
"""

from datetime import datetime
from pydantic import BaseModel, Field


# ================================================================== #
#  Phase 2: Document Upload                                            #
# ================================================================== #

class DocumentUploadResponse(BaseModel):
    """
    The JSON body returned after a successful PDF upload + chunking.

    Phase 3 will add: embedding_model, vectors_stored.
    Phase 4 will add: collection_name.
    """

    document_id: str = Field(
        description=(
            "A UUID (Universally Unique Identifier) that permanently identifies "
            "this document across the entire system. We use it to scope Qdrant "
            "searches to a single document when needed."
        ),
        examples=["3f7a1c2d-8e4b-4f6a-9d0e-1a2b3c4d5e6f"],
    )
    filename: str = Field(
        description="The original filename as provided by the user (not the sanitized version).",
        examples=["HR_Policy_2024.pdf"],
    )
    total_pages: int = Field(
        description="Total number of pages found in the PDF.",
        examples=[42],
    )
    total_chunks: int = Field(
        description=(
            "Number of text chunks produced by RecursiveCharacterTextSplitter. "
            "A 42-page document typically produces 80–200 chunks depending on "
            "text density."
        ),
        examples=[156],
    )
    chunk_size: int = Field(
        description="The character limit per chunk used during splitting.",
        examples=[1000],
    )
    chunk_overlap: int = Field(
        description="The character overlap between adjacent chunks.",
        examples=[200],
    )
    # Phase 3 fields — populated once embedding + storage is complete
    vectors_stored: int = Field(
        default=0,
        description=(
            "Number of vector embeddings written to Qdrant. "
            "Should equal total_chunks when Phase 3 is complete. "
            "0 = Phase 3 not yet active."
        ),
        examples=[51],
    )
    embedding_model: str = Field(
        default="",
        description="The HuggingFace embedding model used to create the vectors.",
        examples=["all-MiniLM-L6-v2"],
    )
    message: str = Field(
        description="Human-readable summary of the processing result.",
    )
    uploaded_at: datetime = Field(
        description="UTC timestamp of when the upload was processed.",
    )


# ================================================================== #
#  Phase 4: Chat / Query (defined now, implemented in Phase 4)        #
# ================================================================== #

class QueryRequest(BaseModel):
    """
    Sent by the React frontend when the user submits a question.
    FastAPI validates this automatically — if 'question' is missing or
    too short, a 422 error is returned before any code runs.
    """

    question: str = Field(
        min_length=3,
        max_length=1000,
        description="The user's natural-language question about the documents.",
        examples=["What is the company's maternity leave policy?"],
    )
    document_id: str | None = Field(
        default=None,
        description=(
            "Optional: restrict the search to one specific document. "
            "If None, the query searches across ALL uploaded documents."
        ),
    )
    top_k: int = Field(
        default=5,
        ge=1,   # ge = greater than or equal to
        le=20,  # le = less than or equal to
        description=(
            "How many document chunks to retrieve from Qdrant. "
            "5 is the sweet spot: enough context, fits in the LLM window."
        ),
    )


class SourceChunk(BaseModel):
    """A single retrieved document chunk included in the answer's citations."""

    page_content: str = Field(description="The raw text of this chunk.")
    page: int = Field(description="Page number in the original PDF (0-indexed).")
    source_filename: str = Field(description="The original PDF filename.")
    start_index: int = Field(
        description="Character position where this chunk starts in the page text."
    )
    score: float = Field(
        description="Cosine similarity score (0–1). Higher = more relevant."
    )


class QueryResponse(BaseModel):
    """
    The complete answer returned to the React frontend.
    Includes the generated answer AND the source chunks that justified it.
    Showing sources is a key feature for enterprise trust — users can verify
    the AI isn't hallucinating.
    """

    answer: str = Field(
        description="The LLM-generated answer to the user's question."
    )
    sources: list[SourceChunk] = Field(
        default_factory=list,
        description="The chunks retrieved from Qdrant that were used as context.",
    )
    question: str = Field(
        description="The original question echoed back (useful for the React chat history).",
    )
