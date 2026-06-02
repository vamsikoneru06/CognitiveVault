"""
embeddings.py — The Local Embedding Model

This module owns the HuggingFace embedding model. The rest of the codebase
never imports HuggingFaceEmbeddings directly — they call get_embedding_model()
from here. This gives us one place to swap models if we upgrade.

MODEL: all-MiniLM-L6-v2
  - "all"        → trained on a large, general-purpose dataset
  - "MiniLM"     → a distilled (compressed) model architecture
  - "L6"         → 6 transformer layers (the "depth" of the neural network)
  - "v2"         → second version
  - Output:      384-dimensional float vectors
  - Size:        ~90MB (downloaded once to ~/.cache/huggingface/)
  - Speed:       ~500 sentences/second on CPU
  - Quality:     Excellent for semantic search over English documents

FIRST RUN NOTE:
  The first time get_embedding_model() is called, sentence-transformers
  will download the model from HuggingFace Hub. This takes 30–90 seconds
  depending on your internet speed. Every run after that loads from cache
  and takes ~1–2 seconds.

SINGLETON PATTERN:
  @lru_cache(maxsize=1) means this function's result is cached after the
  first call. The model is loaded into RAM once and reused forever.
  Without this, every single PDF upload would reload the model from disk
  (~2 seconds of overhead per request).
"""

from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

from app.config import settings


@lru_cache(maxsize=1)
def get_embedding_model() -> HuggingFaceEmbeddings:
    """
    Load the HuggingFace embedding model and cache it permanently.

    lru_cache with maxsize=1 is Python's simplest singleton pattern:
      - Call 1: executes the full function body, caches the result
      - Call 2+: returns the cached HuggingFaceEmbeddings instance instantly
        (the function body does NOT run again)

    Returns:
        A HuggingFaceEmbeddings instance ready to call .embed_documents()
        or .embed_query() on.
    """
    print(f"⏳ Loading embedding model '{settings.embedding_model}'...")
    print("   (First run only: downloading ~90MB from HuggingFace Hub)")

    model = HuggingFaceEmbeddings(
        # The HuggingFace model ID. sentence-transformers downloads this
        # automatically to ~/.cache/huggingface/
        model_name=settings.embedding_model,

        # Force CPU execution. We have no GPU dependency.
        # Change to "cuda" if you have a GPU and want faster embeddings.
        model_kwargs={"device": "cpu"},

        # normalize_embeddings=True scales every vector to unit length (L2 norm = 1).
        # This has two benefits:
        #   1. Cosine similarity becomes equivalent to dot product (faster).
        #   2. All vectors live on the surface of a unit sphere, making
        #      similarity scores consistently interpretable as [0, 1].
        encode_kwargs={"normalize_embeddings": True},
    )

    print(f"✓ Embedding model '{settings.embedding_model}' ready.")
    print(f"  Output dimensions: {settings.embedding_dimension}")
    return model
