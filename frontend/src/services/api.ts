/**
 * api.ts — Typed communication layer with the FastAPI backend
 */

import type { SourceItem, UploadedDoc } from '../types';

const API_BASE = 'http://localhost:8000/api/v1';

// =================================================================
// Upload
// =================================================================

export async function uploadDocument(file: File): Promise<UploadedDoc> {
  const body = new FormData();
  body.append('file', file);

  const res = await fetch(`${API_BASE}/documents/upload`, { method: 'POST', body });
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

      const reader  = res.body!.getReader();
      const decoder = new TextDecoder();

      const read = async (): Promise<void> => {
        const { done, value } = await reader.read();
        if (done) { onDone(); return; }

        const text   = decoder.decode(value);
        const sepIdx = text.indexOf(SEP);

        if (sepIdx !== -1) {
          if (sepIdx > 0) onToken(text.substring(0, sepIdx));
          try { onSources(JSON.parse(text.substring(sepIdx + 1)) as SourceItem[]); }
          catch { onSources([]); }
          onDone();
          reader.releaseLock();
          return;
        }

        onToken(text);
        return read();
      };

      await read();
    })
    .catch((err: Error) => {
      if (err.name === 'AbortError') return;
      onError(err.message);
    });
}
