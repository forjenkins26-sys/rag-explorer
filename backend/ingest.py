import hashlib
from pathlib import Path

from config import CHUNK_OVERLAP, CHUNK_SIZE
from extractors import SUPPORTED_EXTENSIONS, extract_sections
from vector_store import (
    add_chunks,
    delete_source,
    find_source_by_hash,
    list_sources,
)


def _content_hash(sections: list[tuple[str, str]]) -> str:
    """Fingerprint of a document's extracted text, independent of its filename.

    Hashes the normalised text only — not the raw bytes — so the same document
    re-saved by a different PDF writer still matches. Location labels are
    included because a page-order change is a genuinely different document.
    """
    joined = "\n".join(f"{loc}\x00{text}" for loc, text in sections)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def _chunk_text(sections: list[tuple[str, str]]) -> list[dict]:
    """Fixed-size sliding-window chunking over location-tagged text."""
    chunks = []
    for location, text in sections:
        if not text:
            continue
        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            piece = text[start:end].strip()
            if piece:
                chunks.append({"page": location, "text": piece})
            start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def ingest_pdf(doc_path: Path) -> dict:
    """Read, chunk, embed, and store one document. Idempotent per filename AND
    per content. Despite the name, handles any type in SUPPORTED_EXTENSIONS
    (pdf/txt/md/xlsx/xls)."""
    source_name = doc_path.name

    # Extract and hash BEFORE deleting anything. The old chunks are the only
    # copy of this content in the store — dropping them first would mean a
    # duplicate check that has nothing left to find.
    sections = extract_sections(doc_path)
    section_count = len(sections)
    doc_hash = _content_hash(sections)

    # Same bytes already stored under a different filename? Keep the original.
    # Two names for one document would otherwise consume two of the four
    # retrieval slots with identical text.
    existing = find_source_by_hash(doc_hash)
    if existing is not None and existing != source_name:
        return {
            "source": source_name,
            "pages": section_count,
            "chunks": 0,
            "skipped": "duplicate",
            "duplicate_of": existing,
        }

    delete_source(source_name)  # re-ingest cleanly if the file itself changed
    chunks = _chunk_text(sections)

    ids, texts, metadatas = [], [], []
    for idx, chunk in enumerate(chunks):
        chunk_id = hashlib.sha1(f"{source_name}:{idx}".encode()).hexdigest()[:16]
        ids.append(chunk_id)
        texts.append(chunk["text"])
        metadatas.append(
            {
                "source": source_name,
                "page": chunk["page"],
                "chunk_index": idx,
                "doc_hash": doc_hash,
            }
        )

    if texts:
        add_chunks(ids=ids, texts=texts, metadatas=metadatas)

    return {
        "source": source_name,
        "pages": section_count,
        "chunks": len(texts),
    }


def ingest_all() -> list[dict]:
    from config import PDF_DIR

    results = []
    for doc_path in sorted(PDF_DIR.iterdir()):
        if doc_path.is_file() and doc_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            results.append(ingest_pdf(doc_path))
    return results


def sync_deleted():
    """Drop chunks for documents no longer present in data/pdf."""
    from config import PDF_DIR

    on_disk = {
        p.name
        for p in PDF_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    }
    for source in list_sources():
        if source not in on_disk:
            delete_source(source)
