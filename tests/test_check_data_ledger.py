"""`scripts/check_data_ledger.py` の性質テスト(L-190、2026-09-17)。

ネットワークにも実物の `docs/DATA.md` にも触らない。tmp_path に小さな台帳と
`backtest_data/` を作り、**(i)(ii)(iii) と案 A のそれぞれで「拾う側」と
「拾わない側」の両方**を固定する。
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_data_ledger as cdl  # noqa: E402

HEADER = ("| 資産 | 所在 | 範囲 | 状態 | 最終確認日 | プローブのログ | 使った単位 |\n"
          "|---|---|---|---|---|---|---|\n")

TODAY = date(2026, 9, 17)


def _row(asset: str, where: str, last_checked: str) -> str:
    return f"| {asset} | {where} | — | 取得済 | {last_checked} | — | 未使用 |\n"


def _write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """拾う側と拾わない側を 1 件ずつ持つ最小の台帳と実物。"""
    bt = tmp_path / "backtest_data"

    # (i) 拾わない側: 台帳の「所在」列に行がある単位
    _write(bt / "unit_listed" / "a.csv", "a")
    # (i) 拾う側: 実物はあるが台帳のどの「所在」にも出てこない単位
    _write(bt / "unit_unlisted" / "b.csv", "b")

    # (ii) 拾わない側 = unit_listed のパス、拾う側 = 存在しないパスの行
    # (iii) 受領台帳: unit_listed/a.csv だけ載せる(unit_unlisted/b.csv は載せない)
    _write(tmp_path / "paper_logs" / "INTAKE_latest.json",
           json.dumps({"backtest_data/unit_listed/a.csv": {"md5": "0" * 32}}))

    body = [
        "# データ登録簿\n\n## 1. 表\n\n", HEADER,
        # 新しい行(案 A で拾わない側)+ (i)(ii)(iii) の拾わない側
        _row("実在する単位", "`backtest_data/unit_listed/`", "2026-09-16"),
        # 古い行(案 A で拾う側)+ (ii) の拾う側
        _row("実在しないパス", "`backtest_data/no_such_unit/`", "2026-08-01"),
    ]
    _write(tmp_path / "docs" / "DATA.md", "".join(body))
    return tmp_path


def _run(root: Path, max_age_days: int = 14) -> dict:
    return cdl.run(root, max_age_days=max_age_days, today=TODAY)


# --- (i) 台帳に行が無い単位 ------------------------------------------------

def test_i_flags_a_unit_with_no_row_in_the_ledger(tree: Path):
    rep = _run(tree)
    units = {u["unit"] for u in rep["units_without_ledger_row"]}
    assert "unit_unlisted" in units


def test_i_does_not_flag_a_unit_that_is_listed(tree: Path):
    rep = _run(tree)
    units = {u["unit"] for u in rep["units_without_ledger_row"]}
    assert "unit_listed" not in units


def test_i_accepts_a_glob_written_in_the_location_column(tmp_path: Path):
    """`backtest_data/auto_okx_*_2026*/` のような glob 表記でも「行がある」と読む。"""
    _write(tmp_path / "backtest_data" / "auto_okx_20260905" / "a.csv")
    _write(tmp_path / "docs" / "DATA.md",
           "## 1\n\n" + HEADER + _row("glob 表記", "`backtest_data/auto_okx_*/`", "2026-09-16"))
    rep = _run(tmp_path)
    assert rep["units_without_ledger_row"] == []


# --- (ii) 所在のパスが実在しない -------------------------------------------

def test_ii_flags_a_location_path_that_does_not_exist(tree: Path):
    rep = _run(tree)
    hits = {(r["line"], r["path"]) for r in rep["missing_paths"]}
    assert (8, "backtest_data/no_such_unit/") in hits


def test_ii_does_not_flag_an_existing_path_or_a_url(tmp_path: Path):
    _write(tmp_path / "backtest_data" / "unit_listed" / "a.csv")
    _write(tmp_path / "docs" / "DATA.md",
           "## 1\n\n" + HEADER
           + _row("実在", "`backtest_data/unit_listed/`", "2026-09-16")
           + _row("URL は対象外", "`https://example.com/no/such/path`", "2026-09-16")
           + _row("PC のパスは対象外", r"オーナー PC `data\ws\FX_BTC_JPY_*.jsonl.gz`", "2026-09-16"))
    rep = _run(tmp_path)
    assert rep["missing_paths"] == []


# --- (iii) 受領台帳に無いファイル ------------------------------------------

def test_iii_counts_files_missing_from_the_intake_ledger(tree: Path):
    rep = _run(tree)
    per_unit = {r["unit"]: r for r in rep["files_not_in_intake"]}
    assert per_unit["unit_unlisted"]["not_in_ledger"] == 1
    assert per_unit["unit_unlisted"]["file_count"] == 1
    assert "unit_listed" not in per_unit          # 台帳に載っている方は出さない


def test_iii_reports_which_intake_ledger_was_used(tree: Path):
    """`paper_logs/` 側しか無ければそれを使い、どちらを使ったか書く。"""
    rep = _run(tree)
    assert rep["intake_ledger"]["path"] == "paper_logs/INTAKE_latest.json"
    assert "paper_logs" in rep["intake_ledger"]["selection"]


def test_iii_prefers_the_newer_of_the_two_intake_ledgers(tree: Path):
    """両方あれば新しい方。`data/` 側を後から書いたらそちらを使う。"""
    import os
    import time
    shared = tree / "paper_logs" / "INTAKE_latest.json"
    local = tree / "data" / "INTAKE_latest.json"
    _write(local, json.dumps({"backtest_data/unit_unlisted/b.csv": {"md5": "1" * 32}}))
    newer = os.stat(shared).st_mtime + 10
    os.utime(local, (newer, newer))
    time.sleep(0.01)

    rep = _run(tree)
    assert rep["intake_ledger"]["path"] == "data/INTAKE_latest.json"
    assert "data/" in rep["intake_ledger"]["selection"]
    # data/ 側の台帳では unit_unlisted が載っていて unit_listed が載っていない
    per_unit = {r["unit"]: r for r in rep["files_not_in_intake"]}
    assert "unit_unlisted" not in per_unit
    assert per_unit["unit_listed"]["not_in_ledger"] == 1


# --- 案 A 鮮度 --------------------------------------------------------------

def test_freshness_flags_a_row_older_than_the_threshold(tree: Path):
    rep = _run(tree, max_age_days=14)
    stale = {r["line"]: r for r in rep["stale_rows"]}
    assert 8 in stale
    assert stale[8]["last_checked"] == "2026-08-01"
    assert stale[8]["age_days"] == 47


def test_freshness_does_not_flag_a_fresh_row(tree: Path):
    rep = _run(tree, max_age_days=14)
    assert 7 not in {r["line"] for r in rep["stale_rows"]}


def test_freshness_threshold_is_respected(tree: Path):
    assert _run(tree, max_age_days=60)["stale_rows"] == []
    assert _run(tree, max_age_days=1)["stale_rows"][0]["line"] == 8   # 1 日前は「古くない」
    assert len(_run(tree, max_age_days=0)["stale_rows"]) == 2


# --- パーサの寛容さ ---------------------------------------------------------

def test_tables_with_a_different_header_are_skipped_and_reported(tmp_path: Path):
    _write(tmp_path / "docs" / "DATA.md",
           "## 1\n\n" + HEADER + _row("標準形", "`data/`", "2026-09-16")
           + "\n## 2\n\n"
           + "| 資産 | 所在 | 状態 | 最終確認日 | 使った単位 |\n"
           + "|---|---|---|---|---|\n"
           + "| 別の形 | `data/` | 取得済 | 2020-01-01 | 未使用 |\n")
    rep = _run(tmp_path)
    skipped = rep["skipped_tables"]
    assert len(skipped) == 1
    assert skipped[0]["header_line"] == 9
    # 飛ばした表の古い行は鮮度検査に出てこない
    assert rep["stale_rows"] == []


def test_rows_with_a_wrong_cell_count_are_skipped_and_reported(tmp_path: Path):
    _write(tmp_path / "docs" / "DATA.md",
           "## 1\n\n" + HEADER
           + _row("普通の行", "`data/`", "2026-09-16")
           + "| 欠けた行 | `data/` | — |\n")
    rep = _run(tmp_path)
    assert [r["line"] for r in rep["malformed_rows"]] == [6]


def test_a_pipe_inside_backticks_does_not_split_the_row(tmp_path: Path):
    """`docs/DATA.md:96` の `` `ls ... | wc -l` `` で行ごと落とさない。"""
    _write(tmp_path / "backtest_data" / "unit_listed" / "a.csv")
    _write(tmp_path / "docs" / "DATA.md",
           "## 1\n\n" + HEADER
           + "| パイプ入り | `backtest_data/unit_listed/` | — | 取得済(`ls x | wc -l` = 11) "
             "| 2026-09-16 | — | 未使用 |\n")
    rep = _run(tmp_path)
    assert rep["malformed_rows"] == []
    assert rep["units_without_ledger_row"] == []


def test_undated_rows_are_listed_separately(tmp_path: Path):
    _write(tmp_path / "docs" / "DATA.md",
           "## 1\n\n" + HEADER + _row("日付なし", "`data/`", "—"))
    rep = _run(tmp_path)
    assert [r["line"] for r in rep["undated_rows"]] == [5]
    assert rep["stale_rows"] == []


# --- 終了コードと書き込み ---------------------------------------------------

def test_exit_code_is_zero_even_with_findings(tree: Path, capsys):
    rc = cdl.main(["--root", str(tree), "--today", "2026-09-17"])
    assert rc == 0
    assert "食い違い: あり" in capsys.readouterr().out


def test_strict_returns_one_when_there_are_findings(tree: Path):
    assert cdl.main(["--root", str(tree), "--today", "2026-09-17", "--strict"]) == 1


def test_strict_returns_zero_when_clean(tmp_path: Path):
    _write(tmp_path / "backtest_data" / "unit_listed" / "a.csv")
    _write(tmp_path / "paper_logs" / "INTAKE_latest.json",
           json.dumps({"backtest_data/unit_listed/a.csv": {"md5": "0" * 32}}))
    _write(tmp_path / "docs" / "DATA.md",
           "## 1\n\n" + HEADER + _row("実在", "`backtest_data/unit_listed/`", "2026-09-16"))
    assert cdl.main(["--root", str(tmp_path), "--today", "2026-09-17", "--strict"]) == 0


def test_json_output_is_written_and_nothing_else_is_touched(tree: Path):
    before = {p: p.read_bytes() for p in sorted(tree.rglob("*")) if p.is_file()}
    out = tree / "data" / "LEDGER_CHECK.json"
    cdl.main(["--root", str(tree), "--today", "2026-09-17", "--json", str(out)])
    assert out.exists()
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["summary"]["unit_count"] == 2
    for p, content in before.items():
        assert p.read_bytes() == content, f"書き換えた: {p}"
