<div align="center">

# ⎎ CognitiveVault

**Chat with your documents. Entirely on your machine.**

[![License: MIT](https://img.shields.io/badge/License-MIT-violet.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react&logoColor=white)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Llama 3](https://img.shields.io/badge/Llama_3-Local-orange.svg)](https://ollama.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-red.svg)](https://qdrant.tech)

> Upload a PDF, DOCX, PPTX or XLSX → ask questions in plain English → get accurate, cited answers.  
> No cloud. No API keys. Zero data leaves your device.

---

</div>

## ✨ Features

| | Feature | Detail |
|---|---|---|
| 🔒 | **100% Private** | Llama 3 via Ollama runs locally. Qdrant stores vectors locally. Nothing is sent anywhere. |
| 📄 | **Multi-format** | PDF · DOCX · PPTX · XLSX · Images — drag, drop, or paste |
| ⚡ | **Streaming answers** | Tokens stream in real-time as Llama 3 generates |
| 🔍 | **Source citations** | Every answer shows exactly which page it came from |
| 🧠 | **Think mode** | Toggle chain-of-thought reasoning for complex questions |
| 🎤 | **Voice input** | Web Speech API transcribes your question as you speak |
| ■ | **Stop generation** | Cancel a response mid-stream at any time |
| 🎨 | **Particle UI** | Three.js woven-light hero with mouse-reactive particles |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Browser (React + Vite)               │
│  Three.js canvas  ·  Chat UI  ·  PromptInputBox          │
└──────────────────────────┬───────────────────────────────┘
                           │ HTTP / SSE stream
┌──────────────────────────▼───────────────────────────────┐
│                  FastAPI Backend (Python)                 │
│                                                          │
│  POST /documents/upload   →   Ingestion pipeline         │
│    ├── PyPDF / LangChain loader                          │
│    ├── Text splitter (chunks + overlap)                  │
│    └── HuggingFace embeddings (all-MiniLM-L6-v2)        │
│                                                          │
│  POST /chat/stream        →   RAG pipeline               │
│    ├── Embed query                                       │
│    ├── Qdrant similarity search (top-k chunks)           │
│    └── Ollama Llama 3 → streamed response + sources      │
└──────────────┬──────────────────────┬────────────────────┘
               │                      │
   ┌───────────▼──────┐   ┌───────────▼──────────┐
   │  Qdrant (Docker) │   │  Ollama (local HTTP)  │
   │  Vector storage  │   │  Llama 3 / Mistral    │
   └──────────────────┘   └──────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.11+ | [python.org](https://python.org) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Docker | any | [docker.com](https://docker.com) |
| Ollama | any | [ollama.com](https://ollama.com) |

### 1 · Pull the LLM

```bash
ollama pull llama3
```

### 2 · Start Qdrant

```bash
docker compose up -d
```

> Qdrant dashboard → http://localhost:6333/dashboard

### 3 · Start the backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Copy env config (safe defaults, no secrets needed)
cp .env.example .env

# Start the API
uvicorn app.main:app --reload --port 8000
```

> API docs → http://localhost:8000/docs

### 4 · Start the frontend

```bash
cd frontend
npm install
npm run dev
```

> App → http://localhost:5173

---

## 🛠️ Tech Stack

### Backend
| Library | Role |
|---|---|
| **FastAPI** | REST API + Server-Sent Events streaming |
| **LangChain** | Document loading, text splitting, RAG orchestration |
| **Ollama** | Local inference — Llama 3 or Mistral |
| **Qdrant** | High-performance local vector database |
| **sentence-transformers** | Local embeddings via `all-MiniLM-L6-v2` (384-dim) |
| **PyPDF** | PDF text extraction |
| **Pydantic / Pydantic-Settings** | Config validation + request/response schemas |

### Frontend
| Library | Role |
|---|---|
| **React 18 + TypeScript** | UI framework with full type safety |
| **Vite** | Fast dev server and build tool |
| **Tailwind CSS** | Utility-first styling |
| **Three.js** | WebGL particle animation background |
| **Framer Motion** | Smooth UI transitions and animations |
| **Lucide React** | Clean icon system |

---

## 🔐 Security & Privacy

- **No telemetry.** No analytics. No external HTTP calls at runtime.
- **Uploaded files** live only in `backend/uploads/` — gitignored, never committed.
- **Vector embeddings** live only in `qdrant_storage/` — gitignored, never committed.
- **`.env`** is gitignored. Only `.env.example` (zero secrets) is in source control.
- All services bind to `localhost` — unreachable from the internet by default.

---

## 📁 Project Structure

```
CognitiveVault/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # chat.py · documents.py
│   │   ├── core/              # embeddings · ingestion · llm · vector_store
│   │   ├── models/            # Pydantic request / response schemas
│   │   ├── utils/             # file security helpers
│   │   ├── config.py          # centralised settings (Pydantic-Settings)
│   │   └── main.py            # FastAPI app + CORS + router registration
│   ├── uploads/               # runtime only — gitignored
│   ├── .env.example           # template — safe to commit
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/            # ai-prompt-box · woven-light-hero
│   │   │   ├── ChatWindow.tsx
│   │   │   └── MessageBubble.tsx
│   │   ├── services/api.ts    # typed streaming API client
│   │   ├── App.tsx            # landing ↔ chat layout
│   │   └── types.ts
│   └── package.json
│
├── qdrant_storage/            # runtime only — gitignored
├── docker-compose.yml         # Qdrant container definition
└── README.md
```

---

## 🤝 Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feat/my-feature`
3. Commit: `git commit -m 'feat: add my feature'`
4. Push and open a Pull Request

---

## 📄 License

MIT © [vamsikoneru06](https://github.com/vamsikoneru06)
