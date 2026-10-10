"""データの導線の門 G1〜G4(scripts/data_gates.py、L-984・L-986)。止まる入力と通る入力の両方。"""
from __future__ import annotations

import gzip
import importlib.util
import subprocess
from datetime import date, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("data_gates", ROOT / "scripts" / "data_gates.py")
dg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dg)

BASE = Path("/repo")


def decide(tool, ti, *, pending=0, read=True, reg=True):
    return dg.pretool_decision(tool, ti, base=BASE, pending=pending, data_md_read=read, registry_ok=reg)


# ---- 置き場の名前

@pytest.mark.parametrize("path,fam", [
    ("backtest_data/auto_okx_open_interest_5m_20261009/okx_btc_oi_5m.csv", "auto_okx_open_interest_5m"),
    ("backtest_data/binance_BTCUSDT_1m_20170801_20231231/x.csv.gz", "binance_BTCUSDT_1m"),
    ("backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz", "candles_FX_BTC_JPY_31d"),
    ("backtest_data/o3c_price_level_full_20260917_b005/a.csv", "o3c_price_level_full_b005"),
    ("paper_logs/tape/executions_20261009.csv.gz", "paper_logs/tape"),
    ("paper_logs/basis_log.csv", "paper_logs/basis_log"),
    ("paper_logs/QUALITY.json", None),
    ("paper_logs/INTAKE.jsonl", None),
    ("backtest_data/phase2_sealed/x.csv", None),
    ("backtest_data/MD5SUMS", None),
])
def test_family_of(path, fam):
    assert dg.family_of(path) == fam


def test_families_newest_date():
    f = dg.families(["backtest_data/auto_x_20261001/a.csv", "backtest_data/auto_x_20261005/a.csv",
                     "paper_logs/tape/executions_20261009.csv.gz", "backtest_data/plain/a.csv"])
    assert f == {"auto_x": "2026-10-05", "paper_logs/tape": "2026-10-09", "plain": ""}


# ---- G2 登録簿

MD_OK = """# データ登録簿
## 2. 海外
| auto_x の行 | `backtest_data/auto_x_*` |
## 3. 共有
paper_logs/tape の行
## 10. 置き場の一覧(機械が検める)
| 置き場 | 最新の日付 | 説明の節 |
|---|---|---|
| auto_x | 2026-10-05 | §2 |
| paper_logs/tape | 2026-10-09 | §3 |
"""
FAMS = {"auto_x": "2026-10-05", "paper_logs/tape": "2026-10-09"}


def test_registry_ok():
    assert dg.registry_problems(FAMS, MD_OK) == []


def test_registry_no_index():
    assert any("§10" in p for p in dg.registry_problems(FAMS, "# 無い\n"))


def test_registry_missing_row():
    probs = dg.registry_problems({**FAMS, "new_stream": "2026-10-10"}, MD_OK)
    assert probs == ["new_stream: §10 の表に行が無い(実物の最新 2026-10-10)"]


def test_registry_stale_date():
    probs = dg.registry_problems({**FAMS, "auto_x": "2026-10-09"}, MD_OK)
    assert len(probs) == 1 and "古い" in probs[0]


def test_registry_name_not_in_section():
    md = MD_OK.replace("| auto_x | 2026-10-05 | §2 |", "| auto_x | 2026-10-05 | §3 |")
    probs = dg.registry_problems(FAMS, md)
    assert len(probs) == 1 and "説明の節" in probs[0]


# ---- PreToolUse の判定(G1・G3・G2)

def test_g1_blocks_read_data():
    assert "G1" in decide("Read", {"file_path": "/repo/backtest_data/x/a.csv"}, pending=6)


def test_g1_blocks_unknown_ref():
    assert "G1" in decide("Glob", {"pattern": "paper_logs/**"}, pending=None)


def test_g1_allows_git_and_intake_tools():
    assert decide("Bash", {"command": "git merge origin/x && git ls-tree HEAD backtest_data/"}, pending=6) is None
    assert decide("Bash", {"command": "python3 scripts/share_reconcile.py"}, pending=6) is None
    assert decide("Bash", {"command": "python3 scripts/fetch_bitflyer_executions_range.py --since 2026-09-10T00:00:00Z --out-dir backtest_data/b"}, pending=6) is None


def test_g1_blocks_compound_with_data_read():
    assert "G1" in decide("Bash", {"command": "git status && zcat paper_logs/tape/a.csv.gz | head"}, pending=6)


def test_g1_blocks_research_paths():
    assert "G1" in decide("Edit", {"file_path": "/repo/docs/ANALYSIS/x.md"}, pending=1)


def test_unrelated_paths_pass_even_when_pending():
    assert decide("Edit", {"file_path": "/repo/docs/OWNER_LOG.md"}, pending=6, read=False, reg=False) is None
    assert decide("Bash", {"command": "git log -3"}, pending=6, read=False, reg=False) is None


def test_g3_blocks_search_before_reading_registry():
    assert "G3" in decide("Glob", {"pattern": "*", "path": "/repo/backtest_data"}, read=False)
    assert "G3" in decide("Bash", {"command": "ls backtest_data | head"}, read=False)


def test_g3_passes_after_reading_and_for_git_writes():
    assert decide("Glob", {"pattern": "*", "path": "/repo/backtest_data"}, read=True) is None
    assert decide("Bash", {"command": "git add backtest_data/x && git commit -m 'paper_logs'"}, read=False) is None


def test_g2_blocks_research_when_registry_stale():
    assert "G2" in decide("Read", {"file_path": "/repo/scripts/analysis/diag_tables.py"}, reg=False)


def test_g2_allows_commit_gate():
    assert decide("Bash", {"command": "sh scripts/analysis/commit_gate.sh \"msg\""}, reg=False) is None


def test_data_dir_word_needs_slash():
    # 「data」という語だけ(コミットの文など)はデータの置き場とみなさない
    assert decide("Bash", {"command": "echo data quality"}, pending=6, read=False) is None
    assert "G1" in decide("Bash", {"command": "cat data/INTAKE_latest.json"}, pending=6)


# ---- G4 欠け

def test_coverage_gaps_finds_hole():
    t = [datetime(2026, 10, 1, 0, m) for m in (0, 5, 10, 25, 30)]
    gaps = dg.coverage_gaps(t, 5, datetime(2026, 10, 1, 0, 0), datetime(2026, 10, 1, 0, 30))
    assert gaps == [(datetime(2026, 10, 1, 0, 15), datetime(2026, 10, 1, 0, 20))]


def test_coverage_gaps_none_and_tail():
    t = [datetime(2026, 10, 1, 0, m) for m in (0, 5, 10)]
    assert dg.coverage_gaps(t, 5, datetime(2026, 10, 1, 0, 0), datetime(2026, 10, 1, 0, 10)) == []
    assert dg.coverage_gaps(t, 5, datetime(2026, 10, 1, 0, 0), datetime(2026, 10, 1, 0, 20)) == [
        (datetime(2026, 10, 1, 0, 15), datetime(2026, 10, 1, 0, 20))]


def test_bitflyer_day_complete():
    d = date(2026, 9, 19)
    assert dg.bitflyer_day_complete("2026-09-19T00:00:00.37", "2026-09-19T23:59:57.963", d)
    assert not dg.bitflyer_day_complete("2026-09-19T07:24:00", "2026-09-19T23:59:57", d)
    assert not dg.bitflyer_day_complete("2026-09-19T00:00:01", "2026-09-19T01:39:00", d)


def _write_day(p: Path, first: str, last: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wt") as fh:
        fh.write("ts,price,size,side,id\n")
        fh.write(f"{first},1,1,BUY,1\n{last},1,1,SELL,2\n")


def test_bitflyer_missing_and_ledger(tmp_path):
    today = date(2026, 10, 10)
    d = tmp_path / "backtest_data" / "bitflyer_executions_backfill_20261010"
    for k in range(1, 31):
        day = date.fromordinal(today.toordinal() - k)
        if day == date(2026, 9, 20):
            continue
        s = day.isoformat()
        _write_day(d / f"executions_{day:%Y%m%d}.csv.gz", f"{s}T00:00:01.0", f"{s}T23:59:58.0")
    miss = dg.bitflyer_missing(tmp_path, today, set())
    assert len(miss) == 1 and "2026-09-20" in miss[0]
    assert dg.bitflyer_missing(tmp_path, today, {("bitflyer_executions", "2026-09-20")}) == []


def test_parse_gap_ledger():
    md = "## 8. 損失\n### 8.1 欠けの処置(機械が検める)\n| 流れ | 日 | 処置 |\n|---|---|---|\n| bitflyer_executions | 2026-09-20 | 取れない: x |\n## 9. x\n"
    assert dg.parse_gap_ledger(md) == {("bitflyer_executions", "2026-09-20")}


# ---- G1 の参照(本物の git で)

def test_g1_pending_with_git(tmp_path):
    def run(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
    run("init", "-q", "-b", "work")
    run("-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "--allow-empty", "-m", "base")
    assert dg.g1_pending(tmp_path)[0] is None  # 参照が無い
    run("update-ref", f"refs/remotes/{dg.SHARE_REF}", "HEAD")
    assert dg.g1_pending(tmp_path)[0] == 0
    run("checkout", "-q", "-b", "share")
    run("-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "--allow-empty", "-m", "snapshot")
    run("update-ref", f"refs/remotes/{dg.SHARE_REF}", "HEAD")
    run("checkout", "-q", "work")
    assert dg.g1_pending(tmp_path)[0] == 1


def test_stream_lags_finds_stopped_recorder():
    paths = ["paper_logs/tape/executions_20261009.csv.gz", "paper_logs/venues/quotes_20261005.csv.gz",
             "paper_logs/venues/trades_gmo_btc_jpy_20261005.csv.gz", "paper_logs/tape/board_top10_20261008.csv.gz"]
    lags = dg.stream_lags(paths, set())
    assert len(lags) == 2 and all("venues" in x for x in lags)  # 1 日遅れ(board)は止めない
    assert dg.stream_lags(paths, {("venues/quotes", "停止"), ("venues/trades_gmo_btc_jpy", "停止")}) == []


def test_unseen_reads_are_blocked_while_gated():
    # 中で何を読むか文字に出ない操作(台本・ワイルドカード・再帰・置き換え・全体の検索)は、門が閉じている間は止める
    for cmd in ("python3 /tmp/x.py", "ls back*", "find . -name '*.csv'", "cat $(cat list)", "grep -r foo ."):
        assert "G3" in decide("Bash", {"command": cmd}, read=False), cmd
        if not cmd.startswith("ls "):  # 一覧は置き場の整理の操作として G1 でも通す(L-990)
            assert "G1" in decide("Bash", {"command": cmd}, pending=2), cmd
    assert "G3" in decide("Grep", {"pattern": "foo"}, read=False)
    assert "G3" in decide("Glob", {"pattern": "**/*.csv"}, read=False)
    # 門が開いていれば通る
    assert decide("Bash", {"command": "python3 /tmp/x.py"}) is None


def test_quoted_text_and_heredoc_bodies_are_not_commands():
    # 引用の中の | * ? や、ヒアドキュメントの本文は、コマンドとして読まない(文書を書く操作まで止めない。L-990)
    cmd = "printf '%s\\n' '| L-990 | **太字** | どう？ |' >> docs/OWNER_LOG.md"
    assert decide("Bash", {"command": cmd}, pending=6, read=False, reg=False) is None
    cmd = "cat >> docs/X.md <<'EOF'\n| a | **b** | backtest_data/x |\nEOF"
    assert decide("Bash", {"command": cmd}, pending=6, read=False, reg=False) is None
    # 本文を読む側が台本なら、その行で止める
    assert "G1" in decide("Bash", {"command": "python3 - <<'EOF'\nprint(1)\nEOF"}, pending=6)


def test_repair_path_is_never_blocked_by_g1_or_g2():
    for cmd in ("python3 scripts/data_repair/bitflyer_oldest_first.py 2026-09-10 2026-10-04",
                "python3 scripts/fetch_bitflyer_executions_range.py --since x",
                "git merge origin/x"):
        assert decide("Bash", {"command": cmd}, pending=6, read=True, reg=False) is None, cmd


def test_waits_only_excuse_owner_dependent_items():
    probs = {"G1 取り込み": ["x"], "G2 登録簿": ["y"], "G4 欠け": ["z"],
             "G5 記録の停止": ["paper_logs/venues/quotes: 最新 …", "paper_logs/tape/ticker: 最新 …"]}
    md = ("### 8.1 欠けの処置\n| 流れ | 日 | 処置 |\n|---|---|---|\n"
          "| 共有の合流 | 2026-10-11 | オーナー待ち: 照合の表の承認 |\n"
          "| venues/quotes | 2026-10-11 | オーナー待ち: PC の記録器の再起動 |\n")
    out = dg.apply_waits(probs, dg.parse_waits(md), date(2026, 10, 12))
    assert out["G1 取り込み"] == [] and out["G2 登録簿"] == ["y"] and out["G4 欠け"] == ["z"]
    assert out["G5 記録の停止"] == ["paper_logs/tape/ticker: 最新 …"]
    late = dg.apply_waits(probs, dg.parse_waits(md), date(2026, 10, 15))  # 3 日を過ぎたらまた止まる
    assert late["G1 取り込み"] == ["x"] and len(late["G5 記録の停止"]) == 2
