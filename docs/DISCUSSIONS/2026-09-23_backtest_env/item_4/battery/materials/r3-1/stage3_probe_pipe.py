import os, sys, tempfile, json
sys.path[:0] = ["tests/bt/battery/item_4", "tests/bt/item_4", "src"]
import i4_scenes as S, i4w_decl as D
from bot.bt.pipeline import plan_pipeline, run_pipeline
files, ds = S._pipeline_files()
root = tempfile.mkdtemp(prefix="probe_")
for f in files:
    p = os.path.join(root, f["path"]); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(S.file_bytes(f))
KIND = {"bf_trades": "trade", "binance": "trade", "fx_ticks": "quote", "jpx_1m": "bar", "fx_1m": "bar"}
ins = [D.instrument(i["name"], i["price"], KIND[i["price"]], i["with"]) for i in S.INSTRUMENTS]
plan = plan_pipeline(root=root, datasets=ds, instruments=ins, strategy={"kind": "schedule", "orders": S.SCHEDULE},
                     purpose="動作確認", **D.kw())
res = run_pipeline(plan, runs_dir=tempfile.mkdtemp())
for side, m in res.range.items():
    for n, r in m.items():
        print(side, n, [(f["t_ns"] - S.T0, f["side"], f["px"], f["qty"]) for f in r.fills])
print("exp", {n: [(f["t_ns"] - S.T0, f["side"], f["px"]) for f in v] for n, v in S._PF.items()})
print(dict(res.events_read))
