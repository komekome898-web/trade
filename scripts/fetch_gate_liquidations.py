#!/usr/bin/env python3
"""Gate.io の**1 件ごと**の清算(強制決済)履歴を、消える前に取り込む。

なぜ急ぐか: 入手経路を全部当たった結果、**分解能のある清算履歴を過去に遡れるのは
Gate.io だけ**だった(`docs/DATA_SOURCES/LIQUIDATION_HISTORY_SURVEY.md`)。
認証不要・1 件ごと・ローリング**約 90 日**。**窓は動く**ので、取り込まなければ毎日 1 日分ずつ
永久に失われる。Coinalyze の分足は 7 日しか無く、Binance と BitMEX は履歴を持たない。

API の制約(2026-09-08 実測):
- `from`/`to` は **1 時間以内**でなければ 400(`range from/to must in 1 hour`)
- `from`/`to` は**両端とも含む**(from=to=T で T ちょうどの行が返る)
- `to` だけ渡すと**暗黙に 1 時間窓**になる(`to-3600`〜`to`)
- `limit` の上限は **1000**
したがって 1 時間ずつ遡るしかない。90 日 = 2160 リクエスト / 銘柄。

設計上の約束(記録器 `record_liquidations.py` と同じ):
- **返ってきた行をそのまま保存する。** 列を足さない・削らない・解釈しない。
- **窓ごとの取得結果を `.progress.json` に残す。** これがあると「0 件だった時間」と
  「まだ取っていない時間」を区別できる — **陰性と不明を分ける**ための最低条件。
- 窓が飽和(= `limit` ちょうど)したら**半分に割って取り直す**(1 秒まで再帰)。
  飽和するのはカスケードした時間 = 一番見たい時間なので、ここで諦めない。
  1 秒でも飽和したら台帳に区間を残す — **取りこぼしを黙って作らない**。
- 再実行は**続きから**(取得済みの窓は飛ばして追記)。

Usage:
    python scripts/fetch_gate_liquidations.py                    # BTC_USDT を 90 日
    python scripts/fetch_gate_liquidations.py --days 7 --contract ETH_USDT
    python scripts/fetch_gate_liquidations.py --out-dir backtest_data/gate_liquidations_20260908
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[1]
URL = "https://api.gateio.ws/api/v4/futures/usdt/liq_orders"
LIMIT = 1000                 # API の上限
HOUR = 3600
PAUSE = 0.15                 # 連投しない(公開エンドポイントへの礼儀)
MAX_RETRY = 5


def _log(msg: str) -> None:
    print(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}", flush=True)


def _utc(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def fetch_window(contract: str, frm: int, to: int) -> list[dict]:
    """[frm, to] を取る(両端含む)。失敗は指数バックオフで再試行。"""
    backoff = 1.0
    for attempt in range(MAX_RETRY):
        try:
            r = requests.get(URL, timeout=30, params={
                "contract": contract, "limit": LIMIT, "from": frm, "to": to})
        except Exception as e:  # noqa: BLE001
            _log(f"  通信失敗 {type(e).__name__}: {str(e)[:80]} — {backoff:.0f}s 後に再試行")
        else:
            if r.status_code == 200:
                body = r.json()
                return body if isinstance(body, list) else []
            if r.status_code == 400:
                raise RuntimeError(f"400 {r.text[:200]}")   # 窓の取り方が違う = 直す対象
            _log(f"  HTTP {r.status_code} {r.text[:100]} — {backoff:.0f}s 後に再試行")
        time.sleep(backoff)
        backoff = min(backoff * 2, 30.0)
    raise RuntimeError(f"{MAX_RETRY} 回失敗: {contract} {_utc(frm)}")


def fetch_span(contract: str, frm: int, to: int,
               truncated: list[tuple[int, int]]) -> list[dict]:
    """[frm, to] を取る。**飽和したら半分に割って取り直す**(1 秒まで再帰)。

    飽和 = `limit` ちょうど返った = API に切られている = **取りこぼしている**。
    そして飽和するのは清算がカスケードした時間で、それはカツオの機構にとって
    **一番見たい時間**である。だから「15 分まで割って諦める」ではなく、
    **1 秒になるまで割る**。1 秒でも飽和したらそれ以上は割れないので、
    `truncated` に積んで**取りこぼしたことを台帳に残す**(黙って落とさない)。
    """
    rows = fetch_window(contract, frm, to)
    time.sleep(PAUSE)
    if len(rows) < LIMIT:
        return rows
    if frm >= to:
        # 1 秒に 1000 件以上。これ以上は API の粒度で割れない
        _log(f"  **1 秒でも飽和**: {_utc(frm)} ({frm}) — 取りこぼし確定")
        truncated.append((frm, to))
        return rows
    mid = frm + (to - frm) // 2
    _log(f"  飽和({LIMIT} 件): {_utc(frm)} 幅 {to - frm + 1}s — 半分に分割")
    return (fetch_span(contract, frm, mid, truncated)
            + fetch_span(contract, mid + 1, to, truncated))


def fetch_hour(contract: str, frm: int) -> tuple[list[dict], list[tuple[int, int]]]:
    """1 時間ぶん。返り値は (行, 割り切れずに取りこぼした区間)。"""
    truncated: list[tuple[int, int]] = []
    return fetch_span(contract, frm, frm + HOUR - 1, truncated), truncated


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", default="BTC_USDT")
    ap.add_argument("--days", type=float, default=90.0,
                    help="何日前まで遡るか(Gate の窓は約 90 日)")
    ap.add_argument("--out-dir", default=None,
                    help="既定: backtest_data/gate_liquidations_<今日>")
    args = ap.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else (
        REPO / "backtest_data" /
        f"gate_liquidations_{datetime.now(timezone.utc).strftime('%Y%m%d')}")
    out_dir.mkdir(parents=True, exist_ok=True)
    data_path = out_dir / f"{args.contract}.jsonl.gz"
    prog_path = out_dir / f"{args.contract}.progress.json"

    progress: dict[str, dict] = {}
    if prog_path.exists():
        progress = json.loads(prog_path.read_text(encoding="utf-8"))
        _log(f"再開: 取得済みの窓 {len(progress)} 個")

    now = int(time.time())
    newest = (now // HOUR) * HOUR - HOUR      # 進行中の 1 時間は取らない(不完全なので)
    oldest = newest - int(args.days * 86400)
    windows = list(range(newest, oldest, -HOUR))
    todo = [w for w in windows if str(w) not in progress]
    _log(f"{args.contract}: {_utc(oldest)} 〜 {_utc(newest + HOUR)} = "
         f"{len(windows)} 窓、うち未取得 {len(todo)}")

    total = sum(v["n"] for v in progress.values())
    empty_run = 0
    try:
        with gzip.open(data_path, "at", encoding="utf-8") as fh:
            for i, frm in enumerate(todo, 1):
                rows, truncated = fetch_hour(args.contract, frm)
                for row in rows:
                    fh.write(json.dumps(row, ensure_ascii=False,
                                        separators=(",", ":")) + "\n")
                fh.flush()
                progress[str(frm)] = {"n": len(rows),
                                      "trunc": [list(t) for t in truncated]}
                total += len(rows)
                empty_run = empty_run + 1 if not rows else 0
                if truncated:
                    _log(f"  {_utc(frm)}: **取りこぼし {len(truncated)} 区間**")
                if i % 100 == 0 or i == len(todo):
                    prog_path.write_text(json.dumps(progress, separators=(",", ":")),
                                         encoding="utf-8")
                    _log(f"  {i}/{len(todo)}  {_utc(frm)}  累計 {total} 件")
                if empty_run >= 48:
                    # 48 時間続けて空 = 保持窓の外に出たと判断(90 日の境目は動く)
                    _log(f"  48 時間連続で 0 件 — 保持窓の外と判断して打ち切り({_utc(frm)})")
                    break
                time.sleep(PAUSE)
    finally:
        prog_path.write_text(json.dumps(progress, separators=(",", ":")), encoding="utf-8")

    got = sorted(int(k) for k in progress)
    manifest = {
        "source": URL,
        "auth": "none",
        "contract": args.contract,
        "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_covered_utc": [_utc(min(got)), _utc(max(got) + HOUR)] if got else None,
        "hours_requested": len(windows),
        "hours_fetched": len(progress),
        "hours_empty": sum(1 for v in progress.values() if v["n"] == 0),
        "hours_with_truncation": {k: v["trunc"] for k, v in progress.items() if v["trunc"]},
        "rows": total,
        "note": "行は API の返り値そのまま。取得済みの時間は .progress.json が真実 "
                "(0 件だった時間と、取っていない時間を区別するため)。"
                "窓はローリングなので、古い側は再取得できない。",
    }
    (out_dir / f"{args.contract}.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(f"完了: {total} 件 -> {data_path}")
    _log(f"  取得した時間 {len(progress)} / 空だった時間 {manifest['hours_empty']} / "
         f"取りこぼしのある時間 {len(manifest['hours_with_truncation'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
