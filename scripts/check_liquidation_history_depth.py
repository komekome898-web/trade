#!/usr/bin/env python3
"""集計サービスの清算履歴が**どこまで遡れるか**を測る(手順 P9 の確認用)。

なぜ要るか: 清算履歴の入手経路を全部当たった結果、取引所側で遡れるのは
Gate.io の約 90 日と OKX の約 24 時間だけだった(`docs/DATA_SOURCES/LIQUIDATION_HISTORY_SURVEY.md`)。
集計サービス(Coinalyze / CoinGlass)は `liquidation-history` を持っているが**深さが不明**で、
それはキーが無いと分からない。**もし年単位で遡れるなら、自前記録の位置づけが変わる。**

**鍵は表示しない。** `.env` から読み、応答の有無と深さだけを出す。
共有してよいのはこのスクリプトの出力(鍵を含まない)であって、`.env` ではない。

Usage:
    python scripts/check_liquidation_history_depth.py
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[1]
PROBE_DAYS = (1, 7, 30, 90, 180, 365, 730)


def _fmt(ts_sec: float) -> str:
    return datetime.fromtimestamp(ts_sec, tz=timezone.utc).strftime("%Y-%m-%d")


def probe_coinalyze(key: str) -> None:
    """Coinalyze: api_key ヘッダ。1 時間足の清算履歴を過去に向かって当てていく。"""
    url = "https://api.coinalyze.net/v1/liquidation-history"
    now = int(time.time())
    print("--- Coinalyze ---")
    for days in PROBE_DAYS:
        frm, to = now - days * 86400 - 7200, now - days * 86400
        try:
            r = requests.get(url, timeout=30, headers={"api_key": key},
                             params={"symbols": "BTCUSDT_PERP.A", "interval": "1hour",
                                     "from": frm, "to": to, "convert_to_usd": "false"})
            if r.status_code != 200:
                print(f"  {days:>4}日前  HTTP {r.status_code}  {r.text[:120]}")
                if r.status_code in (401, 403):
                    print("        → 鍵が未設定か無効です(P9 の 1 を見直してください)")
                    return
                continue
            data = r.json()
            rows = sum(len(x.get("history", [])) for x in data) if isinstance(data, list) else 0
            print(f"  {days:>4}日前 ({_fmt(frm)})  {'データあり' if rows else 'データなし'}"
                  f"  {rows} 点")
        except Exception as e:  # noqa: BLE001
            print(f"  {days:>4}日前  {type(e).__name__}: {str(e)[:100]}")


def probe_coinglass(key: str) -> None:
    """CoinGlass v4: CG-API-KEY ヘッダ。無料枠で何が返るかを見る。"""
    url = "https://open-api-v4.coinglass.com/api/futures/liquidation/history"
    now_ms = int(time.time() * 1000)
    print("--- CoinGlass ---")
    for days in PROBE_DAYS:
        frm = now_ms - days * 86400_000 - 7_200_000
        try:
            r = requests.get(url, timeout=30, headers={"CG-API-KEY": key},
                             params={"exchange": "Binance", "symbol": "BTCUSDT",
                                     "interval": "1h", "start_time": frm,
                                     "end_time": now_ms - days * 86400_000})
            body = r.json() if r.headers.get("content-type", "").startswith(
                "application/json") else {}
            if str(body.get("code")) not in {"0", "200"}:
                print(f"  {days:>4}日前  code={body.get('code')} {str(body.get('msg'))[:100]}")
                if str(body.get("code")) in {"401", "403"}:
                    print("        → 鍵が未設定か無効、または無料枠の対象外です")
                    return
                continue
            rows = len(body.get("data") or [])
            print(f"  {days:>4}日前 ({_fmt(frm / 1000)})  "
                  f"{'データあり' if rows else 'データなし'}  {rows} 点")
        except Exception as e:  # noqa: BLE001
            print(f"  {days:>4}日前  {type(e).__name__}: {str(e)[:100]}")


def main() -> int:
    load_dotenv(REPO / ".env")
    keys = {"COINALYZE_API_KEY": os.environ.get("COINALYZE_API_KEY", "").strip(),
            "COINGLASS_API_KEY": os.environ.get("COINGLASS_API_KEY", "").strip()}

    for name, val in keys.items():
        # 鍵そのものは絶対に出さない。設定されているかと長さだけ。
        print(f"{name}: {'設定あり(' + str(len(val)) + '文字)' if val else '未設定'}")
    print()

    if not any(keys.values()):
        print("どちらも未設定です。手順 P9 の 1〜2 を先に行ってください。", file=sys.stderr)
        return 1

    if keys["COINALYZE_API_KEY"]:
        probe_coinalyze(keys["COINALYZE_API_KEY"])
        print()
    if keys["COINGLASS_API_KEY"]:
        probe_coinglass(keys["COINGLASS_API_KEY"])

    print("\n**この出力には鍵が含まれていません。そのまま共有して構いません。**")
    print("`.env` は共有しないでください。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
