#!/usr/bin/env python3
"""Build the file list that scripts/cat8_search.py reads, from a directory, so the list is
the whole directory and not a hand-trimmed subset (audit 66, finding 4).

Usage: python3 scripts/cat8_mklist.py --root <dir> --out <list file>
                                      [--exclude <path relative to root>=<reason> ...]
                                      [--add <extra file> ...]

Takes every file under --root (`git ls-files` when --root is a git work tree, otherwise a
walk that skips .git), drops only the files named with --exclude (each with its reason,
printed), appends the --add files (for example a file over 1 MB fetched another way), and
writes the list one path per line. Prints every excluded and added name and the footer
`cat8_mklist: complete out=<list> in_root=R added=A absent=B excluded=X listed=L`
(L = R + A - X; the source's N is R + A + B, of which X + B are not read).
An --exclude that names no file under the root stops with exit code 1.
"""
import argparse
import os
import subprocess
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--root", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--exclude", action="append", default=[])
ap.add_argument("--add", action="append", default=[])
ap.add_argument("--absent", action="append", default=[],
                help="<path>=<reason>: a file of the source tree that is not under --root and not added "
                     "(for example an image over 1 MB the fetch helper did not download). Counted in N, not listed.")
a = ap.parse_args()

root = os.path.abspath(a.root)
if os.path.isdir(os.path.join(root, ".git")):
    out = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True, check=True).stdout
    rel = [p.decode("utf-8", "surrogateescape") for p in out.split(b"\0") if p]
else:
    rel = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x != ".git"]
        for f in files:
            rel.append(os.path.relpath(os.path.join(d, f), root))
rel_set = set(rel)

excl = {}
for e in a.exclude:
    path, sep, why = e.partition("=")
    if not sep or not why.strip():
        sys.exit("cat8_mklist: --exclude needs <path>=<reason>: " + e)
    if path not in rel_set:
        sys.exit("cat8_mklist: excluded path is not under the root: " + path)
    excl[path] = why.strip()
absent = {}
for e in a.absent:
    path, sep, why = e.partition("=")
    if not sep or not why.strip():
        sys.exit("cat8_mklist: --absent needs <path>=<reason>: " + e)
    if path in rel_set:
        sys.exit("cat8_mklist: absent path is under the root: " + path)
    absent[path] = why.strip()
for x in a.add:
    if not os.path.isfile(x):
        sys.exit("cat8_mklist: added file does not exist: " + x)

listed = [os.path.join(root, p) for p in rel if p not in excl] + [os.path.abspath(x) for x in a.add]
with open(a.out, "w", encoding="utf-8", errors="surrogateescape") as f:
    f.write("".join(p + "\n" for p in listed))
for p, why in excl.items():
    print("除外\t%s\t%s" % (p, why))
for p, why in absent.items():
    print("無い\t%s\t%s" % (p, why))
for x in a.add:
    print("足した\t%s" % os.path.abspath(x))
print("cat8_mklist: complete out=%s in_root=%d added=%d absent=%d excluded=%d listed=%d" % (
    os.path.abspath(a.out), len(rel), len(a.add), len(absent), len(excl), len(listed)))
