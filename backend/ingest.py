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


# How far back from the target size we will hunt for a word boundary. Beyond
# this the window is honoured as-is, so one long unbroken token (a URL, a
# base64 blob) cannot collapse a chunk to almost nothing.
_BOUNDARY_SEARCH = 120


def _boundary_before(text: str, index: int) -> int:
    """Largest cut point <= index that does not land inside a word."""
    if index >= len(text):
        return len(text)
    window_start = max(0, index - _BOUNDARY_SEARCH)
    cut = text.rfind(" ", window_start, index + 1)
    return cut if cut > window_start else index


def _chunk_text(sections: list[tuple[str, str]]) -> list[dict]:
    """Sliding-window chunking over location-tagged text, cut on word boundaries.

    A plain fixed-width slice splits words in half, so a chunk could begin
    "d, and TestNG..." — the tail of "Cucumber". That hurts twice: the preview
    reads as corrupted, and the embedding is computed over a fragment that
    starts with a meaningless token.
    """
    chunks = []
    for location, text in sections:
        if not text:
            continue
        start = 0
        while start < len(text):
            end = _boundary_before(text, start + CHUNK_SIZE)
            piece = text[start:end].strip()
            if piece:
                chunks.append({"page": location, "text": piece})
            if end >= len(text):
                break
            # Step back by the overlap, then align that to a word boundary too,
            # so the next chunk also opens on a whole word.
            nxt = _boundary_before(text, max(start + 1, end - CHUNK_OVERLAP))
            start = nxt if nxt > start else end
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
