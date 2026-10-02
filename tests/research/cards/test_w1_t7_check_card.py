"""T7: the field check of a card's description actually stops.

A description with every field passes; the descriptions each missing one field
(the spec's nine and 測定の設定) are refused; a description whose period
overlaps the seal of its market is refused. For every check in `CHECKS`, the
broken version without it lets its description through (so the test that
expects the refusal would fail). Also the critic's fixes 3-5: paths compared
after resolving them, seals per market, the measurement settings with their
sources."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("check_card_w1", ROOT / "scripts" / "check_card.py")
cc = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cc
_spec.loader.exec_module(cc)

FX_DIR = "backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_TEST"
SEALED_FILE = f"{FX_DIR}/f_2023.csv.gz"
JPX_FILE = "backtest_data/jpx_etf_daily_TEST/1306.T.csv"

SETTINGS = ("- vr_q_bars: なし | 出所: 原文に窓の幅が無いので vr を使わない(試験)\n"
            "- day_zone: UTC | 出所: 試験\n"
            "- 参照: S | lag_ns: 0 | 場面: category | 出所: 試験の入力")
BODIES = {
    "原文": "「海外の値動きに bitFlyer が遅れて付いてくる」(L-000 のような原文を逐語で)",
    "意図の地図": "- 入る条件: … → 関数の 12 行\n- 出る条件: …",
    "なぜ": "1. 誰が損をしているか: …\n2. なぜ続くか: …\n3. 何で崩れるか: …",
    "期待する向きと場面": "海外が動いた直後、同じ向き",
    "反証": "海外の動きの後で bitFlyer が動かないなら違う",
    "関数のパス": "`src/bot/research/cards/example.py:Example`",
    "水準とその出所": "窓 1 分(原文にある)",
    "使うデータと遅れ": f"- `{FX_DIR}/f_2020.csv.gz` 遅れ 0(足の終わり)",
    "約定の模型": "成行。次の足の始値",
    "測定の設定": SETTINGS,
    "測る期間": "- 開始: 2020-01-01T00:00:00Z\n- 終了: 2023-12-18T00:00:00Z",
}


def card_text(drop=None, **override) -> str:
    parts = ["# カード example", ""]
    for name, body in BODIES.items():
        if name == drop:
            continue
        head = "原文(逐語)" if name == "原文" else name
        parts += [f"## {head}", override.get(name, body), ""]
    return "\n".join(parts)


def _ledger(root: Path, files) -> None:
    led = root / "backtest_data" / "phase2_sealed" / "PX"
    led.mkdir(parents=True, exist_ok=True)
    (led / "SEALED.json").write_text(json.dumps({
        "unit": "PX", "forward_start": "2026-09-06T00:00:00+00:00",
        "files": [{"path": p, "time_column": "ts", "seal_from_ts": f"{d}T00:00:00+00:00"} for p, d in files]}))


@pytest.fixture()
def root(tmp_path):
    _ledger(tmp_path, [(SEALED_FILE, "2023-12-18"), (JPX_FILE, "2015-08-29")])
    return str(tmp_path)


def data(path, end="2023-12-18T00:00:00Z"):
    return {"使うデータと遅れ": f"- `{path}` 遅れ 0", "測る期間": f"- 開始: 2020-01-01T00:00:00Z\n- 終了: {end}"}


# the description each check is responsible for refusing (one per check)
def cases():
    out = {f"field:{n}": card_text(drop=n) for n in cc.FIELDS}
    out["period"] = card_text(drop="測る期間")
    out["data_paths"] = card_text(**{"使うデータと遅れ": "系列 A の 1 分足、遅れ 0(パスが書かれていない)"})
    out["settings"] = card_text(**{"測定の設定": SETTINGS.replace(" | 出所: 試験の入力", "")})
    out["markets"] = card_text(**data("backtest_data/someone_elses_dir/f.csv"))
    out["seal"] = card_text(**data(f"{FX_DIR}/f_2020.csv.gz", "2023-12-18T00:01:00Z"))
    return out


def test_the_complete_description_passes(root):
    assert cc.problems(card_text(), root) == []


@pytest.mark.parametrize("name", cc.FIELDS)
def test_each_missing_field_is_refused(root, name):
    assert len(cc.FIELDS) == 10
    found = cc.problems(card_text(drop=name), root)
    assert found and any(f"「{name}」" in p for p in found)


@pytest.mark.parametrize("name", cc.FIELDS)
def test_an_empty_or_doubled_field_is_refused(root, name):
    assert cc.problems(card_text(**{name: "   "}), root)
    doubled = card_text() + f"\n## {name}\nもう 1 つ\n"
    assert cc.problems(doubled, root)


@pytest.mark.parametrize("settings", [
    SETTINGS.replace("- vr_q_bars: なし | 出所: 原文に窓の幅が無いので vr を使わない(試験)\n", ""),  # no vr_q_bars
    SETTINGS.replace("- day_zone: UTC | 出所: 試験", "- day_zone: UTC"),  # no source
    SETTINGS.replace("day_zone: UTC", "day_zone: JST"),
    SETTINGS.replace("vr_q_bars: なし", "vr_q_bars: 1"),
    SETTINGS.replace(" | lag_ns: 0", ""),  # a series without its availability
    SETTINGS.replace("lag_ns: 0", "lag_ns: 0 | available_at: per_row"),
    SETTINGS.replace("場面: category", "場面: other"),
    SETTINGS + "\n- seed: 1 | 出所: 試験",  # an unknown setting
    SETTINGS + "\n- day_zone: UTC | 出所: 試験",  # twice
])
def test_measurement_settings_without_a_source_or_unreadable_are_refused(root, settings):
    assert cc.problems(card_text(**{"測定の設定": settings}), root)


def test_per_row_and_a_number_for_vr_pass(root):
    s = SETTINGS.replace("vr_q_bars: なし", "vr_q_bars: 5").replace("lag_ns: 0", "available_at: per_row")
    assert cc.problems(card_text(**{"測定の設定": s}), root) == []


# -- fix 3: paths are compared after resolving them --------------------------------------------------------

@pytest.mark.parametrize("form", ["absolute", "dot", "dotdot"])
def test_other_spellings_of_a_sealed_path_are_refused(root, form):
    path = {"absolute": f"{root}/{FX_DIR}/f_2023.csv.gz", "dot": f"./{FX_DIR}/f_2023.csv.gz",
            "dotdot": f"backtest_data/x/../../{FX_DIR}/f_2023.csv.gz"}[form]
    found = cc.problems(card_text(**data(path, "2024-06-01T00:00:00Z")), root)
    assert any("封印の境" in p for p in found), found


def test_broken_version_comparing_the_text_lets_a_dotdot_path_through(root, monkeypatch):
    """`..` that leaves another market's directory: as text it matches binance_um (sealed only from 2026-08-23),
    resolved it is the bitFlyer series sealed from 2023-12-18."""
    trick = f"backtest_data/binance_um_BTCUSDT_x/../../{FX_DIR}/f_2024.csv.gz"
    text = card_text(**data(trick, "2024-06-01T00:00:00Z"))
    assert cc.problems(text, root)
    monkeypatch.setattr(cc, "normalize", lambda path, root: path)
    assert cc.problems(text, root) == []


def test_a_path_outside_the_root_is_refused(root):
    assert any("根の外" in p for p in cc.problems(card_text(**data("../elsewhere/f.csv")), root))


# -- fix 4: seals per market ---------------------------------------------------------------------------------

def test_a_refetched_directory_of_a_sealed_market_is_refused(root):
    path = "backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20261101/candles.csv.gz"  # not in the ledger
    assert cc.problems(card_text(**data(path, "2023-12-19T00:00:00Z")), root)
    assert cc.problems(card_text(**data(path, "2023-12-18T00:00:00Z")), root) == []


def test_a_crypto_card_is_not_refused_by_a_jpx_seal(root):
    assert cc.problems(card_text(**data("backtest_data/binance_um_BTCUSDT_new/f.csv", "2025-01-01T00:00:00Z")),
                       root) == []
    assert cc.problems(card_text(**data("backtest_data/jpx_etf_daily_new/1321.T.csv", "2016-01-01T00:00:00Z")),
                       root)


def test_a_ledger_file_no_market_matches_refuses(tmp_path):
    _ledger(tmp_path, [(SEALED_FILE, "2023-12-18"), ("backtest_data/unknown_dir/f.csv", "2020-01-01")])
    assert any("市場の表" in p for p in cc.problems(card_text(), str(tmp_path)))


def test_an_unreadable_ledger_refuses(root):
    Path(root, "backtest_data", "phase2_sealed", "PX", "SEALED.json").write_text("{not json")
    assert any("台帳が読めない" in p for p in cc.problems(card_text(), root))


def test_the_repository_ledger_maps_to_markets():
    """Every file of the real ledger maps to one market; bitFlyer FX_BTC_JPY is sealed from 2023-12-18 and a
    crypto card is not caught by the JPX seal (P2-04, 2015-08-29). Only the ledger is read, no sealed data."""
    bounds, problems = cc.boundaries(str(ROOT), cc.MARKETS)
    assert problems == []
    assert bounds["bitflyer:FX_BTC_JPY"] == 1_702_857_600 * 10**9  # 2023-12-18T00:00:00Z
    assert bounds["jpx:cash"] == bounds["jpx:n225_futures"] == 1_440_806_400 * 10**9  # 2015-08-29T00:00:00Z
    refetch = "backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20261101/candles_1m_2024.csv.gz"
    assert cc.problems(card_text(**data(refetch, "2023-12-19T00:00:00Z")), str(ROOT))
    assert cc.problems(card_text(**data(refetch, "2023-12-18T00:00:00Z")), str(ROOT)) == []
    um = "backtest_data/binance_um_BTCUSDT_1m_new/f.csv.gz"
    assert cc.problems(card_text(**data(um, "2025-01-01T00:00:00Z")), str(ROOT)) == []


@pytest.mark.parametrize("period", [
    "- 開始: 2020-01-01T00:00:00Z",                                      # no end
    "- 開始: 2020-01-01T00:00:00\n- 終了: 2021-01-01T00:00:00",         # no offset
    "- 開始: 2021-01-01T00:00:00Z\n- 終了: 2020-01-01T00:00:00Z",       # start after end
    "- 開始: 2020-13-01T00:00:00Z\n- 終了: 2021-01-01T00:00:00Z",       # not a date
])
def test_an_unreadable_period_is_refused(root, period):
    assert cc.problems(card_text(**{"測る期間": period}), root)


def test_every_check_has_its_case():
    assert sorted(c.__name__ for c in cc.CHECKS) == sorted(cases())


@pytest.mark.parametrize("name", sorted(cases()))
def test_broken_version_without_one_check_lets_its_case_through(root, name):
    """The real checker refuses the case; the checker with that one check taken out passes it, so the test
    above that expects the refusal fails on the broken version."""
    text = cases()[name]
    assert cc.problems(text, root) != []
    broken = tuple(c for c in cc.CHECKS if c.__name__ != name)
    assert len(broken) == len(cc.CHECKS) - 1
    assert cc.problems(text, root, broken) == []


def test_the_command_line(root, tmp_path):
    good = tmp_path / "good.md"
    good.write_text(card_text(), encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_text(card_text(drop="反証"), encoding="utf-8")
    script = str(ROOT / "scripts" / "check_card.py")
    r = subprocess.run([sys.executable, script, str(good), "--root", root], capture_output=True, text=True)
    assert r.returncode == 0 and "通る" in r.stdout
    r = subprocess.run([sys.executable, script, str(bad), "--root", root], capture_output=True, text=True)
    assert r.returncode == 1 and "「反証」" in r.stdout
