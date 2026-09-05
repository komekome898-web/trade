# PIPELINE known-answer test — daily execution

Generated 2026-09-05T07:38:46.597100+00:00. seed=20260905 n_days=3000. Computation path: scripts/research_overnight_onr.py: overnight_returns, drop_glitches, mean_t (imported directly, not reimplemented).

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

data_quality.py extreme_return hits on the ETF tape: 5

## パイプラインの欠陥 (findings)

- The unadjusted 10:1 split at 2011-04-29 and the 5 genuine bad-print days are INDISTINGUISHABLE to drop_glitches() (both are just |log-return|>10%): a real corporate action gets silently dropped exactly like a data error. This reproduces, on synthetic data, the same failure mode schema/jpx_etf_daily.json's known_defects records for the real 1306.T 2015-01-05 split (once misclassified as a bad print by an earlier audit pass).
- scripts/data_quality.py:scan_file() reports extreme_return "count" as len(extreme_examples) where extreme_examples is capped at MAX_EXAMPLES=5 (same bug pattern in the crossed_book/maintenance_window/non_monotonic/zero_volume checks -- only duplicate_keys and gaps use an uncapped counter). On this ETF tape with 11 genuine extreme-return transitions, data_quality.py under-reports the count as exactly 5, silently hiding how widespread the problem actually is once a file has more than 5 hits.
