# Packet D — FX Tokyo Fix (blind audit)

Claims: FXL3, FXL4, FXR1, FXR2, FXC3. Data: `backtest_data/fx_usdjpy_1m_20260822.csv.gz`
(timestamp col is UTC-aware ISO8601, 2023-01-01→2026-08-21, 1,640,160 rows, 1-min OHLCV +
`ask_close` populated only 2026-07-23→2026-08-21). JST = UTC+9, fix = 00:55 UTC. Valid trading
days (weekday, complete 08:00–10:30 JST bars, nonzero volume in that window): **n=947** of 1,329
calendar weekdays (382 excluded: gaps/holidays/weekends misfiled/no volume). Script:
`scratchpad/audit_D.py` (own implementation; not read from repo).

Cost: no GMO USDJPY spread/fee constant found in `config/*.yaml` or `src/`; `backtest_data/gmo_swap_usdjpy.csv`
is rollover swap points only, not spread/commission. Used the **stated 0.71bps round-trip floor**
(0.314 spread + 0.4 fee) per instructions, gross reported alongside. 0.71bps ≈ 1,129 JPY round-trip
per 100,000 USD lot at ~159.

## Claimed vs recomputed

| Claim | Claimed | Recomputed | Verdict |
|---|---|---|---|
| FXL3 vol×3.2 (1.92bps) | 3.2x, 1.92bps at 9:54 | 2.80–4.36x (metric-dependent), 2.40bps mean\|ret\|; day-boot 95%CI[4.09,4.65]x, n=944 | 数値差異(結論維持) |
| FXC3 spread floor / UTC21×20 | p10=p75=0.5銭 flat; UTC21=6.33bps=20x | flat p75=0.317bps≈0.5銭 but p10=0.127bps (not flat); UTC21 median=2.97bps(9.4x), p90=5.92bps(23.6x) | 数値差異(結論維持), low confidence (n=26 days, see below) |
| FXR1 pre-mom cost-losing | gross+0.4bps, sign-stable, <0.71 | gross 0.03–0.61bps across grid, **all**<0.71 (n=947/cell) | 再現 (headline); sign-stability premise 数値差異 |
| FXR2 post-reversal absent | mechanism absent, sign flips over H | fade gross −0.12→−0.25bps, sign **stable** (no flip), all \|t\|<1.1, all sub-cost | 数値差異(結論維持) |
| FXL4 gotobi null | n=28, t=−0.42, opposite sign | n=204 gotobi (vs 743 non), t=−1.37, opposite sign confirmed, perm-p=0.127 | 数値差異(結論維持) |

## Detail

**FXL3.** Fix-bar (09:54 JST, covers 9:54–9:55) mean\|ret\|=2.40bps vs day distribution: median-of-minute-medians
baseline gives 2.80–2.96x; a per-day ratio (fix-bar / that day's own median) bootstrap (2000 resamples,
day-clustered, n=944) gives mean 4.36x, 95%CI [4.09,4.65]. All metrics land at "several-fold", not exactly
3.2x — the multiple is sensitive to which baseline (all-minute mean vs median vs per-day) is used; claim's
2 sig-figs imply more precision than the metric supports. **Control:** 200 random non-fix minutes give
mean mult 1.02x, p95 1.56x, max 2.00x — 09:54 (rank 4/1440 by mean\|ret\|) is a genuine outlier, not noise.
**Alternative explanation:** ranks 1–3 are 21:30/22:30/23:00 JST (12:30/13:30/14:00 UTC — US data-release
window), all *larger* than the fix. The fix is a real, but not the day's largest, scheduled-time vol event.

**FXC3.** Only 26 trading days of `ask_close` exist (2026-07-23→08-21) — far short of the claim's implied
coverage; treat as low-n. Flat-hour p75 (0.317bps) matches the claimed 0.5銭≈0.314bps floor well, but
p10=0.127bps is well below it (claim's "p10=p75" flatness is not reproduced — more low-end dispersion than
claimed). UTC21: median 2.97bps (9.4x flat median), p90 5.92bps (23.6x) — the claimed "6.33bps=20x" sits
near the p90–p95 region, not the median, so the claim is citing a tail statistic without saying so.
**Data-validity flag:** several UTC21/near-UTC21 spread values recur at *exactly* equal bps (e.g. 5.9221bps
appears 1381 times bit-identical) — consistent with a formulaic/synthetic ask overlay rather than raw
market ticks; this weakens confidence in FXC3 as a market-microstructure finding from this file specifically.

**FXR1.** Grid: signal window W∈{15,30,60}min ending 09:55, hold to 09:55 or 10:00 (6 cells, n=947 each,
direction = in-sample best/majority sign). Gross ranges 0.03–0.61bps; **every** cell nets negative after
0.71bps (net −0.10 to −0.68bps) — the "cost-losing" headline is robust across the whole declared grid,
including its best cell. However the "sign-stable" premise does not hold: splitting the W=30/hold-955 cell
by year gives signs +,+,−,− for 2023/24/25/26 (means +0.155,+0.583,−0.227,−0.340bps) — the apparent
positive gross is largely an artifact of picking the in-sample-favourable sign, not a stable drift.
**Control:** 300 random 30-min-anchor windows elsewhere in the day (excl. 09:00–11:00) give best-direction
gross mean 0.28bps, p90 0.56bps — the real pre-fix cell (0.08bps) sits at only the ~25th percentile of that
null, i.e. pre-fix momentum is *weaker* than a typical random 30-min window, not special.

**FXR2.** Fade = −sign(09:25→09:55 move) applied to 09:55→(09:55+H) return, H∈{5,15,30} (n=947/cell).
Gross is negative and **sign-stable** across H (−0.12,−0.25,−0.22bps; t=−0.86,−1.10,−0.73) — we do not
reproduce the claimed in-window sign flip; instead fading loses money at every horizon we tried, all
statistically indistinguishable from zero and all sub-cost. Chase (sign-reversed control) mirrors fade
exactly (+0.12,+0.25,+0.22bps), confirming no computation asymmetry. Net effect either way: no exploitable
reversal (or continuation) edge — the *conclusion* "no tradeable mechanism" reproduces even though the
specific "sign flips" narrative does not.

**FXL4.** Gotobi = day-of-month ∈{5,10,15,20,25,30,31} (JST calendar-day approximation; declared, not the
original definition). Using the W=30/hold-955 pre-fix return: gotobi n=204, mean=−0.889bps, t=−1.37;
non-gotobi n=743, mean=+0.348bps, t=+0.90 — sign flip vs overall reproduces qualitatively. But **n=204 vs
claimed n=28 is a 7x denominator mismatch** — plausible causes: a narrower gotobi definition (e.g. only
5th/10th), a shorter sample window, or additional filters not stated in the claim; unverifiable from data
alone. Permutation test (5000 shuffles of the gotobi/non-gotobi label, same group sizes) on the group-mean
gap (−1.237bps observed) gives p=0.127 — not significant, consistent with "null," but weaker than the
claimed t=−0.42 (ours is closer to marginal).

## Selection contamination (Q7)
The pre/post-fix family searched here spans ≈20 implicit cells (FXR1: 6 W×hold × best-direction choice;
FXR2: 3 H × fade/chase; FXL4: 1 split × underlying W choice). Bonferroni-adjusted two-sided z for α=0.05
over 20 cells ≈3.02 (t must exceed ~3.0 to survive). No recomputed cell in FXR1/FXR2/FXL4 exceeds |t|=1.37 —
none would survive a multiplicity correction, reinforcing the reject/null verdicts independent of the
cost-floor argument.

## MDE (Q10, W=15/30/60, hold-955, n=947, α=0.05, power=0.80)
W=15: std=7.47bps → MDE=0.68bps (< 0.71 cost floor — adequately powered to resolve the floor).
W=30: std=10.30bps → MDE=0.94bps (> floor — underpowered near the floor).
W=60: std=14.53bps → MDE=1.32bps (> floor — underpowered). **Falsification:** FXR1 would be falsified by a
W=15 net edge with 95% CI excluding 0 and above 0bps net of 0.71bps — not observed (net 95%CI includes 0
and is centered negative). FXR2 falsified by a stable-sign, |t|>2, net-positive fade edge at any H — not
observed. FXL4 falsified by a gotobi-only edge surviving both the permutation null and the cost floor —
not observed (p=0.127, and −0.89bps gross is itself smaller than floor magnitude in absolute-edge terms).

## 前提の誤り (assumption findings)

| premise | source | data shows | bias direction | inherits to |
|---|---|---|---|---|
| Round-trip cost = 0.71bps is a verified GMO constant | claim text | not found in `config/*.yaml` or `src/`; `gmo_swap_usdjpy.csv` is swap-only | none — we used the stated number as instructed, but it is **unverified from this repo's data**, so any claim resting on "below 0.71 = cost-losing" is only as solid as an external number | FXR1, FXR2, and any other claim citing "the taker/spread cost floor" |
| FXL3's "3.2x" / "1.92bps" is a single precise figure | claim text | recomputed multiple ranges 2.8–4.4x and abs. magnitude 2.40bps depending on baseline/metric choice | claim understates true magnitude by our central estimates but the exact figure is baseline-dependent, not fabricated | any claim building a specific bps budget on top of FXL3's fix vol number |
| FXC3's spread structure generalizes across the full sample | claim text | only 26 of 947 valid days carry `ask_close`; several UTC21 spread values are bit-identical across >1000 rows, suggesting a synthetic/formulaic overlay rather than raw ticks | overstates generality/authenticity — the UTC21×20 finding may be a property of one 1-month data-generation run, not persistent market structure | any downstream claim assuming this spread profile is stable/replicable elsewhere in `backtest_data` |
| FXR1's "sign-stable" gross | claim text | by-year sign is +,+,−,− (2023–2026); a random-window control shows the pre-fix cell is *weaker* than typical random-window momentum | the claim's supporting narrative (a real, if sub-cost, directional drift) is not supported — true state is closer to "no drift at all", which strengthens rather than weakens the reject, but for a different reason than stated | any future re-litigation of FXR1 that assumes "a small stable edge exists but costs eat it" |
| FXR2's "gross sign reverses within judgment window" | claim text | fade sign is stable (negative) across H=5/15/30 in our recomputation; no in-window flip observed | mechanism description does not match; conclusion (no edge) unaffected | none identified beyond FXR2 itself |
| FXL4's n=28 | claim text | our gotobi day count (day-of-month∈{5,10,15,20,25,30,31}, n=947 valid-day universe) = 204, not 28 | direction of bias unclear (definition unverifiable); flags that the original denominator/definition is not reproducible from data+claim text alone | any claim citing "gotobi n=28" as an established sample size |

## Files read
`docs/AUDIT_2026-09/PROTOCOL.md`, `docs/AUDIT_2026-09/00_packets.md` (grep on claim IDs only, section
1.5–1.7 rows), `backtest_data/fx_usdjpy_1m_20260822.csv.gz`, `backtest_data/gmo_swap_usdjpy.csv` (header),
`backtest_data/fx_fundamentals_20260822/` (listing only, not used further — 5-10-day flags derived
directly from calendar day-of-month instead), `config/config.yaml` (grep), `src/` (grep, no fee constant
found). No `research_*.py`/`judge_*.py`/`KNOWLEDGE*`/git history/`*_RUN.txt` opened.

Tool-call budget used: ~19 of 50.
