# Packet L — blind audit: symmetric spread-MM family (L19 / R26 / PR12)

Own implementation: `/tmp/claude-0/.../scratchpad/audit_L.py` (+ `analyze_L.py`, `robustness_L.py`).
Files read: `docs/AUDIT_2026-09/PROTOCOL.md`; `00_packets.md` lines matched to `L19|R26|PR12` only;
`paper_logs/tape/{ticker,executions}_20260820..20260904.csv.gz` (16 days each); `config/products.yaml`;
`backtest_data/board_round_20260904/board_round_series_5s.csv.gz` + `board_round_coverage.json` (depth
sanity check only); `ls` of `backtest_data/venue_survey_20260827/` (not opened further — not needed).
No `docs/*` other than the above two files were opened. No scripts/research_*, judge_*, build_*, KNOWLEDGE*, git log opened.

## Declared readings (ambiguities)
- **K**: "ticks inside the spread" — quotes placed AT `best_bid + K·tick` and `best_ask − K·tick`
  (tick = 1 JPY, confirmed: all `best_bid` values integral, min positive diff = 1.0). This creates a
  fresh top-of-book price with **zero displayed size ahead** (general case of the stated queue rule
  with ahead-size = 0). Round skipped if `spread ≤ 2·K·tick`.
- **Queue/fill**: a resting quote fills on the first execution print whose aggressor side and price
  cross it (`SELL` print `≤ buy_p`, `BUY` print `≥ sell_p`). Requoted (peg) every ticker tick while
  the level moves. Robustness variant (below) instead requires **cumulative** crossing volume ≥ 0.01
  BTC before filling, to test sensitivity to the zero-queue assumption (no L2 book beyond top-of-book
  is available in the tape to verify hidden size at the improved tick).
- **Cap**: timer starts at **position open** (first leg fill); if the second leg hasn't closed as
  maker by `cap` seconds, force a taker exit at the then-current opposite touch. A quote that gets
  *no* first fill within `cap` seconds is cancelled (counted in fill-rate denominator).
- **Reference**: single quote-time mid `M0` (mid at round start) used for both `capture0_bps` (nominal,
  fixed) and to express `net_bps`; **drift** is measured directly as the signed mid move between the
  two legs' own fill times (`mid_exit − mid_entry`, sign flipped for shorts). `adverse_bps = net_bps −
  capture0_bps − drift_bps` (residual). `net_jpy` = raw realized limit/taker price P&L (no synthetic mid used for the trade itself).
- **Exclusions**: crossed-book ticker rows (0.10% of rows) dropped; 19:00–19:15 UTC dropped from both
  tick and exec streams. Fee = 0% (`config/products.yaml: FX_BTC_JPY.taker_fee_pct: 0.0`); swap
  0.06%/day is negligible at ~7s median holds and not applied.
- Gate A = clock 12:30–15:00 UTC. Gate B = Gate A ∪ (2h following any 30-min |mid return| ≥ 0.8%
  "storm" point). All-hours control = no gate. Complement-of-B = `NOT Gate B` (state-conditional control).

## 1. Denominator
16 days (2026-08-20..09-04), all `FX_BTC_JPY` ticker+exec tape, n≈83k–131k ticker rows/day,
17k–101k exec rows/day. Gate-A active 0.4%–15.6% of rows/day (0.0043 on the truncated last day);
Gate-B active 0.04%–85% of rows/day (highly variable — some days had one storm early and its 2h tail
covered most of the session). Round counts (cap=300s): A_K1 13,606; A_K3 13,652; B_K1 41,847; B_K3
41,993, pooled over 16 day-clusters.

## 2–10. Recomputed numbers (day-clustered, cap=300s unless noted)

| cell | n_rounds | net_bps (mean) | 95% CI (day-clustered) | t | capture0_bps | drift_bps | adverse_bps | fill_rate | maker_close_rate | mean/median hold s |
|---|---|---|---|---|---|---|---|---|---|---|
| A clock K1 | 13,606 | +0.101 | [-0.192, 0.394] | 0.74 | 2.650 | -2.136 | -0.413 | 1.000 | 1.000 | 6.8 / — |
| A clock K3 | 13,652 | +0.104 | [-0.189, 0.396] | 0.76 | 2.649 | -2.132 | -0.413 | 1.000 | 1.000 | 6.8 / — |
| B clock∪storm K1 | 41,847 | +0.110 | [-0.167, 0.388] | 0.85 | 2.646 | -2.132 | -0.404 | 1.000 | 1.000 | 7.2 / 3.6 |
| B clock∪storm K3 | 41,993 | +0.115 | [-0.161, 0.392] | 0.89 | 2.644 | -2.125 | -0.403 | 1.000 | 1.000 | 7.2 / — |
| all-hours K1 (control) | 79,348 | -0.028 | [-0.089, 0.034] | -0.96 | — | — | — | 1.000 | 1.000 | — |
| all-hours K3 (control) | 79,605 | -0.022 | [-0.084, 0.039] | -0.78 | — | — | — | 1.000 | 1.000 | — |
| complement-of-B K1 (state control) | 37,524 | **-0.082** | [-0.148, -0.016] | **-2.63** | — | — | — | — | — | — |
| complement-of-B K3 (state control) | 37,635 | **-0.078** | [-0.145, -0.012] | **-2.50** | — | — | — | — | — | — |
| **Robustness: ≥0.01 BTC cumulative fill (B, K1)** | 30,739 | -0.194 | se 0.109 | -1.78 | 2.614 | -2.497 | -0.437 | — | 1.000 | 9.9 / 4.9 |

**Cap sensitivity** (60/300/900s, all 4 cells): estimates move by <0.02 bps between caps; forced-taker
rate is 0.6–0.7% at cap=60s and 0.00–0.005% at cap=300/900s (i.e. the closing leg essentially always
fills as maker well inside 300s already — the cap barely binds). Cap is not the driver of the result.

**Placebo (day-mean sign-flip, 2000 draws, B K1)**: observed day-mean = 0.110 bps; permutation
p = 0.61 — indistinguishable from a mean-zero process, consistent with the t≈0.85 already found (no
spurious "significance" being masked).

**Regime (hour-of-day, B K1)**: per-hour means range −0.37 to +0.34 bps with no monotonic pattern
tied to the gate windows (12:30–15:00 UTC hours 12–14 sit mid-pack: -0.02, -0.08, +0.08 bps) — no
obvious hidden regime driving the near-zero result.

**Consistency**: K=1 vs K=3 agree closely within each gate (0.101 vs 0.104; 0.110 vs 0.115) — low
sensitivity to the free K parameter, arguing against cherry-picking across the 4-cell grid (all 4
cluster inside a 0.014 bps band). Long-first vs short-first entries (B K1) give +0.065 / +0.141 bps
respectively — same sign, same order of magnitude, no directional coding artifact.

**Translation to money**: mean mid over the window ≈ 12.32M JPY/BTC. At the B-K1 recomputed net
(+0.110 bps, CI crossing 0) that is ≈ +136 JPY per unit (1 BTC-CFD notional) round trip, ≈ 2,615
rounds/day observed → a **theoretical** ±0.35M JPY/day/unit if traded at that frequency, but the CI
means this could equally be −0.2M to +0.5M JPY/day — not a number to act on either way. Fee is 0%
(confirmed) so none of this is a fee-floor effect.

**MDE**: day-clustered SD ≈ 0.52–0.55 bps across the 4 cells, n=16 days → MDE(α=.05,power=.80) ≈
0.36–0.39 bps. The claimed effect (−1.02 to −1.42 bps) is **3–4× the MDE** — this audit had ample
power to detect an effect that size had it been present in this data/model, and did not.

**Falsification**: if the drift-exceeds-capture×2 mechanism held here, drift should exceed
2×2.65 ≈ 5.3 bps in magnitude; observed drift is 2.1–2.5 bps (primary) / 2.5 bps (stricter queue
robustness) — well under half that bar in both specifications.

## Claimed vs recomputed

| claim id | claimed | recomputed (this audit) |
|---|---|---|
| L19 | p50 fill 7–15s; maker close 99.8%; leg-drift −3.2〜−3.6 bps | median hold 3.6s (B_K1), maker close 99.97–100% (close match on fill dynamics); leg-drift −1.4 (median) / −2.1〜−2.5 (mean) bps — **smaller magnitude** than claimed |
| R26 | 0/4 cells, net −1.02〜−1.42 unit-bps, t −11〜−17, mechanism "drift always > capture×2" | 0/4 cells significant either way; net **+0.10〜+0.115** bps, t 0.74–0.89 (primary); −0.19 bps, t −1.78 (stricter queue robustness). Drift (2.1–2.5 bps) does **not** exceed capture×2 (5.3 bps) in either specification |
| PR12 | PREREG decision "棄却(R26)" | inherits R26's now-revised numbers (see 前提の誤り) |

## Verdict
- **L19: 数値差異(結論維持)** — fill-time and maker-close-rate mechanics reproduce closely; the
  quoted drift magnitude (−3.2〜−3.6bps) is larger than what this tape/model produces (−1.4〜−2.5bps),
  but sign and qualitative picture (maker almost always closes; some adverse drift) hold.
- **R26: 結論変更** — the specific mechanism ("drift always exceeds capture×2", t −11〜−17) is not
  reproduced. This audit's own implementation, on the same tape/window, finds all 4 cells statistically
  indistinguishable from zero (t<1) in the primary specification, and only marginally negative and
  still non-significant (t=−1.78) under a stricter, more conservative queue-fill assumption. The
  *practical* conclusion ("not a deployable edge") is not overturned — nothing here clears zero either
  — but the *stated strength and mechanism* of the rejection is not reproducible from raw data with an
  independent implementation.
- **PR12: 結論変更 (inherited)** — its "棄却(R26)" rationale should be revisited given R26's numbers
  above; the underlying practical non-deployment stance can likely stand, but not for the reason cited.

## 前提の誤り (assumption findings)
1. **premise**: drift magnitude −3.2〜−3.6 bps (L19, inherited by R26/PR12) | **source**: L19 | **data
   shows**: −1.4 bps median / −2.1〜−2.5 bps mean across two independent fill-model specifications on
   the same 16-day tape | **bias direction**: overstates how adverse leg-to-leg drift is, making
   rejection look stronger than the raw tape supports | **inherits**: every claim that cites this drift
   number as fixed (R26's t-stats, PR12's decision text).
2. **premise**: t −11〜−17 (R26) implying near-certainty of a negative edge | **source**: R26 |
   **data shows**: t 0.74–0.89 (primary) / −1.78 (stricter queue model) at the same n(16 days) — an
   order of magnitude smaller |t|, and MDE analysis shows this audit had power to see an effect 3–4×
   smaller than claimed | **bias direction**: claim's certainty is not supported by an independent
   re-derivation; likely driven by a different (non-reproduced-here) fill/queue or capture-basis
   assumption, or a different/larger sample outside this 16-day window | **inherits**: PR12's citation
   of R26 as settled; any later claim treating "SM family structurally loses" as an established prior.
3. **premise**: implicit assumption that K-tick-improved quotes face zero size ahead (used identically
   in both this audit and, presumably, the original) | **source**: shared modelling convention, not
   directly verifiable | **data shows**: only top-of-book + 5bps-aggregated depth is available (no
   per-tick L2), so zero-queue-ahead at 1–3 JPY inside a ~2,600 JPY average spread cannot be confirmed
   or refuted from this tape | **bias direction**: unknown sign, but the queue-realism robustness check
   (requiring 0.01 BTC cumulative crossing volume) shifts the point estimate from +0.11 to −0.19 bps —
   a swing bigger than the primary estimate itself, so conclusions here are **sensitive to this
   unverifiable assumption** | **inherits**: any claim in this family that reports a specific bps number
   without stating its queue-fill assumption.
4. **premise**: none found regarding fee (0% confirmed in `config/products.yaml`) or tick size (1 JPY,
   confirmed from data) — these check out as stated.

Budget used: ~20 tool calls (well under the 50 cap). Not committed.
