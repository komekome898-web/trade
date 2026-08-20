#!/usr/bin/env python3
"""Local operations dashboard — serves http://127.0.0.1:8300 with live bot
state, scalp trades, kill-switch status and data-collection health.

Read-only over local files; binds to localhost only; no external requests.
Usage: python scripts/dashboard.py [--port 8300]
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bot.monitoring.aggregate import collect_status  # noqa: E402

PAGE = """<!doctype html>
<html lang="ja"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bot Console</title>
<style>
  :root {
    --bg: #0c1322; --panel: #131c30; --line: #223050;
    --ink: #e9eef7; --muted: #93a0b8; --accent: #4cc8cf;
    --ok: #46b87a; --warn: #d9a83f; --crit: #e0604f;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font-family: system-ui, "Hiragino Sans", "Yu Gothic UI", sans-serif;
    font-size: 14px; line-height: 1.55;
  }
  .mono { font-family: ui-monospace, "Cascadia Mono", Consolas, monospace;
          font-variant-numeric: tabular-nums; }
  header {
    display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
    padding: 14px 20px; border-bottom: 1px solid var(--line);
    position: sticky; top: 0; background: var(--bg); z-index: 5;
  }
  header h1 { font-size: 16px; margin: 0; letter-spacing: .02em; }
  header h1 span { color: var(--accent); }
  .pill {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 3px 10px; border-radius: 999px; font-size: 12px;
    border: 1px solid var(--line); color: var(--muted);
  }
  .pill i { width: 8px; height: 8px; border-radius: 50%; display: inline-block;
            background: var(--muted); }
  .pill.ok i { background: var(--ok); } .pill.ok { color: var(--ok); border-color: color-mix(in srgb, var(--ok) 40%, var(--line)); }
  .pill.warn i { background: var(--warn); } .pill.warn { color: var(--warn); }
  .pill.down i, .pill.missing i, .pill.killed i { background: var(--crit); }
  .pill.down, .pill.missing, .pill.killed { color: var(--crit); }
  #updated { margin-left: auto; color: var(--muted); font-size: 12px; }
  main { padding: 20px; max-width: 1200px; margin: 0 auto;
         display: flex; flex-direction: column; gap: 20px; }
  .banner {
    background: color-mix(in srgb, var(--crit) 16%, var(--panel));
    border: 1px solid var(--crit); border-radius: 8px; padding: 12px 16px;
    display: none;
  }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
  .tile { background: var(--panel); border: 1px solid var(--line);
          border-radius: 8px; padding: 12px 14px; }
  .tile .k { color: var(--muted); font-size: 11px; letter-spacing: .06em;
             text-transform: uppercase; }
  .tile .v { font-size: 22px; margin-top: 4px; }
  .tile .v.pos { color: var(--ok); } .tile .v.neg { color: var(--crit); }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media (max-width: 900px) { .grid2 { grid-template-columns: 1fr; } }
  section { background: var(--panel); border: 1px solid var(--line);
            border-radius: 8px; overflow: hidden; }
  section h2 { font-size: 12px; letter-spacing: .06em; text-transform: uppercase;
               color: var(--muted); margin: 0; padding: 10px 14px;
               border-bottom: 1px solid var(--line); }
  .scroll { overflow-x: auto; max-height: 340px; overflow-y: auto; }
  table { border-collapse: collapse; width: 100%; font-size: 12.5px; }
  th, td { text-align: left; padding: 6px 14px; white-space: nowrap; }
  th { color: var(--muted); font-weight: 500; position: sticky; top: 0;
       background: var(--panel); }
  tr + tr td { border-top: 1px solid color-mix(in srgb, var(--line) 55%, transparent); }
  td.num { text-align: right; }
  .sub { color: var(--muted); }
  .empty { color: var(--muted); padding: 16px; }
</style></head><body>
<header>
  <h1>Bot <span>Console</span></h1>
  <span class="pill" id="p-main"><i></i>メインBOT</span>
  <span class="pill" id="p-scalp"><i></i>スキャルパー</span>
  <span class="pill" id="p-ws"><i></i>板記録</span>
  <span class="pill" id="p-radar"><i></i>レーダー</span>
  <span id="updated">—</span>
</header>
<main>
  <div class="banner" id="banner"></div>
  <div class="tiles" id="tiles"></div>
  <div class="grid2">
    <section>
      <h2>メインBOT: 最近の判断</h2>
      <div class="scroll"><table id="t-dec"></table></div>
    </section>
    <section>
      <h2>バーストスキャル(ペーパー)</h2>
      <div class="scroll"><table id="t-scalp"></table></div>
    </section>
  </div>
  <section>
    <h2>データ収集</h2>
    <div class="scroll"><table id="t-col"></table></div>
  </section>
</main>
<script>
const fmt = (v, d=1) => v == null ? "—" : Number(v).toLocaleString("ja-JP", {maximumFractionDigits: d});
const age = s => s == null ? "—" : s < 90 ? `${Math.round(s)}秒前` : s < 5400 ? `${Math.round(s/60)}分前` : `${(s/3600).toFixed(1)}時間前`;
const stateLabel = {ok: "稼働中", warn: "遅延", down: "停止?", missing: "未起動", killed: "停止(Kill)"};

function setPill(id, name, comp) {
  const el = document.getElementById(id);
  el.className = "pill " + comp.state;
  el.innerHTML = `<i></i>${name}: ${stateLabel[comp.state] || comp.state}`;
}

// storm radar (research_storm_b.py G3): armed inside 12:30-15:00 UTC, when
// the scalper trades its lowered entry threshold.
function setRadar(r) {
  const el = document.getElementById("p-radar");
  el.className = "pill" + (r.armed ? " warn" : "");
  el.title = r.reason || "";
  el.innerHTML = `<i></i>${r.armed ? "レーダー: 武装中" : "レーダー: 待機"}` +
    (r.window ? ` <span class="sub">${r.window}</span>` : "");
}

function tile(k, v, cls="") { return `<div class="tile"><div class="k">${k}</div><div class="v mono ${cls}">${v}</div></div>`; }
function pnlCls(v) { return v > 0 ? "pos" : v < 0 ? "neg" : ""; }

async function refresh() {
  let d;
  try { d = await (await fetch("/api/status")).json(); }
  catch { document.getElementById("updated").textContent = "接続エラー"; return; }
  setPill("p-main", "メインBOT", d.components.main_bot);
  setPill("p-scalp", "スキャルパー", d.components.scalper);
  setPill("p-ws", "板記録", d.components.ws_recorder);
  setRadar(d.radar || {});
  document.getElementById("updated").textContent =
    "更新 " + new Date(d.generated_at * 1000).toLocaleTimeString("ja-JP");

  const banner = document.getElementById("banner");
  if (d.kill_switch || d.manual_kill_file) {
    banner.style.display = "block";
    banner.textContent = "⛔ Kill Switch 発動中: " +
      (d.kill_switch ? `${d.kill_switch.reason} — ${d.kill_switch.detail || ""}` : "手動KILLファイル");
  } else banner.style.display = "none";

  const b = d.bot || {};
  document.getElementById("tiles").innerHTML =
    tile("モード", (b.mode || "—").toUpperCase()) +
    tile("価格 (FX_BTC_JPY)", fmt(b.last_price, 0)) +
    tile("仮想残高", fmt(b.balance_jpy, 0) + " 円") +
    tile("本日損益", fmt(b.daily_pnl_jpy, 1) + " 円", pnlCls(b.daily_pnl_jpy)) +
    tile("累積損益", fmt(b.total_pnl_jpy, 1) + " 円", pnlCls(b.total_pnl_jpy)) +
    tile("最大DD", fmt(b.max_drawdown_pct, 2) + " %") +
    tile("ポジション", fmt(b.position_size, 4)) +
    tile("スキャル損益 / 回数", `${fmt(d.scalp.total_pnl_jpy, 0)}円 / ${d.scalp.trades}回`, pnlCls(d.scalp.total_pnl_jpy)) +
    tile("エラー数", fmt(b.error_count, 0));

  const dec = d.decisions || [];
  document.getElementById("t-dec").innerHTML = dec.length ?
    "<tr><th>時刻</th><th>シグナル</th><th>判断</th><th>理由</th></tr>" +
    dec.map(r => `<tr><td class="mono">${(r.timestamp || "").slice(11, 19)}</td>` +
      `<td>${r.strategy_signal || ""}</td><td>${r.decision || ""}</td>` +
      `<td>${(r.reason || "").slice(0, 60)}</td></tr>`).join("")
    : "<tr><td class='empty'>判断ログなし(シグナル待ちは正常です)</td></tr>";

  const sc = d.scalp.recent || [];
  document.getElementById("t-scalp").innerHTML = sc.length ?
    "<tr><th>時刻</th><th>イベント</th><th>方向</th><th class='num'>価格</th><th class='num'>損益</th></tr>" +
    sc.map(r => `<tr><td class="mono">${new Date(r.ts * 1000).toLocaleTimeString("ja-JP")}</td>` +
      `<td>${r.event}</td><td>${r.side || ""}</td>` +
      `<td class="num mono">${fmt(r.price, 0)}</td>` +
      `<td class="num mono">${r.pnl_jpy != null ? fmt(r.pnl_jpy, 1) : ""}</td></tr>`).join("")
    : "<tr><td class='empty'>イベントなし(激変動待ちは正常です)</td></tr>";

  const col = Object.entries(d.collectors || {});
  document.getElementById("t-col").innerHTML =
    "<tr><th>データ</th><th>最終更新</th><th class='num'>サイズ</th></tr>" +
    col.map(([k, v]) => `<tr><td>${k}</td><td>${v ? age(v.age_sec) : "未収集"}</td>` +
      `<td class="num mono">${v ? fmt(v.size / 1e6, 1) + " MB" : "—"}</td></tr>`).join("") +
    `<tr><td>板記録 (WS)</td><td>${d.ws.latest ? age(d.ws.latest.age_sec) : "未収集"}</td>` +
    `<td class="num mono">${fmt(d.ws.total_mb, 1)} MB / ${d.ws.files}ファイル</td></tr>` +
    oiRow(d.oi_snapshot);
}

// OI/DVOL snapshot recorder (scripts/record_oi.py): one row per collector run.
function oiRow(oi) {
  if (!oi) return `<tr><td>OIスナップショット</td><td>未収集</td><td class="num mono">—</td></tr>`;
  const last = oi.last || {};
  const vals = [
    last.dvol ? `DVOL ${fmt(last.dvol, 2)}` : null,
    last.okx_usdt_oi ? `OKX OI ${fmt(last.okx_usdt_oi, 0)}` : null,
    last.okx_ls_ratio ? `L/S ${fmt(last.okx_ls_ratio, 2)}` : null,
  ].filter(Boolean).join(" / ");
  return `<tr><td>OIスナップショット${vals ? ` <span class="sub">${vals}</span>` : ""}</td>` +
    `<td>${age(oi.row_age_sec != null ? oi.row_age_sec : oi.age_sec)}</td>` +
    `<td class="num mono">${fmt(oi.size / 1e6, 2)} MB</td></tr>`;
}
refresh();
setInterval(refresh, 5000);
</script>
</body></html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/status"):
            body = json.dumps(collect_status(".")).encode()
            ctype = "application/json"
        elif self.path == "/" or self.path.startswith("/index"):
            body = PAGE.encode()
            ctype = "text/html; charset=utf-8"
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # keep the console quiet


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8300)
    args = ap.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"dashboard: http://127.0.0.1:{args.port}  (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
