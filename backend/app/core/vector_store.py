"""
vector_store.py — All Qdrant Operations

This module is the single interface between CognitiveVault and Qdrant.
No other file imports qdrant_client directly. If we ever switch vector
databases (e.g. to pgvector), we only change this file.

THREE RESPONSIBILITIES:
  1. ensure_collection_exists() — creates the Qdrant collection on first use
  2. store_chunks()             — embeds Document chunks and saves them to Qdrant
  3. search_similar_chunks()    — finds the top-k most relevant chunks for a query
                                   (used in Phase 4)
"""

from functools import lru_cache
from typing import List

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, VectorParams

from app.config import settings
from app.core.embeddings import get_embedding_model


# ------------------------------------------------------------------ #
#  Qdrant Client — Singleton                                           #
# ------------------------------------------------------------------ #

@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """
    Create and cache the Qdrant HTTP client.

    QdrantClient connects to the Qdrant server (running in Docker).
    It does NOT open a persistent socket — each operation opens and
    closes its own connection. The client object itself is lightweight
    and safe to reuse across requests.
    """
    client = QdrantClient(
        host=settings.qdrant_host,   # "localhost" from config
        port=settings.qdrant_port,   # 6333 from config
    )
    print(f"✓ Qdrant client connected to {settings.qdrant_host}:{settings.qdrant_port}")
    return client


# ------------------------------------------------------------------ #
#  Collection Management                                               #
# ------------------------------------------------------------------ #

def ensure_collection_exists() -> None:
    """
    Create the Qdrant collection if it doesn't already exist.

    WHY WE CALL THIS BEFORE EVERY OPERATION:
    The collection might not exist yet on a fresh Qdrant instance.
    Rather than running a separate setup script, we do a quick check
    at runtime. The check is a single lightweight API call.

    COLLECTION SCHEMA:
    We define two things upfront — the size (dimension) of our vectors
    and how to measure similarity between them.

      vectors_config=VectorParams(
          size=384,             ← must exactly match the embedding model output
          distance=COSINE,      ← measure similarity by angle, not distance
      )

    This schema is FIXED after creation. Changing the embedding model
    later (e.g. to a 768-dim model) requires deleting and recreating
    the collection (and re-indexing all documents).
    """
    client = get_qdrant_client()

    existing_names = [c.name for c in client.get_collections().collections]

    if settings.qdrant_collection_name not in existing_names:
        client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config=VectorParams(
                # CRITICAL: This MUST match settings.embedding_dimension (384).
                # If the model produces 384-dim vectors but the collection
                # expects 768, Qdrant will reject every insert with an error.
                size=settings.embedding_dimension,

                # COSINE: measures the angle between two vectors.
                # Score range: [0, 1] when embeddings are normalized.
                # Score 1.0 = identical direction = identical meaning.
                # Score 0.0 = perpendicular = unrelated meaning.
                # Alternative: Distance.DOT (dot product) or Distance.EUCLID
                distance=Distance.COSINE,
            ),
        )
        print(f"✓ Created Qdrant collection: '{settings.qdrant_collection_name}'")
        print(f"  Vector size: {settings.embedding_dimension} | Distance: COSINE")
    else:
        print(f"✓ Collection '{settings.qdrant_collection_name}' already exists.")


# ------------------------------------------------------------------ #
#  LangChain Vector Store Interface                                    #
# ------------------------------------------------------------------ #

def get_vector_store() -> QdrantVectorStore:
    """
    Return a LangChain QdrantVectorStore instance.

    QdrantVectorStore is LangChain's abstraction over Qdrant. It wraps
    the raw Qdrant client and provides high-level methods:
      .add_documents(chunks)                → embed + store
      .similarity_search_with_score(query)  → embed query + search

    We always call ensure_collection_exists() first to guarantee the
    collection is ready before any operation.
    """
    ensure_collection_exists()

    return QdrantVectorStore(
        client=get_qdrant_client(),
        collection_name=settings.qdrant_collection_name,
        # This is the embedding model that will be called to:
        #   a) embed documents before storing them
        #   b) embed the query string before searching
        embedding=get_embedding_model(),
    )


# ------------------------------------------------------------------ #
#  Phase 3: Store                                                      #
# ------------------------------------------------------------------ #

def store_chunks(chunks: List[Document]) -> int:
    """
    Embed a list of Document chunks and store them in Qdrant.

    WHAT HAPPENS INSIDE add_documents():
      1. Calls embedding_model.embed_documents([chunk.page_content for chunk in chunks])
         → This runs all-MiniLM-L6-v2 on every chunk text in one batch.
         → Returns a list of 384-float vectors, one per chunk.

      2. Generates a UUID for each chunk (the Qdrant point ID).

      3. Packages each chunk as a Qdrant PointStruct:
           PointStruct(
               id=uuid,
               vector=[0.023, -0.451, ...],   ← the 384-float embedding
               payload={
                   "page_content": "...",      ← the raw text (for display)
                   "metadata": {               ← everything from document.metadata
                       "document_id": "...",
                       "source_filename": "...",
                       "page": 4,
                       "start_index": 2048,
                   }
               }
           )

      4. Calls qdrant_client.upsert(points=[...]) to bulk-insert all points.

    Args:
        chunks: The list of Document objects from load_and_chunk_pdf().

    Returns:
        The number of chunks successfully stored.
    """
    vector_store = get_vector_store()

    # add_documents() returns a list of string IDs (one UUID per chunk).
    stored_ids = vector_store.add_documents(documents=chunks)

    print(f"✓ Stored {len(stored_ids)} vectors in Qdrant.")
    return len(stored_ids)


# ------------------------------------------------------------------ #
#  Phase 4: Search (defined now, called in Phase 4)                   #
# ------------------------------------------------------------------ #

def search_similar_chunks(
    query: str,
    top_k: int = 5,
    document_id: str | None = None,
) -> List[tuple[Document, float]]:
    """
    Find the top-k chunks most semantically similar to a query string.

    WHAT HAPPENS INSIDE:
      1. Calls embedding_model.embed_query(query)
         → Produces a single 384-float vector for the question.

      2. Sends that vector to Qdrant's search API.
         Qdrant compares it to every stored vector using COSINE similarity.
         Returns the top-k closest matches.

      3. Qdrant reconstructs the full Document (text + metadata) from
         each matching point's payload.

    Args:
        query:       The user's natural-language question.
        top_k:       Number of chunks to return (default: 5).
        document_id: Optional — restrict search to one specific document.
                     If None, searches across ALL documents in the collection.

    Returns:
        List of (Document, similarity_score) tuples, best match first.
        Score is in [0, 1] for normalized embeddings; 1.0 = identical.
    """
    vector_store = get_vector_store()

    # Optional filter: only return chunks from a specific document.
    # This uses Qdrant's payload filtering — the filter is applied
    # server-side before similarity scoring, so it's very fast.
    qdrant_filter: Filter | None = None
    if document_id:
        qdrant_filter = Filter(
            must=[
                FieldCondition(
                    # "metadata.document_id" is the JSON path inside
                    # each point's payload (set when we stored the chunks)
                    key="metadata.document_id",
                    match=MatchValue(value=document_id),
                )
            ]
        )

    results: List[tuple[Document, float]] = vector_store.similarity_search_with_score(
        query=query,
        k=top_k,
        filter=qdrant_filter,
    )

    return results
