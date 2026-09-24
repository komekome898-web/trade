#!/usr/bin/env python3
"""Tally the cat8_repo_fetch.sh steps of a cat8 raw log (audit 56: the N/M of a
multi-repository candidate must come from the helper's own output, not from prose).

Usage: python3 scripts/cat8_fetch_tally.py <raw log> [--prefix th2-net/]

For each step whose command line runs scripts/cat8_repo_fetch.sh it prints the repo,
the step's exit code, files_in_tree(N), the skipped (>1 MB) and lfs_pointer names,
downloaded_bytes and checked_out_bytes, then the totals. Exits non-zero when a step's
output was cut by cat8_step.py (--keep too small), when a repo appears twice with
different values in any field, or when a successful step lacks one of the helper's count lines.
"""
import argparse
import re
import sys

ap = argparse.ArgumentParser()
ap.add_argument("log")
ap.add_argument("--prefix", default="")
a = ap.parse_args()

lines = open(a.log, encoding="utf-8", errors="replace").read().split("\n")
steps, cur = [], None
for ln in lines:
    if ln.startswith("--- ") and " rc=" in ln:
        cur = {"head": ln, "cmd": "", "out": []}
        steps.append(cur)
    elif cur is not None and ln.startswith("$ ") and not cur["cmd"]:
        cur["cmd"] = ln[2:]
    elif cur is not None:
        cur["out"].append(ln)

rows, errs = {}, []
stopped_by = None  # first repo that ended the fetching with exit 5 or 6
for s in steps:
    if "cat8_repo_fetch.sh" not in s["cmd"]:
        continue
    m = re.search(r"cat8_repo_fetch\.sh\s+(\S+)", s["cmd"])
    repo = m.group(1) if m else "?"
    if not repo.startswith(a.prefix):
        continue
    rc = re.search(r" rc=(\S+)", s["head"]).group(1)
    out = s["out"]
    text = "\n".join(out)
    r = {"rc": rc, "N": None, "skipped": [], "lfs": [], "dl": None, "co": None}
    for ln in out:
        if ln.startswith("files_in_tree(N): "):
            r["N"] = int(ln.split(": ", 1)[1])
        elif ln.startswith("  skipped: "):
            r["skipped"].append(ln[len("  skipped: "):])
        elif ln.startswith("  lfs_pointer: "):
            r["lfs"].append(ln[len("  lfs_pointer: "):])
        elif ln.startswith("downloaded_bytes: "):
            r["dl"] = int(ln.split(": ", 1)[1])
        elif ln.startswith("checked_out_bytes(without .git): "):
            r["co"] = int(ln.split(": ", 1)[1])
    if re.search(r"^\[出力は \d+ 文字。先頭 \d+ 文字だけを残した\]$", text, re.M):
        errs.append("%s: 出力が切られている(cat8_step.py の --keep を大きくして打ち直す)" % repo)
    m = re.search(r"blobs_not_downloaded\(>1MB\): (\d+)", text)
    if m and int(m.group(1)) != len(r["skipped"]):
        errs.append("%s: skipped の件数 %s と行の数 %d が合わない" % (repo, m.group(1), len(r["skipped"])))
    m = re.search(r"lfs_pointers\(not content\): (\d+)", text)
    if m and int(m.group(1)) != len(r["lfs"]):
        errs.append("%s: lfs_pointer の件数 %s と行の数 %d が合わない" % (repo, m.group(1), len(r["lfs"])))
    if rc == "0" and (r["N"] is None or r["co"] is None or not m):
        errs.append("%s: 終了コード 0 なのに件数の行が欠けている" % repo)
    if repo in rows and rows[repo] != r:
        diff = [k for k in r if rows[repo][k] != r[k]]
        errs.append("%s: 2 回打たれて結果が違う(違う項目: %s)" % (repo, ", ".join(diff)))
    if stopped_by and repo != stopped_by:
        errs.append("%s: 終了コード 5・6(%s)で取得をやめたあとに打たれている" % (repo, stopped_by))
    if rc in ("5", "6") and not stopped_by:
        stopped_by = repo
    rows[repo] = r

ok = [r for r in rows.values() if r["rc"] == "0"]


def totals():
    print("== リポジトリ %d 件(終了コード 0 = %d / 4 = %d / 5・6 は下の行 / そのほか = 取れなかった = %d)" % (
        len(rows), len(ok), sum(1 for r in rows.values() if r["rc"] == "4"),
        sum(1 for r in rows.values() if r["rc"] not in ("0", "4", "5", "6"))))
    print("== 終了コード 5(取った量の和が上限で取らなかった) = %d / 6(置き場か和のファイルの誤りで取らなかった) = %d" % (
        sum(1 for r in rows.values() if r["rc"] == "5"), sum(1 for r in rows.values() if r["rc"] == "6")))
    print("== 終了コード 0 の N の和 = %d / skipped の和 = %d / lfs_pointer の和 = %d / downloaded_bytes の和 = %d" % (
        sum(r["N"] or 0 for r in ok), sum(len(r["skipped"]) for r in ok), sum(len(r["lfs"]) for r in ok),
        sum(r["dl"] or 0 for r in rows.values())))
    print("== 誤り %d 件" % len(errs))


# Totals first and last, so a cut output still shows them once (audit 57).
totals()
print("repo\trc\tN\tskipped\tlfs_pointer\tdownloaded_bytes\tchecked_out_bytes")
for repo, r in rows.items():
    print("%s\t%s\t%s\t%d\t%d\t%s\t%s" % (repo, r["rc"], r["N"], len(r["skipped"]), len(r["lfs"]), r["dl"], r["co"]))
for repo, r in rows.items():
    for n in r["skipped"]:
        print("skipped\t%s\t%s" % (repo, n))
    for n in r["lfs"]:
        print("lfs_pointer\t%s\t%s" % (repo, n))
for e in errs:
    print("ERR " + e)
totals()
# Not "---": cat8_step.py prefixes such output lines with "| " (audit 58).
print("== 集計の終わり(誤り %d 件)" % len(errs))
sys.exit(1 if errs else 0)
