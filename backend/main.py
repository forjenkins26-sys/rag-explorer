import asyncio
import re
import secrets
import tempfile
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import vector_store
from config import (
    ADMIN_TOKEN,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CORS_ORIGINS,
    GROQ_MODEL,
    PDF_DIR,
    TOP_K,
)
from extractors import SUPPORTED_EXTENSIONS
from ingest import ingest_all, ingest_pdf, sync_deleted
from llm import generate_answer
from watcher import start_watcher

# Documents committed under data/pdf/ belong to this pseudo-owner. They are the
# demo's shared seed corpus: every visitor can read them, nobody can delete
# them, and they survive the ephemeral disk because they ship with the repo.
SEED_OWNER = "__seed__"

# A visitor id is opaque to us — the browser generates it. Constrain the shape
# anyway: it lands in Chroma metadata and in chunk-id hashes, so anything
# unbounded is an injection surface rather than an identifier.
_VISITOR_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def visitor(x_visitor_id: str | None = Header(default=None)) -> str:
    """The calling visitor's store id, taken from the X-Visitor-Id header.

    A missing or malformed header is rejected outright rather than falling back
    to a shared bucket. A default here would mean every visitor without an id
    sharing one store — the exact leak this design exists to prevent.
    """
    if not x_visitor_id or not _VISITOR_ID.match(x_visitor_id):
        raise HTTPException(
            400,
            "Missing or malformed X-Visitor-Id header. The browser sends this "
            "automatically; if you are calling the API directly, supply 8-64 "
            "characters of [A-Za-z0-9_-].",
        )
    if x_visitor_id == SEED_OWNER:
        raise HTTPException(400, "Reserved visitor id")
    return x_visitor_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ingestion loads the embedding model (first-run download can take
    # several minutes on a cold host). Run it in the background so uvicorn
    # binds the port immediately — hosts like Render kill the deploy if no
    # port opens within their scan timeout.
    asyncio.create_task(asyncio.to_thread(_startup_ingest))
    yield


def _startup_ingest():
    ingest_all(SEED_OWNER)
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


@app.get("/api/admin/usage")
def admin_usage(x_admin_token: str | None = Header(default=None)):
    """Aggregate usage counts. Requires ADMIN_TOKEN.

    Returns numbers only — no owner ids, filenames, or chunk text. An owner id
    is a bearer token in this design, so listing them here would hand out access
    to every workspace.
    """
    if not ADMIN_TOKEN:
        raise HTTPException(404, "Not found")
    # Constant-time: a plain == leaks the secret one character at a time to
    # anyone willing to measure how long the comparison takes.
    if not x_admin_token or not secrets.compare_digest(x_admin_token, ADMIN_TOKEN):
        raise HTTPException(401, "Unauthorized")
    return vector_store.usage()


@app.get("/api/status")
def status(owner: str = Depends(visitor)):
    # Only the seed corpus lives on disk, so only it can fall out of sync with
    # the folder. A visitor's uploads are held in a temp dir that is deleted as
    # soon as ingestion finishes.
    sync_deleted(SEED_OWNER)
    s = vector_store.stats(owner)
    return {
        "embedding_model": "nomic-embed-text-v1.5",
        "llm_model": GROQ_MODEL,
        "vector_db": "ChromaDB (local, persistent)",
        "pdf_folder": "your private workspace",
        "total_chunks": s["total_chunks"],
        "total_chars": s["total_chars"],
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "embedding_dims": vector_store.embedding_dims(owner),
        "sample_embedding": vector_store.sample_embedding(owner),
        "sources": s["sources"],
    }


@app.get("/api/chunks")
def chunks(owner: str = Depends(visitor)):
    return {"chunks": vector_store.list_chunks(owner)}


@app.post("/api/reingest")
def reingest(owner: str = Depends(visitor)):
    """Copy the shared seed corpus into this visitor's workspace."""
    return {"ingested": ingest_all(owner)}


@app.delete("/api/source/{source_name}")
def delete_source_route(source_name: str, owner: str = Depends(visitor)):
    """Remove one of this visitor's documents.

    Only the caller's chunks are touched. Nothing is deleted from disk: the
    watched folder holds the shared seed corpus, and one visitor must not be
    able to remove a document every other visitor can see.
    """
    # Reject any name that is not a plain filename. `Path(...).name` strips
    # directory components, so a traversal attempt fails this equality check
    # rather than being silently rewritten into a valid-looking path.
    if source_name != Path(source_name).name or source_name in ("", ".", ".."):
        raise HTTPException(400, "Invalid source name")

    if source_name not in vector_store.list_sources(owner):
        raise HTTPException(404, f"No such source: {source_name}")

    vector_store.delete_source(source_name, owner)

    return {
        "deleted": source_name,
        "file_removed": False,
        "remaining_sources": sorted(vector_store.list_sources(owner)),
        "total_chunks": vector_store.stats(owner)["total_chunks"],
    }


@app.delete("/api/sources")
def clear_all_sources(owner: str = Depends(visitor)):
    """Empty this visitor's workspace. Other visitors and the shared seed
    corpus on disk are untouched."""
    sources = sorted(vector_store.list_sources(owner))
    vector_store.delete_owner(owner)

    return {
        "cleared": sources,
        "files_removed": [],
        "total_chunks": vector_store.stats(owner)["total_chunks"],
    }


@app.post("/api/upload")
async def upload(file: UploadFile, owner: str = Depends(visitor)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # Filename is used only as a display label; the file is always written
    # under a fixed, sanitized name — no path traversal risk.
    safe_name = "".join(c for c in file.filename if c.isalnum() or c in " ._-()") or f"upload{ext}"

    # Written to a temp dir, never PDF_DIR. A visitor's upload landing in the
    # watched folder would be picked up by the observer and ingested for the
    # seed corpus, making it visible to everybody.
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / safe_name
        dest.write_bytes(await file.read())
        result = ingest_pdf(dest, owner)
    return {"ingested": result}


@app.post("/api/query")
def query(req: QueryRequest, owner: str = Depends(visitor)):
    result = vector_store.query(req.question, req.top_k, owner)

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
