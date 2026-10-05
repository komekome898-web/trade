"""分析の仕組みの道具(`scripts/analysis/` の ledger_rows・count_tables・local_effects・check_placeholders・
commit_gate.sh)の試験。L-705・L-706、案 `docs/DISCUSSIONS/2026-10-05_analysis_mechanism/PROPOSAL.md` §4 案 A の 3。

台帳・文書はすべて一時ディレクトリに作る。実際の `docs/` は書き換えない。
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AN = ROOT / "scripts" / "analysis"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lr = _load("ledger_rows", AN / "ledger_rows.py")
ct = _load("count_tables", AN / "count_tables.py")
le = _load("local_effects", AN / "local_effects.py")
cp = _load("check_placeholders", AN / "check_placeholders.py")

# ---------------------------------------------------------------- ledger_rows

LEDGER = """# 知見台帳

## 書式

```
### K-001 見本(囲みの中は数えない)
- 観察: 見本
```

## 観察

### K-010 既にある行
- 観察: 短く持った取引で稼ぎ、長く持った取引で失っている
- 対象: 仕組み
- 出所: `docs/RESEARCH/FINDINGS_LEDGER.md` の表 1
- 測った日: 2026-10-03
- 射程: Binance の 5 分足、2017-08〜2023-12
- 大きさ: +3.2bp / 取引
- 確かさ: 未監査
- 監査: なし
- 否定を含む: いいえ
- 渡す先: カツオの降り方の改良
- 次の問い: 長く持ったときの降り方を変えて測る
- なぜの仮説: ① 短く持つと戻りだけを取る ② 偶然 ③ 測りの癖
- 予言: 未(W3 で書く)
- 確かめのデータ: 見つけたのと同じ(表 1)
- 状態: 開いている

## カード

### カード: カツオ
- 状態: 測定中
- 場面ごとの効き: K-010
- なぜ: 未
- 安定: 未
- 重なり: 未
- 経費と約定: 未
- bitFlyer で効くか: 未
- 改良の周: 0
- 次に打てる手: 長く持ったときの降り方を変える
"""

ROW = ("K-011", "土日に正・平日に負", "場面", "曜日ごとの 1 日あたりは土日が正",
       "`docs/RESEARCH/FINDINGS_LEDGER.md` の表 2", "土 +33.09 bp/日", "いいえ", "段 4 の場面の変数",
       "区間を付けても 0 より上か", "① 週末は参加者が少ない ② 偶然")

DEFS = '''SCOPE = "bitFlyer FX_BTC_JPY の 1 分足、2015-11-29〜2023-12-17"
PRED = "未(W3 で書く)"
DATA = "見つけたのと同じ(この分析の表)"
ROWS = {rows!r}
'''


@pytest.fixture()
def ledger(tmp_path):
    p = tmp_path / "LEDGER.md"
    p.write_text(LEDGER, encoding="utf-8")
    return p


def _defs(tmp_path, rows):
    p = tmp_path / "rows_x.py"
    p.write_text(DEFS.format(rows=rows), encoding="utf-8")
    return str(p)


def test_fixture_ledger_is_clean():
    assert lr.cfl.check_ledger_text(LEDGER, repo=ROOT) == []


def test_ledger_rows_adds_rows_before_cards(tmp_path, ledger, capsys):
    row2 = ("K-012",) + ROW[1:]
    rc = lr.main([_defs(tmp_path, [ROW, row2]), "--ledger", str(ledger), "--date", "2026-10-05"])
    assert rc == 0, capsys.readouterr().err
    text = ledger.read_text(encoding="utf-8")
    assert text.index("### K-010") < text.index("### K-011") < text.index("### K-012") < text.index("## カード")
    assert "- 測った日: 2026-10-05" in text
    assert "- 射程: bitFlyer FX_BTC_JPY の 1 分足、2015-11-29〜2023-12-17" in text
    assert "- 確かさ: 未監査" in text and "- 状態: 開いている" in text
    assert lr.cfl.check_ledger_text(text, repo=ROOT) == []
    assert "足した: K-011, K-012" in capsys.readouterr().out


def test_ledger_rows_default_date_is_today_jst(tmp_path, ledger):
    assert lr.main([_defs(tmp_path, [ROW]), "--ledger", str(ledger)]) == 0
    assert f"- 測った日: {lr.today_jst()}" in ledger.read_text(encoding="utf-8")


def test_ledger_rows_duplicate_k_stops_and_ledger_unchanged(tmp_path, ledger, capsys):
    before = ledger.read_bytes()
    dup = ("K-010",) + ROW[1:]
    assert lr.main([_defs(tmp_path, [ROW, dup]), "--ledger", str(ledger), "--date", "2026-10-05"]) == 1
    assert "K-010 は台帳に既にある" in capsys.readouterr().err
    assert ledger.read_bytes() == before
    assert lr.main([_defs(tmp_path, [ROW, ROW]), "--ledger", str(ledger), "--date", "2026-10-05"]) == 1
    assert "2 回ある" in capsys.readouterr().err
    assert ledger.read_bytes() == before


def test_ledger_rows_example_in_fence_is_not_a_duplicate(tmp_path, ledger):
    """`## 書式` の囲みの見本(K-001)は台帳の行ではない(検査と同じ読み方)。"""
    row = ("K-001",) + ROW[1:]
    assert lr.main([_defs(tmp_path, [row]), "--ledger", str(ledger), "--date", "2026-10-05"]) == 0


@pytest.mark.parametrize("i,val,word", [(8, "", "次の問い"), (8, "なし", "次の問い"), (6, "たぶん", "否定を含む"),
                                        (4, "どこか", "出所"), (4, "`docs/NO_SUCH.md`", "出所")])
def test_ledger_rows_checker_problem_stops_and_ledger_unchanged(tmp_path, ledger, capsys, i, val, word):
    before = ledger.read_bytes()
    bad = ROW[:i] + (val,) + ROW[i + 1:]
    assert lr.main([_defs(tmp_path, [bad]), "--ledger", str(ledger), "--date", "2026-10-05"]) == 1
    err = capsys.readouterr().err
    assert word in err and "検査の問題" in err
    assert ledger.read_bytes() == before


def test_ledger_rows_structure_problems_stop(tmp_path, ledger, capsys):
    before = ledger.read_bytes()
    for rows, msg in (([ROW[:9]], "長さ 10"), ([ROW[:3] + ("改行が\nある",) + ROW[4:]], "改行"),
                      ([("K-1",) + ROW[1:]], "K-数字"), ([], "空")):
        assert lr.main([_defs(tmp_path, rows), "--ledger", str(ledger), "--date", "2026-10-05"]) == 1
        assert msg in capsys.readouterr().err
    p = tmp_path / "no_scope.py"
    p.write_text(f"ROWS = {[ROW]!r}\nPRED = 'x'\nDATA = 'y'\n", encoding="utf-8")
    assert lr.main([str(p), "--ledger", str(ledger)]) == 1
    assert "SCOPE" in capsys.readouterr().err
    assert lr.main([_defs(tmp_path, [ROW]), "--ledger", str(ledger), "--date", "10/05"]) == 1
    assert ledger.read_bytes() == before


def test_ledger_rows_existing_problem_blocks_add(tmp_path, ledger, capsys):
    """足す前から台帳に問題があれば足さない(問題 0 の台帳にしか足さない)。"""
    ledger.write_text(LEDGER.replace("- 次の問い: 長く持ったときの降り方を変えて測る", "- 次の問い: なし"), encoding="utf-8")
    before = ledger.read_bytes()
    assert lr.main([_defs(tmp_path, [ROW]), "--ledger", str(ledger), "--date", "2026-10-05"]) == 1
    assert ledger.read_bytes() == before


def test_ledger_rows_restores_when_check_after_write_fails(tmp_path, ledger, monkeypatch, capsys):
    """書いた後の読み直しの検査で問題が出たら、元の中身に戻す。"""
    before = ledger.read_bytes()
    real = lr.cfl.check_ledger_text
    calls = []

    def fake(text, repo=lr.REPO):
        calls.append(1)
        return real(text, repo=repo) if len(calls) == 1 else ["1: 書いた後に見つかった問題"]

    monkeypatch.setattr(lr.cfl, "check_ledger_text", fake)
    assert lr.main([_defs(tmp_path, [ROW]), "--ledger", str(ledger), "--date", "2026-10-05"]) == 1
    assert "元の中身に戻した" in capsys.readouterr().err
    assert ledger.read_bytes() == before
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".ledger_rows.")]


# ---------------------------------------------------------------- count_tables

DOC_TABLES = """# 診断

| 前置きの表 | x |
|---|---|
| 1 | 2 |

## P 前提

> | 写しの表 | x |
> |---|---|
> | 1 | 2 |

### 当てたこと(P)

| a | b |
|---|---|
| 1 | 2 |
| 3 | 4 |

文。

| c |
|:--|
| 5 |

> | 引用の表 | x |
> |---|---|
> | 9 | 9 |

| 区切りの無い塊 |

## D0 次

### 当てたこと(D0)

```
| 囲みの表 |
|---|
| 1 |
```

| d | e |
|---|---|
| 1 | 2 |
> | 引用 | の行 |
| f | g |
|---|---|
"""


def test_count_tables_counts_tables_and_rows_per_section():
    res = ct.count(DOC_TABLES)
    assert res == {"P": (2, 3), "D0": (2, 1)}


def test_count_tables_ignores_quoted_lines():
    quoted_only = "### 当てたこと(D2)\n\n> | a | b |\n> |---|---|\n> | 1 | 2 |\n"
    assert ct.count(quoted_only) == {"D2": (0, 0)}


def test_count_tables_main_prints_total(tmp_path, capsys):
    p = tmp_path / "doc.md"
    p.write_text(DOC_TABLES, encoding="utf-8")
    assert ct.main([str(p)]) == 0
    out = capsys.readouterr().out
    assert "P: 表 2・行 3" in out and "計: 表 4・行 4" in out


# ---------------------------------------------------------------- local_effects

DOC_HALVES = """## D2 場面

### 当てたこと(D2)

| 区分 | 全期間 | 前半 [区間] | 後半 [区間] |
|---|---|---|---|
| 両方正 | +1.0 [+0.5, +1.5] | +1.2 [+0.1, +2.0] | +0.9 [+0.2, +1.7] |
| 両方負 | −2.0 [−3.0, −1.0] | −1,234.5 [−2,000.0, −100.0] | -3.0 [-4.0, -0.5] |
| 前半だけ | +1.0 [+0.5, +1.5] | +1.2 [+0.1, +2.0] | +0.9 [−0.2, +1.7] |
| 0 を含む | +1.0 [+0.5, +1.5] | +1.2 [−0.1, +2.0] | +0.9 [−0.2, +1.7] |
| 端が 0 | +1.0 [+0.5, +1.5] | +1.2 [0.0, +2.0] | +0.9 [+0.2, +1.7] |
| 逆の側 | +1.0 [+0.5, +1.5] | +1.2 [+0.1, +2.0] | −0.9 [−1.7, −0.2] |
| 百分率 | 1% [1%, 2%] | 12.0% [10.1%, 14.0%] | 11.0% [9.0%, 13.0%] |
| 列が壊れた |g| の行 | +1.2 [+0.1, +2.0] | +0.9 [+0.2, +1.7] | x |

| 窓 | 起点から [区間] | 対照 [区間] |
|---|---|---|
| 1w | +40.39 [+7.74, +90.12] | +2.18 [+0.31, +4.50] |

## D1 年

### 当てたこと(D1)

| 年 | 前半 | 後半 |
|---|---|---|
| D1 は見ない | +1.2 [+0.1, +2.0] | +0.9 [+0.2, +1.7] |
"""


def test_local_effects_picks_same_side_rows_only():
    n, hits = le.scan(DOC_HALVES)
    heads = [h[1].split(" / ")[0] for h in hits]
    assert heads == ["両方正", "両方負", "百分率"]
    assert all(h[0] == "D2" for h in hits)
    assert n == 7  # 列が壊れた行・別の表の行・D1 の行は数えない


def test_local_effects_main_prints(tmp_path, capsys):
    p = tmp_path / "doc.md"
    p.write_text(DOC_HALVES, encoding="utf-8")
    assert le.main([str(p)]) == 0
    out = capsys.readouterr().out
    assert "両半分で同じ側 3" in out and "前半 +1.2 [+0.1, +2.0]" in out


# ---------------------------------------------------------------- check_placeholders

def test_check_placeholders_finds_placeholder(tmp_path, capsys):
    p = tmp_path / "a.md"
    p.write_text("# x\n\n観察 3 → この番号は後で書き足す。\n(e) の指す先: ここに書き足す\nあとで埋める\nTODO: 数え直す\n",
                 encoding="utf-8")
    assert cp.main([str(p)]) == 1
    out = capsys.readouterr().out
    assert ":3: 番号は後で書き足す" in out and ":4: ここに書き足す" in out and ":5: あとで埋める" in out and ":6: TODO" in out
    assert "仮置き 4" in out


def test_check_placeholders_ignores_quoted_and_past(tmp_path, capsys):
    p = tmp_path / "b.md"
    p.write_text("\n".join([
        "カード 9 の D9b で「カード 7 の D9b を書くときに足して、ここの番号を書き足す」と書いた分",
        "入れ子「外「ここに書き足す」外」も引用",
        "カード 5・6 の D9b の後に書き足した",
        "> 崩れたと分かった後で「いつから」を書く。番号は後で書き足す",
        "D0 の ✕ を埋める / 崩れたと分かった後で記述する",
        "```", "番号は後で書き足す(見本)", "```",
    ]) + "\n", encoding="utf-8")
    assert cp.main([str(p)]) == 0
    assert "仮置き 0" in capsys.readouterr().out


def test_check_placeholders_unclosed_quote_runs_to_line_end():
    assert cp.find("「閉じない ここに書き足す\n次の行の後で書き足す\n") == [(2, "後で書き足す", "次の行の後で書き足す")]


def test_check_placeholders_missing_file_is_2(tmp_path):
    assert cp.main([str(tmp_path / "none.md")]) == 2


# ---------------------------------------------------------------- commit_gate.sh

def _gate_repo(tmp_path):
    """一時の git の置き場に、門と検査 2 本を写す(門は自分の置き場から根を解くので、実際の repo には触れない)。"""
    r = tmp_path / "repo"
    (r / "scripts" / "analysis").mkdir(parents=True)
    (r / "docs" / "RESEARCH").mkdir(parents=True)
    (r / "docs" / "ANALYSIS").mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "check_findings_ledger.py", r / "scripts")
    shutil.copy(AN / "check_placeholders.py", r / "scripts" / "analysis")
    shutil.copy(AN / "commit_gate.sh", r / "scripts" / "analysis")
    (r / "docs" / "RESEARCH" / "FINDINGS_LEDGER.md").write_text(LEDGER, encoding="utf-8")
    (r / "docs" / "ANALYSIS" / "2026-10-05_x.md").write_text("# x\n\n書いた。\n", encoding="utf-8")
    env = dict(os.environ, GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="commit.gpgsign", GIT_CONFIG_VALUE_0="false",
               GIT_CONFIG_KEY_1="core.hooksPath", GIT_CONFIG_VALUE_1="/dev/null",
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    subprocess.run(["git", "init", "-q"], cwd=r, check=True, env=env)
    return r, env


def _gate(r, env, msg="docs: test"):
    p = subprocess.run(["sh", str(r / "scripts" / "analysis" / "commit_gate.sh"), msg], cwd=r, env=env,
                       capture_output=True, text=True)
    log = subprocess.run(["git", "log", "--oneline"], cwd=r, env=env, capture_output=True, text=True).stdout
    return p.returncode, p.stdout + p.stderr, log


def test_commit_gate_stops_on_ledger_problem(tmp_path):
    r, env = _gate_repo(tmp_path)
    led = r / "docs" / "RESEARCH" / "FINDINGS_LEDGER.md"
    led.write_text(LEDGER.replace("- 次の問い: 長く持ったときの降り方を変えて測る", "- 次の問い: なし"), encoding="utf-8")
    rc, out, log = _gate(r, env)
    assert rc == 1 and "台帳の検査" in out and log == ""


def test_commit_gate_stops_on_placeholder(tmp_path):
    r, env = _gate_repo(tmp_path)
    (r / "docs" / "ANALYSIS" / "2026-10-05_x.md").write_text("# x\n\n番号は後で書き足す\n", encoding="utf-8")
    rc, out, log = _gate(r, env)
    assert rc == 1 and "仮置き" in out and log == ""


def test_commit_gate_commits_when_both_clean(tmp_path):
    r, env = _gate_repo(tmp_path)
    rc, out, log = _gate(r, env, "docs: clean")
    assert rc == 0, out
    assert "docs: clean" in log
    files = subprocess.run(["git", "show", "--name-only", "--format="], cwd=r, env=env,
                           capture_output=True, text=True).stdout.split()
    assert files and all(f.startswith("docs/") for f in files)


def test_commit_gate_needs_message(tmp_path):
    r, env = _gate_repo(tmp_path)
    rc, _, log = _gate(r, env, "")
    assert rc == 2 and log == ""
