# RAG Explorer

Visual walkthrough of a full RAG pipeline: PDF/TXT/MD/Excel → chunk → embed (Nomic) → ChromaDB → query → top-4 retrieval → Groq LLM answer.

![RAG Explorer UI](docs/ui-screenshot.png)

## Live

- **Frontend:** https://frontend-six-alpha-35.vercel.app (Vercel)
- **Backend:** https://rag-explorer-api.onrender.com (Render, free tier)

Both are real deploys, independent of any local machine — works whether or
not your laptop is on.

**Cold start caveat:** Render's free tier sleeps the backend after 15 min of
no traffic. The first request after that wakes it up (~30-50s), then it's
fast again until the next idle period. This is a free-tier behavior, not a
bug — upgrading to a paid Render plan removes it if it matters.

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

## Redeploying (already set up — quick path)

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

## How this was deployed from scratch

Steps taken to go from local-only to the two independent, always-on URLs
above. Useful if setting this up again on a new repo/account.

**1. Push the app to its own GitHub repo.**
This app lives at `RAG/Basic_Rag/app/` inside a much larger monorepo — Render
and Vercel both need a clean repo to point at, so `app/` was pushed to its
own dedicated repo (`git init` inside `app/`, new GitHub repo, push), rather
than exposing the whole monorepo.

**2. Get a Nomic API key.**
[atlas.nomic.ai](https://atlas.nomic.ai) → sign up → Settings → API Keys →
create a key. Free tier: 1M embedding tokens/month. This is what lets the
backend embed documents without running torch locally.

**3. Swap local embeddings for Nomic's hosted API.**
The original build used `sentence-transformers` + torch to run
`nomic-embed-text-v1.5` locally. That's the part that doesn't fit a free
host — see [Why hosted embeddings, not local](#why-hosted-embeddings-not-local)
below. Swapped `vector_store.py`'s embedding calls to `nomic.embed.text()`
(the `nomic` pip package, authenticated via `nomic.login(NOMIC_API_KEY)`),
same model name, same 768 dimensions. Removed `sentence-transformers`,
`torch`, and `einops` from `requirements.txt` entirely.

**4. Deploy the backend to Render.**
- [render.com](https://render.com) → New → Web Service → connect the GitHub
  repo from step 1.
- Render reads `backend/render.yaml` (already in the repo) for the build
  command (`pip install -r requirements.txt`), start command
  (`uvicorn main:app --host 0.0.0.0 --port $PORT`), and root directory
  (`backend/`).
- Set env vars in the Render dashboard: `GROQ_API_KEY`, `NOMIC_API_KEY`,
  `GROQ_MODEL` (`llama-3.3-70b-versatile`), `CORS_ORIGINS` (leave as `*`
  until step 6, then tighten it).
- Deploy. Note the resulting URL (`https://<service-name>.onrender.com`).

**5. Deploy the frontend to Vercel.**
```
cd frontend
vercel deploy --prod --yes
```
This creates a Vercel project from the `frontend/` folder (Vite build
auto-detected) and gives a `*.vercel.app` URL.

**6. Wire the frontend to the backend.**
```
vercel env add VITE_API_URL production
# paste the Render URL from step 4 when prompted
vercel deploy --prod --yes   # rebuild so the env var gets baked in
```
`frontend/src/api.js` reads `VITE_API_URL` at build time and prefixes all
`/api/*` calls with it — this is what makes the deployed frontend talk to
the deployed backend instead of `localhost`.

**7. Tighten CORS.**
Back in the Render dashboard, set `CORS_ORIGINS` to the real Vercel URL
from step 5 (comma-separated if allowing more than one origin, e.g. also
`http://localhost:5173` for local dev against the live backend). Redeploy
the backend (or it picks it up on the next natural deploy).

That's the whole path — no local machine, tunnel, or always-on process
required afterward.

### Leftover from earlier deploy attempts

- `backend/Dockerfile` + `.dockerignore` — written for a Hugging Face Spaces
  attempt (abandoned: Docker/Gradio Spaces require HF Pro, $9/mo, not
  actually free as initially assumed). Kept in case a Docker-based host is
  ever preferred over Render's native Python runtime.
- A Cloudflare Tunnel (`cloudflared`) was used as a stopgap demo before the
  Render+Nomic swap — exposed a local backend publicly but only while the
  local machine and tunnel process stayed running. No longer in use; the
  binary was gitignored (`backend/bin/`) and never committed.
