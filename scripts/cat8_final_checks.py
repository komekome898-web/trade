#!/usr/bin/env python3
"""区分 8 の回の最後に、起動文 §7 の 4 つの検査と大きさを打ち、出力の全文を報告の末尾に書き足す道具(調査班が最後に 1 回打つ)。

置いた理由(2026-09-26、35 回目の検収 監査 134 回目の指摘 1): 起動文 §7 で「1〜4 の出力を全部貼る」と書いても、
24〜26・32・35 回目に 2〜4 の出力が報告に貼られなかった。規則ではなく道具で貼る。

使い方:
  python3 scripts/cat8_final_checks.py --round <回> [--report docs/DATA/SCAN_2026-09-23_tools_cat8.md]

報告の末尾に `### 受け入れ検査の出力(道具が貼った)` の小節を 1 つ足す。打ったコマンドと出力をそのまま書く。
検査 4(過去の節から消えた行)は HEAD との差で数えるので、この道具が書き足す前に打つ。
"""
import argparse, pathlib, subprocess

ap = argparse.ArgumentParser()
ap.add_argument("--round", type=int, required=True)
ap.add_argument("--report", default="docs/DATA/SCAN_2026-09-23_tools_cat8.md")
a = ap.parse_args()
n = a.round
logs = " ".join("docs/DATA/probes/20260923_tools_8_run%d.log" % i for i in range(1, n + 1))
log = "docs/DATA/probes/20260923_tools_8_run%d.log" % n
cmds = [
    "python3 scripts/check_scan_report.py %s %s" % (a.report, logs),
    "python3 scripts/cat8_ledger.py check-elements %s --round %d" % (a.report, n),
    'python3 scripts/cat8_ledger.py check "" %s' % log,
    "git diff -U0 HEAD -- %s | grep '^-[^-]' | wc -l" % a.report,
    "wc -c %s %s" % (a.report, log),
]
HEAD = "### 受け入れ検査の出力(道具が貼った)"
# 打ち直し(報告を直したあとにもう一度打つ)のとき、この回の節に前に貼った小節を消してから貼る
# (2026-09-26 監査 135 回目の指摘 2: 追記だけだと古い出力が残って 2 段になる)。消すのは、
# この回の節の見出しより後ろにある、この道具の見出しから末尾まで(まだコミットしていない部分)だけ。
text = pathlib.Path(a.report).read_text()
sec = text.rfind("\n## 区分8 — %d 回目の実行" % n)
old = text.find("\n" + HEAD, sec if sec >= 0 else len(text))
if sec >= 0 and old >= 0:
    pathlib.Path(a.report).write_text(text[:old].rstrip("\n") + "\n")
    print("[cat8_final_checks] 前に貼った小節を消して貼り直す")
out = ["", HEAD, "",
       "`scripts/cat8_final_checks.py --round %d` が打った。コマンドと出力の全文。" % n, ""]
for c in cmds:
    p = subprocess.run(["bash", "-c", c], capture_output=True, text=True, errors="replace")
    out += ["```", "$ " + (c if len(c) < 400 else c[:200] + " … (生ログ 1〜%d 本)" % n), (p.stdout + p.stderr).rstrip("\n"), "```", ""]
with open(a.report, "a") as f:
    f.write("\n".join(out))
print("\n".join(out))
