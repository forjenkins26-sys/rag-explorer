# RAG Explorer

Visual walkthrough of a full RAG pipeline: PDF → chunk → embed (Nomic) → ChromaDB → query → top-4 retrieval → Groq LLM answer.

![RAG Explorer UI](docs/ui-screenshot.png)

## Run

**Backend** (FastAPI, port 8000)
```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # then paste your GROQ_API_KEY
uvicorn main:app --reload --port 8000
```

Drop any PDF into `backend/data/pdf/` — it auto-ingests (watchdog watches the folder; also ingests on startup). A sample PDF is already there.

**Frontend** (Vite dev server, port 5173)
```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Notes

- Embedding model: `nomic-ai/nomic-embed-text-v1.5` via `sentence-transformers`, runs fully local — no Nomic API key needed. First run downloads the model (~500MB).
- Vector DB: ChromaDB, persisted to `backend/chroma_db/`.
- LLM: Groq, `llama-3.3-70b-versatile` (real model — spec's "OpenGPT 1.2 120B" isn't a Groq model; swap `GROQ_MODEL` in `.env` if you want `openai/gpt-oss-120b` instead).
- Without a `GROQ_API_KEY`, retrieval still works — the answer panel shows a placeholder instead of a generated response.
