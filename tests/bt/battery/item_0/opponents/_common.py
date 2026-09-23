"""Shared helpers for 調査結果の候補 (opponent) adapters.

Every helper here does REAL work against the package actually installed in
this candidate's isolated venv (see `docs/DATA/delegations/20260923_backtest_env_prompt.md`
Sec.4: `<scratchpad>/bt/venvs/item_0/<candidate>/`) -- nothing is copied from
`REQUIREMENTS.md`'s prior SCAN-based analysis, even where the finding matches
it. Each adapter file records, in `SceneResult.detail`, the actual module
path / class / call it used, so a later reader can redo the check.
"""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Iterable


def walk_submodule_names(package) -> list[str]:
    """All submodule dotted names under an already-imported package, real walk."""
    try:
        return [m.name for m in pkgutil.walk_packages(package.__path__, prefix=package.__name__ + ".")]
    except Exception:  # noqa: BLE001
        return []


def keyword_hit_modules(all_names: Iterable[str], keywords: Iterable[str]) -> list[str]:
    kws = [k.lower() for k in keywords]
    return [n for n in all_names if any(k in n.lower() for k in kws)]


def class_methods_present(cls, candidate_names: Iterable[str]) -> dict[str, bool]:
    return {n: hasattr(cls, n) for n in candidate_names}


def read_source(module) -> str:
    try:
        return Path(module.__file__).read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""
