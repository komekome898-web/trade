"""本測定の族の枝を取り込んだ後の確かめ(SESSIONS.md の「受け取りで見ること」)。
本ごとに: 置き場のファイルがそろっているか・run.json の git が 5a69618a・report.json と run.json の params が
JOBS.md の JSON(MAIN_BASE + 上書き)を原典の値に上書きしたものと == か・足の本数の上限が 0 か・まとめの数。
    PYTHONPATH=src:scripts/simple python3 scripts/simple/receive_main.py [--tables] <族> [<族> ...]
--tables(L-903 の後の測定): 取引の行(trades.csv.gz・summary.json)と標準の表(diag_tables.md・diag_paths.md)も
そろっているか、取引の行の summary.json の閉じた取引の数が走らせの summary.json と同じか、表の境が CUT か(diag_tables.md に「後半の最初の日 <CUT>」の文字列。`--cut` の口を足した後の形)を見る。
"""
import json, os, sys
from main_jobs import CUT, FAMILIES, MAIN_BASE, OUT, TABLES, TRADES
from bot.strategy.matilda_simple import BASE_PARAMS

GIT = "5a69618ad8f1e7f4d3550e8807b01bd4b96a38b7"
NEED = ("fills.csv.gz", "signals.csv.gz", "summary.json", "run.json", "report.json")
NEED_TRADES = ("trades.csv.gz", "summary.json")
NEED_TABLES = ("diag_tables.md", "diag_paths.md")
args = sys.argv[1:]
tables = "--tables" in args
fams = [a for a in args if a != "--tables"]
bad = 0
for fam in fams:
    for name, over in FAMILIES[fam]:
        d = os.path.join(OUT, name)
        miss = [f for f in NEED if not os.path.isfile(os.path.join(d, f))]
        if miss:
            print(fam, name, "欠け", miss); bad += 1; continue
        run = json.load(open(os.path.join(d, "run.json"))); rep = json.load(open(os.path.join(d, "report.json")))
        exp = dict(BASE_PARAMS); exp.update(MAIN_BASE); exp.update(over)
        ok = run["git"] == GIT and run["params"] == exp and rep["params"] == exp and rep["bar_limit"] == 0
        bad += not ok
        if tables:
            tdir, gdir = os.path.join(TRADES, name), os.path.join(TABLES, name)
            miss = [os.path.join(tdir, f) for f in NEED_TRADES if not os.path.isfile(os.path.join(tdir, f))]
            miss += [os.path.join(gdir, f) for f in NEED_TABLES if not os.path.isfile(os.path.join(gdir, f))]
            if miss:
                print(fam, name, "表の欠け", miss); bad += 1; continue
            n_run = json.load(open(os.path.join(d, "summary.json"))).get("closed_trades")
            chk = json.load(open(os.path.join(tdir, "summary.json"))).get("check", {})
            n_tr = chk.get("closed_trades") if chk.get("matches_summary") is True else None
            cut_ok = f"後半の最初の日 {CUT}" in open(os.path.join(gdir, "diag_tables.md")).read()
            t_ok = n_run is not None and n_run == n_tr and cut_ok
            print(fam, name, "表", "OK" if t_ok else "違う", "閉じた取引", n_run, n_tr, "境", CUT if cut_ok else "違う")
            bad += not t_ok
        print(fam, name, "OK" if ok else "違う", "git", run["git"][:8], "秒", rep["run_sec"], "MB", rep["max_rss_mb"], json.dumps(rep["summary"], ensure_ascii=False))
print("違う・欠け", bad)
sys.exit(1 if bad else 0)
