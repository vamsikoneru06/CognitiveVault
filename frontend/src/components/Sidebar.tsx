import { useRef, useState } from 'react';
import type { UploadedDoc } from '../types';

interface Props {
  uploadedDoc:  UploadedDoc | null;
  onUpload:     (file: File) => void;
  isUploading:  boolean;
  uploadError:  string | null;
}

export default function Sidebar({ uploadedDoc, onUpload, isUploading, uploadError }: Props) {
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File | undefined | null) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Please select a PDF file.');
      return;
    }
    onUpload(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };

  return (
    <aside className="w-[272px] flex-shrink-0 flex flex-col bg-[#111120] border-r border-white/[0.06] overflow-hidden">
      {/* ── Logo ── */}
      <div className="px-5 py-[18px] border-b border-white/[0.06] flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#7c5cfc] flex items-center justify-center text-base flex-shrink-0">
            🔒
          </div>
          <span className="text-[15px] font-semibold tracking-tight text-white">CognitiveVault</span>
        </div>
      </div>

      <div className="flex-1 p-4 overflow-y-auto flex flex-col gap-3">
        <p className="text-[10px] font-bold tracking-[0.1em] uppercase text-white/25 mt-1 px-1">
          Document
        </p>

        {/* ── Uploading spinner ── */}
        {isUploading && (
          <div className="flex items-center gap-3 px-4 py-3.5 bg-[#7c5cfc]/10 rounded-2xl border border-[#7c5cfc]/25">
            <div className="w-4 h-4 rounded-full border-2 border-[#7c5cfc]/20 border-t-[#7c5cfc] animate-spin flex-shrink-0" />
            <div>
              <p className="text-sm text-[#a78bfa] font-medium">Indexing…</p>
              <p className="text-[11px] text-white/25 mt-0.5">chunk → embed → store</p>
            </div>
          </div>
        )}

        {/* ── Document card ── */}
        {!isUploading && uploadedDoc && (
          <div className="rounded-2xl border border-[#444444] bg-[#1F2023] p-4 shadow-[0_8px_30px_rgba(0,0,0,0.24)]">
            {/* File icon + name */}
            <div className="flex gap-3 mb-3">
              <span className="text-xl flex-shrink-0 mt-0.5">📄</span>
              <p className="text-[13px] font-medium text-white leading-[1.4] break-all">
                {uploadedDoc.filename}
              </p>
            </div>

            {/* Stats grid */}
            <div className="grid grid-cols-2 gap-1.5 mb-3">
              {[
                { v: uploadedDoc.total_pages,    l: 'Pages'   },
                { v: uploadedDoc.total_chunks,   l: 'Chunks'  },
                { v: uploadedDoc.vectors_stored, l: 'Vectors' },
                { v: 384,                        l: 'Dims'    },
              ].map(({ v, l }) => (
                <div key={l} className="bg-[#191926] rounded-lg px-3 py-2">
                  <div className="text-[18px] font-bold text-white leading-none">{v}</div>
                  <div className="text-[10px] text-white/25 uppercase tracking-wider mt-1">{l}</div>
                </div>
              ))}
            </div>

            {/* Ready badge */}
            <div className="inline-flex items-center gap-1.5 text-[11px] text-emerald-400 bg-emerald-400/10 rounded-full px-3 py-1 mb-3">
              ✓ Ready for queries
            </div>

            {/* Replace button */}
            <button
              onClick={() => fileRef.current?.click()}
              className="w-full py-2 text-xs text-white/30 border border-white/[0.08] rounded-xl
                         hover:border-[#7c5cfc]/60 hover:text-[#a78bfa] hover:bg-[#7c5cfc]/10
                         transition-all duration-200"
            >
              Replace document
            </button>

            <input
              type="file" accept=".pdf" className="hidden" ref={fileRef}
              onChange={e => handleFile(e.target.files?.[0])}
            />
          </div>
        )}

        {/* ── Upload drop zone ── */}
        {!isUploading && !uploadedDoc && (
          <div
            className={`border-[1.5px] border-dashed rounded-2xl p-8 text-center cursor-pointer
                        transition-all duration-200 select-none
                        ${dragging
                          ? 'border-[#7c5cfc] bg-[#7c5cfc]/10'
                          : 'border-white/[0.08] bg-[#191926] hover:border-[#7c5cfc]/60 hover:bg-[#7c5cfc]/8'
                        }`}
            onClick={() => fileRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
          >
            <div className="text-3xl mb-3 opacity-60">📤</div>
            <p className="text-sm text-white/40 leading-relaxed">
              Drop your PDF here<br />or click to browse
            </p>
            <p className="text-[11px] text-white/20 mt-2">PDF only · max 50 MB</p>

            <input
              type="file" accept=".pdf" className="hidden" ref={fileRef}
              onChange={e => handleFile(e.target.files?.[0])}
            />
          </div>
        )}

        {/* ── Upload error ── */}
        {uploadError && (
          <div className="px-3 py-2.5 bg-red-500/8 border border-red-500/20 rounded-xl
                          text-[12px] text-red-400 leading-relaxed">
            ⚠ {uploadError}
          </div>
        )}
      </div>
    </aside>
  );
}
