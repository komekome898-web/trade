"""L-967・L-968 の利確の位置の読み (1) の材料。基準の引数を同じコードで走らせ直し、足が閉じるごとの線(snap: 中心・ボラ・
上下のブレイクの線)と、取引の始まり(1 段目の約定)ごとの値を書き出す。戦略の判断には触らない(値を写すだけ)。
出力: <置き場>/snaps.npz(end = 線を作った足の終わりの ns = 次の足の始まり・center・vola・bu・bd。線が無いときは nan)と entries.csv。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/stage2/r7_snap_dump.py <置き場> '<引数の JSON>'
"""
import csv
import json
import os
import sys
from array import array

import numpy as np

sys.path.insert(0, "scripts/simple")
import run_one  # noqa: E402
from bot.bt.simple import run  # noqa: E402
from bot.strategy.matilda_simple import BASE_PARAMS, MatildaSimple  # noqa: E402

NAN = float("nan")


class Dump(MatildaSimple):
    cols = {k: array("d") for k in ("center", "vola", "bu", "bd")}
    ends = array("q")
    rows = []

    def _close_window(self):
        end = self._win["end"]
        super()._close_window()
        sn = self._snap
        if sn is not None:
            Dump.ends.append(end)
            for k in ("center", "vola", "bu", "bd"):
                v = sn[k]
                Dump.cols[k].append(NAN if v is None else float(v))

    def _apply_fill(self, f, start, roles0):
        if self._pos == 0:
            Dump.rows.append({"start": start, "side": 1 if f["side"] == "buy" else -1, "px": float(f["px"]), "qty": float(f["qty"])})
        return super()._apply_fill(f, start, roles0)


out, over = sys.argv[1], json.loads(sys.argv[2])
os.makedirs(out, exist_ok=True)
p = dict(BASE_PARAMS)
p.update(over)
run(run_one._bars(None), Dump(p), out_dir=out, tick=1.0, meta={"params": p, "seal": run_one.SEAL})
np.savez(os.path.join(out, "snaps.npz"), end=np.frombuffer(Dump.ends, dtype=np.int64),
         **{k: np.frombuffer(v, dtype=np.float64) for k, v in Dump.cols.items()})
with open(os.path.join(out, "entries.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(Dump.rows[0]))
    w.writeheader()
    w.writerows(Dump.rows)
print(len(Dump.ends), len(Dump.rows))
