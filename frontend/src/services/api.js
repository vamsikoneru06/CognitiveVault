/**
 * api.js — All communication with the FastAPI backend
 *
 * Two functions are exported:
 *
 *  uploadDocument(file)
 *    POST multipart/form-data to /documents/upload
 *    Returns a Promise<DocumentUploadResponse>
 *
 *  streamQuery(question, documentId, topK, onToken, onSources, onDone, onError)
 *    POST JSON to /chat/stream
 *    Reads the response body as a stream.
 *    Calls onToken(str) for each text token from Llama 3.
 *    Calls onSources(array) once — the sources JSON emitted at stream end.
 *    Calls onDone() when the stream closes cleanly.
 *    Calls onError(message) on any failure.
 */

const API_BASE = 'http://localhost:8000/api/v1';

// ================================================================
// Upload
// ================================================================

/**
 * Upload a PDF file to be parsed, embedded, and stored.
 *
 * IMPORTANT: Do NOT set the Content-Type header manually when using
 * FormData. The browser sets it automatically with the correct
 * multipart boundary:
 *   Content-Type: multipart/form-data; boundary=----Abc123
 * If you set it yourself, the boundary is missing and FastAPI's
 * python-multipart parser will reject the upload.
 */
export async function uploadDocument(file) {
  const body = new FormData();
  body.append('file', file); // 'file' must match FastAPI's parameter name

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body,
    // No Content-Type header — browser adds it automatically
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Upload failed (${res.status})`);
  return data;
}

// ================================================================
// Streaming Query
// ================================================================

/**
 * Stream an AI answer, token by token.
 *
 * PROTOCOL (matches backend llm.py stream_answer):
 *   • Text tokens arrive as plain strings → forwarded to onToken()
 *   • The LAST chunk begins with \x1e (ASCII Record Separator, code 30)
 *     followed by a JSON array of source objects → forwarded to onSources()
 *   • After the sources chunk, onDone() is called.
 *
 * WHY CALLBACKS instead of async generator?
 *   The streaming update (onToken) happens synchronously inside a
 *   .then() chain. Using an async generator would require the caller
 *   to await the loop, which prevents React from batching state updates
 *   efficiently. Callbacks let React schedule updates freely.
 *
 * @param {string}        question     - The user's question
 * @param {string|null}   documentId   - Optional: restrict to one document
 * @param {number}        topK         - Chunks to retrieve (default 5)
 * @param {Function}      onToken      - Called with each text token string
 * @param {Function}      onSources    - Called once with the sources array
 * @param {Function}      onDone       - Called when the stream ends cleanly
 * @param {Function}      onError      - Called with an error message string
 */
export function streamQuery(
  question,
  documentId,
  topK,
  onToken,
  onSources,
  onDone,
  onError,
) {
  const SOURCES_SEP = '\x1e'; // ASCII Record Separator — our micro-protocol delimiter

  fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      document_id: documentId ?? null,
      top_k: topK ?? 5,
    }),
  })
    .then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Stream request failed' }));
        throw new Error(err.detail);
      }

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();

      // Recursive read function — reads one chunk at a time.
      const readChunk = async () => {
        const { done, value } = await reader.read();

        if (done) {
          // Stream ended without a sources separator (shouldn't happen
          // with our backend, but handle gracefully).
          onDone();
          return;
        }

        const text = decoder.decode(value);

        // Check if this chunk contains the sources delimiter \x1e
        const sepIdx = text.indexOf(SOURCES_SEP);

        if (sepIdx !== -1) {
          // Everything BEFORE the separator is a trailing text token
          const trailingText = text.substring(0, sepIdx);
          if (trailingText) onToken(trailingText);

          // Everything AFTER the separator is the JSON sources payload
          const sourcesJson = text.substring(sepIdx + 1);
          try {
            onSources(JSON.parse(sourcesJson));
          } catch {
            onSources([]); // Parsing failed — show no sources rather than crash
          }

          onDone();
          reader.releaseLock();
          return;
        }

        // Regular text token — forward to UI
        onToken(text);
        // Continue reading the next chunk
        return readChunk();
      };

      await readChunk();
    })
    .catch((err) => onError(err.message));
}
