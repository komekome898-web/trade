"""kabu STATION API connectivity check + ON1 pre-LIVE verification (port 18081).

Run on the Windows PC with kabu STATION started and logged in.  Stages:

  1. (default)        read-only: /token -> /symbolname/future (micro, central
                      month) -> /board.  Proves password, plan, and data access.
  2. --entry-test     sends ONE 引成 buy of 1 micro contract to the 検証 port —
                      the exact ON1 entry payload.  Run during the day session
                      (12:00-15:44 is fine).
  3. --exit-test      sends ONE plain market sell (返済) — the exact ON1 exit
                      payload.  THE question this answers (docs/ON1_LIVE_PLAN.md,
                      spec unknown #1): run it at 8:40-8:44 before the open and
                      see whether kabu STATION accepts a pre-open market order.
                      Accepted -> the 8:40 exit design works.  Rejected (4xx) ->
                      report the error code back to the research session; the
                      exit moves to 9:00.

SAFETY: order tests REFUSE to run against the production port 18080, no
override.  This script must never be pointed at real money — arming LIVE has
its own three-gate procedure and is not this script's job.

NOTE: kabu STATION keeps SEPARATE API passwords for 本番 and 検証.  This script
reads KABU_API_PASSWORD from .env; while testing against 18081 set it to the
検証用 password (kabu STATION: 設定 -> API -> 検証用パスワード).
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv                                    # noqa: E402

from bot.jpx.kabu_client import (                                 # noqa: E402
    KabuClient, KabuError, KabuNetworkError, OrderStateUnknown,
    PRODUCTION_PORT, VERIFICATION_PORT,
)
from bot.jpx import on1_executor as on1                           # noqa: E402
from bot.settings import Secret                                   # noqa: E402


def central_month() -> str:
    month, _row, reason = on1.resolve_central_month(
        ROOT / "data" / "jpx_daily" / "nk225_sessions.csv", date.today())
    if month:
        return month
    # No local JPX data (fresh machine): fall back to the next quarterly month.
    print(f"  (central month from JPX csv unavailable: {reason}; "
          "falling back to the next quarterly month)")
    today = date.today()
    year, quarter_month = today.year, ((today.month - 1) // 3 + 1) * 3
    if today >= on1.sq_date(f"{year}{quarter_month:02d}"):
        quarter_month += 3
        if quarter_month > 12:
            year, quarter_month = year + 1, 3
    return f"{year}{quarter_month:02d}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=VERIFICATION_PORT,
                    help=f"default {VERIFICATION_PORT} (検証)")
    ap.add_argument("--entry-test", action="store_true",
                    help="send the ON1 entry payload (引成 buy) to the 検証 port")
    ap.add_argument("--exit-test", action="store_true",
                    help="send the ON1 exit payload (market sell) to the 検証 port; "
                         "run at 8:40-8:44 to answer the pre-open question")
    args = ap.parse_args()

    order_test = args.entry_test or args.exit_test
    if order_test and args.port == PRODUCTION_PORT:
        print(f"REFUSED: order tests never run against the production port "
              f"{PRODUCTION_PORT}. No override exists.")
        return 1

    load_dotenv(ROOT / ".env")
    import os
    password = os.environ.get("KABU_API_PASSWORD", "")
    if not password:
        print("KABU_API_PASSWORD is not set in .env — set it and rerun "
              "(検証用パスワード while testing port 18081).")
        return 1

    client = KabuClient(Secret(password), port=args.port)
    print(f"port {args.port} ({'検証' if args.port == VERIFICATION_PORT else '本番'})")

    # -- stage 1: read-only ------------------------------------------------
    try:
        client.issue_token()
        print("1a token          : OK")
    except (KabuError, KabuNetworkError) as exc:
        print(f"1a token          : FAILED — {exc}")
        print("   kabu STATION is not running / not logged in, the API plan is "
              "not enabled, or the password does not match this port.")
        return 1

    month = central_month()
    try:
        info = client.symbol_name_future(on1.FUTURE_CODE_MICRO, int(month))
        symbol, name = info.get("Symbol"), info.get("SymbolName")
        print(f"1b symbolname     : OK — {month} -> {symbol} {name}")
    except (KabuError, KabuNetworkError) as exc:
        print(f"1b symbolname     : FAILED — {exc}")
        return 1
    if on1.MICRO_NAME_MARKER not in str(name or ""):
        print(f"1b               : WARNING — SymbolName has no 「マイクロ」; "
              "the ON1 sanity check would refuse this. Report it back.")

    try:
        board = client.board(str(symbol), on1.EXCHANGE_DAY_SESSION)
        print(f"1c board          : OK — CurrentPrice {board.get('CurrentPrice')!r} "
              f"({board.get('CurrentPriceTime') or 'no time'})")
    except (KabuError, KabuNetworkError) as exc:
        print(f"1c board          : FAILED — {exc}  (outside trading hours a "
              "missing price can be normal; a 4xx here is not)")

    if not order_test:
        print("read-only checks done. Order tests: --entry-test (day session) / "
              "--exit-test (8:40-8:44).")
        return 0

    # -- stage 2/3: one order to the 検証 port ----------------------------
    job = on1.ENTRY if args.entry_test else on1.EXIT
    payload = {
        "Symbol": str(symbol),
        "Exchange": on1.EXCHANGE_DAY_SESSION,
        "TradeType": on1.TRADE_TYPE_NEW if job == on1.ENTRY else on1.TRADE_TYPE_CLOSE,
        "TimeInForce": on1.TIME_IN_FORCE_FAK,
        "Side": on1.SIDE_BUY if job == on1.ENTRY else on1.SIDE_SELL,
        "Qty": on1.MAX_QTY,
        "FrontOrderType": (on1.FRONT_ORDER_TYPE_MARKET_ON_CLOSE if job == on1.ENTRY
                           else on1.FRONT_ORDER_TYPE_MARKET),
        "Price": 0,
        "ExpireDay": on1.EXPIRE_DAY_TODAY,
    }
    if job == on1.EXIT:
        payload["ClosePositionOrder"] = on1.CLOSE_POSITION_ORDER_OLDEST
    print(f"2  sending the ON1 {job} payload to the 検証 port: {payload}")
    try:
        result = client.send_future_order(payload)
        print(f"2  {job}-test      : ACCEPTED — OrderId {result.get('OrderId')!r}")
        if job == on1.EXIT:
            print("   => a pre-open market order is accepted; the 8:40 exit "
                  "design stands (confirm it shows State in /orders).")
        try:
            rows = client.orders(symbol=str(symbol))
            for r in rows[-3:]:
                print(f"   /orders: ID {r.get('ID')!r} State {r.get('State')!r} "
                      f"CumQty {r.get('CumQty')!r}")
        except (KabuError, KabuNetworkError) as exc:
            print(f"   /orders read failed: {exc}")
    except KabuError as exc:
        print(f"2  {job}-test      : REJECTED — HTTP {exc.status_code} "
              f"code={exc.code}: {exc.message}")
        print("   Copy this line back to the research session (a rejection is "
              "an answer, not a failure — especially for the 8:40 exit case).")
    except (OrderStateUnknown, KabuNetworkError) as exc:
        print(f"2  {job}-test      : NO ANSWER — {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
