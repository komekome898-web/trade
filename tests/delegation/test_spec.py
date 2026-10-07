"""委任文の検め(`check_delegation.py`)と報告の受け取りの検め(`check_report.py`)の受け入れの試験。

リードが書いた(L-791「**測定に限らず全ての委任において、委任のミスでやり直しが発生しない委任文の書き方と仕組み**」)。
事前の批評 2 回で、散文の受け入れは読み方の「決まっていない」を回ごとに新しく生んだ(1 回目 40 件、2 回目 33 件。
`docs/DISCUSSIONS/2026-10-07_delegation_redesign/DELEGATION_checker_premortem{1,2}.md`)。そこで受け入れをこの試験で渡す。
作業者は試験を変えずに通す(変えたいときは問いとして返す)。

道具の置き場: 環境変数 `DELEGATION_TOOLS_DIR`(無ければ `scripts/delegation/`)。道具が無ければこの組は飛ばす(作る前の全体の試験を
落とさないため)。受け取りのときは、道具がある状態で飛ばしが 0 であることを確かめる。

道具の口(この試験が決める):
- `check_delegation.py <委任文> --owner-log P --fixed P --scenes P --root DIR [--require-approval] [--print-hash]`
- `check_report.py <報告> --delegation <委任文> --owner-log P --fixed P --scenes P --root DIR`
- `--root` は、読んだ事実の確かめの欄のパスと、変異の表の試験のファイルを解く根。既定は道具の置き場から決めたリポジトリの根。
- 終了コード: 0 合格 / 1 検めの失敗 / 2 入力の誤り(ファイルが無い・ディレクトリ・UTF-8 でない)。どの入力でも標準エラーに
  `Traceback` を出さない。失敗の行は全部、標準出力に日本語で出す(複数の欠けは全部出す)。
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
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


# ---------------------------------------------------------------- 作り物

OWNER_LOG = (
    "| L番号 | 日付 | 種類 | オーナーの逐語 | 読み |\n"
    "|---|---|---|---|---|\n"
    "| L-100 | d | 決定 | 「**甲の\t乙を作れ　すぐに**」 | x |\n"
    "| L-277 | d | 決定 | 「**一つ目**」 | x |\n"
    "| L-277 | d | 決定 | 「**二つ目の行**」 | x |\n"
    "| L-499a | d | 決定 | 「**枝の番号の行**」 | x |\n"
    "| L-D01 | d | 決定 | 「**Dの番号の行**」 | x |\n"
    "| L-200 | d | 承認 | 「**委任してよい**」 | x |\n"
)


def _fixed_section() -> str:
    t = FIXED.read_text(encoding="utf-8")
    sec = t.split("## 決まった制約\n", 1)[1]
    return "## 決まった制約\n" + sec.split("\n## ", 1)[0].rstrip("\n") + "\n"


def make_delegation(kind: str = "作る") -> str:
    scenes = "".join(f"| {n} | U1 |\n" if i % 2 == 0 else f"| {n} | この委任には無い(試しの理由) |\n"
                     for i, n in enumerate(SCENE_NAMES))
    decide = "".join(f"| {k} | 決めた |\n" for k in
                     ("出力の置き場", "分母・数え方", "比べの方法", "確かめ方", "依存", "絞り方・選び方", "単位・通貨のそろえ方"))
    parts = [
        "# 委任文: 試し\n\n",
        f"種類: {kind}\n\n",
        "## 着手前の表\n表を出す。\n\n",
        "## 目的(オーナーの逐語)\n- L-100「**甲の 乙を作れ すぐに**」\n\n",
        "## 読んだ事実\n\n| # | 事実 | 確かめ |\n|---|---|---|\n"
        "| データ | 無い | この委任には無い(市場のデータを使わない) |\n"
        "| 既存の決まり | 参照 | `src/a.py:2` |\n"
        "| 列の意味 | 列 | `grep -n x src/a.py` → 2 行目に x |\n\n",
        "## 決めてよいこと・決めてはいけないこと\n\n| 選び | 決め |\n|---|---|\n" + decide + "\n",
        "## 変えないもの\n\n- H1: 何も変えない。確かめ: git diff\n\n",
    ]
    if kind == "作る":
        parts += [
            "## 壊す場面\n\n| 場面 | 書いたこと |\n|---|---|\n" + scenes + "\n",
            "## 受け入れ\n\n- U1: 一つ目\n- U2: 二つ目\n\n",
            "## 変異の表\n\n形: | 番号 | 壊した変更 | 落ちた試験 |\n\n",
        ]
    if kind == "読む":
        parts += ["## 出典の決まり\n\n表の最後の列に出典。\n\n"]
    parts += [
        _fixed_section() + "\n",
        "## 終わる条件と上限\n\n- 終わる条件: 全部通る\n- 上限: 2 周\n\n",
        "## 報告\n\n- 書く\n\n",
        "## 途中の決め\n\n(まだ無い)\n",
    ]
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


def premortem(h: str, items: list[tuple[str, str]]) -> str:
    lines = [f"委任文 sha256: {h}", "", "## 問1"]
    for mark, resp in items:
        lines.append(f"- [{mark}] 指摘の文(括弧(入れ子)を含む)")
        if resp is not None:
            lines.append(f"  応答: {resp}")
    return "\n".join(lines) + "\n"


class Env:
    def __init__(self, tmp: Path, kind: str = "作る"):
        self.tmp = tmp
        self.root = tmp / "root"
        (self.root / "src").mkdir(parents=True)
        (self.root / "src" / "a.py").write_text("x = 1\nx = 2\nx = 3\n", encoding="utf-8")
        (self.root / "tests").mkdir()
        (self.root / "tests" / "test_a.py").write_text("def test_one():\n    pass\n\nclass TestK:\n    def test_two(self):\n        pass\n", encoding="utf-8")
        self.log = tmp / "OWNER_LOG.md"
        self.log.write_text(OWNER_LOG, encoding="utf-8")
        self.d = tmp / "work" / "DELEGATION_x.md"
        self.d.parent.mkdir()
        self.write(make_delegation(kind))
        if kind == "作る":
            self.write_pm(1, premortem(body_hash(self.text()), [("直す", "直した(節「受け入れ」(U2))"), ("聞く", "オーナーに聞く(L-200)")]))

    def text(self) -> str:
        return self.d.read_text(encoding="utf-8")

    def write(self, t: str) -> None:
        self.d.write_text(t, encoding="utf-8")

    def write_pm(self, n: int, t: str) -> None:
        (self.d.parent / f"DELEGATION_x_premortem{n}.md").write_text(t, encoding="utf-8")

    def rehash_pm(self) -> None:
        p = self.d.parent / "DELEGATION_x_premortem1.md"
        t = p.read_text(encoding="utf-8").split("\n", 1)[1]
        p.write_text(f"委任文 sha256: {body_hash(self.text())}\n" + t, encoding="utf-8")

    def stamp(self) -> Path:
        return self.d.parent / "DELEGATION_x.stamp.json"

    def run_cd(self, *extra: str, path: Path | None = None):
        return _run([sys.executable, str(CD), str(path or self.d), "--owner-log", str(self.log), "--fixed", str(FIXED),
                     "--scenes", str(SCENES), "--root", str(self.root), *extra])

    def run_cr(self, report: Path):
        return _run([sys.executable, str(CR), str(report), "--delegation", str(self.d), "--owner-log", str(self.log),
                     "--fixed", str(FIXED), "--scenes", str(SCENES), "--root", str(self.root)])


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert "Traceback" not in r.stderr, r.stderr
    return r


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


def ok(r):
    assert r.returncode == 0, r.stdout + r.stderr


def fails(r, *words):
    assert r.returncode == 1, (r.returncode, r.stdout, r.stderr)
    for w in words:
        assert w in r.stdout, (w, r.stdout)


# ---------------------------------------------------------------- 合格と印

def test_valid_passes_and_writes_stamp(env):
    r = env.run_cd()
    ok(r)
    import json
    s = json.loads(env.stamp().read_text(encoding="utf-8"))
    assert s["delegation_sha256"] == hashlib.sha256(env.d.read_bytes()).hexdigest()
    assert s["body_sha256"] == body_hash(env.text())
    assert s["kind"] == "作る"
    assert s["premortem"].endswith("DELEGATION_x_premortem1.md")


def test_print_hash_is_bare_64_hex_and_skips_checks(env):
    env.write(env.text().replace("## 報告", "## 報告X"))  # 検めでは落ちる形でも
    r = env.run_cd("--print-hash")
    assert r.returncode == 0
    assert r.stdout == body_hash(env.text()) + "\n"


def test_hash_rule_literal():
    """事前の批評の sha256 の決まりを、固定のバイト列と固定の値で決める(道具の値もこれと同じでなければならない)。"""
    t = "# x\n\n種類: 作る\n\n## 目的(オーナーの逐語)\n本文\n## 途中の決め\n- Q1: 答え\n## 報告\n終わり"
    assert body_hash(t) == "e586ff9d777883eb42fbbf85488bbc2f1e258c001697417b316f2360f69ed3e8"
    t2 = "# x\n## 報告\n終わり\n## 途中の決め\n- Q1: 答え"  # 終わりの節・最後の改行なし
    assert body_hash(t2) == "d3a7e3b56523c32616ee2e09cad50f1ab1f955e9182ce0b5ea74cd01ecdb9190"


@pytest.mark.parametrize("t,expect", [
    ("# x\n\n種類: 作る\n\n## 目的(オーナーの逐語)\n本文\n## 途中の決め\n- Q1: 答え\n## 報告\n終わり",
     "e586ff9d777883eb42fbbf85488bbc2f1e258c001697417b316f2360f69ed3e8"),
    ("# x\n## 報告\n終わり\n## 途中の決め\n- Q1: 答え", "d3a7e3b56523c32616ee2e09cad50f1ab1f955e9182ce0b5ea74cd01ecdb9190"),
])
def test_tool_hash_matches_literal(tmp_path, t, expect):
    p = tmp_path / "d.md"
    p.write_text(t, encoding="utf-8")
    r = _run([sys.executable, str(CD), str(p), "--print-hash"])
    assert r.stdout.strip() == expect


def test_failure_removes_old_stamp(env):
    ok(env.run_cd())
    assert env.stamp().exists()
    env.write(env.text().replace("## 報告\n", "## 報告X\n"))
    env.rehash_pm()
    fails(env.run_cd(), "報告")
    assert not env.stamp().exists()


def test_input_error_exit_2_and_removes_stamp(env, tmp_path):
    ok(env.run_cd())
    r = env.run_cd(path=tmp_path / "nothing.md")
    assert r.returncode == 2
    # OWNER_LOG がディレクトリ・委任文が UTF-8 でない
    r = _run([sys.executable, str(CD), str(env.d), "--owner-log", str(tmp_path), "--fixed", str(FIXED),
              "--scenes", str(SCENES), "--root", str(env.root)])
    assert r.returncode == 2
    assert not env.stamp().exists()
    env.d.write_bytes(b"\xff\xfe\x00bad")
    assert env.run_cd().returncode == 2


def test_all_failures_listed_together(env):
    t = env.text().replace("## 報告\n", "## 報告X\n").replace("| 依存 | 決めた |\n", "")
    env.write(t)
    env.rehash_pm()
    fails(env.run_cd(), "報告", "依存")


# ---------------------------------------------------------------- 1 種類の行

@pytest.mark.parametrize("pos,good", [(3, True), (5, True), (6, False)])
def test_kind_line_within_first_5(env, pos, good):
    lines = env.text().split("\n")
    kind = lines.pop(2)  # 3 行目
    lines.insert(pos - 1, kind)
    t = "\n".join(lines)
    if pos != 3:
        t = t.replace("# 委任文: 試し\n", "# 委任文: 試し\n", 1)
    env.write(t)
    env.rehash_pm()
    r = env.run_cd()
    if good:
        ok(r)
    else:
        fails(r, "種類")


@pytest.mark.parametrize("bad", ["", "種類: 作業", "種類: 作る\n種類: 読む"])
def test_kind_line_bad(env, bad):
    env.write(env.text().replace("種類: 作る", bad, 1))
    env.rehash_pm()
    fails(env.run_cd(), "種類")


# ---------------------------------------------------------------- 2 見出し

CORE = ["## 着手前の表", "## 目的(オーナーの逐語)", "## 読んだ事実", "## 決めてよいこと・決めてはいけないこと",
        "## 変えないもの", "## 決まった制約", "## 終わる条件と上限", "## 報告"]
MAKE = ["## 壊す場面", "## 受け入れ", "## 変異の表"]


@pytest.mark.parametrize("h", CORE + MAKE)
def test_missing_heading(env, h):
    env.write(env.text().replace(h + "\n", "## 別の見出し\n", 1))
    env.rehash_pm()
    fails(env.run_cd(), h[3:])


def test_read_kind_needs_source_rule_not_make_sections(tmp_path):
    e = Env(tmp_path, kind="読む")
    ok(e.run_cd())  # 事前の批評の記録・壊す場面・受け入れ・変異の表が無くても合格
    e.write(e.text().replace("## 出典の決まり\n", "## 別\n"))
    fails(e.run_cd(), "出典の決まり")


def test_critic_kind_core_only(tmp_path):
    e = Env(tmp_path, kind="批評")
    ok(e.run_cd())


# ---------------------------------------------------------------- 3 引用

def test_quote_whitespace_normalized_tab_and_fullwidth(env):
    ok(env.run_cd())  # OWNER_LOG はタブ・全角の空白、委任文は半角の空白


@pytest.mark.parametrize("old,new", [
    ("「**甲の 乙を作れ すぐに**」", "「**甲の 乙を作れ すぐ**」"),       # 1 字違い
    ("L-100「**", "L-999「**"),                                           # 無い番号
])
def test_quote_mismatch(env, old, new):
    env.write(env.text().replace(old, new))
    env.rehash_pm()
    fails(env.run_cd(), "L-")


def test_quote_reverse_direction_and_adjacent(env):
    t = env.text().replace("- L-100「**甲の 乙を作れ すぐに**」",
                           "- 「**一つ目**」「**二つ目の行**」L-277\n- 「**枝の番号の行**」L-499a\n- L-D01「**Dの番号の行**」")
    env.write(t)
    env.rehash_pm()
    ok(env.run_cd())  # L-277 は 2 行あり、どちらかに含まれればよい。並んだ 2 つは後ろの番号に付く
    env.write(t.replace("「**二つ目の行**」", "「**二つ目の列**」"))
    env.rehash_pm()
    fails(env.run_cd(), "L-277")


def test_unnumbered_quote_in_purpose_fails(env):
    env.write(env.text().replace("## 目的(オーナーの逐語)\n", "## 目的(オーナーの逐語)\n- 「**番号の無い引用**」\n"))
    env.rehash_pm()
    fails(env.run_cd(), "番号")


def test_unnumbered_quote_outside_purpose_ok(env):
    env.write(env.text().replace("## 報告\n\n- 書く", "## 報告\n\n- 書く。例: `「**バッククォートの中**」`"))
    env.rehash_pm()
    ok(env.run_cd())


# ---------------------------------------------------------------- 4 読んだ事実

@pytest.mark.parametrize("cell,good", [
    ("`src/a.py:3`", True),               # 行の数ちょうど
    ("`src/a.py:4`", False),              # 1 多い
    ("`src/a.py:1-3`", True),
    ("`src/a.py:1-4`", False),            # 後ろの数で比べる
    ("`src/nothing.py:1`", False),        # 無いパス
    ("`src/a.py:1` と `src/a.py:9`", False),   # 全部を求める
    ("`grep x src/a.py` → 出た", True),
    ("`grep x src/a.py`", False),          # → が無い
    ("`grep x src/a.py` → ", False),       # 要点が空
    ("この委任には無い(x)", True),          # 理由 1 字
    ("この委任には無い（全角の括弧）", True),
    ("この委任には無い()", False),
    ("", False),
    ("見た", False),
    ("07:31 に見た", False),               # 時刻はパスでない(拡張子の無い語は拾わない)
])
def test_fact_cell(env, cell, good):
    env.write(env.text().replace("| 既存の決まり | 参照 | `src/a.py:2` |", f"| 既存の決まり | 参照 | {cell} |"))
    env.rehash_pm()
    r = env.run_cd()
    if good:
        ok(r)
    else:
        fails(r, "読んだ事実")


def test_fact_cell_backtick_pipe_not_a_separator(env):
    cell = '`grep "^| L-" src/a.py \\| wc -l` → 0'
    env.write(env.text().replace("| 既存の決まり | 参照 | `src/a.py:2` |", f"| 既存の決まり | 参照 | {cell} |"))
    env.rehash_pm()
    ok(env.run_cd())


@pytest.mark.parametrize("row", ["データ", "既存の決まり", "列の意味"])
def test_fact_required_rows(env, row):
    t = "\n".join(l for l in env.text().split("\n") if not l.startswith(f"| {row} |"))
    env.write(t)
    env.rehash_pm()
    fails(env.run_cd(), row)


@pytest.mark.parametrize("p", [
    "docs/RESEARCH/WINDOW1/x.md:1",
    "./backtest_data/phase2_sealed/../phase2_sealed/y.csv:1",
    "Docs/Research/Window1/z.md:1",
])
def test_seal_path_fails_without_opening(env, p):
    # 封印の置き場に「開くと止まる」名前付きパイプを置く。開けば試験は時間切れで落ちる
    target = env.root / Path(os.path.normpath(p.split(":")[0]))
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        os.mkfifo(target)
    env.write(env.text().replace("| 既存の決まり | 参照 | `src/a.py:2` |", f"| 既存の決まり | 参照 | `{p}` |"))
    env.rehash_pm()
    fails(env.run_cd(), "封印")


def test_seal_path_absolute_and_outside_root(env):
    for p in (f"{env.root}/docs/RESEARCH/WINDOW1/a.md:1", "../root/docs/RESEARCH/WINDOW1/a.md:1"):
        env.write(make_delegation().replace("| 既存の決まり | 参照 | `src/a.py:2` |", f"| 既存の決まり | 参照 | `{p}` |"))
        env.rehash_pm()
        fails(env.run_cd(), "封印")


def test_seal_names_in_fixed_section_do_not_fail(env):
    ok(env.run_cd())  # 決まった制約の節に封印の名前があるだけでは失敗しない


# ---------------------------------------------------------------- 5 決めてよいこと

@pytest.mark.parametrize("k", ["出力の置き場", "分母・数え方", "比べの方法", "確かめ方", "依存", "絞り方・選び方", "単位・通貨のそろえ方"])
def test_decide_rows(env, k):
    t = env.text()
    env.write(t.replace(f"| {k} | 決めた |\n", ""))
    env.rehash_pm()
    fails(env.run_cd(), k)
    env.write(t.replace(f"| {k} | 決めた |\n", f"| {k} |  |\n"))
    env.rehash_pm()
    fails(env.run_cd(), k)


# ---------------------------------------------------------------- 6 壊す場面

@pytest.mark.parametrize("i", range(12))
def test_scene_row_missing(env, i):
    name = SCENE_NAMES[i]
    t = "\n".join(l for l in env.text().split("\n") if not l.startswith(f"| {name} |"))
    env.write(t)
    env.rehash_pm()
    fails(env.run_cd(), name)


@pytest.mark.parametrize("cell", ["", "書いた", "U99", "この委任には無い()"])
def test_scene_cell_bad(env, cell):
    name = SCENE_NAMES[0]
    t = re.sub(rf"^\| {re.escape(name)} \|.*$", f"| {name} | {cell} |", env.text(), flags=re.M)
    env.write(t)
    env.rehash_pm()
    fails(env.run_cd(), name)


def test_scene_name_one_char_changed(env):
    name = SCENE_NAMES[1]
    env.write(env.text().replace(f"| {name} |", f"| {name}X |"))
    env.rehash_pm()
    fails(env.run_cd(), name)


def test_scene_rows_out_of_order_fail(env):
    lines = env.text().split("\n")
    idx = [i for i, l in enumerate(lines) if any(l.startswith(f"| {n} |") for n in SCENE_NAMES)]
    lines[idx[0]], lines[idx[1]] = lines[idx[1]], lines[idx[0]]
    env.write("\n".join(lines))
    env.rehash_pm()
    fails(env.run_cd(), "壊す場面")


def test_scene_u_reference_boundary(env):
    # U1 を定義から消し U10 だけにすると、場面の欄の U1 は「定義が無い」で落ちる(U1 は U10 に当たらない)
    env.write(env.text().replace("- U1: 一つ目", "- U10: 一つ目"))
    env.rehash_pm()
    fails(env.run_cd(), "U1")


# ---------------------------------------------------------------- 7 番号

def test_u_duplicate_fails_gap_ok(env):
    t = env.text()
    env.write(t.replace("- U2: 二つ目", "- U1: 二つ目"))
    env.rehash_pm()
    fails(env.run_cd(), "U1")
    env.write(t.replace("- U2: 二つ目", "- U3: 三つ目"))
    env.rehash_pm()
    ok(env.run_cd())


def test_no_u_definitions_fails(env):
    env.write(env.text().replace("- U1: 一つ目\n- U2: 二つ目\n", "(無し)\n"))
    env.rehash_pm()
    fails(env.run_cd(), "受け入れ")


def test_h_none_line_ok_and_missing_fails(env):
    t = env.text()
    env.write(t.replace("- H1: 何も変えない。確かめ: git diff", "- H0: この委任には無い(新しく作るだけ)"))
    env.rehash_pm()
    ok(env.run_cd())
    env.write(t.replace("- H1: 何も変えない。確かめ: git diff", "何も無い"))
    env.rehash_pm()
    fails(env.run_cd(), "変えないもの")


# ---------------------------------------------------------------- 8 決まった制約

def test_fixed_one_char_changed_fails(env):
    env.write(env.text().replace("worktree add", "worktree  add", 1))
    env.rehash_pm()
    fails(env.run_cd(), "決まった制約")


def test_fixed_line_removed_or_added_fails(env):
    t = env.text()
    first = _fixed_section().split("\n")[1]
    env.write(t.replace(first + "\n", "", 1))
    env.rehash_pm()
    fails(env.run_cd(), "決まった制約")
    env.write(t.replace(first + "\n", first + "\n- 足した行\n", 1))
    env.rehash_pm()
    fails(env.run_cd(), "決まった制約")


def test_fixed_trailing_space_and_blank_lines_ok(env):
    first = _fixed_section().split("\n")[1]
    env.write(env.text().replace(first + "\n", first + "   \n", 1).replace("\n## 終わる条件と上限", "\n\n\n## 終わる条件と上限"))
    env.rehash_pm()
    ok(env.run_cd())


# ---------------------------------------------------------------- 9 終わる条件と上限

def test_end_and_limit_words(env):
    env.write(env.text().replace("- 上限: 2 周", "- 限り: 2 周"))
    env.rehash_pm()
    fails(env.run_cd(), "上限")


# ---------------------------------------------------------------- 10 事前の批評の記録

def test_premortem_missing_fails(env):
    (env.d.parent / "DELEGATION_x_premortem1.md").unlink()
    fails(env.run_cd(), "事前の批評")


def test_premortem_hash_mismatch_after_body_edit(env):
    ok(env.run_cd())
    env.write(env.text().replace("- U2: 二つ目", "- U2: 二つ目を直した"))
    fails(env.run_cd(), "sha256")
    assert not env.stamp().exists()


def test_adding_midway_decision_keeps_premortem_valid(env):
    h = body_hash(env.text())
    env.write(env.text().replace("(まだ無い)", "- Q1: 作業者の問いへの答え"))
    r = env.run_cd("--print-hash")
    assert r.stdout.strip() == h
    ok(env.run_cd())


@pytest.mark.parametrize("resp,good", [
    (None, False),
    ("直さない()", False),
    ("直さない(理由)", True),
    ("直した(節「受け入れ」(U2)に足した)", True),     # 括弧の入れ子: 行末の閉じ括弧までを中身とする
    ("オーナーに聞く（全角）", True),
    ("考える(x)", False),
])
def test_premortem_response_values(env, resp, good):
    env.write_pm(1, premortem(body_hash(env.text()), [("直す", resp)]))
    r = env.run_cd()
    if good:
        ok(r)
    else:
        fails(r, "応答")


def test_premortem_last_finding_at_end_of_file(env):
    env.write_pm(1, premortem(body_hash(env.text()), [("直す", "直さない(x)"), ("聞く", None)]))
    fails(env.run_cd(), "応答")


def test_second_round_is_last_and_cannot_say_fixed(env):
    h = body_hash(env.text())
    env.write_pm(2, premortem(h, [("直す", "直した(x)")]))
    fails(env.run_cd(), "2 回目")
    env.write_pm(2, premortem(h, [("直す", "直さない(x)")]))
    ok(env.run_cd())


def test_next_version_response_needs_after_change_section(env):
    h = body_hash(env.text())
    env.write_pm(2, premortem(h, [("直す", "次の版で直す(3 版目で)")]))
    ok(env.run_cd())  # 委任文を変えていなければ通る
    # 本文を変えたら、事前の批評の後の変更の節に「見た版の sha256」を書けば通る
    env.write(env.text().replace("- U2: 二つ目", "- U2: 二つ目(次の版)") +
              f"\n## 事前の批評の後の変更\n\n見た版の sha256: {h}\n- U2 の文を直した\n")
    ok(env.run_cd())
    # 見た版の sha256 が記録と違えば落ちる
    env.write(env.text().replace(f"見た版の sha256: {h}", "見た版の sha256: " + "0" * 64))
    fails(env.run_cd(), "sha256")


def test_next_version_not_allowed_in_round_1_when_round_2_exists(env):
    h = body_hash(env.text())
    env.write_pm(1, premortem(h, [("直す", "次の版で直す(x)")]))
    env.write_pm(2, premortem(h, [("直す", "直さない(x)")]))
    fails(env.run_cd(), "次の版で直す")


# ---------------------------------------------------------------- 承認(L-793)

def test_require_approval(env):
    ok(env.run_cd())
    fails(env.run_cd("--require-approval"), "承認")
    env.write(env.text() + "\n## オーナーの承認\n\n- L-200「**委任してよい**」\n")
    ok(env.run_cd("--require-approval"))  # 承認の節は事前の批評の sha256 に入らない
    env.write(env.text().replace("L-200「**委任してよい**」", "L-200「**委任してよいよ**」"))
    fails(env.run_cd("--require-approval"), "L-200")


# ---------------------------------------------------------------- 1 回だけ読む

def test_reads_delegation_once(env, tmp_path):
    """道具は委任文を 1 回だけ読む: 同じプロセスで読み込みを数える。"""
    code = (
        "import builtins, runpy, sys, io\n"
        f"target = {str(env.d)!r}\n"
        "count = {'n': 0}\n"
        "orig = builtins.open\n"
        "def wrapped(f, *a, **k):\n"
        "    if str(f) == target: count['n'] += 1\n"
        "    return orig(f, *a, **k)\n"
        "builtins.open = wrapped\n"
        "import pathlib\n"
        "orb, ort = pathlib.Path.read_bytes, pathlib.Path.read_text\n"
        "def rb(self): \n"
        "    if str(self) == target: count['n'] += 1\n"
        "    return orb(self)\n"
        "def rt(self, *a, **k):\n"
        "    if str(self) == target: count['n'] += 1\n"
        "    return ort(self, *a, **k)\n"
        "pathlib.Path.read_bytes, pathlib.Path.read_text = rb, rt\n"
        f"sys.argv = [{str(CD)!r}, target, '--owner-log', {str(env.log)!r}, '--fixed', {str(FIXED)!r}, '--scenes', {str(SCENES)!r}, '--root', {str(env.root)!r}]\n"
        "try:\n"
        f"    runpy.run_path({str(CD)!r}, run_name='__main__')\n"
        "except SystemExit:\n"
        "    pass\n"
        "print('READS', count['n'])\n"
    )
    r = _run([sys.executable, "-c", code])
    assert "READS 1" in r.stdout, r.stdout


# ---------------------------------------------------------------- check_report

def _report(env, rows: str, questions: str = "問いとして返したことは無い。") -> Path:
    p = env.tmp / "REPORT.md"
    p.write_text("# 報告\n\n## 変異の表\n\n| 番号 | 壊した変更 | 落ちた試験 |\n|---|---|---|\n" + rows +
                 "\n## 問いとして返したこと\n\n" + questions + "\n", encoding="utf-8")
    return p


GOOD_ROWS = ("| U1 | 見出しの一覧から 1 つ消す | tests/test_a.py::test_one |\n"
             "| U2 | 場面の検めを外す | tests/test_a.py::TestK::test_two |\n"
             "| H1 | git diff --stat | 3 本とも出ない(1 行の要約) |\n")


def test_report_ok(env):
    ok(env.run_cd())
    ok(env.run_cr(_report(env, GOOD_ROWS)))


def test_report_param_test_name_ok(env):
    ok(env.run_cr(_report(env, GOOD_ROWS.replace("tests/test_a.py::test_one", "tests/test_a.py::test_one[case1]"))))


@pytest.mark.parametrize("rows,word", [
    (GOOD_ROWS.replace("| U1 |", "| U10 |"), "U1"),                  # U10 は U1 に当たらない
    (GOOD_ROWS.replace("| H1 | git diff --stat | 3 本とも出ない(1 行の要約) |\n", ""), "H1"),
    (GOOD_ROWS.replace("tests/test_a.py::test_one", ""), "U1"),
    (GOOD_ROWS.replace("tests/test_a.py::test_one", "tests/test_a.py::test_nothing"), "test_nothing"),
    (GOOD_ROWS.replace("tests/test_a.py::test_one", "tests/nothing.py::test_one"), "nothing.py"),
    (GOOD_ROWS.replace("tests/test_a.py::test_one", "tests/../docs/RESEARCH/WINDOW1/x.py::test_a"), "封印"),
])
def test_report_mutation_table_bad(env, rows, word):
    fails(env.run_cr(_report(env, rows)), word)


def test_report_two_ids_in_one_cell(env):
    rows = ("| U1・U2 | 両方 | tests/test_a.py::test_one |\n"
            "| H1 | git diff --stat | 出ない |\n")
    ok(env.run_cr(_report(env, rows)))


def test_report_rechecks_delegation_not_stamp(env):
    ok(env.run_cd())
    env.write(env.text().replace("- U2: 二つ目", "- U2: 二つ目を直した"))  # 事前の批評と合わなくなる
    fails(env.run_cr(_report(env, GOOD_ROWS)), "sha256")


def test_report_forged_stamp_does_not_matter(env):
    ok(env.run_cd())
    env.stamp().write_text('{"delegation_sha256": "' + "0" * 64 + '"}', encoding="utf-8")
    r = env.run_cr(_report(env, GOOD_ROWS))
    ok(r)  # 印は信じない。委任文の検めをやり直して通れば合格


def test_report_does_not_write_stamp(env):
    assert not env.stamp().exists()
    ok(env.run_cr(_report(env, GOOD_ROWS)))
    assert not env.stamp().exists()  # 受け取りの検めは印を書かない・消さない


def test_report_questions_need_midway_decisions(env):
    q = "- Q2: これはどうするか"
    fails(env.run_cr(_report(env, GOOD_ROWS, q)), "Q2")
    env.write(env.text().replace("(まだ無い)", "- Q2: こうする"))
    ok(env.run_cr(_report(env, GOOD_ROWS, q)))


def test_report_questions_section_required(env):
    p = env.tmp / "R2.md"
    p.write_text("# 報告\n\n## 変異の表\n\n| 番号 | 壊した変更 | 落ちた試験 |\n|---|---|---|\n" + GOOD_ROWS, encoding="utf-8")
    fails(env.run_cr(p), "問いとして返したこと")
    fails(env.run_cr(_report(env, GOOD_ROWS, "特に無し")), "問いとして返したこと")


def test_report_read_kind_source_column(tmp_path):
    e = Env(tmp_path, kind="読む")
    p = tmp_path / "R.md"
    p.write_text("# 報告\n\n## 結果\n\n| # | 主張 | 出典 |\n|---|---|---|\n| 1 | a | `src/a.py:1` |\n| 2 | b |  |\n"
                 "\n## 問いとして返したこと\n\n問いとして返したことは無い。\n", encoding="utf-8")
    fails(e.run_cr(p), "出典")
    p.write_text("# 報告\n\n## 問いとして返したこと\n\n問いとして返したことは無い。\n", encoding="utf-8")
    fails(e.run_cr(p), "結果")  # 結果の節・表が無い


def test_report_input_error_exit_2(env, tmp_path):
    assert env.run_cr(tmp_path / "none.md").returncode == 2
