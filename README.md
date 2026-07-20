# RAG Explorer

Visual walkthrough of a full RAG pipeline: PDF/TXT/MD/Excel → chunk → embed (Nomic) → ChromaDB → query → top-4 retrieval → Groq LLM answer.

![RAG Explorer UI](docs/ui-screenshot.png)

## Live

- **Frontend:** https://frontend-six-alpha-35.vercel.app (Vercel)
- **Backend:** https://rag-explorer-api.onrender.com (Render, free tier)

Both are real, always-on deploys — independent of any local machine.

## Run locally

**Backend** (FastAPI, port 8000)
```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # then paste GROQ_API_KEY + NOMIC_API_KEY
uvicorn main:app --reload --port 8000
```

Drop any PDF/TXT/MD/Excel file into `backend/data/pdf/` — it auto-ingests (watchdog watches the folder; also ingests on startup). A sample PDF is already there.

**Frontend** (Vite dev server, port 5173)
```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. In dev, Vite proxies `/api` to `localhost:8000` — no env var needed locally.

## Notes

- Embedding model: `nomic-embed-text-v1.5` via [Nomic's hosted Atlas API](https://docs.nomic.ai/atlas/embeddings-and-retrieval/generate-embeddings) — not run locally. Needs a free `NOMIC_API_KEY` from [atlas.nomic.ai](https://atlas.nomic.ai) (free tier: 1M embedding tokens/month). 768 dimensions.
- Vector DB: ChromaDB, persisted to `backend/chroma_db/` (ephemeral on Render's free tier — resets on redeploy/restart; fine for a demo, not for permanent storage).
- LLM: Groq, `llama-3.3-70b-versatile` (real model — the original spec's "OpenGPT 1.2 120B" isn't an actual Groq model; swap `GROQ_MODEL` in `.env` if you want `openai/gpt-oss-120b` instead).
- Without a `GROQ_API_KEY`, retrieval still works — the answer panel shows a placeholder instead of a generated response.
- Ingestion supports PDF, TXT, Markdown, and Excel (`.xlsx`/`.xls`) — drop any of these into `backend/data/pdf/` and they auto-ingest. Manual upload button in the UI works the same way.

## Why hosted embeddings, not local

The backend originally ran embeddings locally via `sentence-transformers` +
torch. That doesn't fit free-tier host RAM (512MB) — confirmed by testing:
the process crash-looped every ~7 minutes on Render's free plan, killed
mid-download of the model weights, before ever finishing startup. Every free
static/serverless host (Vercel, Netlify, Cloudflare Pages/Functions) has the
same wall for a different reason (deploy size caps, no persistent disk, no
long-lived process for the folder watcher).

Swapped to Nomic's hosted embedding API instead — same model
(`nomic-embed-text-v1.5`), same 768 dimensions, but the backend no longer
imports torch at all. That's what made a real free-tier deploy possible.

## Redeploying

**Backend (Render):** push to `main` — Render auto-deploys via the connected
GitHub repo (`backend/render.yaml` defines the build/start commands and env
vars). `GROQ_API_KEY`, `NOMIC_API_KEY`, and `CORS_ORIGINS` are set directly
in the Render dashboard (not committed).

**Frontend (Vercel):**
```
cd frontend
vercel deploy --prod --yes
```
`VITE_API_URL` is set as a Vercel project env var (Settings → Environment
Variables) and gets baked into the build — changing it requires a redeploy
to take effect.

### Leftover from earlier deploy attempts

- `backend/Dockerfile` + `.dockerignore` — written for a Hugging Face Spaces
  attempt (abandoned: Docker/Gradio Spaces require HF Pro, $9/mo, not
  actually free as initially assumed). Kept in case a Docker-based host is
  ever preferred over Render's native Python runtime.
