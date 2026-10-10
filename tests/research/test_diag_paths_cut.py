"""読み口 `scripts/analysis/diag_paths.py` の足し(分析の持ち越しの 2・3)の受け入れの試験。

リードが書いた。持ち越しの 2 = D5 の対照に「24 時間前の同じ時刻」を足す(分析のスキル D5「対照が中立かを確かめる」:
「24 時間前の対照も並べ、本体を先に読み、対照との差は後に読む」)。持ち越しの 3 = 門で外した合図の読みを前半・後半に分ける
(`--cut`)。L-909「**次の私の「進めてください」の合図で順次始めてください。**」・L-927「**進めてください**」。
作業者は試験を変えずに通す(変えたいときは問いとして返す)。既存の試験 `tests/research/test_diag_paths.py` も変えずに通す。

読み口の口(この試験が決める):
- `d5(signals, bars, days)` の各 h の dict に、鍵 "control_24h_before" を足す。中身は "control_24h" と同じ作り
  (`per_day_ratio`。値は `signal_move(ns − DAY, side, bars, h)`、日は合図の UTC の日 `dt.utc_day(ns)`、足が無ければ数えない)。
  既にある鍵 "signal"・"control_24h" は変えない。
- `d5_halves(signals, bars, days, cut)` → {"first": d5(前半の合図, bars, 前半の日), "second": d5(後半の合図, bars, 後半の日)}。
  前半 = `dt.utc_day(ns) < cut`、後半 = それ以外。前半の日 = days のうち cut より前、後半の日 = cut 以後。
- `render(res)`: D5 の表に列「対照(24 時間前の同じ時刻)[区間]」を足す(既にある列の後ろ)。res に鍵 "d5_halves"
  ({群の名前: {"first": …, "second": …}})があれば、群ごとに見出し `### <群の名前> — 前半(日 < <cut>)` と
  `### <群の名前> — 後半(日 ≥ <cut>)` の表を足す(res["cut"] に境の文字列)。
- `main(argv)`: 引数 `--cut YYYY-MM-DD` を足す(無ければ今までどおり)。渡したときは、D5 の全部の群(建てた合図の 2 つの起点・
  建てなかった合図の 2 つの起点)について d5_halves を作り、res["d5_halves"]・res["cut"] に入れて書く。
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

M = dp.MIN
DAY = dp.DAY
T0 = int(datetime(2019, 12, 1, tzinfo=timezone.utc).timestamp()) * 10**9  # 1 日目の 0 時(UTC)
NDAYS = 16


def _bars(seed=5):
    n = NDAYS * 1440
    rng = np.random.default_rng(seed)
    t = np.array([T0 + i * M for i in range(n)], dtype=np.int64)
    c = 1_000_000.0 + np.cumsum(rng.normal(0, 100, n))
    return dp.Bars(t, c + 50, c - 50, c)


def _days():
    return [dt.utc_day(T0 + d * DAY) for d in range(NDAYS)]


def _sigs():
    out = []
    for d in range(1, NDAYS - 1):
        for k, hh in enumerate((3, 9, 15, 21)):
            out.append((T0 + d * DAY + hh * 60 * M + 7 * M, 1 if (d + k) % 2 else -1))
    return out


def _mean(vals):
    return sum(vals) / len(vals)


def test_d5_has_24h_before_control():
    b, days, sigs = _bars(), _days(), _sigs()
    res = dp.d5(sigs, b, days)
    for h in dp.HORIZONS:
        x = res[h]
        assert set(("signal", "control_24h", "control_24h_before")) <= set(x)
        want = [dp.signal_move(ns - DAY, s, b, h) for ns, s in sigs]
        want = [v for v in want if v is not None]
        assert x["control_24h_before"]["trades"] == len(want)
        assert x["control_24h_before"]["per_trade"] == pytest.approx(_mean(want), rel=1e-12, abs=1e-12)
        # 既にある鍵は変わらない
        after = [v for v in (dp.signal_move(ns + DAY, s, b, h) for ns, s in sigs) if v is not None]
        assert x["control_24h"]["per_trade"] == pytest.approx(_mean(after), rel=1e-12, abs=1e-12)


def test_before_control_skips_missing_bars():
    b, days = _bars(), _days()
    sig = [(T0 + 12 * 60 * M, 1)]  # 1 日目。24 時間前の足は無い
    res = dp.d5(sig, b, days)
    for h in dp.HORIZONS:
        assert res[h]["signal"]["trades"] == 1
        assert res[h]["control_24h_before"]["trades"] == 0


def test_d5_halves_split_by_utc_day():
    b, days, sigs = _bars(), _days(), _sigs()
    cut = dt.utc_day(T0 + 8 * DAY)
    res = dp.d5_halves(sigs, b, days, cut)
    assert set(res) == {"first", "second"}
    first = [(ns, s) for ns, s in sigs if dt.utc_day(ns) < cut]
    second = [(ns, s) for ns, s in sigs if dt.utc_day(ns) >= cut]
    assert first and second
    for half, sel, dd in (("first", first, [d for d in days if d < cut]), ("second", second, [d for d in days if d >= cut])):
        want = dp.d5(sel, b, dd)
        for h in dp.HORIZONS:
            for k in ("signal", "control_24h", "control_24h_before"):
                g, w = res[half][h][k], want[h][k]
                assert g["trades"] == w["trades"]
                assert g["per_trade"] == pytest.approx(w["per_trade"], rel=1e-12, abs=1e-12)
                if w["lo"] is None:
                    assert g["lo"] is None
                else:
                    assert g["lo"] == pytest.approx(w["lo"]) and g["hi"] == pytest.approx(w["hi"])


def test_d5_halves_boundary_day_goes_to_second():
    b, days = _bars(), _days()
    cut = dt.utc_day(T0 + 8 * DAY)
    sig = [(T0 + 8 * DAY, 1), (T0 + 8 * DAY - M, -1)]  # 境の日の 0 時ちょうど と その 1 分前
    res = dp.d5_halves(sig, b, days, cut)
    assert res["second"][1]["signal"]["trades"] == 1
    assert res["first"][1]["signal"]["trades"] == 1


def test_render_has_before_column_and_halves():
    b, days, sigs = _bars(), _days(), _sigs()
    cut = dt.utc_day(T0 + 6 * DAY)  # 前半と後半の合図の数が違うように(前半 5 日・後半 9 日)
    trades = [{"entry_ns": ns, "exit_ns": ns + 10 * M, "side": s, "pnl_jpy": 1.0, "entry_px": float(b.close_at(ns))}
              for ns, s in sigs]
    res = {"name": "合成", "d4": dp.d4(trades, b, days), "d5": {"建てた合図(起点 = 建ての時刻)": dp.d5(sigs, b, days)},
           "d5_halves": {"建てた合図(起点 = 建ての時刻)": dp.d5_halves(sigs, b, days, cut)}, "cut": cut}
    txt = dp.render(res)
    assert "対照(24 時間前の同じ時刻)" in txt
    assert f"### 建てた合図(起点 = 建ての時刻) — 前半(日 < {cut})" in txt
    assert f"### 建てた合図(起点 = 建ての時刻) — 後半(日 ≥ {cut})" in txt
    # 前半・後半の表の数が d5_halves と同じ(1 分の行の合図の数)
    for half in ("first", "second"):
        n = res["d5_halves"]["建てた合図(起点 = 建ての時刻)"][half][1]["signal"]["trades"]
        assert f"| 1 分 | {n} |" in txt
    # 本体の表の行は 合図・24 時間後・24 時間前 の順に区間つきで並ぶ
    for h, x in res["d5"]["建てた合図(起点 = 建ての時刻)"].items():
        assert x["control_24h"]["per_trade"] != x["control_24h_before"]["per_trade"]
        assert (f"| {h} 分 | {x['signal']['trades']} | {dt._ci(x['signal'])} | {dt._ci(x['control_24h'])} | "
                f"{dt._ci(x['control_24h_before'])} |") in txt
    # cut が無い res は今までどおり(前半・後半の見出しが出ない)
    res2 = {k: v for k, v in res.items() if k not in ("d5_halves", "cut")}
    assert "— 前半" not in dp.render(res2)


def test_main_has_cut_argument(capsys):
    with pytest.raises(SystemExit):
        dp.main(["--help"])
    assert "--cut" in capsys.readouterr().out
