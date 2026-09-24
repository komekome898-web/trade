"""Survey candidate 70 `PineForge` (C++ engine with a C ABI; built here with its
own CMake, core only -- install record `survey_results/attempts/70.log`),
driven through a small C driver against the native C API
(`include/pineforge/native_c_api.h`): `strategy_native_host_create_v1`
(a callback table: `on_run_begin`, `on_bar`, `on_applied`,
`on_execution_terms`), `strategy_configure_native_v1` (the run spec: clock,
instrument, account, fee kind and value), `strategy_native_run_v1` (the bars),
and from inside the callbacks `strategy_native_submit_v1`, `_cancel_v1`,
`_working_len_v1`, `_position_v1`, `_events_v1`, `_series_bar_v1`,
`_partial_bar_v1`, `_declare_subscriptions_v1`. The driver (`c70_driver`,
source in the install record) sits in the venv `c70`'s `bin/`.

What the tool is: a bar-driven strategy kernel. The only market input is the
OHLCV bar (`pf_bar_t`, time = the bar's open in Unix milliseconds); requests
submitted in a bar's callback are matched from the next eligible point on;
the kernel keeps an append-only event history (accepted / rejected /
cancelled / applied ...) the strategy may read; settlement price, fee kind
(percent / cash per unit / cash per execution) and margin rules are
pluggable. There is no trade, book, funding, liquidation or timer input
type, and no order latency model.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

EXE = str(Path(sys.prefix) / "bin" / "c70_driver")
NO_TYPE = ("この道具の相場の入力は足(pf_bar_t: 始値・高値・安値・終値・出来高・時刻)の 1 種で、{k} を渡す口が無い"
           "(約定の型 pf_trade_tick_t は Pine の台本を流す stream の口 strategy_stream_push_tick の入力で、足の出来高に足し込まれる)")
MS = 1_000_000


_CHOSEN = {"tf": "1D"}  # the configured target's chosen time frame (round r8-1); set by the adapter


def _settings(opts) -> None:
    """Round r8-1 (positive definition A (1)): the settings the driver (survey_results/attempts/70.log, int main)
    makes through the tool's public C API, recorded in its order."""
    kv_ = dict(o.split("=", 1) for o in opts if "=" in o and not o.startswith("sub="))
    subs = [o[4:] for o in opts if o.startswith("sub=")]
    C.configure_compiled("c:pineforge strategy_native_host_create_v1", what="strategy_native_host_create_v1(利用者の callbacks)",
                         decided_from=("場面の入力",))
    for sub in subs:
        C.configure_compiled("c:pineforge pf_native_subscription_v1", what=f"subscription(時間枠:lookahead = {sub})",
                             decided_from=("場面の入力",))
    scene_keys = sorted(k for k in kv_ if k in ("capital", "fee_kind", "fee_value", "margin", "terms"))
    C.configure_compiled("c:pineforge strategy_configure_native_v1",
                         what=f"strategy_configure_native_v1(input_tf = script_tf = {kv_.get('tf', '1D')}, ticker X, crypto, JPY, UTC, 24x7, "
                              f"price_tick 0.01, close_execution NEXT_ELIGIBLE_POINT{', ' + ', '.join(scene_keys) if scene_keys else ''})",
                         decided_from=("選ぶ値", "場面の入力") if scene_keys else ("選ぶ値",))
    C.configure_compiled("c:pineforge strategy_native_run_v1", what="strategy_native_run_v1(場面の足)", decided_from=("場面の入力",))


def drv(*opts, bars) -> list[list[str]]:
    opts = tuple(o for o in map(str, opts) if not o.startswith("tf=")) + (f"tf={_CHOSEN['tf']}",)
    _settings(opts)
    r = subprocess.run([EXE, *map(str, opts), "--", *bars], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"c70_driver rc={r.returncode} {r.stderr[:200]}")
    return [ln.split() for ln in r.stdout.splitlines() if ln.strip()]


def kv(row: list[str]) -> dict:
    return dict(x.split("=", 1) for x in row if "=" in x)


def bar_arg(e: dict) -> str:
    """ts_ns -> the tool's Unix milliseconds (floor; a sub-millisecond part is lost -- the tool's type)."""
    b = C.as_bar(e)
    return (f"{int(b['ts_ns']) // MS}:{float(b['open'])}:{float(b['high'])}:{float(b['low'])}:{float(b['close'])}:"
            f"{float(b.get('volume', 1.0) or 1.0)}")


def calls(rows) -> list[list[str]]:
    return [r for r in rows if r[0] == "CALL"]


# what the driver's on_bar callback receives: the tool's own struct (include/pineforge/native_c_api.h), one per call
BAR_CARRIER = "c:pineforge pf_bar_t (on_bar の引数)"


def carriers(rows) -> list[str]:
    return [C.compiled(BAR_CARRIER) for _ in calls(rows)]


def errors(rows) -> list[str]:
    return [" ".join(r) for r in rows if r[0] == "ERROR"]


class PineforgeAdapter(Adapter):
    # round r8-1 (positive definition A): the time frame is a value the user chooses; each value is its own configured
    # target, the same in every scene (until round r8-1 the ns-time scenes ran with 1S and the others with 1D)
    CONFIGS = {"tf=1D": {"tf": "1D"}, "tf=1S": {"tf": "1S"}}

    def __init__(self, config: str = "tf=1D") -> None:
        super().__init__(config or "tf=1D")
        _CHOSEN["tf"] = self.choose["tf"]
    name = "opp_pineforge"

    # ---------------- P0-1
    def scene_p1_one_call_per_event(self, sc):
        rows = drv(bars=[bar_arg(e) for e in C.events(sc)])
        return ok({"sequence": [["bar", int(r[2]) * MS] for r in calls(rows)]},
                  "足を pf_bar_t にして strategy_native_run_v1、on_bar の各回に (道具の型 = 足, bar.timestamp の ms を ns に)。"
                  f"誤り {errors(rows)}", {"carriers": carriers(rows)})

    def scene_p1_merge_by_time(self, sc):
        return not_supported(NO_TYPE.format(k="約定と資金調達"))

    def scene_p1_typed_events(self, sc):
        return not_supported(NO_TYPE.format(k="約定"))

    # ---------------- P0-2
    def _iso(self, sc):
        return not_supported("日時の文字列を読む口が無い(時刻は pf_bar_t.timestamp の Unix ミリ秒の整数。道具の CSV の読み込み "
                             "tools/aggregate_feed.cpp も timestamp の欄を整数で読む)")

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _obs(self, sc):
        evs = [{"kind": "bar", "ts_ns": e["ts_ns"], "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 1.0}
               for e in C.events(sc)]
        rows = drv(bars=[bar_arg(e) for e in evs])
        if errors(rows):
            return not_supported("時刻の型が Unix ミリ秒(pf_bar_t.timestamp、int64)で、ns を持てない。ミリ秒に切り下げて渡した足を道具が拒否した"
                                 f"(入力の時間枠 {_CHOSEN['tf']}): {errors(rows)}")
        return ok({"observed_ts_ns": [int(r[2]) * MS for r in calls(rows)]},
                  "足の時刻は Unix ミリ秒(pf_bar_t.timestamp、int64)。ns の時刻をミリ秒に切り下げて渡し、on_bar の bar.timestamp を ns に戻した"
                  f"(入力の時間枠 {_CHOSEN['tf']})。誤り {errors(rows)}", {"carriers": carriers(rows)})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _obs

    # ---------------- P0-3
    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NO_TYPE.format(k=e["kind"]))
        rows = drv(bars=[bar_arg(e)])
        c = calls(rows)
        f = dict(zip(("close", "eff", "open", "high", "low", "volume"), c[0][3:])) if c else {}
        return ok({"sequence": [["bar", int(r[2]) * MS] for r in c],
                   "fields": {k: float(f[k]) if k in f else None for k in ("open", "high", "low", "close", "volume")}},
                  "足 1 本を pf_bar_t で渡し、on_bar が受けた型・時刻と欄(open / high / low / close / volume)", {"carriers": carriers(rows)})

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        return not_supported(NO_TYPE.format(k="約定・板の写真・板の差分・資金調達・清算"))

    def scene_p3_clock_timer(self, sc):
        return not_supported("戦略が時刻を頼んで起こされる口が無い(呼び出しは足ごとの on_bar / on_bar_open / on_tick と、宣言した上位の時間枠の "
                             "on_timeframe_bar。時刻を指定する口は無い)")

    def _orders(self, sc, *opts):
        return drv(*opts, bars=[bar_arg(e) for e in C.events(sc)])

    @staticmethod
    def _notices(rows):
        # the kernel's event kinds: ACCEPTED, REJECTED (at submit), MATCH_REJECTED (refused when matched), CANCELLED, APPLIED
        name = {"match_rejected": "rejected"}
        return [name.get(r[2], r[2]) for r in rows if r[0] == "NOTICE"]

    def scene_p3_notice_accepted(self, sc):
        rows = self._orders(sc, "buy_at=1", "order=limit90")
        return ok({"notices": [n for n in self._notices(rows) if n != "applied"] + (["filled"] if "applied" in self._notices(rows) else [])},
                  "1 回目の on_bar で指値 買い 1 @90(strategy_native_submit_v1)。戦略は各回の on_bar の中で strategy_native_events_v1 を読み、"
                  f"受付・拒否・取消・約定の事象を記録した。driver の出力 {[' '.join(r) for r in rows if r[0] in ('SUBMIT', 'NOTICE')]}")

    def scene_p3_notice_rejected(self, sc):
        rows = self._orders(sc, "buy_at=1", "capital=1000", "margin=1")
        ns = self._notices(rows)
        return ok({"notices": [n for n in ns if n != "applied"] + (["filled"] if "applied" in ns else [])},
                  "run spec の initial_capital = 1000、initial_margin_fraction = 1(レバレッジ無し)、1 回目に成行 買い 1。戦略が各回の on_bar の中で "
                  "strategy_native_events_v1 から読んだ事象(MATCH_REJECTED = 照合の時点の拒否を rejected に数えた)。"
                  f"driver の出力 {[' '.join(r) for r in rows if r[0] in ('SUBMIT', 'NOTICE', 'APPLIED', 'ERROR')]}")

    def scene_p3_notice_filled(self, sc):
        rows = self._orders(sc, "buy_at=1")
        ap = [kv(r) for r in rows if r[0] == "APPLIED"]
        return ok({"filled_qty_in_notices": sum(float(a["opened"]) for a in ap)},
                  "1 回目に成行 買い 1。戦略の on_applied(約定の知らせ)が受けた opened_units の合計。"
                  f"driver の出力 {[' '.join(r) for r in rows if r[0] in ('SUBMIT', 'APPLIED')]}")

    # ---------------- P0-4
    def scene_p4_visible_at_step(self, sc):
        return not_supported("戦略が過去の足を読む口が無い(on_bar に渡るのは今の足 1 本。strategy_native_series_bar_v1 は宣言した時間枠の最新の 1 本、"
                             "partial_bar は今の足の途中。過去の件数と最大の終値は、戦略が自分で覚える以外に読めない)")

    def scene_p4_received_time(self, sc):
        return not_supported("事象に受け取れる時刻を持たせる口が無い(pf_bar_t の時刻は 1 つ)")

    def scene_p4_future_read_attempt(self, sc):
        probe_ms = int(sc.input["probe_at_ns"]) // MS
        rows = drv(f"probe={probe_ms}", "sub=2D:1", "sub=2D:0", "sub=1W:1", bars=[bar_arg(e) for e in C.events(sc)])
        att = C.Attempts()
        for r in rows:
            if r[0] == "SERIES":
                d = kv(r)
                la = "AT_FIRST_INPUT(区間の最後の値を最初の入力で渡す)" if d["lookahead"] == "1" else "AT_COMPLETION"
                # takes no time and no position: it returns the declared timeframe's bar that holds now (and, with
                # lookahead, its last value) -- a call that returns the bar reaching past now (shape next_call)
                att.run(f"strategy_native_series_bar_v1(時間枠 {d['tf']}、lookahead = {la}。5 本目を含む区間)", "position",
                        lambda d=d: None if d["rc"] != "0" else {"timestamp_ms": int(d["ts"]), "close": float(d["close"])},
                        via=C.compiled("c:pineforge strategy_native_series_bar_v1"),
                        shape="next_call", naming="next")
            if r[0] == "PARTIAL":
                d = kv(r)
                att.run("strategy_native_partial_bar_v1(今の足の途中)", "other",
                        lambda d=d: None if d["rc"] != "0" else {"timestamp_ms": int(d["ts"]), "close": float(d["close"])},
                        via=C.compiled("c:pineforge strategy_native_partial_bar_v1"))
        if not att.items:
            return not_supported(f"T0 + 4 日の呼び出しが無かった。driver の出力 {rows[:6]}")
        return ok(att.output(), "T0 + 4 日の on_bar の中で試した(on_run_begin で上位の時間枠を宣言。位置で次を読む口は無い): " + att.summary())

    # ---------------- P0-5
    def scene_p5_same_time_twice(self, sc):
        return not_supported(NO_TYPE.format(k="約定・資金調達・清算"))

    scene_p5_hand_over_order = scene_p5_same_time_twice

    def scene_p5_same_stream_order(self, sc):
        rows = drv(bars=[bar_arg(e) for e in C.events(sc)])
        if errors(rows):
            return not_supported(f"同じ時刻の足を 2 本以上受けない(道具が拒否した): 同じ時刻の 3 本を足にして strategy_native_run_v1 -> {errors(rows)}")
        return ok({"prices": [float(r[3]) for r in calls(rows)]},
                  f"同じ時刻の 3 本を足にして渡し、on_bar の終値の順。誤り {errors(rows)}", {"carriers": carriers(rows)})

    # ---------------- P0-6
    def scene_p6_place_then_cancel(self, sc):
        rows = self._orders(sc, "buy_at=1", "order=limit90", "cancel_at=2")
        w = {int(r[1]): int(r[2]) for r in rows if r[0] == "WORKING"}
        return ok({"open_at_call2": w.get(2), "open_at_call3": w.get(3)},
                  "1 回目に指値 買い 1 @90、2 回目に strategy_native_working_len_v1 を読んでから strategy_native_cancel_v1、3 回目に working_len。"
                  f"driver の出力 {[' '.join(r) for r in rows if r[0] in ('SUBMIT', 'WORKING', 'CANCEL', 'NOTICE')]}")

    def scene_p6_cancel_notice(self, sc):
        rows = self._orders(sc, "buy_at=1", "order=limit90", "cancel_at=2")
        return ok({"cancel_notice_received": "cancelled" in self._notices(rows)},
                  "p6-place-then-cancel と同じ流れで、戦略が各回の on_bar の中で strategy_native_events_v1 から読んだ事象。"
                  f"{[' '.join(r) for r in rows if r[0] in ('CANCEL', 'NOTICE')]}")

    def scene_p6_fill_seen_by_strategy(self, sc):
        rows = self._orders(sc, "buy_at=1", "read_at=3")
        p = next((kv(r) for r in rows if r[0] == "POS"), None)
        return ok({"filled_qty_at_call3": float(p["units"]) if p and p.get("rc") == "0" else None},
                  "1 回目に成行 買い 1、3 回目に strategy_native_position_v1 の建玉の数量(注文ごとの約定済み数量は on_applied の知らせで渡る)。"
                  f"driver の出力 {[' '.join(r) for r in rows if r[0] in ('SUBMIT', 'APPLIED', 'POS')]}")

    # ---------------- P0-7
    def scene_p7_fill_model_swap(self, sc):
        rows = self._orders(sc, "buy_at=1", "capital=100000", "terms=12345")
        a = next((kv(r) for r in rows if r[0] == "APPLIED"), None)
        return ok({"fill_price": float(a["price"]) if a else None},
                  "callbacks.on_execution_terms(約定の値を決める口。既定以外を返すと out の resolved_price で決まる)に 12345.0 を返す関数、"
                  f"1 回目に成行 買い 1。on_applied の resolved_price。{[' '.join(r) for r in rows if r[0] in ('SUBMIT', 'APPLIED', 'NOTICE', 'ERROR')]}")

    def scene_p7_latency_model_swap(self, sc):
        return not_supported("遅延の模型の口が無い(注文は出した足の次の約定できる点から照合される。run spec と callbacks に遅延の欄・口が無い、native_c_api.h)")

    def _fee(self, sc, kind: int, value: float, qty: int, what: str):
        rows = self._orders(sc, "buy_at=1", "capital=100000", f"fee_kind={kind}", f"fee_value={value}", f"qty={qty}", "read_at=3")
        lots = [kv(r) for r in rows if r[0] == "LOT"]
        return ok({"fee": sum(float(x["entry_commission"]) for x in lots) if lots else None},
                  f"run spec の fee_kind = {what}、fee_value = {value}、1 回目に成行 買い {qty}。3 回目に strategy_native_open_lot_count_v1 / "
                  f"open_lot_get_v1 で読んだ建玉の entry_commission の合計。{[' '.join(r) for r in rows if r[0] in ('SUBMIT', 'APPLIED', 'LOT')]}")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, 2, 0.5, 1, "PF_NATIVE_FEE_CASH_PER_EXECUTION(約定 1 件あたりの額)")

    def scene_p7_cost_per_unit(self, sc):
        return self._fee(sc, 1, 0.375, 2, "PF_NATIVE_FEE_CASH_PER_UNIT(数量 1 あたりの額)")

    def scene_p7_account_swap(self, sc):
        return not_supported("口座(建玉・現金・証拠金)は kernel が run spec から作り、差し替える口が無い(callbacks で答えられるのは証拠金の要求額・"
                             "確かめる点・強制決済の数量など規則の一部で、約定を渡す先の口座は差し込めない)")
