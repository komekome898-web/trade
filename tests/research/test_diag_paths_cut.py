"""読み口 `scripts/analysis/diag_paths.py` の足し(分析の持ち越しの 2・3)の試験。

リードが書いた。L-909「**24 時間前の対照(読み口にまだ口が無い)。**」「**門で外した合図の読みを前半・後半に分けることと、ほかの門の値での読み。**」。
L-932「**無駄な試験を消せ、話はそこから**」で、足す中身を決める 3 つだけに減らした(16 件 → 3 件)。

決まり:
- `d5(signals, bars, days)` の各 h の dict に鍵 "control_24h_before" を足す(値は `signal_move(ns − DAY, side, bars, h)`、
  日は合図の UTC の日。作りは "control_24h" と同じ)。
- `d5_halves(signals, bars, days, cut)` → {"first": 合図の日 < cut の d5, "second": 合図の日 ≥ cut の d5}(日もそれぞれの半分だけ)。
- `render`: D5 の表に列「対照(24 時間前の同じ時刻)[区間]」を足す。res に "d5_halves" と "cut" があれば、群ごとに
  `### <群> — 前半(日 < <cut>)`・`### <群> — 後半(日 ≥ <cut>)` の表を、本体と同じ列でこの順に書く。
- `main` に `--cut YYYY-MM-DD` を足し、渡したら D5 の全部の群に d5_halves を作る。
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "analysis"))
import diag_paths as dp  # noqa: E402
import diag_tables as dt  # noqa: E402

M, DAY = dp.MIN, dp.DAY
T0 = int(datetime(2019, 12, 1, tzinfo=timezone.utc).timestamp()) * 10**9
NDAYS, CUT_DAY = 32, 14  # 前半・後半とも 10 日(区間を作る最小)より長く、本数も違う


def _setup():
    rng = np.random.default_rng(5)
    n = NDAYS * 1440
    t = np.array([T0 + i * M for i in range(n)], dtype=np.int64)
    c = 1_000_000.0 + np.cumsum(rng.normal(0, 100, n))
    bars = dp.Bars(t, c + 50, c - 50, c)
    days = [dt.utc_day(T0 + d * DAY) for d in range(NDAYS)]
    sigs = [(T0 + d * DAY + hh * 60 * M + 7 * M, 1 if (d + k) % 2 else -1)
            for d in range(1, NDAYS - 1) for k, hh in enumerate((3, 9, 15, 21))]
    return bars, days, sigs, dt.utc_day(T0 + CUT_DAY * DAY)


def test_d5_24h_before_control():
    b, days, sigs, _ = _setup()
    res = dp.d5(sigs, b, days)
    for h in dp.HORIZONS:
        want = [v for v in (dp.signal_move(ns - DAY, s, b, h) for ns, s in sigs) if v is not None]
        x = res[h]["control_24h_before"]
        assert x["trades"] == len(want)
        assert x["per_trade"] == pytest.approx(sum(want) / len(want), rel=1e-12, abs=1e-12)


def test_d5_halves():
    b, days, sigs, cut = _setup()
    res = dp.d5_halves(sigs, b, days, cut)
    for half, keep, dd in (("first", lambda d: d < cut, [d for d in days if d < cut]),
                           ("second", lambda d: d >= cut, [d for d in days if d >= cut])):
        want = dp.d5([(ns, s) for ns, s in sigs if keep(dt.utc_day(ns))], b, dd)
        for h in dp.HORIZONS:
            for k in ("signal", "control_24h", "control_24h_before"):
                g, w = res[half][h][k], want[h][k]
                assert w["lo"] is not None
                assert (g["trades"], g["per_trade"], g["lo"], g["hi"]) == pytest.approx(
                    (w["trades"], w["per_trade"], w["lo"], w["hi"]))


def test_render_columns_and_halves_order():
    b, days, sigs, cut = _setup()
    g = "建てた合図(起点 = 建ての時刻)"
    trades = [{"entry_ns": ns, "exit_ns": ns + 10 * M, "side": s, "pnl_jpy": 1.0, "entry_px": float(b.close_at(ns))}
              for ns, s in sigs]
    res = {"name": "合成", "d4": dp.d4(trades, b, days), "d5": {g: dp.d5(sigs, b, days)},
           "d5_halves": {g: dp.d5_halves(sigs, b, days, cut)}, "cut": cut}
    txt = dp.render(res)

    def row(h, x):
        return (f"| {h} 分 | {x['signal']['trades']} | {dt._ci(x['signal'])} | {dt._ci(x['control_24h'])} | "
                f"{dt._ci(x['control_24h_before'])} |")

    p_f, p_s = txt.index(f"### {g} — 前半(日 < {cut})"), txt.index(f"### {g} — 後半(日 ≥ {cut})")
    for h in dp.HORIZONS:
        assert txt.index(row(h, res["d5"][g][h])) < p_f < txt.index(row(h, res["d5_halves"][g]["first"][h])) < p_s
        assert p_s < txt.index(row(h, res["d5_halves"][g]["second"][h]))
