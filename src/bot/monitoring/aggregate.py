"""Aggregate all runtime state files into one dashboard payload.

Pure functions over the files the components already write — no new state,
no network. Everything degrades to None/empty when a file is missing.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from bot.monitoring.decision_text import (
    decision_ja, jst_label, reason_ja, signal_ja,
)
from bot.monitoring.gates import cached_scan, collect_gates, parse_ts
from bot.radar import StormRadar

# データ蓄積表 + 判定ゲート双方が読む「目的」注記 (日本語・簡潔)。表示専用の静的
# テキストであり、ゲートのバー文字列/判定ロジック(gates.py, judge_gates.py)には
# 一切触れない — fail-close設計のバーはここでは変更できない。
GATE_PURPOSE: dict[str, str] = {
    "champion": "n>=30決済で本番投入可否を判定(判定済みFAIL・以後はC2用データの収集運搬役)",
    "c2": "嵐時計窓内サブセットの追加検証(§4a)",
    "oi": "30日到達で清算リバージョンのフェーズC判定",
    "board": "板7日で監視モードの再校正",
    "spreadmm": "板14日でスプレッドMMの確認判定(maker線は探索で既に棄却済み)",
    "funding": "63日で資金調達後ドリフト再検定",
}

# データ蓄積表: 収集ラベル -> 目的 (「何のために集めているか」を1行で)。
# scripts/dashboard.py が同じキーでこの目的文言を参照する。
COLLECTOR_PURPOSE: dict[str, str] = {
    "板記録 (WS)": "G7・監視モード(スプレッドMM再開条件)・GMO校正",
    "ティッカー/板上位テープ": "S12判定・嵐ライブラリ",
    "venues (bitbank/GMO/bF現物)": "効率ギャップ地図の定点観測",
    "OIスナップショット (+価格)": "G6フェーズC・推定建値台帳",
    "注目系列": "市場加熱度計器・長期チャート",
    "JPX日報": "ON1ペーパー台帳",
    "bitFlyer candles": "G8資金調達窓",
    "Binance日次": "G6特徴量・レジーム監視",
    "USDJPY": "円換算",
    "Binance 1m": "外部特徴量(短期足)参考",
    "bitbank 1m": "退役スキャルパーの参考系列",
    "spread record": "実効スプレッド計測",
}

# 推定建値台帳 (scripts/research_position_ladder.py): 価格列は 2026-08-31 以降の
# 行のみ使う (それ以前は btc_usd が無い/バックフィル対象外のロット)。
LADDER_PRICE_CUTOFF = "2026-08-31"


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _tail_jsonl(path: Path, n: int | None = None,
                max_bytes: int = 512 * 1024) -> list[dict]:
    """The last ``n`` JSON objects of a .jsonl file (all of them when n is None),
    read from at most ``max_bytes`` of tail. Missing file -> []. Shared with
    bot.monitoring.market_view, which reads a larger tail and wants every
    record rather than a fixed count."""
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            f.seek(max(0, size - max_bytes))
            chunk = f.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    lines = chunk.splitlines()
    if len(lines) and size > max_bytes:
        lines = lines[1:]  # drop the partial first line
    out = []
    for line in (lines if n is None else lines[-n:]):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def _file_info(path: Path, now: float) -> dict | None:
    try:
        st = path.stat()
    except OSError:
        return None
    return {"size": st.st_size, "age_sec": round(now - st.st_mtime, 1)}


def _ingest_latest(dir_path: Path, pattern: str, now: float,
                   dated: bool = True) -> dict | None:
    """Freshness of the newest collector output matching ``pattern``.

    ``dated`` files carry YYYYMMDD in the name (data/tape's daily shards), so
    the newest is the lexicographic max and its stamped date is reported;
    otherwise (data/venues) the newest mtime wins and ``date`` stays None.
    Missing directory or no match -> None — the tile renders 未収集.
    """
    try:
        files = [f for f in dir_path.glob(pattern) if f.is_file()]
    except OSError:
        files = []
    if not files:
        return None
    if dated:
        latest = max(files, key=lambda f: f.name)
    else:
        def _mtime(f: Path) -> float:
            try:
                return f.stat().st_mtime
            except OSError:
                return 0.0
        latest = max(files, key=_mtime)
    info = _file_info(latest, now)
    if info is None:
        return None
    date = None
    if dated:
        m = re.search(r"(\d{4})(\d{2})(\d{2})", latest.name)
        if m:
            date = "-".join(m.groups())
    return {"date": date, "age_sec": info["age_sec"], "size": info["size"]}


def _last_csv_row(path: Path, max_bytes: int = 8192) -> dict[str, str] | None:
    """Header + last non-empty line of a small CSV, without reading it all.

    Used for data/oi_snapshots.csv (scripts/record_oi.py appends one row per
    collector run). Returns None when the file is missing, header-only or
    unreadable.
    """
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            header = f.readline().decode("utf-8", errors="replace")
            f.seek(max(f.tell(), size - max_bytes))
            tail = f.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    cols = [c.strip() for c in header.strip().split(",") if c.strip()]
    lines = [ln for ln in tail.splitlines() if ln.strip()]
    if not cols or not lines:
        return None
    values = lines[-1].split(",")
    if len(values) != len(cols):
        return None
    return {c: v.strip() for c, v in zip(cols, values)}


def _oi_snapshot(path: Path, now: float) -> dict[str, Any] | None:
    """Freshness + values of the newest data/oi_snapshots.csv row."""
    info = _file_info(path, now)
    if info is None:
        return None
    row = _last_csv_row(path)
    row_age = None
    if row and row.get("ts_utc"):
        try:
            row_age = round(now - datetime.fromisoformat(row["ts_utc"]).timestamp(), 1)
        except ValueError:
            row_age = None
    return {
        "size": info["size"],
        # file mtime age; row_age is the age of the snapshot the row records
        "age_sec": info["age_sec"],
        "row_age_sec": row_age,
        "last": row,
    }


_ladder_module_cache: dict[str, Any] = {}


def _ladder_module() -> Any:
    """Lazily loads scripts/research_position_ladder.py's build_ladder — the
    ONE implementation of the OI-delta ladder inference, shared with the CLI
    tool by file identity rather than duplicated here. No network call is
    made: only build_ladder (pure) is used, never the OKX backfill helpers."""
    mod = _ladder_module_cache.get("mod")
    if mod is not None:
        return mod
    path = Path(__file__).resolve().parents[3] / "scripts" / "research_position_ladder.py"
    spec = importlib.util.spec_from_file_location("research_position_ladder", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _ladder_module_cache["mod"] = mod
    return mod


def _position_ladder(path: Path, now: float) -> dict[str, Any] | None:
    """Estimated entry-price ladder for the その他 console section (推定建値
    台帳). Rows are restricted to ts_utc >= LADDER_PRICE_CUTOFF (earlier rows
    predate the price backfill) and rows with no btc_usd cell are skipped —
    both per the same rule build_ladder's own docstring records. Display only:
    G6 phase-C study pending (KNOWLEDGE §4), no signal is adopted from this.
    """
    info = _file_info(path, now)
    if info is None:
        return None
    try:
        with path.open(newline="", encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r.get("okx_usdt_oi")]
    except OSError:
        return None
    rows = [r for r in rows if (r.get("ts_utc") or "") >= LADDER_PRICE_CUTOFF]
    if not rows:
        return {"age_sec": info["age_sec"], "price": None, "above_pct": None,
                "below_pct": None, "rungs": []}
    ladder, px = _ladder_module().build_ladder(rows)
    if not ladder or px is None:
        return {"age_sec": info["age_sec"], "price": px, "above_pct": None,
                "below_pct": None, "rungs": []}
    total = sum(ladder.values())
    above = sum(v for b, v in ladder.items() if b > px)
    below = sum(v for b, v in ladder.items() if b < px)
    top5 = sorted(ladder.items(), key=lambda kv: kv[1], reverse=True)[:5]
    return {
        "age_sec": info["age_sec"],
        "price": px,
        "above_pct": round(above / total * 100, 1),
        "below_pct": round(below / total * 100, 1),
        "rungs": [{"price": b, "share_pct": round(v / total * 100, 2)}
                 for b, v in top5],
    }


def _on1_paper(path: Path, now: float) -> dict[str, Any] | None:
    """ON1 forward paper ledger (scripts/paper_on1.py, docs/PREREG_on1_forward.md).

    Guard levels are the PREREG §3 lines verbatim (p05 warn / p01 stop of the
    judged 1990-2026 net series, and the signed micro-vs-large friction stop).
    The values are duplicated here deliberately: the dashboard must render the
    frozen lines even if the ledger script changes, and a mismatch between the
    two is itself a bug worth seeing.
    """
    info = _file_info(path, now)
    if info is None:
        return None
    guards = {63: (-11.1, -22.4), 126: (-14.2, -42.5), 245: (-20.4, -51.1)}
    trades: list[dict[str, str]] = []
    try:
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return None
    trades = [r for r in rows if r.get("net_bps")]
    skipped = len(rows) - len(trades)
    if not trades:
        return {"trades": 0, "skipped": skipped, "age_sec": info["age_sec"]}
    net_bps = [float(r["net_bps"]) for r in trades]
    cum_yen = sum(float(r["net_yen"]) for r in trades)
    state = "OK"
    for win, (warn, stop) in guards.items():
        if len(net_bps) < win:
            continue
        cum_pct = sum(net_bps[-win:]) / 1e4 * 100
        if cum_pct < stop:
            state = "停止"
            break
        if cum_pct < warn:
            state = "警告"
    fr = [r for r in trades[-21:]
          if r.get("micro_minus_large_entry") and r.get("micro_minus_large_exit")]
    friction = None
    if len(fr) >= 15:
        friction = round(sum(float(r["micro_minus_large_exit"])
                             - float(r["micro_minus_large_entry"]) for r in fr) / len(fr), 1)
        if friction < -10.0 and state != "停止":
            state = "停止"
    return {
        "trades": len(trades),
        "skipped": skipped,
        "cum_net_yen": round(cum_yen),
        "mean_net_bps": round(sum(net_bps) / len(net_bps), 2),
        "last_exit_date": trades[-1].get("exit_date"),
        "guard": state,
        "friction_yen": friction,
        "age_sec": info["age_sec"],
    }


def _attention_gauge(path: Path, now: float) -> dict[str, Any] | None:
    """Crowd-heat gauge from data/attention/attention.csv (fetch_attention.py).

    Rolling-365-row z-scores of log levels — levels decay secularly (survey:
    EN median 8.3k in 2015 -> 3.1k in 2026) so a raw level is meaningless.
    Newest COMPLETE wp row is used (Wikipedia publishes at D-2).  Display only:
    direction-prediction from these series is a recorded no-go.
    """
    import math
    import statistics

    info = _file_info(path, now)
    if info is None:
        return None
    try:
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return None

    def z_of(key: str) -> tuple[float | None, str | None]:
        series = [(r["date"], math.log(float(r[key]) + 1.0))
                  for r in rows if r.get(key)]
        if len(series) < 400:
            return None, None
        window = [v for _, v in series[-366:-1]]
        mean, sd = statistics.fmean(window), statistics.stdev(window)
        if sd <= 0:
            return None, None
        return round((series[-1][1] - mean) / sd, 2), series[-1][0]

    z_ja, d_ja = z_of("wp_ja")
    z_en, _ = z_of("wp_en")
    z_gd, _ = z_of("gdelt_vol")
    fng_rows = [(r["date"], float(r["fng"])) for r in rows if r.get("fng")]
    fng = round(fng_rows[-1][1]) if fng_rows else None
    if z_ja is None and z_en is None and z_gd is None and fng is None:
        return None
    return {"z_wp_ja": z_ja, "z_wp_en": z_en, "z_gdelt": z_gd,
            "fng": fng, "asof": d_ja, "age_sec": info["age_sec"]}


def _attention_chart(path: Path) -> list[dict[str, Any]]:
    """Monthly series for the long-horizon chart: BTC close (last of month) +
    mean daily rolling-365 z per attention series.  ~135 points since 2015, so
    the payload stays tiny; recomputed only when the CSV changes (cached_scan).
    Display only — same no-signal caveat as the gauge.
    """
    import math
    import statistics

    def build() -> list[dict[str, Any]]:
        try:
            with path.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        except OSError:
            return []
        if len(rows) < 400:
            return []

        def z_series(key: str) -> dict[str, float]:
            pts = [(r["date"], math.log(float(r[key]) + 1.0))
                   for r in rows if r.get(key)]
            out: dict[str, float] = {}
            vals = [v for _, v in pts]
            for i in range(365, len(pts)):
                window = vals[i - 365:i]
                mean = statistics.fmean(window)
                sd = statistics.stdev(window)
                if sd > 0:
                    out[pts[i][0]] = (vals[i] - mean) / sd
            return out

        z = {k: z_series(k) for k in ("wp_ja", "wp_en", "gdelt_vol")}
        months: dict[str, dict[str, Any]] = {}
        for r in rows:
            day = r["date"]
            month = f"{day[:4]}-{day[4:6]}"
            slot = months.setdefault(month, {"m": month, "o": None, "h": None,
                                             "l": None, "c": None,
                                             "ja": [], "en": [], "gd": []})
            if r.get("btc_usd"):
                slot["c"] = float(r["btc_usd"])  # last close of the month wins
            if r.get("btc_open") and slot["o"] is None:
                slot["o"] = float(r["btc_open"])  # first open of the month
            if r.get("btc_high"):
                hi = float(r["btc_high"])
                slot["h"] = hi if slot["h"] is None else max(slot["h"], hi)
            if r.get("btc_low"):
                lo = float(r["btc_low"])
                slot["l"] = lo if slot["l"] is None else min(slot["l"], lo)
            for out_key, src_key in (("ja", "wp_ja"), ("en", "wp_en"),
                                     ("gd", "gdelt_vol")):
                if day in z[src_key]:
                    slot[out_key].append(z[src_key][day])
        series = []
        for month in sorted(months):
            slot = months[month]
            series.append({
                "m": month,
                "o": slot["o"], "h": slot["h"], "l": slot["l"], "c": slot["c"],
                "ja": round(statistics.fmean(slot["ja"]), 2) if slot["ja"] else None,
                "en": round(statistics.fmean(slot["en"]), 2) if slot["en"] else None,
                "gd": round(statistics.fmean(slot["gd"]), 2) if slot["gd"] else None,
            })
        return series

    return cached_scan("attention_chart", path, build) or []


def _percentile(values: list[float], q: float) -> float:
    """Nearest-rank percentile over an already-sorted-able list."""
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round(q * (len(ordered) - 1)))
    return ordered[max(0, min(idx, len(ordered) - 1))]


# A status.json older than this is a stopped or wedged bot, not a live reading.
STATUS_FRESH_SEC = 120.0


def _api_health(path: Path, now: float, status: dict,
                window_sec: float = 900.0,
                max_bytes: int = 512 * 1024) -> dict[str, Any] | None:
    """Latency/error picture of the bot's own API calls (data/api_health.csv).

    The file is a plain append of one line per call written best-effort by
    bot.exchange.resilience.ApiHealthRecorder, so parsing is line-tolerant: a
    torn or short line is skipped, never fatal. Falls back to the live fields
    in status.json when the CSV is missing — condition and health are known
    there too; only the percentiles need the file.

    status.json is only believed while it is FRESH (`STATUS_FRESH_SEC`). A
    crashed bot leaves its last status on disk forever, and the tile was
    reporting that "NORMAL" as the current state of the venue for as long as
    the file sat there. Once it is stale the CSV's last row is used instead and
    the payload carries `stale: True` so the dashboard can say so.
    """
    rows: list[tuple[float, float, str, str, str]] = []
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            f.seek(max(0, size - max_bytes))
            chunk = f.read().decode("utf-8", errors="replace")
    except OSError:
        chunk = ""
    cutoff = now - window_sec
    for line in chunk.splitlines():
        parts = line.split(",")
        if len(parts) < 7:
            continue
        try:
            ts = float(parts[0])
            latency = float(parts[3])
        except ValueError:
            continue          # header line or a torn append
        if ts < cutoff:
            continue
        rows.append((ts, latency, parts[4], parts[5], parts[6].strip()))
    updated_at = status.get("updated_at")
    try:
        fresh = updated_at is not None and (now - float(updated_at)) < STATUS_FRESH_SEC
    except (TypeError, ValueError):
        fresh = False
    live = status if fresh else {}
    if not rows and not status:
        return None
    if not rows:
        return {
            "p50_ms": None, "p95_ms": None, "error_rate": live.get("api_error_rate"),
            "samples": 0, "window_sec": window_sec,
            "condition": live.get("api_condition", "NORMAL"),
            "health": live.get("api_health_status"),
            "health_age_sec": live.get("api_health_age_sec"),
            "stale": not fresh,
        }
    latencies = [r[1] for r in rows]
    errors = sum(1 for r in rows if r[2] != "ok")
    last = rows[-1]
    return {
        "p50_ms": round(_percentile(latencies, 0.50), 1),
        "p95_ms": round(_percentile(latencies, 0.95), 1),
        "error_rate": round(errors / len(rows), 4),
        "samples": len(rows),
        "window_sec": window_sec,
        # The live monitor is authoritative for the level ONLY while status.json
        # is fresh; otherwise the CSV's last row is what actually happened.
        "condition": live.get("api_condition") or last[3],
        "health": live.get("api_health_status") or (last[4] or None),
        "health_age_sec": live.get("api_health_age_sec"),
        "stale": not fresh,
    }


def _bot_events(path: Path) -> list[dict[str, Any]]:
    """FILLED main-bot trades, paired entry->exit (market_view.parse_bot_events).

    Imported lazily: market_view reads `_tail_jsonl` from this module, so a
    top-level import here would be a cycle. Feeds the 決定 table and the chart
    markers, both of which only ever show the recent tail — the §5 CLOSED-trade
    COUNT is a separate, full-log read (bot.monitoring.gates.champion_gate,
    at judge_gates' own depth) precisely because this one is not.

    Memoised on the log's (mtime, size): the pairing reads a 4 MB tail and the
    console polls every 5 seconds, while the bot appends about once a minute.
    """
    from bot.monitoring.market_view import parse_bot_events

    return cached_scan("bot_events", path, lambda: parse_bot_events(path))


def _enrich_decisions(decisions: list[dict], events: list[dict]
                      ) -> list[dict[str, Any]]:
    """Decision rows plus JST times, Japanese labels and the trade they were.

    The pairing is done HERE rather than in the page: whether a filled order
    opened or closed a position is positional (a BUY with a short open is an
    exit), which the page cannot see from one row, and the realized P&L of an
    exit is a STEP in the cumulative ``PnL`` field — two facts that must be
    derived from the whole log or not at all.

    Rows that were not trades keep every field they had and gain the labels
    only; ``fill_price``/``realized_pnl_jpy`` stay None so the page renders an
    empty cell instead of a zero that looks like a flat trade.
    """
    by_ts: dict[float, list[dict]] = {}
    for event in events:
        ts = event.get("ts")
        if ts is not None:
            by_ts.setdefault(round(float(ts), 3), []).append(event)
    out: list[dict[str, Any]] = []
    for rec in decisions:
        row = dict(rec)
        row["time_jst"] = jst_label(rec.get("timestamp"))
        row["signal_ja"] = signal_ja(rec.get("strategy_signal"))
        row["decision_ja"] = decision_ja(rec.get("decision"))
        row["reason_ja"] = reason_ja(rec.get("reason"))
        row["trade_kind"] = None
        row["trade_side"] = None
        row["fill_price"] = None
        row["realized_pnl_jpy"] = None
        ts = parse_ts(rec.get("timestamp"))
        bucket = by_ts.get(round(ts, 3)) if ts is not None else None
        if bucket:
            event = bucket.pop(0)
            row["trade_kind"] = event.get("kind")
            row["trade_side"] = event.get("side")
            row["fill_price"] = event.get("price")
            if event.get("kind") == "exit":
                row["realized_pnl_jpy"] = event.get("pnl")
        out.append(row)
    return out


def _liveness(age_sec: float | None, warn_after: float, dead_after: float) -> str:
    if age_sec is None:
        return "missing"
    if age_sec < warn_after:
        return "ok"
    if age_sec < dead_after:
        return "warn"
    return "down"


def collect_status(root: str | Path = ".", now: float | None = None) -> dict[str, Any]:
    root = Path(root)
    now = now or time.time()

    status = _read_json(root / "logs" / "status.json") or {}
    kill = _read_json(root / "data" / "kill_switch.json")
    manual_kill = (root / "KILL").exists()

    bot_log = root / "logs" / "bot.jsonl"
    decisions = [d for d in _tail_jsonl(bot_log, 400)
                 if d.get("event") == "decision" or d.get("strategy_signal")]
    # Says what each recent decision row actually did (trade_kind/fill_price/
    # realized_pnl). The §5 champion gate below does its OWN full-log pairing
    # (bot.monitoring.gates.champion_gate) rather than reusing this tail.
    bot_events = _bot_events(bot_log)
    decisions = _enrich_decisions(decisions, bot_events)

    scalp_events = _tail_jsonl(root / "data" / "scalp_paper.jsonl", 400)
    scalp_trades = [e for e in scalp_events if e.get("event") == "exit"]
    scalp_pnl = round(sum(t.get("pnl_jpy", 0.0) for t in scalp_trades), 1)
    scalp_last = scalp_events[-1] if scalp_events else None

    ws_dir = root / "data" / "ws"
    ws_files = sorted(ws_dir.glob("*.jsonl.gz")) if ws_dir.exists() else []
    ws_latest = _file_info(ws_files[-1], now) if ws_files else None
    ws_total_bytes = sum(f.stat().st_size for f in ws_files) if ws_files else 0
    ws_total_mb = round(ws_total_bytes / 1e6, 1) if ws_files else 0.0

    oi_snapshot = _oi_snapshot(root / "data" / "oi_snapshots.csv", now)
    on1 = _on1_paper(root / "data" / "paper_on1" / "ledger.csv", now)
    attention = _attention_gauge(root / "data" / "attention" / "attention.csv", now)

    # 収集の鮮度: the newest daily shard each recorder wrote. data/tape names
    # carry the UTC day; data/venues (when it exists at all) is read by mtime.
    # Every entry degrades to None so an offline box renders 未収集, not an
    # error.
    tape = root / "data" / "tape"
    ingest = {
        "ticker": _ingest_latest(tape, "ticker_*.csv.gz", now),
        "board_top": _ingest_latest(tape, "board_top*.csv.gz", now),
        "venues": _ingest_latest(root / "data" / "venues", "*", now,
                                 dated=False),
    }

    # データ蓄積表 (§A1 dashboard reorg): データ / 最終更新 / サイズ / 目的.
    # Every entry is {"age_sec", "size"} or None so the existing "v ? ... :
    # 未収集" render keeps working unchanged; COLLECTOR_PURPOSE (dashboard.py
    # mirrors the same keys) supplies the 目的 text. ティッカー/板上位テープ
    # folds data/tape's two shard kinds into one row (freshest age, summed
    # size) — the underlying per-kind freshness stays available in ``ingest``.
    tape_entries = [e for e in (ingest["ticker"], ingest["board_top"]) if e]
    tape_row = ({"age_sec": min(e["age_sec"] for e in tape_entries),
                "size": sum(e.get("size") or 0 for e in tape_entries)}
               if tape_entries else None)
    ws_row = ({"age_sec": ws_latest["age_sec"], "size": ws_total_bytes}
             if ws_latest else None)
    venues_row = ingest["venues"]

    collectors = {
        "板記録 (WS)": ws_row,
        "ティッカー/板上位テープ": tape_row,
        "venues (bitbank/GMO/bF現物)": venues_row,
        "OIスナップショット (+価格)": oi_snapshot,
        "注目系列": _file_info(root / "data" / "attention" / "attention.csv", now),
        "JPX日報": _file_info(root / "data" / "jpx_daily" / "nk225_sessions.csv", now),
        "bitFlyer candles": _file_info(root / "data" / "candles_FX_BTC_JPY.csv", now),
        "Binance日次": _file_info(root / "data" / "binance_daily" / "metrics.csv", now),
        "USDJPY": _file_info(root / "data" / "binance_daily" / "usdjpy.csv", now),
        "Binance 1m": _file_info(root / "data" / "binance_BTCUSDT_1m.csv", now),
        "bitbank 1m": _file_info(root / "data" / "bitbank_xrp_jpy_1m.csv", now),
        "spread record": _file_info(root / "data" / "spread_FX_BTC_JPY.csv", now),
    }

    bot_age = (now - status["updated_at"]) if status.get("updated_at") else None
    scalp_age = (now - scalp_last["ts"]) if scalp_last else None
    ws_age = ws_latest["age_sec"] if ws_latest else None

    return {
        "generated_at": now,
        "components": {
            "main_bot": {
                "state": ("killed" if (kill or manual_kill) else
                          _liveness(bot_age, 30, 120)),
                "age_sec": round(bot_age, 1) if bot_age is not None else None,
            },
            # retired 2026-08-21 after the formal paper rejection (report
            # #16, -3.83bps vs the +5bps bar); start_all no longer launches
            # it. The pill stays as a record, not a liveness signal.
            "scalper": {
                "state": "retired",
                "age_sec": round(scalp_age, 1) if scalp_age is not None else None,
            },
            "ws_recorder": {"state": _liveness(ws_age, 300, 1200),
                            "age_sec": ws_age},
        },
        "bot": status,
        # Composite telemetry, surfaced beside the bot block instead of buried
        # in it. Both stay None under a strategy that has no overlay / no
        # module framework (xborder_momentum), which is not the same as an
        # overlay sitting at full size or an empty enabled-module list.
        "overlay": status.get("overlay"),
        "active_modules": status.get("active_modules"),
        # Execution resilience: how bitFlyer is actually answering us right
        # now, and how it answered over the last 15 minutes. This is the tile
        # that would have shown the 2019 failure mode while it was happening.
        "api_health": _api_health(root / "data" / "api_health.csv", now, status),
        "kill_switch": kill,
        "manual_kill_file": manual_kill,
        "decisions": decisions[-30:][::-1],
        "scalp": {
            "trades": len(scalp_trades),
            "total_pnl_jpy": scalp_pnl,
            "recent": scalp_events[-30:][::-1],
        },
        "ws": {"files": len(ws_files), "total_mb": ws_total_mb, "latest": ws_latest},
        "collectors": collectors,
        "ingest": ingest,
        # storm radar: the one adopted precursor (scripts/research_storm_b.py
        # G3, 12:30-15:00 UTC, lift 2.23) — armed windows are when the
        # scalper runs its lowered entry threshold
        "radar": StormRadar().state(now),
        "oi_snapshot": oi_snapshot,
        # ON1 forward paper tracking (Nikkei micro overnight; report #36,
        # PREREG_on1_forward.md). None until the first ledger is built.
        "on1": on1,
        # Crowd-heat gauge (attention z-scores; display only, no signal --
        # direction-prediction from these series is a recorded no-go).
        "attention": attention,
        # Long-horizon monthly chart: BTC close + attention z (display only).
        "attention_chart": _attention_chart(root / "data" / "attention" / "attention.csv"),
        # Pending COVERAGE gates (docs/KNOWLEDGE.md §4/§5) with the bars
        # scripts/judge_gates.py judges against, so the console can show how
        # far off each pre-registered sample still is. Progress and ETA only —
        # nothing here decides anything. ``purpose`` is display-only text
        # (GATE_PURPOSE above) — the bar/verdict fields judge_gates shares
        # with this module are untouched.
        "gates": [dict(g, purpose=GATE_PURPOSE.get(g["key"], ""))
                 for g in collect_gates(root, now, ws_files)],
        # S12 clock-burst-30m status tile (scripts/research_clock_burst.py
        # --status-json): n / fresh period / last day only, written by
        # fetch_all.bat daily. None until the first run writes the file — the
        # n<30 safety valve on the full report is a separate concern and
        # still applies; this payload never carries a statistic either way.
        "s12": _read_json(root / "data" / "s12_status.json"),
        # 推定建値台帳 (scripts/research_position_ladder.py:build_ladder,
        # imported by identity — see _ladder_module). Display/monitoring
        # only: G6 phase-C study pending (KNOWLEDGE §4), no signal adopted.
        "ladder": _position_ladder(root / "data" / "oi_snapshots.csv", now),
    }
