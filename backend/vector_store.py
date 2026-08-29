import threading

from config import CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL_NAME, NOMIC_API_KEY

# `chromadb`'s import is cheap, but must still not run at module load — module
# import happens before uvicorn can bind its port, and hosts like Render kill
# a deploy that doesn't open a port within a few minutes. Lazy-init it inside
# the first function that needs it.
#
# The background ingestion task and incoming API requests both call
# get_collection() concurrently on different threads. Chroma's SQLite-backed
# PersistentClient crashes with "Could not connect to tenant default_tenant"
# if two threads race to create it on a brand-new (not yet initialized) data
# directory — so it's guarded by a lock.
#
# Embeddings come from Nomic's hosted Atlas API (nomic.embed.text), not a
# local sentence-transformers/torch model — torch doesn't fit free-tier host
# RAM (512MB), confirmed by a crash-loop on Render's free plan. The hosted
# API keeps the backend lightweight enough to deploy anywhere for free.
_client = None
_collection = None
_collection_lock = threading.Lock()


def get_collection():
    global _client, _collection
    if _collection is None:
        with _collection_lock:
            if _collection is None:  # re-check: another thread may have won the race
                import chromadb

                _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
                _collection = _client.get_or_create_collection(
                    name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
                )
    return _collection


_nomic_logged_in = False
_nomic_login_lock = threading.Lock()


def _ensure_nomic_login():
    global _nomic_logged_in
    if not _nomic_logged_in:
        with _nomic_login_lock:
            if not _nomic_logged_in:
                import nomic

                nomic.login(NOMIC_API_KEY)
                _nomic_logged_in = True


def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    from nomic import embed

    _ensure_nomic_login()
    result = embed.text(
        texts=texts,
        model=EMBED_MODEL_NAME,
        task_type=task_type,
        dimensionality=768,
    )
    return result["embeddings"]


def embed_documents(texts: list[str]) -> list[list[float]]:
    return _embed(texts, task_type="search_document")


def embed_query(text: str) -> list[float]:
    return _embed([text], task_type="search_query")[0]


def add_chunks(ids: list[str], texts: list[str], metadatas: list[dict]) -> None:
    embeddings = embed_documents(texts)
    get_collection().upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)


def query(text: str, top_k: int) -> dict:
    embedding = embed_query(text)
    return get_collection().query(
        query_embeddings=[embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )


def delete_source(source_name: str) -> None:
    get_collection().delete(where={"source": source_name})


def list_sources() -> set[str]:
    data = get_collection().get(include=["metadatas"])
    return {m["source"] for m in data["metadatas"]} if data["metadatas"] else set()


def find_source_by_hash(doc_hash: str) -> str | None:
    """Filename already storing this exact content, or None.

    Content-level dedup: the same document uploaded under two names (spaces vs
    underscores, "(1)" suffixes) would otherwise be stored twice and consume two
    of the four retrieval slots with identical text. Filename equality alone
    cannot catch that.
    """
    data = get_collection().get(where={"doc_hash": doc_hash}, include=["metadatas"])
    metadatas = data.get("metadatas") or []
    return metadatas[0]["source"] if metadatas else None


def stats() -> dict:
    # Documents come back alongside metadata so the character total is derived
    # from what is actually stored, rather than a counter kept in parallel that
    # would drift on every delete or re-ingest.
    data = get_collection().get(include=["metadatas", "documents"])
    metadatas = data["metadatas"] or []
    documents = data["documents"] or []
    sources = {}
    for m, doc in zip(metadatas, documents):
        s = sources.setdefault(m["source"], {"chunks": 0, "pages": set(), "chars": 0})
        s["chunks"] += 1
        s["pages"].add(m["page"])
        s["chars"] += len(doc or "")
    return {
        "total_chunks": len(metadatas),
        "total_chars": sum(len(d or "") for d in documents),
        "sources": {
            name: {"chunks": v["chunks"], "pages": len(v["pages"]), "chars": v["chars"]}
            for name, v in sources.items()
        },
    }


def embedding_dims() -> int:
    sample = get_collection().get(limit=1, include=["embeddings"])
    embeddings = sample.get("embeddings")
    if embeddings is not None and len(embeddings):
        return len(embeddings[0])
    return 0


def sample_embedding(n: int = 8) -> list[float]:
    sample = get_collection().get(limit=1, include=["embeddings"])
    embeddings = sample.get("embeddings")
    if embeddings is not None and len(embeddings):
        return [round(x, 4) for x in embeddings[0][:n]]
    return []


def list_chunks(limit: int = 200) -> list[dict]:
    """All stored chunks, ordered by chunk_index, for the preview browser."""
    data = get_collection().get(limit=limit, include=["documents", "metadatas"])
    rows = list(zip(data["documents"] or [], data["metadatas"] or []))
    rows.sort(key=lambda r: (r[1]["source"], r[1]["chunk_index"]))
    return [
        {
            "index": meta["chunk_index"],
            "source": meta["source"],
            "page": meta["page"],
            "chars": len(doc),
            "content": doc,
        }
        for doc, meta in rows
    ]
