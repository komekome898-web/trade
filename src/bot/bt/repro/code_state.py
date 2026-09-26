"""The code a run ran with: the git HEAD and a hash of the working tree's
difference from it (item 3, old item 8: 「git の SHA と差分のハッシュ」).

diff_hash = sha256 over (a) `git diff HEAD --binary` of the code scope and
(b) every untracked, not ignored file of the scope as (path, sha256 of its
bytes). A clean tree still gets a hash (of the empty difference); `dirty`
says whether the difference is empty. The scope is the code that can change
a run's result: CODE_SCOPE (documents are outside it, so editing a note does
not change a run's identity).
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

from .errors import ReproError

REPO = str(Path(__file__).resolve().parents[4])
CODE_SCOPE = ("src", "scripts", "config", "pyproject.toml")
ITEM3_VERSION = "bt-item3-r1"


def _git(repo: str, *args: str) -> bytes:
    try:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReproError(f"git {' '.join(args)} could not run: {exc}") from None
    if r.returncode != 0:
        raise ReproError(f"git {' '.join(args)} failed in {repo}: {r.stderr.decode(errors='replace')[-300:]}")
    return r.stdout


def code_state(repo: Optional[str] = None, scope: Sequence[str] = CODE_SCOPE) -> dict:
    repo = REPO if repo is None else repo
    sha = _git(repo, "rev-parse", "HEAD").decode().strip()
    diff = _git(repo, "diff", "HEAD", "--binary", "--", *scope)
    untracked = sorted(p for p in _git(repo, "ls-files", "--others", "--exclude-standard", "-z", "--", *scope)
                       .decode("utf-8", errors="surrogateescape").split("\0") if p)
    h = hashlib.sha256()
    h.update(b"diff\0" + diff + b"\0untracked\0")
    for p in untracked:
        try:
            with open(os.path.join(repo, p), "rb") as fh:
                content = fh.read()
        except OSError as exc:
            raise ReproError(f"untracked file {p} cannot be read: {exc}") from None
        h.update(p.encode("utf-8", errors="surrogateescape") + b"\0" + hashlib.sha256(content).digest())
    return {"git_sha": sha, "diff_hash": h.hexdigest(), "dirty": bool(diff) or bool(untracked),
            "untracked_files": len(untracked), "code_scope": list(scope)}


def version() -> str:
    import numpy
    import pandas

    from ..core.contract import CORE_VERSION
    return (f"{ITEM3_VERSION}; core {CORE_VERSION}; python {sys.version.split()[0]}; "
            f"numpy {numpy.__version__}; pandas {pandas.__version__}")
