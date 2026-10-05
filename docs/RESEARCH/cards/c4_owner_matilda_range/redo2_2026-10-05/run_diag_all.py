"""カード 4 の分析のやり直し(L-696・L-698): 保存済みの走らせの全部に、試験のある読み口 diag_tables.py を
そのまま当てる(走らせ直しではない)。表は diag_tables が出し、この台本は呼ぶだけ。

- カードの形(成行): measure/<変種>/ の 20 本。--run だけ。
- 指値の再現: limit_sim/families_r2/ の組(<名前>_good と <名前>_bad は --run good --bad bad、D8)。
  R2・READ* は走らせではないので外す。limit_sim/families/・v37_full/ は同じ引数の前の版なので当てない。
- --valid-min は渡さない(P: 前提の文に数の有効期間が無いので、根拠のない値を置かない。A-12)。合図 → 建ての
  分の分布(25・50・75・90・99% と最大)は値なしでも出る。

出力: このフォルダの diag/<名前>.md・.json。
    PYTHONPATH=src python3 docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/run_diag_all.py
"""
import os
import subprocess
import sys

REPO = "/home/user/trade"
C2 = os.path.join(REPO, "docs/RESEARCH/cards/c4_owner_matilda_range")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diag")
TOOL = os.path.join(REPO, "scripts/analysis/diag_tables.py")


def call(name, run, bad=None):
    out = os.path.join(OUT, name + ".md")
    if os.path.exists(out):
        return
    cmd = [sys.executable, TOOL, "--run", run, "--out", out]
    if bad:
        cmd += ["--bad", bad]
    r = subprocess.run(cmd, cwd=REPO, env={**os.environ, "PYTHONPATH": "src"}, capture_output=True, text=True)
    print(name, r.returncode, (r.stderr.strip().splitlines() or [""])[-1][:200], flush=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    for v in sorted(os.listdir(os.path.join(C2, "measure"))):
        p = os.path.join(C2, "measure", v)
        if os.path.isdir(p):
            call("card_" + v, p)
    runs = os.path.join(C2, "limit_sim/families_r2")
    names = sorted(d for d in os.listdir(runs) if not d.startswith("READ") and d != "R2")
    done = set()
    for d in names:
        if d in done:
            continue
        if d.endswith("_good") and d[:-5] + "_bad" in names:
            call(d[:-5], os.path.join(runs, d), os.path.join(runs, d[:-5] + "_bad"))
            done |= {d, d[:-5] + "_bad"}
        elif d.endswith("_bad") and d[:-4] + "_good" in names:
            continue
        else:
            call(d, os.path.join(runs, d))
            done.add(d)


if __name__ == "__main__":
    main()
