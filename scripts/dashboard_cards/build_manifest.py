"""backtest_runs_shared/cards/manifest.json を作る(各変種の provenance.json と git の測定出力の一覧から)。

    python3 scripts/dashboard_cards/build_manifest.py [--logs <ログの置き場>]...
全変種 = git の docs/RESEARCH/cards/c*/measure/*/ にある変種 + c4 の limit_sim/v37_full の good・bad。
書き出しが無いものは status を not_exported とし、理由(ログの最後の行)を書く。対象外は reason を書く。
"""
from __future__ import annotations

import argparse
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CARDS = os.path.join(ROOT, "docs/RESEARCH/cards")
OUT = os.path.join(ROOT, "backtest_runs_shared", "cards")
EXCLUDED = [
    {"card": "c3_yen_premium_revert", "variant": "measure_limit/{1h,1d,1w}", "status": "excluded",
     "reason": "対象外: 台本 scratchpad/w4/limit/limit_core.py がリポジトリに無い"},
    {"card": "c9_liquidation_cascade", "variant": "-", "status": "excluded", "reason": "対象外: 測定が無い(文書のみ)"},
    {"card": "c4_owner_matilda_range", "variant": "m_b{1,5}_w*_e*_* のうち git に出力が無い 114 個", "status": "excluded",
     "reason": "対象外: git に出力がある変種だけを対象にする(リードの判断)"},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", action="append", default=[])
    a = ap.parse_args()
    want = []
    for d in sorted(glob.glob(f"{CARDS}/c[1-8]_*/measure/*/")):
        want.append((d.split("/")[-4], os.path.basename(d.rstrip("/"))))
    want += [("c4_owner_matilda_range", "limit_v37_good"), ("c4_owner_matilda_range", "limit_v37_bad")]
    variants, tot = [], 0
    for cid, v in want:
        d = os.path.join(OUT, cid, v)
        pf = os.path.join(d, "provenance.json")
        if not os.path.exists(pf):
            why = "未実行または失敗"
            for lg in a.logs:
                f = glob.glob(os.path.join(lg, f"{cid[:2]}_{v}.log"))
                if f:
                    why = "ログの最後: " + open(f[0], errors="replace").read().strip().splitlines()[-1][:300]
            variants.append({"card": cid, "variant": v, "status": "not_exported", "display_ok": False, "reason": why})
            continue
        p = json.load(open(pf))
        sizes = {f: os.path.getsize(os.path.join(d, f)) for f in sorted(os.listdir(d))}
        tot += sum(sizes.values())
        variants.append({"card": cid, "variant": v, "status": "exported", "display_ok": p["display_ok"],
                         "verified_items": p.get("verified_items", []), "not_verified": p.get("not_verified", []),
                         "n_trades": p["n_trades"], "period": p["period"], "file_bytes": sizes,
                         "seconds": p["seconds"].get("research_run"),
                         "reason": None if p["display_ok"] else "照合が合わない(表示しない)。provenance.json の checks に差"})
    m = {"version": 1, "git_sha": None, "total_bytes": tot, "variants": variants, "excluded": EXCLUDED}
    import subprocess
    m["git_sha"] = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    json.dump(m, open(os.path.join(OUT, "manifest.json"), "w"), ensure_ascii=False, indent=1)
    print(len(variants), "変種", sum(1 for x in variants if x["status"] == "exported"), "書き出し済み", tot, "bytes")


if __name__ == "__main__":
    main()
