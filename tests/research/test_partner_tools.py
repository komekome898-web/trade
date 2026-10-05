"""相方の道具(`scripts/analysis/partner_brief.py`・`scripts/analysis/check_partner.py`)の試験。
L-705・L-706・L-707・L-711、案 `docs/DISCUSSIONS/2026-10-05_analysis_mechanism/PROPOSAL.md` §6。

文書・台帳・置き場・偽の封印の置き場はすべて一時ディレクトリに作る。実際の `docs/` は書き換えない(依頼の文・目標・
状態板・スキルは読むだけ)。本物の封印の置き場には触れない。

壊し方を試すとき(台本の写しに当てて試験が落ちるかを見る): 写しを `<X>/scripts/analysis/` に置き(partner_brief.py と
check_partner.py の両方。check_partner.py は同じ置き場の partner_brief.py を読む)、`<X>/scripts/check_findings_ledger.py`
に本物を写すか張る(partner_brief.py は自分の置き場の 2 つ上の scripts/ からそれを読む)。そのうえで環境変数
PARTNER_TOOLS_DIR=<X>/scripts/analysis を付けて走らせる。diag_skeleton.py は本物を読む。
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AN = Path(os.environ.get("PARTNER_TOOLS_DIR", ROOT / "scripts" / "analysis"))
REQUEST = ROOT / ".claude" / "skills" / "analysis-lens" / "PARTNER_REQUEST.md"
GOAL = ROOT / "docs" / "PROJECT_GOAL.md"
STATUS = ROOT / "docs" / "OWNER_STATUS.md"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pb = _load("partner_brief", AN / "partner_brief.py")
cpt = _load("check_partner", AN / "check_partner.py")
ds = _load("diag_skeleton", ROOT / "scripts" / "analysis" / "diag_skeleton.py")

# ---------------------------------------------------------------- 作り物の文書と台帳

LEDGER = """# 知見台帳

## 書式

```
### K-001 見本(囲みの中は数えない)
- 観察: 見本
```

## 観察

### K-010 既にある行
- 観察: 短く持った取引で稼ぎ、長く持った取引で失っている
- 出所: `docs/RESEARCH/FINDINGS_LEDGER.md` の表 1
- 状態: 開いている

### K-011 封印を指す行(バッククォート)
- 観察: 封印の置き場を出所にした行
- 出所: `docs/RESEARCH/WINDOW1/x.md`
- 状態: 開いている

### K-012 封印を指す行(裸)
- 観察: 裸のパス
- 出所: 裸 docs/RESEARCH/WINDOW1/y.csv
- 状態: 開いている

### K-013 封印を指す行(囲みの中)
- 観察: 囲み
```
cat `backtest_data/phase2_sealed/z.json`
```
- 状態: 開いている

## カード
"""

QUOTE_LINE = "写しの中の `quote/only.md` と K-010 は ⑤ の対象に数えない"


def make_doc(filled: dict[str, str | None], steps=("P", "D0", "D9b", "D10"), quote=(QUOTE_LINE,)) -> str:
    """骨組みの書式(`diag_skeleton.step_block`)で文書を作る。filled に無い・None の節は「(未記入)」のまま。"""
    L = ["# 診断 — x", "", "- 単位: x", ""]
    for s in steps:
        block = ds.step_block(s, f"## {s} 見出し", [f"手順 {s} の本文", *quote])
        content = filled.get(s)
        if content is not None:
            i = block.index(ds.EMPTY)
            block = block[:i] + content.split("\n") + block[i + 1:]
        L += block
    return "\n".join(L)


@pytest.fixture()
def env(tmp_path):
    led = tmp_path / "LEDGER.md"
    led.write_text(LEDGER, encoding="utf-8")
    return tmp_path, led


def brief(tmp_path, led, text, at, done="完了の形の逐語", name="2026-10-05_x.md", doc_dir=None, **kw):
    doc = (doc_dir or tmp_path) / name
    if text is not None:
        doc.write_text(text, encoding="utf-8")
    out = tmp_path / "out"
    args = ["--doc", str(doc), "--at", at, "--done", done, "--out-dir", str(out), "--ledger", str(led),
            "--request", str(kw.get("request", REQUEST)), "--goal", str(kw.get("goal", GOAL)),
            "--status", str(kw.get("status", STATUS)), "--repo", str(kw.get("repo", ROOT))]
    rc = pb.main(args)
    sub = out / Path(name).stem
    files = sorted(sub.glob("*.md")) if sub.is_dir() else []
    return rc, files


def part(text: str, head: str) -> str:
    m = re.search(rf"^## {re.escape(head)}.*?$(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert m, head
    return m.group(1)


FILLED = {"P": "中身P の前提", "D0": "中身D0", "D9b": "中身D9b の観察", "D10": "中身D10 の知見の文"}

# ---------------------------------------------------------------- partner_brief


def test_skeleton_fresh_block_is_unfilled():
    """骨組みが作ったままの「当てたこと」(案内の行 + 「(未記入)」)は未記入。案内の行の文が骨組みと揃っているか。"""
    text = "\n".join(ds.step_block("X", "## X 見出し", ["本文"]))
    assert pb.GUIDE in text
    assert pb.is_filled(text, "X") is False
    assert pb.is_filled(text.replace(ds.EMPTY, "書いた"), "X") is True
    assert pb.is_filled(text, "Y") is None


def test_request_part_matches_current_partner_request(env, capsys):
    tmp, led = env
    rc, files = brief(tmp, led, make_doc(FILLED), "D10")
    assert rc == 0, capsys.readouterr().err
    out = files[0].read_text(encoding="utf-8")
    req = REQUEST.read_text(encoding="utf-8")
    first = part(out, "① 依頼の文")
    for name in ("依頼", "返し方"):
        m = re.search(rf"^## {name}\n(.*?)(?=^## |\Z)", req, re.S | re.M)
        body = m.group(1).strip("\n")
        assert f"### {name}\n\n{body}\n" in first


@pytest.mark.parametrize("at,inside,outside", [
    ("P", ["中身P"], ["中身D9b", "中身D10", "中身D0"]),
    ("D9b", ["中身D9b"], ["中身P", "中身D10", "中身D0"]),
    ("D10", ["中身D10"], ["中身P", "中身D9b", "中身D0"]),
    ("push", ["中身D9b", "中身D10"], ["中身P", "中身D0"]),
])
def test_section_matches_at(env, capsys, at, inside, outside):
    tmp, led = env
    rc, files = brief(tmp, led, make_doc(FILLED), at)
    assert rc == 0, capsys.readouterr().err
    out = files[0].read_text(encoding="utf-8")
    target = part(out, "⑤ 対象")
    for w in inside:
        assert w in target
    for w in outside:
        assert w not in out
    assert pb.AT_FOCUS[at] in part(out, "② 時点")
    # スキルの写しの中のバッククォート・K 番号は ⑤ の対象に数えない(写しは ④ に写る)
    assert "quote/only.md" not in target and "K-010" not in target


@pytest.mark.parametrize("at,steps", [("P", ["P"]), ("D10", ["D10"]), ("push", ["D9b", "D10"])])
def test_skill_quote_of_at_step_is_copied(env, capsys, at, steps):
    """[7] 時点の節のスキルの写し(<!-- step:X --> 〜 <!-- /step:X --> の中)を ④ に写す。ほかの節の写しは写さない。"""
    tmp, led = env
    rc, files = brief(tmp, led, make_doc(FILLED), at)
    assert rc == 0, capsys.readouterr().err
    view = part(files[0].read_text(encoding="utf-8"), "④ オーナーの観点")
    for s in ["P", "D0", "D9b", "D10"]:
        assert (f"> 手順 {s} の本文" in view) == (s in steps)
    assert f"> {QUOTE_LINE}" in view


def test_k_rows_full_text_and_missing(env, capsys):
    tmp, led = env
    filled = dict(FILLED, D10="知見は K-010 と同じ向き。K-999 は無い番号。K-001 は見本。K-0105 は 4 桁")
    rc, files = brief(tmp, led, make_doc(filled), "D10")
    assert rc == 0, capsys.readouterr().err
    target = part(files[0].read_text(encoding="utf-8"), "⑤ 対象")
    row = LEDGER[LEDGER.index("### K-010"):LEDGER.index("### K-011")].rstrip("\n")
    assert row in target
    assert re.search(r"#### K-999\n\n台帳に無い", target)
    assert re.search(r"#### K-001\n\n台帳に無い", target)  # 書式の見本の囲みは台帳の行ではない
    assert "K-0105" not in re.findall(r"#### (\S+)", target)


def test_paths_listed_with_existence_and_fence_ignored(env, capsys):
    tmp, led = env
    (tmp / "have.md").write_text("x", encoding="utf-8")
    filled = dict(FILLED, D10="\n".join(["出力 `have.md` と `none/no.md`、指示 `--refresh`",
                                         "```", "`inside/fence.md`", "```"]))
    rc, files = brief(tmp, led, make_doc(filled), "D10", repo=tmp)
    assert rc == 0, capsys.readouterr().err
    out = files[0].read_text(encoding="utf-8")
    target = part(out, "⑤ 対象")
    assert "- `have.md`: 有る" in target
    assert f"- `none/no.md`: {pb.NOT_FOUND}" in target  # [6]「無い」と断定しない
    assert "根からは見つからない(相対の書き方かもしれない)" in target
    assert "- `--refresh`" not in target and "- `inside/fence.md`" not in target
    assert "\x00" not in out  # 有無の印が残らない


# ---- 封印([止める 1])。偽の封印の置き場を一時の根に作り、そこのファイルに触れないことも見る

@pytest.fixture()
def fake_root(tmp_path):
    r = tmp_path / "repo"
    (r / "docs" / "RESEARCH" / "WINDOW1").mkdir(parents=True)
    (r / "docs" / "RESEARCH" / "WINDOW1" / "a.csv").write_text("fake", encoding="utf-8")
    (r / "backtest_data" / "phase2_sealed").mkdir(parents=True)
    return r


@pytest.fixture()
def stat_spy(monkeypatch):
    """os.path.exists に渡されたパスを記録する(封印の置き場に有無の確かめが行かないことを見る)。"""
    seen = []
    real = os.path.exists

    def spy(p):
        seen.append(str(p))
        return real(p)

    monkeypatch.setattr(pb.os.path, "exists", spy)
    return seen


@pytest.mark.parametrize("d10", [
    "読んだのは `docs/RESEARCH/WINDOW1/a.csv`",                      # バッククォート
    "```\npython run.py --in `docs/RESEARCH/WINDOW1/a.csv`\n```",   # 囲みの中のバッククォート
    "```\npython run.py --in docs/RESEARCH/WINDOW1/a.csv\n```",     # 囲みの中の裸のパス
    "読んだ docs/RESEARCH/WINDOW1/a.csv",                            # 裸のパス
    "`docs//RESEARCH/WINDOW1/a.csv`",                                # //
    "`docs/RESEARCH/./WINDOW1/a.csv`",                               # ./
    "`docs/ANALYSIS/../RESEARCH/WINDOW1/a.csv`",                     # ../
    "`docs/research/window1/a.csv`",                                 # 小文字
    "`Backtest_Data/Phase2_Sealed/SEALED.json`",                     # 大文字小文字の混ざり
    "`backtest_data\\phase2_sealed\\x`",                             # 逆スラッシュ
    "`/home/user/trade/docs/RESEARCH/WINDOW1/`",                     # 絶対パス
    "**docs/RESEARCH/WINDOW1/a.csv**",                               # 太字の中
])
def test_sealed_word_in_section_stops_before_stat(env, fake_root, stat_spy, capsys, d10):
    tmp, led = env
    rc, files = brief(tmp, led, make_doc(dict(FILLED, D10=d10)), "D10", repo=fake_root)
    assert rc == 1 and files == []
    assert "封印の置き場" in capsys.readouterr().err
    assert not [p for p in stat_spy if re.search(r"(?i)window1|phase2_sealed", p)]


@pytest.mark.parametrize("kid", ["K-011", "K-012", "K-013"])
def test_sealed_word_in_ledger_row_stops(env, fake_root, stat_spy, capsys, kid):
    """台帳の行のバッククォート・裸のパス・囲みの中、のどれでも止まる。"""
    tmp, led = env
    rc, files = brief(tmp, led, make_doc(dict(FILLED, D9b=f"観察 → {kid}")), "D9b", repo=fake_root)
    assert rc == 1 and files == []
    assert "封印の置き場" in capsys.readouterr().err
    assert not [p for p in stat_spy if re.search(r"(?i)window1|phase2_sealed", p)]


def test_sealed_word_in_skill_quote_stops(env, capsys):
    """④ に写すスキルの写しの中にあっても止まる。"""
    tmp, led = env
    text = make_doc(FILLED, quote=("写しの中の docs/RESEARCH/WINDOW1/q.md",))
    rc, files = brief(tmp, led, text, "D10")
    assert rc == 1 and files == []


def _git_env():
    env = dict(os.environ, GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="commit.gpgsign", GIT_CONFIG_VALUE_0="false",
               GIT_CONFIG_KEY_1="core.hooksPath", GIT_CONFIG_VALUE_1="/dev/null",
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    return env


def test_sealed_word_in_git_log_subject_stops(env, capsys):
    """⑥ の git log の件名に封印の置き場があっても止まる。件名に無ければ git log の行が入る。"""
    tmp, led = env
    g = tmp / "gitrepo"
    g.mkdir()
    e = _git_env()
    subprocess.run(["git", "init", "-q"], cwd=g, check=True, env=e)
    doc = g / "2026-10-05_x.md"
    doc.write_text(make_doc(FILLED), encoding="utf-8")
    subprocess.run(["git", "add", doc.name], cwd=g, check=True, env=e)
    subprocess.run(["git", "commit", "-q", "-m", "clean subject"], cwd=g, check=True, env=e)
    old = dict(os.environ)
    os.environ.update(e)
    try:
        rc, files = brief(tmp, led, None, "D10", doc_dir=g)
        assert rc == 0, capsys.readouterr().err
        assert "clean subject" in part(files[0].read_text(encoding="utf-8"), "⑥ 手順の履歴")
        doc.write_text(make_doc(FILLED) + "\n", encoding="utf-8")
        subprocess.run(["git", "commit", "-q", "-am", "read Docs/Research/Window1/a.csv"], cwd=g, check=True, env=e)
        rc, files2 = brief(tmp, led, None, "D10", doc_dir=g)
    finally:
        os.environ.clear()
        os.environ.update(old)
    assert rc == 1 and files2 == files
    assert "封印の置き場" in capsys.readouterr().err


def test_sealed_words_function():
    assert pb.sealed_words("a docs/x/../RESEARCH/WINDOW1/b c") == ["docs/x/../RESEARCH/WINDOW1/b"]
    assert pb.sealed_words("WINDOW1 だけ・RESEARCH/WINDOW の語") == []
    assert pb.sealed_words("`docs/RESEARCH/partner/x.md`") == []


# ---- 止めるもの

@pytest.mark.parametrize("done", ["", "  ", "\n"])
def test_empty_done_stops(env, capsys, done):
    tmp, led = env
    rc, files = brief(tmp, led, make_doc(FILLED), "D10", done=done)
    assert rc == 1 and files == []
    assert "--done" in capsys.readouterr().err


@pytest.mark.parametrize("at,empty", [("P", "P"), ("D9b", "D9b"), ("D10", "D10"), ("push", "D9b"), ("push", "D10")])
def test_unfilled_section_stops(env, capsys, at, empty):
    tmp, led = env
    filled = dict(FILLED)
    filled[empty] = None
    rc, files = brief(tmp, led, make_doc(filled), at)
    assert rc == 1 and files == []
    assert f"当てたこと({empty})" in capsys.readouterr().err


def test_unfilled_other_section_does_not_stop(env, capsys):
    """時点に要らない節(D0)が未記入でも止めない。⑥ の一覧に未記入と出る。"""
    tmp, led = env
    rc, files = brief(tmp, led, make_doc(dict(FILLED, D0=None)), "D10")
    assert rc == 0, capsys.readouterr().err
    hist = part(files[0].read_text(encoding="utf-8"), "⑥ 手順の履歴")
    assert "| D0 | (未記入) |" in hist and "| D10 | 埋まっている |" in hist
    assert "git の記録が無い" in hist


def test_no_skeleton_or_missing_step_stops(env, capsys):
    tmp, led = env
    rc, files = brief(tmp, led, "# 診断\n\n### 当てたこと(D10)\n\n書いた\n", "D10")
    assert rc == 1 and files == [] and "骨組みの節" in capsys.readouterr().err
    rc, files = brief(tmp, led, make_doc(FILLED, steps=("P", "D0")), "D10")
    assert rc == 1 and files == [] and "節 D10 が無い" in capsys.readouterr().err


def test_numbering_increments_and_never_overwrites(env, capsys):
    tmp, led = env
    text = make_doc(FILLED)
    assert brief(tmp, led, text, "D10")[0] == 0
    rc, files = brief(tmp, led, text, "push")
    assert rc == 0
    assert [f.name for f in files] == ["01_D10_brief.md", "02_push_brief.md"]
    (files[0]).unlink()  # 01 を消すと数は 1。02 は既にあるので 03 に飛ばす
    rc, files = brief(tmp, led, text, "P")
    assert rc == 0 and [f.name for f in files] == ["02_push_brief.md", "03_P_brief.md"]


def test_stdout_path_lines_sha(env, capsys):
    tmp, led = env
    capsys.readouterr()
    rc, files = brief(tmp, led, make_doc(FILLED), "D10")
    out = capsys.readouterr().out.splitlines()
    data = files[0].read_bytes()
    assert out[0].endswith("01_D10_brief.md")
    nl = data.count(b"\n")
    assert out[1] == f"行数 {nl}"
    assert out[2] == f"sha256 {hashlib.sha256(data).hexdigest()[:12]}"


def test_purpose_and_owner_view_and_not_given(env, capsys):
    tmp, led = env
    rc, files = brief(tmp, led, make_doc(FILLED), "D10", done="カードごとに台帳にある")
    out = files[0].read_text(encoding="utf-8")
    purpose = part(out, "③ 目的")
    para = pb.goal_paragraph(str(GOAL))
    assert para and all(ln in purpose for ln in para)
    assert "いまの位置" in purpose and "カードごとに台帳にある" in purpose
    view = part(out, "④ オーナーの観点")
    for p in pb.OWNER_VIEW:
        assert f"`{p}`(有る)" in view
    given = part(out, "⑦ 渡さないもの・読まないもの")
    assert "docs/RESEARCH/WINDOW1/" in given and "backtest_data/phase2_sealed/" in given and "過去の検証結果" in given
    assert "夜" not in given  # L-707 で外した
    heads = re.findall(r"^## (\S)", out, re.M)
    assert heads == ["①", "②", "③", "④", "⑤", "⑥", "⑦"]
    assert "git log で代える" in re.search(r"^## ⑥.*$", out, re.M).group(0)  # [7] 案 §6.2 ⑤ の置き換えを見出しに


def test_purpose_not_found_is_written(env, capsys):
    tmp, led = env
    g = tmp / "goal.md"
    g.write_text("# 目標\n\n何も無い\n", encoding="utf-8")
    s = tmp / "status.md"
    s.write_text("# 状態\n", encoding="utf-8")
    rc, files = brief(tmp, led, make_doc(FILLED), "D10", goal=g, status=s)
    assert rc == 0
    purpose = part(files[0].read_text(encoding="utf-8"), "③ 目的")
    assert purpose.count("見つからない") == 2


def test_goal_paragraph_after_heading(tmp_path):
    g = tmp_path / "g.md"
    g.write_text("# 目標\n\n## 最終目標\n\n**一行目**\n二行目\n\n## 次\n本文\n", encoding="utf-8")
    assert pb.goal_paragraph(str(g)) == ["**一行目**", "二行目"]
    g.write_text("# 目標\n\n前置き\nこの段落に最終目標がある\n後ろ\n\n別\n", encoding="utf-8")
    assert pb.goal_paragraph(str(g)) == ["前置き", "この段落に最終目標がある", "後ろ"]


# ---------------------------------------------------------------- check_partner

R_HEAD = "| # | 時点 | 相方 | 渡し書き | 記録 | 応答 |"
R_SEP = "|---|---|---|---|---|---|"
NAME = "2026-10-06_x.md"   # 手順 R の後の文書
OLD = "2026-10-05_x.md"    # 手順 R の前の文書(遡りの行を許す)
RETRO_ROW = "| 1 | (遡り) | advisor の道具 | 無し | 無し(遡り。会話にだけある) | — |"


def r_doc(d10: str | None, r: str | None) -> str:
    """節 R を持つ文書。R の写しの中にも見本の表を置く(写しの中は数えないことを見るため)。"""
    L = make_doc(dict(FILLED, D10=d10), steps=("P", "D9b", "D10")).split("\n")
    block = ds.step_block("R", "## R 相方の検め", ["見本:", R_HEAD, R_SEP, "| 1 | D10 | advisor | x | `none.md` | x |"])
    if r is not None:
        i = block.index(ds.EMPTY)
        block = block[:i] + r.split("\n") + block[i + 1:]
    return "\n".join(L + block)


def table(*rows: str) -> str:
    return "\n".join(["表:", "", R_HEAD, R_SEP, *rows])


@pytest.fixture()
def prepo(tmp_path):
    """記録の置き場を持つ一時の根。"""
    d = tmp_path / "docs" / "RESEARCH" / "partner" / "x"
    d.mkdir(parents=True)
    (d / "01_D10_reply.md").write_text("x", encoding="utf-8")
    (d / "01_D10_brief.md").write_text("x", encoding="utf-8")
    (d / "sub_reply.md").mkdir()
    (tmp_path / "README.md").write_text("x", encoding="utf-8")
    return tmp_path


OK_REC = "`docs/RESEARCH/partner/x/01_D10_reply.md`"


def ok_row(rec: str = OK_REC, n: int = 1) -> str:
    return f"| {n} | D10 | advisor | `b.md` | {rec} | 直した |"


def test_check_partner_d10_unfilled_passes_with_r_unfilled():
    assert cpt.check_text(r_doc(None, None), name=NAME) == (True, [])


def test_check_partner_d10_filled_r_unfilled_stops():
    has, errs = cpt.check_text(r_doc("知見の文", None), name=NAME)
    assert has and any("当てたこと(R)" in e for e in errs)


def test_check_partner_zero_rows_stops():
    """表の見出しだけ・1 列目が数字でない行だけ・写しの中の見本の表だけ、はどれも行 0。"""
    for r in ("書いたが表が無い", table(), table("| 番号 | D10 | advisor | x | 無し(遡り) | x |"),
              "> " + R_HEAD + "\n> " + R_SEP + "\n> | 1 | D10 | a | x | 無し(遡り) | x |"):
        has, errs = cpt.check_text(r_doc("知見の文", r), name=OLD)
        assert has and any("表の行が無い" in e for e in errs), r


def test_check_partner_step_block_excluded_even_without_gt():
    """写しの区切り(<!-- step:R --> 〜 <!-- /step:R -->)の中は、「>」の無い行でも表と数えない。"""
    text = r_doc("知見の文", "書いたが表が無い").replace(
        "<!-- /step:R -->", "\n".join([R_HEAD, R_SEP, RETRO_ROW, "<!-- /step:R -->"]))
    has, errs = cpt.check_text(text, name=OLD)
    assert has and any("表の行が無い" in e for e in errs)


@pytest.mark.parametrize("wrap", [
    lambda t: "```\n" + t + "\n```",
    lambda t: "~~~\n" + t + "\n~~~",
    lambda t: "\n".join("    " + ln for ln in t.split("\n")),
    lambda t: "\n".join("\t" + ln for ln in t.split("\n")),
    lambda t: "<!--\n" + t + "\n-->",
    lambda t: "```\n~~~\n" + t + "\n~~~\n```",
], ids=["backtick", "tilde", "indent4", "tab", "comment", "nested"])
def test_check_partner_table_in_fence_indent_or_comment_not_counted(wrap):
    """[4] ``` と ~~~ の囲み・4 字下げ・<!-- --> の中の表は R の記録として数えない。"""
    r = "表は下:\n\n" + wrap("\n".join([R_HEAD, R_SEP, RETRO_ROW]))
    has, errs = cpt.check_text(r_doc("知見の文", r), name=OLD)
    assert has and any("表の行が無い" in e for e in errs)


def test_check_partner_table_after_closed_fence_counts():
    """囲みを閉じた後の表は数える(囲みの閉じを見ているか)。"""
    r = "```\nコマンド\n```\n\n" + table(RETRO_ROW)
    assert cpt.check_text(r_doc("知見の文", r), name=OLD) == (True, [])
    r = "~~~\n```\n~~~\n\n" + table(RETRO_ROW)   # ~~~ の囲みの中の ``` で閉じない・~~~ で閉じる
    assert cpt.check_text(r_doc("知見の文", r), name=OLD) == (True, [])


@pytest.mark.parametrize("rec", ["", "会話の中だけ", "`--refresh`", "無し", "遡り 無し(遡り)", "無し（遡り）"])
def test_check_partner_record_neither_path_nor_retro_stops(rec):
    """記録の列が、バッククォートのパスでも「無し(遡り」で始まる文でもない行は止める(リードの判断 2026-10-06)。"""
    has, errs = cpt.check_text(r_doc("知見の文", table(ok_row(rec))), name=NAME)
    assert has and errs and all("記録の列がバッククォートのパスでも" in e for e in errs), errs


def test_check_partner_record_ok(prepo):
    assert cpt.check_text(r_doc("知見の文", table(ok_row())), repo=str(prepo), name=NAME) == (True, [])


@pytest.mark.parametrize("rec,why", [
    ("`docs/RESEARCH/partner/x/gone_reply.md`", "無い"),
    ("`docs/RESEARCH/partner/x/sub_reply.md`", "通常のファイルでない"),        # ディレクトリ
    ("`docs/`", "通常のファイルでない"),
    ("`./`", "通常のファイルでない"),
    ("`/etc/hosts`", "リポジトリの外"),
    ("`../../../etc/hosts`", "リポジトリの外"),
    ("`docs/RESEARCH/partner/../../../../outside_reply.md`", "リポジトリの外"),
    ("`README.md`", "docs/RESEARCH/partner/ の下でない"),
    ("`docs/RESEARCH/partner/x/01_D10_brief.md`", "_reply.md で終わらない"),
    (OK_REC + " と `README.md`", "docs/RESEARCH/partner/ の下でない"),
])
def test_check_partner_record_path_rules_stop(prepo, rec, why):
    """[止める 2] 記録のパスは、根の中・通常のファイル・docs/RESEARCH/partner/ の下・_reply.md、の全部で通る。"""
    has, errs = cpt.check_text(r_doc("知見の文", table(ok_row(rec))), repo=str(prepo), name=NAME)
    assert has and len(errs) == 1 and why in errs[0], errs


def test_check_partner_record_symlink_out_of_root_stops(prepo, tmp_path_factory):
    out = tmp_path_factory.mktemp("outside") / "z_reply.md"
    out.write_text("x", encoding="utf-8")
    link = prepo / "docs" / "RESEARCH" / "partner" / "x" / "link_reply.md"
    link.symlink_to(out)
    rec = "`docs/RESEARCH/partner/x/link_reply.md`"
    has, errs = cpt.check_text(r_doc("知見の文", table(ok_row(rec))), repo=str(prepo), name=NAME)
    assert len(errs) == 1 and "リポジトリの外" in errs[0]


def test_check_partner_retro_row_passes_only_old_doc_and_retro_at():
    """[5] 遡りの行は、時点の列が「(遡り)」で、文書の名前の日付が 2026-10-05 以前のときだけ通す。"""
    assert cpt.check_text(r_doc("知見の文", table(RETRO_ROW)), name=OLD) == (True, [])
    assert cpt.check_text(r_doc("知見の文", table(RETRO_ROW)), name="docs/ANALYSIS/2026-10-04_y.md") == (True, [])
    for name in (NAME, "x.md", None, "2026-13-01_x.md"):
        has, errs = cpt.check_text(r_doc("知見の文", table(RETRO_ROW)), name=name)
        assert len(errs) == 1 and "2026-10-05 以前" in errs[0], (name, errs)
    row = RETRO_ROW.replace("| (遡り) |", "| D10 |")
    has, errs = cpt.check_text(r_doc("知見の文", table(row)), name=OLD)
    assert len(errs) == 1 and "時点の列" in errs[0]


def test_check_partner_skips_doc_without_r():
    assert cpt.check_text(make_doc(FILLED), name=NAME) == (False, [])


def test_check_partner_r_heading_without_marker_stops():
    """[3] 「## R 」の見出しがあって <!-- step:R --> の印が無ければ問題。"""
    text = r_doc("知見の文", table(RETRO_ROW)).replace("<!-- step:R -->\n", "")
    has, errs = cpt.check_text(text, name=OLD)
    assert has and len(errs) == 1 and "印が無い" in errs[0]


@pytest.mark.parametrize("bad", ["### 当てたこと(D10) ", "### 当てたこと（D10）", "### 当てたこと D10"])
def test_check_partner_r_without_d10_heading_stops(bad):
    """[3] R 節があって「### 当てたこと(D10)」の見出しが無ければ問題(R の検めも行う)。"""
    text = r_doc("知見の文", "表なし").replace("### 当てたこと(D10)", bad)
    has, errs = cpt.check_text(text, name=OLD)
    assert has and any("当てたこと(D10)」の見出しが無い" in e for e in errs)
    assert any("表の行が無い" in e for e in errs)


def fill(text: str, step: str, content: str) -> str:
    """「### 当てたこと(step)」の下の最初の「(未記入)」を content に替える。"""
    i = text.index(f"### 当てたこと({step})")
    j = text.index(ds.EMPTY, i)
    return text[:j] + content + text[j + len(ds.EMPTY):]


def test_check_partner_real_skeleton_r_quote_example_not_counted(prepo):
    """本物のスキルの R の写し(`diag_skeleton.new_doc`)の中にある例の表(字下げ)を、R の記録として数えない。"""
    text = ds.new_doc("x", "2026-10-06")
    assert "<!-- step:R -->" in text
    quote = text[text.index("<!-- step:R -->"):text.index("<!-- /step:R -->")]
    assert R_HEAD in quote and "| 1 | D9b |" in quote  # 写しに例の表がある(無ければこの試験は意味を持たない)
    assert cpt.check_text(text, name=NAME) == (True, [])  # D10 未記入なら通る
    d10 = fill(text, "D10", "知見の文")
    has, errs = cpt.check_text(d10, repo=str(prepo), name=NAME)
    assert has and any("当てたこと(R)" in e for e in errs) and any("表の行が無い" in e for e in errs)
    has, errs = cpt.check_text(fill(d10, "R", "呼んだ記録は無い"), repo=str(prepo), name=NAME)
    assert errs and all("表の行が無い" in e for e in errs)
    ok = fill(d10, "R", table(ok_row()))
    assert cpt.check_text(ok, repo=str(prepo), name=NAME) == (True, [])


def test_check_partner_main_counts_and_exit(tmp_path, capsys, monkeypatch):
    d = tmp_path / "ANALYSIS"
    (d / "sub").mkdir(parents=True)
    (d / "2026-10-06_a.md").write_text(make_doc(FILLED), encoding="utf-8")
    (d / "sub" / "2026-10-06_b.md").write_text(r_doc("知見の文", None), encoding="utf-8")
    (d / "2026-10-05_c.md").write_text(r_doc("知見の文", table(RETRO_ROW)), encoding="utf-8")
    (d / "README.md").write_text(r_doc("知見の文", None), encoding="utf-8")
    monkeypatch.setattr(cpt, "DEFAULT_GLOB", str(d / "**" / "*.md"))
    assert cpt.main([]) == 1
    out = capsys.readouterr().out
    assert out.splitlines()[-1] == "ファイル 3・R 節あり 2・問題 2"
    assert "2026-10-06_b.md" in out and "README" not in out and "2026-10-05_c.md" not in out
    assert cpt.main([str(d / "2026-10-05_c.md")]) == 0  # 名前の日付で遡りの行が通る
    assert capsys.readouterr().out.splitlines()[-1] == "ファイル 1・R 節あり 1・問題 0"
    assert cpt.main([str(d / "none.md")]) == 2


def test_check_partner_default_glob_is_analysis_recursive():
    assert cpt.DEFAULT_GLOB.endswith(os.path.join("docs", "ANALYSIS", "**", "*.md"))


def test_check_partner_real_analysis_docs_pass():
    """本物の 9 枚(2026-10-05_card*.md、時点「(遡り)」の行)が通る(読むだけ)。"""
    docs = sorted((ROOT / "docs" / "ANALYSIS").glob("2026-10-05_card*.md"))
    assert docs
    for p in docs:
        has, errs = cpt.check_text(p.read_text(encoding="utf-8"), repo=str(ROOT), name=str(p))
        assert has and errs == [], (p.name, errs)
