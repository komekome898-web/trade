"""段 2 の読み R4 の 1(STAGE2_MATERIALS §9.1、K-342・K-353。L-963「1を裏で走らせながら」)。
基準の引数(と break_dist だけ変えた引数)を同じコードで走らせ直し、取引の始まり(1 段目の約定)ごとに、
その時点の線(snap の bu・bd)と、k = 1〜8 個前の線の候補(_up[-k]・_dn[-k])と range_max2・range_min2・幅を書き出す。
戦略の判断には触らない(_apply_fill の前に値を写すだけ)。新しい引数の走らせではない(段 1 の 3 本と同じ引数)。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/stage2/r4_lines_dump.py <出力の置き場> '<引数の JSON>'
"""
import csv
import json
import os
import sys

sys.path.insert(0, "scripts/simple")
import run_one  # noqa: E402
from bot.bt.simple import run  # noqa: E402
from bot.strategy.matilda_simple import BASE_PARAMS, MatildaSimple  # noqa: E402

K = 8


class Dump(MatildaSimple):
    rows = []

    def _apply_fill(self, f, start, roles0):
        if self._pos == 0:
            sn, ind = self._snap, self.ind
            r = {"start": start, "side": 1 if f["side"] == "buy" else -1, "px": float(f["px"]),
                 "bu": sn["bu"], "bd": sn["bd"], "rmax2": ind["range_max2"], "rmin2": ind["range_min2"],
                 "width": ind["width"], "center": sn["center"]}
            for k in range(1, K + 1):
                r[f"up{k}"] = self._up[-k] if len(self._up) >= k else None
                r[f"dn{k}"] = self._dn[-k] if len(self._dn) >= k else None
            Dump.rows.append(r)
        return super()._apply_fill(f, start, roles0)


out, over = sys.argv[1], json.loads(sys.argv[2])
os.makedirs(out, exist_ok=True)
p = dict(BASE_PARAMS)
p.update(over)
run(run_one._bars(None), Dump(p), out_dir=out, tick=1.0, meta={"params": p, "seal": run_one.SEAL})
with open(os.path.join(out, "lines.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(Dump.rows[0]))
    w.writeheader()
    w.writerows(Dump.rows)
print(len(Dump.rows))
