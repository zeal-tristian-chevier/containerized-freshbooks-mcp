"""
CHEVS Garage Call Processor
----------------------------
Run:  python -m call_processor.main
Drop audio files into watch_folder/ — everything else is automatic.
"""

import signal
import sys
import time
from . import watcher, scheduler


def main() -> None:
    print("CHEVS Garage Call Processor")
    print("Drop audio files into watch_folder/ to process them.\n")

    observer = watcher.start()
    scheduler.get_scheduler()

    # List any pending reminders on startup
    pending = scheduler.list_pending()
    if pending:
        print(f"[STARTUP] {len(pending)} reminder(s) pending:")
        for p in pending:
            args = p.get("args", [])
            print(f"  {p['next_run']} — {args[0][:70] if args else '?'}")
    print()

    def _shutdown(sig, frame):
        print("\nShutting down...")
        observer.stop()
        observer.join()
        scheduler.get_scheduler().shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
