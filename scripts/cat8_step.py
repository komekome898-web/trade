#!/usr/bin/env python3
"""区分 8 の生ログに 1 手を書き足す道具(調査班が打つ)。

置いた理由(2026-09-23、区分 8 の 1 回目の検収): 1 回目の生ログは、別々の 6 本の検索が同じ秒の時刻を持ち、
「実測」の手のコマンドが「grep … 等」と要約されていて打ち直せなかった(あとからまとめて書いた形)。
委任文 §5-5 は 1 手ずつ、コマンド・出力・終了コード・所要時間・UTC 時刻を残すことを求めている。
この道具を通して打てば、時刻・所要時間・終了コード・コマンド・出力は道具が書くので、手で作れない。

使い方:
  # シェルのコマンドを打って記録する(出力の先頭 3000 文字を残す)
  python3 scripts/cat8_step.py --log <生ログ> --method run --target <語> --note <文> -- <コマンド ...>
  # WebSearch・WebFetch・x_fetch など、シェルの外の道具の結果を記録する(標準入力に結果をそのまま流す)
  python3 scripts/cat8_step.py --log <生ログ> --method websearch --target <語> --note <文> --manual "<打った問い>" < 結果.txt

--manual のとき、時間と終了コードは道具が測れないので `time_s=NA rc=NA` と書く(作った数を書かない)。
結果は要約せず、返ってきた一覧(題名と URL)をそのまま流す。
"""
import argparse, datetime, pathlib, subprocess, sys, time

ap = argparse.ArgumentParser()
ap.add_argument("--log", required=True)
ap.add_argument("--method", required=True)
ap.add_argument("--target", required=True)
ap.add_argument("--note", required=True)
ap.add_argument("--manual")
ap.add_argument("--keep", type=int, default=3000)
ap.add_argument("cmd", nargs=argparse.REMAINDER)
a = ap.parse_args()

def one_word(s):
    return "_".join(s.split()) or "-"


def one_line(s):
    # 見出しは 1 行でなければならない(改行を含む note が孤立した行を残した = 監査 10 回目の指摘 5)
    return " ".join(s.split()) or "-"

now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
if a.manual is not None:
    body = sys.stdin.read()
    head = "--- %s method=%s target=%s rc=NA time_s=NA note=%s" % (now, one_word(a.method), one_word(a.target), one_line(a.note))
    cmdline, out, rc = one_line(a.manual), body, 0
else:
    cmd = a.cmd[1:] if a.cmd[:1] == ["--"] else a.cmd
    if not cmd:
        sys.exit("コマンドが無い(-- のあとに書く)")
    cmdline = " ".join(cmd)
    t0 = time.monotonic()
    p = subprocess.run(["bash", "-c", cmdline], capture_output=True, text=True, errors="replace")
    dt = time.monotonic() - t0
    rc, out = p.returncode, (p.stdout + p.stderr)
    head = "--- %s method=%s target=%s rc=%d time_s=%.3f note=%s" % (
        now, one_word(a.method), one_word(a.target), rc, dt, one_line(a.note))
cut = out[: a.keep]
tail = "" if len(out) <= a.keep else "\n[出力は %d 文字。先頭 %d 文字だけを残した]" % (len(out), a.keep)
with open(a.log, "a") as f:
    f.write(head + "\n$ " + cmdline + "\n" + cut.rstrip("\n") + tail + "\n")
n = sum(1 for _ in open(a.log))
print(out[: a.keep])
print("[cat8_step] 記録した: %s(生ログは %d 行)" % (head[:120], n), file=sys.stderr)
sys.exit(rc if a.manual is None else 0)
