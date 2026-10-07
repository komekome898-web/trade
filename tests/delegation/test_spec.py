"""委任文の検め(`check_delegation.py`)と報告の受け取りの検め(`check_report.py`)の受け入れの試験。

リードが書いた(L-791「**測定に限らず全ての委任において、委任のミスでやり直しが発生しない委任文の書き方と仕組み**」)。
散文の受け入れは事前の批評 2 回で「決まっていない」を回ごとに新しく生んだので(40 件 → 33 件)、受け入れをこの試験で渡す。
作業者は試験を変えずに通す(変えたいときは問いとして返す)。試験で決まらない振る舞いは作業者が決めてよい。

L-794「**重複していたり過剰すぎたりしている内容をまとめて少なくする方法はありませんか？**」を受けて、1 つの検めの場面は
1 つの試験の表(CASES)で回し、落ちた場面を全部名前で出す形にした(確かめる場面は減らしていない)。

道具の置き場: 環境変数 `DELEGATION_TOOLS_DIR`(無ければ `scripts/delegation/`)。道具が無ければこの組は飛ばす。

道具の口(この試験が決める):
- `check_delegation.py <委任文> --owner-log P --fixed P --scenes P --root DIR [--require-approval] [--print-hash]`
- `check_report.py <報告> --delegation <委任文> --owner-log P --fixed P --scenes P --root DIR`
- 道具は 1 ファイルずつで完結させる(同じ置き場の部品を import しない)。Python の標準ライブラリだけ。
- 委任文は、渡されたパスのまま(resolve・absolute をせず)`Path.read_bytes()` で 1 回だけ読む。
- `--print-hash` は委任文だけを読み、事前の批評の sha256 を 64 桁の 16 進で 1 行出す。既定のパスを読まず、印に触れない。
- `--root` は、読んだ事実の確かめの欄のパスと、変異の表の試験のファイルを解く根。
- 終了コード: 0 合格 / 1 検めの失敗 / 2 入力の誤り(委任文・OWNER_LOG・FIXED・BREAK_SCENES・報告が無い・ディレクトリ・UTF-8 でない)。
  どの入力でも標準エラーに `Traceback` を出さない。失敗の行は全部、標準出力に日本語で出す。
- 種類は 5 行目までの行頭の `種類: ` の行 1 つで、値は `作る`・`読む`・`批評` の 3 つ。
- 表の行は、バッククォートの外の `|` で区切る。
- 決まった制約の節は、FIXED の `## 決まった制約` の節と、行末の空白と空行を除いて行ごとに一字違わず同じ。
- オーナーの引用(`L-番号「**…**」` か `「**…**」L-番号`。番号は `L-` と数字 3 桁と英小文字 0〜1 字、または `L-D` と数字 2 桁)は、
  委任文の全部の節で、OWNER_LOG の 1 列目がちょうどその番号の行の 4 列目(オーナーの逐語の欄)に、空白の並びを 1 つの半角の
  空白にそろえて含まれるか、で比べる。読みの列(5 列目)や「L-100 結果」のような 1 列目の行とは比べない。
  1 行に引用が続けて並び(`「**a**」「**b**」L-277` / `L-277「**a**」「**b**」`)番号が 1 つのときは、並びの全部がその番号の
  引用で、1 つずつ、その番号のどれかの行に含まれれば通る。バッククォートの中は見ない。番号の無い引用が失敗になるのは
  `## 目的(オーナーの逐語)` の節の中だけ(ほかの節の番号の無い引用は見ない)。
- 読んだ事実の確かめの欄の `パス:行`: パスは「/ を 1 つ以上含む ASCII の語」(点で始まるディレクトリ・拡張子の無いファイル
  を含む)。欄の中の全部の `パス:行` を見る。ファイルに触れる前に、`--root` から解いて文字の上で畳んだパスを小文字にして封印の
  置き場の下か・根の外かを見る(どちらも失敗)。次に ふつうのファイルか(`is_file()`)を見て、ふつうのファイルでなければ
  失敗(開かない)。行の番号(範囲 `a-b` なら b)はファイルの行の数以下。
- 事前の批評の記録: `<委任文の名前から .md を除いたもの>_premortem<数字>.md`。最後の回 = 番号の一番大きい記録。最後の回の
  1 行目 `委任文 sha256: <64 桁>` が今の委任文の事前の批評の sha256 と同じ(`## 事前の批評の後の変更` の節に `見た版の sha256:`
  があればその値と同じ)。全部の回で、行頭が `- [直す]`・`- [聞く]` の指摘ごとに、次の指摘か見出しまでの、空白を除いた行頭が
  `応答: ` の行が 1 つあり、値は `直した`・`直さない`・`オーナーに聞く`・`次の版で直す` に半角か全角の括弧で、行末の閉じ括弧
  までの中身が 1 字以上。番号が 2 以上の最後の回は「直した」を書けない。
- 印: 合格のとき委任文の横に `<名前>.stamp.json`(delegation_sha256・body_sha256・kind・premortem・approved)。0 以外のときは
  古い印を消す。approved = `## オーナーの承認` の節に、上の決まりで通るオーナーの引用が 1 つ以上ある。`--require-approval`
  のときは approved でなければ失敗。check_report は印を読まず書かず、委任文の検めをやり直す。
- 報告(作る): `## 変異の表` の表で、委任文の U と H の番号が全部、どこかの行の 1 列目に出る(1 欄に複数可。U1 は U10 に
  当たらない)。U の行の 3 列目は `パス::名前`(`クラス::名前` と `[…]` の付いた名前を含む)で、`--root` から解いたファイルに
  その名前の関数がある(パスは上の封印の決まりも当てる)。空・`落ちなかった` は失敗。H の行の 3 列目は空でない。
- 報告(読む): `## 結果` の節の表の各行の最後の列(出典)が空でない。
- 報告(全部の種類): `## 問いとして返したこと` の節に、`問いとして返したことは無い。` か、行頭の `- Q<数字>:` があり、その
  番号が全部、委任文の `## 途中の決め` の行頭の `- Q<数字>:` に出る。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(os.environ.get("DELEGATION_TOOLS_DIR", ROOT / "scripts" / "delegation"))
CD = TOOLS / "check_delegation.py"
CR = TOOLS / "check_report.py"
FIXED = ROOT / ".claude" / "skills" / "delegated-study" / "FIXED_CONSTRAINTS.md"
SCENES = ROOT / ".claude" / "skills" / "delegated-study" / "BREAK_SCENES.md"

pytestmark = pytest.mark.skipif(not (CD.exists() and CR.exists()), reason="道具がまだ無い(作る前)")

SCENE_NAMES = [l[2:].split(":", 1)[0] for l in SCENES.read_text(encoding="utf-8").splitlines() if l.startswith("- ")]
DECIDE = ("出力の置き場", "分母・数え方", "比べの方法", "確かめ方", "依存", "絞り方・選び方", "単位・通貨のそろえ方")
CORE = ["## 着手前の表", "## 目的(オーナーの逐語)", "## 読んだ事実", "## 決めてよいこと・決めてはいけないこと",
        "## 変えないもの", "## 決まった制約", "## 終わる条件と上限", "## 報告"]
MAKE = ["## 壊す場面", "## 受け入れ", "## 変異の表"]

# 読みの列(5 列目)と「L-100 結果」の行に、引用と同じ文を置く(それに当たっても通さないため)
OWNER_LOG = (
    "| L番号 | 日付 | 種類 | オーナーの逐語 | 読み |\n"
    "|---|---|---|---|---|\n"
    "| L-100 | d | 決定 | 「**前置き。甲の\t乙を作れ　すぐに**」 | 読みの列: 読みだけにある文 |\n"
    "| L-100 結果 | d | (リード) | — | 結果の行にだけある文 |\n"
    "| L-277 | d | 決定 | 「**一つ目**」 | x |\n"
    "| L-277 | d | 決定 | 「**二つ目の行**」 | x |\n"
    "| L-499a | d | 決定 | 「**枝の番号の行**」 | x |\n"
    "| L-D01 | d | 決定 | 「**Dの番号の行**」 | x |\n"
    "| L-200 | d | 承認 | 「**委任してよい**」 | x |\n"
)


def _fixed_section() -> str:
    sec = FIXED.read_text(encoding="utf-8").split("## 決まった制約\n", 1)[1]
    return "## 決まった制約\n" + sec.split("\n## ", 1)[0].rstrip("\n") + "\n"


def make_delegation(kind: str = "作る") -> str:
    scenes = "".join(f"| {n} | U1 と説明 |\n" if i % 2 == 0 else f"| {n} | この委任には無い(試しの理由) |\n"
                     for i, n in enumerate(SCENE_NAMES))
    decide = "".join(f"| {k} | 決めた |\n" for k in DECIDE) + "| 余分な行 | 許す |\n"
    parts = [
        "# 委任文: 試し\n\n", f"種類: {kind}\n\n",
        "## 着手前の表\n表を出す。\n\n",
        "## 目的(オーナーの逐語)\n- L-100「**甲の 乙を作れ すぐに**」\n\n",
        "## 読んだ事実\n\n| # | 事実 | 確かめ |\n|---|---|---|\n"
        "| データ | 無い | この委任には無い(市場のデータを使わない) |\n"
        "| 既存の決まり | 参照 | `src/a.py:2` |\n"
        "| 既存の決まり | 点のディレクトリ | `.cfg/b.md:1-2` |\n"
        "| 既存の決まり | 拡張子の無いファイル | `hooks/pre-push:1` |\n"
        "| 列の意味 | 列 | `grep -n x src/a.py` → 2 行目に x |\n\n",
        "## 決めてよいこと・決めてはいけないこと\n\n| 選び | 決め |\n|---|---|\n" + decide + "\n",
        "## 変えないもの\n\n- H1: 何も変えない。確かめ: git diff\n\n",
    ]
    if kind == "作る":
        parts += ["## 壊す場面\n\n| 場面 | 書いたこと |\n|---|---|\n" + scenes + "\n",
                  "## 受け入れ\n\n- U1: 一つ目\n- U2: 二つ目\n\n",
                  "## 変異の表\n\n形: | 番号 | 壊した変更 | 落ちた試験 |\n\n"]
    if kind == "読む":
        parts += ["## 出典の決まり\n\n表の最後の列に出典。\n\n"]
    parts += [_fixed_section() + "\n", "## 終わる条件と上限\n\n- 終わる条件: 全部通る\n- 上限: 2 周\n\n",
              "## 報告\n\n- 書く\n\n", "## 途中の決め\n\n(まだ無い)\n"]
    return "".join(parts)


def body_hash(text: str) -> str:
    """事前の批評の sha256: `## 途中の決め`・`## オーナーの承認`・`## 事前の批評の後の変更` の見出しの行から、次の `## ` の行の手前
    (無ければ終わり)までを除いたバイト。"""
    out, skip = [], False
    for line in text.splitlines(keepends=True):
        if line.startswith("## "):
            skip = line.rstrip("\r\n").rstrip() in ("## 途中の決め", "## オーナーの承認", "## 事前の批評の後の変更")
        if not skip:
            out.append(line)
    return hashlib.sha256("".join(out).encode("utf-8")).hexdigest()


def premortem(h: str, items) -> str:
    lines = [f"委任文 sha256: {h}", "", "## 問1"]
    for mark, resp in items:
        lines.append(f"- [{mark}] 指摘の文(括弧(入れ子)を含む)")
        if resp is not None:
            lines.append(f"  応答: {resp}")
    return "\n".join(lines) + "\n"


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert "Traceback" not in r.stderr, r.stderr
    return r


class Env:
    def __init__(self, tmp: Path, kind: str = "作る"):
        self.tmp, self.kind = tmp, kind
        self.root = tmp / "root"
        for rel, txt in (("src/a.py", "x = 1\nx = 2\nx = 3\n"), (".cfg/b.md", "a\nb\n"), ("hooks/pre-push", "#!/bin/sh\n"),
                         ("tests/test_a.py", "def test_one():\n    pass\n\nclass TestK:\n    def test_two(self):\n        pass\n")):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(txt, encoding="utf-8")
        self.log = tmp / "OWNER_LOG.md"
        self.log.write_text(OWNER_LOG, encoding="utf-8")
        self.d = tmp / "work" / "DELEGATION_x.md"
        self.d.parent.mkdir()
        self.reset()

    def reset(self, text: str | None = None):
        for p in self.d.parent.glob("DELEGATION_x_premortem*.md"):
            p.unlink()
        self.write(text if text is not None else make_delegation(self.kind))
        if self.kind == "作る":
            self.write_pm(1, premortem(body_hash(self.text()), [("直す", "直した(節「受け入れ」(U2))"), ("聞く", "オーナーに聞く(L-200)")]))

    def text(self):
        return self.d.read_text(encoding="utf-8")

    def write(self, t):
        self.d.write_text(t, encoding="utf-8")

    def write_pm(self, n, t):
        (self.d.parent / f"DELEGATION_x_premortem{n}.md").write_text(t, encoding="utf-8")

    def edit(self, old, new, count=1):
        """本文を変え、事前の批評の記録の sha256 も合わせる(事前の批評の検め以外を試すため)。"""
        t = self.text()
        assert old in t, old
        self.reset(t.replace(old, new, count))

    def stamp(self):
        return self.d.parent / "DELEGATION_x.stamp.json"

    def cd(self, *extra, path=None):
        return _run([sys.executable, str(CD), str(path or self.d), "--owner-log", str(self.log), "--fixed", str(FIXED),
                     "--scenes", str(SCENES), "--root", str(self.root), *extra])

    def cr(self, report):
        return _run([sys.executable, str(CR), str(report), "--delegation", str(self.d), "--owner-log", str(self.log),
                     "--fixed", str(FIXED), "--scenes", str(SCENES), "--root", str(self.root)])


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


def check_cases(env, cases):
    """cases: [(名前, 変更する関数(env), 期待: "ok" か 落ちたときに標準出力に含む語)]。全部回して、外れた場面を全部名前で出す。"""
    bad = []
    for name, change, expect in cases:
        env.reset()
        change(env)
        try:
            r = env.cd()
        except subprocess.TimeoutExpired:
            bad.append(f"{name}: 60 秒で終わらない(名前付きパイプを開いた?)")
            continue
        if expect == "ok":
            if r.returncode != 0:
                bad.append(f"{name}: 合格のはずが {r.returncode}: {r.stdout.strip()[:200]}")
        elif r.returncode != 1 or expect not in r.stdout:
            bad.append(f"{name}: 終了コード 1 と「{expect}」のはずが {r.returncode}: {r.stdout.strip()[:200]}")
    assert not bad, "\n".join(bad)


def E(old, new):
    return lambda env: env.edit(old, new)


# ---------------------------------------------------------------- 合格・印・入力の誤り(U1)

def test_valid_passes_writes_stamp_and_failure_removes_it(env):
    r = env.cd()
    assert r.returncode == 0, r.stdout
    s = json.loads(env.stamp().read_text(encoding="utf-8"))
    assert s["delegation_sha256"] == hashlib.sha256(env.d.read_bytes()).hexdigest()
    assert s["body_sha256"] == body_hash(env.text())
    assert s["kind"] == "作る" and s["premortem"].endswith("DELEGATION_x_premortem1.md") and s["approved"] is False
    env.edit("## 報告\n", "## 報告X\n")
    assert env.cd().returncode == 1 and not env.stamp().exists()


def test_input_errors_exit_2_and_all_failures_listed(env, tmp_path):
    assert env.cd(path=tmp_path / "nothing.md").returncode == 2
    assert env.cd().returncode == 0 and env.stamp().exists()
    r = _run([sys.executable, str(CD), str(env.d), "--owner-log", str(tmp_path), "--fixed", str(FIXED),
              "--scenes", str(SCENES), "--root", str(env.root)])
    assert r.returncode == 2 and not env.stamp().exists()
    env.d.write_bytes(b"\xff\xfe\x00bad")
    assert env.cd().returncode == 2
    env.reset()
    env.edit("| 依存 | 決めた |\n", "")
    env.edit("## 報告\n", "## 報告X\n")
    r = env.cd()
    assert r.returncode == 1 and "依存" in r.stdout and "報告" in r.stdout, r.stdout


# ---------------------------------------------------------------- sha256 の決まり(U12)

HASH_CASES = [
    ("# x\n\n種類: 作る\n\n## 目的(オーナーの逐語)\n本文\n## 途中の決め\n- Q1: 答え\n## 報告\n終わり",
     "e586ff9d777883eb42fbbf85488bbc2f1e258c001697417b316f2360f69ed3e8"),
    ("# x\n## 報告\n終わり\n## 途中の決め\n- Q1: 答え", "d3a7e3b56523c32616ee2e09cad50f1ab1f955e9182ce0b5ea74cd01ecdb9190"),
]


def test_hash_rule_and_print_hash(tmp_path):
    for t, expect in HASH_CASES:
        assert body_hash(t) == expect
        p = tmp_path / "d.md"
        p.write_text(t, encoding="utf-8")
        r = _run([sys.executable, str(CD), str(p), "--print-hash"])  # 既定のパスを渡さない(読まない)
        assert r.returncode == 0 and r.stdout == expect + "\n", r.stdout


# ---------------------------------------------------------------- 形の検め(U2〜U11)

def _move_kind(pos):
    def f(env):
        lines = env.text().split("\n")
        k = lines.pop(2)
        lines.insert(pos - 1, k)
        env.reset("\n".join(lines))
    return f


def _drop_line(prefix):
    def f(env):
        env.reset("\n".join(l for l in env.text().split("\n") if not l.startswith(prefix)))
    return f


def _swap_scene_rows(env):
    lines = env.text().split("\n")
    idx = [i for i, l in enumerate(lines) if any(l.startswith(f"| {n} |") for n in SCENE_NAMES)]
    lines[idx[0]], lines[idx[1]] = lines[idx[1]], lines[idx[0]]
    env.reset("\n".join(lines))


def _scene_cell(i, cell):
    def f(env):
        n = SCENE_NAMES[i]
        env.reset(re.sub(rf"^\| {re.escape(n)} \|.*$", f"| {n} | {cell} |", env.text(), flags=re.M))
    return f


def _fact(cell):
    return E("| 既存の決まり | 参照 | `src/a.py:2` |", f"| 既存の決まり | 参照 | {cell} |")


def _fifo(rel):
    def f(env):
        p = env.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            os.mkfifo(p)  # 開けば止まる。止まれば 60 秒で試験が落ちる
        env.edit("| 既存の決まり | 参照 | `src/a.py:2` |", f"| 既存の決まり | 参照 | `{rel}:1` |")
    return f


FIRST_FIXED = _fixed_section().split("\n")[1]

FORM_CASES = [
    # U2 種類
    ("種類 5 行目", _move_kind(5), "ok"),
    ("種類 6 行目", _move_kind(6), "種類"),
    ("種類 無し", E("種類: 作る", ""), "種類"),
    ("種類 知らない値", E("種類: 作る", "種類: 作業"), "種類"),
    ("種類 2 つ", E("種類: 作る", "種類: 作る\n種類: 読む"), "種類"),
    # U3 見出し(1 つずつ)
    *[(f"見出し {h}", E(h + "\n", "## 別の見出し\n"), h[3:]) for h in CORE + MAKE],
    # U4 引用
    ("引用 真ん中の 1 字", E("甲の 乙を作れ", "甲の 丙を作れ"), "L-100"),
    ("引用 無い番号", E("L-100「**", "L-999「**"), "L-999"),
    ("引用 逐語の一部(頭を落とす)は可", E("「**甲の 乙を作れ すぐに**」", "「**乙を作れ**」"), "ok"),
    ("引用 読みの列にだけある文", E("「**甲の 乙を作れ すぐに**」", "「**読みだけにある文**」"), "L-100"),
    ("引用 「L-100 結果」の行にだけある文", E("「**甲の 乙を作れ すぐに**」", "「**結果の行にだけある文**」"), "L-100"),
    ("引用 逆向き・並び・枝番号・D 番号・同じ番号の 2 行",
     E("- L-100「**甲の 乙を作れ すぐに**」", "- L-100「**甲の 乙を作れ すぐに**」\n- 「**一つ目**」「**二つ目の行**」L-277\n"
       "- 「**枝の番号の行**」L-499a\n- L-D01「**Dの番号の行**」"), "ok"),
    ("引用 並びの 2 つ目の誤り", E("- L-100「**甲の 乙を作れ すぐに**」", "- L-100「**甲の 乙を作れ すぐに**」\n- 「**一つ目**」「**二つ目の列**」L-277"), "L-277"),
    ("引用 目的の節の番号の無い引用", E("## 目的(オーナーの逐語)\n", "## 目的(オーナーの逐語)\n- 「**番号の無い引用**」\n"), "番号"),
    ("引用 目的の外のバッククォートの中は可", E("## 報告\n\n- 書く", "## 報告\n\n- 書く。例: `「**中**」`"), "ok"),
    # U5 読んだ事実
    ("事実 行の数ちょうど", _fact("`src/a.py:3`"), "ok"),
    ("事実 行の数 +1", _fact("`src/a.py:4`"), "読んだ事実"),
    ("事実 範囲の後ろで比べる", _fact("`src/a.py:1-4`"), "読んだ事実"),
    ("事実 無いパス", _fact("`src/nothing.py:1`"), "読んだ事実"),
    ("事実 全部の パス:行 を見る", _fact("`src/a.py:1` と `src/a.py:9`"), "読んだ事実"),
    ("事実 コマンドと出力", _fact("`grep x src/a.py` → 出た"), "ok"),
    ("事実 → が無い", _fact("`grep x src/a.py`"), "読んだ事実"),
    ("事実 → の後が空", _fact("`grep x src/a.py` → "), "読んだ事実"),
    ("事実 無い(理由 1 字)", _fact("この委任には無い(x)"), "ok"),
    ("事実 無い(全角の括弧)", _fact("この委任には無い（全角）"), "ok"),
    ("事実 無い(理由が空)", _fact("この委任には無い()"), "読んだ事実"),
    ("事実 空", _fact(""), "読んだ事実"),
    ("事実 確かめの形でない", _fact("見た"), "読んだ事実"),
    ("事実 時刻はパスでない", _fact("07:31 に見た"), "読んだ事実"),
    ("事実 バッククォートの中の | は区切りでない", _fact('`grep "^| L-" src/a.py \\| wc -l` → 0'), "ok"),
    ("事実 ディレクトリ", _fact("`src/:1`"), "読んだ事実"),
    ("事実 名前付きパイプは開かない", _fifo("src/pipe.txt"), "読んだ事実"),
    *[(f"事実 {r} の行が無い", _drop_line(f"| {r} |"), r) for r in ("データ", "既存の決まり", "列の意味")],
    # U6 封印
    ("封印 そのまま", _fifo("docs/RESEARCH/WINDOW1/x.md"), "封印"),
    ("封印 畳む", _fifo("./backtest_data/phase2_sealed/../phase2_sealed/y.csv"), "封印"),
    ("封印 大文字小文字", _fifo("Docs/Research/Window1/z.md"), "封印"),
    ("封印 根の中の絶対パス", lambda env: env.edit("`src/a.py:2`", f"`{env.root}/docs/RESEARCH/WINDOW1/a.md:1`"), "封印"),
    ("封印 根の外を通って根の中へ", _fact("`../root/docs/RESEARCH/WINDOW1/a.md:1`"), "封印"),
    ("根の外", _fact("`../../outside/a.md:1`"), "根の外"),
    # U7 決めてよいこと(1 つずつ消す・空にする)
    *[(f"決め {k} 無し", E(f"| {k} | 決めた |\n", ""), k) for k in DECIDE],
    *[(f"決め {k} 空", E(f"| {k} | 決めた |\n", f"| {k} |  |\n"), k) for k in DECIDE],
    # U8 壊す場面
    *[(f"場面 {n} 無し", _drop_line(f"| {n} |"), n) for n in SCENE_NAMES],
    ("場面 名前の 1 字", E(f"| {SCENE_NAMES[1]} |", f"| {SCENE_NAMES[1]}X |"), SCENE_NAMES[1]),
    ("場面 並び", _swap_scene_rows, "壊す場面"),
    *[(f"場面の欄 {c!r}", _scene_cell(0, c), SCENE_NAMES[0]) for c in ("", "書いた", "U99", "この委任には無い()")],
    ("場面の U1 は U10 に当たらない", E("- U1: 一つ目", "- U10: 一つ目"), "U1"),
    # U9 番号
    ("U 重なり", E("- U2: 二つ目", "- U1: 二つ目"), "U1"),
    ("U 飛びは可", E("- U2: 二つ目", "- U3: 三つ目"), "ok"),
    ("U 定義無し", E("- U1: 一つ目\n- U2: 二つ目\n", "(無し)\n"), "受け入れ"),
    ("H0 は可", E("- H1: 何も変えない。確かめ: git diff", "- H0: この委任には無い(新しく作るだけ)"), "ok"),
    ("H 無し", E("- H1: 何も変えない。確かめ: git diff", "何も無い"), "変えないもの"),
    # U10 決まった制約
    ("制約 1 字", E("Do not push.", "Do not push!"), "決まった制約"),
    ("制約 1 行消す", E(FIRST_FIXED + "\n", ""), "決まった制約"),
    ("制約 1 行足す", E(FIRST_FIXED + "\n", FIRST_FIXED + "\n- 足した行\n"), "決まった制約"),
    ("制約 行末の空白・空行は可", E(FIRST_FIXED + "\n", FIRST_FIXED + "   \n\n\n"), "ok"),
    # U11 終わる条件と上限
    ("上限の語が無い", E("- 上限: 2 周", "- 限り: 2 周"), "上限"),
]


def test_form_checks(env):
    check_cases(env, FORM_CASES)


def test_other_kinds(tmp_path):
    bad = []
    for kind in ("読む", "批評"):
        e = Env(tmp_path / kind, kind=kind)
        if e.cd().returncode != 0:  # 事前の批評の記録・壊す場面・受け入れ・変異の表が無くても合格
            bad.append(f"{kind} の合格")
    e = Env(tmp_path / "read2", kind="読む")
    e.write(e.text().replace("## 出典の決まり\n", "## 別\n"))
    r = e.cd()
    if r.returncode != 1 or "出典の決まり" not in r.stdout:
        bad.append("読む の出典の決まり無し")
    assert not bad, bad


# ---------------------------------------------------------------- 事前の批評の記録(U12)

def _pm(*recs):
    """recs: [(番号, sha256 か None(今の本文の値), [(印, 応答)])]"""
    def f(env):
        for p in env.d.parent.glob("DELEGATION_x_premortem*.md"):
            p.unlink()
        for n, h, items in recs:
            env.write_pm(n, premortem(h or body_hash(env.text()), items))
    return f


def _body_edit(env):
    t = env.text()
    pm = (env.d.parent / "DELEGATION_x_premortem1.md").read_text(encoding="utf-8")
    env.write(t.replace("- U2: 二つ目", "- U2: 二つ目を直した"))
    env.write_pm(1, pm)  # 記録は古い本文のまま


def _midway(env):
    env.write(env.text().replace("(まだ無い)", "- Q1: 作業者の問いへの答え"))


def _after_change(seen):
    def f(env):
        h = body_hash(env.text())
        env.write_pm(2, premortem(h, [("直す", "次の版で直す(x)")]))
        env.write(env.text().replace("- U2: 二つ目", "- U2: 二つ目(次の版)") +
                  f"\n## 事前の批評の後の変更\n\n見た版の sha256: {seen or h}\n- U2 の文を直した\n")
    return f


PM_CASES = [
    ("記録が無い", _pm(), "事前の批評"),
    ("本文を直した後の古い記録", _body_edit, "sha256"),
    ("途中の決めを足しても記録はそのまま", _midway, "ok"),
    ("応答が無い", _pm((1, None, [("直す", None)])), "応答"),
    ("応答の理由が空", _pm((1, None, [("直す", "直さない()")])), "応答"),
    ("応答 直さない", _pm((1, None, [("直す", "直さない(理由)")])), "ok"),
    ("応答 括弧の入れ子", _pm((1, None, [("直す", "直した(節「受け入れ」(U2)に足した)")])), "ok"),
    ("応答 全角の括弧", _pm((1, None, [("聞く", "オーナーに聞く（全角）")])), "ok"),
    ("応答 知らない語", _pm((1, None, [("直す", "考える(x)")])), "応答"),
    ("最後の指摘がファイルの終わり", _pm((1, None, [("直す", "直さない(x)"), ("聞く", None)])), "応答"),
    ("2 回目に直した", _pm((1, None, [("直す", "直した(x)")]), (2, None, [("直す", "直した(x)")])), "最後の回"),
    ("2 回目に直さない", _pm((1, None, [("直す", "直した(x)")]), (2, None, [("直す", "直さない(x)")])), "ok"),
    ("最後の回は番号の一番大きい記録", _pm((1, "0" * 64, [("直す", "直した(x)")]), (2, "1" * 64, [("直す", "次の版で直す(x)")]),
                                          (3, None, [("直す", "直さない(x)")])), "ok"),
    ("3 回目に直した", _pm((1, "0" * 64, [("直す", "直した(x)")]), (3, None, [("直す", "直した(x)")])), "最後の回"),
    ("最後の回の sha256 が違う", _pm((1, None, [("直す", "直した(x)")]), (2, "2" * 64, [("直す", "直さない(x)")])), "sha256"),
    ("次の版で直す 本文がそのまま", _pm((1, None, [("直す", "直した(x)")]), (2, None, [("直す", "次の版で直す(x)")])), "ok"),
    ("事前の批評の後の変更 見た版が合う", _after_change(None), "ok"),
    ("事前の批評の後の変更 見た版が違う", _after_change("0" * 64), "sha256"),
]


def test_premortem_checks(env):
    check_cases(env, PM_CASES)


# ---------------------------------------------------------------- 承認(U13)・1 回だけ読む(U14)

def test_require_approval_and_stamp_flag(env):
    assert env.cd().returncode == 0
    r = env.cd("--require-approval")
    assert r.returncode == 1 and "承認" in r.stdout
    env.write(env.text() + "\n## オーナーの承認\n\n- L-200「**委任してよい**」\n")
    assert env.cd("--require-approval").returncode == 0  # 承認の節は事前の批評の sha256 に入らない
    assert json.loads(env.stamp().read_text(encoding="utf-8"))["approved"] is True
    env.write(env.text().replace("L-200「**委任してよい**」", "L-200「**委任してよいよ**」"))
    r = env.cd("--require-approval")
    assert r.returncode == 1 and "L-200" in r.stdout


def test_reads_delegation_once(env):
    code = (
        "import builtins, runpy, sys, pathlib\n"
        f"target = {str(env.d)!r}\n"
        "n = [0]\n"
        "o_open, o_rb, o_rt = builtins.open, pathlib.Path.read_bytes, pathlib.Path.read_text\n"
        "def w_open(f, *a, **k):\n"
        "    if str(f) == target: n[0] += 1\n"
        "    return o_open(f, *a, **k)\n"
        "def w_rb(self):\n"
        "    if str(self) == target: n[0] += 1\n"
        "    return o_rb(self)\n"
        "def w_rt(self, *a, **k):\n"
        "    if str(self) == target: n[0] += 1\n"
        "    return o_rt(self, *a, **k)\n"
        "builtins.open, pathlib.Path.read_bytes, pathlib.Path.read_text = w_open, w_rb, w_rt\n"
        f"sys.argv = [{str(CD)!r}, target, '--owner-log', {str(env.log)!r}, '--fixed', {str(FIXED)!r},"
        f" '--scenes', {str(SCENES)!r}, '--root', {str(env.root)!r}]\n"
        "try:\n"
        f"    runpy.run_path({str(CD)!r}, run_name='__main__')\n"
        "except SystemExit:\n"
        "    pass\n"
        "print('READS', n[0])\n"
    )
    r = _run([sys.executable, "-c", code])
    assert re.search(r"^READS 1$", r.stdout, re.M), r.stdout


# ---------------------------------------------------------------- 受け取りの検め(U15)

GOOD_ROWS = ("| U1 | 見出しの一覧から 1 つ消す | tests/test_a.py::test_one[case1] |\n"
             "| U2 | 場面の検めを外す | tests/test_a.py::TestK::test_two |\n"
             "| H1 | git diff --stat | 3 本とも出ない(1 行の要約) |\n")


def _report(env, rows=GOOD_ROWS, questions="問いとして返したことは無い。", name="REPORT.md"):
    p = env.tmp / name
    p.write_text("# 報告\n\n## 変異の表\n\n| 番号 | 壊した変更 | 落ちた試験 |\n|---|---|---|\n" + rows +
                 "\n## 問いとして返したこと\n\n" + questions + "\n", encoding="utf-8")
    return p


REPORT_CASES = [
    ("合格(パラメータ付き・クラスの中の名前)", {}, "ok"),
    ("U1 は U10 に当たらない", {"rows": GOOD_ROWS.replace("| U1 |", "| U10 |")}, "U1"),
    ("1 欄に 2 つの番号", {"rows": "| U1・U2 | 両方 | tests/test_a.py::test_one |\n| H1 | git diff | 出ない |\n"}, "ok"),
    ("H1 の行が無い", {"rows": GOOD_ROWS.replace("| H1 | git diff --stat | 3 本とも出ない(1 行の要約) |\n", "")}, "H1"),
    ("落ちた試験が空", {"rows": GOOD_ROWS.replace("tests/test_a.py::test_one[case1]", "")}, "U1"),
    ("落ちなかった", {"rows": GOOD_ROWS.replace("tests/test_a.py::test_one[case1]", "落ちなかった")}, "U1"),
    ("関数が無い", {"rows": GOOD_ROWS.replace("test_one[case1]", "test_nothing")}, "test_nothing"),
    ("ファイルが無い", {"rows": GOOD_ROWS.replace("tests/test_a.py::test_one", "tests/nothing.py::test_one")}, "nothing.py"),
    ("封印の下の試験のファイル", {"rows": GOOD_ROWS.replace("tests/test_a.py::test_one", "tests/../docs/RESEARCH/WINDOW1/x.py::test_a")}, "封印"),
    ("問いの Q2 が途中の決めに無い", {"questions": "- Q2: これはどうするか"}, "Q2"),
    ("問いの節の文が無い", {"questions": "特に無し"}, "問いとして返したこと"),
]


def test_report_checks(env):
    assert env.cd().returncode == 0
    bad = []
    for name, kw, expect in REPORT_CASES:
        r = env.cr(_report(env, **kw))
        if (expect == "ok" and r.returncode != 0) or (expect != "ok" and (r.returncode != 1 or expect not in r.stdout)):
            bad.append(f"{name}: {r.returncode}: {r.stdout.strip()[:200]}")
    assert not bad, "\n".join(bad)


def test_report_stamp_and_delegation_recheck(env, tmp_path):
    p = _report(env)
    assert env.cr(p).returncode == 0 and not env.stamp().exists()  # 受け取りは印を書かない
    env.stamp().write_text('{"delegation_sha256": "' + "0" * 64 + '"}', encoding="utf-8")
    assert env.cr(p).returncode == 0  # 印は読まない
    env.write(env.text().replace("(まだ無い)", "- Q2: こうする"))
    assert env.cr(_report(env, questions="- Q2: これはどうするか")).returncode == 0  # 途中の決めは記録の sha256 に入らない
    env.write(env.text().replace("- U2: 二つ目", "- U2: 二つ目を直した"))
    r = env.cr(p)
    assert r.returncode == 1 and "sha256" in r.stdout  # 委任文の検めをやり直す
    q = tmp_path / "R2.md"
    q.write_text("# 報告\n\n## 変異の表\n\n| 番号 | 壊した変更 | 落ちた試験 |\n|---|---|---|\n" + GOOD_ROWS, encoding="utf-8")
    env.reset()
    r = env.cr(q)
    assert r.returncode == 1 and "問いとして返したこと" in r.stdout
    assert env.cr(tmp_path / "none.md").returncode == 2


def test_report_read_kind(tmp_path):
    e = Env(tmp_path, kind="読む")
    p = tmp_path / "R.md"
    p.write_text("# 報告\n\n## 結果\n\n| # | 主張 | 出典 |\n|---|---|---|\n| 1 | a | `src/a.py:1` |\n| 2 | b |  |\n"
                 "\n## 問いとして返したこと\n\n問いとして返したことは無い。\n", encoding="utf-8")
    r = e.cr(p)
    assert r.returncode == 1 and "出典" in r.stdout
    p.write_text("# 報告\n\n## 問いとして返したこと\n\n問いとして返したことは無い。\n", encoding="utf-8")
    r = e.cr(p)
    assert r.returncode == 1 and "結果" in r.stdout
