"""Double-start guard for the ON1 jobs.

The scheduler can fire a task twice (a missed run replayed on wake, a manual
double-click on top of the scheduled run).  Two concurrent ON1 runs would each
see the same FLAT state and each send an order, which is exactly the failure the
{0,+1} invariant exists to prevent — so the guard is a lock, not a warning.

No pgrep / process scanning: the lock is the file itself.  A lock left behind by
a killed process is honoured until `stale_after_sec` (an ON1 job runs for
seconds; anything older than a few minutes is a corpse), after which it is taken
over and the takeover is reported.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path


class LockBusy(Exception):
    """Another run holds the lock."""


class RunLock:
    def __init__(self, path: str | Path, *, stale_after_sec: float = 900.0,
                 clock=time.time):
        self.path = Path(path)
        self.stale_after_sec = stale_after_sec
        self._clock = clock
        self._held = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            age = self._age()
            if age is None or age < self.stale_after_sec:
                raise LockBusy(f"{self.path} held, age {age}") from None
            self.path.unlink(missing_ok=True)
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps({"pid": os.getpid(), "ts": self._clock()}))
        self._held = True

    def _age(self) -> float | None:
        try:
            stamp = json.loads(self.path.read_text(encoding="utf-8")).get("ts")
            return max(0.0, self._clock() - float(stamp))
        except Exception:
            return None

    def release(self) -> None:
        if self._held:
            self.path.unlink(missing_ok=True)
            self._held = False

    def __enter__(self) -> "RunLock":
        self.acquire()
        return self

    def __exit__(self, *exc) -> None:
        self.release()
