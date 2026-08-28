#!/usr/bin/env python3
"""
FX-S4 JUDGMENT -- IMPULSE-DIRECTION RESUMPTION (E+60s -> E+300s) ON BACKWARD-FRESH
2005-2014 US MACRO EVENTS.  RUN ONCE.

PRE-REGISTRATION -- docs/PREREG_fx_s4_judgment.md, frozen 2026-08-28, reproduced
VERBATIM below.  This script implements that document and nothing else.
================================================================================

    # PREREG -- FX-S4判定: 初撃方向再開(E+60s→300s)の後方新鮮イベント検定

    **凍結日: 2026-08-28。以降の変更は「事前登録の破棄」。**
    横展開ラウンド(Round 26)の第1弾。対象は KNOWLEDGE_FX §4 に係属登録済みの唯一の
    コスト込み正候補: 「米指標イベントの初撃 → 部分押し → E+60〜300秒での方向再開」。

    ## 0. 位置づけ

    - S4(第20報系)の実測: 実測コスト後で**全6セル正(+0.8〜+3.0bps)、ただし t<1.6**、
      かつ**事前登録外の発見**だったため採用不可 → 「新鮮イベント限定で再検定」と登録済み。
    - 新鮮の定義(本登録の核心): S4 が使ったのは 2015〜2026 の477イベント。
      **2005〜2014 のイベントは一度も触れられていない後方新鮮データ**であり、
      Dukascopy ティック(2005年〜、取得方法は KNOWLEDGE_FX §5 に実証済み)で判定可能。
      未来方向の新鮮イベント(月4〜5件)を待つより1桁速く、同等に汚染がない。

    ## 1. 判定対象(S4 の6セルを逐語凍結 — 変更・追加禁止)

    S4 実装(`scripts/research_fx_event_ticks.py` 系)のセル定義をそのまま使う:
    エントリ = E+60s に初撃方向(E→E+5s の符号)へ成行、決済 = E+300s 成行、
    イベント {NFP, CPI, FOMC} × 方向条件等 S4 の6構成を**コードから逐語移植**
    (本 PREREG はセルを再定義しない — S4 の実装が正)。BOJ は発表時刻が漂うため
    S4 同様ティックバースト推定で E を定める。

    ## 2. データ

    - **判定セット: 2005-01-01〜2014-12-31 の米指標イベント**(NFP・CPI・FOMC)。
      カレンダーは**一次資料から構築**(BLS リリースアーカイブ、Fed FOMC 履歴 —
      §4.5 の教訓どおり「12日近傍」等のルール推定は使わない)。目標 n ≥ 300。
    - ティック: Dukascopy USDJPY(bi5、月0始まり・LZMA・429=0.25s/req 制限を遵守)、
      各イベント E−10分〜E+10分の窓のみ取得(全量ではない)。bid/ask 両方。
    - スナップショットを `backtest_data/fx_event_ticks_2005_2014/` に恒久保存。

    ## 3. 判定基準(凍結)

    1. **機構の再現**: 判定セットで、S4 と同一の6セルのグロス(E+60→300 の方向付き値幅)が
       **同符号 かつ イベントクラスタ t ≥ 2.0**(6セル中、S4 で最良だった上位2セルを
       主判定とし事前指名: S4 実装内の net 順位で機械的に決まる2つ。残り4セルは台地条件 —
       過半が同符号であること)。
    2. **当時コストでの成立**: 判定セット自体の bid/ask から**その時代の実効コスト**を実測し
       (2005〜2010年の店頭FXはスプレッドが今より広い — 現在の0.71bpsを仮定しない)、
       当時コスト込みでも主2セルが正であること(t≥1.5 で可 — コストは時代付随条件のため)。
    3. **今日コストでの経済性**: 現在の実測コスト地図(KNOWLEDGE_FX §2.5: E+60→300 の
       往復実コスト中央値 0.89〜1.46bps)を適用した net > 0、主2セルとも。
    4. 通過時の2段目: **未来方向の新鮮イベントでのペーパー追跡**(GMOコインFX API 想定、
       週末フラット・UTC21成行禁止・介入テールルールの安全不変条件込み)。
       ペーパー開始はオーナー承認制。

    ## 4. 必須報告

    全6セル×{2005-14判定, 2015-26参照}の表(グロス・当時コスト net・今日コスト net・
    イベントクラスタt/CI・n)/ 年次分解(機構が特定の時代に偏っていないか)/
    スプレッドの時代推移(2005→2014)/ 初撃サイズの時代比較(§2.5: ピークは2023-24)/
    サニティ(E推定の妥当性・カレンダー一次資料率・ルックアヘッド0・決定性)/
    多重性(6セル・主2事前指名)。

    ## 5. 読み方(先に決める)

    | 結果 | 結論 |
    |---|---|
    | 1〜3すべて通過 | 2段目(未来ペーパー)へ。**全市場で初の判定通過候補** |
    | 機構は再現するが当時コストで負 | 「時代コスト依存」— 今日コストでの成立を条件に格下げ通過を**しない**(機構が当時の市場で取引不能だったなら、なぜ今残っているかの説明義務が生じる — その検討をレポートに書き、不通過とする) |
    | 機構が再現しない(符号不安定/t<2) | S4 の+0.8〜3.0bps は掘り出しと確定。棄却 |

    署名: リード。実装: `scripts/research_fx_s4_judgment.py`(本文書逐語、S4実装を import/移植、
    seed 20260828)。

================================================================================
HOW THE PRE-REGISTRATION IS TURNED INTO CODE (fixed before any number was read)
================================================================================

THE SIX CELLS ARE NOT RE-DEFINED HERE.  They are imported.
    scripts/research_fx_event_ticks.py prints exactly one table with exactly six
    rows for "enter at E+60s WITH the impulse, exit at E+300s" -- its family
    "F2R" (the mechanical mirror of F2), tabulated as
        {exploration, judgment} x {m = 5, 10, 20 bps}
    That is the 6-cell object KNOWLEDGE_FX sec.4 refers to ("all six cells
    positive after measured cost, but t < 1.6": the six F2R net_base means are
    +0.767 .. +2.196 and the largest t is +1.59).  This script enumerates the
    same six (split, m) pairs in the same order and calls s4.run_config(...,
    "F2R", m, s4.F2_EXIT_S) -- the S4 function itself.  Entry offset, exit
    offset, direction rule, fill rule, fee and threshold list all come from the
    S4 module's own constants.  Nothing about a cell is written down twice.

THE SPLIT INSIDE A LIBRARY is S4's rule verbatim: sort the whole calendar by
    nominal event time, first 60% by COUNT = exploration, last 40% = judgment,
    boundary fixed BEFORE validity filtering.  S4 hardcodes 286 of 477; the same
    arithmetic gives 192 of 320 here.  A self-check asserts the formula
    reproduces 286 for 477.

THE PRIMARY TWO CELLS ARE PRE-DESIGNATED MECHANICALLY, BY CODE, FROM THE 2015-
2026 REFERENCE RUN, BEFORE THE 2005-2014 NUMBERS ARE COMPUTED.  The ranking key
    is S4's own selection key: net_base mean descending, tie-break by t
    descending (s4 SELECTION: sort_values(["mean","t"], ascending=False)).  The
    full 6-row ranking is printed.  A reproduction gate asserts the six
    reference net_base means equal the ones the committed S4 run printed.

E (THE RELEASE INSTANT) IS S4'S PROCEDURE VERBATIM: for NFP / CPI / FOMC,
    E = calendar.csv time_utc, which is primary-source verified.  The judgment
    set contains no BOJ events, so the burst detector is NOT used to place E.
    It IS run on every event as a price-blind VALIDATION of the calendar times
    (s4.detect_boj_release + s4.price_peak_minute_ms), and its agreement rate is
    reported.  It never moves E.

THE THREE BARS
    (1) MECHANISM.  gross = s4's `gross_mid`, the zero-cost mid-to-mid move
        signed WITH the impulse direction, E+60s -> E+300s.  Both primary cells
        must carry the same sign as the 2015-2026 reference (positive) AND
        event-clustered t >= 2.0.  One trade per event, so events ARE the
        clusters and the plain t over events IS the event-clustered t.  Plateau:
        a majority (>= 3) of the other four cells must share the sign.
    (2) ERA COST.  s4's `net_base`: the trade is filled by CROSSING THE BOOK at
        the judgment set's own Dukascopy bid/ask at E+60s and E+300s -- i.e. the
        spread actually quoted in 2005-2014, measured, never assumed -- minus
        S4's 0.4 bps round-trip fee.  Both primary cells must be > 0 with
        t >= 1.5.  `gross_book` (book crossing, no fee) is printed beside it so
        the fee's share is visible; the BAR uses net_base, the stricter number.
    (3) TODAY'S COST.  net_today = gross_mid - C with C from KNOWLEDGE_FX sec.2.5
        (E+60->E+300 measured round trip, 0.89 .. 1.46 bps).  Both primary cells
        must be > 0 at the CONSERVATIVE end C = 1.46.  C = 0.89 is printed too.

READING (PREREG sec.5) IS ALSO FIXED IN CODE.  In particular, if bar (1) passes
    and bar (2) fails, the verdict is NOT a downgraded pass: the script prints
    the explanation-duty note and returns FAIL.

seed 20260828.  Run twice, same output.  No network.  Nothing is written.

Run:  PYTHONPATH=src python scripts/research_fx_s4_judgment.py
"""

from __future__ import annotations

import csv
import hashlib
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import research_fx_event_ticks as s4                                  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_JUDGE = os.path.join(ROOT, "backtest_data", "fx_event_ticks_2005_2014")
LIB_REF = s4.LIB                       # 2015-2026, the S4 library, read-only

SEED = 20260828
BOOT_N = s4.BOOT_N

# KNOWLEDGE_FX sec.2.5 -- measured E+5s->E+300s round-trip cost map, today
COST_TODAY_LO, COST_TODAY_HI = 0.89, 1.46

# the six cells, in S4's own print order
CELLS = [(split, m) for split in ("exploration", "judgment") for m in s4.THRESHOLDS]

# reproduction gate: the six F2R net_base means printed by the committed S4 run
S4_F2R_NET_BASE = {("exploration", 5.0): 0.767, ("exploration", 10.0): 1.876,
                   ("exploration", 20.0): 1.688, ("judgment", 5.0): 2.196,
                   ("judgment", 10.0): 1.463, ("judgment", 20.0): 1.988}

EPOCH = s4.EPOCH


def hr(ch="-", n=104):
    return ch * n


def explore_n(total: int) -> int:
    """S4's split arithmetic: first 60% by count.  477 -> 286."""
    return int(total * 0.6)


def boot_ci(x, seed=SEED):
    x = np.asarray(x, float)
    if x.size < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, x.size, size=(BOOT_N, x.size))].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def stat(x):
    x = np.asarray(x, float)
    lo, hi = boot_ci(x)
    return dict(n=int(x.size), mean=float(x.mean()) if x.size else np.nan,
                t=s4.tstat(x), lo=lo, hi=hi,
                win=float((x > 0).mean()) if x.size else np.nan)


# --------------------------------------------------------------------------- #
def load_library(lib: str, label: str):
    """Build S4 event objects for every calendar row of a library.  Returns
    (events_in_calendar_order, calendar_dataframe, split_index)."""
    cal = pd.read_csv(os.path.join(lib, "calendar.csv"))
    cal["nominal_ms"] = ((pd.to_datetime(cal["time_utc"], utc=True) - EPOCH)
                         / pd.Timedelta("1ms")).astype(np.int64)
    cal = cal.sort_values(["nominal_ms", "type"], kind="stable").reset_index(drop=True)
    split = explore_n(len(cal))
    events, missing = [], 0
    for _, r in cal.iterrows():
        p = os.path.join(lib, f"{r.type}_{r.date.replace('-', '')}.csv.gz")
        if not os.path.exists(p):
            missing += 1
            continue
        events.append(s4.build_event(r.type, r.date, int(r.nominal_ms), p))
    print(f"  {label:<12} calendar {len(cal):>4}  files missing {missing:>3}  "
          f"built {len(events):>4}  valid {sum(e.valid for e in events):>4}  "
          f"split at event #{split} ({cal.date.iloc[min(split, len(cal)-1)]})")
    drops = pd.Series([re.sub(r"\(score=[\d.]+\)", "(ratio<4)", e.drop)
                       for e in events if not e.valid]).value_counts()
    for k, v in drops.items():
        print(f"      drop {v:>4}  {k}")
    if any(not e.valid for e in events):
        yr = pd.Series([e.year for e in events if not e.valid]).value_counts().sort_index()
        print("      drops by year: " + ", ".join(f"{k}:{v}" for k, v in yr.items()))
    return events, cal, split


def cell_frames(events, split_n: int):
    """The six S4 F2R cells for one library.  Split by position in the calendar
    order (S4's rule: fixed by count BEFORE validity filtering)."""
    order = {(e.typ, e.date): i for i, e in enumerate(events)}
    ex = [e for e in events if order[(e.typ, e.date)] < split_n]
    ju = [e for e in events if order[(e.typ, e.date)] >= split_n]
    out = {}
    for split, m in CELLS:
        evs = ex if split == "exploration" else ju
        out[(split, m)] = s4.run_config(evs, "F2R", m, s4.F2_EXIT_S)
    return out, ex, ju


def cell_table(frames, title: str):
    print(f"\n  {title}")
    print(f"  {'cell':<22}{'n':>6}{'gross(zero-cost)':>18}{'t':>7}"
          f"{'book-cross':>12}{'net ERA':>10}{'t':>7}{'  95% CI (era net)':<22}"
          f"{'net@0.89':>10}{'net@1.46':>10}{'win':>7}")
    rows = {}
    for split, m in CELLS:
        d = frames[(split, m)]
        if d.empty:
            print(f"  {split+' m='+str(int(m)):<22}{0:>6}   (no trades)")
            rows[(split, m)] = None
            continue
        g = stat(d.gross_mid.to_numpy())
        b = float(d.gross_book.mean())
        nb = stat(d.net_base.to_numpy())
        rows[(split, m)] = dict(g=g, nb=nb, book=b,
                                lo_today=g["mean"] - COST_TODAY_LO,
                                hi_today=g["mean"] - COST_TODAY_HI)
        print(f"  {split+' m='+str(int(m)):<22}{g['n']:>6}{g['mean']:>+18.3f}{g['t']:>+7.2f}"
              f"{b:>+12.3f}{nb['mean']:>+10.3f}{nb['t']:>+7.2f}"
              f"  [{nb['lo']:+7.3f},{nb['hi']:+7.3f}]"
              f"{g['mean']-COST_TODAY_LO:>+10.3f}{g['mean']-COST_TODAY_HI:>+10.3f}"
              f"{100*nb['win']:>6.1f}%")
    return rows


# --------------------------------------------------------------------------- #
def main() -> int:
    print(hr("="))
    print("FX-S4 JUDGMENT -- IMPULSE-DIRECTION RESUMPTION (E+60s -> E+300s)")
    print("2005-2014 BACKWARD-FRESH US MACRO EVENTS -- RUN ONCE, REPORTED AS-IS")
    print(hr("="))
    assert explore_n(477) == s4.SPLIT_EXPLORE_N, "split arithmetic does not reproduce S4"
    print(f"  split arithmetic self-check: explore_n(477) = {explore_n(477)} "
          f"== S4's SPLIT_EXPLORE_N {s4.SPLIT_EXPLORE_N}  OK")
    print(f"  cells (imported from S4, family F2R = enter E+{s4.F2_ENTRY_S}s WITH the impulse, "
          f"exit E+{s4.F2_EXIT_S}s):")
    for c in CELLS:
        print(f"      {c[0]:<12} m={c[1]:.0f} bps")
    print(f"  fee per side {s4.FEE_BPS_PER_SIDE} bps ; impulse window E..E+{s4.IMPULSE_S}s ; "
          f"thresholds {s4.THRESHOLDS} -- all from the S4 module")

    # ------------------------------------------------------------------ calendar provenance
    print("\n" + hr())
    print("SANITY -- CALENDAR PROVENANCE (both libraries)")
    print(hr())
    for lib, label in ((LIB_JUDGE, "2005-2014"), (LIB_REF, "2015-2026")):
        with open(os.path.join(lib, "calendar.csv"), encoding="utf-8") as f:
            rr = list(csv.DictReader(f))
        src = pd.Series([r["source"] for r in rr]).value_counts().to_dict()
        conf = pd.Series([r["confidence"] for r in rr]).value_counts().to_dict()
        typ = pd.Series([r["type"] for r in rr]).value_counts().to_dict()
        prim = sum(1 for r in rr if r["source"] == "verified_web")
        print(f"  {label}: n={len(rr)}  " + ", ".join(f"{k}={v}" for k, v in sorted(typ.items())))
        print(f"      source {src}   confidence {conf}")
        print(f"      PRIMARY-SOURCE RATE = {100.0*prim/len(rr):.1f}%  "
              f"(rule-generated dates: {len(rr)-prim})")
    print("  2005-2014 dates: bls.gov/schedule/{YYYY}/home.htm (NFP, CPI) and")
    print("  federalreserve.gov/monetarypolicy/fomchistorical{YYYY}.htm (FOMC, scheduled")
    print("  meetings only -- conference-call statements excluded).  Zero rule-generated dates.")
    print("  FOMC clock time: scraped exactly where the Fed publishes it (fomcpresconf pages,")
    print("  2011-04 onward); otherwise the era rule 14:15 ET (pre 2013-03-20) / 14:00 ET,")
    print("  each documented by a Fed press release cited in the calendar's note column.")

    # ------------------------------------------------------------------ build
    print("\n" + hr())
    print("BUILDING EVENT FEATURES (S4's build_event, unchanged)")
    print(hr())
    ju_events, ju_cal, ju_split = load_library(LIB_JUDGE, "2005-2014")
    ref_events, ref_cal, ref_split = load_library(LIB_REF, "2015-2026")

    ju_frames, ju_ex, ju_ju = cell_frames(ju_events, ju_split)
    ref_frames, ref_ex, ref_ju = cell_frames(ref_events, ref_split)

    # ------------------------------------------------------------------ reproduction gate
    print("\n" + hr())
    print("REPRODUCTION GATE (protocol sec.6) -- do the six 2015-2026 cells reproduce the")
    print("numbers the committed S4 run printed?")
    print(hr())
    ok_all = True
    for c in CELLS:
        got = float(ref_frames[c].net_base.mean())
        want = S4_F2R_NET_BASE[c]
        ok = abs(got - want) < 0.002
        ok_all &= ok
        print(f"  {c[0]:<12} m={c[1]:>4.0f}   S4 printed {want:>+7.3f}   here {got:>+7.3f}   "
              f"{'MATCH' if ok else 'MISMATCH'}")
    print(f"  gate: {'PASS' if ok_all else 'FAIL -- the transplant is not the S4 object'}")
    if not ok_all:
        print("  ABORTING: refusing to judge with a cell definition that is not S4's.")
        return 2

    # ------------------------------------------------------------------ pre-designation
    print("\n" + hr())
    print("PRE-DESIGNATION OF THE TWO PRIMARY CELLS (mechanical, from the 2015-2026 reference,")
    print("using S4's own selection key: net_base mean desc, tie-break t desc)")
    print(hr())
    rank = []
    for c in CELLS:
        d = ref_frames[c]
        rank.append(dict(cell=c, n=len(d), mean=float(d.net_base.mean()),
                         t=s4.tstat(d.net_base.to_numpy()),
                         gross=float(d.gross_mid.mean())))
    rank = sorted(rank, key=lambda r: (-r["mean"], -r["t"]))
    print(f"  {'rank':<6}{'cell':<24}{'n':>6}{'net_base':>11}{'t':>8}{'gross':>10}")
    for i, r in enumerate(rank, 1):
        star = "  <== PRIMARY" if i <= 2 else ""
        print(f"  {i:<6}{r['cell'][0]+' m='+str(int(r['cell'][1])):<24}{r['n']:>6}"
              f"{r['mean']:>+11.3f}{r['t']:>+8.2f}{r['gross']:>+10.3f}{star}")
    PRIMARY = [rank[0]["cell"], rank[1]["cell"]]
    OTHERS = [c for c in CELLS if c not in PRIMARY]
    REF_SIGN = {c: (1 if float(ref_frames[c].gross_mid.mean()) > 0 else -1) for c in CELLS}
    print(f"  PRIMARY (pre-designated): {PRIMARY[0]} and {PRIMARY[1]}")
    print(f"  reference gross signs    : " + ", ".join(
        f"{c[0][:2]}m{int(c[1])}={'+' if REF_SIGN[c] > 0 else '-'}" for c in CELLS))
    print("  MULTIPLICITY: 6 cells exist; 2 are named before the judgment numbers are read;")
    print("  the other 4 serve only as the plateau condition.  No cell is added later.")

    # ------------------------------------------------------------------ THE TABLE
    print("\n" + hr("="))
    print("THE SIX CELLS x {2005-2014 JUDGMENT, 2015-2026 REFERENCE}")
    print("gross = zero-cost mid-to-mid signed with the impulse; book-cross = filled by")
    print("crossing the library's own bid/ask; net ERA = book-cross - 0.4 bps fee;")
    print(f"net@C = gross - C, C from KNOWLEDGE_FX sec.2.5 ({COST_TODAY_LO} / {COST_TODAY_HI} bps)")
    print(hr("="))
    ju_rows = cell_table(ju_frames, "2005-2014  *** JUDGMENT SET (backward-fresh) ***")
    ref_rows = cell_table(ref_frames, "2015-2026  reference (S4's own library)")

    # ------------------------------------------------------------------ bars
    print("\n" + hr("="))
    print("THE THREE PRE-REGISTERED BARS")
    print(hr("="))
    b1_primary, b2_primary, b3_primary = True, True, True
    print("  (1) MECHANISM -- primary cells: gross same sign as 2015-2026 AND event-clustered t >= 2.0")
    for c in PRIMARY:
        r = ju_rows[c]
        if r is None:
            print(f"      {str(c):<26} NO TRADES -> FAIL")
            b1_primary = False
            continue
        same = (1 if r["g"]["mean"] > 0 else -1) == REF_SIGN[c]
        okt = r["g"]["t"] >= 2.0
        b1_primary &= (same and okt)
        print(f"      {str(c):<26} n={r['g']['n']:>4} gross {r['g']['mean']:>+8.3f} "
              f"(ref sign {'+' if REF_SIGN[c] > 0 else '-'}: {'same' if same else 'OPPOSITE'})  "
              f"t {r['g']['t']:>+6.2f}  -> {'PASS' if (same and okt) else 'FAIL'}")
    same_sign_others = sum(1 for c in OTHERS
                           if ju_rows[c] and (1 if ju_rows[c]["g"]["mean"] > 0 else -1) == REF_SIGN[c])
    b1_plateau = same_sign_others >= 3
    print(f"      PLATEAU: {same_sign_others}/4 remaining cells share the reference sign "
          f"-> {'PASS' if b1_plateau else 'FAIL'} (needs a majority, >= 3)")
    BAR1 = b1_primary and b1_plateau
    print(f"      BAR 1 = {'PASS' if BAR1 else 'FAIL'}")

    print("\n  (2) ERA COST -- primary cells: net at the era's OWN measured spread > 0, t >= 1.5")
    for c in PRIMARY:
        r = ju_rows[c]
        if r is None:
            b2_primary = False
            continue
        ok = (r["nb"]["mean"] > 0) and (r["nb"]["t"] >= 1.5)
        b2_primary &= ok
        print(f"      {str(c):<26} book-cross {r['book']:>+8.3f}  net ERA {r['nb']['mean']:>+8.3f} "
              f"t {r['nb']['t']:>+6.2f}  CI [{r['nb']['lo']:+.3f},{r['nb']['hi']:+.3f}]  "
              f"-> {'PASS' if ok else 'FAIL'}")
    BAR2 = b2_primary
    print(f"      BAR 2 = {'PASS' if BAR2 else 'FAIL'}")

    print(f"\n  (3) TODAY'S COST -- primary cells: gross - {COST_TODAY_HI} bps > 0 "
          f"(conservative end of the sec.2.5 map)")
    for c in PRIMARY:
        r = ju_rows[c]
        if r is None:
            b3_primary = False
            continue
        ok = r["hi_today"] > 0
        b3_primary &= ok
        print(f"      {str(c):<26} net@{COST_TODAY_LO} {r['lo_today']:>+8.3f}   "
              f"net@{COST_TODAY_HI} {r['hi_today']:>+8.3f}  -> {'PASS' if ok else 'FAIL'}")
    BAR3 = b3_primary
    print(f"      BAR 3 = {'PASS' if BAR3 else 'FAIL'}")

    # ------------------------------------------------------------------ yearly
    print("\n" + hr("="))
    print("YEAR-BY-YEAR (is the mechanism concentrated in one era?)")
    print(hr("="))
    for lab, frames, cells in (("2005-2014 judgment", ju_frames, CELLS),
                               ("2015-2026 reference", ref_frames, CELLS)):
        pooled = pd.concat([frames[c].assign(cell=f"{c[0][:2]}m{int(c[1])}") for c in cells],
                           ignore_index=True)
        print(f"\n  {lab} -- all six cells pooled (a trade may appear in several cells; this is a")
        print("  DIAGNOSTIC of where the tape moves, not a portfolio)")
        print(f"      {'year':<6}{'n':>6}{'gross':>10}{'t':>8}{'net ERA':>10}{'t':>8}{'win':>8}")
        for y, g in pooled.groupby("year"):
            gs, ns = stat(g.gross_mid.to_numpy()), stat(g.net_base.to_numpy())
            print(f"      {y:<6}{gs['n']:>6}{gs['mean']:>+10.3f}{gs['t']:>+8.2f}"
                  f"{ns['mean']:>+10.3f}{ns['t']:>+8.2f}{100*ns['win']:>7.1f}%")
    print(f"\n  primary cells only, 2005-2014, by year")
    for c in PRIMARY:
        d = ju_frames[c]
        print(f"      cell {c[0]} m={c[1]:.0f}")
        print(f"          {'year':<6}{'n':>6}{'gross':>10}{'t':>8}{'net ERA':>10}")
        for y, g in d.groupby("year"):
            gs, ns = stat(g.gross_mid.to_numpy()), stat(g.net_base.to_numpy())
            print(f"          {y:<6}{gs['n']:>6}{gs['mean']:>+10.3f}{gs['t']:>+8.2f}"
                  f"{ns['mean']:>+10.3f}")
    print(f"\n  by event type, 2005-2014, all six cells pooled")
    pooled = pd.concat([ju_frames[c] for c in CELLS], ignore_index=True)
    print(f"      {'type':<6}{'n':>6}{'gross':>10}{'t':>8}{'net ERA':>10}{'t':>8}")
    for t_, g in pooled.groupby("typ"):
        gs, ns = stat(g.gross_mid.to_numpy()), stat(g.net_base.to_numpy())
        print(f"      {t_:<6}{gs['n']:>6}{gs['mean']:>+10.3f}{gs['t']:>+8.2f}"
              f"{ns['mean']:>+10.3f}{ns['t']:>+8.2f}")

    # ------------------------------------------------------------------ spread era
    print("\n" + hr("="))
    print("SPREAD ACROSS THE ERAS -- what a trade in these seconds actually cost, by year")
    print("(median quoted spread in bps at the instant; Dukascopy interbank USD/JPY)")
    print(hr("="))
    def spread_frame(events):
        return pd.DataFrame([dict(year=e.year, typ=e.typ,
                                  **{f"s{o}": e.snap_spread.get(o, np.nan) for o in s4.F3_OFFSETS_S},
                                  base=e.base_spread, imp=abs(e.impulse_bps))
                             for e in events if e.valid])
    ju_sp, ref_sp = spread_frame(ju_events), spread_frame(ref_events)
    hdr = (f"      {'year':<6}{'n':>5}" + "".join(f"{('E'+(f'{o:+d}' if o else ''))+'s':>11}"
                                                  for o in s4.F3_OFFSETS_S)
           + f"{'RT E+60->300':>14}")
    print(hdr)
    for lab, sp in (("2005-2014", ju_sp), ("2015-2026", ref_sp)):
        print(f"  {lab}")
        for y, g in sp.groupby("year"):
            rt = ((g["s60"] + g["s300"]) / 2 + 2 * s4.FEE_BPS_PER_SIDE).median()
            print(f"      {y:<6}{len(g):>5}"
                  + "".join(f"{g[f's{o}'].median():>11.3f}" for o in s4.F3_OFFSETS_S)
                  + f"{rt:>14.3f}")
    print("\n  RT E+60->300 = half-spread in + half-spread out + 0.4 bps fee, i.e. the actual")
    print("  round-trip cost of THIS trade in THAT year.  Compare with the GMO retail floor")
    print(f"  {s4.GMO_FLOOR_ROUNDTRIP_BPS} bps and the sec.2.5 map {COST_TODAY_LO}-{COST_TODAY_HI} bps.")
    print("\n  spread by era, pooled (median / p90 bps)")
    for lab, sp in (("2005-2014", ju_sp), ("2015-2026", ref_sp)):
        rt = ((sp["s60"] + sp["s300"]) / 2 + 2 * s4.FEE_BPS_PER_SIDE)
        print(f"      {lab}: E-60s {sp['s-60'].median():.3f}/{sp['s-60'].quantile(.9):.3f}   "
              f"E+1s {sp['s1'].median():.3f}/{sp['s1'].quantile(.9):.3f}   "
              f"E+60s {sp['s60'].median():.3f}/{sp['s60'].quantile(.9):.3f}   "
              f"E+300s {sp['s300'].median():.3f}/{sp['s300'].quantile(.9):.3f}   "
              f"RT {rt.median():.3f}/{rt.quantile(.9):.3f}")

    # ------------------------------------------------------------------ impulse era
    print("\n" + hr("="))
    print("IMPULSE SIZE ACROSS THE ERAS  |mid(E+5s)-mid(E)| in bps")
    print("(KNOWLEDGE_FX sec.2.5 records the peak at 2023-24; does 2005-2014 look like it?)")
    print(hr("="))
    print(f"      {'year':<6}{'n':>5}{'p50':>9}{'p75':>9}{'p90':>9}{'max':>10}"
          f"{'>=5bps':>9}{'>=10bps':>9}{'>=20bps':>9}")
    for lab, sp in (("2005-2014", ju_sp), ("2015-2026", ref_sp)):
        print(f"  {lab}")
        for y, g in sp.groupby("year"):
            print(f"      {y:<6}{len(g):>5}{g['imp'].median():>9.2f}{g['imp'].quantile(.75):>9.2f}"
                  f"{g['imp'].quantile(.9):>9.2f}{g['imp'].max():>10.2f}"
                  f"{100*(g['imp']>=5).mean():>8.0f}%{100*(g['imp']>=10).mean():>8.0f}%"
                  f"{100*(g['imp']>=20).mean():>8.0f}%")
    print(f"\n      {'type/era':<16}{'n':>5}{'p50':>9}{'p90':>9}")
    for lab, sp in (("2005-2014", ju_sp), ("2015-2026", ref_sp)):
        for t_, g in sp.groupby("typ"):
            print(f"      {lab+' '+t_:<16}{len(g):>5}{g['imp'].median():>9.2f}"
                  f"{g['imp'].quantile(.9):>9.2f}")

    # ------------------------------------------------------------------ E validity
    print("\n" + hr("="))
    print("SANITY -- IS E RIGHT?  price-blind tick-ARRIVAL burst detector vs the calendar clock")
    print("(S4's detector, run here ONLY as validation; it never moves E)")
    print(hr("="))
    print(f"  {'era':<12}{'type':<6}{'n':>5}{'burst found':>13}{'|dE| p50 s':>12}"
          f"{'<=30s':>8}{'<=60s':>8}{'<=300s':>9}")
    for lab, lib, evs in (("2005-2014", LIB_JUDGE, ju_events), ("2015-2026", LIB_REF, ref_events)):
        rows = []
        for e in evs:
            if not e.valid or e.typ == "BOJ":
                continue
            tp = s4.load_tape(os.path.join(lib, f"{e.typ}_{e.date.replace('-', '')}.csv.gz"))
            br = s4.detect_boj_release(tp)
            rows.append(dict(typ=e.typ, year=e.year, found=bool(br.ok),
                             d=abs(br.e_ms - e.e_ms) / 1000.0 if br.ok else np.nan,
                             score=br.score))
        R = pd.DataFrame(rows)
        for t_, g in list(R.groupby("typ")) + [("ALL", R)]:
            f = g[g.found]
            print(f"  {lab:<12}{t_:<6}{len(g):>5}{100*g.found.mean():>12.0f}%"
                  f"{(f.d.median() if len(f) else np.nan):>12.0f}"
                  f"{(100*(f.d<=30).mean() if len(f) else np.nan):>7.0f}%"
                  f"{(100*(f.d<=60).mean() if len(f) else np.nan):>7.0f}%"
                  f"{(100*(f.d<=300).mean() if len(f) else np.nan):>8.0f}%")
        if lab == "2005-2014":
            print("      by year (2005-2014): burst-found rate / median |dE| s")
            for y, g in R.groupby("year"):
                f = g[g.found]
                print(f"          {y}  {100*g.found.mean():>5.0f}%   "
                      f"{(f.d.median() if len(f) else float('nan')):>6.0f}   n={len(g)}")
    print("  NOTE. The detector needs a tick-arrival burst >= 4x the trailing rate.  On a thin")
    print("  2005-2008 tape a real release can fail that test without E being wrong; a low")
    print("  found-rate is a statement about tick DENSITY, not about the calendar.  What would")
    print("  indict the calendar is a burst found FAR from E, so |dE| is the column to read.")

    # ------------------------------------------------------------------ look-ahead
    print("\n" + hr("="))
    print("SANITY -- LOOK-AHEAD IS ZERO BY CONSTRUCTION")
    print(hr("="))
    vv = [e for e in ju_events if e.valid]
    gaps = np.array([e.q[s4.F2_ENTRY_S][3] - e.sig_ts_ms for e in vv], float)
    fills = np.array([e.q[s4.F2_ENTRY_S][4] for e in vv], float)
    xg = np.array([e.q[s4.F2_EXIT_S][3] - e.q[s4.F2_ENTRY_S][3] for e in vv], float)
    print(f"  signal window is [E, E+{s4.IMPULSE_S}s]; the entry decision is at E+{s4.F2_ENTRY_S}s,")
    print(f"  i.e. a hard {s4.F2_ENTRY_S - s4.IMPULSE_S}-second gap between the last tick the signal")
    print(f"  may read and the earliest tick the entry may fill on.")
    print(f"  entry_tick_ts - signal_tick_ts (ms): min {gaps.min():.0f}, median {np.median(gaps):.0f}, "
          f"negatives {int((gaps <= 0).sum())}")
    print(f"  entry fill gap past the decision instant (ms): median {np.median(fills):.0f}, "
          f"p90 {np.percentile(fills, 90):.0f}, max {fills.max():.0f} (cap {s4.MAX_FILL_GAP_MS})")
    print(f"  exit_tick_ts - entry_tick_ts (ms): min {xg.min():.0f} (must exceed 0)")
    print("  no feature used by a cell reads a tick after its own decision instant.")

    # ------------------------------------------------------------------ worked example
    print("\n" + hr())
    print("ONE TRADE WORKED OUT FROM RAW 2005-2014 QUOTES (auditable by hand)")
    print(hr())
    demo = max(vv, key=lambda e: abs(e.impulse_bps))
    eb, ea, em, ets, eg = demo.q[s4.F2_ENTRY_S]
    xb, xa, xm, xts, xgp = demo.q[s4.F2_EXIT_S]
    d = 1 if demo.impulse_bps > 0 else -1
    nb_, ng_, gb_, gm_ = s4.trade_bps(demo, d, s4.F2_ENTRY_S, s4.F2_EXIT_S)
    print(f"  {demo.typ} {demo.date}  E = {s4.utc(demo.e_ms)}   mid(E) = {demo.mid_e:.5f}")
    print(f"    impulse {demo.impulse_bps:+.2f} bps -> {'LONG' if d > 0 else 'SHORT'} at E+60s")
    print(f"    entry fill @ {s4.utc(ets)} (+{eg} ms): bid {eb:.5f} / ask {ea:.5f}")
    print(f"    exit  fill @ {s4.utc(xts)} (+{xgp} ms): bid {xb:.5f} / ask {xa:.5f}")
    print(f"    book-cross {gb_:+.3f} bps ; minus {2*s4.FEE_BPS_PER_SIDE} bps fee -> "
          f"net ERA {nb_:+.3f} bps ; zero-cost mid-to-mid {gm_:+.3f} bps")

    # ------------------------------------------------------------------ determinism
    print("\n" + hr())
    print("SANITY -- DETERMINISM")
    print(hr())
    def digest(frames):
        h = hashlib.sha256()
        for c in CELLS:
            d = frames[c][["typ", "date", "dirn", "impulse", "net_base", "gross_mid",
                           "gross_book"]].round(9)
            h.update(pd.util.hash_pandas_object(d, index=False).to_numpy().tobytes())
        return h.hexdigest()[:16]
    h1 = digest(ju_frames)
    ju_frames2, _, _ = cell_frames(ju_events, ju_split)
    h2 = digest(ju_frames2)
    c0 = PRIMARY[0]
    b1 = boot_ci(ju_frames[c0].net_base.to_numpy())
    b2 = boot_ci(ju_frames[c0].net_base.to_numpy())
    print(f"  six-cell trade-table hash: run A {h1} / run B {h2}   identical={h1 == h2}")
    print(f"  bootstrap CI reproduced exactly (seed {SEED}): {b1 == b2}  {b1}")
    print("  no network access, no RNG outside the seeded bootstrap, no files written.")

    # ------------------------------------------------------------------ verdict
    print("\n" + hr("="))
    print("VERDICT (PREREG sec.5 -- the reading was fixed before the run)")
    print(hr("="))
    print(f"  BAR 1 mechanism reproduces (primary t>=2.0, same sign, plateau): "
          f"{'PASS' if BAR1 else 'FAIL'}")
    print(f"  BAR 2 positive at the ERA's own measured cost (t>=1.5)        : "
          f"{'PASS' if BAR2 else 'FAIL'}")
    print(f"  BAR 3 positive at today's cost map (conservative {COST_TODAY_HI} bps) : "
          f"{'PASS' if BAR3 else 'FAIL'}")
    if BAR1 and BAR2 and BAR3:
        verdict = "PASS -- proceed to stage 2 (forward paper tracking, owner approval required)"
    elif not BAR1:
        verdict = ("REJECT -- the mechanism does not reproduce on backward-fresh events. "
                   "S4's +0.8..+3.0 bps is confirmed as a dig-out.")
    else:
        verdict = ("REJECT -- mechanism reproduces but fails a cost bar. PREREG sec.5 forbids "
                   "a downgraded pass here.")
    print(f"\n  >>> {verdict} <<<")
    if BAR1 and not BAR2:
        print("\n  PREREG sec.5, row 2 -- THE EXPLANATION DUTY (written because it is owed, not")
        print("  because it rescues anything):")
        print("    If the move is real but was untradable at the spreads actually quoted in")
        print("    2005-2014, then either (a) the same edge existed then and was eaten by the")
        print("    era's cost, in which case nothing selected it away and its survival to today")
        print("    is unexplained -- an edge no one could take is an edge no one competed away,")
        print("    so it should be LARGER today, not smaller; or (b) it is not the same object")
        print("    at all, and the 2015-2026 version is a property of the modern microstructure")
        print("    that the 2005-2014 tape cannot speak to.  Neither branch licenses adoption on")
        print("    today's cost map alone, and the pre-registration says so.  NOT PASSED.")
    print(hr("="))
    print(f"FINAL: {'PASS' if (BAR1 and BAR2 and BAR3) else 'REJECT'}   "
          f"primary cells {PRIMARY[0]} / {PRIMARY[1]}   "
          f"judgment events {len([e for e in ju_events if e.valid])} valid of {len(ju_cal)}")
    print(hr("="))
    return 0


if __name__ == "__main__":
    sys.exit(main())
