"""探索の窓 1 の読み方の決まり(`scripts/w4_measure/window1_read.py` の W1〜W10 と台本の決め a〜h)を、走らせる前に固める。"""
from __future__ import annotations

import importlib.util
import random
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "w4_measure"))
_spec = importlib.util.spec_from_file_location("window1_read", REPO / "scripts" / "w4_measure" / "window1_read.py")
wr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wr)


def _ns(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()) * 10**9


# ---------------------------------------------------------------- W9

def test_label_positive_d0():
    d0 = 12.0
    assert wr.label(-5.0, 0.0, d0) == "逆向き"          # 上端 = 0 も逆向き
    assert wr.label(-5.0, -1.0, d0) == "逆向き"
    assert wr.label(1.0, 20.0, d0) == "引き継がれた側"
    assert wr.label(1.0, 11.0, d0) == "引き継がれた側(元の大きさより小さい)"
    assert wr.label(0.0, 11.0, d0) == "元の大きさは否定"  # 下端 = 0 は「下端 ≤ 0」
    assert wr.label(-3.0, 12.0, d0) == "不明"            # 上端 = d0 は「上端 ≥ d0」
    assert wr.label(-3.0, 30.0, d0) == "不明"


def test_label_negative_d0_mirrors():
    d0 = -10.87
    assert wr.label(0.0, 5.0, d0) == "逆向き"            # 下端 ≥ 0
    assert wr.label(-20.0, -1.0, d0) == "引き継がれた側"
    assert wr.label(-9.0, -1.0, d0) == "引き継がれた側(元の大きさより小さい)"
    assert wr.label(-9.0, 2.0, d0) == "元の大きさは否定"
    assert wr.label(-10.87, 2.0, d0) == "不明"
    assert wr.label(-2.56, 1.0, -2.56) == "不明"


def test_label_zero_d0():
    assert wr.label(0.1, 1.0, 0.0) == "正"
    assert wr.label(-1.0, -0.1, 0.0) == "負"
    assert wr.label(-1.0, 1.0, 0.0) == "不明"


def test_label_exactly_one_rule_fires():
    """W9 の 4 つ(d0 > 0)は重ならず、どれかに必ず当たる。決まりを独立に書き直して突き合わせる。"""
    rng = random.Random(1)
    for _ in range(5000):
        d0 = rng.choice([12.0, 1.13, 164.13, -10.87, -2.56, -1.0])
        lo = rng.uniform(-30, 30)
        hi = lo + rng.uniform(0, 30)
        s = 1 if d0 > 0 else -1
        L, H = (lo, hi) if s > 0 else (-hi, -lo)
        D = abs(d0)
        hits = [H <= 0, L > 0, L <= 0 < H < D, L <= 0 and H >= D]
        assert sum(hits) == 1
        want = ["逆向き", "引き継がれた側", "元の大きさは否定", "不明"][hits.index(True)]
        assert wr.label(lo, hi, d0).startswith(want)


def test_d0_table_matches_prereg():
    """D0 の値が PREREG.md §3 の表と同じ(走らせる前に固定した値を台本が書き換えていない)。"""
    text = (REPO / "docs" / "RESEARCH" / "WINDOW1" / "PREREG.md").read_text(encoding="utf-8")
    rows = dict(re.findall(r"^\s*\| (K-[^|]+?|M-A − M-0\(良い側 / 悪い側\)) \| ([^|]+?) \|", text, re.M))
    for k in ("K-A − K-0", "K-B − K-0", "K-B − K-A", "K-A+D − K-A", "K-B+D − K-B"):
        assert float(rows[k].replace("−", "-")) == wr.D0[k]
    g, b = rows["M-A − M-0(良い側 / 悪い側)"].split(" / ")
    assert float(g) == wr.D0["M-A − M-0 良"] and float(b) == wr.D0["M-A − M-0 悪"]


# ---------------------------------------------------------------- 決め b・c・d

def test_day_is_exit_minus_one_ns():
    assert wr.utc_day(_ns("2025-12-12T00:00:00Z")) == date(2025, 12, 11)
    assert wr.utc_day(_ns("2025-12-11T23:59:00Z")) == date(2025, 12, 11)
    assert wr.utc_day(_ns("2024-01-01T00:00:01Z")) == date(2024, 1, 1)


def test_daily_zero_fill_and_range():
    tr = [(0, _ns("2023-12-18T10:00:00Z"), 4.0), (0, _ns("2023-12-20T00:00:00Z"), -1.0),  # 12-20 0 時ちょうど → 12-19
          (0, _ns("2023-12-17T23:00:00Z"), 99.0), (0, _ns("2023-12-21T05:00:00Z"), 99.0)]
    assert wr.daily(tr, date(2023, 12, 18), date(2023, 12, 20)) == [4.0, -1.0, 0.0]


def test_gate_drop_by_entry_jst_day():
    # 2023-12-18T16:00Z = 日本時間 12-19 の 1 時 → 区分は 12-19 の区分
    tr = [(_ns("2023-12-18T16:00:00Z"), _ns("2023-12-18T17:00:00Z"), 1.0),
          (_ns("2023-12-18T10:00:00Z"), _ns("2023-12-18T11:00:00Z"), 2.0),   # 日本時間 12-18
          (_ns("2025-12-11T20:00:00Z"), _ns("2025-12-11T21:00:00Z"), 3.0)]   # 日本時間 12-12 = 区分なし → 外さない
    cls = {"2023-12-19": "low", "2023-12-18": "mid"}
    keep, n = wr.gate_drop(tr, cls, ("low",))
    assert n == 1 and [p for _, _, p in keep] == [2.0, 3.0]
    keep, n = wr.gate_drop(tr, cls, ("low", "mid"))
    assert n == 2 and [p for _, _, p in keep] == [3.0]


def test_series_adds_gate_forms_from_the_same_trades():
    tr = {k: [] for k in wr.K_RUNS + wr.M_RUNS}
    tr["K-A"] = [(_ns("2024-01-02T01:00:00Z"), _ns("2024-01-02T02:00:00Z"), 5.0)]
    tr["K-B"] = None
    out, dropped = wr.series(tr, {"2024-01-02": "low"})
    assert out["K-A+D"] == [] and dropped["K-A+D"] == (1, 1)
    assert out["K-B+D"] is None and "K-B+D" not in dropped


# ---------------------------------------------------------------- W1・W5・W7

def _fake(m: float, n_days: int = 725, seed: int = 0) -> list:
    rng = random.Random(seed)
    lo = datetime(2023, 12, 18, 12, tzinfo=timezone.utc).timestamp()
    return [(int(lo + 86400 * i) * 10**9, int(lo + 86400 * i + 600) * 10**9, m + rng.gauss(0, 1)) for i in range(n_days)]


def test_build_shapes_and_labels():
    tr = {"K-0": _fake(0, seed=1), "K-A": _fake(3, seed=2), "K-B": _fake(1, seed=3),
          "M-0_good": _fake(0, seed=4), "M-0_bad": _fake(0, seed=5), "M-A_good": _fake(50, seed=6), "M-A_bad": None}
    r = wr.build(tr, {}, None)
    assert r["missing"] == ["M-A_bad"]
    w = r["W1"]["K-A − K-0"]
    assert w["days"] == 725 and 2 < w["mean"] < 4 and w["lo"] < w["mean"] < w["hi"] and w["mde"] > 0
    assert w["label"] == wr.label(w["lo"], w["hi"], 12.0)
    assert r["W1"]["M-A − M-0 悪"] is None
    assert r["W1"]["K-A+D − K-A"]["mean"] == 0.0  # 区分なし = 何も外さない
    assert r["W5"]["FX"]["K-A − K-0"]["days"] == (date(2024, 3, 27) - date(2023, 12, 18)).days + 1
    assert r["W5"]["CFD"]["K-A − K-0"]["days"] == (date(2025, 12, 11) - date(2024, 3, 28)).days + 1
    assert "label" not in r["W5"]["FX"]["K-A − K-0"]  # 決め g
    assert r["W7"]["years"][2023]["K-A − K-0"]["days"] == 14
    assert r["W7"]["years"][2024]["K-A − K-0"]["days"] == 366
    assert r["W4"]["K-A"]["trades"] == 725 and abs(r["W4"]["K-A"]["trades_per_day"] - 1.0) < 1e-12
    md = wr.render(r)
    assert "足りない走らせ: M-A_bad" in md and "W10" in md


def test_edges_reproduce_classify():
    import vol_split_daily as vs
    rng = random.Random(7)
    vol, d = {}, date(2016, 1, 1)
    while d <= date(2019, 12, 31):
        vol[d.isoformat()] = rng.uniform(1, 10) * (1 + (d.year - 2016))
        d = date.fromordinal(d.toordinal() + 1)
    cls = vs.classify(vol)
    e = wr.edges(vol)
    for day, c in cls.items():
        q1, q2 = e[int(day[:4])]
        v = vol[vs.prev_day(day)]
        assert c == ("low" if v < q1 else ("mid" if v < q2 else "high"))
    rows = wr.vol_table(vol, cls, "2019-12-31")
    assert [x["year"] for x in rows] == [2017, 2018, 2019] and sum(rows[0]["days"].values()) == 365


def test_check_d0_rounded_terms_for_kb_minus_ka():
    """K-B − K-A は丸めた 2 項の差で突き合わせる(事前登録の表の出所の書き方)。"""
    lo = date(2020, 1, 1)
    t = lambda m: [(0, _ns(f"2020-01-0{i}T01:00:00Z"), m) for i in (1, 2)]  # noqa: E731
    tr = {"K-0": t(0.0), "K-A": t(12.004), "K-B": t(1.134), "M-0_good": t(0), "M-0_bad": t(0),
          "M-A_good": t(164.13), "M-A_bad": t(205.76)}
    periods = {k: (lo, date(2020, 1, 2)) for k in tr}
    r = wr.check_d0(tr, {}, periods)["diffs"]
    assert r["K-B − K-A"]["d0_from_rounded_terms"] == round(1.13 - 12.00, 10) or abs(
        r["K-B − K-A"]["d0_from_rounded_terms"] - (-10.87)) < 1e-9
    assert r["K-B − K-A"]["match"] and r["K-A − K-0"]["match"]
