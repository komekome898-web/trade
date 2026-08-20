#!/usr/bin/env python3
"""Read-only bitFlyer API verification. Sends NO orders.

Run from an environment with network access to api.bitflyer.com:
    python scripts/check_api.py

Verifies: connectivity, market list + min order sizes context, ticker,
exchange health, and (if credentials are configured) authentication,
key permissions (fails loudly if withdrawal permission is present),
balance and open orders.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bot.exchange.bitflyer_client import BitflyerClient, BitflyerError, NetworkError  # noqa: E402
from bot.settings import load_settings  # noqa: E402

# Known minimum order sizes per official docs — re-verify against docs when run.
KNOWN_MIN_SIZES = {"BTC_JPY": 0.001, "ETH_JPY": 0.01, "XRP_JPY": 0.1, "FX_BTC_JPY": 0.01}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root)
    client = BitflyerClient(settings.api_key, settings.api_secret)
    ok = True

    print("== Public API ==")
    try:
        markets = client.markets()
        print(f"markets: OK ({len(markets)} products)")
        ticker = client.ticker(settings.product_code)
        ltp = float(ticker["ltp"])
        print(f"ticker {settings.product_code}: ltp={ltp} bid={ticker['best_bid']} ask={ticker['best_ask']}")
        health = client.health(settings.product_code)
        print(f"health: {health.get('status')}")
        min_size = KNOWN_MIN_SIZES.get(settings.product_code)
        if min_size:
            print(f"min order size (per docs, re-verify): {min_size} -> "
                  f"min notional ~= {min_size * ltp:.0f} JPY")
    except (BitflyerError, NetworkError) as e:
        print(f"PUBLIC API FAILED: {e}")
        return 1

    if not settings.api_key:
        print("\nNo API key configured (.env) — skipping private checks.")
        return 0

    print("\n== Private API (read-only) ==")
    try:
        perms = client.get_permissions()
        withdrawal = [p for p in perms if "withdraw" in p.lower() or "sendcoin" in p.lower()
                      or "sendmoney" in p.lower()]
        if withdrawal:
            print(f"DANGER: API key has withdrawal-related permissions: {withdrawal}")
            print("Re-issue the key WITHOUT withdrawal permission before continuing.")
            ok = False
        else:
            print(f"permissions: OK, no withdrawal permission ({len(perms)} endpoints allowed)")
        balance = client.get_balance()
        jpy = next((b for b in balance if b.get("currency_code") == "JPY"), None)
        print(f"balance JPY: {jpy}")
        orders = client.get_child_orders(settings.product_code, child_order_state="ACTIVE")
        print(f"active orders: {len(orders)}")
    except (BitflyerError, NetworkError) as e:
        print(f"PRIVATE API FAILED: {e}")
        ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
