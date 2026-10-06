"""# 10 の決定の取り出し(カード 3・5・8 は 1 分足のカードの持ち高から、カード 9 は Binance COIN-M の清算のプリントから)と、
決定ごとの約定の記録の読み(その分の最初の約定の側・その足の中の高値と安値の順)。

D1B_FRAMINGS の行 10: 何を 1 件と数えるか = 「1 決定(その分の最初の約定の側・その足の中の高値と安値の順)」/ 対照 =
「側が半々のときの割合 0.5」。

決定(台本の決め。2026-10-06 のリードの決め 1〜5 で確定):
  カード 3・5・8: カードを `bot.research.cards.run.run_card` で 1 分足に通し(カードは import、写さない)、持ち高 e が
    1 つ前の決定の持ち高と違う分を 1 決定とする。向き = Δe の符号(+1 = 買い、−1 = 売り)。大きさ |Δe| を列に残す。
    約定の分 = 次の空でない足の始まり(W1 仕様 C2: 次の足の始値で約定)。決定の日 = 約定の分の UTC の日(約定の記録の日)。
    決定の種類 = flip(反転 ±1 → ∓1 など符号が変わる)・open(0 → ±)・close(± → 0)・resize(同じ向きの大きさの変化)。
    カード 3(持ち高は連続 1 − 2q)は Δe ≠ 0 の分を全部決定にし、表は種類ごとと全部の行を並べる(リードの決め 1)。
    カード 5・8 の「向きが変わった分」「平均をまたいだ分」= flip。表は flip を主にし、open・close を別の行で並べる(決め 2)。
    カード 3 の窓は 1 時間・1 日・1 週の 3 通り、カード 8 の区切りは jst_day・bf_maint の 2 通り(決め 3)。
  カード 9: Binance COIN-M BTCUSD_PERP の清算のプリント(`bot.research.liq_response.load_binance_cm_liquidations_with_dedup_stats`、
    生の 10 列が全部同じ行を 1 件)。時刻 t0 がその日の中のもの。向き = 清算の向き(SELL = ロングの強制決済 = −1、BUY = +1)。
    約定の分は 2 通り(決め 5): 主 =「秒」= t0 以後の最初の bitFlyer の約定(その約定の側と、時刻 [t0, t0 + 60 秒) の固定の窓の
    約定だけでの高値と安値の順。清算の前の約定は入れない。窓は批評家 1 回目の後のリードの決めで 60 秒の固定)。並べる =「1 分」= t0 を含む分の次の分(REDESIGN §3.2 の 1 分の
    反応の起点)。REDESIGN §3.2 の秒の反応(h 秒の値動き・追い始めるまでの秒数)は作らない。
    Binance の時刻と tardis の時刻の照合(REDESIGN §3.2 の UTC の照合)はしていない。
  側の差の bp(批評家 1 回目の後のリードの決め。決め 7 を取り消し。行 10 の問い「どれだけ動くか」): 各決定に、約定の分の始値と
    「t 以後で、側 = 決定の向きの最初の約定」の値段の差(bp、決定の向きを掛けた符号)を 1 列(side_bp)足す。探すのは約定の分の
    始まり(カード 9 の「秒」は t0)から 60 秒まで。無ければ None(件数を型・分けごとに出す。リードの決め)。

決定ごとに読む約定の記録:
  first_side = 約定の分の最初の約定の側(+1 / −1 / 0 = unknown。約定が無ければ None)
  same_side  = first_side == 向き(成行がその向きに出したときと同じ側の約定で始値が付いた)
  hl_order   = その分の高値と安値の順("up" / "down" / "none"。c4_w6b_order の O3 の決まり。カード 9 の「秒」は上の範囲だけ)
  dir_first  = 向きの側の端が先か(向き +1 なら "up"、−1 なら "down" と同じか。hl_order が "none" なら None)
  side_bp    = d × (始値の後で側 = 向きの最初の約定の値段 − 始値) ÷ 始値 × 1e4(side_wait_ms = その約定までの時間)
"""
from __future__ import annotations

import os
import sys
from datetime import date

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from g3_trades import DAY_NS, DayTrades  # noqa: E402

from common import (FX_DIR, MIN_NS, ROOT, binance_ref_dataset, iso, load_bars,  # noqa: E402
                    usdjpy_ref_dataset)

LIQ_ROOT = "backtest_data/binance_cm_o3c_20260913/liquidationSnapshot/BTCUSD_PERP"
# 決定の型(行 10 の 5 通りのうち、1 分足のカードの持ち高から取るもの)。カード 4 は g3_c4_replay、カード 9 は liq_decisions
CARD_TYPES = {
    "c3_1h": ("c3_yen_premium_revert", "1h"), "c3_1d": ("c3_yen_premium_revert", "1d"),
    "c3_1w": ("c3_yen_premium_revert", "1w"),
    "c5": ("c5_tokyo_fix_momentum", None),
    "c8_jst_day": ("c8_session_mean_revert", "jst_day"), "c8_bf_maint": ("c8_session_mean_revert", "bf_maint"),
}
# 日の前に流す慣らしの長さ。カード 3 の 1 週の窓は「窓が 1 回過ぎるまで 0」なので 1 週より長く(8 日)。窓の中の値だけで
# 持ち高が決まるので、窓が 1 回過ぎた後は、全期間を流した場合と同じ持ち高になる【推定: カードの説明 2・4 から。試験で確かめる】。
# カード 5 は日本時間の日の錨、カード 8 はセッションの和だけを持つので 1 日前から(日本時間の日・保守の区切りの始まりを含む)。
WARMUP_NS = {"c3_yen_premium_revert": 8 * DAY_NS, "c5_tokyo_fix_momentum": DAY_NS, "c8_session_mean_revert": DAY_NS}


def make_card(card_id: str, variant):
    if card_id == "c3_yen_premium_revert":
        from bot.research.cards.library.c3_yen_premium_revert import YenPremiumRevert
        return YenPremiumRevert(variant)
    if card_id == "c5_tokyo_fix_momentum":
        from bot.research.cards.library.c5_tokyo_fix_momentum import TokyoFixMomentum
        return TokyoFixMomentum()
    from bot.research.cards.library.c8_session_mean_revert import SessionMeanRevert
    return SessionMeanRevert(variant)


def card_decl(card_id: str) -> dict:
    """CARD.md の測定の設定の参照の宣言(run_v2・run_b2 と同じ読み方)。"""
    from bot.research.cards import cardmd
    with open(os.path.join(ROOT, f"docs/RESEARCH/cards/{card_id}/CARD.md"), encoding="utf-8") as fh:
        st, problems = cardmd.settings(cardmd.parse(fh.read()))
    if problems:
        raise SystemExit(f"{card_id} の CARD.md の測定の設定が読めない: {problems}")
    return dict(st.declarations)


def run_card_for_day(typ: str, day_ns: int):
    """その日のための 1 回の走らせ: 足は [日 − 慣らし, 日 + 1 日)、参照(カード 3)は同じ範囲。封印の門(common.load_bars・
    bot.bt.data.reference.load_reference)を通して読む。CardRun を返す。"""
    from bot.bt.data.reference import load_reference
    from bot.research.cards.run import run_card
    card_id, variant = CARD_TYPES[typ]
    lo, hi = day_ns - WARMUP_NS[card_id], day_ns + DAY_NS
    bars, _kinds, _h = load_bars(FX_DIR, "FX_BTC_JPY", lo, hi)
    decl = card_decl(card_id)
    refs = {}
    if card_id == "c3_yen_premium_revert":
        from bot.research.cards.library.c3_yen_premium_revert import FX, OVERSEAS
        refs[OVERSEAS] = load_reference(ROOT, binance_ref_dataset(OVERSEAS, "close", lo, hi), declarations=decl)
        # USDJPY は as-of で読む。日の前の週末の分も入るよう、範囲の始めを 4 日前に広げる(値は範囲の中の行だけ)
        refs[FX] = load_reference(ROOT, usdjpy_ref_dataset(FX, lo - 4 * DAY_NS, hi, extend=True), declarations=decl)
    card = make_card(card_id, variant)
    return run_card(card, bars, references=refs, declarations=decl, venue="bitflyer", symbol="FX_BTC_JPY")


def exposure_decisions(start_ns, end_ns, volume, decided, exposure) -> list:
    """持ち高の系列から決定を取り出す(先読みなし: 決定 i の判断は足 i の終わりまでの持ち高、約定の分は次の空でない足の
    始まり)。最初の決定の前の持ち高は 0。戻り値: dict の列(t_ns = 決定の時刻 = 足の終わり、fill_ns、dir、size、kind)。"""
    out = []
    prev = 0.0
    n = len(start_ns)
    nonempty = np.flatnonzero(np.asarray(volume) > 0)
    for i in range(n):
        if not decided[i]:
            continue
        e = float(exposure[i])
        if e == prev:
            continue
        k = int(np.searchsorted(nonempty, i, side="right"))
        j = int(nonempty[k]) if k < len(nonempty) else None
        d = 1 if e > prev else -1
        if prev != 0 and e != 0 and np.sign(prev) != np.sign(e):
            kind = "flip"
        elif prev == 0:
            kind = "open"
        elif e == 0:
            kind = "close"
        else:
            kind = "resize"
        out.append({"t_ns": int(end_ns[i]), "fill_ns": None if j is None else int(start_ns[j]), "dir": d,
                    "size": abs(e - prev), "kind": kind})
        prev = e
    return out


def card_decisions_for_day(typ: str, day_ns: int, run=None) -> list:
    """その日(約定の分がその日の中)の決定。"""
    r = run if run is not None else run_card_for_day(typ, day_ns)
    ds = exposure_decisions(r.start_ns, r.end_ns, r.volume, r.decided, r.exposure)
    return [d for d in ds if d["fill_ns"] is not None and day_ns <= d["fill_ns"] < day_ns + DAY_NS]


def liq_prints_for_day(day: str):
    """その UTC の日の清算のプリント(一意化の後)と、一意化の件数。"""
    from bot.research.liq_response import load_binance_cm_liquidations_with_dedup_stats
    d = date.fromisoformat(day)
    ev, stats = load_binance_cm_liquidations_with_dedup_stats(os.path.join(ROOT, LIQ_ROOT), d, d)
    lo = iso(day + "T00:00:00Z")
    inside = [e for e in ev if lo <= e.ts_ms * 1_000_000 < lo + DAY_NS]
    return inside, {"read": len(ev), "in_day": len(inside), "dedup": stats.__dict__ if hasattr(stats, "__dict__") else str(stats)}


def liq_decisions(prints) -> list:
    """プリント → 決定(向き = 清算の向き。約定の分は「1 分」と「秒」の 2 通りを、読みの段で付ける)。"""
    return [{"t_ns": e.ts_ms * 1_000_000, "dir": -1 if e.side == "long" else 1, "qty": e.qty} for e in prints]


SEC_WINDOW_NS = 60 * 1_000_000_000  # カード 9 の「秒」の窓: t0 から 60 秒の固定(リードの決め、批評家 1 回目の後)


SIDE_LIMIT_NS = 60 * 1_000_000_000  # side_bp の探す長さの上限: 約定の分の始まりから 60 秒(リードの決め。古い・遠い約定を使わない)


def side_bp(dt: DayTrades, i: int, d: int, t_start: int) -> dict:
    """行 i(約定の分の始値 = その分の最初の約定、カード 9 の「秒」は t0 以後の最初の約定)の値段と、行 i 以後で側 = 決定の向きの
    最初の約定の値段の差(bp、決定の向きを掛けた符号: d × (その値段 − 始値) ÷ 始値 × 1e4)。正 = 決定の向きの成行は始値より
    不利な値段で付く。探すのは t_start(約定の分の始まり。カード 9 の「秒」は t0)から 60 秒まで。その間にその側の約定が
    無ければ None(表では「60 秒以内に向きの側の約定が無い」件数として出す)。"""
    j = dt.next_with_side(i, d)
    if j is None or int(dt.ts[j]) >= t_start + SIDE_LIMIT_NS:
        return {"side_bp": None, "side_wait_ms": None}
    p0 = float(dt.px[i])
    return {"side_bp": d * (float(dt.px[j]) - p0) / p0 * 1e4, "side_wait_ms": (int(dt.ts[j]) - int(dt.ts[i])) / 1e6}


def read_decision(dt: DayTrades, fill_ns, d: int) -> dict:
    """約定の分 fill_ns(分の始まり)の最初の約定の側と、その分の高値と安値の順と、側の差の bp。"""
    if fill_ns is None or fill_ns not in dt.minutes:
        return {"first_side": None, "same_side": None, "hl_order": None, "dir_first": None, "side_bp": None,
                "side_wait_ms": None}
    i = dt.first_in_minute(fill_ns)
    fs = int(dt.side[i])
    o = dt.hl_order(fill_ns)
    return dict({"first_side": fs, "same_side": None if fs == 0 else fs == d, "hl_order": o,
                 "dir_first": None if o == "none" else (o == ("up" if d == 1 else "down"))}, **side_bp(dt, i, d, fill_ns))


def read_liq_decision(dt: DayTrades, t_ns: int, d: int) -> dict:
    """カード 9: 主 =「秒」= t0 以後の最初の約定(その側・側の差の bp・t0 からの待ち wait_ms)と、時刻 [t0, t0 + 60 秒) の約定
    だけでの高値と安値の順(清算の前の約定は入れない。60 秒が日の終わりを越える分は日の中だけ = window_truncated)。
    並べる =「1 分」= t0 を含む分の次の分(read_decision と同じ)。"""
    m1 = (t_ns // MIN_NS + 1) * MIN_NS
    one = read_decision(dt, m1, d)
    i = dt.first_at_or_after(t_ns)
    trunc = t_ns + SEC_WINDOW_NS > dt.day_ns + DAY_NS
    if i is None:
        sec = {"first_side": None, "same_side": None, "hl_order": None, "dir_first": None, "wait_ms": None,
               "side_bp": None, "side_wait_ms": None, "window_truncated": trunc}
    else:
        fs = int(dt.side[i])
        o = dt.hl_order_window(t_ns, t_ns + SEC_WINDOW_NS)
        sec = dict({"first_side": fs, "same_side": None if fs == 0 else fs == d, "hl_order": o,
                    "dir_first": None if o == "none" else (o == ("up" if d == 1 else "down")),
                    "wait_ms": (int(dt.ts[i]) - t_ns) / 1e6, "window_truncated": trunc}, **side_bp(dt, i, d, t_ns))
    return {"one_min": one, "sec": sec}


__all__ = ["CARD_TYPES", "LIQ_ROOT", "card_decisions_for_day", "exposure_decisions", "liq_decisions",
           "liq_prints_for_day", "read_decision", "read_liq_decision", "run_card_for_day"]
