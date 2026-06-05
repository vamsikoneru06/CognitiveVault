import { useCallback, useRef, useState } from 'react';
import ChatWindow from './components/ChatWindow';
import { OwnerCard } from './components/ui/owner-card';
import { PromptInputBox } from './components/ui/ai-prompt-box';
import { WovenCanvas } from './components/ui/woven-light-hero';
import { streamQuery, uploadDocument } from './services/api';
import type { Message } from './types';

let _counter = 0;
const newId = () => `msg_${++_counter}_${Date.now()}`;

export default function App() {
  const [messages,   setMessages]   = useState<Message[]>([]);
  const [isQuerying, setIsQuerying] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsQuerying(false);
    setMessages(prev => prev.map(m =>
      (m.isStreaming || m.isLoading)
        ? { ...m, isStreaming: false, isLoading: false }
        : m,
    ));
  }, []);

  const handleSend = useCallback(async (message: string, files?: File[]) => {
    const question = message.trim();
    if (!question || isQuerying) return;

    // If a file is attached, upload it first and get its document_id
    let docId: string | null = null;
    if (files && files.length > 0) {
      const uploadMsgId = newId();
      setMessages(prev => [...prev, {
        id: uploadMsgId, role: 'assistant' as const,
        content: '', isLoading: true, isStreaming: false, sources: [],
      }]);
      try {
        const uploaded = await uploadDocument(files[0]);
        docId = uploaded.document_id;
        setMessages(prev => prev.filter(m => m.id !== uploadMsgId));
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Upload failed';
        setMessages(prev => prev.map(m =>
          m.id === uploadMsgId
            ? { ...m, content: `⚠ ${msg}`, isLoading: false, isError: true }
            : m,
        ));
        return;
      }
    }

    abortRef.current = new AbortController();
    setIsQuerying(true);
    const userMsgId = newId();
    const aiMsgId   = newId();

    setMessages(prev => [
      ...prev,
      { id: userMsgId, role: 'user', content: question },
      { id: aiMsgId, role: 'assistant', content: '', isLoading: true, isStreaming: false, sources: [] },
    ]);

    streamQuery(
      question,
      docId,
      5,
      (token) => {
        setMessages(prev => prev.map(m =>
          m.id === aiMsgId
            ? { ...m, content: m.content + token, isLoading: false, isStreaming: true }
            : m,
        ));
      },
      (sources) => {
        setMessages(prev => prev.map(m =>
          m.id === aiMsgId ? { ...m, sources } : m,
        ));
      },
      () => {
        setMessages(prev => prev.map(m =>
          m.id === aiMsgId ? { ...m, isStreaming: false, isLoading: false } : m,
        ));
        setIsQuerying(false);
      },
      (errMsg) => {
        setMessages(prev => prev.map(m =>
          m.id === aiMsgId
            ? { ...m, content: `⚠ ${errMsg}`, isLoading: false, isStreaming: false, isError: true }
            : m,
        ));
        setIsQuerying(false);
      },
      abortRef.current.signal,
    );
  }, [isQuerying]);

  const isEmpty = messages.length === 0;

  return (
    <div className="relative flex flex-col h-screen w-full overflow-hidden bg-white">
      {/* ── Particle background ── */}
      <WovenCanvas />

      {/* ── Persistent top-left title ── */}
      <header className="absolute top-0 left-0 z-20 px-8 pt-6">
        <h1
          className="text-[21px] font-semibold tracking-tight text-slate-900 select-none"
          style={{ fontFamily: "'Playfair Display', serif", letterSpacing: '-0.01em' }}
        >
          CognitiveVault
        </h1>
        <p
          className="text-[11px] text-slate-400 mt-[1px]"
          style={{ fontFamily: "'Inter', sans-serif", letterSpacing: '0.02em' }}
        >
          Local AI · private by default
        </p>
      </header>

      {/* ── Content area (below the header) ── */}
      <div className="relative z-10 flex flex-col flex-1 overflow-hidden pt-[72px]">
        {isEmpty ? (
          /* ── Landing: headline + input centred ── */
          <div className="flex flex-col flex-1 items-center justify-center px-6 pb-10">
            <div className="w-full max-w-[560px] flex flex-col items-center">

              <h2
                className="text-[38px] font-semibold text-slate-900 text-center leading-[1.2] mb-3"
                style={{ fontFamily: "'Playfair Display', serif" }}
              >
                Your documents,<br />answered instantly.
              </h2>

              <p
                className="text-[13.5px] text-slate-400 text-center mb-8 max-w-[280px] leading-relaxed"
                style={{ fontFamily: "'Inter', sans-serif" }}
              >
                Llama 3 runs entirely on your machine —
                zero data ever leaves your device.
              </p>

              <div className="w-full">
                <PromptInputBox
                  onSend={handleSend}
                  onStop={handleStop}
                  isLoading={isQuerying}
                  placeholder="Attach a document and ask anything…"
                />
              </div>

              {/* Suggestion chips */}
              <div className="flex flex-wrap justify-center gap-2 mt-5">
                {[
                  'Summarise this document',
                  'What are the key findings?',
                  'List the main action items',
                  'Explain the conclusions',
                ].map(q => (
                  <button
                    key={q}
                    onClick={() => handleSend(q)}
                    className="px-3 py-1.5 rounded-full text-[12px] text-slate-500
                               border border-slate-200 bg-white/60 backdrop-blur-sm
                               hover:border-violet-300 hover:text-violet-600 hover:bg-violet-50
                               transition-all duration-150"
                    style={{ fontFamily: "'Inter', sans-serif" }}
                  >
                    {q}
                  </button>
                ))}
              </div>

            </div>
          </div>
        ) : (
          /* ── Chat: messages + bottom input ── */
          <div className="flex flex-col flex-1 items-center overflow-hidden">
            <div className="w-full max-w-2xl px-6 flex-shrink-0">
              <div className="h-px bg-slate-100" />
            </div>

            <main className="flex flex-col flex-1 w-full max-w-2xl overflow-hidden">
              <div className="flex-1 overflow-hidden backdrop-blur-[2px]">
                <ChatWindow messages={messages} />
              </div>

              <div className="flex-shrink-0 px-4 pb-5 pt-2">
                <PromptInputBox
                  onSend={handleSend}
                  onStop={handleStop}
                  isLoading={isQuerying}
                  placeholder={isQuerying ? 'Generating response…' : 'Ask anything…'}
                />
              </div>
            </main>
          </div>
        )}
      </div>

      {/* ── Owner attribution card ── */}
      <OwnerCard />
    </div>
  );
}
