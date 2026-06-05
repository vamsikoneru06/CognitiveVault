import { Github, Linkedin } from 'lucide-react';

export function OwnerCard() {
  return (
    <div
      className="fixed bottom-4 left-4 z-30 flex items-center gap-3 px-3.5 py-2.5
                 rounded-xl border border-slate-200 bg-white/80 backdrop-blur-sm shadow-sm
                 select-none"
      style={{ fontFamily: "'Inter', sans-serif" }}
    >
      {/* Avatar */}
      <div
        className="h-7 w-7 rounded-full bg-slate-900 flex items-center justify-center
                   text-white text-[11px] font-semibold shrink-0"
      >
        VK
      </div>

      {/* Name + title */}
      <div className="flex flex-col leading-none gap-0.5">
        <span className="text-[12px] font-semibold text-slate-800 whitespace-nowrap">
          Vamsi Koneru
        </span>
        <span className="text-[10px] text-slate-400 whitespace-nowrap">
          Built by the owner
        </span>
      </div>

      {/* Divider */}
      <div className="h-6 w-px bg-slate-200" />

      {/* Links */}
      <div className="flex items-center gap-1.5">
        <a
          href="https://github.com/vamsikoneru06"
          target="_blank"
          rel="noopener noreferrer"
          className="p-1 rounded-md text-slate-500 hover:text-slate-900
                     hover:bg-slate-100 transition-colors duration-150"
          title="GitHub"
        >
          <Github size={14} strokeWidth={1.8} />
        </a>
        <a
          href="https://www.linkedin.com/in/vamsi-koneru-0a0661330/"
          target="_blank"
          rel="noopener noreferrer"
          className="p-1 rounded-md text-slate-500 hover:text-[#0A66C2]
                     hover:bg-blue-50 transition-colors duration-150"
          title="LinkedIn"
        >
          <Linkedin size={14} strokeWidth={1.8} />
        </a>
      </div>
    </div>
  );
}
