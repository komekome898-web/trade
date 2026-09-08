#!/usr/bin/env python3
"""集計サービスの清算履歴が**どこまで・どの細かさで**遡れるかを測る(手順 P9 の確認用)。

なぜ要るか: 清算履歴の入手経路を全部当たった結果、取引所側で遡れるのは
Gate.io の約 90 日(**1 件ごと**)と OKX の約 24 時間だけだった
(`docs/DATA_SOURCES/LIQUIDATION_HISTORY_SURVEY.md`)。集計サービスがそれより
**深い / 細かい**ものを持っているなら設計が変わるので、キーを入れて実測する。

測るのは 3 つ:
  1. **深さ** — どこまで遡れるか(二分探索で境目を詰める)
  2. **細かさ** — 使える最小の足(1分 / 5分 / … / 日)。1 件ごとか、集計値か
  3. **中身** — 実際に返る値(1 バケットだけ表示。市場データなので秘密ではない)

**鍵は表示しない。** `.env` から読み、設定の有無と文字数だけを出す。
出力はそのまま共有してよい。`.env` は共有しない。

Usage:
    python scripts/check_liquidation_history_depth.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[1]
CA_URL = "https://api.coinalyze.net/v1/liquidation-history"
CA_SYMBOL = "BTCUSDT_PERP.A"          # Binance USDT 無期限(Coinalyze の記法)
CA_INTERVALS = ["1min", "5min", "15min", "30min", "1hour", "4hour", "daily"]
CG_URL = "https://open-api-v4.coinglass.com/api/futures/liquidation/history"


def _day(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


# --------------------------------------------------------------------------- #
# Coinalyze
# --------------------------------------------------------------------------- #

def ca_fetch(key: str, interval: str, days_ago: float, window_h: int = 6):
    """days_ago 日前の window_h 時間ぶん。返り値は (点数, 生の1点 or None, 注記)。"""
    now = int(time.time())
    to = now - int(days_ago * 86400)
    frm = to - window_h * 3600
    try:
        r = requests.get(CA_URL, timeout=30, headers={"api_key": key},
                         params={"symbols": CA_SYMBOL, "interval": interval,
                                 "from": frm, "to": to, "convert_to_usd": "false"})
    except Exception as e:  # noqa: BLE001
        return 0, None, f"{type(e).__name__}: {str(e)[:80]}"
    if r.status_code != 200:
        return 0, None, f"HTTP {r.status_code} {r.text[:100]}"
    try:
        data = r.json()
    except ValueError:
        return 0, None, "JSON ではない応答"
    hist = [pt for series in data for pt in series.get("history", [])] \
        if isinstance(data, list) else []
    return len(hist), (hist[0] if hist else None), ""


def ca_depth_edge(key: str, interval: str, lo_days: float, hi_days: float) -> float:
    """lo(データあり)と hi(なし)の間を二分探索して、遡れる限界を日で返す。"""
    for _ in range(7):
        mid = (lo_days + hi_days) / 2
        n, _s, err = ca_fetch(key, interval, mid)
        if err:
            break
        if n:
            lo_days = mid
        else:
            hi_days = mid
    return lo_days


def probe_coinalyze(key: str) -> None:
    print("=== Coinalyze ===")

    # 1) 使える細かさ(2 日前で試す)
    print("--- 細かさ(2 日前の 6 時間ぶんで確認)---")
    usable = []
    for iv in CA_INTERVALS:
        n, sample, err = ca_fetch(key, iv, 2)
        mark = f"{n} 点" if n else "なし"
        print(f"  {iv:>6}  {mark}{('  ' + err) if err else ''}")
        if n:
            usable.append((iv, sample))
    if not usable:
        print("  どの足でもデータが返りませんでした。鍵か銘柄記法を確認してください。")
        return

    finest = usable[0][0]
    print(f"  → 使える最小の足: **{finest}**")

    # 2) 中身(市場データなので表示してよい)
    print("--- 中身(1 点だけ)---")
    print(f"  {json.dumps(usable[0][1], ensure_ascii=False)[:300]}")
    print("  ※ 値が入っていれば**集計値**(1 件ごとの約定ではない)。"
          "1 件ごとが要るなら Gate.io を使う")

    # 3) 深さ(足ごとに違うことがあるので、最小の足と daily の両方)
    print("--- 深さ(二分探索で境目を詰める)---")
    for iv in dict.fromkeys([finest, "1hour", "daily"]):
        n_far, _s, err = ca_fetch(key, iv, 730)
        if err:
            print(f"  {iv:>6}  確認できず: {err}")
            continue
        if n_far:
            print(f"  {iv:>6}  **730 日前でもデータあり**(それ以上は未確認)")
            continue
        edge = ca_depth_edge(key, iv, 1, 730)
        print(f"  {iv:>6}  約 **{edge:.0f} 日**まで "
              f"({_day(time.time() - edge * 86400)} 頃)")


# --------------------------------------------------------------------------- #
# CoinGlass
# --------------------------------------------------------------------------- #

def probe_coinglass(key: str) -> None:
    print("=== CoinGlass ===")
    now_ms = int(time.time() * 1000)
    for days in (1, 7, 30, 90, 180, 365, 730):
        frm = now_ms - days * 86400_000 - 21_600_000
        try:
            r = requests.get(CG_URL, timeout=30, headers={"CG-API-KEY": key},
                             params={"exchange": "Binance", "symbol": "BTCUSDT",
                                     "interval": "1h", "start_time": frm,
                                     "end_time": now_ms - days * 86400_000})
            body = r.json()
        except Exception as e:  # noqa: BLE001
            print(f"  {days:>4}日前  {type(e).__name__}: {str(e)[:80]}")
            continue
        if str(body.get("code")) not in {"0", "200"}:
            print(f"  {days:>4}日前  code={body.get('code')} {str(body.get('msg'))[:90]}")
            if str(body.get("code")) in {"401", "403"}:
                print("        → 鍵が無効か、無料枠の対象外です")
                return
            continue
        rows = body.get("data") or []
        print(f"  {days:>4}日前 ({_day(frm / 1000)})  "
              f"{'データあり' if rows else 'データなし'}  {len(rows)} 点")
        if rows and days == 1:
            print(f"        中身: {json.dumps(rows[0], ensure_ascii=False)[:220]}")


def main() -> int:
    load_dotenv(REPO / ".env")
    keys = {"COINALYZE_API_KEY": os.environ.get("COINALYZE_API_KEY", "").strip(),
            "COINGLASS_API_KEY": os.environ.get("COINGLASS_API_KEY", "").strip()}
    for name, val in keys.items():
        print(f"{name}: {'設定あり(' + str(len(val)) + '文字)' if val else '未設定'}")
    print()

    if not any(keys.values()):
        print("どちらも未設定です。手順 P9 の 1〜3 を先に行ってください。", file=sys.stderr)
        return 1

    if keys["COINALYZE_API_KEY"]:
        probe_coinalyze(keys["COINALYZE_API_KEY"])
        print()
    if keys["COINGLASS_API_KEY"]:
        probe_coinglass(keys["COINGLASS_API_KEY"])

    print("\n**この出力に鍵は含まれていません。そのまま共有して構いません。**")
    print("`.env` は共有しないでください。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
