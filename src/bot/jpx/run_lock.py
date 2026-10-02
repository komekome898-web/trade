"""Double-start guard for the ON1 jobs.

The scheduler can fire a task twice (a missed run replayed on wake, a manual
double-click on top of the scheduled run).  Two concurrent ON1 runs would each
see the same FLAT state and each send an order, which is exactly the failure the
{0,+1} invariant exists to prevent — so the guard is a lock, not a warning.

No pgrep / process scanning: the lock is the file itself.  A lock left behind by
a killed process is honoured until `stale_after_sec` (an ON1 job runs for
seconds; anything older than a few minutes is a corpse), after which it is taken
over and the takeover is reported. A lock left EMPTY (killed between creating
the file and writing it) ages by its mtime instead (`RunLock._age`).
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
        """Seconds since the lock was taken; None only when nothing can say.

        A readable lock ages by the `ts` its holder wrote, on `self._clock`,
        exactly as before.

        An UNREADABLE lock (empty, or cut mid-write) ages by the file's mtime.
        `acquire` creates the file with O_EXCL and writes the stamp right
        after; a crash or power loss between the two leaves an empty file, and
        that file used to read as "held, age None" forever — every later run
        refused (exit code 3) until a human deleted it.

        What an empty file older than `stale_after_sec` (900 s by default) can
        be: almost always the remains of a process that died between the
        create and the write. Not ONLY that: a process suspended in exactly
        that gap (sleep, hibernation) for longer than `stale_after_sec` also
        leaves one, and wakes up believing it holds a lock another run has
        meanwhile taken over. That gap is microseconds wide, and the readable
        path has always had the same exposure — a holder suspended for longer
        than `stale_after_sec` after writing its stamp is taken over the same
        way. So the double-start guard of the ON1 jobs is not newly weakened
        by this fallback; an empty file younger than `stale_after_sec` is
        still honoured as held. Holders that refresh their lock (the
        recorders' heartbeats) rewrite the JSON, so they stay on the readable
        path.

        The mtime is the filesystem's WALL clock, so it is compared with
        `time.time()`, not with the injectable `self._clock`: a fake clock
        minus a real mtime would come out negative, clamp to 0 and read
        "fresh" forever — the same bug in the other direction. None only when
        the file cannot even be stat'ed (vanished between the failed create
        and here: the next attempt decides).
        """
        try:
            stamp = json.loads(self.path.read_text(encoding="utf-8")).get("ts")
            return max(0.0, self._clock() - float(stamp))
        except Exception:
            pass
        try:
            return max(0.0, time.time() - self.path.stat().st_mtime)
        except OSError:
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
