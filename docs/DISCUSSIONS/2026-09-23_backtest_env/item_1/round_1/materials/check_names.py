#!/usr/bin/env python3
"""Count, per table, words that could identify a target: tool / module / API
names (any line), clock times (any line), and the Japanese words that tell our
current state or a reproduction apart (note lines only; the header's column
word 「再現」 is the protocol's own word)."""
import re
import sys
from pathlib import Path
ROUND = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/home/user/trade/tests/bt/battery/item_1")
import i1_targets as TG  # noqa: E402

names = set()
for k, v in TG.TARGETS.items():
    names.add(k)
    names.add(k.replace("opp_", ""))
    if v.get("venv"):
        names.add(v["venv"].split("/")[-1])
names |= {"vectorbt", "vbt", "qlib", "finmarketpy", "findatapy", "pytrendfollow", "hftbacktest", "tardis", "pybotters",
          "backtesting.py", "qstrader", "vnpy", "slippage", "barter", "pysystemtrade", "read_timestamps", "load_unsealed",
          "read_candles", "load_sealed", "market_view", "run_backtest", "md5_of", "src/bot", "bot.research",
          "SealedDataError", "DataError", "PathRefused", "bot.bt", "Yahoo", "CCXT", "Alpaca", "Tardis"}
names = {n for n in names if n and n not in {"-", "c3", "c61", "c87", "c105"}}
pat = re.compile("|".join(re.escape(n) for n in sorted(names, key=len, reverse=True)), re.I)
clock = re.compile(r"\b\d{1,2}:\d{2}(:\d{2})?\b|\d{4}-\d{2}-\d{2}T\d{2}")
ja = re.compile("現状|再現|(?<!別々)の道具|模擬器")  # 「別々の道具 N 件」 in the fold note is generic
tot = 0
for p in sorted(ROUND.glob("表_*.md")):
    hits = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        for m in pat.finditer(line):
            hits.append((i, m.group(0)))
        for m in clock.finditer(line):
            hits.append((i, m.group(0)))
        if line.startswith("注記"):
            for m in ja.finditer(line):
                hits.append((i, m.group(0)))
    tot += len(hits)
    print(f"{p.name}\t{len(hits)}\t{hits[:10]}")
print("names checked:", len(names), "total hits:", tot)
