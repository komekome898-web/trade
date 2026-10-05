"""カード 2 の D7(アドバイザーの指摘 4): 足 15・5 分それぞれで、基準 weak_f<足>_close_a に対し、変種を
diag_tables.py の --vs で比べる(走らせ直しではない。読み口をそのまま呼ぶ)。
  --run <変種> --vs <基準>。出力 d7/<足>_<変種>.md・.json。
    PYTHONPATH=src python3 docs/RESEARCH/cards/c2_owner_xvenue_wick/redo2_2026-10-05/run_d7.py
"""
import os
import subprocess
import sys

REPO = "/home/user/trade"
RUNS = os.path.join(REPO, "docs/RESEARCH/cards/c2_owner_xvenue_wick/limit_sim/runs")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "d7")
TOOL = os.path.join(REPO, "scripts/analysis/diag_tables.py")
VARIANTS = {
    15: ["close_a_time6", "close_a_time7", "close_a_time8", "close_a_time9", "close_a_time10", "close_a_time11",
         "close_a_time12", "close_a_time24", "close_a_stop1", "close_a_stop2", "close_a_stop3", "gate_close_a",
         "rgate_close_a", "close_a_refjoin", "limit_a_good", "close_b"],
    5: ["close_a_time6", "close_a_time12", "close_a_time24", "close_a_stop1", "close_a_stop2", "close_a_stop3",
        "gate_close_a", "rgate_close_a", "close_a_refjoin", "limit_a_good", "close_b"],
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for foot, vs in VARIANTS.items():
        base = os.path.join(RUNS, f"weak_f{foot}_close_a")
        for v in vs:
            out = os.path.join(OUT, f"f{foot}_{v}.md")
            if os.path.exists(out):
                continue
            cmd = [sys.executable, TOOL, "--run", os.path.join(RUNS, f"weak_f{foot}_{v}"), "--vs", base, "--out", out]
            r = subprocess.run(cmd, cwd=REPO, env={**os.environ, "PYTHONPATH": "src"}, capture_output=True, text=True)
            print(foot, v, r.returncode, (r.stderr.strip().splitlines() or [""])[-1][:200], flush=True)


if __name__ == "__main__":
    main()
