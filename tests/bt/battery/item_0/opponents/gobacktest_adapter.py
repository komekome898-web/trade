"""Survey candidate 69 `gobacktest` (GitHub `dirkolbrich/gobacktest`, commit
719cff68; Go), built here with `go build` (install record
`survey_results/attempts/69.log`) and driven through a small Go driver against
its public API (`c69_driver` in the venv `c69`'s `bin/`; source in the
install record): `Backtest.SetData / SetStrategy / SetPortfolio / SetExchange
/ Run`, `Data.SetStream` (the stream is handed in the scene's order; the CSV
loader would `SortStream` by time then symbol), `Bar` and `Tick` data events,
a `StrategyHandler` whose `OnData(event)` records what it receives and
returns a buy `Signal` when the scene says, `Size`, `CommissionHandler`
(`Exchange.Commission`), `PortfolioHandler` (the tool's `Portfolio` wrapped
to print each fill handed to it).

What the tool is: an event loop over data events (`Bar`: OHLCV with an
int64 volume; `Tick`: bid / ask quote) -> strategy -> `Signal` (a direction
only) -> portfolio sizes it into a market `Order` -> the exchange fills it at
the latest price. Time is Go's `time.Time` (nanoseconds). There is no trade,
book, funding or liquidation type, no timer, no latency, no limit order or
cancel for the strategy, and the strategy is not told of fills.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

EXE = str(Path(sys.prefix) / "bin" / "c69_driver")
TYPE = {"*gobacktest.Bar": "bar", "*gobacktest.Tick": "tick"}
NO_TYPE = "この道具の相場の事象の型は Bar(OHLCV)と Tick(買い気配と売り気配)の 2 つで、{k} を渡す口が無い"


_GO = "go:github.com/dirkolbrich/gobacktest"


def _settings(payload: dict) -> None:
    """Round r8-1 (positive definition A (1)): the settings the driver (survey_results/attempts/69.log, func main)
    makes through the tool's public Go API, recorded in its order."""
    if payload.get("mode") == "csv":
        C.configure_compiled(f"{_GO}/data.(*BarEventFromCSVFile).Load", what="BarEventFromCSVFile{FileDir}.Load([X])",
                             decided_from=("場面の入力",))
        return
    scene = ("場面の入力",)
    C.configure_compiled(f"{_GO}.(*Data).SetStream", what="Data.SetStream(場面の足)", decided_from=scene)
    C.configure_compiled(f"{_GO}.New", what="gobacktest.New()", decided_from=("公開の既定",))
    C.configure_compiled(f"{_GO}.(*Backtest).SetSymbols", what="SetSymbols([X])", decided_from=scene)
    C.configure_compiled(f"{_GO}.(*Backtest).SetData", what="SetData(data)", decided_from=scene)
    C.configure_compiled(f"{_GO}.(*Portfolio).SetSizeManager",
                         what=f"NewPortfolio().SetSizeManager(Size{{DefaultSize: {payload.get('qty', 1)}, DefaultValue: MaxFloat64}})",
                         decided_from=scene)
    C.configure_compiled(f"{_GO}.(*Backtest).SetPortfolio",
                         what="SetPortfolio(" + ("場面の口座(Portfolio を包む)" if payload.get("plug") == "account" else "Portfolio") + ")",
                         decided_from=scene)
    C.configure_compiled(f"{_GO}.(*Backtest).SetExchange",
                         what="SetExchange(NewExchange()" + (", Commission = 場面の費用の模型" if payload.get("plug") in ("cost05", "cost0375unit") else "")
                              + ")", decided_from=scene)
    C.configure_compiled(f"{_GO}.(*Backtest).SetStrategy", what="SetStrategy(場面の戦略 = NewStrategy の子, SetChildren(NewAsset(X)))",
                         decided_from=scene)


def drv(payload: dict) -> list[dict]:
    _settings(payload)
    r = subprocess.run([EXE], input=json.dumps(payload), capture_output=True, text=True, timeout=60)
    return [json.loads(ln) for ln in r.stdout.splitlines() if ln.startswith("{")]


def bar(e: dict) -> dict:
    b = C.as_bar(e)
    return C.substitute(b, "bar", open=float(b["open"]), high=float(b["high"]), low=float(b["low"]), close=float(b["close"]), volume=float(b.get("volume", 100.0)))


def seq(rows) -> list:
    return [[TYPE.get(r["ev"], r["ev"]), int(r["ts"])] for r in rows if "ev" in r]


def carriers(rows) -> list:
    """The Go type of each event OnData received, printed by the driver with %T from the event itself."""
    return [C.compiled(f"go:{r['ev']}") for r in rows if "ev" in r]


class GobacktestAdapter(Adapter):
    # round r8-1 (positive definition A): one configured target (the driver uses the tool's defaults)
    CONFIGS = {"": {"exchange": "NewExchange()", "portfolio": "NewPortfolio()"}}
    name = "opp_gobacktest"

    # ---------------- P0-1
    def scene_p1_one_call_per_event(self, sc):
        rows = drv({"events": [bar(e) for e in C.events(sc)]})
        return ok({"sequence": seq(rows)}, "足を Bar にして Data.SetStream、OnData の各回に (事象の型, Time().UnixNano())",
                  {"carriers": carriers(rows)})

    def scene_p1_merge_by_time(self, sc):
        return not_supported(NO_TYPE.format(k="約定と資金調達") + "(入力も Data の 1 本の流れ)")

    def scene_p1_typed_events(self, sc):
        evs = []
        for e in C.events(sc):
            evs.append(bar(e) if e["kind"] == "bar" else {"kind": "tick", "ts_ns": int(e["ts_ns"]), "bid": float(e["price"]), "ask": float(e["price"])})
        rows = drv({"events": evs})
        return ok({"sequence": seq(rows)}, "足は Bar、約定は約定の型が無いので Tick(買い気配 = 売り気配 = 約定の値)で渡し、OnData が受けた型と時刻",
                  {"carriers": carriers(rows)})

    # ---------------- P0-2
    def _iso(self, sc):
        with tempfile.TemporaryDirectory(dir=os.environ.get("BT_SCRATCH") or None) as d:
            Path(d, "X.csv").write_text(f"Date,Open,High,Low,Close,Adj Close,Volume\n{sc.input['iso']},1,1,1,1,1,1\n", encoding="utf-8")
            out = drv({"mode": "csv", "dir": d + "/"})
        r = out[0] if out else {}
        return ok(r.get("times", [None])[0] if r.get("times") else None,
                  "道具の CSV の読み込み(data.BarEventFromCSVFile、data/data-csv.go は Date を time.Parse(\"2006-01-02\") で読む)に ISO の日付を 1 行書いて Load。"
                  f"読めた行の時刻 {r.get('times')}、Load の誤り '{r.get('csv_error')}'(読めない行は誤りを返さずに捨てる)",
                  {"reader": C.compiled("go:github.com/dirkolbrich/gobacktest/data.BarEventFromCSVFile.Load")})

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    # ---------------- P0-2 unit scenes (round r16-1): no entry that reads a time in a unit
    def _units(self, sc):
        return C.unit_time(sc, [], tried='時刻を読む入口は CSV の Date の欄だけ(data/data-csv.go、time.Parse("2006-01-02"))' + '(r16-1 の場面係が道具の配布物を fromtimestamp・unit=・timestamp_to_datetime・datetime64[s/ms/us]・/1000・*1000・epoch で検索した範囲。記録 survey_results/attempts/r16-1_unit_entries.txt)' + "。" + C.iso_entry_tried(self._iso, sc))

    scene_p2_s_text = scene_p2_s_text_subns = scene_p2_s_int = scene_p2_s_float_held = scene_p2_s_float_subns = \
        scene_p2_ms_text = scene_p2_ms_text_subns = scene_p2_ms_int = scene_p2_ms_float_held = scene_p2_ms_float_subns = \
        scene_p2_us_text = scene_p2_us_text_subns = scene_p2_us_int = scene_p2_us_float_held = _units  # round r16-1

    def _obs(self, sc):
        evs = [C.substitute(e, "bar", open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0)
               for e in C.events(sc)]
        rows = drv({"events": evs})
        return ok({"observed_ts_ns": [t for _, t in seq(rows)]}, "Bar の時刻(time.Time)で渡し、OnData の event.Time().UnixNano()",
                  {"carriers": carriers(rows)})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _obs

    # ---------------- P0-3
    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NO_TYPE.format(k=e["kind"]))
        rows = [r for r in drv({"events": [bar(e)]}) if "ev" in r]
        f = rows[0] if rows else {}
        return ok({"sequence": seq(rows), "fields": {k: (float(f[k]) if k in f else None) for k in ("open", "high", "low", "close", "volume")}},
                  "足 1 本を Bar で渡した。OnData が受けた Bar の型・時刻と欄(Open / High / Low / Close / Volume。Volume は int64)",
                  {"carriers": carriers(rows)})

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        return not_supported(NO_TYPE.format(k="約定・板の写真・板の差分・資金調達・清算"))

    def scene_p3_clock_timer(self, sc):
        return not_supported("戦略を頼んだ時刻に呼ぶ口が無い(OnData はデータの事象ごとだけ)")

    def _notice(self, sc):
        return not_supported("注文の受付・拒否・約定を戦略に知らせる口が無い(約定は Exchange -> Portfolio.OnFill に渡り、StrategyHandler に知らせの口が無い)")

    scene_p3_notice_accepted = scene_p3_notice_rejected = scene_p3_notice_filled = _notice

    # ---------------- P0-4
    def scene_p4_visible_at_step(self, sc):
        rows = drv({"events": [bar(e) for e in C.events(sc)], "probe": sc.input["probe_at_ns"]})
        v = next((r for r in rows if "visible_count" in r), None)
        if v is None:
            return not_supported("T0 + 4 日の呼び出しが無かった")
        reads = C.Reads()
        reads.read("go:Data().History() の Price()(driver が T0 + 4 日の OnData で読んだ列)", lambda: v["visible_closes"],
                   of=C.compiled("go:github.com/dirkolbrich/gobacktest.Data.History"))
        return ok(reads.output(), "T0 + 4 日の OnData で、戦略の Data().History() の件数と Price() の最大", reads.provenance())

    def scene_p4_received_time(self, sc):
        return not_supported("事象に受け取れる時刻を持たせる口が無い(Bar / Tick の時刻は Time() の 1 つ)")

    def scene_p4_future_read_attempt(self, sc):
        rows = drv({"events": [bar(e) for e in C.events(sc)], "probe": sc.input["probe_at_ns"]})
        att = C.Attempts()
        for r in rows:
            if "read" not in r:
                continue
            # round r6-2: recorded through common.Attempts.compiled (the driver's read of the tool's DataHandler)
            base = (r["read"], r["form"], r.get("shape", "other"), r.get("naming", "other"), "go:github.com/dirkolbrich/gobacktest.Data")
            if r.get("expressible") is False:  # a Go slice has no step: a strategy cannot write this naming
                att.compiled(*base, message="Go の区間に歩幅は無く書けない", expressible=False)
            elif "error" in r:
                att.compiled(*base, raised="panic", message=r["error"])
            else:
                att.compiled(*base, returned=r["value"])
        if not att.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった")
        return ok(att.output(), "T0 + 4 日の OnData で試した(戦略の Data() は DataHandler で、Stream() はまだ流れていない事象の列を返す): " + att.summary())

    # ---------------- P0-5
    def scene_p5_same_time_twice(self, sc):
        return not_supported(NO_TYPE.format(k="約定・資金調達・清算"))

    scene_p5_hand_over_order = scene_p5_same_time_twice

    def scene_p5_same_stream_order(self, sc):
        rows = drv({"events": [bar(e) for e in C.events(sc)]})
        return ok({"prices": [float(r["price"]) for r in rows if "ev" in r]}, "同じ時刻の 3 本を Bar にして Data.SetStream(並べ替えない)、OnData の Price() の順",
                  {"carriers": carriers(rows)})

    # ---------------- P0-6
    def scene_p6_place_then_cancel(self, sc):
        return not_supported("戦略が出すのは向き(BOT / SLD)だけの Signal で、指値の注文・取消・未決の注文の読み出しの口が無い"
                             "(Portfolio.OnSignal が成行の Order を作る、portfolio.go)")

    scene_p6_cancel_notice = scene_p6_place_then_cancel

    def scene_p6_fill_seen_by_strategy(self, sc):
        rows = drv({"events": [bar(e) for e in C.events(sc)], "buy_at": 1, "read_at": 3})
        r = next((x for x in rows if "read_at" in x), None)
        import re
        m = re.search(r"qty:(-?\d+)", (r or {}).get("position", ""))
        return ok({"filled_qty_at_call3": float(m.group(1)) if m else None},
                  "1 回目に買いの Signal(Size の既定の数量 1)、3 回目に Portfolio.IsInvested('X') の建玉の数量(注文から約定済み数量を読む口は無い)。"
                  f"{r}")

    # ---------------- P0-7
    def scene_p7_fill_model_swap(self, sc):
        return not_supported("約定の模型の口(Backtest.SetExchange の ExecutionHandler)はあるが、包みの外からは約定の値を決められない: Fill の値の欄 price は"
                             "非公開で、公開の setter は SetDirection と SetQty だけ(fill.go)。試したこと: 包みの外に OnOrder で f.SetPrice(12345.0) を呼ぶ "
                             "ExecutionHandler を書いて go build -> f.SetPrice undefined (type *gobacktest.Fill has no field or method SetPrice)(導入の記録)")

    def scene_p7_latency_model_swap(self, sc):
        return not_supported("遅延の模型の口が無い(Exchange.OnOrder は注文をその場で最新の値で埋める、execution.go)")

    def _fee(self, sc, plug, qty):
        rows = drv({"events": [bar(e) for e in C.events(sc)], "buy_at": 1, "plug": plug, "qty": qty})
        f = [r for r in rows if "fill_qty" in r]
        return ok({"fee": sum(float(r["commission"]) for r in f) if f else None},
                  f"Exchange.Commission に CommissionHandler(Calculate(qty, price))を差し込み、1 回目に買いの Signal(数量 {qty})。Fill.Commission() の合計。{f}")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, "cost05", 1)

    def scene_p7_cost_per_unit(self, sc):
        return self._fee(sc, "cost0375unit", 2)

    def scene_p7_account_swap(self, sc):
        rows = drv({"events": [bar(e) for e in C.events(sc)], "buy_at": 1, "plug": "account"})
        return ok({"account_recorded_fill_qty": [float(r["fill_qty"]) for r in rows if r.get("account")]},
                  "Backtest.SetPortfolio に、道具の Portfolio を包んで OnFill で受けた約定の数量を記録する PortfolioHandler を差し込んだ")
