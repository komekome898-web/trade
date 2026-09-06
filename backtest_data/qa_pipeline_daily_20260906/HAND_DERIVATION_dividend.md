# Hand derivation — dividend-adjustment known-answer case

## Part 1: record date -> effective ex-date (ex_dates_from_record_dates)

Independently checked against 4 hand-derived cases spanning both the T+3
(pre 2019-07-16) and T+2 (post) JPX settlement regimes, and both a weekend and a
trading-day record date:

| record date | expected ex-date | got ex-date | matches |
|---|---|---|---|
| 2018-03-31 | 2018-03-28 | 2018-03-28 | True |
| 2020-03-31 | 2020-03-30 | 2020-03-30 | True |
| 2013-02-10 | 2013-02-06 | 2013-02-06 | True |
| 2019-08-10 | 2019-08-08 | 2019-08-08 | True |

all 4 hand-derived record-date cases match: True

## Part 2: dividend-adjusted overnight return (overnight_returns dividends=...)

The 3 ex-dates below are the ex_date_effective values Part 1's function produced
from the record dates ['2024-01-06', '2024-01-10', '2024-01-14'] against the synthetic tape's own
trading-day calendar -- NOT hardcoded row indices.

Computed independently of `overnight_returns`, before running it, using
`r_adj = ln((raw_open(t+1) + amount) / close(t))` where `raw_open(t+1)` is the
as-printed (ex-dividend-depressed) open and `amount` is the planted distribution.

| t+1 row | date(t) | date(ex) | amount | raw_open(t+1) | close(t) | hand r |
|---|---|---|---|---|---|---|
| 2 | 2024-01-03 | 2024-01-04 | 12.5 | 993.002500 | 1005.000000 | 0.0004998750 |
| 5 | 2024-01-08 | 2024-01-09 | 8.0 | 1012.510000 | 1020.000000 | 0.0004998750 |
| 7 | 2024-01-10 | 2024-01-11 | 20.25 | 1010.265000 | 1030.000000 | 0.0004998750 |

Expected mean(adjusted r) - mean(raw r) over all 11 legs = sum(ln((raw_open+amount)/raw_open)) / n = 0.0036568749

## Result of running overnight_returns(df, dividends=...)

| t+1 row | hand r | function r | abs diff |
|---|---|---|---|
| 2 | 0.0004998750 | 0.0004998750 | 0.00e+00 |
| 5 | 0.0004998750 | 0.0004998750 | 0.00e+00 |
| 7 | 0.0004998750 | 0.0004998750 | 0.00e+00 |

actual mean(adjusted r) - mean(raw r) = 0.0036568749
exact_match (max abs diff < 1e-12): True
mean_diff_matches (< 1e-12): True
