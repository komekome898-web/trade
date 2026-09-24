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
ap.add_argument("--candidate", required=True, help="台帳の番号 8-NNN。検索がどの候補のものかを検査が突き合わせる(監査 68 回目)")
ap.add_argument("--out", required=True)
ap.add_argument("--exclude", action="append", default=[])
ap.add_argument("--add", action="append", default=[])
ap.add_argument("--absent", action="append", default=[],
                help="<path>=<reason>: a file of the source tree that is not under --root and not added "
                     "(for example an image over 1 MB the fetch helper did not download). Counted in N, not listed.")
a = ap.parse_args()
import re as _re
if not _re.fullmatch(r"8-\d{3}", a.candidate):
    sys.exit("--candidate は 8-NNN の形: " + a.candidate)

root = os.path.abspath(a.root)
if os.path.isdir(os.path.join(root, ".git")):
    out = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True, check=True).stdout
    rel = [p.decode("utf-8", "surrogateescape") for p in out.split(b"\0") if p]
else:
    rel, links = [], []
    for d, dirs, files in os.walk(root):
        for x in list(dirs):
            if os.path.islink(os.path.join(d, x)):
                links.append(os.path.relpath(os.path.join(d, x), root))
        dirs[:] = [x for x in dirs if x != ".git" and not os.path.islink(os.path.join(d, x))]
        for f in files:
            rel.append(os.path.relpath(os.path.join(d, f), root))
    if links:
        # A symlinked directory is neither walked nor silently dropped (audit 67, finding 5).
        sys.exit("cat8_mklist: symlinked directories under the root (copy their files in or list them with --add): "
                 + " ".join(links))
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
# A repo fetched by cat8_repo_fetch.sh records the blobs it did not download; each must be
# --add-ed (fetched another way, given as <root>/<path>) or --absent-ed with a reason (audit 67, finding 4).
fetched_skipped = []
if os.path.isfile(os.path.join(root, ".git", "cat8_missing")) and os.path.isfile(os.path.join(root, ".git", "cat8_tree")):
    missing = set(open(os.path.join(root, ".git", "cat8_missing")).read().split())
    for e in open(os.path.join(root, ".git", "cat8_tree"), "rb").read().split(b"\0"):
        if not e:
            continue
        meta, path = e.split(b"\t", 1)
        if meta.split()[2].decode() in missing:
            fetched_skipped.append(path.decode("utf-8", "surrogateescape"))
    added_rel = {os.path.relpath(os.path.abspath(x), root) for x in a.add}
    unaccounted = [p for p in fetched_skipped if p not in absent and p not in added_rel]
    if unaccounted:
        sys.exit("cat8_mklist: files the fetch did not download are neither --add-ed nor --absent-ed: "
                 + " ".join(unaccounted))

listed = [os.path.join(root, p) for p in rel if p not in excl] + [os.path.abspath(x) for x in a.add]
import hashlib
body = "".join(p + "\0" for p in listed).encode("utf-8", "surrogateescape")  # NUL: names may hold newlines
with open(a.out, "wb") as f:
    f.write(body)
digest = hashlib.sha256(body).hexdigest()[:16]
for p, why in excl.items():
    print("除外\t%s\t%s" % (p, why))
for p, why in absent.items():
    print("無い\t%s\t%s" % (p, why))
for x in a.add:
    print("足した\t%s" % os.path.abspath(x))
print("cat8_mklist: complete out=%s in_root=%d added=%d absent=%d excluded=%d listed=%d sha=%s candidate=%s" % (
    os.path.abspath(a.out), len(rel), len(a.add), len(absent), len(excl), len(listed), digest, a.candidate))
