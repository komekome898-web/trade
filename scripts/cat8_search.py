#!/usr/bin/env python3
"""The one way to run a search that a cat8 `なし` may rest on (audits 63-65: every list of
"cut" forms had a gap, so the checker now accepts only this tool's complete output).

Usage: python3 scripts/cat8_search.py --list <file of paths, one per line or NUL-separated>
                                      --pattern <regex> [--ignore-case]

Reads every file in the list (a file that cannot be read is reported and makes the exit code
1), prints every matching line as `path:line: text`, then a per-file count and a footer
`cat8_search: complete files=N read=M files_with_hits=F hits=H`. A line longer than 400
characters is printed as the 200 characters on each side of each match, with its length
stated, so a minified file cannot flood the log without hiding any match. Nothing is cut
silently, and the footer is printed only after every file was read.
Run it through cat8_step.py with a large --keep and without any pipe after it.
"""
import argparse
import re
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--list", required=True)
ap.add_argument("--pattern", required=True)
ap.add_argument("-i", "--ignore-case", action="store_true")
a = ap.parse_args()

raw = open(a.list, "rb").read()
sep = b"\0" if b"\0" in raw else b"\n"
paths = [p.decode("utf-8", "surrogateescape") for p in raw.split(sep) if p.strip()]
rx = re.compile(a.pattern, re.I if a.ignore_case else 0)

read, unread, per_file, hits, encs = 0, [], {}, 0, []
for p in paths:
    try:
        with open(p, "rb") as f:
            data = f.read()
    except OSError as e:
        unread.append((p, e.strerror))
        continue
    # Binary (NUL) and undecodable files are not "read": a silent replacement would lose
    # Japanese matches (audit 66, finding 3). Exclude binaries with cat8_mklist --exclude.
    if b"\0" in data:
        unread.append((p, "バイナリ(NUL を含む。cat8_mklist の --exclude で理由を書いて外す)"))
        continue
    text = None
    for enc in ("utf-8", "utf-8-sig", "cp932", "euc_jp"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        unread.append((p, "符号化が utf-8・cp932・euc_jp のどれでもない"))
        continue
    if enc not in ("utf-8", "utf-8-sig"):
        encs.append((p, enc))
    read += 1
    for no, line in enumerate(text.splitlines(), 1):
        ms = list(rx.finditer(line))
        if not ms:
            continue
        hits += 1
        per_file[p] = per_file.get(p, 0) + 1
        if len(line) <= 400:
            print("%s:%d: %s" % (p, no, line))
        else:
            parts = ["…%s…" % line[max(0, m.start() - 200):m.end() + 200] for m in ms]
            print("%s:%d: [行の長さ %d 字。当たった %d か所の前後 200 字] %s" % (p, no, len(line), len(ms), " ".join(parts)))

print("== ファイルごとの当たった行の数")
for p, n in per_file.items():
    print("%d\t%s" % (n, p))
for p, enc in encs:
    print("符号化\t%s\t%s として読んだ" % (p, enc))
for p, why in unread:
    print("読めなかった\t%s\t%s" % (p, why))
import os
print("cat8_search: %s files=%d read=%d files_with_hits=%d hits=%d list=%s" % (
    "complete" if not unread and paths else "INCOMPLETE", len(paths), read, len(per_file), hits, os.path.abspath(a.list)))
sys.exit(1 if unread or not paths else 0)
