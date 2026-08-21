"""Dashboard aggregation over the runtime files."""
from __future__ import annotations

import json

import pytest

from bot.monitoring.aggregate import collect_status


def test_collect_status_empty_root(tmp_path):
    d = collect_status(tmp_path)
    assert d["components"]["main_bot"]["state"] == "missing"
    assert d["components"]["ws_recorder"]["state"] == "missing"
    assert d["scalp"]["trades"] == 0
    assert d["decisions"] == []


def test_collect_status_full(tmp_path):
    now = 1_000_000.0
    (tmp_path / "logs").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "logs" / "status.json").write_text(json.dumps({
        "mode": "paper", "last_price": 11000000, "balance_jpy": 200000,
        "daily_pnl_jpy": -50, "updated_at": now - 5}), encoding="utf-8")
    with open(tmp_path / "logs" / "bot.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"event": "decision", "strategy_signal": "HOLD",
                            "decision": "HOLD", "timestamp": "2026-08-20T05:00:00"}) + "\n")
    with open(tmp_path / "data" / "scalp_paper.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now - 60, "event": "entry", "side": "LONG",
                            "price": 1.0}) + "\n")
        f.write(json.dumps({"ts": now - 30, "event": "exit", "side": "LONG",
                            "price": 1.0, "pnl_jpy": 12.5}) + "\n")

    d = collect_status(tmp_path, now=now)
    assert d["components"]["main_bot"]["state"] == "ok"
    assert d["bot"]["last_price"] == 11000000
    assert d["scalp"]["trades"] == 1
    assert d["scalp"]["total_pnl_jpy"] == 12.5
    assert d["decisions"][0]["strategy_signal"] == "HOLD"


def test_overlay_and_active_modules_surfaced(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "status.json").write_text(json.dumps({
        "mode": "paper", "updated_at": 1_000_000.0,
        "overlay": {"factor": 0.5, "consecutive_losses": 3, "dd_pct": 6.2},
        "active_modules": []}), encoding="utf-8")
    d = collect_status(tmp_path, now=1_000_000.0)
    assert d["overlay"] == {"factor": 0.5, "consecutive_losses": 3, "dd_pct": 6.2}
    assert d["active_modules"] == []


def _dashboard_module(offline: bool = True):
    """scripts/dashboard.py, loaded by path (scripts/ is not a package).

    Loaded ``offline`` by default: the two public bitFlyer reads are replaced
    by stubs so no test ever opens a socket. Tests that exercise the fetchers
    pass offline=False and monkeypatch the session instead.
    """
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "dashboard.py"
    spec = importlib.util.spec_from_file_location("dashboard_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if offline:
        module.fetch_board = lambda now=None: None
        module.fetch_executions = lambda now=None: []
    return module


def _dashboard_page() -> str:
    return _dashboard_module().PAGE


def test_page_renders_the_overlay_and_active_modules_it_is_served(tmp_path):
    """The page must consume the keys collect_status publishes — telemetry that
    is written and never displayed is not visible to an operator. Checked
    against a real collect_status payload rather than a hand-written key list."""
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "status.json").write_text(json.dumps({
        "mode": "paper", "updated_at": 1_000_000.0,
        "overlay": {"factor": 0.25, "consecutive_losses": 4, "dd_pct": 7.1},
        "active_modules": ["radar_window"]}), encoding="utf-8")
    d = collect_status(tmp_path, now=1_000_000.0)
    page = _dashboard_page()

    assert "overlayTile(d.overlay)" in page          # tile is rendered
    assert "setModules(d.active_modules)" in page    # modules pill is rendered
    for field in d["overlay"]:                       # every field is shown
        assert f"ov.{field}" in page
    # null (no overlay / no module framework) is hidden, not shown as x1.00
    assert "if (ov == null) return \"\";" in page
    assert "if (mods == null) { el.style.display = \"none\"; return; }" in page


def test_overlay_absent_for_a_strategy_without_one(tmp_path):
    """None means 'no overlay / no module framework in this strategy', which
    is not the same as an overlay sitting at full size."""
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "status.json").write_text(json.dumps({
        "mode": "paper", "updated_at": 1_000_000.0}), encoding="utf-8")
    d = collect_status(tmp_path, now=1_000_000.0)
    assert d["overlay"] is None and d["active_modules"] is None


def test_status_write_survives_windows_permission_error(tmp_path, monkeypatch):
    """A dashboard reader holding status.json open must never crash the bot
    (Windows os.replace raises PermissionError then)."""
    from pathlib import Path
    from bot.monitoring.status import StatusWriter

    w = StatusWriter(tmp_path / "status.json", clock=lambda: 123.0)
    monkeypatch.setattr(Path, "replace",
                        lambda self, target: (_ for _ in ()).throw(PermissionError(5)))
    w.write()  # must not raise
    assert json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))[
        "updated_at"] == 123.0  # fell back to the direct write


def test_kill_switch_reflected(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "kill_switch.json").write_text(
        json.dumps({"reason": "manual", "detail": "test"}), encoding="utf-8")
    d = collect_status(tmp_path)
    assert d["components"]["main_bot"]["state"] == "killed"
    assert d["kill_switch"]["reason"] == "manual"


# ---- storm radar + OI snapshot ---------------------------------------------
def test_radar_state_in_status(tmp_path):
    """The radar window (research_storm_b.py G3, 12:30-15:00 UTC) is surfaced
    for the header pill; 13:00 UTC is inside it, 03:00 UTC is not."""
    from datetime import datetime, timezone

    def utc(h, m=0):
        return datetime(2026, 8, 20, h, m, tzinfo=timezone.utc).timestamp()

    armed = collect_status(tmp_path, now=utc(13))["radar"]
    assert armed["armed"] is True
    assert armed["window"] == "12:30-15:00 UTC"
    assert collect_status(tmp_path, now=utc(3))["radar"]["armed"] is False


def test_oi_snapshot_missing(tmp_path):
    assert collect_status(tmp_path)["oi_snapshot"] is None


def test_oi_snapshot_last_row(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "oi_snapshots.csv").write_text(
        "ts_utc,okx_usdt_oi,okx_usd_oi,okx_ls_ratio,dvol,deribit_oi\n"
        "2026-08-20T11:00:00+00:00,1.0,2.0,,38.25,3.0\n"
        "2026-08-20T12:00:00+00:00,10.0,20.0,1.13,39.5,30.0\n", encoding="utf-8")
    row_ts = 1787227200.0  # 2026-08-20T12:00:00+00:00
    oi = collect_status(tmp_path, now=row_ts + 600)["oi_snapshot"]
    assert oi["last"]["dvol"] == "39.5"
    assert oi["last"]["okx_ls_ratio"] == "1.13"
    assert oi["row_age_sec"] == 600.0


def test_oi_snapshot_header_only_file(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "oi_snapshots.csv").write_text(
        "ts_utc,okx_usdt_oi,okx_usd_oi,okx_ls_ratio,dvol,deribit_oi\n",
        encoding="utf-8")
    oi = collect_status(tmp_path)["oi_snapshot"]
    assert oi is not None and oi["last"] is None and oi["row_age_sec"] is None


def test_status_payload_is_json_serialisable(tmp_path):
    json.dumps(collect_status(tmp_path))


# ---- マーケットタブ ---------------------------------------------------------
def _serve(tmp_path, monkeypatch):
    """The real handler on a throwaway localhost port, rooted at tmp_path so
    the endpoints answer over an empty workspace instead of the live data/."""
    import threading
    from http.server import ThreadingHTTPServer

    monkeypatch.chdir(tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _dashboard_module().Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _get(port, path):
    import urllib.request

    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as r:
        return r.status, r.headers.get("Content-Type"), r.read()


def test_api_market_endpoint_serves_the_market_payload(tmp_path, monkeypatch):
    server, thread = _serve(tmp_path, monkeypatch)
    try:
        port = server.server_address[1]
        status, ctype, body = _get(port, "/api/market")
        assert status == 200 and ctype == "application/json"
        d = json.loads(body)
        # empty workspace: every section degrades instead of erroring
        assert d["state"] is None and d["chart"] is None and d["oi"] is None
        assert [t["tf"] for t in d["timeframes"]] == ["1m", "15m", "1h", "4h", "1d"]

        assert _get(port, "/api/status")[0] == 200
        assert "マーケット" in _get(port, "/")[2].decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_api_market_is_cached_until_a_file_changes(tmp_path, monkeypatch):
    """collect_market re-parses every candle row; a 30s poll per open tab must
    not pay for that when nothing on disk moved."""
    from tests.test_market_view import _make_workspace

    _make_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    module = _dashboard_module()
    calls = []
    monkeypatch.setattr(module, "collect_market",
                        lambda root, live_bars=(): calls.append(root) or {"n": len(calls)})

    first = module.market_body(".", now=1000.0)
    assert json.loads(first)["n"] == 1
    assert module.market_body(".", now=1005.0) == first    # inside the TTL
    assert module.market_body(".", now=1100.0) == first    # TTL over, files same
    assert len(calls) == 1

    (tmp_path / "logs" / "bot.jsonl").write_text(
        json.dumps({"event": "decision", "timestamp": "2026-08-20T00:31:00+00:00",
                    "strategy_signal": "HOLD", "decision": "HOLD",
                    "PnL": 0.0}) + "\n", encoding="utf-8")
    assert json.loads(module.market_body(".", now=1200.0))["n"] == 2
    assert len(calls) == 2


def test_page_has_both_tabs_and_switches_without_reloading(tmp_path):
    page = _dashboard_page()
    assert 'onclick="showTab(\'console\')"' in page and "Botコンソール" in page
    assert 'onclick="showTab(\'market\')"' in page and "マーケット" in page
    assert 'id="view-console"' in page and 'id="view-market"' in page
    # market data is fetched on show and refreshed while the tab is visible —
    # every 10s on the 1m scalp view, every 30s on the slower frames
    assert "setInterval(refreshMarket, marketPollMs())" in page
    assert "FAST_POLL_MS = 10000, SLOW_POLL_MS = 30000" in page
    assert 'chartTf === FAST_TF ? FAST_POLL_MS : SLOW_POLL_MS' in page
    assert 'clearInterval(marketTimer)' in page
    assert '"/api/market"' in page


def test_page_renders_the_market_keys_it_is_served(tmp_path):
    """Checked against a real collect_market payload, not a hand-written list —
    a field that is computed and never displayed is invisible to the owner."""
    from bot.monitoring.market_view import collect_market

    d = collect_market(tmp_path)
    page = _dashboard_page()
    for key in d:
        assert (f"d.{key}" in page or f"marketData.{key}" in page
                or f'"{key}"' in page), key
    for tf in d["timeframes"]:
        assert f'>{tf["label"]}<' in page or "t.label" in page
    # the three state pills and the 1m-approximation label are all reachable
    for state in ("嵐", "ブレイク", "静穏レンジ", "通常"):
        assert state in page
    assert "s.approx" in page


def _node() -> str | None:
    import shutil

    return shutil.which("node")


HARNESS = r"""
// DOM-less harness: runs the page script under stub globals so the market
// rendering path can be exercised headlessly. The 2d context records WHAT was
// drawn and WHERE, not just which methods were called — the chart now has
// three panes and "some fillRects happened" cannot tell them apart.
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
const data = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));

function El(id) {
  this.id = id; this.innerHTML = ""; this.textContent = "";
  this.className = ""; this.hidden = false; this.style = {}; this.events = {};
}
El.prototype.addEventListener = function (k, f) { this.events[k] = f; };
El.prototype.getBoundingClientRect = () => ({left: 0, top: 0, width: 800, height: 420});
El.prototype.scrollIntoView = function () { this.scrolled = true; };

const els = {};
const document = {getElementById: id => (els[id] = els[id] || new El(id))};
let ops = [], rects = [], segs = [], texts = [], cur = null;
const ctx = {
  fillStyle: "", strokeStyle: "", lineWidth: 1, font: "", textAlign: "",
  globalAlpha: 1,
  setTransform() { ops.push("setTransform"); },
  clearRect() { ops.push("clearRect"); rects = []; segs = []; texts = []; },
  fillRect(x, y, w, h) {
    ops.push("fillRect");
    rects.push({x: x, y: y, w: w, h: h, fill: this.fillStyle, a: this.globalAlpha});
  },
  beginPath() { ops.push("beginPath"); cur = []; },
  moveTo(x, y) { ops.push("moveTo"); (cur = cur || []).push([x, y]); },
  lineTo(x, y) { ops.push("lineTo"); (cur = cur || []).push([x, y]); },
  stroke() { ops.push("stroke"); segs.push({pts: cur || [], stroke: this.strokeStyle}); },
  fill() { ops.push("fill"); },
  closePath() { ops.push("closePath"); },
  setLineDash() { ops.push("setLineDash"); },
  fillText(s, x, y) { ops.push("fillText"); texts.push({s: String(s), x: x, y: y}); },
};
const canvas = document.getElementById("m-chart");
canvas.getContext = () => ctx;
canvas.parentElement = {clientWidth: 800};
const window = {devicePixelRatio: 2, addEventListener() {}};

const api = new Function(
  "document", "window", "fetch", "setInterval", "clearInterval", "navigator",
  src + "\nreturn {renderMarket, drawChart, showTab, setChartTf, arrowSvg, " +
        "chartHover, showTrendTable, pollMs: () => marketPollMs(), " +
        "tf: () => chartTf, geom: () => chartGeom};"
)(document, window, () => Promise.reject(new Error("no network")),
  () => 7, () => 0, {});

api.showTab("market");
api.renderMarket(data);           // opens on the default (1m) frame
const g = api.geom();
const openTf = api.tf(), openPoll = api.pollMs();

// A price gridline is the only horizontal segment that crosses BOTH the price
// pane and the depth panel — that shared y-axis is the point of the layout.
// Vertical segments are the time grid.
const horiz = segs.filter(s => s.pts.length === 2 && s.pts[0][1] === s.pts[1][1] &&
  g && s.pts[0][0] === g.padL && s.pts[1][0] === g.depthX + g.depthW);
// a time gridline is one path with FOUR points: it crosses the price pane and
// the volume pane but skips the gap between them (a candle wick has two)
const vert = segs.filter(s => s.pts.length === 4 && s.pts.every(p => p[0] === s.pts[0][0]));
const openRects = rects;
const inVolPane = g ? openRects.filter(r => r.y >= g.volTop - 0.5) : [];
const inDepth = g ? openRects.filter(r => r.x >= g.depthX - 0.5 && r.y < g.volTop) : [];
const byFill = list => {
  const out = {};
  for (const r of list) out[r.fill] = (out[r.fill] || 0) + 1;
  return out;
};

// what the page looked like on the frame it OPENED on, before any switching
const openSub = els["m-chart-sub"].textContent, openLegend = els["m-legend"].innerHTML;
const openStrip = els["m-strip"].innerHTML, openTexts = texts.map(t => t.s);

const before = ops.length;
api.setChartTf("1h");
api.chartHover({clientX: 300, currentTarget: canvas});
const hover1h = els["m-tip"].innerHTML, hoverDisplay = els["m-tip"].style.display;
api.chartHover({clientX: 780, currentTarget: canvas});   // over the depth panel
const hoverDepth = els["m-tip"].style.display;
api.showTrendTable();

console.log(JSON.stringify({
  console_hidden: els["view-console"].hidden,
  market_hidden: els["view-market"].hidden,
  tab_class: els["tab-market"].className,
  strip: els["m-strip"].innerHTML,
  table: els["t-tf"].innerHTML,
  oi: els["m-oi"].innerHTML,
  dir_strip: els["m-dir"].innerHTML,
  dir_chips: (els["m-dir"].innerHTML.match(/class="chip/g) || []).length,
  scrolled_to_table: els["t-tf"].scrolled === true,
  open_tf: openTf, open_poll_ms: openPoll, poll_after_switch: api.pollMs(),
  open_chart_sub: openSub, open_legend: openLegend, open_strip: openStrip,
  open_texts: openTexts,
  tf_buttons: (els["m-tfs"].innerHTML.match(/<button/g) || []).length,
  chart_sub: els["m-chart-sub"].textContent,
  legend: els["m-legend"].innerHTML,
  canvas_px: [canvas.width, canvas.height],
  redrawn_on_tf_switch: ops.length - before,
  price_grid_lines: horiz.length,
  time_grid_lines: vert.length,
  time_grid_majors: vert.filter(s => s.stroke !== "rgba(34,48,80,.9)").length,
  vol_rects: inVolPane.length, vol_fills: byFill(inVolPane),
  depth_rects: inDepth.length, depth_fills: byFill(inDepth),
  translucent_bars: openRects.filter(r => r.a < 1).length,
  axis_texts: texts.map(t => t.s),
  tip: hover1h, tip_display: hoverDisplay, tip_over_depth: hoverDepth,
  bars_drawn: g ? g.bars.length : 0,
  geom: g ? {plotW: g.plotW, depthW: g.depthW, priceH: g.priceH, volH: g.volH,
             W: g.W, H: g.H} : null,
  arrow_up: api.arrowSvg(35), arrow_flat: api.arrowSvg(null),
}));
"""


def _render_market_in_node(tmp_path, payload) -> dict:
    """Execute the page's own JS against ``payload`` and report what it built."""
    import re
    import subprocess

    js = re.search(r"<script>(.*)</script>", _dashboard_page(), re.S).group(1)
    (tmp_path / "page.js").write_text(js, encoding="utf-8")
    (tmp_path / "harness.js").write_text(HARNESS, encoding="utf-8")
    (tmp_path / "market.json").write_text(json.dumps(payload), encoding="utf-8")
    node = _node()
    subprocess.run([node, "--check", str(tmp_path / "page.js")], check=True)
    out = subprocess.run(
        [node, str(tmp_path / "harness.js"), str(tmp_path / "page.js"),
         str(tmp_path / "market.json")],
        check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_renders_a_full_payload(tmp_path):
    from tests.test_market_view import T0, _make_workspace
    from bot.monitoring.market_view import collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    _make_workspace(workspace)
    payload = collect_market(workspace, now=T0 + 400 * 60)
    r = _render_market_in_node(tmp_path, payload)

    assert r["console_hidden"] is True and r["market_hidden"] is False
    assert r["tab_class"] == "on"
    assert payload["state"]["state"] in r["strip"] and "レーダー" in r["strip"]
    assert "24時間" in r["strip"] and "買い比率" in r["strip"]
    assert r["table"].count("<tr>") == 6           # header + five timeframes
    assert "OKX USDT建 OI" in r["oi"] and "DVOL" in r["oi"]
    assert r["tf_buttons"] == 5 and "1時間" in r["chart_sub"]
    assert "ロング建て" in r["legend"] and "レンジ" in r["legend"]
    # crisp on devicePixelRatio 2: the backing store is twice the CSS size
    assert r["canvas_px"] == [1600, 840]
    assert r["bars_drawn"] > 0
    assert r["redrawn_on_tf_switch"] > 10          # switching TF repaints
    assert r["tip_display"] == "block" and "JST" in r["tip"]
    assert "出来高" in r["tip"]                    # the tooltip reports volume
    assert r["tip_over_depth"] == "none"           # the depth panel is not a bar
    assert "rotate(-35.0 12 12)" in r["arrow_up"]  # SVG y is down: up = -angle
    assert r["arrow_flat"] == '<span class="flat">—</span>'


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_opens_on_the_1m_frame_at_the_fast_cadence(tmp_path):
    """The owner scalps the 1m chart: it is what opens, and it is polled at
    10s. The slower frames drop back to 30s so the extra polls are not spent
    on bars that move once an hour."""
    from tests.test_market_view import T0, _make_workspace
    from bot.monitoring.market_view import collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    _make_workspace(workspace)
    r = _render_market_in_node(tmp_path, collect_market(workspace, now=T0 + 400 * 60))

    assert r["open_tf"] == "1m" and r["open_poll_ms"] == 10000
    assert r["poll_after_switch"] == 30000         # after switching to 1h
    assert r["open_chart_sub"].startswith("1分 /")
    assert "レンジ 15分" in r["open_legend"]        # the 1m frame's own band


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_shows_the_higher_frames_as_direction_chips(tmp_path):
    """Direction is read off 15分/1時間/4時間/日足 while scalping 1m, so it sits
    above the chart as chips — coloured by the same trend score as the table,
    and clicking one goes to the table."""
    from tests.test_market_view import T0, _make_workspace
    from bot.monitoring.market_view import collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    _make_workspace(workspace, minutes=16 * 1440)   # enough history to vote 日足
    payload = collect_market(workspace, now=T0 + 16 * 1440 * 60)
    r = _render_market_in_node(tmp_path, payload)

    assert r["dir_chips"] == 4                      # 15m / 1h / 4h / 1d, not 1m
    for tf in payload["timeframes"]:
        if tf["tf"] == "1m":
            assert f'>{tf["label"]} ' not in r["dir_strip"]
            continue
        assert f'>{tf["label"]} ' in r["dir_strip"]
        glyph = {1: "▲", -1: "▼", 0: "─"}[
            (tf["trend"]["score"] > 0) - (tf["trend"]["score"] < 0)]
        assert f'{tf["label"]} {glyph}' in r["dir_strip"]
    # the chips carry the same up/down semantics as everything else on the page
    assert '"chip up"' in r["dir_strip"] or '"chip down"' in r["dir_strip"] \
        or '"chip flat"' in r["dir_strip"]
    assert r["scrolled_to_table"] is True


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_draws_the_volume_pane_and_the_depth_panel(tmp_path):
    """The chart is three panes on one canvas: price, volume under it on the
    same x, order-book depth beside it on the same y."""
    from tests.test_market_view import T0, _make_workspace
    from bot.monitoring.market_view import attach_board, collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    # 120 minutes from UTC midnight, so the visible 1m window contains the one
    # boundary that gets the stronger gridline
    _make_workspace(workspace, minutes=120)
    payload = collect_market(workspace, now=T0 + 120 * 60)
    mid = payload["chart"]["tfs"]["1m"]["bars"][-1]["c"]
    attach_board(payload, {
        "mid_price": mid,
        "bids": [{"price": mid - 500 - i * 1500, "size": 0.4 + i * 0.01} for i in range(120)],
        "asks": [{"price": mid + 500 + i * 1500, "size": 0.3 + i * 0.01} for i in range(120)],
    }, now=T0 + 120 * 60)
    r = _render_market_in_node(tmp_path, payload)

    # panes are sized as designed: volume ~20% of the body, depth ~15% of width
    geom = r["geom"]
    assert geom["W"] == 800 and geom["H"] == 420
    assert 0.17 < geom["volH"] / (geom["volH"] + geom["priceH"] + 10) < 0.23
    assert 0.13 < geom["depthW"] / (geom["depthW"] + geom["plotW"] + 8) < 0.17

    # a fine price grid — one line per server-computed gridline, each labelled
    # at the right edge in the monospace (tabular) face
    grid = payload["chart"]["tfs"]["1m"]["scale"]["grid"]
    assert 6 <= len(grid) <= 14 and r["price_grid_lines"] == len(grid)
    for price in grid:
        assert round(price) == price and f"{round(price):,}" in r["open_texts"]
    # time gridlines on clock boundaries, with UTC midnight drawn stronger
    assert r["time_grid_lines"] == len(payload["chart"]["tfs"]["1m"]["time_grid"])
    assert r["time_grid_majors"] >= 1

    # the volume pane draws a stacked buy/sell column: _make_workspace writes a
    # flow file, so the split is real data rather than an undifferentiated bar
    assert r["vol_rects"] >= len(payload["chart"]["tfs"]["1m"]["bars"])
    assert "#46b87a" in r["vol_fills"] and "#e0604f" in r["vol_fills"]

    # the depth panel drew both sides, and drew them inside its own column
    assert r["depth_rects"] > 4
    assert "rgba(224,96,79,.55)" in r["depth_fills"]     # asks
    assert "rgba(70,184,122,.55)" in r["depth_fills"]    # bids
    assert "板情報なし" not in r["open_texts"]
    assert "板" in r["open_legend"] and "出来高" in r["open_legend"]


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_says_so_when_the_board_fetch_failed(tmp_path):
    """The board comes off the network and the network is allowed to fail: the
    panel says 板情報なし and every other pane draws exactly as before."""
    from tests.test_market_view import T0, _make_workspace
    from bot.monitoring.market_view import attach_board, collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    _make_workspace(workspace)
    payload = attach_board(collect_market(workspace, now=T0 + 400 * 60), None)
    assert payload["board"] is None
    r = _render_market_in_node(tmp_path, payload)

    assert "板情報なし" in r["open_texts"]
    assert r["depth_rects"] == 0
    assert r["bars_drawn"] > 0 and r["vol_rects"] > 0 and r["price_grid_lines"] > 0
    assert "右 = 板情報なし" in r["open_legend"]


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_draws_the_live_tail_as_translucent(tmp_path):
    """Live 1m buckets are built from the public tape and are not in the CSV
    yet, so they are drawn dimmer than an archived bar and labelled as live."""
    from tests.test_market_view import T0, _make_workspace, _exec
    from bot.monitoring.market_view import bars_from_executions, collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    _make_workspace(workspace)
    last_close = 11_000_000.0 * 1.0002 ** 400
    live = bars_from_executions([_exec(400 * 60 + s, last_close, 0.2)
                                 for s in (5, 35, 65, 95)])
    payload = collect_market(workspace, now=T0 + 402 * 60, live_bars=live)
    assert payload["live"]["bars"] == 2

    r = _render_market_in_node(tmp_path, payload)
    assert "ライブ 2本" in r["open_chart_sub"]
    assert "ライブ追記 2分" in r["open_strip"]
    assert r["translucent_bars"] > 0
    assert "半透明の足" in r["open_legend"]


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_says_the_feed_stopped_instead_of_labelling_it(tmp_path):
    """Day-old candles must not render as 静穏レンジ — the pill says the
    collector stopped, and the freshness line stays."""
    from tests.test_market_view import T0, _make_workspace
    from bot.monitoring.market_view import collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    _make_workspace(workspace)
    payload = collect_market(workspace, now=T0 + 400 * 60 + 24 * 3600)
    assert payload["state"]["state"] is None and payload["state"]["stale"] is True

    r = _render_market_in_node(tmp_path, payload)
    assert "データ停止 24.0時間前" in r["strip"]
    assert "足 24.0時間前" in r["strip"]                  # freshness line kept
    for label in ("嵐", "ブレイク", "静穏レンジ", "通常"):
        assert label not in r["strip"].split("レーダー")[0]
    assert r["bars_drawn"] > 0                            # the chart still draws


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_renders_an_empty_payload_without_errors(tmp_path):
    """Every data file missing: empty states, no exception, no chart."""
    from bot.monitoring.market_view import collect_market

    empty = tmp_path / "empty"
    empty.mkdir()
    r = _render_market_in_node(tmp_path, collect_market(empty))

    assert "ローソク足データなし" in r["strip"]
    assert "ローソク足データなし" in r["table"]
    assert "OIスナップショット未収集" in r["oi"]
    assert r["tf_buttons"] == 0 and r["chart_sub"] == "データなし"
    assert r["legend"] == "" and r["bars_drawn"] == 0
    assert r["tip_display"] == "none"
    # nothing to take a direction from, so no chips and no panes
    assert r["dir_strip"] == "" and r["dir_chips"] == 0
    assert r["vol_rects"] == 0 and r["depth_rects"] == 0
    assert r["price_grid_lines"] == 0 and r["time_grid_lines"] == 0
    assert "チャートデータなし" in r["axis_texts"]


# ---- public bitFlyer reads (board + execution tape) -------------------------
class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeSession:
    """Records every GET and answers from a scripted queue. No sockets."""

    def __init__(self, answers):
        self.answers = answers          # path -> payload, or an Exception
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {}), timeout))
        answer = self.answers[url.rsplit("/v1/", 1)[1].split("?")[0]]
        if isinstance(answer, Exception):
            raise answer
        return _FakeResponse(answer)


def _board_payload(mid=11_000_000.0, n=5, step=None):
    step = step if step is not None else max(mid * 0.0001, 0.01)
    return {"mid_price": mid,
            "bids": [{"price": mid - step * (i + 1), "size": 0.5} for i in range(n)],
            "asks": [{"price": mid + step * (i + 1), "size": 0.4} for i in range(n)]}


def _exec_payload(count=3, price=11_000_000.0):
    return [{"id": i, "side": "BUY" if i % 2 else "SELL", "price": price + i,
             "size": 0.01, "exec_date": f"2026-08-20T00:00:{i:02d}.000"}
            for i in range(count)]


def test_public_reads_hit_the_documented_endpoints_without_auth(monkeypatch):
    module = _dashboard_module(offline=False)
    session = _FakeSession({"board": _board_payload(),
                            "executions": _exec_payload()})
    monkeypatch.setattr(module, "_session", session)

    assert module.fetch_board(now=1000.0)["mid_price"] == 11_000_000.0
    assert len(module.fetch_executions(now=1000.0)) == 3

    urls = [c[0] for c in session.calls]
    assert urls == ["https://api.bitflyer.com/v1/board",
                    "https://api.bitflyer.com/v1/executions"]
    assert session.calls[0][1] == {"product_code": "FX_BTC_JPY"}
    assert session.calls[1][1] == {"product_code": "FX_BTC_JPY", "count": 500}
    assert all(c[2] == module.PUBLIC_TIMEOUT == 3.0 for c in session.calls)
    # no auth material anywhere near these: they are public read-only endpoints
    assert not hasattr(session, "headers")


def test_public_reads_are_cached_so_the_rate_budget_is_bounded(monkeypatch):
    """The bot shares the 500 req / 5 min public IP budget. Two endpoints at
    one call per PUBLIC_TTL is 0.4 req/s worst case, whatever the poll rate."""
    module = _dashboard_module(offline=False)
    session = _FakeSession({"board": _board_payload(),
                            "executions": _exec_payload()})
    monkeypatch.setattr(module, "_session", session)

    assert module.PUBLIC_TTL >= 5.0
    for t in (1000.0, 1001.0, 1004.9):
        module.fetch_board(now=t)
        module.fetch_executions(now=t)
    assert len(session.calls) == 2                  # one per endpoint

    module.fetch_board(now=1005.0)
    module.fetch_executions(now=1005.0)
    assert len(session.calls) == 4
    worst_case_rps = 2 / module.PUBLIC_TTL
    assert worst_case_rps <= 0.4


def test_public_reads_fail_soft_and_keep_serving_the_last_snapshot(monkeypatch):
    """bitFlyer down, the box offline, a timeout: the console must not care."""
    module = _dashboard_module(offline=False)
    good = _FakeSession({"board": _board_payload(), "executions": _exec_payload()})
    monkeypatch.setattr(module, "_session", good)
    assert module.fetch_board(now=1000.0) is not None

    broken = _FakeSession({"board": RuntimeError("connection reset"),
                           "executions": RuntimeError("connection reset")})
    monkeypatch.setattr(module, "_session", broken)
    # the last good board is still served, with the age it really has
    assert module.fetch_board(now=1010.0)["mid_price"] == 11_000_000.0
    assert module.board_fetched_at() == 1000.0
    assert module._public_cache["board"]["error"].startswith("RuntimeError")
    # a hard-down endpoint is still only retried once per TTL
    module.fetch_board(now=1011.0)
    assert len(broken.calls) == 1

    # nothing was ever fetched: None / [], and the payload still assembles
    fresh = _dashboard_module(offline=False)
    monkeypatch.setattr(fresh, "_session",
                        _FakeSession({"board": OSError("no route"),
                                      "executions": OSError("no route")}))
    assert fresh.fetch_board(now=1.0) is None
    assert fresh.fetch_executions(now=1.0) == []
    assert fresh.live_bars(now=1.0) == []


def test_live_bars_come_off_the_execution_tape(monkeypatch):
    module = _dashboard_module(offline=False)
    monkeypatch.setattr(module, "_session",
                        _FakeSession({"board": _board_payload(),
                                      "executions": _exec_payload(count=4)}))
    bars = module.live_bars(now=1000.0)
    assert len(bars) == 1 and bars[0]["live"] is True
    assert bars[0]["trades"] == 4 and bars[0]["volume"] == pytest.approx(0.04)


def test_api_market_attaches_a_fresh_board_to_the_cached_payload(tmp_path, monkeypatch):
    """The heavy file parse is cached; the board is not part of that key, so a
    depth panel never waits on a candle file to change."""
    from tests.test_market_view import _make_workspace

    _make_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    module = _dashboard_module()
    calls = []
    monkeypatch.setattr(module, "collect_market",
                        lambda root, live_bars=(): calls.append(root) or
                        json.loads(json.dumps(_market_skeleton())))
    board = {"now": _board_payload(mid=100.0)}
    monkeypatch.setattr(module, "fetch_board", lambda now=None: board["now"])
    monkeypatch.setattr(module, "board_fetched_at", lambda: 55.0)

    first = json.loads(module.market_body(".", now=1000.0))
    assert first["board"]["mid"] == 100.0 and first["board"]["fetched_at"] == 55.0
    assert first["chart"]["tfs"]["1m"]["depth"]["step"] == 5.0

    board["now"] = _board_payload(mid=101.0)
    second = json.loads(module.market_body(".", now=1002.0))
    assert len(calls) == 1                       # the payload came from cache
    assert second["board"]["mid"] == 101.0       # the board did not


def _market_skeleton():
    """The minimum collect_market shape attach_board has to cope with."""
    return {"chart": {"tfs": {"1m": {"scale": {"hi": 110.0, "lo": 90.0, "step": 5.0,
                                               "grid": [90.0, 95.0, 100.0, 105.0, 110.0]}}}}}


def test_api_market_rebuilds_when_the_live_tail_moves(tmp_path, monkeypatch):
    """The CSV writer runs every ~15 min; the live tail is what actually moves
    between polls, so it has to be part of the cache key."""
    from tests.test_market_view import _make_workspace

    _make_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    module = _dashboard_module()
    calls = []
    monkeypatch.setattr(module, "collect_market",
                        lambda root, live_bars=(): calls.append(list(live_bars)) or
                        {"n": len(calls)})
    tail = [{"ts": 60.0, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0,
             "volume": 0.5, "live": True}]
    monkeypatch.setattr(module, "live_bars", lambda now=None: [dict(tail[0])])

    assert json.loads(module.market_body(".", now=1000.0))["n"] == 1
    assert json.loads(module.market_body(".", now=1100.0))["n"] == 1   # tail same
    tail[0]["close"] = 2.0                        # price moved inside the minute
    assert json.loads(module.market_body(".", now=1200.0))["n"] == 2
    assert calls[-1][0]["close"] == 2.0           # and it reached collect_market


def test_page_carries_the_new_panes_and_chips():
    page = _dashboard_page()
    # volume pane, depth panel and the chip strip are all present in the markup
    assert 'id="m-dir"' in page and 'class="dirstrip"' in page
    assert "function drawDepth(" in page and "板情報なし" in page
    assert "drawDepth(ctx, payload.depth" in page
    assert "payload.time_grid" in page and "payload.scale" in page
    assert "payload.vmax" in page and "b.bv" in page and "b.sv" in page
    assert "showTrendTable()" in page and "scrollIntoView" in page
    # the chart opens on 1m and the range band is named by its own window
    assert 'chartTf = "1m"' in page
    assert "p.range.window_label" in page
    # the payload's new top-level sections are consumed by the page
    for key in ("board", "live"):
        assert f"d.{key}" in page or f"marketData.{key}" in page, key


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_market_tab_flags_a_collector_outage_behind_the_live_tail(tmp_path):
    """The tape can keep the price live while the CSV writer is dead. That is
    a hole in the series, not a live feed, and the page has to say so — the
    windows measured across it are refused rather than faked."""
    from tests.test_market_view import T0, _make_workspace, _exec
    from bot.monitoring.market_view import bars_from_executions, collect_market

    workspace = tmp_path / "ws"
    workspace.mkdir()
    _make_workspace(workspace)
    live = bars_from_executions([_exec(400 * 60 + 24 * 3600 + s, 13_000_000.0, 0.2)
                                 for s in (5, 35)])
    payload = collect_market(workspace, now=T0 + 400 * 60 + 24 * 3600 + 60,
                             live_bars=live)
    assert payload["state"]["stale"] is False        # the tape is live
    assert payload["state"]["ret_30m_pct"] is None   # the 30m window is a hole
    assert payload["live"]["gap_sec"] > 86000

    r = _render_market_in_node(tmp_path, payload)
    assert "CSV欠落 24.0時間" in r["open_strip"]
    assert "CSV欠落 24.0時間前" not in r["open_strip"]   # a duration, not an age
    assert "30分</span><span class=\"mono flat\">—" in r["open_strip"]
