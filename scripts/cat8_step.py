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
--deadline <UTC の ISO 時刻> を付けると、その時刻を過ぎていたら手を打たずに生ログに「期限切れ」の 1 手を書き、終了コード 3 で止まる
(予算の区切りを自己申告に任せないため。2026-09-23 監査 12 回目の指摘 5)。
結果は要約せず、返ってきた一覧(題名と URL)をそのまま流す。
"""
import argparse, datetime, pathlib, shlex, subprocess, sys, time

ap = argparse.ArgumentParser()
ap.add_argument("--log", required=True)
ap.add_argument("--method", required=True)
ap.add_argument("--target", required=True)
ap.add_argument("--note", required=True)
ap.add_argument("--manual")
ap.add_argument("--keep", type=int, default=3000)
ap.add_argument("--deadline", help="UTC の ISO 時刻。これを過ぎていたら手を打たずに終了コード 3 で止まる(予算の区切り)")
ap.add_argument("--sandbox", help="一時・キャッシュの置き場所の根(scratchpad の下)。一度付ければ同じ生ログの以後の手に自動で掛かる")
ap.add_argument("cmd", nargs=argparse.REMAINDER)
a = ap.parse_args()
if a.cmd[:1] == ["--"]:
    a.cmd = a.cmd[1:]

# 置き場所の環境変数を道具が付ける(2026-09-26、33 回目の検収 監査 130 回目の指摘 1: 起動文で「毎回付ける」と
# 書いても 33 回目は pip の手の 1 本にも付かなかった。規則ではなく道具で付ける)。
# --sandbox を省いた手は、同じ生ログの最後の「[sandbox <道>]」を引き継ぐ。
SANDBOX_TAG = " [sandbox %s]"
if not a.sandbox and pathlib.Path(a.log).exists():
    for ln in open(a.log, errors="replace"):
        if ln.startswith("--- ") and " [sandbox " in ln:
            a.sandbox = ln.rsplit(" [sandbox ", 1)[1].split("]", 1)[0]
env = None
if a.sandbox:
    import os
    sb = pathlib.Path(a.sandbox)
    for sub in ("tmp", "pipcache", "m2", "gradle", "cache"):
        (sb / sub).mkdir(parents=True, exist_ok=True)
    env = dict(os.environ,
               TMPDIR=str(sb / "tmp"), PIP_CACHE_DIR=str(sb / "pipcache"), XDG_CACHE_HOME=str(sb / "cache"),
               GRADLE_USER_HOME=str(sb / "gradle"), MAVEN_OPTS="-Dmaven.repo.local=%s" % (sb / "m2"),
               # JVM は TMPDIR を見ない。-XX:-UsePerfData で /tmp/hsperfdata_<利用者> を作らせない(33 回目に作られた)
               JAVA_TOOL_OPTIONS="-XX:-UsePerfData -Djava.io.tmpdir=%s" % (sb / "tmp"))


def to_cmdline(cmd):
    # 引数が 1 つならシェルの文として打つ(パイプなどを使える)。2 つ以上なら 1 つずつ引用して繋ぐ
    # (空白を含む引数が割れていた = 2026-09-23 監査 13 回目の指摘 1。`date -u -d '+20 min' +%FT%TZ` が失敗した)
    return cmd[0] if len(cmd) == 1 else shlex.join(cmd)

def one_word(s):
    return "_".join(s.split()) or "-"


def one_line(s):
    # 見出しは 1 行でなければならない(改行を含む note が孤立した行を残した = 監査 10 回目の指摘 5)
    return " ".join(s.split()) or "-"

_now = datetime.datetime.now(datetime.timezone.utc)
now = _now.strftime("%Y-%m-%dT%H:%M:%SZ")
dl_tag = (" [期限 %s]" % a.deadline if a.deadline else "") + (SANDBOX_TAG % a.sandbox if a.sandbox else "")
if a.deadline:
    dl = datetime.datetime.strptime(a.deadline, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    if _now > dl:
        with open(a.log, "a") as f:
            f.write("--- %s method=budget target=期限切れ rc=3 time_s=0 note=期限 %s を過ぎたので手を打たなかった\n"
                    "$ (打たなかった) %s\n" % (now, a.deadline, one_line(to_cmdline(a.cmd) if a.cmd else (a.manual or ""))))
        print("[cat8_step] 期限 %s を過ぎた。次の段・次の候補に入らずに、返す前の手順(起動文 §7)へ進む" % a.deadline,
              file=sys.stderr)
        sys.exit(3)
if a.manual is not None:
    body = sys.stdin.read()
    head = "--- %s method=%s target=%s rc=NA time_s=NA note=%s" % (now, one_word(a.method), one_word(a.target), one_line(a.note) + dl_tag)
    cmdline, out, rc = one_line(a.manual), body, 0
else:
    cmd = a.cmd
    if not cmd:
        sys.exit("コマンドが無い(-- のあとに書く)")
    cmdline = to_cmdline(cmd)
    t0 = time.monotonic()
    p = subprocess.run(["bash", "-c", cmdline], capture_output=True, text=True, errors="replace", env=env)
    dt = time.monotonic() - t0
    rc, out = p.returncode, (p.stdout + p.stderr)
    head = "--- %s method=%s target=%s rc=%d time_s=%.3f note=%s" % (
        now, one_word(a.method), one_word(a.target), rc, dt, one_line(a.note) + dl_tag)
cut = out[: a.keep]
# 出力の中の「--- 」「$ 」で始まる行は、見出しやコマンドの行と取り違えられる(2026-09-23、2 回目の生ログの 584・586 行が
# 見出しの形の検査に当たった)。出力の行だと分かるように、先頭に「| 」を付けて残す。
cut = "\n".join(("| " + ln) if (ln.startswith("---") or ln.startswith("$ ")) else ln for ln in cut.split("\n"))
tail = "" if len(out) <= a.keep else "\n[出力は %d 文字。先頭 %d 文字だけを残した]" % (len(out), a.keep)
with open(a.log, "a") as f:
    f.write(head + "\n$ " + cmdline + "\n" + cut.rstrip("\n") + tail + "\n")
n = sum(1 for _ in open(a.log))
print(out[: a.keep])
print("[cat8_step] 記録した: %s(生ログは %d 行)" % (head[:120], n), file=sys.stderr)
sys.exit(rc if a.manual is None else 0)
