import asyncio
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import vector_store
from config import CORS_ORIGINS, GROQ_MODEL, PDF_DIR, TOP_K
from extractors import SUPPORTED_EXTENSIONS
from ingest import ingest_all, ingest_pdf, sync_deleted
from llm import generate_answer
from watcher import start_watcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ingestion loads the embedding model (first-run download can take
    # several minutes on a cold host). Run it in the background so uvicorn
    # binds the port immediately — hosts like Render kill the deploy if no
    # port opens within their scan timeout.
    asyncio.create_task(asyncio.to_thread(_startup_ingest))
    yield


def _startup_ingest():
    ingest_all()
    global _watcher_observer
    _watcher_observer = start_watcher()


_watcher_observer = None


app = FastAPI(title="RAG Explorer API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str
    top_k: int = TOP_K


@app.get("/api/status")
def status():
    sync_deleted()
    s = vector_store.stats()
    return {
        "embedding_model": "nomic-embed-text-v1.5",
        "llm_model": GROQ_MODEL,
        "vector_db": "ChromaDB (local, persistent)",
        "pdf_folder": str(PDF_DIR),
        "total_chunks": s["total_chunks"],
        "embedding_dims": vector_store.embedding_dims(),
        "sample_embedding": vector_store.sample_embedding(),
        "sources": s["sources"],
    }


@app.get("/api/chunks")
def chunks():
    return {"chunks": vector_store.list_chunks()}


@app.post("/api/reingest")
def reingest():
    return {"ingested": ingest_all()}


@app.post("/api/upload")
async def upload(file: UploadFile):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # Filename is used only as a display label; the file is always written
    # under a fixed, sanitized name inside PDF_DIR — no path traversal risk.
    safe_name = "".join(c for c in file.filename if c.isalnum() or c in " ._-()") or f"upload{ext}"
    dest = PDF_DIR / safe_name
    dest.write_bytes(await file.read())
    result = ingest_pdf(dest)
    return {"ingested": result}


@app.post("/api/query")
def query(req: QueryRequest):
    result = vector_store.query(req.question, req.top_k)

    docs = result["documents"][0] if result["documents"] else []
    metas = result["metadatas"][0] if result["metadatas"] else []
    dists = result["distances"][0] if result["distances"] else []

    retrieved = []
    for i, (doc, meta, dist) in enumerate(zip(docs, metas, dists), start=1):
        retrieved.append(
            {
                "chunk_number": i,
                "similarity": round(1 - dist, 4),  # cosine distance -> similarity
                "source": meta["source"],
                "page": meta["page"],
                "content": doc,
            }
        )

    if not retrieved:
        return {
            "query": req.question,
            "chunks": [],
            "answer": "No chunks retrieved — ingest a PDF into data/pdf first.",
            "prompt": None,
            "tokens": None,
        }

    gen = generate_answer(req.question, retrieved)
    return {
        "query": req.question,
        "chunks": retrieved,
        "answer": gen["answer"],
        "prompt": gen["prompt"],
        "tokens": gen["tokens"],
    }
