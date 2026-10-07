"""The road record in the バックテスト tab: the reader (版, missing tables, range cuts, ids), the catalog (ledger, family
axes found from record.json, 古い形), the table API (sort, filter, page) and the trace (signal -> order -> fill -> trade)."""
from __future__ import annotations

import gzip
import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from bot.monitoring import backtest_chart as C
from bot.monitoring import road_catalog as RC
from bot.monitoring import road_strategies as RS
from bot.monitoring import road_view as RV
from road_fixture import FAKE, NS, trade, write_road_run

REPO = Path(__file__).resolve().parents[1]
RID = "a" * 64
TR = [trade(1000, 1600, 100, 110), trade(2000, 2600, 100, 90, "sell"), trade(3000, 3600, 100, 95)]


@pytest.fixture()
def run(tmp_path):
    root = write_road_run(tmp_path, RID, TR, first=0, last=5000)
    return root, str(Path(root) / "g" / RID)


# ---- the reader ---------------------------------------------------------------------------------------------------
def test_status_and_load_read_a_run_and_cache_it_by_path_mtime_size(run):
    _, d = run
    assert RV.status(d).ok and RV.status(d).version == "road-record-7"
    a, b = RV.load(d), RV.load(d)
    assert a is b and a.pairs == [("XBTUSD", "pessimistic"), ("XBTUSD", "optimistic")] and a.ranges == ["pessimistic", "optimistic"]
    assert {t: len(a.frames[t]) for t in RV.CSV_TABLES} == {"signals": 6, "orders": 12, "fills": 12, "fx": 0, "ledger_fills": 12, "trades": 6}
    p = Path(d) / "road" / "summary.json"
    p.write_text(p.read_text() + " ")  # size changes: read again
    assert RV.load(d) is not a


def test_unknown_version_missing_table_and_wrong_columns_are_refused_with_a_reason(tmp_path):
    root = write_road_run(tmp_path, "1" * 64, TR, first=0, last=5000, version="road-record-8")
    st = RV.status(str(Path(root) / "g" / ("1" * 64)))
    assert not st.ok and "road-record-8" in st.reason and "知らない版" in st.reason
    root = write_road_run(tmp_path, "2" * 64, TR, first=0, last=5000, drop="fills")
    st = RV.status(str(Path(root) / "g" / ("2" * 64)))
    assert not st.ok and "欠けた表" in st.reason and "fills" in st.reason
    root = write_road_run(tmp_path, "3" * 64, TR, first=0, last=5000, drop="summary")
    assert "summary" in RV.status(str(Path(root) / "g" / ("3" * 64))).reason
    root = write_road_run(tmp_path, "4" * 64, TR, first=0, last=5000)
    d = Path(root) / "g" / ("4" * 64)
    with gzip.open(d / "road" / "trades.csv.gz", "wt") as fh:
        fh.write("instrument,range,wrong\n")
    with pytest.raises(RV.RoadError, match="SCHEMA.json の列と違う"):
        RV.load(str(d))
    (d / "road" / "SCHEMA.json").unlink()
    assert "SCHEMA.json が無い" in RV.status(str(d)).reason
    (tmp_path / "x").mkdir()
    assert "古い形" in RV.status(str(tmp_path / "x")).reason


def test_a_schema_file_name_with_a_path_is_refused(tmp_path):
    root = write_road_run(tmp_path, "5" * 64, TR, first=0, last=5000)
    d = Path(root) / "g" / ("5" * 64)
    sch = json.loads((d / "road" / "SCHEMA.json").read_text())
    sch["tables"]["fills"]["file"] = "../../../etc/passwd"
    (d / "road" / "SCHEMA.json").write_text(json.dumps(sch))
    st = RV.status(str(d))
    assert not st.ok and "安全でない" in st.reason


def test_range_cut_uses_binary_search_on_sorted_times_and_returns_only_the_range(run):
    _, d = run
    g = RV.load(d).group("XBTUSD", "pessimistic")
    assert list(g.fl_t) == sorted(g.fl_t)
    L = RV.layers(g, 1500 * NS, 2100 * NS, 2**62, 60)
    assert [f["id"] for f in L["fills"]] == ["1", "2"] and [t["id"] for t in L["trades"]] == ["0", "1"]  # trade 0 ends at 1600, trade 1 starts 2000
    assert L["cum"][0] == [(1500 - 1) // 60 * 60, pytest.approx(0.0)] and L["pos"][0][1] == pytest.approx(0.1)  # still long from the fill at 1000
    # the left edge carries the value from before the range
    L = RV.layers(g, 1700 * NS, 1900 * NS, 2**62, 60)
    assert L["fills"] == [] and L["cum"][0][1] == pytest.approx(1.0) and L["avg"][0][1] is None  # flat since the fill at 1600
    # a big table: the range of 400,000 sorted times is found without scanning (searchsorted)
    t = np.arange(400_000, dtype=np.int64) * 60 * NS
    assert int(np.searchsorted(t, 1000 * 60 * NS)) == 1000


def test_signals_orders_and_trades_that_are_still_open_end_at_the_end_of_the_data(tmp_path):
    root = write_road_run(tmp_path, "6" * 64, [trade(1000, 1600, 100, 110)], first=0, last=5000)
    d = Path(root) / "g" / ("6" * 64)
    # an open signal (end empty) in the signals table
    p = d / "road" / "signals.csv.gz"
    import pandas as pd
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    df.loc[0, ["end_t_ns", "end_reason"]] = ["", "データの終わり"]
    df.to_csv(p, index=False, compression="gzip")
    g = RV.load(str(d)).group("XBTUSD", "pessimistic")
    L = RV.layers(g, 0, 5000 * NS, 2**62, 60, last_ns=5000 * NS)
    s = L["signals"][0]
    assert s["open"] is True and s["t1"] == 5000.0


def test_summary_rows_and_headline_numbers_come_from_the_tables(run):
    _, d = run
    data = RV.load(d)
    h = RV.headline(data, data.group("XBTUSD", "pessimistic"))
    t = h["trades"]
    # pnl: (110-100)*0.1 = 1, (100-90)*0.1 = 1, (95-100)*0.1 = -0.5  -> sum 1.5; 2 wins 1 loss
    assert t["closed"] == 3 and t["wins"] == 2 and t["losses"] == 1 and t["win_rate"] == pytest.approx(2 / 3) and t["pnl_sum"] == pytest.approx(1.5)
    assert t["levels_dist"] == [[1, 3]] and t["hold_min_dist"][0] == [0, 10.0]
    assert h["signals"]["count"] == 3 and h["signals"]["with_closed_trade"] == 3 and h["signals"]["pnl_per_signal_mean"] == pytest.approx(0.5)
    assert h["orders"]["count"] == 6 and h["orders"]["unfilled"] == 0 and h["fills"]["fee_sum"] == 0 and "帳簿の損益" in h["fills"]["formulas"]["fee_sum"]
    assert h["drawdown"]["max"] == pytest.approx(0.5)
    row = [r for r in RV.summary_rows(data) if r["range"] == "pessimistic"][0]
    assert row["closed_trades"] == 3 and float(row["pnl_jpy"]) == pytest.approx(1.5)


def test_unfilled_and_zero_quantity_orders_are_counted_apart(tmp_path):
    root = write_road_run(tmp_path, "7" * 64, TR, first=0, last=5000, canceled=2, zero=3)
    data = RV.load(str(Path(root) / "g" / ("7" * 64)))
    g = data.group("XBTUSD", "pessimistic")
    o = RV.headline(data, g)["orders"]
    assert o["zero_qty"] == 3 and o["sent"] == 8 and o["unfilled"] == 2 and o["unfilled_ratio"] == pytest.approx(2 / 8)
    assert o["unfilled_by"]["canceled"] == 2
    kinds = sorted(set(g.ord_kind))
    assert kinds == ["canceled", "filled", "zero"]
    L = RV.layers(g, 0, 5000 * NS, 2**62, 60)
    assert sorted({x["kind"] for x in L["orders"]}) == ["canceled", "filled", "zero"]


# ---- the ids: signal -> order -> fill -> trade --------------------------------------------------------------------
def _ids(tr, table):
    return [r[0 if False else 0] for l in tr["links"] if l["table"] == table for r in l["rows"]]


def test_trace_follows_the_numbers_both_ways(run):
    _, d = run
    data = RV.load(d)
    trades = data.frames["trades"]
    row = int(np.flatnonzero(((trades["range"] == "pessimistic") & (trades["trade_id"] == "1")).to_numpy())[0])
    tr = RV.trace(data, "trades", row)
    links = {l["table"]: l for l in tr["links"]}
    assert links["ledger_fills"]["count"] == 2 and links["fills"]["count"] == 2 and links["orders"]["count"] == 2 and links["signals"]["count"] == 1
    oc = data.cols["orders"].index("order_id")
    assert sorted(r[oc] for r in links["orders"]["rows"]) == ["road-2", "road-3"]
    assert tr["t_s"] == 2000.0 and tr["t_end_s"] == 2600.0 and tr["range"] == "pessimistic"
    # a signal -> its order and its trade; an order -> its fills, trade and signal
    sig = int(np.flatnonzero(((data.frames["signals"]["range"] == "pessimistic") & (data.frames["signals"]["signal_id"] == "s2")).to_numpy())[0])
    ts = {l["table"]: l for l in RV.trace(data, "signals", sig)["links"]}
    assert ts["orders"]["count"] == 1 and ts["fills"]["count"] == 1 and ts["trades"]["count"] == 1
    od = int(np.flatnonzero(((data.frames["orders"]["range"] == "optimistic") & (data.frames["orders"]["order_id"] == "road-1")).to_numpy())[0])
    to = {l["table"]: l for l in RV.trace(data, "orders", od)["links"]}
    assert to["fills"]["count"] == 1 and to["trades"]["count"] == 1 and to["signals"]["count"] == 0  # a close order has no signal (無し)
    # rows of the other range are never mixed in
    assert {r[1] for l in tr["links"] for r in l["rows"]} == {"pessimistic"}
    with pytest.raises(RV.RoadError):
        RV.trace(data, "trades", 10_000)
    with pytest.raises(RV.RoadError):
        RV.trace(data, "summary", 0)


# ---- the table API ------------------------------------------------------------------------------------------------
def test_table_page_sorts_filters_pages_and_shows_every_column(run):
    _, d = run
    data = RV.load(d)
    p = RV.table_page(data, "trades", "XBTUSD", "pessimistic", sort="pnl_jpy", desc=True)
    assert [r[2] for r in p["rows"]] == ["0", "1", "2"]  # trade_id, by pnl_jpy descending: 1, 1, -0.5 (ties keep the file order)
    assert len(p["columns"]) == len(data.cols["trades"]) and [c["name"] for c in p["columns"]] == data.cols["trades"]
    pn = [c["name"] for c in p["columns"]].index("pnl_jpy")
    assert [float(r[pn]) for r in p["rows"]] == sorted([float(r[pn]) for r in p["rows"]], reverse=True)
    asc = RV.table_page(data, "trades", "XBTUSD", "pessimistic", sort="pnl_jpy")
    assert float(asc["rows"][0][pn]) == pytest.approx(-0.5)
    f = RV.table_page(data, "trades", "XBTUSD", "pessimistic", filters=[["pnl_jpy", "gt", "0.5"], ["direction", "eq", "long"]])
    assert f["matched"] == 1 and f["total"] == 3
    assert RV.table_page(data, "orders", "XBTUSD", "pessimistic", filters=[["side", "contains", "sel"]])["matched"] == 3
    assert RV.table_page(data, "orders", "XBTUSD", "pessimistic", filters=[["attached_to", "empty", ""]])["matched"] == 6
    both = RV.table_page(data, "fills", "XBTUSD", "all", size=5)
    assert both["matched"] == 12 and both["pages"] == 3 and len(both["rows"]) == 5
    last = RV.table_page(data, "fills", "XBTUSD", "all", size=5, page=99)
    assert last["page"] == 2 and len(last["rows"]) == 2 and last["row_ids"] == sorted(last["row_ids"])
    assert RV.table_page(data, "fx", "XBTUSD", "pessimistic")["matched"] == 0
    s = RV.table_page(data, "summary", "XBTUSD", "pessimistic")
    assert s["matched"] == 1 and [c["name"] for c in s["columns"]] == data.cols["summary"]
    for bad in ([["nocol", "eq", "1"]], [["pnl_jpy", "like", "1"]], [["pnl_jpy", "gt", "abc"]], ["x"]):
        with pytest.raises(RV.RoadError):
            RV.table_page(data, "trades", "XBTUSD", "pessimistic", filters=bad)
    with pytest.raises(RV.RoadError):
        RV.table_page(data, "trades", "XBTUSD", "pessimistic", sort="nocol")
    with pytest.raises(RV.RoadError):
        RV.table_page(data, "nosuch", "XBTUSD", "pessimistic")


# ---- the catalog: ledger, family axes from record.json, 古い形 ---------------------------------------------------
def test_family_axes_are_the_config_leaves_that_differ_and_nothing_is_written_for_them(tmp_path):
    root = None
    for i, (lv, w) in enumerate([(3, 40), (5, 40), (3, 50), (5, 50)]):
        root = write_road_run(tmp_path, f"{i:064x}", TR, first=0, last=5000, params={"levels": lv, "window": w, "k": 1.5})
    cat = RC.catalog(root)
    st = cat["themes"][0]["strategies"][0]
    assert cat["themes"][0]["id"] == "fake" and st["fake"] is True and st["n_runs"] == 4
    axes = {a["key"]: [v["value"] for v in a["values"]] for a in st["axes"]}
    assert axes == {"strategy.params.levels": ["3", "5"], "strategy.params.window": ["40", "50"]}  # k is the same in every run: not an axis
    assert [a["label"] for a in st["axes"]] == ["段数(levels)", "窓の本数(window)"]
    combos = {tuple(r["axes"].values()) for r in st["runs"]}
    assert len(combos) == 4 and st["default_run_id"] == st["runs"][0]["run_id"]
    assert all("出所" not in d["text"] and d["source"] for d in st["description"])


def test_a_strategy_missing_from_the_ledger_is_listed_and_says_so(tmp_path):
    root = write_road_run(tmp_path, RID, TR, first=0, last=5000, module="bot.strategy.nobody_wrote_this")
    cat = RC.catalog(root)
    th = cat["themes"][0]
    st = th["strategies"][0]
    assert th["id"] == RS.THEME_UNLISTED and RS.NOT_IN_LEDGER in st["description"][0]["text"] and st["n_runs"] == 1
    assert RS.strategy_entry("bot.strategy.matilda_v37")["theme"] == "matilda"
    assert "bot.strategy.matilda_v37" in RS.STRATEGIES and all(d["source"] for d in RS.STRATEGIES["bot.strategy.matilda_v37"]["description"])


def test_old_form_runs_are_last_and_unreadable_road_runs_are_named_with_the_reason(tmp_path):
    root = write_road_run(tmp_path, RID, TR, first=0, last=5000)
    write_road_run(tmp_path, "b" * 64, TR, first=0, last=5000, version="road-record-9")
    old = Path(root) / "old" / ("c" * 64)
    old.mkdir(parents=True)
    (old / "record.json").write_text(json.dumps({"config": {"instrument": "X"}, "setup": {"name": "old"}, "purpose": "研究"}))
    (old / "repro.json").write_text("{}")
    cat = RC.catalog(root)
    assert [t["id"] for t in cat["themes"]] == ["fake", "legacy"] and cat["n_legacy_runs"] == 1
    legacy = cat["themes"][-1]["strategies"][0]["runs"][0]
    assert legacy["run_id"] == "c" * 64 and legacy["legacy"] is True and cat["themes"][-1]["title"] == "古い形の走らせ(道の記録が無い)"
    un = cat["themes"][0]["strategies"][0]["unavailable"]
    assert [u["run_id"] for u in un] == ["b" * 64] and "road-record-9" in un[0]["reason"]
    s = C.run_summary(root, "c" * 64, tmp_path)
    assert s["legacy"] is True and "古い形" in s["unavailable"]
    with pytest.raises(C.ChartError, match="古い形"):
        C.run_chart(root, "c" * 64, root=tmp_path)


# ---- the fake runs kept in tests/road_fake_runs --------------------------------------------------------------------
def test_the_fake_runs_in_the_repository_are_readable_and_named_as_fake():
    runs = FAKE / "runs"
    cat = RC.catalog(str(runs))
    assert cat["n_road_runs"] == 4 and cat["themes"][0]["id"] == "fake" and cat["themes"][0]["fake"] is True
    titles = {s["title"] for s in cat["themes"][0]["strategies"]}
    assert any("マチルダではない" in t for t in titles)
    for rid in [p.name for p in runs.iterdir()]:
        data = RV.load(str(runs / rid))
        assert data.version == "road-record-7" and data.instruments == ["FX_BTC_JPY"]
        for rg in data.ranges:  # the summary.json numbers equal the numbers made from the tables
            h = RV.headline(data, data.group("FX_BTC_JPY", rg))
            row = [r for r in RV.summary_rows(data) if r["range"] == rg][0]
            assert h["trades"]["closed"] == row["closed_trades"] and h["fills"]["count"] == row["fill_count"]
            assert h["trades"]["pnl_sum"] == pytest.approx(float(row["pnl_jpy"]))


def test_fake_runs_carry_ladders_cancels_and_zero_quantity_orders():
    kinds = set()
    levels = set()
    for p in (FAKE / "runs").iterdir():
        data = RV.load(str(p))
        g = data.group("FX_BTC_JPY", "pessimistic")
        kinds |= set(g.ord_kind)
        if len(data.frames["trades"]):
            levels |= set(data.frames["trades"]["levels"])
    assert {"filled", "canceled", "zero"} <= kinds and max(map(int, levels)) >= 2


def test_record_and_schema_files_are_served_by_fixed_names_only(run):
    root, d = run
    assert C.run_files(root, RID, "SCHEMA.json")["json"]["version"] == "road-record-7"
    assert C.run_files(root, RID, "record.json")["json"]["config"]["instrument"] == "XBTUSD"
    for bad in ("../repro.json", "repro.json", "road/trades.csv.gz", ""):
        with pytest.raises(C.ChartError):
            C.run_files(root, RID, bad)
    with pytest.raises(Exception):
        C.run_files(root, "../" + RID, "record.json")


def test_page_and_script_carry_the_road_pieces_and_the_old_ledgers_are_gone():
    import importlib.util
    spec = importlib.util.spec_from_file_location("dashboard_for_road_view", REPO / "scripts" / "dashboard.py")
    dash = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dash)
    js = (Path(C.STATIC_DIR) / "backtest_tab.js").read_text(encoding="utf-8")
    for need in ("/api/backtest/table/", "/api/backtest/trace/", "/api/backtest/file/", 'data-layer="', "合図の帯", "指値の線", "約定の矢印", "平均の建値", "取引の囲み",
                 "悲観側", "楽観側", "両方(重ねる)", "拡大すると出る", "計算式", "帳簿の損益に入っていない", "古い形"):
        assert need in js, need
    for need in ('id="bt-v-table"', 'id="bt-v-record"', 'id="bt-trace"', 'id="bt-pos"', 'id="bt-pnl"', 'id="bt-stats"', 'id="bt-scope"'):
        assert need in dash.PAGE, need
    for gone in ("src/bot/monitoring/backtest_themes.py", "src/bot/monitoring/backtest_cards.py", "scripts/dashboard_cards"):
        assert not (REPO / gone).exists(), gone


# ---- the seal on a run that crosses the boundary (critic round 1) --------------------------------------------------
B = 1_702_857_600  # 2023-12-18T00:00:00Z in s
CROSS = [trade(B - 3000, B - 2400, 100, 110, signal="sa"), trade(B - 1200, B - 600, 100, 90, "sell", signal="sa"),
         trade(B - 100, B + 30, 100, 70, "buy", signal="sa")]  # the third closes AFTER the boundary (its closing order was placed before it) and loses 3.0


@pytest.fixture()
def cross(tmp_path):
    root = write_road_run(tmp_path, RID, CROSS, first=B - 5000, last=B + 5000, canceled=1)
    d = str(Path(root) / "g" / RID)
    return root, d, RV.load(d)


LIM = B * NS


def _col(data, table, name):
    return data.cols[table].index(name)


def test_crossing_run_serves_no_summary_and_counts_only_the_rows_shown(cross):
    root, d, data = cross
    from test_backtest_chart import _seal
    _seal(Path(root).parent)
    s = C.run_summary(root, RID, Path(root).parent)
    assert s["summary_cut"] and s["summary_rows"] == [] and "まとめ" in s["summary_cut_reason"]
    assert s["road"]["counts_cut"] and s["road"]["tables"]["trades"] == 4 and s["road"]["tables"]["fills"] == 10  # 2 ranges: 2 trades, 5 fills each
    with pytest.raises(RV.RoadError, match="境をまたぐ"):
        RV.table_page(data, "summary", "XBTUSD", "pessimistic", LIM, cut_summary=True)
    assert RV.table_page(data, "summary", "XBTUSD", "pessimistic")["matched"] == 1  # a run that does not cross keeps its summary


def test_an_order_row_is_cut_when_any_of_its_fills_is_at_or_after_the_boundary(cross):
    _, _, data = cross
    # the third trade's closing order (road-5) was placed before the boundary and filled after it: its state and filled_qty would show the later fill
    t = RV.table_page(data, "orders", "XBTUSD", "pessimistic", LIM, open_cut=True)
    ids = [r[_col(data, "orders", "order_id")] for r in t["rows"]]
    assert "road-5" not in ids and "road-4" in ids and "road-0" in ids and len(ids) == 6  # 5 orders of trades 0-1 + the entry of trade 2
    g = data.group("XBTUSD", "pessimistic")
    L = RV.layers(g, 0, 2**61, LIM, 60, last_ns=(B + 5000) * NS)
    assert "road-5" not in {o["id"] for o in L["orders"]} and all(f["t"] < B for f in L["fills"]) and len(L["fills"]) == 5
    with pytest.raises(RV.RoadError):
        RV.trace(data, "orders", int(np.flatnonzero((data.frames["orders"]["order_id"] == "road-5").to_numpy())[0]), LIM, True)
    assert RV.headline(data, g, LIM, True)["orders"]["count"] == 6


def test_signals_and_trades_that_end_after_the_boundary_or_are_still_open_are_cut(cross, tmp_path):
    _, _, data = cross
    g = data.group("XBTUSD", "pessimistic")
    h = RV.headline(data, g, LIM, True)
    assert h["trades"]["closed"] == 2 and h["signals"]["count"] == 2  # signals / trades of the third trade end after the boundary
    # a signal that never ends and a trade that never closes: shown by a run that ends before the boundary, not by one that crosses it
    for first, last, shown in ((B - 5000, B - 10, 3), (B - 5000, B + 5000, 2)):
        root = write_road_run(tmp_path / f"r{last}", "e" * 64, CROSS[:2] + [trade(B - 100, B - 50, 100, 105, signal="sz")], first=first, last=last)
        d = Path(root) / "g" / ("e" * 64)
        import pandas as pd
        p = d / "road" / "signals.csv.gz"
        df = pd.read_csv(p, dtype=str, keep_default_na=False)
        df.loc[df["signal_id"] == "sz", ["end_t_ns", "end_reason"]] = ["", "データの終わり"]
        df.to_csv(p, index=False, compression="gzip")
        dd = RV.load(str(d))
        n = len(RV.table_page(dd, "signals", "XBTUSD", "pessimistic", LIM, open_cut=last >= B)["rows"])
        assert n == shown, (last, n)


def test_trace_links_never_lead_to_a_row_the_seal_cuts(cross):
    _, _, data = cross
    sg = data.frames["signals"]
    row = int(np.flatnonzero(((sg["range"] == "pessimistic") & (sg["signal_id"] == "sa")).to_numpy())[0])  # the first of three rows of signal "sa"
    tr = RV.trace(data, "signals", row, LIM, True)
    links = {l["table"]: l for l in tr["links"]}
    tc = _col(data, "trades", "last_t_ns")
    assert links["trades"]["count"] == 2 and all(int(r[tc]) < LIM for r in links["trades"]["rows"])  # "sa" is also the third trade's signal: cut
    fc = _col(data, "fills", "t_ns")
    assert links["fills"]["count"] == 3 and all(int(r[fc]) < LIM for r in links["fills"]["rows"])
    # trace of a trade, an order and a fill that belong to the cut trade: the cut rows are not among the links
    for table, key, val in (("trades", "trade_id", "1"), ("orders", "order_id", "road-4"), ("fills", "fill_id", "4")):
        f = data.frames[table]
        row = int(np.flatnonzero(((f["range"] == "pessimistic") & (f[key] == val)).to_numpy())[0])
        for l in RV.trace(data, table, row, LIM, True)["links"]:
            for r in l["rows"]:
                assert max(int(x) for x, c in zip(r, data.cols[l["table"]]) if c.endswith("_ns") and x != "") < LIM, (table, l["table"])
    bad = int(np.flatnonzero(((data.frames["trades"]["range"] == "pessimistic") & (data.frames["trades"]["trade_id"] == "2")).to_numpy())[0])
    with pytest.raises(RV.RoadError, match="封印"):
        RV.trace(data, "trades", bad, LIM, True)
    assert RV.trace(data, "trades", bad)["links"]  # without a limit it is there


def test_drawdown_and_ledger_numbers_are_made_from_the_rows_before_the_boundary(cross):
    _, _, data = cross
    g = data.group("XBTUSD", "pessimistic")
    cut = RV.headline(data, g, LIM, True)["drawdown"]["max"]
    full = RV.headline(data, g)["drawdown"]["max"]
    assert cut == pytest.approx(0.0 + 0.0) or cut == pytest.approx(1.0) or cut < full  # the losing trade 2 closes after the boundary
    assert full == pytest.approx(full) and cut != full
    assert RV.headline(data, g, LIM, True)["trades"]["pnl_sum"] == pytest.approx(0.0 + 1.0 + 1.0)  # (110-100)*0.1 + (100-90)*0.1


# ---- a fill that closes one trade and opens the next (ドテン) ------------------------------------------------------------
def _doten(tmp_path):
    from road_fixture import _gz_csv, schema
    root = write_road_run(tmp_path, "d" * 64, [trade(1000, 1600, 100, 110)], first=0, last=5000, ranges=("pessimistic",))
    d = Path(root) / "g" / ("d" * 64) / "road"
    sch = schema()
    cols = {t: [c[0] for c in sch["tables"][t]["columns"]] for t in sch["tables"]}
    ir = {"instrument": "XBTUSD", "range": "pessimistic"}
    N = NS
    fills = [dict(ir, fill_id=0, order_id="o0", signal_id="s0", t_ns=1000 * N, side="buy", qty=0.1, px=100),
             dict(ir, fill_id=1, order_id="o1", signal_id="s1", t_ns=1600 * N, side="sell", qty=0.2, px=110),
             dict(ir, fill_id=2, order_id="o2", signal_id="無し", t_ns=2000 * N, side="buy", qty=0.1, px=105)]
    orders = [dict(ir, order_id=f["order_id"], signal_id=f["signal_id"], side=f["side"], placed_t_ns=f["t_ns"] - 60 * N, state="FILLED",
                   filled_qty=f["qty"]) for f in fills]
    lf = [dict(ir, fill_id=0, t_ns=1000 * N, trade_id=0, opens_trade_id=0, px=100, position_after=0.1, pnl_jpy_cum=0),
          dict(ir, fill_id=1, t_ns=1600 * N, trade_id=0, opens_trade_id=1, px=110, position_after=-0.1, pnl_jpy_cum=1),
          dict(ir, fill_id=2, t_ns=2000 * N, trade_id=1, opens_trade_id="", px=105, position_after=0, pnl_jpy_cum=1.5)]
    tr = [dict(ir, trade_id=0, signal_id="s0", first_fill_id=0, fill_count=2, first_t_ns=1000 * N, last_t_ns=1600 * N, status="closed", pnl_jpy=1),
          dict(ir, trade_id=1, signal_id="s1", first_fill_id=1, fill_count=2, first_t_ns=1600 * N, last_t_ns=2000 * N, status="closed", pnl_jpy=0.5)]
    for t, rows in (("fills", fills), ("orders", orders), ("ledger_fills", lf), ("trades", tr)):
        _gz_csv(d / sch["tables"][t]["file"], cols[t], rows)
    return RV.load(str(d.parent))


def test_a_doten_fill_belongs_to_the_trade_it_closed_and_the_one_it_opened(tmp_path):
    data = _doten(tmp_path)
    tr = RV.trace(data, "trades", 1)
    L = {l["table"]: l for l in tr["links"]}
    fid = lambda t: sorted(r[_col(data, t, "fill_id")] for r in L[t]["rows"])
    assert fid("ledger_fills") == ["1", "2"] and fid("fills") == ["1", "2"]  # the fill that opens trade 1 is in it (it closes trade 0)
    assert sorted(r[_col(data, "orders", "order_id")] for r in L["orders"]["rows"]) == ["o1", "o2"]
    y = {l["table"]: l for l in RV.trace(data, "fills", 1)["links"]}
    assert sorted(r[_col(data, "trades", "trade_id")] for r in y["trades"]["rows"]) == ["0", "1"]
    o = {l["table"]: l for l in RV.trace(data, "orders", 1)["links"]}
    assert sorted(r[_col(data, "trades", "trade_id")] for r in o["trades"]["rows"]) == ["0", "1"]
    g = data.group("XBTUSD", "pessimistic")
    boxes = {t["id"]: (t["lo"], t["hi"]) for t in RV.layers(g, 0, 5000 * NS, 2**62, 60)["trades"]}
    assert boxes["1"] == (105.0, 110.0) and boxes["0"] == (100.0, 110.0)  # trade 1's box covers its opening fill at 110


# ---- orders that are open, sorting, exact ns, columns, names, locks, bars --------------------------------------------------
def test_a_partly_filled_order_that_was_never_closed_is_drawn_open_not_closed(tmp_path):
    import pandas as pd
    root = write_road_run(tmp_path, "f" * 64, [trade(1000, 1600, 100, 110)], first=0, last=5000)
    d = Path(root) / "g" / ("f" * 64)
    p = d / "road" / "orders.csv.gz"
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    df.loc[df["order_id"] == "road-1", ["state", "filled_qty"]] = ["PARTIALLY_FILLED", "0.05"]
    df.to_csv(p, index=False, compression="gzip")
    g = RV.load(str(d)).group("XBTUSD", "pessimistic")
    L = RV.layers(g, 0, 5000 * NS, 2**62, 60, last_ns=5000 * NS)
    o = [x for x in L["orders"] if x["id"] == "road-1"][0]
    assert o["kind"] == "partial" and o["open"] is True and o["t1"] == 5000.0  # to the end of the data, not to its last fill


def test_order_numbers_sort_by_their_number_and_ns_filters_compare_as_integers(tmp_path):
    many = [trade(1_700_000_000 + 1000 * i, 1_700_000_000 + 1000 * i + 500, 100, 101) for i in range(6)]
    root = write_road_run(tmp_path, "a" * 64, many, first=1_700_000_000, last=1_700_010_000)
    data = RV.load(str(Path(root) / "g" / ("a" * 64)))
    t = RV.table_page(data, "orders", "XBTUSD", "pessimistic", sort="order_id", size=100)
    ids = [r[_col(data, "orders", "order_id")] for r in t["rows"]]
    assert ids == [f"road-{i}" for i in range(12)]  # road-2 before road-10
    d = RV.table_page(data, "orders", "XBTUSD", "pessimistic", sort="order_id", desc=True)
    assert [r[2] for r in d["rows"]][:2] == ["road-11", "road-10"]
    ns = 1_700_000_000 * NS
    assert RV.table_page(data, "trades", "XBTUSD", "pessimistic", filters=[["first_t_ns", "eq", str(ns)]])["matched"] == 1
    assert RV.table_page(data, "trades", "XBTUSD", "pessimistic", filters=[["first_t_ns", "eq", str(ns + 1)]])["matched"] == 0  # a float would say 1
    assert RV.table_page(data, "trades", "XBTUSD", "pessimistic", filters=[["first_t_ns", "gt", str(ns)]])["matched"] == 5
    with pytest.raises(RV.RoadError):
        RV.table_page(data, "trades", "XBTUSD", "pessimistic", filters=[["first_t_ns", "eq", "1.5"]])


def test_a_schema_that_does_not_match_the_columns_of_its_version_is_refused_with_the_column_names(tmp_path):
    root = write_road_run(tmp_path, "b" * 64, TR, first=0, last=5000)
    d = Path(root) / "g" / ("b" * 64)
    sch = json.loads((d / "road" / "SCHEMA.json").read_text())
    sch["tables"]["trades"]["columns"] = [c for c in sch["tables"]["trades"]["columns"] if c[0] != "hold_ns"]
    (d / "road" / "SCHEMA.json").write_text(json.dumps(sch))
    st = RV.status(str(d))
    assert not st.ok and "trades" in st.reason and "欠けた列: hold_ns" in st.reason
    s = C.run_summary(root, "b" * 64, Path(root).parent)
    assert "hold_ns" in s["unavailable"]  # an answer, not a 500
    with pytest.raises(C.ChartError, match="hold_ns"):
        C.run_chart(root, "b" * 64, root=Path(root).parent)
    cat = RC.catalog(root)
    assert "hold_ns" in cat["themes"][0]["strategies"][0]["unavailable"][0]["reason"]


def test_a_table_file_name_with_a_colon_is_refused(tmp_path):
    root = write_road_run(tmp_path, "c" * 64, TR, first=0, last=5000)
    d = Path(root) / "g" / ("c" * 64)
    sch = json.loads((d / "road" / "SCHEMA.json").read_text())
    sch["tables"]["fills"]["file"] = "C:evil.csv.gz"
    (d / "road" / "SCHEMA.json").write_text(json.dumps(sch))
    assert "安全でない" in RV.status(str(d)).reason


def test_two_requests_for_one_run_read_it_once(run, monkeypatch):
    import threading
    import time
    _, d = run
    RV._CACHE.clear()
    calls = []
    orig = RV._read_table

    def slow(*a, **k):
        calls.append(a[2])
        time.sleep(0.05)
        return orig(*a, **k)
    monkeypatch.setattr(RV, "_read_table", slow)
    out = []
    ths = [threading.Thread(target=lambda: out.append(RV.load(d))) for _ in range(5)]
    [t.start() for t in ths]
    [t.join(30) for t in ths]
    assert len(out) == 5 and all(o is out[0] for o in out) and len(calls) == len(RV.CSV_TABLES)


def test_the_lines_below_the_chart_put_an_event_at_the_end_of_a_bar_in_that_bar(tmp_path):
    root = write_road_run(tmp_path, "9" * 64, [trade(1000, 1620, 100, 110)], first=0, last=5000)
    g = RV.load(str(Path(root) / "g" / ("9" * 64))).group("XBTUSD", "pessimistic")
    L = RV.layers(g, 900 * NS, 2000 * NS, 2**62, 60)
    cum = dict((k, v) for k, v in L["cum"])
    assert cum[1560] == pytest.approx(1.0) and 1620 not in cum  # the fill stamped 1620 closes the bar that starts at 1560 (the chart above puts it at that bar's right edge)
    pos = dict((k, v) for k, v in L["pos"])
    assert pos[960] == pytest.approx(0.1) and pos[1560] == 0.0


def test_a_run_on_made_up_data_is_marked_fake_by_its_own_record_and_the_page_lists_unreadable_records(tmp_path):
    root = write_road_run(tmp_path, RID, TR, first=0, last=5000, module="bot.strategy.nobody_wrote_this",
                          data=[{"dataset": "g", "origin": "synthetic", "path": None}])
    st = RC.catalog(root)["themes"][0]["strategies"][0]
    assert st["fake"] is True and st["runs"][0]["fake"] is True
    assert C.run_summary(root, RID, Path(root).parent)["strategy"]["fake"] is True
    bad = Path(root) / "g" / ("b" * 64)
    bad.mkdir()
    (bad / "record.json").write_text("{not json")
    (bad / "repro.json").write_text("{}")
    cat = RC.catalog(root)
    assert [b["run_id"] for b in cat["broken"]] == ["b" * 64] and "record.json が読めない" in cat["broken"][0]["reason"]
    js = (Path(C.STATIC_DIR) / "backtest_tab.js").read_text(encoding="utf-8")
    assert "読めない record.json" in js and 'value="${esc(v)}"' in js and 'value="${v}"' not in js


def test_the_matilda_ledger_says_what_its_sources_say():
    d = " ".join(x["text"] for x in RS.STRATEGIES["bot.strategy.matilda_v37"]["description"])
    src = " ".join(x["source"] for x in RS.STRATEGIES["bot.strategy.matilda_v37"]["description"])
    assert "建てた時の値段" in d and "L-781" in d and "L-789" in d and "step_exit" in d and "建玉の管理料" in d
    assert "MATILDA_ROAD_FRAMING" not in src and "FRAMING_V37.md §8" in src
