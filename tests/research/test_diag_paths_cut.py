"""読み口 `scripts/analysis/diag_paths.py` の足し(分析の持ち越しの 2・3)の受け入れの試験。

リードが書いた。持ち越しの 2 = D5 の対照に「24 時間前の同じ時刻」を足す(分析のスキル D5「対照が中立かを確かめる」:
「24 時間前の対照も並べ、本体を先に読み、対照との差は後に読む」)。持ち越しの 3 = 門で外した合図の読みを前半・後半に分ける
(`--cut`)。L-909「**24 時間前の対照(読み口にまだ口が無い)。**」「**門で外した合図の読みを前半・後半に分けることと、ほかの門の値での読み。**」・L-927「**進めてください**」。
作業者は試験を変えずに通す(変えたいときは問いとして返す)。既存の試験 `tests/research/test_diag_paths.py` も変えずに通す。
2 版目(事前の批評 1 回目 `docs/DISCUSSIONS/2026-10-08_matilda_main/DELEGATION_dpcut_premortem1.md` の指摘で、表の並び・区間の枝・
24 時間前の対照の日・main の組み立て・足を読む範囲・--cut の検めを足した)。

読み口の口(この試験が決める):
- `d5(signals, bars, days)` の各 h の dict に、鍵 "control_24h_before" を足す。中身は "control_24h" と同じ作り
  (`per_day_ratio`。値は `signal_move(ns − DAY, side, bars, h)`、日は**合図の** UTC の日 `dt.utc_day(ns)`(ずらした先の日ではない)、
  足が無ければ数えない)。既にある鍵 "signal"・"control_24h" は変えない。
- `d5_halves(signals, bars, days, cut)` → {"first": d5(前半の合図, bars, 前半の日), "second": d5(後半の合図, bars, 後半の日)}。
  前半 = `dt.utc_day(ns) < cut`、後半 = それ以外。前半の日 = days のうち cut より前、後半の日 = cut 以後。
- `check_cut(cut, days)`: cut が 10 字の YYYY-MM-DD(`date.fromisoformat(cut).isoformat() == cut`)でない、または
  `days[0] < cut <= days[-1]` でない(片方の半分の日が 0 になる)なら ValueError。
- `bar_window(trades, others)` → (lo, hi)。lo = 全部の取引(trades と others)の entry_ns と signal_ns(ある行だけ)の最小 − DAY − 2 分、
  hi = 全部の取引の exit_ns の最大 + 2 × DAY(封印の境で切るのは main)。24 時間前の対照に要る足を、最初の合図の 1 日前から読む。
- `build_res(name, trades, bars, days, other=None, other_name="other", cut=None)` → main が書く res(鍵 "name"・"d4"(今の d4)・"d5"、cut があれば "d5_halves"・"cut")。
  res["d5"] の群は今の main と同じ 2 つ(建てた合図・起点 = 合図の時刻 / 建ての時刻)と、other があれば建てなかった合図の 2 つ
  (群の名前は今の main と同じ形で、`<走らせ>` の所に other_name)。cut があれば check_cut を通し、res["d5_halves"] に
  res["d5"] と同じ鍵の全部の群の d5_halves を、res["cut"] に cut を入れる。cut が無ければ "d5_halves"・"cut" の鍵を持たない。
  main はこれを呼ぶ(足を読む範囲は bar_window で決め、hi は封印の境で切る)。
- `render(res)`: D5 の表の列は「合図の後 | 合図 | 起点から [区間] | 対照(24 時間後の同じ時刻)[区間] | 対照(24 時間前の同じ時刻)[区間]」。
  res に "d5_halves" があれば、群ごとに、本体の表の後に見出し `### <群の名前> — 前半(日 < <cut>)` の表、その後に
  `### <群の名前> — 後半(日 ≥ <cut>)` の表を、本体と同じ列で書く。D5 の節の頭に 1 行
  「前半・後半は合図の UTC の日で分けた(D1 の表は取引の出の UTC の日で分ける)」を書く。
- `main(argv)`: 引数 `--cut YYYY-MM-DD` を足す(無ければ今までどおり)。
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
NDAYS = 32  # 前半・後半とも 10 日(区間を作る最小の日数)より長くする
CUT_DAY = 14  # 前半 14 日・後半 18 日(数が違うように)
G_SIG, G_ENT = "建てた合図(起点 = 合図の時刻)", "建てた合図(起点 = 建ての時刻)"


def _bars(seed=5):
    n = NDAYS * 1440
    rng = np.random.default_rng(seed)
    t = np.array([T0 + i * M for i in range(n)], dtype=np.int64)
    c = 1_000_000.0 + np.cumsum(rng.normal(0, 100, n))
    return dp.Bars(t, c + 50, c - 50, c)


def _days():
    return [dt.utc_day(T0 + d * DAY) for d in range(NDAYS)]


def _cut():
    return dt.utc_day(T0 + CUT_DAY * DAY)


def _sigs():
    out = []
    for d in range(1, NDAYS - 1):
        for k, hh in enumerate((3, 9, 15, 21)):
            out.append((T0 + d * DAY + hh * 60 * M + 7 * M, 1 if (d + k) % 2 else -1))
    return out


def _trades(sigs, b, lag=15):
    return [{"signal_ns": ns, "entry_ns": ns + lag * M, "exit_ns": ns + (lag + 10) * M, "side": s, "pnl_jpy": 1.0,
             "entry_px": float(b.close_at(ns + lag * M))} for ns, s in sigs]


def _mean(vals):
    return sum(vals) / len(vals)


def _same(g, w):
    assert g["trades"] == w["trades"]
    assert g["per_trade"] == pytest.approx(w["per_trade"], rel=1e-12, abs=1e-12)
    if w["lo"] is None:
        assert g["lo"] is None
    else:
        assert g["lo"] == pytest.approx(w["lo"]) and g["hi"] == pytest.approx(w["hi"])


# ------------------------------------------------------------------ U1 24 時間前の対照
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
        assert x["control_24h_before"]["lo"] is not None  # 区間の枝が走る長さ
        after = [v for v in (dp.signal_move(ns + DAY, s, b, h) for ns, s in sigs) if v is not None]
        assert x["control_24h"]["per_trade"] == pytest.approx(_mean(after), rel=1e-12, abs=1e-12)


def test_before_control_skips_missing_bars():
    b, days = _bars(), _days()
    sig = [(T0 + 12 * 60 * M, 1)]  # 1 日目。24 時間前の足は無い
    res = dp.d5(sig, b, days)
    for h in dp.HORIZONS:
        assert res[h]["signal"]["trades"] == 1
        assert res[h]["control_24h_before"]["trades"] == 0


# ------------------------------------------------------------------ U2 前半・後半
def test_d5_halves_split_by_utc_day():
    b, days, sigs, cut = _bars(), _days(), _sigs(), _cut()
    res = dp.d5_halves(sigs, b, days, cut)
    assert set(res) == {"first", "second"}
    first = [(ns, s) for ns, s in sigs if dt.utc_day(ns) < cut]
    second = [(ns, s) for ns, s in sigs if dt.utc_day(ns) >= cut]
    for half, sel, dd in (("first", first, [d for d in days if d < cut]), ("second", second, [d for d in days if d >= cut])):
        want = dp.d5(sel, b, dd)
        for h in dp.HORIZONS:
            for k in ("signal", "control_24h", "control_24h_before"):
                assert want[h][k]["lo"] is not None  # 区間の枝が走る(半分とも 10 日以上)
                _same(res[half][h][k], want[h][k])


def test_d5_halves_boundary_day_goes_to_second():
    b, days, cut = _bars(), _days(), _cut()
    sig = [(T0 + CUT_DAY * DAY, 1), (T0 + CUT_DAY * DAY - M, -1)]  # 境の日の 0 時ちょうど と その 1 分前
    res = dp.d5_halves(sig, b, days, cut)
    assert res["second"][1]["signal"]["trades"] == 1
    assert res["first"][1]["signal"]["trades"] == 1
    # 24 時間前の対照も合図の日で数える(ずらした先の日ではない)
    assert res["second"][1]["control_24h_before"]["trades"] == 1
    assert res["first"][1]["control_24h_before"]["trades"] == 1


@pytest.mark.parametrize("cut", ["20191215", "2019-12-1", "2019-W50-1", "2019-11-30", "2019-12-01", "2020-01-02", "2020-02-01"])
def test_check_cut_rejects(cut):
    with pytest.raises(ValueError):
        dp.check_cut(cut, _days())  # 期間は 2019-12-01〜2020-01-01


def test_check_cut_accepts():
    dp.check_cut(_cut(), _days())
    dp.check_cut("2020-01-01", _days())


# ------------------------------------------------------------------ U4 main の組み立て
def test_bar_window_reaches_one_day_before_first_signal():
    b = _bars()
    tr = _trades(_sigs()[3:], b)
    other = _trades(_sigs()[:6], b, lag=30)
    lo, hi = dp.bar_window(tr, other)
    first = min([t["signal_ns"] for t in tr + other] + [t["entry_ns"] for t in tr + other])
    assert lo == first - DAY - 2 * M
    assert hi == max(t["exit_ns"] for t in tr + other) + 2 * DAY
    tr2 = [{k: v for k, v in t.items() if k != "signal_ns"} for t in tr]  # 合図の時刻の無い行
    lo2, _ = dp.bar_window(tr2, [])
    assert lo2 == min(t["entry_ns"] for t in tr2) - DAY - 2 * M


def test_build_res_groups_and_halves():
    b, days, sigs, cut = _bars(), _days(), _sigs(), _cut()
    taken = _trades(sigs[::2], b)
    other = _trades(sigs, b)  # 建てなかった合図 = other にあって taken に無い合図
    res = dp.build_res("合成", taken, b, days, other=other, other_name="門無し", cut=cut)
    want_groups = {G_SIG, G_ENT, "建てなかった合図(起点 = 合図の時刻。門無し にあってこちらに無い)",
                   "建てなかった合図(起点 = 門無し で建った時刻)"}
    assert set(res["d5"]) == want_groups
    assert set(res["d5_halves"]) == want_groups
    assert res["cut"] == cut
    blocked = [(t["signal_ns"], t["side"]) for t in other if t["signal_ns"] not in {x["signal_ns"] for x in taken}]
    _same(res["d5_halves"]["建てなかった合図(起点 = 合図の時刻。門無し にあってこちらに無い)"]["first"][15]["signal"],
          dp.d5_halves(blocked, b, days, cut)["first"][15]["signal"])
    res2 = dp.build_res("合成", taken, b, days)
    assert set(res2["d5"]) == {G_SIG, G_ENT}
    assert "d5_halves" not in res2 and "cut" not in res2
    with pytest.raises(ValueError):
        dp.build_res("合成", taken, b, days, cut="2019-11-30")


def test_main_has_cut_argument(capsys):
    with pytest.raises(SystemExit):
        dp.main(["--help"])
    assert "--cut" in capsys.readouterr().out


# ------------------------------------------------------------------ U3 表
def _row(h, x):
    return (f"| {h} 分 | {x['signal']['trades']} | {dt._ci(x['signal'])} | {dt._ci(x['control_24h'])} | "
            f"{dt._ci(x['control_24h_before'])} |")


def test_render_columns_order_and_halves():
    b, days, sigs, cut = _bars(), _days(), _sigs(), _cut()
    taken = _trades(sigs, b)
    res = dp.build_res("合成", taken, b, days, cut=cut)
    res["d4"] = dp.d4([{k: v for k, v in t.items() if k != "signal_ns"} for t in taken], b, days)
    txt = dp.render(res)
    assert "| 合図の後 | 合図 | 起点から [区間] | 対照(24 時間後の同じ時刻)[区間] | 対照(24 時間前の同じ時刻)[区間] |" in txt
    assert "前半・後半は合図の UTC の日で分けた(D1 の表は取引の出の UTC の日で分ける)" in txt
    for g in (G_SIG, G_ENT):
        main_x = res["d5"][g]
        hf, hs = f"### {g} — 前半(日 < {cut})", f"### {g} — 後半(日 ≥ {cut})"
        p_main, p_f, p_s = txt.index(f"### {g}\n"), txt.index(hf), txt.index(hs)
        assert p_main < p_f < p_s
        for h in dp.HORIZONS:
            assert main_x[h]["control_24h"]["per_trade"] != main_x[h]["control_24h_before"]["per_trade"]
            r_main = txt.index(_row(h, main_x[h]), p_main)
            assert r_main < p_f
            fx, sx = res["d5_halves"][g]["first"][h], res["d5_halves"][g]["second"][h]
            assert fx["signal"]["trades"] != sx["signal"]["trades"]
            r_f = txt.index(_row(h, fx), p_f)
            r_s = txt.index(_row(h, sx), p_s)
            assert p_f < r_f < p_s < r_s
    res2 = {k: v for k, v in res.items() if k not in ("d5_halves", "cut")}
    txt2 = dp.render(res2)
    assert "— 前半" not in txt2 and "前半・後半は合図の UTC の日で分けた" not in txt2
