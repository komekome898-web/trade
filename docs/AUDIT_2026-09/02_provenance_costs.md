# Provenance audit — bitFlyer FX_BTC_JPY cost constants (AR-1 follow-up)

Scope: trace every taker/maker cost constant in KNOWLEDGE.md §1/§2 to its first appearance,
check it against the fee facts actually recorded in the repo, and list every downstream
verdict that cites a cost floor. Builds on `01_assumption_register.md` (AR-1, AR-2) and
audits `C_board_imbalance_taker.md` / `E_cost_floor_maker.md`.

## 1. Constant-by-constant provenance

| Constant | First appearance | Exact text | How computed |
|---|---|---|---|
| スリッページ 2bps/片道 (FX) | `docs/RESEARCH_REPORT_2026-08-20d.md:6` (commit `c9a17a8`, 2026-08-20, 第4報) | 「コスト: FX実測(手数料0%・スプレッド0.0235%・**スリッページ0.02%**・スワップ0.04%/日)」 | Listed as "実測" (measured) alongside three genuinely-sourced figures, but **no script, dataset, or method is cited for the slippage figure itself** in this report or any earlier one — it is the earliest occurrence and reads as an assumed round number bundled with real ones, not a derivation. |
| 実測スプレッド 0.0235% (2.35bps) | `docs/RESEARCH_REPORT_2026-08-20c.md:5` (commit `0b42daf`, 2026-08-20, 第3報) | 「FX_BTC_JPY は taker/maker手数料0%・**実測スプレッド0.0235%**」 | Genuinely measured from early ticker data (small sample, first day of collection). Half of it (1.175≈1.18bps) is reused later as "半スプレッド". |
| taker 片道 3.2bps / 往復 6.35bps | `docs/KNOWLEDGE.md:8` (commit `4aef360`, 2026-08-21, first KNOWLEDGE.md) | 「taker 片道 ≒ 3.2bps(半スプレッド1.18 + スリッページ2.0)、往復 6.35bps (e)」 | = half-spread(1.18, derived from c's 2.35bps) + the unverified 2bps slippage from (d), doubled for round trip: 2.35 + 2×2.0 = 6.35. Citation "(e)" (`RESEARCH_REPORT_2026-08-20e.md`, commit `080d110`) merely **uses** "taker往復コスト6.35bps" as an input to an event study — it does not derive it; the half-spread+slippage breakdown was written for the first time in KNOWLEDGE.md itself, not in report (e). |
| バースト 3.96bps(1.96+2.0)/ 平穏 2.93bps(0.93+2.0) | `docs/KNOWLEDGE.md:9`; underlying number used in `docs/RESEARCH_REPORT_2026-08-20i.md:30` (commit `06555c3`, 2026-08-20, 第9報) | 「ネット期待値(burst時コスト3.96bps)」 | Same formula: burst half-spread(1.96, ≈2× the calm 0.93/1.18) + the same 2bps slippage constant. No new slippage measurement — burst-time widening comes from spread, not from re-measured slippage. |
| スプレッド 1.56〜2.22bps(板記録) | `docs/RESEARCH_REPORT_2026-08-20f.md:28` (1.56bps) and `...g.md:26` (2.22bps) (commits `ff57b3d`, `b556786`, both 2026-08-20) | 「実測スプレッド1.56bps(mid比)」/「実測スプレッド2.22bps」 | Genuinely measured (mid-referenced quote spread) from ~4h of board recording each — small, single-session samples, not the full 16-day tape later audited in `E_cost_floor_maker.md` (which finds median ≈1.8–2.1bps, i.e. this range is roughly right but not exact). |
| maker 逆選択 6〜9bps | `docs/KNOWLEDGE.md:11`; components: `...i.md:35` (差9.3bps, commit `06555c3`), `...j.md:36` (差6.2bps, commit `3d18266`) | 「差9.3bps」(scalper, taker-vs-would-be-maker gap) / 「差6.2bps」(anchor-deviation, filled-vs-missed gap) | Both are genuinely measured gaps between filled-limit outcomes and missed-limit-as-if-taker outcomes in two independent studies (a third, report k, is cited in KNOWLEDGE but contributes no distinct adverse-selection bps figure — its finding is about exit fills, not entry adverse selection). Range "6–9" = min/max of the two real numbers. |
| maker 脚間ドリフト −3.2〜−3.6bps | `docs/RESEARCH_REPORT_2026-08-29ag.md:36` (commit `efde2ca`, 第32報) | 「第1脚の約定は逆行の開始点を選んで起き、7〜15秒の脚間にmidが平均**3.2〜3.6bps**動く」 | Genuinely measured from a symmetric spread-MM simulation (own script), no queue-position/displayed-size fill model. `E_cost_floor_maker.md` independently re-derives −1.1 to −1.6bps (about a third to a half) with a similar no-queue fill rule, and finds **net round-trip positive** (+0.39 to +1.02bps) in every regime tested — opposite sign to the −1.02〜−1.42bps claimed net. |
| JFSA venue floor 5.4/5.6/5.8bps (Coincheck/GMO/bitFlyer) | `docs/RESEARCH_REPORT_2026-08-27ac.md:12-16` (commit `88ac3bb`, 第28報) | 「bitFlyer CFD(基準) 0/0 spr 1.84 **床5.84**」 | **Reverse-engineered here**: for every one of the 9 venues in the table, `floor = 2×taker_fee_bps + spread_p50 + 4.00bps` exactly (bitFlyer: 0+1.84+4.00=5.84; Coincheck: 0+1.43+4.00=5.43; GMO lev: 0+1.60+4.00=5.60; bitbank BTC: 20+0.00+4.00=24.0; OKJ: 28+6.81+4.00=38.81≈38.8; bitFlyer spot XRP: 30+17.9+4.00=51.9 — all match to rounding). The **+4.00bps is the same round-trip slippage assumption from (d) (2bps/leg)**, applied uniformly across all 11 venues without re-measuring slippage per venue. So "5.8" for bitFlyer CFD is not an independent venue-survey measurement of bitFlyer's cost — it is `measured spread (1.84bps) + the same unverified 2bps/leg slippage constant carried since 2026-08-20`. |

**Bottom line**: every one of 5.8bps, 7.9bps (sensitivity variant, `PREREG_clock_burst.md:28`: "片道+4bps=合計7.96bps/side" — i.e. 3.96 + 4 more bps of assumed extra slippage under stress), 3.96bps/side, 3.2bps/side and the JFSA map's "5.4–5.8bps" all trace back to **one un-derived assumption — 2bps of taker slippage per leg**, first written in `docs/RESEARCH_REPORT_2026-08-20d.md` on 2026-08-20 with no measurement shown, then compounded with genuinely-measured spread figures across 8 days of subsequent reports and consolidated into KNOWLEDGE.md's "taker 片道 3.2bps" line.

## 2. Fee facts actually recorded in the repo

- `config/products.yaml:19`: `FX_BTC_JPY: {..., taker_fee_pct: 0.0, ..., swap_daily_pct: 0.06}` — **0% trading fee is the value actually consumed** by the order path (`src/bot/products.py:ProductSpec`, used at `src/bot/main.py:231`); confirmed in `E_cost_floor_maker.md`.
- `config/config.yaml`: `costs.taker_fee_pct: 0.15` is a **generic/spot-tier default**, the class default in `src/bot/execution/paper.py` / `src/bot/backtest/engine.py`, and is **not** applied to FX_BTC_JPY — using it for this product is a mismatch (flagged independently by audits C and E).
- `docs/NOTE_CRYPTO_CFD_2026-08-20.md` (owner-triggered fact check, 2026-08-20): confirms via **official bitFlyer API docs** — not a live account fee query — that Lightning FX was discontinued 2024-03-28, `FX_BTC_JPY` continues as the Crypto CFD product code, and **"手数料0%・レバレッジ最大2倍は変更なし"**. It also records the real cost item the constants are *not* about: **funding rate (FR)**, settled 3×/day (UTC 05/13/21), cap ±0.375%/settlement, measured average |rate| ≈0.021%/settlement ≈0.062%/day — a **holding/carry** cost, unrelated to a single round-trip trade held minutes-to-hours. `swap_daily_pct: 0.06` in products.yaml encodes this.
- `scripts/check_api.py` is read-only and never queries a fee/commission endpoint — it checks connectivity, permissions (rejects withdrawal-capable keys), balance, and open orders. **The project has never queried the live account's actual fee tier via the API**; the 0% figure rests entirely on the official-docs cross-check in NOTE_CRYPTO_CFD, not on an API-verified account fee.
- No repo file records a "taker fee 0.15%" specifically for FX_BTC_JPY at any point in git history (`git log -S`) — the 0.15% figure only ever appears attached to spot pairs (`BTC_JPY`, `XRP_JPY`, etc.) and the generic config default.

**Conclusion on Q2**: the constants do **not** fold in the daily leverage/holding charge (funding rate is tracked and modeled separately as `swap_daily_pct`, and is immaterial for sub-day holds). They fold in an **unverified fixed slippage assumption (2bps/leg)**, not a fee misread.

## 3. Which is right for a taker round trip held minutes to hours

For a trade that pays the exchange's taker fee and crosses the spread once each way, holding
minutes to hours (funding rate irrelevant at that horizon): **fee(0%) + measured spread ≈2bps
is the correct floor**, not 5.8–7.9bps. `E_cost_floor_maker.md` measures spread at 1.78–2.07bps
(quote/time/trade-count weighted) to 2.07bps (trade-vs-mid effective) across the full 16-day tape
(1.59M quote rows); `C_board_imbalance_taker.md` independently measures 1.77–1.91bps over the
same window. Neither reproduces 5.8–7.9bps under any weighting; the 0.15% generic fee (wrong
product) overshoots to ~32bps. **5.8–7.9bps sits in neither the correct-fee nor the wrong-fee
regime** — it is explained precisely by spread + an un-remeasured 2bps/leg slippage carried
since day one, not by a fee regime change, and not by folding in the funding rate.

Whether real intra-trade slippage (market impact of an actual taker fill, as opposed to quoted
spread) is near 0bps or near 2bps/leg is genuinely unresolved by this audit — no report shows a
fill-vs-quote slippage measurement for FX_BTC_JPY takers. That is the one open question a true
floor still depends on; everything else in the 5.8–7.9bps chain is arithmetic on that one
unverified number.

## 4. Blast radius — claims citing a cost floor / コスト負け verdict

| Claim (source) | Cost value used | Flips if true floor ≈2bps? |
|---|---|---|
| コストの壁(single-symbol technical, BT/b) | 往復コスト(spot ≈0.55%, FX ≈0.06%) | No — spot floor unaffected; FX rejects were already deep negative |
| S9 嵐時計ブラケット(v) | 往復7.92bps | **Yes** — best cell gross was reported near the line; needs re-check vs ≈2bps |
| C2 時計窓タッチ継続(v) | 往復taker 7.92bps ("届かない") | **Yes** — explicitly "コスト線の下"; the gap to a 2bps floor is large |
| バースト面 78セル(L6/y) | 往復7.92bps threshold | **Yes** — the 78-cell "window-overlap illusion" cross-over was judged against 7.92bps |
| S12 時計バースト30分(PREREG_clock_burst, y) | 片道3.96bps (+7.96 sensitivity) | **Yes** — design net and judgment bar both use 3.96bps/side; already independently re-audited in `B_s12_clock_burst.md` (net turns negative on fresh data even before this correction) |
| リーダー追随族(L7/y) | コスト床0.079% (7.9bps) RT | **Yes** — "n≥400セルの taker 線超え0.0%" is measured against 7.9bps |
| 板不均衡taker(L14/ap, audit C) | 往復5.8bps | **Yes, in principle** — but audit C already recomputed at ≈1.9bps and rejection still holds (best cell gross 1.25bps < 1.9bps) |
| JFSA効率ギャップ地図(L15/ac) | bitFlyer 5.84/GMO 5.60/Coincheck 5.43bps | **Yes** — ranking and "拮抗" claim both rest on the +4bps constant; true floors ≈1.8–2.6bps, ranking order likely preserved but magnitudes wrong |
| bot狩り(ao) | 「現行JPY床5.4〜5.8の1/5以下が必要」 | **Yes** — the required-edge bar (0.5–1bps) was set relative to 5.4–5.8; against ≈2bps floor the bar would be ≈0.4–0.5bps, conclusion likely unchanged (still very tight) but the stated ratio is wrong |
| SURVEY_JP_EQUITIES §1 (comparison table) | BTC CFD 5.8bps used as cross-market benchmark | **Yes** — "TOPIX100級2.8bps is about half of BTC CFD" becomes "TOPIX100級2.8bps is *higher* than BTC CFD ≈2bps"; the equities-favorable framing partly inverts |
| S12 PREREG judgment bar (`docs/PREREG_clock_burst.md:29`) | 3.96bps/side primary; 7.96bps/side sensitivity | **Yes** — both the primary and stress bar are built on the unverified constant |
| 深掘り台帳(D) 現物系棄却 "コスト床0.55%が全天井の上" | spot RT 0.55% (taker 0.15%×2+spread) | No — spot fee is separately confirmed at 0.15% in products.yaml; unaffected |

Rows not flipped: any verdict resting on spot-market costs (0.15% fee is real and unrelated to
this issue) or on effects already rejected at magnitudes far below even a 2bps floor (most of
KNOWLEDGE §3's index).

## 5. Maker-side constants — separate provenance, separate audit status

- **逆選択 6〜9bps** (reports i, j — 2026-08-20): genuinely measured fill-vs-miss gaps, **not**
  derived from the disputed fee/slippage constant chain — this figure is not implicated by the
  taker-fee error. No audit finding disputes it directly.
- **脚間ドリフト −3.2〜−3.6bps** (report ag, 2026-08-27/29): `E_cost_floor_maker.md` reproduces
  the *sign* but only a third to a half of the *magnitude* (−1.1 to −1.6bps), and — more
  importantly — finds **net round-trip positive** in every regime tested under a no-queue fill
  model, opposite sign to the claimed net (−1.02〜−1.42bps). This is tracked as AR-2, unresolved
  pending a queue-position/displayed-size fill model (neither audit built one). Independent of
  AR-1's fee/slippage question — a queue-aware refill of the fill rule, not a fee correction,
  is what would settle it.
