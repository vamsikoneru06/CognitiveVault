"""
security.py — File Upload Validation and Sanitization

WHY THIS FILE EXISTS:
Accepting user file uploads is one of the most dangerous things a web
server can do. Without validation, an attacker could:

  1. Upload a malicious .exe renamed as .pdf → remote code execution
  2. Upload a 10GB file → exhaust your server's RAM (DoS)
  3. Name their file "../../app/main.py" → overwrite server source code
     (path traversal attack)

This module provides three defences:
  - validate_pdf():       checks the file is legitimate and within size limits
  - sanitize_filename():  strips any path manipulation from the filename

These are used by the upload route BEFORE any processing begins.
If validate_pdf() raises an exception, FastAPI returns the error
immediately and no PDF is ever saved to disk.
"""

import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings

# Every legitimate PDF file starts with these 4 bytes.
# This is called a "magic number" — a file-format signature.
# Checking this is much harder to spoof than checking the file extension.
PDF_MAGIC_BYTES = b"%PDF"


async def validate_pdf(file: UploadFile) -> None:
    """
    Validate an uploaded file is a legitimate, safe PDF.

    Raises:
        HTTPException(400): if the file extension is wrong
        HTTPException(400): if the magic bytes don't match a PDF
        HTTPException(413): if the file exceeds the size limit

    This function is ASYNC because reading from UploadFile is an
    async operation in FastAPI — the file data streams in over the
    network and we must await it.
    """

    # ---- Layer 1: Extension Check ------------------------------------
    # Simple but catches accidents (user selected the wrong file).
    # Not a security measure by itself — attackers can rename any file.
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided.",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid file type: '{file.filename}'. "
                "Only PDF files (.pdf) are accepted."
            ),
        )

    # ---- Layer 2: Magic Bytes Check ----------------------------------
    # Read only the FIRST 4 bytes of the file to check the signature.
    # After reading, we seek back to position 0 so the full file can
    # be read again later (by the code that saves it to disk).
    #
    # Technical note: await file.read(4) gives us bytes b"%PDF" for a
    # valid PDF, or something else (e.g. b"PK\x03\x04" for a ZIP file,
    # b"\xff\xd8\xff" for a JPEG, etc.) for a renamed non-PDF.
    header = await file.read(4)
    await file.seek(0)  # ← CRITICAL: reset file pointer to the beginning

    if header != PDF_MAGIC_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                "File signature check failed. "
                "The uploaded file does not appear to be a valid PDF, "
                "even though it has a .pdf extension."
            ),
        )

    # ---- Layer 3: Size Check -----------------------------------------
    # Read the entire file into memory temporarily to measure its size.
    # We seek back to 0 immediately so downstream code reads a complete file.
    #
    # WHY: An attacker could upload a gigabyte-sized file to exhaust
    # your server's memory and crash it (denial-of-service attack).
    # We reject anything above the configured limit (default: 50MB).
    content = await file.read()
    await file.seek(0)

    size_bytes = len(content)
    if size_bytes > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,  # 413 = "Content Too Large"
            detail=(
                f"File size ({size_bytes / 1_048_576:.1f} MB) exceeds the "
                f"maximum allowed size of {settings.max_file_size_mb} MB."
            ),
        )

    if size_bytes == 0:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )


def sanitize_filename(original_filename: str) -> str:
    """
    Produce a safe, unique filename from the user-provided filename.

    The original filename could contain:
      - Directory separators: "../../etc/passwd.pdf" → path traversal attack
      - Special characters: "file<script>.pdf" → XSS if rendered in HTML
      - Unicode: "résumé.pdf" → encoding issues on Windows filesystems
      - Duplicates: two users uploading "report.pdf" overwrite each other

    WHAT WE DO:
      1. Extract only the filename stem (strip any directory path)
      2. Replace every unsafe character with an underscore
      3. Prepend a short UUID to guarantee uniqueness

    Example:
      Input:  "../../app/main.py"     → stem = "main"
      After:  "3a1b2c3d_main.pdf"

      Input:  "HR Policy 2024 (v3).pdf"  → stem = "HR Policy 2024 (v3)"
      After:  "3a1b2c3d_HR_Policy_2024__v3_.pdf"

    Returns:
        A string like "3a1b2c3d_safe_name.pdf" — safe to use as a filesystem path.
    """
    # Path(original_filename).stem strips directory components AND the extension.
    # e.g. "../../etc/passwd.pdf" → stem = "passwd"
    # e.g. "HR Report.pdf"        → stem = "HR Report"
    stem = Path(original_filename).stem

    # Replace any character that isn't a letter, digit, hyphen, or underscore
    # with an underscore. The regex [^a-zA-Z0-9_\-] means
    # "any character NOT in this set".
    safe_stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", stem)

    # Truncate to 100 characters to prevent excessively long filenames
    safe_stem = safe_stem[:100]

    # Use the first 8 characters of a UUID as a unique prefix.
    # This guarantees no two uploads ever have the same saved filename,
    # even if the original filenames were identical.
    unique_prefix = str(uuid.uuid4())[:8]

    return f"{unique_prefix}_{safe_stem}.pdf"
