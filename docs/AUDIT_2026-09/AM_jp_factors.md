# AM audit — JPL3 (JP momentum/value/reversal factor laws)

**Claim (verbatim, 00_packets.md §1, source=SURVEY_JP_EQUITIES):** "モメンタム不在は2026年も継続(FF Japan WML+1.5%/
年t=0.62)。バリュー生存(+4.85%t=2.69)". Packet-AM row: reproduce FF Japan WML/HML/reversal sign & t independently.

**Files read:** `PROTOCOL.md`; `00_packets.md` lines 15-16,186,287,304 (grep only); `backtest_data/
jp_factors_20260905/{README.txt,MD5SUMS,Japan_3_Factors.csv,Japan_MOM_Factor.csv}`; `config/{config,products,
on1_live}.yaml`. Script: `scratchpad/audit_AM.py` (own re-implementation; both CSV MD5s verified OK).

## 1. Denominator
Monthly FF Japan factors ("202607 Bloomberg database" vintage). 3-factor file n=433mo (199007–202607); momentum
n=429mo (199011–202607, 4mo formation lag). No `-99.99` missing codes, no dup/skipped months in either file.
Annual trailer rows (n=35yr, 1991-2025) used only as a cross-check, not primary.

## 2. Reproduction — full sample (Newey-West HAC, Bartlett, auto-lag L=floor(4·(T/100)^(2/9))=5)
| factor | n | ann.mean | ann.sd | t(NW) | Sharpe |
|---|---|---|---|---|---|
| WML | 429 | +0.99%/yr | 14.78% | 0.367 | 0.067 |
| HML | 433 | +4.94%/yr | 10.78% | 2.297 | 0.458 |
| SMB | 433 | -0.37%/yr | 10.45% | -0.219 | -0.036 |
| Mkt-RF | 433 | +2.29%/yr | 18.89% | 0.678 | 0.121 |

Naive (no HAC) monthly t: WML 0.399, HML 2.753. Annual-return naive t (n=35, French's own annual rows): WML
0.656, HML 1.262. **HML +4.85%/t=2.69** reproduces well under plain monthly OLS (4.94%/2.75). **WML +1.5%/t=0.62**
does not reproduce jointly with HML under any single method (monthly-naive/NW L=4-12/annual-naive all tried) —
qualitative conclusion (≈0, insignificant) holds everywhere, magnitude/precision differs.

## 3. By decade (NW t)
| factor | 1990s | 2000s | 2010s | 2020-26 |
|---|---|---|---|---|
| WML | +4.5%/t=0.71 | -2.3%/t=-0.36 | +0.5%/t=0.17 | +1.7%/t=0.37 |
| HML | -2.4%/t=-0.62 | +14.2%/t=3.85 | -1.8%/t=-0.69 | +11.7%/t=1.91 |
| SMB | -5.8%/t=-1.30 | +2.6%/t=0.79 | +4.7%/t=2.56 | -4.8%/t=-1.75 |
| Mkt-RF | +0.3%/t=0.03 | -4.8%/t=-0.68 | +7.8%/t=2.26 | +7.5%/t=1.38 |

WML never significant in any decade. HML significant only in the 2000s, sign-flips negative 1990s/2010s — its
full-sample significance is carried by one decade, not a stable per-decade effect.

## 4. Rolling 10yr (120mo) NW-t
WML: 310 windows, range [-0.95,+1.11], never crosses ±1.96. HML: 314 windows, range [-1.46,+3.90], 18.2% exceed
+1.96 (clustered around the 2000s), 0% below -1.96. HML's "significance" comes and goes with a ~10y window.

## 5. Years for t=2 (iid-annual, N=(2·sd/mean)²)
WML **900yr** (near-never at observed mean/sd — stronger evidence for "absent" than claim's own t suggests). HML
**19.0yr** (claim's "~20yr" reproduces closely). SMB 3160yr, Mkt-RF 272yr. Ignores positive AR(1) (HML 0.149,
WML 0.083) which would push true N higher.

## 6. MDE at observed n (α=.05 two-sided, power=.80, NW SE)
WML(429) ≈7.52%/yr; HML(433) ≈6.02%/yr; SMB 4.75%/yr; Mkt-RF 9.47%/yr. Claimed WML effect (1.5%/yr) is ~5x below
its own MDE — failing to reject momentum=0 was near-guaranteed at this n regardless of a small true effect.

## 7. Controls
- Sign-reversed: trivial mirror (|t| unchanged) — no new info, included for completeness.
- Random-sign placebo (2000 draws on |WML|): placebo t~N(-0.001,1.054); 73% of draws produce |t|≥observed 0.367
  — WML statistic indistinguishable from noise.
- State-conditional: not applicable, claim names no conditioning state; none fabricated.
- Multiple comparisons: 4 factors tested, only HML clears naive |t|>1.96. Bonferroni crit (α/4, 5%)≈2.24 —
  naive-monthly HML 2.75 clears it, NW HML 2.30 barely clears it; thin margin.

## 8. Simplest alternative explanation
corr(WML,Mkt-RF)=-0.13, corr(HML,Mkt-RF)=-0.19, corr(WML,HML)=-0.22 — all small; neither factor reduces to a
market-beta or reversal-of-the-other story.

## 9. Consistency (split-half)
WML: 1st half +2.21%/t=0.52 → 2nd half -0.24%/t=-0.07 (sign flips toward zero: momentum weakened, not
strengthened, over time — supports "absent...continues"). HML: 1st half +6.12%/t=2.03 → 2nd half +3.76%/t=1.28
(same sign, materially weaker recently) — not mentioned in claim's "value survives" framing.

## 10. Translation to money / cost
No fee constant in this repo applies to a JP-equity long/short factor book: `config/products.yaml` and
`config.yaml` cover bitFlyer crypto (taker_fee_pct 0-0.15%); `on1_live.yaml` covers ON1 (Nikkei-225 micro
futures, directional single-instrument), not a 2x3-sorted L/S portfolio. Stated explicitly rather than borrowing
an unrelated fee. French factors are gross, zero-investment, no-cost hypothetical portfolios (no short borrow,
no rebalancing slippage/impact) — so 4.94%/yr HML gross is an upper bound; bias direction is to overstate net
achievable return. On JPY10,000,000 gross/leg, HML ≈JPY494,000/yr gross before any implementation cost; this repo
has no JP cash-equity execution path (`src/`) to earn it.

## Falsification
If Japan WML's true ann. mean is ≥±7.5%/yr (this n's MDE), NW |t| would exceed 1.96 at ~80% power; it does not
(t=0.37) — a premium that large is rejected at this n. Effects <~7.5%/yr cannot be distinguished from zero here
regardless of true value, so "absent" means "not detectably large," not "proven zero."

## Verdict: 数値差異(結論維持)
Both directional conclusions (momentum absent / value alive-but-fading) hold; the specific claimed numbers do
not jointly reproduce under one consistent methodology.

| stat | claimed | NW (primary) | monthly-naive | annual-naive |
|---|---|---|---|---|
| WML mean | +1.5%/yr | +0.99%/yr | +0.99%/yr | +2.28%/yr |
| WML t | 0.62 | 0.37 | 0.40 | 0.66 |
| HML mean | +4.85%/yr | +4.94%/yr | +4.94%/yr | +3.77%/yr |
| HML t | 2.69 | 2.30 | 2.75 | 1.26 |

HML mean/t reproduce closely under plain monthly OLS. WML's t reproduces under no single tried method, but stays
"insignificant, near zero" everywhere — the NW estimate and 900yr time-to-significance argue "absent" even more
strongly than the claim's own t=0.62. "~20yr for value t=2" reproduces almost exactly (19.0yr). No reversal
factor exists in the French Japan library (only 3-factor+momentum published) — not fabricated, see below.

## 前提の誤り
1. **premise:** one consistent method underlies both WML t=0.62 and HML t=2.69. **source:** both quoted together
   as if same procedure. **data shows:** HML matches plain OLS-monthly; WML is closer to an annual-return calc;
   no method reproduces both at once. **bias:** unclear direction (typo, or undisclosed method split).
   **inherits:** any JPL/SURVEY_JP_EQUITIES claim quoting mean+t without stating estimator/lag/horizon — e.g.
   JPC1-3, JPR1, JPR3, SV1, SV2 (external-fetchable list, `00_packets.md` L304), if drawn from the same survey.

2. **premise:** JP short-term reversal is a French-library factor comparable to WML/HML. **source:** JPL3 asserts
   reversal "exists"; packet row asks to reproduce its sign/t. **data shows:** the supplied French Japan snapshot
   has only 3-factor+momentum — **no JP ST-reversal series exists** in this data (unlike the US library). This
   sub-claim is **unverifiable from supplied data**; audit used only WML/HML/SMB/Mkt-RF per protocol instruction.
   **bias:** claim states reversal as settled fact; this cannot corroborate or refute it — citing it as
   established here would overstate confidence. **inherits:** any claim citing "JP reversal" without naming a
   (daily-equity) data source.

3. **premise:** French Japan values are a fixed historical record. **source:** implicit — static t quoted with no
   vintage date. **data shows:** README states "202607 Bloomberg database" vintage; French restates the *entire*
   series on each database refresh, so an earlier-vintage t-stat won't exactly match today's re-fetch even over
   the same nominal range — plausibly explains part of the WML/HML mismatch above, on top of finding 1.
   **bias:** not systematic; makes exact point-value reproduction inherently time-limited. **inherits:** every
   Ken-French-sourced claim in `00_packets.md` L304 (JPC1-3, JPL1, JPL3, JPR1, JPR3, SV1, SV2).

4. **premise:** HML's significance is a stable, decade-robust property. **source:** "バリュー生存" stated as a
   standing fact. **data shows:** decade NW-t = -0.62/+3.85/-0.69/+1.91; only one of four decades individually
   significant; rolling-10y t ≥1.96 in only 18% of windows, clustered on one period. **bias:** overstates
   persistence/reliability of the value premium. **inherits:** any composite/strategy claim treating "JP value" as
   a dependable always-on tilt (would need checking against `composite.yaml`/strategy docs — out of scope here).
