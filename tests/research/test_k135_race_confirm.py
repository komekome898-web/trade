"""scripts/why_predict/k135_race_confirm.py の試験。

(a) 作り物の足で、手で数えられる小さな例の反転・継続・決まらないが合う。
(b) 再現: カード 7 の測定の足(bitFlyer FX_BTC_JPY、2015-11-28T15:00Z〜2023-12-17T15:00Z)に台本を当てると RACE_REPLAY.md・
    RACE_BLOCK_CI.md の数と一致する。
    - 軽い版: 保存済みの measure/<窓>/run.npz の決定の足(数秒)。
    - 重い版: 封印の門から 1 分足を読み直す(約 6 分)。環境変数 K135_HEAVY=1 のときだけ走る。
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "why_predict"))
import k135_race_confirm as m  # noqa: E402

C7 = os.path.join(ROOT, "docs", "RESEARCH", "cards", "c7_barrier_race")
MIN = 60 * m.NS
H = 3600 * m.NS


# ---------------------------------------------------------------- (a) 作り物の足

def _series(closes, highs=None, lows=None, t0=0):
    c = np.array(closes, dtype=float)
    t = t0 + MIN * np.arange(1, len(c) + 1, dtype=np.int64)
    return {"end_ns": t, "close": c, "high": c if highs is None else np.array(highs, float),
            "low": c if lows is None else np.array(lows, float)}


def test_hand_counted_close_races():
    # 窓 1h、1 分足 61 本の温まり(値動き a)の後に、手で決めた動き。w は窓の √Σr² で、温まりは r = ±a の交互。
    a = 0.001
    x = [0.0]
    for i in range(60):
        x.append(x[-1] + (a if i % 2 == 0 else -a))
    # 61 本目(k = 60)の終わり = 最初の足の終わり + 1h → レースを始める。w0 = √(60 a²) = a√60
    w0 = a * np.sqrt(60)
    # 上へ w0 で当たり(最初の当たり)→ 次の w は窓の r² で決まる。ここでは大きく動かして側を決める
    seq = [x[-1] + w0 * 1.01]                     # 上の当たり(最初)
    seq.append(seq[-1] + 0.05)                     # 上の当たり(継続)
    seq.append(seq[-1] - 0.2)                      # 下の当たり(反転)
    seq.append(seq[-1] - 0.5)                      # 下の当たり(継続)
    closes = np.exp(np.array(x + seq))
    s = _series(closes)
    hits = m.replay(s["end_ns"], np.log(s["close"]), H)
    sides = [h[1] for h in hits]
    assert sides == [1, 1, -1, -1]
    assert m.classify(hits) == ["first", "continuation", "reversal", "continuation"]
    assert hits[0][2] == pytest.approx(w0)


def test_warm_up_and_window_edge():
    # 温まりの足(終わり = 最初の終わり + 窓)より前では当たりは出ない
    closes = np.exp(np.r_[np.zeros(30), 1.0, np.zeros(40)])  # 31 本目に大きな跳ね(温まりの中)
    s = _series(closes)
    hits = m.replay(s["end_ns"], np.log(s["close"]), H)
    # k = 60 で始め: 窓 (t60 − 1h, t60] は t1..t60 の r(跳ねの上り r31 と下り r32 を含む)→ w = √2、その後は動かないので当たり無し
    assert hits == []


def test_highlow_undecided_both_and_prev():
    a = 0.001
    x = [0.0]
    for i in range(60):
        x.append(x[-1] + (a if i % 2 == 0 else -a))
    w0 = a * np.sqrt(60)
    base = x[-1]
    cl = list(x)
    hi = list(x)
    lo = list(x)
    # k = 61: 高値だけ上の線を越える(終値は動かない)→ 上の当たり(最初)。高値・安値の判定だけが当てる
    cl.append(base); hi.append(base + w0 * 1.01); lo.append(base)
    # k = 62: 高値も安値も両方の線を越える(終値は起点)→ 決まらない(同じ足で両方)
    cl.append(base); hi.append(base + 1.0); lo.append(base - 1.0)
    # k = 63: 下の線を安値で越える → 前の側が分からない
    cl.append(base); hi.append(base); lo.append(base - 2.0)
    # k = 64: 安値で下 → 前は下 → 継続
    cl.append(base); hi.append(base); lo.append(base - 3.0)
    # k = 65: 高値で上 → 反転
    cl.append(base); hi.append(base + 3.0); lo.append(base)
    s = _series(np.exp(cl), np.exp(hi), np.exp(lo))
    t, xc = s["end_ns"], np.log(s["close"])
    hl = m.replay(t, xc, H, np.log(s["high"]), np.log(s["low"]))
    assert [h[1] for h in hl] == [1, 0, -1, -1, 1]
    assert m.classify(hl) == ["first", "undecided_both", "undecided_prev", "continuation", "reversal"]
    # 終値の判定では終値が動かないので当たりは無い
    assert m.replay(t, xc, H) == []
    tb = m.tables(t, hl, m.day_list(t))
    allrow = [r for r in tb["rows"] if r["band"] == "全部" and r["part"] == "全期間"][0]
    assert (allrow["n"], allrow["rev"], allrow["und_both"], allrow["und_prev"]) == (2, 1, 1, 1)


def test_highlow_anchor_is_the_close_of_the_hit_bar():
    # 当たった足(k = 61)の高値だけが上の線を越え、終値は起点のまま。次の起点は終値(base)であって高値ではない。
    # 起点が終値なら k = 62(全部 base)は当たらず、k = 63 の高値で上に当たる。
    # 起点を ln(高値) にすると(批評家の壊し方 M4)、k = 62 の安値 base が 高値 − w1 以下になって下に当たる。
    a = 0.001
    x = [0.0]
    for i in range(60):
        x.append(x[-1] + (a if i % 2 == 0 else -a))
    w0 = a * np.sqrt(60)
    base = x[-1]
    cl, hi, lo = list(x), list(x), list(x)
    cl.append(base); hi.append(base + w0 * 1.01); lo.append(base)   # k = 61: 高値で上(最初)
    cl.append(base); hi.append(base); lo.append(base)               # k = 62: 動かない
    cl.append(base); hi.append(base + 1.0); lo.append(base)         # k = 63: 高値で上
    s = _series(np.exp(cl), np.exp(hi), np.exp(lo))
    hl = m.replay(s["end_ns"], np.log(s["close"]), H, np.log(s["high"]), np.log(s["low"]))
    w1 = a * np.sqrt(59)
    assert w0 * 1.01 > w1  # 起点が高値なら k = 62 で下に当たる大きさ(試験の前提)
    assert [(h[0], h[1]) for h in hl] == [(61, 1), (63, 1)]
    assert [h[4] for h in hl] == [60, 61]  # レースの始まり = 起点を置いた足
    assert m.classify(hl) == ["first", "continuation"]


def test_weekend_definition():
    # 1970-01-04 は日曜、1970-01-05 は月曜(UTC)
    d = 86400 * m.NS
    sun = 3 * d
    assert not m.is_weekend_start(sun + (20 * 3600 - 60) * m.NS)   # 日曜 19:59
    assert m.is_weekend_start(sun + 20 * 3600 * m.NS)               # 日曜 20:00
    assert m.is_weekend_start(sun + d + (22 * 3600 - 60) * m.NS)    # 月曜 21:59
    assert not m.is_weekend_start(sun + d + 22 * 3600 * m.NS)       # 月曜 22:00
    assert not m.is_weekend_start(sun - d + 21 * 3600 * m.NS)       # 土曜 21:00


def test_bands_are_terciles_of_counted_w():
    rng = np.random.default_rng(1)
    x = np.cumsum(rng.normal(0, 0.002, 20000))
    s = _series(np.exp(x))
    hits = m.replay(s["end_ns"], x, H)
    tb = m.tables(s["end_ns"], hits, m.day_list(s["end_ns"]))
    ws = np.array([h[2] for h, k in zip(hits, m.classify(hits)) if k != "first"])
    q1, q2 = np.quantile(ws, [1 / 3, 2 / 3])
    assert tb["q1"] == q1 and tb["q2"] == q2
    n = {r["band"]: r["n"] for r in tb["rows"] if r["part"] == "全期間"}
    assert n["下"] + n["中"] + n["上"] == n["全部"] == len(ws)


# ---------------------------------------------------------------- (b) 再現(RACE_REPLAY.md・RACE_BLOCK_CI.md の数)

# 窓: (当たり, 反転, 継続, 最初の当たりの日, 帯の境 bp, {(帯, 期間): (数, 割合, 区間)})。RACE_REPLAY.md から写した
EXPECT = {
    "1h": (31606, 16259, 15346, "2015-11-29", ("45.8", "80.8"), {
        ("全部", "全期間"): (31605, "0.514", "[0.509, 0.520]"), ("全部", "前半"): (13943, "0.507", "[0.499, 0.516]"),
        ("全部", "後半"): (17662, "0.520", "[0.513, 0.527]"),
        ("下", "全期間"): (10535, "0.516", "[0.507, 0.526]"), ("下", "前半"): (4702, "0.507", "[0.493, 0.522]"),
        ("下", "後半"): (5833, "0.523", "[0.510, 0.536]"),
        ("中", "全期間"): (10535, "0.512", "[0.503, 0.522]"), ("中", "前半"): (3853, "0.508", "[0.493, 0.524]"),
        ("中", "後半"): (6682, "0.515", "[0.503, 0.527]"),
        ("上", "全期間"): (10535, "0.515", "[0.505, 0.524]"), ("上", "前半"): (5388, "0.506", "[0.493, 0.520]"),
        ("上", "後半"): (5147, "0.523", "[0.510, 0.537]")}),
    "1d": (1727, 783, 943, "2016-05-30", ("264.1", "399.9"), {
        ("全部", "全期間"): (1726, "0.454", "[0.430, 0.477]"), ("全部", "前半"): (779, "0.425", "[0.391, 0.460]"),
        ("全部", "後半"): (947, "0.477", "[0.446, 0.509]"),
        ("下", "全期間"): (575, "0.405", "[0.366, 0.446]"), ("下", "前半"): (216, "0.338", "[0.278, 0.403]"),
        ("下", "後半"): (359, "0.446", "[0.395, 0.497]"),
        ("中", "全期間"): (575, "0.438", "[0.398, 0.479]"), ("中", "前半"): (211, "0.355", "[0.294, 0.422]"),
        ("中", "後半"): (364, "0.486", "[0.435, 0.537]"),
        ("上", "全期間"): (576, "0.517", "[0.477, 0.558]"), ("上", "前半"): (352, "0.520", "[0.468, 0.572]"),
        ("上", "後半"): (224, "0.513", "[0.448, 0.578]")}),
    "1w": (342, 145, 196, "2016-06-12", ("758.3", "1111.3"), {
        ("全部", "全期間"): (341, "0.425", "[0.374, 0.478]"), ("全部", "前半"): (162, "0.395", "[0.323, 0.472]"),
        ("全部", "後半"): (179, "0.453", "[0.381, 0.526]"),
        ("下", "全期間"): (114, "0.298", "[0.222, 0.388]"), ("下", "前半"): (40, "0.150", "[0.071, 0.291]"),
        ("下", "後半"): (74, "0.378", "[0.276, 0.492]"),
        ("中", "全期間"): (113, "0.496", "[0.405, 0.586]"), ("中", "前半"): (49, "0.469", "[0.337, 0.606]"),
        ("中", "後半"): (64, "0.516", "[0.396, 0.634]"),
        ("上", "全期間"): (114, "0.482", "[0.393, 0.573]"), ("上", "前半"): (73, "0.479", "[0.369, 0.592]"),
        ("上", "後半"): (41, "0.488", "[0.343, 0.635]")}),
}
# RACE_BLOCK_CI.md の「両方」の行(日の塊の区間)
EXPECT_BLOCK = {
    "1h": {"全期間": "[0.509, 0.519]", "前半": "[0.499, 0.516]", "後半": "[0.512, 0.527]"},
    "1d": {"全期間": "[0.432, 0.476]", "前半": "[0.392, 0.459]", "後半": "[0.446, 0.507]"},
    "1w": {"全期間": "[0.370, 0.480]", "前半": "[0.320, 0.473]", "後半": "[0.378, 0.531]"},
}


def _check(v, tb):
    nh, nrev, ncont, fday, (e1, e2), rows = EXPECT[v]
    assert (tb["hits"], tb["n_rev"], tb["n_cont"], tb["first_day"]) == (nh, nrev, ncont, fday)
    assert (f"{tb['q1'] * 1e4:.1f}", f"{tb['q2'] * 1e4:.1f}") == (e1, e2)
    assert tb["edge"] == "2019-12-08" and tb["days"] == 2941
    got = {(r["band"], r["part"]): r for r in tb["rows"]}
    for key, (n, rate, iv) in rows.items():
        r = got[key]
        assert (r["n"], f"{r['rate']:.3f}", f"[{r['wilson'][0]:.3f}, {r['wilson'][1]:.3f}]") == (n, rate, iv), key
    for part, iv in EXPECT_BLOCK[v].items():
        r = got[("全部", part)]
        assert f"[{r['block'][0]:.3f}, {r['block'][1]:.3f}]" == iv, (v, part)


def _npz_series(v):
    z = np.load(os.path.join(C7, "measure", v, "run.npz"))
    d = np.flatnonzero(z["decided"])
    return {"end_ns": z["end_ns"][d].astype(np.int64), "close": z["close"][d], "high": z["high"][d], "low": z["low"][d]}


@pytest.mark.parametrize("v", ["1h", "1d", "1w"])
def test_reproduces_race_replay_on_saved_bars(v):
    s = _npz_series(v)
    days = sorted(line.split(",")[0] for line in open(os.path.join(C7, "measure", v, "daily.csv")).read().splitlines()[1:])
    assert m.day_list(s["end_ns"]) == days
    _hits, tb = m.run(s, v, "close")
    _check(v, tb)


@pytest.mark.skipif(os.environ.get("K135_HEAVY") != "1", reason="重い: 封印の門から bitFlyer の 1 分足を読み直す(K135_HEAVY=1 で走る)")
def test_reproduces_race_replay_from_the_gate():
    s = m.load_series("bitflyer_fx", log=lambda *_: None)
    ref = _npz_series("1d")
    assert np.array_equal(s["end_ns"], ref["end_ns"]) and np.array_equal(s["close"], ref["close"])
    for v in ("1h", "1d", "1w"):
        _hits, tb = m.run(s, v, "close")
        _check(v, tb)
