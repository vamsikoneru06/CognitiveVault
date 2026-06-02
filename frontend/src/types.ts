// =================================================================
// Shared TypeScript types used across the application
// =================================================================

export interface SourceItem {
  page: number;
  source_filename: string;
  score: number;
  preview: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isLoading?: boolean;
  isStreaming?: boolean;
  isError?: boolean;
  sources?: SourceItem[];
}

export interface UploadedDoc {
  document_id: string;
  filename: string;
  total_pages: number;
  total_chunks: number;
  chunk_size: number;
  chunk_overlap: number;
  vectors_stored: number;
  embedding_model: string;
  message: string;
  uploaded_at: string;
}
