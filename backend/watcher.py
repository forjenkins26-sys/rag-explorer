import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import PDF_DIR
from extractors import SUPPORTED_EXTENSIONS
from ingest import ingest_pdf, sync_deleted

# The watched folder holds the shared seed corpus — documents committed with the
# repo that every visitor can read. Anything appearing here is ingested for that
# pseudo-owner, never for a visitor: a file on the server's disk has no visitor
# attached to it. Visitor uploads go through /api/upload into a temp dir instead.
SEED_OWNER = "__seed__"


class DocHandler(FileSystemEventHandler):
    def _maybe_ingest(self, path: str):
        if Path(path).suffix.lower() in SUPPORTED_EXTENSIONS:
            time.sleep(0.5)  # let the OS finish writing the file
            print(f"[watcher] ingesting {path} for the seed corpus")
            target = PDF_DIR / Path(path).name
            if target.exists():
                ingest_pdf(target, SEED_OWNER)

    def on_created(self, event):
        if not event.is_directory:
            self._maybe_ingest(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._maybe_ingest(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            sync_deleted(SEED_OWNER)


def start_watcher():
    observer = Observer()
    observer.schedule(DocHandler(), str(PDF_DIR), recursive=False)
    thread = threading.Thread(target=observer.start, daemon=True)
    thread.start()
    return observer
