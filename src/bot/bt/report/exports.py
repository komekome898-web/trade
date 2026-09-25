"""The metric exports (item 3, old item 9: 「実行の目的(`動作確認` / `研究`)を指標の書き出しに
必ず載せる」; 委任文 §4).

Every export file is a JSON object {"purpose", "run_id", "kind", "data"}
written by `write_export`, which refuses an export without a purpose (the
two purposes only). No other writer of metric files exists in this layer,
so an export without its purpose cannot be made through it.
"""
from __future__ import annotations

import json
import os
from typing import Any

from .errors import ReportError

PURPOSES = ("動作確認", "研究")
SMOKE, RESEARCH = PURPOSES
SMOKE_WARNING = "動作確認の実行。相場の結論には使わない"


def check_purpose(purpose: Any) -> str:
    if purpose not in PURPOSES or type(purpose) is not str:
        raise ReportError(f"purpose must be one of {PURPOSES}, got {purpose!r}")
    return purpose


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1, allow_nan=False)


def write_export(run_dir: str, kind: str, data: Any, *, purpose: str, run_id: str) -> str:
    p = check_purpose(purpose)
    if type(kind) is not str or not kind.isidentifier():
        raise ReportError(f"export kind must be an identifier, got {kind!r}")
    if type(run_id) is not str or not run_id:
        raise ReportError("run_id must be a non-empty str")
    body = {"purpose": p, "run_id": run_id, "kind": kind, "data": data}
    if p == SMOKE:
        body["warning"] = SMOKE_WARNING
    try:
        text = canonical_json(body)
    except ValueError as exc:
        raise ReportError(f"export {kind}: a value is not finite JSON: {exc}") from None
    path = os.path.join(run_dir, f"{kind}.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text + "\n")
    return path


def read_export(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        body = json.load(fh)
    check_purpose(body.get("purpose"))
    return body
