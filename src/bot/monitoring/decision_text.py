"""Japanese labels for the decision log the console shows (最近の判断).

bot/main.py writes every decision in English — the strategy's own ``reason``
string, plus HOLD / ORDER_SENT / REJECTED — because that is what the research
side reads back. The owner reads the console, so the translation happens HERE,
once, on the server: the page then renders whatever it is handed and a new
reason string needs no JavaScript change.

The rule is: an UNKNOWN string passes through raw. A strategy that is swapped
in tomorrow will log reasons nobody has mapped yet, and a wrong-but-Japanese
label would be worse than the English original — the owner would have no way to
tell a mistranslation from a real state. Every mapping below is a string the
bot actually emits (bot/main.py and bot/strategy/*.py); when the source string
carries a number, the number is carried through unchanged.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

JST = timezone(timedelta(hours=9))

# bot/main.py: the three decisions the main loop can log.
DECISION_JA = {
    "HOLD": "様子見",
    "ORDER_SENT": "発注",
    "REJECTED": "発注却下",
}

# bot/strategy/base.py SignalType + the protective stop main.py logs as a
# pseudo-signal.
SIGNAL_JA = {
    "BUY": "買い",
    "SELL": "売り",
    "CLOSE": "決済",
    "HOLD": "待機",
    "STOP_LOSS": "損切り",
}

# ---- exact reasons ---------------------------------------------------------
# Keyed on the literal string the strategy returns. Ordered by strategy so a
# grep from either side lands in the same place.
_EXACT = {
    # every strategy
    "insufficient history": "履歴不足",
    "indicators warming up": "指標の準備中",
    # xborder_momentum (the champion under validation). The two below the
    # current pair are older wordings that are still in logs/bot.jsonl, and the
    # console reads the log's tail, not the source tree.
    "no leader data column": "先行データ列なし",
    "leader data gap": "先行データ欠落",
    "between exit band and threshold": "手仕舞い帯と閾値の間",
    "below threshold": "閾値未満",
    # ema_cross
    "no cross": "クロスなし",
    "EMA fast crossed above slow": "EMA 上抜け",
    "EMA fast crossed below slow": "EMA 下抜け",
    # breakout
    "inside channel": "チャネル内",
    # inago (order flow)
    "no order-flow columns": "オーダーフロー列なし",
    "no volume surge": "出来高の急増なし",
    "surge without direction": "急増(方向なし)",
    # range_fade
    "regime not calm — stand aside": "静穏でない — 待機",
    "regime not calm - stand aside": "静穏でない — 待機",
    "degenerate range": "レンジ幅なし",
    "back at range middle": "レンジ中央に回帰",
    "inside range": "レンジ内",
    # rsi_reversion
    "RSI neutral": "RSI 中立",
    # wick_reversal
    "no dominant wick": "顕著なヒゲなし",
    # bot/main.py events that carry a `reason` of their own (entry suppression
    # and sizing); they are not decision rows today, but they are the strings
    # the bot logs and the console must not print them raw if one ever is.
    "risk_overlay": "リスクオーバーレイ",
    "budget_below_min": "発注額が最小単位未満",
    "exchange_stopped": "取引所が停止中",
    "exchange_condition": "取引所コンディション悪化",
    "exchange_degraded": "取引所の応答が劣化",
}

# ---- reasons that carry a number -------------------------------------------
# (pattern, template). The captured groups are substituted positionally; the
# numbers themselves are never reformatted — the log's own precision is what
# the研究 side reads, so the console shows the same digits.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # bot/main.py protective stop
    (re.compile(r"^protective stop: unrealized (.+)$"), "保護ストップ(含み {0})"),
    # bot/strategy/composite.py module veto
    (re.compile(r"^(BUY|SELL) entry vetoed by module (.+)$"),
     "新規{0}をモジュール {1} が拒否"),
    # xborder_momentum
    (re.compile(r"^leader ([+-]?[\d.]+)% over (\d+) bars$"),
     "先行 {0}% / {1}本"),
    (re.compile(r"^leader momentum faded \((.+)\)$"), "先行モメンタム減衰 ({0})"),
    (re.compile(r"^leader momentum (\S+) <= exit$"), "先行モメンタム {0} ≤ 手仕舞い帯"),
    # ema_cross
    (re.compile(r"^volatility too low \((.+)\)$"), "ボラ不足 ({0})"),
    # breakout
    (re.compile(r"^close (\S+) broke above (\d+)-bar high (\S+)$"),
     "{1}本高値 {2} を上抜け"),
    (re.compile(r"^close (\S+) broke below (\d+)-bar low (\S+)$"),
     "{1}本安値 {2} を下抜け"),
    # inago
    (re.compile(r"^buy surge x([\d.]+)$"), "買い急増 x{0}"),
    (re.compile(r"^sell surge x([\d.]+)$"), "売り急増 x{0}"),
    # range_fade
    (re.compile(r"^at range bottom \((.+)\)$"), "レンジ下限 ({0})"),
    (re.compile(r"^at range top \((.+)\)$"), "レンジ上限 ({0})"),
    # rsi_reversion
    (re.compile(r"^RSI oversold \((.+)\) in non-down trend$"),
     "RSI 売られすぎ ({0})"),
    (re.compile(r"^RSI overbought \((.+)\)$"), "RSI 買われすぎ ({0})"),
    # wick_reversal
    (re.compile(r"^lower wick (.+) rejected$"), "下ヒゲ {0} を否定"),
    (re.compile(r"^upper wick (.+) rejected$"), "上ヒゲ {0} を否定"),
]


def reason_ja(reason: Any) -> str:
    """A concise Japanese label, or the raw string when it is not one we know."""
    if not isinstance(reason, str):
        return ""
    text = reason.strip()
    if not text:
        return ""
    hit = _EXACT.get(text)
    if hit is not None:
        return hit
    for pattern, template in _PATTERNS:
        m = pattern.match(text)
        if m:
            return template.format(*m.groups())
    return text                                   # unknown: pass through raw


def decision_ja(decision: Any) -> str:
    if not isinstance(decision, str):
        return ""
    return DECISION_JA.get(decision.strip().upper(), decision)


def signal_ja(signal: Any) -> str:
    if not isinstance(signal, str):
        return ""
    return SIGNAL_JA.get(signal.strip().upper(), signal)


def jst_label(timestamp: Any) -> str:
    """``MM/DD HH:MM:SS`` in JST from the log's UTC ISO stamp.

    The bot stamps UTC (bot/logging_setup.py), and the owner reads JST — a
    console that shows raw UTC has been misread as "the bot stopped nine hours
    ago" more than once. A naive stamp is UTC, matching every reader in this
    repo; anything unparseable falls back to the raw text rather than to a
    plausible wrong time.
    """
    if isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool):
        dt = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
        return dt.astimezone(JST).strftime("%m/%d %H:%M:%S")
    if not isinstance(timestamp, str) or not timestamp.strip():
        return ""
    text = timestamp.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return timestamp
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(JST).strftime("%m/%d %H:%M:%S")
