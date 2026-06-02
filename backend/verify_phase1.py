"""
verify_phase1.py — Phase 1 Environment Verification Script

Run this BEFORE starting Phase 2 to confirm everything is installed
and reachable. If any check fails, it tells you exactly what to fix.

Usage (from the backend/ directory, with venv activated):
    python verify_phase1.py
"""

import sys
import importlib
import urllib.request
import urllib.error
import json


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def check(label: str, ok: bool, hint: str = "") -> bool:
    status = "  PASS" if ok else "  FAIL"
    color = "\033[92m" if ok else "\033[91m"
    reset = "\033[0m"
    print(f"{color}{status}{reset}  {label}")
    if not ok and hint:
        print(f"        FIX: {hint}")
    return ok


def http_get_json(url: str) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return json.loads(r.read())
    except Exception:
        return None


# ------------------------------------------------------------------ #
#  Checks                                                              #
# ------------------------------------------------------------------ #

def run_checks() -> None:
    print("\n========================================")
    print("  CognitiveVault — Phase 1 Verification")
    print("========================================\n")

    all_ok = True

    # 1. Python version
    major, minor = sys.version_info[:2]
    ok = major == 3 and minor >= 11
    all_ok &= check(
        f"Python 3.11+ (found {major}.{minor})", ok,
        "Download Python 3.11 from https://python.org"
    )

    # 2. Required packages
    packages = {
        "fastapi": "pip install fastapi",
        "uvicorn": "pip install uvicorn[standard]",
        "langchain": "pip install langchain",
        "langchain_community": "pip install langchain-community",
        "langchain_text_splitters": "pip install langchain-text-splitters",
        "langchain_huggingface": "pip install langchain-huggingface",
        "qdrant_client": "pip install qdrant-client",
        "sentence_transformers": "pip install sentence-transformers",
        "ollama": "pip install ollama",
        "pypdf": "pip install pypdf",
        "pydantic_settings": "pip install pydantic-settings",
        "aiofiles": "pip install aiofiles",
        "multipart": "pip install python-multipart",
    }
    for pkg, install_cmd in packages.items():
        try:
            importlib.import_module(pkg)
            ok = True
        except ImportError:
            ok = False
        all_ok &= check(f"Package: {pkg}", ok, install_cmd)

    # 3. Qdrant reachable
    data = http_get_json("http://localhost:6333/")
    ok = data is not None
    all_ok &= check(
        "Qdrant reachable at localhost:6333", ok,
        "Run: docker compose up -d  (from project root, where docker-compose.yml is)"
    )

    # 4. Ollama reachable
    data = http_get_json("http://localhost:11434/api/tags")
    ok = data is not None
    all_ok &= check(
        "Ollama reachable at localhost:11434", ok,
        "Start Ollama desktop app or run: ollama serve"
    )

    # 5. Ollama model pulled
    if data is not None:
        models = [m.get("name", "") for m in data.get("models", [])]
        has_model = any("llama3" in m or "mistral" in m for m in models)
        all_ok &= check(
            f"Ollama model available {models}", has_model,
            "Run: ollama pull llama3   (or: ollama pull mistral)"
        )

    # 6. Config loads without error
    try:
        from app.config import settings
        ok = settings.app_name == "CognitiveVault"
    except Exception as e:
        ok = False
    all_ok &= check(
        "app/config.py loads correctly", ok,
        "Check that .env file exists in backend/ (copy .env.example to .env)"
    )

    # 7. Uploads directory exists
    from pathlib import Path
    ok = Path("uploads").exists()
    all_ok &= check(
        "uploads/ directory exists", ok,
        "Run: mkdir uploads  (from backend/)"
    )

    # ---- Summary ----
    print()
    if all_ok:
        print("\033[92m  All checks passed! You are ready for Phase 2.\033[0m")
    else:
        print("\033[91m  Some checks failed. Fix the issues above and re-run.\033[0m")
    print()


if __name__ == "__main__":
    run_checks()
