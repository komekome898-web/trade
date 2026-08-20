"""Causal technical indicators.

Every function maps a series to a series of the same length where element i
depends ONLY on elements 0..i (no look-ahead). Warm-up positions are NaN.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    out = series.ewm(span=period, adjust=False, min_periods=period).mean()
    return out


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.where(avg_loss != 0, 100.0).where(~(avg_gain.isna() | avg_loss.isna()))


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    line = ema(series, fast) - ema(series, slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def rolling_volatility(series: pd.Series, period: int = 20) -> pd.Series:
    return series.pct_change().rolling(period, min_periods=period).std()


def donchian(high: pd.Series, low: pd.Series, period: int = 20) -> pd.DataFrame:
    # shift(1): today's breakout is judged against PRIOR N bars, not including today
    return pd.DataFrame({
        "upper": high.rolling(period, min_periods=period).max().shift(1),
        "lower": low.rolling(period, min_periods=period).min().shift(1),
    })
