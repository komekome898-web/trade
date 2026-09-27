"""Repro (synthetic data only, 2026-09-27 k1 env fixes): does load() read a ledger-sealed file's bytes before it refuses it?

Usage: PYTHONPATH=src python3 scripts/k1_newenv_fix_seal_repro.py <a scratch folder>
"""
import json, os, sys, tempfile
import bot.bt.data.loader as L
from bot.bt.data import load, SealedRangeError

root = tempfile.mkdtemp(prefix="seal_repro_", dir=sys.argv[1])
os.makedirs(os.path.join(root, "backtest_data", "x"))
os.makedirs(os.path.join(root, "backtest_data", "phase2_sealed", "U"))
f = os.path.join(root, "backtest_data", "x", "f.csv")
open(f, "w").write("ts,o,h,l,c,vol\n2020-01-01T00:00:00,1,2,0.5,1.5,1\n")
json.dump({"unit": "U", "forward_start": "2020-01-01T00:00:00+00:00",
           "files": [{"path": "backtest_data/x/f.csv", "time_column": "ts", "seal_from_ts": "2020-01-01T00:00:00+00:00"}]},
          open(os.path.join(root, "backtest_data", "phase2_sealed", "U", "SEALED.json"), "w"))
events = []
real_f = os.path.realpath(f)
sys.addaudithook(lambda ev, a: events.append(("open", os.path.realpath(os.fsdecode(a[0])))) if ev == "open" and not isinstance(a[0], int) and a[0] is not None and os.path.realpath(os.fsdecode(a[0])) == real_f else None)
orig = L.hashlib.sha256
def spy(b=b""):
    if b:
        events.append(("sha256 of bytes", len(b)))
    return orig(b)
L.hashlib.sha256 = spy
spec = {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "X", "asset": "crypto",
        "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
        "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "vol"},
        "bar": {"interval_s": 1, "label": "start"}, "key": "start"}
try:
    load(root, [{"name": "d", "paths": ["backtest_data/x/f.csv"], "spec": spec}])
    print("NOT refused")
except SealedRangeError as exc:
    events.append(("refused", type(exc).__name__))
print("file size", os.path.getsize(f))
for e in events:
    print(e[0], e[1] if e[0] != "open" else os.path.relpath(e[1], root))
