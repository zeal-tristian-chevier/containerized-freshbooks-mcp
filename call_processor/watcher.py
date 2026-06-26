import time
import shutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .config import WATCH_FOLDER, PROCESSED_FOLDER, AUDIO_EXTENSIONS
from . import pipeline


class _AudioHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in AUDIO_EXTENSIONS:
            return
        # Wait briefly to ensure the file is fully written before processing
        time.sleep(3)
        if not path.exists():
            return
        try:
            pipeline.process(path)
            dest = PROCESSED_FOLDER / path.name
            shutil.move(str(path), str(dest))
            print(f"[WATCHER] Moved to processed/: {path.name}")
        except Exception as exc:
            print(f"[WATCHER] Error processing {path.name}: {exc}")


def start() -> Observer:
    WATCH_FOLDER.mkdir(parents=True, exist_ok=True)
    PROCESSED_FOLDER.mkdir(parents=True, exist_ok=True)
    observer = Observer()
    observer.schedule(_AudioHandler(), str(WATCH_FOLDER), recursive=False)
    observer.start()
    print(f"[WATCHER] Watching {WATCH_FOLDER}")
    return observer
