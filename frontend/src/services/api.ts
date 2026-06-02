/**
 * api.ts — Typed communication layer with the FastAPI backend
 */

import type { SourceItem, UploadedDoc } from '../types';

const API_BASE = (import.meta as any).env?.VITE_API_BASE ?? 'http://localhost:8000/api/v1';

// =================================================================
// Upload
// =================================================================

export async function uploadDocument(file: File): Promise<UploadedDoc> {
  const body = new FormData();
  body.append('file', file);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}/documents/upload`, { method: 'POST', body });
  } catch (e) {
    throw new Error('Cannot reach the backend. Is it running?');
  }

  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? `Upload failed (${res.status})`);
  return data as UploadedDoc;
}

// =================================================================
// Streaming Query
// =================================================================

export function streamQuery(
  question:   string,
  documentId: string | null,
  topK:       number,
  onToken:    (token: string) => void,
  onSources:  (sources: SourceItem[]) => void,
  onDone:     () => void,
  onError:    (msg: string) => void,
  signal?:    AbortSignal,
): void {
  const SEP = '\x1e';
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;

  fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, document_id: documentId ?? null, top_k: topK }),
    signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Stream request failed' }));
        throw new Error(err.detail as string);
      }

      if (!res.body) {
        onError('Empty response body');
        return;
      }

      reader = res.body.getReader();
      const decoder = new TextDecoder();

      // Accumulate across chunks so the SEP delimiter is never missed
      // at a chunk boundary.
      let buf = '';

      const read = async (): Promise<void> => {
        const { done, value } = await reader!.read();

        if (done) {
          if (buf) onToken(buf);
          onDone();
          return;
        }

        buf += decoder.decode(value, { stream: true });
        const sepIdx = buf.indexOf(SEP);

        if (sepIdx !== -1) {
          if (sepIdx > 0) onToken(buf.substring(0, sepIdx));
          const jsonStr = buf.substring(sepIdx + 1);
          try { onSources(JSON.parse(jsonStr) as SourceItem[]); }
          catch { onSources([]); }
          onDone();
          reader!.cancel();
          return;
        }

        // Flush all but the last character — guards against a lone \x1e
        // arriving as the last byte of a chunk with JSON in the next chunk.
        if (buf.length > 1) {
          onToken(buf.slice(0, -1));
          buf = buf.slice(-1);
        }
        return read();
      };

      await read();
    })
    .catch((err: Error) => {
      if (err.name === 'AbortError') { reader?.cancel(); return; }
      onError(err.message);
    });
}
