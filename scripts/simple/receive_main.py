"""本測定の族の枝を取り込んだ後の確かめ(SESSIONS.md の「受け取りで見ること」)。
本ごとに: 置き場のファイルがそろっているか・run.json の git が 5a69618a・report.json と run.json の params が
JOBS.md の JSON(MAIN_BASE + 上書き)を原典の値に上書きしたものと == か・足の本数の上限が 0 か・まとめの数。
    PYTHONPATH=src:scripts/simple python3 scripts/simple/receive_main.py <族> [<族> ...]
"""
import json, os, sys
from main_jobs import FAMILIES, MAIN_BASE, OUT
from bot.strategy.matilda_simple import BASE_PARAMS

GIT = "5a69618ad8f1e7f4d3550e8807b01bd4b96a38b7"
NEED = ("fills.csv.gz", "signals.csv.gz", "summary.json", "run.json", "report.json")
bad = 0
for fam in sys.argv[1:]:
    for name, over in FAMILIES[fam]:
        d = os.path.join(OUT, name)
        miss = [f for f in NEED if not os.path.isfile(os.path.join(d, f))]
        if miss:
            print(fam, name, "欠け", miss); bad += 1; continue
        run = json.load(open(os.path.join(d, "run.json"))); rep = json.load(open(os.path.join(d, "report.json")))
        exp = dict(BASE_PARAMS); exp.update(MAIN_BASE); exp.update(over)
        ok = run["git"] == GIT and run["params"] == exp and rep["params"] == exp and rep["bar_limit"] == 0
        bad += not ok
        print(fam, name, "OK" if ok else "違う", "git", run["git"][:8], "秒", rep["run_sec"], "MB", rep["max_rss_mb"], json.dumps(rep["summary"], ensure_ascii=False))
print("違う・欠け", bad)
sys.exit(1 if bad else 0)
