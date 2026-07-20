from config import CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL_NAME

# `chromadb` and `sentence_transformers` (which pulls in torch) are both slow
# to *import*, not just to construct — 15s+ each on a fast machine, much more
# on a cold/shared-CPU host. That import cost must not happen at module load,
# because module import happens before uvicorn can bind its port, and hosts
# like Render kill a deploy that doesn't open a port within a few minutes.
# Import both lazily, inside the first function that actually needs them.
_client = None
_collection = None
_model = None


def get_collection():
    global _client, _collection
    if _collection is None:
        import chromadb

        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
    return _collection


def get_embedder():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(EMBED_MODEL_NAME, trust_remote_code=True)
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    return get_embedder().encode(texts, normalize_embeddings=True).tolist()


def add_chunks(ids: list[str], texts: list[str], metadatas: list[dict]) -> None:
    embeddings = embed(texts)
    get_collection().upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)


def query(text: str, top_k: int) -> dict:
    embedding = embed([text])[0]
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


def stats() -> dict:
    data = get_collection().get(include=["metadatas"])
    metadatas = data["metadatas"] or []
    sources = {}
    for m in metadatas:
        sources.setdefault(m["source"], {"chunks": 0, "pages": set()})
        sources[m["source"]]["chunks"] += 1
        sources[m["source"]]["pages"].add(m["page"])
    return {
        "total_chunks": len(metadatas),
        "sources": {
            name: {"chunks": v["chunks"], "pages": len(v["pages"])}
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
