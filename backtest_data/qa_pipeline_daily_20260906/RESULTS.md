# PIPELINE known-answer test — daily execution

Generated 2026-09-06T00:50:59.246183+00:00. seed=20260905 n_days=3000. Computation path: src/bot/research/overnight.py: overnight_returns, drop_glitches (imported directly, not reimplemented; the same module scripts/research_overnight_onr.py itself imports).

| Y planted (bps/day, high-vol tercile) | recovered mean | SE | t-stat | MDE | within MDE | low-tercile t | mid-tercile t |
|---|---|---|---|---|---|---|---|
| 0.0 | 0.5145 | 0.5985 | 0.8597 | 1.6757 | YES | -1.1972 | -0.1288 |
| 2.0 | 2.5145 | 0.5985 | 4.2016 | 1.6757 | YES | -1.1972 | -0.1288 |
| 5.0 | 5.5145 | 0.5985 | 9.2143 | 1.6757 | YES | -1.1972 | -0.1288 |

## ETF traps (drop_glitches / data_quality.py)

planted defect dates expected to be flagged: ['2005-04-07', '2005-04-08', '2006-03-21', '2006-03-22', '2010-05-11', '2010-05-12', '2011-04-29', '2012-08-08', '2012-08-09', '2013-12-16', '2013-12-17']

- Y=0.0: drop_glitches dropped 11 date(s): ['2005-04-07', '2005-04-08', '2006-03-21', '2006-03-22', '2010-05-11', '2010-05-12', '2011-04-29', '2012-08-08', '2012-08-09', '2013-12-16', '2013-12-17']
- Y=2.0: drop_glitches dropped 11 date(s): ['2005-04-07', '2005-04-08', '2006-03-21', '2006-03-22', '2010-05-11', '2010-05-12', '2011-04-29', '2012-08-08', '2012-08-09', '2013-12-16', '2013-12-17']
- Y=5.0: drop_glitches dropped 11 date(s): ['2005-04-07', '2005-04-08', '2006-03-21', '2006-03-22', '2010-05-11', '2010-05-12', '2011-04-29', '2012-08-08', '2012-08-09', '2013-12-16', '2013-12-17']

data_quality.py extreme_return hits on the ETF tape: 11

## Dividend-adjustment case (see HAND_DERIVATION_dividend.md)

planted record dates: ['2024-01-06', '2024-01-10', '2024-01-14'], amounts: [12.5, 8.0, 20.25]
ex_dates_from_record_dates() hand-derived cases match (4/4, both settlement regimes): True
max abs diff vs hand derivation: 0.00e+00 (exact_match=True)
expected mean(adjusted)-mean(raw) diff: 0.0036568749
actual mean(adjusted)-mean(raw) diff: 0.0036568749 (mean_diff_matches=True)

## Return-kind case (log vs simple, see HAND_DERIVATION_return_kind.md)

planted simple overnight return: 5.0bps
kind='simple' recovered: 5.000000bps (matches planted exactly: True)
kind='log' recovered: 0.0004998750
r_simple - r_log = 0.000000124958, first-order r_simple**2/2 = 0.000000125000 (matches within 1%: True)

## パイプラインの欠陥 (findings)

- The unadjusted 10:1 split at 2011-04-29 and the 5 genuine bad-print days are INDISTINGUISHABLE to drop_glitches() (both are just |log-return|>10%): a real corporate action gets silently dropped exactly like a data error. This reproduces, on synthetic data, the same failure mode schema/jpx_etf_daily.json's known_defects records for the real 1306.T 2015-01-05 split (once misclassified as a bad print by an earlier audit pass).
