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


def _dashboard_module():
    """scripts/dashboard.py, loaded by path (scripts/ is not a package)."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "dashboard.py"
    spec = importlib.util.spec_from_file_location("dashboard_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
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
                        lambda root: calls.append(root) or {"n": len(calls)})

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
    # market data is fetched on show and refreshed while the tab is visible
    assert 'setInterval(refreshMarket, 30000)' in page
    assert 'clearInterval(marketTimer)' in page
    assert '"/api/market"' in page


def test_page_renders_the_market_keys_it_is_served(tmp_path):
    """Checked against a real collect_market payload, not a hand-written list —
    a field that is computed and never displayed is invisible to the owner."""
    from bot.monitoring.market_view import collect_market

    d = collect_market(tmp_path)
    page = _dashboard_page()
    for key in d:
        assert f"d.{key}" in page or f'"{key}"' in page, key
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
// rendering path can be exercised headlessly.
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
const data = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));

function El(id) {
  this.id = id; this.innerHTML = ""; this.textContent = "";
  this.className = ""; this.hidden = false; this.style = {}; this.events = {};
}
El.prototype.addEventListener = function (k, f) { this.events[k] = f; };
El.prototype.getBoundingClientRect = () => ({left: 0, top: 0, width: 800, height: 340});

const els = {};
const document = {getElementById: id => (els[id] = els[id] || new El(id))};
const ops = [];
const ctx = {};
for (const m of ["setTransform", "clearRect", "fillRect", "beginPath", "moveTo",
                 "lineTo", "stroke", "fill", "closePath", "setLineDash", "fillText"]) {
  ctx[m] = () => ops.push(m);
}
const canvas = document.getElementById("m-chart");
canvas.getContext = () => ctx;
canvas.parentElement = {clientWidth: 800};
const window = {devicePixelRatio: 2, addEventListener() {}};

const api = new Function(
  "document", "window", "fetch", "setInterval", "clearInterval", "navigator",
  src + "\nreturn {renderMarket, drawChart, showTab, setChartTf, arrowSvg, " +
        "chartHover, geom: () => chartGeom};"
)(document, window, () => Promise.reject(new Error("no network")),
  () => 0, () => 0, {});

api.showTab("market");
api.renderMarket(data);
const before = ops.length;
api.setChartTf("1h");
api.chartHover({clientX: 300, currentTarget: canvas});

console.log(JSON.stringify({
  console_hidden: els["view-console"].hidden,
  market_hidden: els["view-market"].hidden,
  tab_class: els["tab-market"].className,
  strip: els["m-strip"].innerHTML,
  table: els["t-tf"].innerHTML,
  oi: els["m-oi"].innerHTML,
  tf_buttons: (els["m-tfs"].innerHTML.match(/<button/g) || []).length,
  chart_sub: els["m-chart-sub"].textContent,
  legend: els["m-legend"].innerHTML,
  canvas_px: [canvas.width, canvas.height],
  redrawn_on_tf_switch: ops.length - before,
  fill_rects: ops.filter(o => o === "fillRect").length,
  strokes: ops.filter(o => o === "stroke").length,
  tip: els["m-tip"].innerHTML,
  tip_display: els["m-tip"].style.display,
  bars_drawn: api.geom() ? api.geom().bars.length : 0,
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
    assert r["canvas_px"] == [1600, 680]
    assert r["bars_drawn"] > 0 and r["fill_rects"] > 10 and r["strokes"] > 10
    assert r["redrawn_on_tf_switch"] > 10          # switching TF repaints
    assert r["tip_display"] == "block" and "JST" in r["tip"]
    assert "rotate(-35.0 12 12)" in r["arrow_up"]  # SVG y is down: up = -angle
    assert r["arrow_flat"] == '<span class="flat">—</span>'


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
