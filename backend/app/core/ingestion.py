"""
ingestion.py — The PDF Parsing and Chunking Engine

This is the first step of the RAG pipeline. It takes a saved PDF file
and returns a list of text chunks, each packaged as a LangChain Document.

A LangChain Document is a simple object with two attributes:
  - .page_content  → the actual text string
  - .metadata      → a dict of extra information (page number, filename, etc.)

The metadata is crucial: when we later retrieve a chunk from Qdrant,
we use the metadata to tell the user WHICH PAGE of WHICH DOCUMENT
the answer came from. This is what makes the system trustworthy.

PIPELINE:
  PDF file on disk
      ↓
  PyPDFLoader       → reads each page → list of Document (one per page)
      ↓
  Add metadata      → document_id, filename, etc.
      ↓
  RecursiveCharacterTextSplitter → slices pages into overlapping chunks
      ↓
  Return list of chunk Documents (ready to be embedded in Phase 3)
"""

from pathlib import Path
from typing import List, Tuple

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ------------------------------------------------------------------ #
#  Chunking Constants                                                  #
# ------------------------------------------------------------------ #
# These are the two most important tuning parameters in your RAG system.
# See the Phase 2 tutorial for the full math behind these numbers.

CHUNK_SIZE = 1000
# Character limit per chunk.
# ≈ 200 words ≈ 1–2 paragraphs.
# Top-5 chunks × 1000 chars = 5000 chars of context for the LLM.

CHUNK_OVERLAP = 200
# Characters shared between consecutive chunks.
# = 20% of CHUNK_SIZE — the standard rule of thumb.
# Prevents key sentences from being split across chunk boundaries.

# Separators tried in ORDER. The splitter always prefers the highest-level
# boundary it can find that still produces a chunk small enough.
SEPARATORS = [
    "\n\n",  # Paragraph break — semantically the cleanest cut point
    "\n",    # Line break — preserves sentence integrity
    " ",     # Word boundary — never cuts a word in half
    "",      # Character — last resort, almost never triggered at chunk_size=1000
]


def load_and_chunk_pdf(
    file_path: Path,
    document_id: str,
    original_filename: str,
) -> Tuple[List[Document], int]:
    """
    Parse a PDF and split it into overlapping text chunks.

    Args:
        file_path:         Absolute path to the PDF saved on disk.
        document_id:       UUID string for this document (from the route layer).
        original_filename: The user's original filename (for metadata display).

    Returns:
        A tuple:
          [0] List of Document objects — the chunks, ready to be embedded.
          [1] int — total number of pages in the PDF.

    Raises:
        ValueError: if the PDF is empty or contains no extractable text.
        Exception:  if pypdf fails to read the file (corrupted PDF).
    """

    # ==================================================================
    # STEP 1: Load the PDF
    # ==================================================================
    # PyPDFLoader opens the PDF and reads it page by page.
    # Each page becomes one Document object.
    #
    # A 10-page PDF → loader.load() returns a list of 10 Documents.
    # A 100-page PDF → 100 Documents.
    #
    # Important limitation: PyPDFLoader extracts DIGITAL text only.
    # If a PDF is a scanned image (a photo of a document), pypdf
    # extracts nothing — the page_content will be empty. Handling
    # scanned PDFs requires OCR (Optical Character Recognition) which
    # we'll add as a future enhancement.
    loader = PyPDFLoader(str(file_path))

    # loader.load() can raise various exceptions if the PDF is corrupted
    # or password-protected. We let these bubble up to the route handler
    # which will catch them and return an appropriate HTTP error.
    pages: List[Document] = loader.load()
    total_pages = len(pages)

    if total_pages == 0:
        raise ValueError(
            f"Could not read any pages from '{original_filename}'. "
            "The file may be empty or corrupted."
        )

    # ==================================================================
    # STEP 2: Enrich Page Metadata
    # ==================================================================
    # After loading, each Document.metadata looks like:
    #   {"source": "/path/to/file.pdf", "page": 0}
    #
    # We add our own fields so that when we retrieve a chunk from Qdrant
    # later, we know exactly which document and page it came from.
    for page_doc in pages:
        page_doc.metadata["document_id"] = document_id
        page_doc.metadata["source_filename"] = original_filename
        # Note: pypdf uses 0-based page numbers. Page 1 of the PDF = index 0.
        # We keep it 0-based throughout for consistency.

    # ==================================================================
    # STEP 3: Create the Text Splitter
    # ==================================================================
    splitter = RecursiveCharacterTextSplitter(
        # ── chunk_size ───────────────────────────────────────────────
        # Maximum number of characters in any single chunk.
        # The splitter will NEVER produce a chunk larger than this.
        chunk_size=CHUNK_SIZE,

        # ── chunk_overlap ─────────────────────────────────────────────
        # How many characters from the END of chunk N are copied to
        # the BEGINNING of chunk N+1.
        #
        # Without this:
        #   Chunk 3 ends with: "...approval required for all expenses above"
        #   Chunk 4 starts with: "$500. Submit within 14 days..."
        #   ← Neither chunk is complete. Both are hard to retrieve.
        #
        # With overlap=200:
        #   Chunk 3 ends with: "...approval required for all expenses above"
        #   Chunk 4 starts with: "expenses above $500. Submit within 14 days..."
        #   ← Chunk 4 now contains the full key fact.
        chunk_overlap=CHUNK_OVERLAP,

        # ── length_function ───────────────────────────────────────────
        # Tells the splitter how to measure "size".
        # len() counts characters. This is fast and consistent.
        # Alternative: count tokens (more accurate for LLM limits, but
        # requires loading a tokenizer — slower, adds complexity).
        length_function=len,

        # ── separators ────────────────────────────────────────────────
        # The hierarchy of split points (see constant defined above).
        separators=SEPARATORS,

        # ── add_start_index ───────────────────────────────────────────
        # Adds metadata["start_index"] = char position in original page text.
        # Useful for Phase 5: highlighting the source text in the frontend.
        add_start_index=True,
    )

    # ==================================================================
    # STEP 4: Split Pages Into Chunks
    # ==================================================================
    # split_documents() takes our list of page Documents and returns a
    # new, LONGER list of chunk Documents.
    #
    # Example: 10 pages, each ~3000 chars → ~3 chunks per page → ~30 chunks
    # Example: 100 pages, each ~2000 chars → ~2 chunks per page → ~200 chunks
    #
    # Each chunk's .metadata inherits ALL of its parent page's metadata,
    # plus the new "start_index" key added by add_start_index=True.
    chunks: List[Document] = splitter.split_documents(pages)

    # ==================================================================
    # STEP 5: Filter Out Empty Chunks
    # ==================================================================
    # Some PDF pages are:
    #   - Cover pages with only images
    #   - Table of contents pages with just numbers
    #   - Blank separator pages
    #
    # PyPDFLoader returns empty strings for these. We filter them out.
    # An empty chunk would produce a useless embedding and waste space in Qdrant.
    chunks = [
        chunk for chunk in chunks
        if chunk.page_content.strip()  # .strip() removes leading/trailing whitespace
    ]

    if not chunks:
        raise ValueError(
            f"No extractable text was found in '{original_filename}'. "
            "The PDF may contain only images (scanned document). "
            "OCR support is planned for a future phase."
        )

    return chunks, total_pages
