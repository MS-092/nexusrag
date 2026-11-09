from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

log = logging.getLogger("nexusrag.jobs")


class JobRunner:
    """In-process background job runner. Upload requests return before work
    finishes; tests call join() to wait deterministically."""

    def __init__(self, workers: int = 2) -> None:
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="nexusrag-job")
        self._lock = threading.Lock()
        self._pending = 0
        self._idle = threading.Condition(self._lock)

    def submit(self, fn: Callable[[], None]) -> None:
        with self._lock:
            self._pending += 1
        self._pool.submit(self._run, fn)

    def _run(self, fn: Callable[[], None]) -> None:
        try:
            fn()
        except Exception:  # a failing job must not kill the runner
            log.exception("job failed")
        finally:
            with self._idle:
                self._pending -= 1
                self._idle.notify_all()

    def join(self, timeout: float | None = 30) -> None:
        with self._idle:
            if not self._idle.wait_for(lambda: self._pending == 0, timeout=timeout):
                raise TimeoutError("jobs still running")

    def shutdown(self) -> None:
        self._pool.shutdown(wait=True)
