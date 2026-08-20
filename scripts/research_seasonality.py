"""
Time-of-day / seasonality research on bitFlyer FX_BTC_JPY 1-minute candles.

Purely descriptive, causal (no look-ahead), simple pandas aggregation.
Prints numbers only -- no strategy or trading recommendations.

Usage:
    PYTHONPATH=src python scripts/research_seasonality.py
"""
import numpy as np
import pandas as pd

CSV_PATH = "data/candles_FX_BTC_JPY.csv"

pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 20)
pd.set_option("display.float_format", lambda x: f"{x:,.4f}")


def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["ts"])
    df = df.set_index("ts").sort_index()
    # ensure tz-aware UTC index
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    return df


def add_returns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # 1-minute log return computed from close-to-close, using only past+current bar
    # (causal: return at time t uses close[t] and close[t-1], no future info)
    df["log_ret"] = np.log(df["close"] / df["close"].shift(1))
    return df


def section_hour_of_day(df: pd.DataFrame) -> None:
    print("=" * 100)
    print("1) BY UTC HOUR: mean 1m log return (bps), std of 1m return (bps), volume share (%)")
    print("=" * 100)

    d = df.dropna(subset=["log_ret"]).copy()
    d["hour"] = d.index.hour

    grp = d.groupby("hour")
    mean_bps = grp["log_ret"].mean() * 1e4
    std_bps = grp["log_ret"].std() * 1e4
    n = grp["log_ret"].count()
    vol_by_hour = grp["volume"].sum()
    vol_share_pct = vol_by_hour / vol_by_hour.sum() * 100

    out = pd.DataFrame(
        {
            "n_obs": n,
            "mean_ret_bps": mean_bps,
            "std_ret_bps": std_bps,
            "volume_share_pct": vol_share_pct,
        }
    )
    out.index.name = "utc_hour"

    def marker(h):
        tags = []
        if h == 0:
            tags.append("09:00 JST open")
        if h == 13:
            tags.append("13:00 UTC funding")
        if h == 5:
            tags.append("05:00 UTC funding")
        if h == 21:
            tags.append("21:00 UTC funding")
        if h == 13:
            tags.append("~09:30 NY approaching (NY cash open ~13:30-14:30 UTC dep. DST)")
        return "; ".join(tags)

    out["note"] = [marker(h) for h in out.index]

    print(out.to_string())
    print(
        "\nNote: 09:00 JST = 00:00 UTC (JST = UTC+9, no DST). "
        "09:30 New York = 13:30 UTC during US Eastern Daylight Time (UTC-4, in effect for "
        "the sample period, late Jul-Aug 2026); the 13:00 UTC row is the last full UTC hour "
        "bucket preceding that 13:30 UTC mark, and 13:00 UTC also coincides with a funding "
        "settlement."
    )
    print(f"\nTotal 1-minute observations with valid return: {len(d)}")


def event_study(df: pd.DataFrame) -> None:
    print()
    print("=" * 100)
    print("2) FUNDING-SETTLEMENT EVENT STUDY (settlements at 05:00, 13:00, 21:00 UTC)")
    print("   Cumulative log return (bps) and mean |1m log return| (bps) over windows")
    print("   relative to settlement minute, averaged across all occurrences in sample.")
    print("=" * 100)

    settlement_hours = [5, 13, 21]
    windows = [(-60, -30), (-30, 0), (0, 30), (30, 60)]

    close = df["close"]
    log_ret = df["log_ret"]

    # build the list of settlement timestamps actually present (aligned to the grid)
    all_days = pd.Series(df.index.normalize().unique())

    rows = []
    for hour in settlement_hours:
        # collect settlement instants (day, hour:00) that exist within data range
        settlement_times = [d + pd.Timedelta(hours=hour) for d in all_days]
        settlement_times = [
            t for t in settlement_times if df.index.min() <= t <= df.index.max()
        ]

        for w_start, w_end in windows:
            cum_rets = []
            abs_rets = []
            n_events_used = 0
            for t0 in settlement_times:
                t_from = t0 + pd.Timedelta(minutes=w_start)
                t_to = t0 + pd.Timedelta(minutes=w_end)

                # cumulative log return over the window = log(close[t_to]/close[t_from])
                # using nearest available bars at/after t_from and at/before t_to (causal,
                # no future leakage beyond the window's own right edge)
                window_slice = log_ret.loc[
                    (log_ret.index > t_from) & (log_ret.index <= t_to)
                ]
                if window_slice.empty:
                    continue
                # require the window to be reasonably complete (>= 25 of 30 expected minutes)
                expected_minutes = w_end - w_start
                if len(window_slice) < expected_minutes - 5:
                    continue

                cum_ret = window_slice.sum()  # sum of 1m log returns == log return over window
                cum_rets.append(cum_ret)
                abs_rets.append(window_slice.abs().mean())
                n_events_used += 1

            mean_cum_bps = np.mean(cum_rets) * 1e4 if cum_rets else np.nan
            std_cum_bps = np.std(cum_rets, ddof=1) * 1e4 if len(cum_rets) > 1 else np.nan
            mean_abs_bps = np.mean(abs_rets) * 1e4 if abs_rets else np.nan

            rows.append(
                {
                    "settlement_utc_hour": hour,
                    "window_min": f"[{w_start:+d},{w_end:+d}]",
                    "n_events": n_events_used,
                    "mean_cum_ret_bps": mean_cum_bps,
                    "std_cum_ret_bps": std_cum_bps,
                    "mean_abs_1m_ret_bps": mean_abs_bps,
                }
            )

    out = pd.DataFrame(rows)
    print(out.to_string(index=False))


def section_day_of_week(df: pd.DataFrame) -> None:
    print()
    print("=" * 100)
    print("3) DAY-OF-WEEK: mean daily log return (%) and daily realized vol (%) by weekday")
    print("=" * 100)

    d = df.dropna(subset=["log_ret"]).copy()
    d["date"] = d.index.normalize()

    daily_ret = d.groupby("date")["log_ret"].sum()  # sum of 1m log rets = daily log return
    daily_rv = np.sqrt(d.groupby("date")["log_ret"].apply(lambda x: (x**2).sum()))  # realized vol (log-return units)
    daily_n = d.groupby("date")["log_ret"].count()

    daily = pd.DataFrame(
        {
            "log_ret": daily_ret,
            "realized_vol": daily_rv,
            "n_minutes": daily_n,
        }
    )
    daily["weekday"] = daily.index.day_name()
    daily["weekday_num"] = daily.index.weekday

    grp = daily.groupby(["weekday_num", "weekday"])
    out = grp.agg(
        n_days=("log_ret", "count"),
        mean_daily_log_ret_pct=("log_ret", lambda x: x.mean() * 100),
        mean_daily_realized_vol_pct=("realized_vol", lambda x: x.mean() * 100),
    ).reset_index().sort_values("weekday_num").drop(columns="weekday_num").set_index("weekday")

    print(out.to_string())
    print(f"\nTotal calendar days covered: {len(daily)} (dates: {daily.index.min().date()} to {daily.index.max().date()})")
    print("\nPer-day detail (date, weekday, log_ret %, realized_vol %, n_minutes):")
    detail = daily[["log_ret", "realized_vol", "n_minutes"]].copy()
    detail["log_ret"] = detail["log_ret"] * 100
    detail["realized_vol"] = detail["realized_vol"] * 100
    detail = detail.rename(columns={"log_ret": "log_ret_pct", "realized_vol": "realized_vol_pct"})
    print(detail.to_string())


def main():
    df = load_data(CSV_PATH)
    df = add_returns(df)

    print(f"Loaded {len(df)} 1-minute candles from {df.index.min()} to {df.index.max()} (UTC)")
    n_days_span = (df.index.max() - df.index.min()).days + 1
    print(f"Span: ~{n_days_span} calendar days")
    print()

    section_hour_of_day(df)
    event_study(df)
    section_day_of_week(df)


if __name__ == "__main__":
    main()
