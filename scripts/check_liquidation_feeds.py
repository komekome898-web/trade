#!/usr/bin/env python3
"""清算(強制決済)フィードの到達確認 — オーナー PC で 1 回走らせるための道具。

なぜ要るか: 清算フローは取引所によって**履歴の有無が違う**。Gate.io はローリング約 90 日、
OKX は約 24 時間を公開しているが、**Binance と BitMEX はストリームのみで履歴が無い**
(全経路の実測: `docs/DATA_SOURCES/LIQUIDATION_HISTORY_SURVEY.md`)。
履歴を持たない取引所ぶんは自前で記録するしかないので、まずどれが届くかを確かめる。

**このスクリプトは WS で記録できるかだけを見る。** Gate.io の 90 日は REST の取り込みで、
別建て(未実装)。ここに Gate が出てこないのはそのため。

このスクリプトがすること:
  1. 各取引所の REST に GET して応答コードを見る(**HEAD は使わない** — 偽の 404 を返す
     ことがある。`docs/DATA_PERISHABILITY.md` §5 の方法上の注意)
  2. 各取引所の WebSocket に接続し、購読を送り、**実際にメッセージが来るか**を待つ
  3. 結果を表で出し、`data/liquidation_feed_check.json` に書く

読み取り専用・認証なし・発注なし。ネットワークに出る以外の副作用は上記 JSON のみ。

Usage:
    python scripts/check_liquidation_feeds.py            # 全ベニュー、各 60 秒待つ
    python scripts/check_liquidation_feeds.py --wait 20  # 待ち時間を変える
    python scripts/check_liquidation_feeds.py --venues okx,bitmex
"""
from __future__ import annotations

import argparse
import asyncio
import json
import ssl
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    import websockets
except ImportError:  # pragma: no cover - reported, not raised
    websockets = None

REPO = Path(__file__).resolve().parents[1]

# 清算フィードの定義。sub = 接続後に送る購読メッセージ(None なら URL に含む)。
# 「清算らしいメッセージか」の判定は hit() が行う — 板やハートビートを数えないため。
FEEDS: dict[str, dict] = {
    "binance_um": {
        "rest": "https://fapi.binance.com/fapi/v1/ping",
        "ws": "wss://fstream.binance.com/ws/!forceOrder@arr",
        "sub": None,
        "hit": lambda m: isinstance(m, dict) and m.get("e") == "forceOrder",
        "note": "Binance USD-M 先物。全銘柄の強制決済。**履歴なし**(記録しないと永久に空白)",
    },
    "bybit": {
        "rest": "https://api.bybit.com/v5/market/time",
        "ws": "wss://stream.bybit.com/v5/public/linear",
        "sub": {"op": "subscribe", "args": ["allLiquidation.BTCUSDT"]},
        "hit": lambda m: isinstance(m, dict) and str(m.get("topic", "")).startswith(
            ("allLiquidation", "liquidation")),
        "note": "Bybit linear perps。**履歴なし**(公開アーカイブに清算フラグが無い)",
    },
    "okx": {
        "rest": ("https://www.okx.com/api/v5/public/liquidation-orders"
                 "?instType=SWAP&uly=BTC-USDT&state=filled&limit=1"),
        "ws": "wss://ws.okx.com:8443/ws/v5/public",
        "sub": {"op": "subscribe",
                "args": [{"channel": "liquidation-orders", "instType": "SWAP"}]},
        "hit": lambda m: isinstance(m, dict)
        and m.get("arg", {}).get("channel") == "liquidation-orders"
        and m.get("data"),
        "note": "OKX SWAP。REST はローリング約 24 時間(実測)= 欠測の修復に使える",
    },
    "bitmex": {
        "rest": "https://www.bitmex.com/api/v1/liquidation?symbol=XBTUSD&count=1",
        "ws": "wss://ws.bitmex.com/realtime?subscribe=liquidation:XBTUSD",
        "sub": None,
        # partial は購読直後の「現在オープンの清算注文」スナップショットで、
        # 空のことが多い。**中身がある時だけ**清算と数える(0 件を 1 件と誤らせない)。
        "hit": lambda m: isinstance(m, dict) and m.get("table") == "liquidation"
        and m.get("action") in {"insert", "partial", "update"} and m.get("data"),
        "note": "BitMEX XBTUSD。カツオの原典ベニュー。**履歴なし**(公開約定に清算フラグも無い)",
    },
}


def check_rest(url: str, timeout: float = 20.0) -> dict:
    """GET で叩く。HEAD は使わない(偽の 404 を返す実例がある)。"""
    try:
        r = requests.get(url, timeout=timeout,
                         headers={"User-Agent": "liquidation-feed-check/1.0"})
        body = r.text[:200].replace("\n", " ")
        return {"ok": r.status_code == 200, "status": r.status_code, "body": body}
    except Exception as e:  # noqa: BLE001 - 到達確認なので理由をそのまま出す
        return {"ok": False, "status": None, "error": f"{type(e).__name__}: {e}"[:200]}


async def check_ws(name: str, spec: dict, wait_sec: float) -> dict:
    """接続 → 購読 → **清算メッセージが実際に来るか**を wait_sec まで待つ。

    清算は常時起きるものではないので、来なければ「届かない」とは限らない。
    そこを混同しないよう、接続の成否と受信の有無を別々に返す。
    """
    if websockets is None:
        return {"connected": False, "error": "websockets が入っていない"}
    out: dict = {"connected": False, "messages": 0, "liquidations": 0,
                 "first_liquidation": None}
    try:
        ctx = ssl.create_default_context()
        async with websockets.connect(spec["ws"], ssl=ctx,
                                      open_timeout=20, close_timeout=5) as ws:
            out["connected"] = True
            if spec["sub"]:
                await ws.send(json.dumps(spec["sub"]))
            deadline = time.monotonic() + wait_sec
            while time.monotonic() < deadline:
                try:
                    raw = await asyncio.wait_for(
                        ws.recv(), timeout=max(1.0, deadline - time.monotonic()))
                except asyncio.TimeoutError:
                    break
                out["messages"] += 1
                try:
                    msg = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                if spec["hit"](msg):
                    out["liquidations"] += 1
                    if out["first_liquidation"] is None:
                        out["first_liquidation"] = json.dumps(msg)[:300]
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {e}"[:200]
    return out


async def run(venues: list[str], wait_sec: float) -> dict:
    result = {"checked_utc": datetime.now(timezone.utc).isoformat(),
              "wait_sec": wait_sec, "venues": {}}
    for name in venues:
        spec = FEEDS[name]
        print(f"--- {name} ---")
        rest = check_rest(spec["rest"])
        print(f"  REST  {rest.get('status')}  "
              f"{'OK' if rest['ok'] else rest.get('error', rest.get('body', ''))[:80]}")
        ws = await check_ws(name, spec, wait_sec)
        if ws["connected"]:
            print(f"  WS    接続OK  受信 {ws['messages']} 件 / うち清算 "
                  f"{ws['liquidations']} 件")
        else:
            print(f"  WS    接続不可  {ws.get('error', '')[:100]}")
        result["venues"][name] = {"rest": rest, "ws": ws, "note": spec["note"]}
    return result


def verdict(v: dict) -> str:
    """記録に使えるか。**清算が 0 件でも接続できていれば「使える」**
    (清算は常時起きるものではない)。"""
    if v["ws"].get("connected"):
        return "使える(記録可)" if v["ws"]["liquidations"] else "使える(接続OK・清算未発生)"
    if v["rest"]["ok"]:
        return "WS 不可 / REST は届く(ポーリングなら可)"
    return "届かない"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--venues", default=",".join(FEEDS),
                    help="カンマ区切り。既定は全部")
    ap.add_argument("--wait", type=float, default=60.0,
                    help="各ベニューで清算メッセージを待つ秒数(既定 60)")
    args = ap.parse_args()

    venues = [v.strip() for v in args.venues.split(",") if v.strip()]
    unknown = [v for v in venues if v not in FEEDS]
    if unknown:
        print(f"不明なベニュー: {unknown}。選べるのは {list(FEEDS)}", file=sys.stderr)
        return 2

    result = asyncio.run(run(venues, args.wait))

    print("\n=== まとめ ===")
    for name, v in result["venues"].items():
        v["verdict"] = verdict(v)
        print(f"  {name:12s} {v['verdict']}")
        print(f"               {v['note']}")

    out = REPO / "data" / "liquidation_feed_check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n結果を書きました: {out}")
    print("このファイルを共有してください(次の手順で記録を始めるベニューを決めます)。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
