import { useState, useCallback } from 'react';
import { User, Sparkles, ChevronRight, ChevronDown, FileText, Copy, Check } from 'lucide-react';
import type { Message } from '../types';

interface Props { message: Message }

function renderContent(text: string): React.ReactNode {
  const normalized = text.replace(/ \* /g, '\n* ');
  const lines = normalized.split('\n');
  const result: React.ReactNode[] = [];
  let listBuffer: string[] = [];
  let key = 0;

  const flushList = () => {
    if (listBuffer.length === 0) return;
    result.push(
      <ul key={key++} className="mt-3 space-y-2">
        {listBuffer.map((item, i) => (
          <li key={i} className="flex items-start gap-2.5 text-slate-700">
            <span className="mt-[9px] h-1.5 w-1.5 rounded-full bg-violet-400 shrink-0" />
            <span className="leading-[1.72]">{item}</span>
          </li>
        ))}
      </ul>
    );
    listBuffer = [];
  };

  lines.forEach(line => {
    const match = line.match(/^\*\s+(.+)/);
    if (match) {
      listBuffer.push(match[1].trim());
    } else {
      flushList();
      const trimmed = line.trim();
      if (trimmed) {
        result.push(
          <p key={key++} className={`leading-[1.78] text-slate-700 ${result.length > 0 ? 'mt-3' : ''}`}>
            {trimmed}
          </p>
        );
      }
    }
  });
  flushList();

  return <>{result}</>;
}

export default function MessageBubble({ message }: Props) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [copied, setCopied]           = useState(false);
  const { role, content, isLoading, isStreaming, isError, sources = [] } = message;

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  }, [content]);

  /* ── User message ── */
  if (role === 'user') {
    return (
      <div className="flex items-end justify-end gap-2.5 group">
        <div
          className="max-w-[72%] px-4 py-3 rounded-2xl rounded-br-sm
                     bg-slate-900 text-white text-[14px] leading-[1.72]
                     whitespace-pre-wrap break-words select-text"
          style={{ fontFamily: "'Inter', sans-serif" }}
        >
          {content}
        </div>
        <div className="w-7 h-7 rounded-full bg-slate-100 border border-slate-200
                        flex items-center justify-center shrink-0 mb-0.5">
          <User className="h-3.5 w-3.5 text-slate-500" strokeWidth={1.75} />
        </div>
      </div>
    );
  }

  /* ── Assistant message ── */
  return (
    <div className="flex items-start gap-3 group">

      {/* Avatar */}
      <div className="w-7 h-7 rounded-full bg-violet-50 border border-violet-100
                      flex items-center justify-center shrink-0 mt-0.5">
        <Sparkles className="h-3.5 w-3.5 text-violet-400" strokeWidth={1.75} />
      </div>

      <div className="flex-1 min-w-0" style={{ fontFamily: "'Inter', sans-serif" }}>

        {/* Content */}
        {isLoading ? (
          <div className="flex items-center gap-1.5 py-2">
            {[0, 1, 2].map(i => (
              <div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-dot-bounce"
                style={{ animationDelay: `${i * 0.18}s` }}
              />
            ))}
          </div>
        ) : (
          <div
            className={[
              'text-[14px] select-text',
              isError ? 'text-red-500' : '',
              isStreaming ? 'streaming-cursor' : '',
            ].filter(Boolean).join(' ')}
          >
            {renderContent(content)}
          </div>
        )}

        {/* Actions row — copy button, sources toggle */}
        {!isLoading && content && (
          <div className="flex items-center gap-3 mt-3">
            {/* Copy */}
            {!isError && (
              <button
                onClick={handleCopy}
                className="inline-flex items-center gap-1.5 text-[11px] text-slate-400
                           hover:text-slate-600 transition-colors duration-150"
              >
                {copied
                  ? <><Check className="h-3.5 w-3.5 text-emerald-500" strokeWidth={2} /><span className="text-emerald-500">Copied</span></>
                  : <><Copy className="h-3.5 w-3.5" strokeWidth={1.75} /><span>Copy</span></>
                }
              </button>
            )}

            {/* Sources */}
            {!isStreaming && sources.length > 0 && (
              <button
                onClick={() => setSourcesOpen(o => !o)}
                className="inline-flex items-center gap-1 text-[11px] font-medium
                           text-slate-400 hover:text-slate-600 transition-colors duration-150"
              >
                {sourcesOpen
                  ? <ChevronDown className="h-3.5 w-3.5" strokeWidth={2} />
                  : <ChevronRight className="h-3.5 w-3.5" strokeWidth={2} />
                }
                {sources.length} source{sources.length !== 1 ? 's' : ''}
              </button>
            )}
          </div>
        )}

        {/* Sources panel */}
        {sourcesOpen && sources.length > 0 && (
          <div className="mt-2.5 flex flex-col gap-2">
            {sources.map((src, i) => (
              <div key={i} className="flex gap-3 bg-white/70 border border-slate-100
                                      rounded-xl px-3.5 py-3 shadow-sm backdrop-blur-sm">
                <FileText className="h-4 w-4 text-slate-300 shrink-0 mt-0.5" strokeWidth={1.5} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1.5 gap-2">
                    <span className="text-[11px] font-semibold text-violet-500 truncate">
                      {src.source_filename} &middot; p.{src.page}
                    </span>
                    <span className="text-[10px] text-emerald-600 bg-emerald-50
                                     px-2 py-0.5 rounded-full shrink-0 font-medium">
                      {(src.score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-[12px] text-slate-400 leading-relaxed italic">
                    &ldquo;{src.preview}&hellip;&rdquo;
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}
