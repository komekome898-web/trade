"""カード 4(アドバイザーの指摘 2): 読み口 diag_tables.py をそのまま呼ぶだけ(走らせ直しではない)。
(a) 悪い側の D1(前半・後半): families_r2 の <名前>_bad を --run で 1 本ずつ → diag_bad/<名前>.md
(b) D7(L-666 の一番不利な組み合わせ): --run <新しい形>_<側> --vs <元の形>_<側> を 3 通り(悪 − 良、良 − 良、悪 − 悪)
    組 = center の 5 種 × v37、R2 の門 2 種 × A1_center_4_3、R2_ratio_gate_rolling × D_ratio_gate12.96、門の 4 形 × v37(L-666 の元の比べ) → d7/<組>_<側>.md
    PYTHONPATH=src python3 docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/run_bad_d7.py
"""
import os
import subprocess
import sys

REPO = "/home/user/trade"
R = os.path.join(REPO, "docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/families_r2")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(REPO, "scripts/analysis/diag_tables.py")
PAIRS = [("A1_center_2_0.8", "v37"), ("A1_center_2_1", "v37"), ("A1_center_3_2", "v37"), ("A1_center_4_3", "v37"),
         ("A1_center_5_1", "v37"), ("R2_ratio_gate12.96_center_4_3", "A1_center_4_3"),
         ("R2_ratio_gate_rolling_center_4_3", "A1_center_4_3"), ("R2_ratio_gate_rolling", "D_ratio_gate12.96"),
         # L-666 の元の比べ(門の形を原典 v37 と比べる)。2026-10-05 にアドバイザーの前に足した
         ("R2_ratio_gate12.96_center_4_3", "v37"), ("R2_ratio_gate_rolling_center_4_3", "v37"),
         ("R2_ratio_gate_rolling", "v37"), ("D_ratio_gate12.96", "v37")]
SIDES = [("bad", "good"), ("good", "good"), ("bad", "bad")]


def call(args, out):
    if os.path.exists(out):
        return
    r = subprocess.run([sys.executable, TOOL, *args, "--out", out], cwd=REPO, env={**os.environ, "PYTHONPATH": "src"},
                       capture_output=True, text=True)
    print(os.path.basename(out), r.returncode, (r.stderr.strip().splitlines() or [""])[-1][:200], flush=True)


def main():
    os.makedirs(os.path.join(HERE, "diag_bad"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "d7"), exist_ok=True)
    for new, base in PAIRS:
        for sn, sb in SIDES:
            call(["--run", os.path.join(R, f"{new}_{sn}"), "--vs", os.path.join(R, f"{base}_{sb}")],
                 os.path.join(HERE, "d7", f"{new}__{sn}_vs_{base}__{sb}.md"))
    for d in sorted(os.listdir(R)):
        if d.endswith("_bad"):
            call(["--run", os.path.join(R, d)], os.path.join(HERE, "diag_bad", d[:-4] + ".md"))


if __name__ == "__main__":
    main()
