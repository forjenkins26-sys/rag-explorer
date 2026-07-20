import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import PDF_DIR
from extractors import SUPPORTED_EXTENSIONS
from ingest import ingest_pdf, sync_deleted


class DocHandler(FileSystemEventHandler):
    def _maybe_ingest(self, path: str):
        if Path(path).suffix.lower() in SUPPORTED_EXTENSIONS:
            time.sleep(0.5)  # let the OS finish writing the file
            print(f"[watcher] ingesting {path}")
            target = PDF_DIR / Path(path).name
            if target.exists():
                ingest_pdf(target)

    def on_created(self, event):
        if not event.is_directory:
            self._maybe_ingest(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._maybe_ingest(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            sync_deleted()


def start_watcher():
    observer = Observer()
    observer.schedule(DocHandler(), str(PDF_DIR), recursive=False)
    thread = threading.Thread(target=observer.start, daemon=True)
    thread.start()
    return observer
