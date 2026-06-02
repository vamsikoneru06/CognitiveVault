"""
config.py — The Single Source of Truth for All Settings

WHY THIS FILE EXISTS:
Instead of scattering magic strings like "localhost" and "6333" throughout
the codebase, we centralise every configurable value here. This means:
  1. To change any setting, you edit ONE file (or the .env).
  2. Pydantic validates types automatically — if QDRANT_PORT is set to "abc"
     in .env, the app crashes immediately with a clear error, not silently
     at runtime when you try to connect.
  3. Secrets (future API keys etc.) stay in .env and never touch source code.

HOW IT WORKS:
  - BaseSettings reads variables from your .env file first,
    then falls back to the defaults defined here.
  - The `settings` object at the bottom is a singleton — import it
    everywhere with:  from app.config import settings
"""

from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ------------------------------------------------------------------ #
    #  Application                                                         #
    # ------------------------------------------------------------------ #
    app_name: str = "CognitiveVault"
    app_version: str = "1.0.0"
    # In DEBUG mode FastAPI shows detailed error tracebacks.
    # Set DEBUG=False in production.
    debug: bool = False

    # ------------------------------------------------------------------ #
    #  Qdrant Vector Database                                              #
    # ------------------------------------------------------------------ #
    # Where the Qdrant Docker container is reachable.
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    # A "collection" in Qdrant is like a table in a relational database.
    # All our document embeddings will be stored in this collection.
    qdrant_collection_name: str = "cognitive_vault"

    # ------------------------------------------------------------------ #
    #  Ollama Local LLM                                                    #
    # ------------------------------------------------------------------ #
    ollama_base_url: str = "http://localhost:11434"
    # Change to "mistral" if you pulled Mistral instead of Llama3.
    ollama_model: str = "llama3"

    # ------------------------------------------------------------------ #
    #  HuggingFace Embeddings                                              #
    # ------------------------------------------------------------------ #
    # all-MiniLM-L6-v2: small (90MB), fast, 384-dimensional output vectors.
    # It will auto-download to ~/.cache/huggingface/ on first use.
    embedding_model: str = "all-MiniLM-L6-v2"
    # This MUST match the actual output size of the model above.
    # Qdrant needs to know this upfront when we create the collection.
    embedding_dimension: int = 384

    # ------------------------------------------------------------------ #
    #  File Upload Security                                                #
    # ------------------------------------------------------------------ #
    max_file_size_mb: int = 50
    # The directory (relative to backend/) where uploaded PDFs are saved.
    upload_dir: str = "uploads"

    # ------------------------------------------------------------------ #
    #  Pydantic-Settings Configuration                                     #
    # ------------------------------------------------------------------ #
    # This tells pydantic-settings WHERE to find the .env file and that
    # variable names are case-insensitive (QDRANT_HOST == qdrant_host).
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------ #
    #  Computed / Derived Properties                                       #
    # ------------------------------------------------------------------ #
    @property
    def max_file_size_bytes(self) -> int:
        """Convert the human-readable MB limit to bytes for comparison."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        """Return the upload directory as an absolute Path.
        Resolving relative to this file prevents CWD-dependent behaviour."""
        return Path(__file__).parent.parent / self.upload_dir

    @field_validator("embedding_dimension")
    @classmethod
    def validate_dimension(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Embedding dimension must be a positive integer.")
        return v


# ------------------------------------------------------------------ #
#  Singleton Instance                                                  #
# ------------------------------------------------------------------ #
# Create ONE instance of Settings. Every other module imports THIS
# object — they do NOT call Settings() themselves.
# This ensures the .env file is only read once.
settings = Settings()
