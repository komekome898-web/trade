"""前提の直接の測り(D1b)の台本 `scripts/analysis/d1b_matilda.py` の受け入れの試験。

リードが書いた(L-928「**1.B 2.A**」の 1.B = 台本は委任で作る。決まりの正本は
`docs/DISCUSSIONS/2026-10-08_matilda_main/D1B_SPEC.md`)。作業者は試験を変えずに通す(変えたいときは問いとして返す)。
試験で決まらない振る舞いは作業者が決めてよい。台本が無ければこの組は飛ばす。

台本の口(この試験が決める):
- `SEAL = "2023-12-17T15:00:00+00:00"`・`CUT = "2019-12-09"`・`LABELS = ("i", "ii", "iii", "iv", "both")`
- `base_params()` → 基準の引数(`BASE_PARAMS` に levels 5・entry_setting 4・exit_setting 3 を上書きした新しい dict)。
- `outcome(side, c0, tp_line, break_line, path, t0)` → `(結果, k)`。side = −1(上の起点。下へ戻るのを待つ)/ +1(下の起点)。
  path = 起点の足より後の足 `(ts, 高値, 安値)` の並び(時刻の順。飛ばした足は入れない)。t0 = 起点の足の ts。
  k = (足の ts − t0) の分。1 ≤ k ≤ 40 の足だけを見る。
  上の起点(side −1)で: ブレイク = 高値 ≥ break_line(None なら無い)。k ≤ 20 で 利確 = 安値 ≤ tp_line、
  21 ≤ k ≤ 40 で 戻り = 安値 ≤ c0。足を k の順に見て、最初に何かが起きた足で決める:
  同じ足で (利確 か 戻り) と ブレイク の両方 → "both"、利確 → "i"、戻り → "ii"、ブレイク → "iii"。40 分までに何も無い → ("iv", None)。
  下の起点(side +1)は上下を入れ替える(ブレイク = 安値 ≤ break_line、利確 = 高値 ≥ tp_line、戻り = 高値 ≥ c0)。
- `starts(bars, params=None, seal=SEAL)` → `{"records": [...], "days": [...]}`。
  bars = `bot.bt.simple.read_bars` と同じ形の足 `(ts, 始値, 高値, 安値, 終値, 出来高)` の並び(生成器でもよい)。
  ts が seal 以後の足に届いたら、その足より先を求めない。向きの決まらない足(始値 = 終値 かつ、直前に飛ばさずに回した
  足の終値と同じ、またはデータの頭)は無い足として飛ばす(`src/bot/bt/simple/run.py` の決まり)。
  飛ばさない足ごとに `MatildaSimple(params).decide({"kind": "close", "ts": ts, "price": 終値, "fills": [],
  "touched": [], "bar": 足})` を呼び、その後の `_snap`(次の足の線)と `ind` を読む。`_snap` が None か vola ≤ 0 の足は
  起点にならない(「評価した足」にも入れない)。評価した足の UTC の日を days に(並べて重なり無し)。
  起点 = 終値 > `_snap["up"]`(side −1)か 終値 < `_snap["lo"]`(side +1)。
  1 件の記録の鍵: ts・day・side・entry(直前に評価した足が同じ side の起点でない = True)・gate(`_snap["gate"]`)・
  brk(`decide` の後の戦略のブレイク中の印 `_brk`。玉が無くても終値がブレイクの線を越えると ±1 になる。
  `matilda_simple.py` の `_rejudge`。ブレイク中は建ての注文を置かない = `_place`)・
  c0・center・vola・width(`ind["width"]`)・tp_line(= center − side × exit_setting × vola)・
  break_line(side −1 なら `_snap["bu"]`、+1 なら `_snap["bd"]`)・outcome・k・
  n_win(起点の後 40 分の中の飛ばさない足の数 = 1 ≤ k ≤ 40 の足の数。結果に依らない。足の疎らさを表に並べるため)。
  足の時刻が直前に読んだ足(飛ばした足を含む)より増えていなければ ValueError(ファイルの順の誤りを黙って進めない)。
  終わり end = seal 以後の足に届いたなら seal、届かずに足が尽きたなら最後に読んだ足(飛ばした足を含む)の ts + 1 分。
  起点の ts + 41 分 > end の起点は記録しない(40 分目の足が終わるまでのデータが無い)。
- `ratio_diff_ci(days_a, num_a, den_a, days_b, num_b, den_b)` → `{"mean", "lo", "hi", "mde"}`(後半 b − 前半 a の割合の差)。
  rng = `np.random.default_rng(diag_tables.SEED)`(= 20261004)。先に b、次に a について、1,000 回ずつ: 塊 5 の循環の選び直し
  (`diag_tables._boot_means` と同じ引き方: nb = ceil(n/5)、starts = rng.integers(0, n, size=nb)、
  idx = (starts[:, None] + arange(5)).ravel()[:n] % n)で Σnum[idx] ÷ Σden[idx]。Σden[idx] = 0 の回は捨てる。
  差 = b の回 − a の回(回の番号どうし。どちらかを捨てた回は差も捨てる)。lo・hi = 差の 2.5・97.5 百分位、
  mean = 点の差(Σnum_b ÷ Σden_b − Σnum_a ÷ Σden_a)、mde = 2.8 × 差の標準偏差(ddof=1)。
- `main(argv)`: `--files <足のファイル ...>`(`read_bars` に渡す)・`--out <置き場>`・`--seal`(既定 SEAL)。
  `--seal` が SEAL より後(時刻で比べる。時差の付いた値も UTC に直して比べる)なら、ファイルを開かずに 2 を返す。
  `<置き場>/day_counts.csv`(見出し `day,side,entry,gate,brk,outcome,n`。entry・gate は 0/1、brk は −1/0/1。起点の数を日 × 側 × entry × gate × brk × 結果で数え、
  0 の組は書かない。行は文字列の並びで並べる)と `<置き場>/tables.md`(4 つの見方ごとの表。見方の名前を見出しに含む。
  年・first・second の起点の数と 5 つの結果の割合、first・second の区間、diff の点・区間・MDE。あわせて起点の
  幅 ÷ ボラ と n_win の年ごとの中央値。幅 ÷ ボラ は起点の時点の値で、`width_vola.out` の全部の足の値とは母集団が違うと表に書く)を書き、0 を返す。
- `summarize(records, days, cut=CUT)` → res[見方][期間][結果]。見方 = "entry_open"(entry かつ gate かつ brk = 0)・"entry_all"・
  "point_open"(gate かつ brk = 0。門が開いていて、足が閉じた時点の判定でブレイク中でない)・"point_all"。期間 = 年の文字列(起点の UTC の年)・"first"(day < cut)・"second"(day ≥ cut)。
  各 = {"n": 起点の数, "count": その結果の数, "share": count ÷ n}。first・second はさらに "lo"・"hi" =
  `diag_tables.group_ratio_ci(その期間の days, 日ごとの count, 日ごとの n)` の lo・hi。
  res[見方]["diff"][結果] = `ratio_diff_ci`(first の days・日ごとの count・日ごとの n、second の同じもの)。
  期間の起点が 0 本なら share・lo・hi は None、diff の 4 つも None(どちらかの期間が 0 本のとき)。割り算で落とさない。
"""
from __future__ import annotations

import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "analysis"))
if os.environ.get("D1B_MODULE_DIR"):  # 変異の表: 壊した写しの置き場を先に読む(試験の写しを作らずに当てる)
    sys.path.insert(0, os.environ["D1B_MODULE_DIR"])
d1b = pytest.importorskip("d1b_matilda")
import diag_tables as dt  # noqa: E402

from bot.strategy.matilda_simple import BASE_PARAMS, MatildaSimple  # noqa: E402

T0 = datetime(2020, 1, 1, tzinfo=timezone.utc)


def _ts(minute: int, base: datetime = T0) -> str:
    return (base + timedelta(minutes=minute)).isoformat()


def _path(pairs, base=T0):
    """(k, 高値, 安値) → (ts, 高値, 安値)。起点の足は minute 0。"""
    return [(_ts(k, base), h, lo) for k, h, lo in pairs]


# ------------------------------------------------------------------ outcome(手で作った場面)
UP = dict(side=-1, c0=1000.0, tp_line=970.0, break_line=1050.0, t0=_ts(0))
DN = dict(side=1, c0=1000.0, tp_line=1030.0, break_line=950.0, t0=_ts(0))

OUTCOME_CASES = [
    ("上: 5 分目に利確の線まで", UP, [(1, 1005, 990), (5, 1000, 969)], ("i", 5)),
    ("上: 20 分目に利確の線ちょうど", UP, [(20, 1000, 970.0)], ("i", 20)),
    ("上: 21 分目に利確の線を越えても戻り", UP, [(21, 1000, 960)], ("ii", 21)),
    ("上: 10 分目に起点の値段まで(利確の線の手前)は数えない", UP, [(10, 1001, 999)], ("iv", None)),
    ("上: 10 分目は起点まで、25 分目に起点まで", UP, [(10, 1001, 999), (25, 1002, 1000.0)], ("ii", 25)),
    ("上: 3 分目にブレイクの線", UP, [(3, 1051, 1001)], ("iii", 3)),
    ("上: 3 分目にブレイクの線ちょうど", UP, [(3, 1050.0, 1001)], ("iii", 3)),
    ("上: 4 分目に利確とブレイクの両方", UP, [(4, 1060, 960)], ("both", 4)),
    ("上: 30 分目に戻りとブレイクの両方", UP, [(30, 1060, 990)], ("both", 30)),
    ("上: ブレイクの線が無い", dict(UP, break_line=None), [(3, 99999, 1001)], ("iv", None)),
    ("上: 41 分目は見ない", UP, [(41, 1000, 900)], ("iv", None)),
    ("上: 足の欠け(1 分目と 35 分目だけ)", UP, [(1, 1010, 1001), (35, 1001, 995)], ("ii", 35)),
    ("上: 40 分目にブレイク", UP, [(40, 1050, 1001)], ("iii", 40)),
    ("下: 5 分目に利確の線まで", DN, [(5, 1031, 1000)], ("i", 5)),
    ("下: 25 分目に起点の値段まで", DN, [(25, 1000.0, 990)], ("ii", 25)),
    ("下: 3 分目にブレイクの線ちょうど", DN, [(3, 999, 950.0)], ("iii", 3)),
    ("下: 4 分目に利確とブレイクの両方", DN, [(4, 1040, 940)], ("both", 4)),
    ("下: 何も無い", DN, [(1, 999, 990), (39, 999, 951)], ("iv", None)),
]


@pytest.mark.parametrize("name,kw,pairs,want", OUTCOME_CASES, ids=[c[0] for c in OUTCOME_CASES])
def test_outcome_cases(name, kw, pairs, want):
    got = d1b.outcome(kw["side"], kw["c0"], kw["tp_line"], kw["break_line"], _path(pairs), kw["t0"])
    assert tuple(got) == want, name


# ------------------------------------------------------------------ starts(合成の足を、戦略そのもので作った参照と突き合わせる)
def _synthetic_bars(n=900, seed=7, base=T0, gaps=(150, 151, 400), start_px=1_000_000.0):
    rng = np.random.default_rng(seed)
    px = start_px
    out = []
    for i in range(n):
        if i in gaps:
            continue  # 足の欠け(その分の行が無い)
        o = px
        if i % 97 == 50:
            c = o + 6000.0  # 上への跳ね(上の起点を作る)
        elif i % 89 == 30:
            c = o - 6000.0  # 下への跳ね
        elif i % 53 == 7:
            c = o  # 向きの決まらない足(前の終値 = 始値 = 終値)
        else:
            c = float(round(o + rng.normal(0, 80)))
        h = max(o, c) + float(abs(round(rng.normal(0, 20))))
        lo = min(o, c) - float(abs(round(rng.normal(0, 20))))
        out.append((_ts(i, base), o, h, lo, c, 1.0))
        px = c
    return out


def _ref_outcome(side, c0, tp, brk, fut, t0):
    t0d = datetime.fromisoformat(t0)
    for ts, h, lo in fut:
        k = round((datetime.fromisoformat(ts) - t0d).total_seconds() / 60)
        if k < 1 or k > 40:
            continue
        hit_b = brk is not None and ((h >= brk) if side == -1 else (lo <= brk))
        if k <= 20:
            hit_r = (lo <= tp) if side == -1 else (h >= tp)
            lab = "i"
        else:
            hit_r = (lo <= c0) if side == -1 else (h >= c0)
            lab = "ii"
        if hit_r and hit_b:
            return "both", k
        if hit_r:
            return lab, k
        if hit_b:
            return "iii", k
    return "iv", None


def _reference(bars, params, seal_iso):
    """戦略そのもの(MatildaSimple)で線を取り、起点と結果を作る(台本を使わない参照)。"""
    seal = datetime.fromisoformat(seal_iso)
    st = MatildaSimple(params)
    kept, evald = [], []  # 飛ばさない足、評価した足の (足, snap, ind)
    prev = None
    end = None
    last = None
    for b in bars:
        t = datetime.fromisoformat(b[0])
        if t >= seal:
            end = seal
            break
        last = t
        o, c = b[1], b[4]
        if o == c and (prev is None or o == prev):
            continue
        prev = c
        st.decide({"kind": "close", "ts": b[0], "price": c, "fills": [], "touched": [], "bar": b})
        kept.append(b)
        sn, ind = st._snap, st.ind
        if sn is None or sn["vola"] <= 0:
            continue
        evald.append((len(kept) - 1, dict(sn), dict(ind), st._brk))
    if end is None:
        end = last + timedelta(minutes=1)
    recs, days = [], []
    prev_side = None
    ex = params["exit_setting"]
    for ix, sn, ind, brk_state in evald:
        b = kept[ix]
        day = b[0][:10]
        if not days or days[-1] != day:
            days.append(day)
        c = b[4]
        side = -1 if c > sn["up"] else (1 if c < sn["lo"] else None)
        was = prev_side
        prev_side = side
        if side is None:
            continue
        t0 = datetime.fromisoformat(b[0])
        if t0 + timedelta(minutes=41) > end:
            continue
        tp = sn["center"] - side * ex * sn["vola"]
        brk = sn["bu"] if side == -1 else sn["bd"]
        fut = [(x[0], x[2], x[3]) for x in kept[ix + 1:ix + 60]]
        lab, k = _ref_outcome(side, c, tp, brk, fut, b[0])
        mins = [round((datetime.fromisoformat(x[0]) - t0).total_seconds() / 60) for x in fut]
        n_win = sum(1 for m in mins if 1 <= m <= 40)
        recs.append({"ts": b[0], "day": day, "side": side, "entry": was != side, "gate": sn["gate"], "brk": brk_state,
                     "n_win": n_win, "c0": c,
                     "center": sn["center"], "vola": sn["vola"], "width": ind["width"], "tp_line": tp,
                     "break_line": brk, "outcome": lab, "k": k})
    return recs, days


KEYS = ("ts", "day", "side", "entry", "gate", "brk", "n_win", "c0", "center", "vola", "width", "tp_line", "break_line", "outcome", "k")


def _cmp(got, want):
    assert len(got) == len(want)
    for g, w in zip(got, want):
        for key in KEYS:
            gv, wv = g[key], w[key]
            if isinstance(wv, float) and gv is not None:
                assert math.isclose(gv, wv, rel_tol=0, abs_tol=1e-6), (key, g["ts"], gv, wv)
            else:
                assert gv == wv, (key, g["ts"], gv, wv)


def test_base_params():
    p = d1b.base_params()
    want = dict(BASE_PARAMS)
    want.update({"levels": 5, "entry_setting": 4, "exit_setting": 3})
    assert p == want
    assert p is not BASE_PARAMS


def test_starts_match_strategy_reference():
    bars = _synthetic_bars()
    p = d1b.base_params()
    want, wdays = _reference(bars, p, d1b.SEAL)
    got = d1b.starts(iter(bars), p)
    _cmp(got["records"], want)
    assert list(got["days"]) == wdays
    # 試験の足が場面を持つことの確かめ(足りなければ試験の作りの誤り)
    assert {r["side"] for r in want} == {-1, 1}
    assert any(r["entry"] for r in want) and any(not r["entry"] for r in want)
    assert any(r["brk"] != 0 for r in want) and any(r["brk"] == 0 for r in want)
    assert {r["outcome"] for r in want} >= {"i", "iii"}


def test_starts_default_params_are_base():
    bars = _synthetic_bars(n=400, seed=3)
    _cmp(d1b.starts(iter(bars))["records"], d1b.starts(iter(bars), d1b.base_params())["records"])


def test_starts_gate_closed_is_recorded():
    """幅の下の門を大きくすると門の閉じた起点が記録される(門で起点を落とさない)。"""
    bars = _synthetic_bars()
    p = d1b.base_params()
    p["range_setting"] = 0.05
    want, _ = _reference(bars, p, d1b.SEAL)
    got = d1b.starts(iter(bars), p)["records"]
    _cmp(got, want)
    assert want and not any(r["gate"] for r in want)


def test_starts_stop_at_seal_and_drop_late_starts():
    bars = _synthetic_bars()
    cut_i = 700
    seal = bars[cut_i][0]
    consumed = []

    def gen():
        for b in bars:
            consumed.append(b[0])
            yield b
            if b[0] >= seal:
                raise AssertionError("封印の境の足より先を求めた")

    p = d1b.base_params()
    got = d1b.starts(gen(), p, seal=seal)
    want, wdays = _reference(bars, p, seal)
    _cmp(got["records"], want)
    assert list(got["days"]) == wdays
    sd = datetime.fromisoformat(seal)
    assert all(datetime.fromisoformat(r["ts"]) + timedelta(minutes=41) <= sd for r in got["records"])
    assert consumed[-1] == seal


def test_starts_drop_starts_near_data_end():
    bars = _synthetic_bars()[:600]
    end = datetime.fromisoformat(bars[-1][0]) + timedelta(minutes=1)
    got = d1b.starts(iter(bars), d1b.base_params())["records"]
    want, _ = _reference(bars, d1b.base_params(), d1b.SEAL)
    _cmp(got, want)
    assert all(datetime.fromisoformat(r["ts"]) + timedelta(minutes=41) <= end for r in got)


def test_skipped_bars_are_not_in_path():
    """向きの決まらない足は線にも結果にも使わない: その足の安値が利確の線より下でも、利確にしない。"""
    bars = _synthetic_bars()
    p = d1b.base_params()
    recs = d1b.starts(iter(bars), p)["records"]
    r = next(x for x in recs if x["side"] == -1 and (x["outcome"] == "iv" or (x["outcome"] == "iii" and x["k"] > 1)))
    i = next(j for j, b in enumerate(bars) if b[0] == r["ts"])
    prev_c = bars[i][4]
    t1 = (datetime.fromisoformat(r["ts"]) + timedelta(minutes=1)).isoformat()
    ins = (t1, prev_c, prev_c, r["tp_line"] - 1000.0, prev_c, 1.0)  # 始値 = 終値 = 直前の終値、ヒゲだけ下へ
    later = [b for b in bars[i + 1:] if b[0] > t1]
    bars2 = bars[:i + 1] + [ins] + later
    recs2 = d1b.starts(iter(bars2), p)["records"]
    r2 = next(x for x in recs2 if x["ts"] == r["ts"])
    assert r2["outcome"] != "i"


@pytest.mark.parametrize("dup", ["same", "back"])
def test_starts_refuse_non_increasing_time(dup):
    bars = _synthetic_bars(n=300)
    j = 200
    b = bars[j - 1] if dup == "same" else bars[j - 5]
    bad = bars[:j] + [(b[0],) + tuple(bars[j][1:])] + bars[j + 1:]
    with pytest.raises(ValueError):
        d1b.starts(iter(bad), d1b.base_params())


# ------------------------------------------------------------------ 割合の区間
def _days(n, start=datetime(2019, 1, 1)):
    return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n)]


def _ref_ratio_diff(da, na, ca, db, nb_, cb):
    rng = np.random.default_rng(20261004)

    def boot(days, num, den):
        x = np.array([num.get(d, 0) for d in days], dtype=float)
        y = np.array([den.get(d, 0) for d in days], dtype=float)
        n = len(days)
        nb = math.ceil(n / 5)
        out = []
        for _ in range(1000):
            s = rng.integers(0, n, size=nb)
            idx = (s[:, None] + np.arange(5)[None, :]).ravel()[:n] % n
            dd = y[idx].sum()
            out.append(x[idx].sum() / dd if dd > 0 else None)
        return out

    rb = boot(db, nb_, cb)
    ra = boot(da, na, ca)
    d = np.array([b - a for a, b in zip(ra, rb) if a is not None and b is not None])
    pa = sum(na.values()) / sum(ca.values())
    pb = sum(nb_.values()) / sum(cb.values())
    lo, hi = np.percentile(d, [2.5, 97.5])
    return {"mean": pb - pa, "lo": float(lo), "hi": float(hi), "mde": 2.8 * float(np.std(d, ddof=1))}


def test_ratio_diff_ci_formula():
    rng = np.random.default_rng(1)
    da, db = _days(60), _days(50, datetime(2021, 1, 1))
    ca = {d: int(rng.integers(0, 6)) for d in da}
    cb = {d: int(rng.integers(0, 6)) for d in db}
    na = {d: int(rng.integers(0, c + 1)) for d, c in ca.items()}
    nb_ = {d: int(rng.integers(0, c + 1)) for d, c in cb.items()}
    got = d1b.ratio_diff_ci(da, na, ca, db, nb_, cb)
    want = _ref_ratio_diff(da, na, ca, db, nb_, cb)
    for k in ("mean", "lo", "hi", "mde"):
        assert math.isclose(got[k], want[k], rel_tol=1e-12, abs_tol=1e-12), k


def test_summarize_empty_half_is_none():
    days = _days(30, datetime(2020, 6, 1))
    recs = [{"ts": f"{d}T00:00:00+00:00", "day": d, "side": -1, "entry": True, "gate": True, "brk": 0, "outcome": "i"}
            for d in days]
    res = d1b.summarize(recs, days)
    for v in res:
        for lab in d1b.LABELS:
            assert res[v]["first"][lab]["n"] == 0 and res[v]["first"][lab]["share"] is None
            assert res[v]["first"][lab]["lo"] is None and res[v]["first"][lab]["hi"] is None
            assert all(res[v]["diff"][lab][k] is None for k in ("mean", "lo", "hi", "mde"))
    assert res["point_all"]["second"]["i"]["share"] == 1.0


def test_summarize_counts_and_cis():
    rng = np.random.default_rng(2)
    days = _days(40, datetime(2019, 11, 20)) + _days(40, datetime(2020, 6, 1))
    recs = []
    for d in days:
        for j in range(int(rng.integers(0, 4))):
            recs.append({"ts": f"{d}T00:{j:02d}:00+00:00", "day": d, "side": int(rng.choice([-1, 1])),
                         "entry": bool(rng.integers(0, 2)), "gate": bool(rng.integers(0, 2)),
                         "brk": int(rng.choice([0, 0, 1, -1])),
                         "outcome": d1b.LABELS[int(rng.integers(0, 5))]})
    res = d1b.summarize(recs, days)
    views = {"entry_open": lambda r: r["entry"] and r["gate"] and r["brk"] == 0, "entry_all": lambda r: r["entry"],
             "point_open": lambda r: r["gate"] and r["brk"] == 0, "point_all": lambda r: True}
    assert set(res) == set(views)
    for v, f in views.items():
        sel = [r for r in recs if f(r)]
        for per, keep, pdays in (("first", lambda d: d < d1b.CUT, [d for d in days if d < d1b.CUT]),
                                 ("second", lambda d: d >= d1b.CUT, [d for d in days if d >= d1b.CUT])):
            rs = [r for r in sel if keep(r["day"])]
            den = {}
            for r in rs:
                den[r["day"]] = den.get(r["day"], 0) + 1
            for lab in d1b.LABELS:
                num = {}
                for r in rs:
                    if r["outcome"] == lab:
                        num[r["day"]] = num.get(r["day"], 0) + 1
                cell = res[v][per][lab]
                assert cell["n"] == len(rs) and cell["count"] == sum(num.values())
                assert math.isclose(cell["share"], sum(num.values()) / len(rs))
                g = dt.group_ratio_ci(pdays, num, den)
                assert math.isclose(cell["lo"], g["lo"]) and math.isclose(cell["hi"], g["hi"])
        for y in ("2019", "2020"):
            rs = [r for r in sel if r["day"][:4] == y]
            for lab in d1b.LABELS:
                cell = res[v][y][lab]
                assert cell["n"] == len(rs) and cell["count"] == sum(r["outcome"] == lab for r in rs)
        fd = [d for d in days if d < d1b.CUT]
        sd = [d for d in days if d >= d1b.CUT]
        for lab in d1b.LABELS:
            def cnt(days_, only_lab):
                out = {}
                for r in sel:
                    if r["day"] in days_ and (not only_lab or r["outcome"] == lab):
                        out[r["day"]] = out.get(r["day"], 0) + 1
                return out
            want = d1b.ratio_diff_ci(fd, cnt(fd, True), cnt(fd, False), sd, cnt(sd, True), cnt(sd, False))
            got = res[v]["diff"][lab]
            for k in ("mean", "lo", "hi", "mde"):
                assert math.isclose(got[k], want[k], rel_tol=1e-12, abs_tol=1e-12), (v, lab, k)


# ------------------------------------------------------------------ 出力
def test_main_writes_day_counts(tmp_path):
    import csv
    import gzip
    bars = _synthetic_bars()
    f = tmp_path / "candles_1m_2020.csv.gz"
    with gzip.open(f, "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ts", "open", "high", "low", "close", "volume"])
        for b in bars:
            w.writerow(list(b))
    out = tmp_path / "out"
    assert d1b.main(["--files", str(f), "--out", str(out)]) == 0
    with open(out / "day_counts.csv", encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["day", "side", "entry", "gate", "brk", "outcome", "n"]
    recs = d1b.starts(iter(bars), d1b.base_params())["records"]
    want = {}
    for r in recs:
        k = (r["day"], str(r["side"]), str(int(r["entry"])), str(int(r["gate"])), str(r["brk"]), r["outcome"])
        want[k] = want.get(k, 0) + 1
    got = {tuple(x[:6]): int(x[6]) for x in rows[1:]}
    assert got == want
    assert rows[1:] == sorted(rows[1:])
    txt = (out / "tables.md").read_text(encoding="utf-8")
    assert all(v in txt for v in ("entry_open", "entry_all", "point_open", "point_all"))
    res = d1b.summarize(recs, d1b.starts(iter(bars), d1b.base_params())["days"])
    for v in ("point_open", "point_all"):
        for lab in ("i", "iii"):
            share = res[v]["second"][lab]["share"]
            assert f"{100 * share:.1f}" in txt, (v, lab)  # 表の数が summarize と同じ(% で小数 1 桁)


@pytest.mark.parametrize("seal", ["2024-01-01T00:00:00+00:00", "2023-12-17T09:00:00-08:00"])  # 後者 = 17:00Z(文字列では前に見える)
def test_main_refuses_later_seal(tmp_path, seal):
    missing = tmp_path / "candles_1m_2024.csv.gz"  # 開けば無いファイルの例外になる
    assert d1b.main(["--files", str(missing), "--out", str(tmp_path / "o"), "--seal", seal]) == 2
    assert not (tmp_path / "o" / "day_counts.csv").exists()
