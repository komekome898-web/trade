"""測定 1 回ごとの取引の記録 `trades.json.gz`(オーナー L-D04、L-594)。

ダッシュボード(バックテストのタブ)がこの形を読む。1 取引 1 行の中身を、列ごとの配列にして gzip した JSON で書く:

    {"version": 1, "t_unit": "ns", "entry_t_ns": [...], "entry_px": [...], "exit_t_ns": [...], "exit_px": [...],
     "side": [1 か -1], "qty": [...], "pnl_pct": [...]}

- 置き場はその実行の run_record.json と同じ所。git に入れる(.gitignore で外さない)。
- 封印: 封印の境(2023-12-18T00:00Z。`scripts/w4_measure/common.py` の SEAL、P2-08)以降に建てたか決済した取引が
  1 つでもあれば書かない(`SealedTradesError`)。封印にかかる実行の取引の記録は git に入れない(L-D04 (4))。
- 量 qty はその取引の最大の持ち高(持ち高の最大を 1 とする尺度)。損益 pnl_pct は各台本の定義の損益の率を % で書く
  (L-920: bp は値動き率だけの名前。建玉や段数で重みを付けた損益の率は bp と呼ばない)。
- L-920 より前の記録は pnl_bp(同じ率 × 1 万)を持つ。read_trades_json は pnl_bp を / 100 して pnl_pct として返す。
- 大きさを抑えるため、値段は小数 4 桁、量は 6 桁、損益は 6 桁(% の 6 桁 = 前の × 1 万の 4 桁)に丸めて書く(表示に要る精度。集計は各台本の
  summary.json が丸める前の値で出す)。
"""
from __future__ import annotations

import gzip
import json
import math
from datetime import datetime, timezone
from typing import Iterable

SEAL_START_NS = int(datetime(2023, 12, 18, tzinfo=timezone.utc).timestamp()) * 1_000_000_000
_DIGITS = {"entry_px": 4, "exit_px": 4, "qty": 6, "pnl_pct": 6}
FIELDS = ("entry_t_ns", "entry_px", "exit_t_ns", "exit_px", "side", "qty", "pnl_pct")


class SealedTradesError(ValueError):
    """封印の境以降の取引を含む記録は書かない。"""


def write_trades_json(path: str, trades: Iterable[dict], seal_start_ns: int = SEAL_START_NS) -> int:
    """trades の各要素は FIELDS の鍵を持つ dict。書いた取引の数を返す。"""
    cols: dict = {k: [] for k in FIELDS}
    for t in trades:
        e, x = int(t["entry_t_ns"]), int(t["exit_t_ns"])
        if e >= seal_start_ns or x >= seal_start_ns:
            raise SealedTradesError(f"封印の境以降の取引がある(entry {e}, exit {x})。取引の記録は書かない")
        side = int(t["side"])
        if side not in (1, -1):
            raise ValueError(f"side は 1 か -1: {side!r}")
        cols["entry_t_ns"].append(e)
        cols["exit_t_ns"].append(x)
        cols["side"].append(side)
        for k in ("entry_px", "exit_px", "qty", "pnl_pct"):
            v = float(t[k])
            if not math.isfinite(v):
                raise ValueError(f"{k} が有限でない: {v!r}")
            cols[k].append(round(v, _DIGITS[k]))
    doc = {"version": 1, "t_unit": "ns", **cols}
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(doc, fh, separators=(",", ":"))
    return len(cols["side"])


def read_trades_json(path: str) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        doc = json.load(fh)
    if doc.get("version") != 1 or doc.get("t_unit") != "ns":
        raise ValueError(f"形が違う: version={doc.get('version')!r} t_unit={doc.get('t_unit')!r}")
    if "pnl_pct" not in doc and "pnl_bp" in doc:  # L-920 より前の記録(損益の率 × 1 万)。% に換える
        doc["pnl_pct"] = [v / 100 for v in doc.pop("pnl_bp")]
    n = {len(doc[k]) for k in FIELDS}
    if len(n) != 1:
        raise ValueError(f"列の長さが揃っていない: {sorted(n)}")
    return doc


__all__ = ["FIELDS", "SEAL_START_NS", "SealedTradesError", "read_trades_json", "write_trades_json"]
