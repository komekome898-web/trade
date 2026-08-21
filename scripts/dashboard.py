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
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bot.monitoring.aggregate import collect_status  # noqa: E402
from bot.monitoring.market_view import PRODUCT, collect_market  # noqa: E402

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
  .tile .v .sub { font-size: 12px; }
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
  [hidden] { display: none !important; }

  /* ---- tabs ---- */
  nav.tabs { display: flex; gap: 4px; padding: 0 20px; background: var(--bg);
             border-bottom: 1px solid var(--line); position: sticky; top: 52px; z-index: 4; }
  nav.tabs button { background: none; border: 0; border-bottom: 2px solid transparent;
                    color: var(--muted); font: inherit; font-size: 13px;
                    padding: 9px 14px; cursor: pointer; }
  nav.tabs button:hover { color: var(--ink); }
  nav.tabs button.on { color: var(--ink); border-bottom-color: var(--accent); }

  /* ---- market: shared semantics (up / down / flat, never the accent) ---- */
  .up { color: var(--ok); } .down { color: var(--crit); } .flat { color: var(--muted); }
  .arw { width: 22px; height: 22px; vertical-align: -6px; }
  .arw path { fill: none; stroke: currentColor; stroke-width: 2;
              stroke-linecap: round; stroke-linejoin: round; }
  .bar { display: inline-block; width: 56px; height: 6px; border-radius: 3px;
         background: color-mix(in srgb, var(--line) 70%, transparent);
         vertical-align: middle; overflow: hidden; }
  .bar i { display: block; height: 100%; background: currentColor; }
  .strip { display: flex; align-items: center; gap: 8px 18px; flex-wrap: wrap; padding: 12px 14px; }
  .strip .big { font-size: 20px; }
  .strip .k { color: var(--muted); font-size: 11px; letter-spacing: .06em;
              text-transform: uppercase; margin-right: 4px; }
  .pill.storm { color: var(--crit); border-color: var(--crit); } .pill.storm i { background: var(--crit); }
  .pill.brk { color: var(--warn); border-color: var(--warn); } .pill.brk i { background: var(--warn); }
  .pill.calm { color: var(--ok); border-color: color-mix(in srgb, var(--ok) 40%, var(--line)); }
  .pill.calm i { background: var(--ok); }
  .pill.stale { color: var(--muted); border-color: var(--line); } .pill.stale i { background: var(--muted); }
  .mkt-grid { display: grid; grid-template-columns: 1fr 260px; gap: 20px; }
  @media (max-width: 900px) { .mkt-grid { grid-template-columns: 1fr; } }
  .oi { padding: 12px 14px; display: flex; flex-direction: column; gap: 8px; }
  .oi .row { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
  .oi .row .k { color: var(--muted); font-size: 11.5px; }
  .tfbar { display: flex; gap: 6px; padding: 10px 14px 0; flex-wrap: wrap; }
  .tfbar button { background: var(--bg); border: 1px solid var(--line); border-radius: 6px;
                  color: var(--muted); font: inherit; font-size: 12px; padding: 3px 11px;
                  cursor: pointer; }
  .tfbar button.on { color: var(--ink); border-color: var(--accent); }
  .chartwrap { position: relative; padding: 10px 14px 6px; }
  canvas { display: block; width: 100%; }
  .tip { position: absolute; pointer-events: none; display: none; z-index: 3;
         background: var(--bg); border: 1px solid var(--line); border-radius: 6px;
         padding: 6px 9px; font-size: 11.5px; white-space: pre; }
  .legend { display: flex; gap: 16px; flex-wrap: wrap; color: var(--muted);
            font-size: 11.5px; padding: 0 14px 12px; }
  .legend b { font-weight: 500; }
</style></head><body>
<header>
  <h1>Bot <span>Console</span></h1>
  <span class="pill" id="p-main"><i></i>メインBOT</span>
  <span class="pill" id="p-scalp"><i></i>スキャルパー</span>
  <span class="pill" id="p-ws"><i></i>板記録</span>
  <span class="pill" id="p-radar"><i></i>レーダー</span>
  <span class="pill" id="p-modules"><i></i>モジュール</span>
  <span id="updated">—</span>
</header>
<nav class="tabs">
  <button id="tab-console" class="on" onclick="showTab('console')">Botコンソール</button>
  <button id="tab-market" onclick="showTab('market')">マーケット</button>
</nav>
<main id="view-console">
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
<main id="view-market" hidden>
  <section>
    <h2>現在の状態</h2>
    <div class="strip" id="m-strip"><span class="empty">読込中…</span></div>
  </section>
  <div class="mkt-grid">
    <section>
      <h2>時間足別 トレンド / 値幅 / 出来高</h2>
      <div class="scroll"><table id="t-tf"></table></div>
    </section>
    <section>
      <h2>建玉 (OKX USDT) / IV</h2>
      <div class="oi" id="m-oi"></div>
    </section>
  </div>
  <section>
    <h2>チャート <span class="sub" id="m-chart-sub"></span></h2>
    <div class="tfbar" id="m-tfs"></div>
    <div class="chartwrap"><canvas id="m-chart"></canvas><div class="tip" id="m-tip"></div></div>
    <div class="legend" id="m-legend"></div>
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

// Composite modules (bot/strategy/composite.py). null = the running strategy
// has no module framework at all; [] = framework present, nothing enabled —
// deliberately different facts, so the pill is hidden only in the null case.
function setModules(mods) {
  const el = document.getElementById("p-modules");
  if (mods == null) { el.style.display = "none"; return; }
  el.style.display = "";
  el.className = "pill" + (mods.length ? " warn" : "");
  el.innerHTML = `<i></i>モジュール: ` +
    (mods.length ? mods.join(", ") : "なし");
}

function tile(k, v, cls="") { return `<div class="tile"><div class="k">${k}</div><div class="v mono ${cls}">${v}</div></div>`; }
function pnlCls(v) { return v > 0 ? "pos" : v < 0 ? "neg" : ""; }

// Risk overlay (bot/strategy/composite.py: size_factor). null = the running
// strategy has no overlay, which is not the same as an overlay sitting at full
// size — so the tile is omitted entirely rather than shown as x1.00.
function overlayTile(ov) {
  if (ov == null) return "";
  const brake = ov.factor != null && ov.factor < 1;
  return tile("リスクオーバーレイ",
    `x${fmt(ov.factor, 2)} <span class="sub">連敗 ${fmt(ov.consecutive_losses, 0)} / ` +
    `DD ${fmt(ov.dd_pct, 2)}%</span>`, brake ? "neg" : "");
}

async function refresh() {
  let d;
  try { d = await (await fetch("/api/status")).json(); }
  catch { document.getElementById("updated").textContent = "接続エラー"; return; }
  setPill("p-main", "メインBOT", d.components.main_bot);
  setPill("p-scalp", "スキャルパー", d.components.scalper);
  setPill("p-ws", "板記録", d.components.ws_recorder);
  setRadar(d.radar || {});
  setModules(d.active_modules);
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
    tile("エラー数", fmt(b.error_count, 0)) +
    overlayTile(d.overlay);

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
// ===========================================================================
// マーケットタブ — /api/market (bot/monitoring/market_view.collect_market)
// ===========================================================================
const MC = {up: "#46b87a", down: "#e0604f", flat: "#93a0b8", accent: "#4cc8cf",
            grid: "rgba(34,48,80,.9)", band: "rgba(76,200,207,.07)"};
const STATE_CLS = {"嵐": "storm", "ブレイク": "brk", "静穏レンジ": "calm", "通常": ""};
const VOTE_NAME = {ema_cross: "EMA12/48", ema_slope: "EMA48の傾き", rsi: "RSI14"};
let marketData = null, marketTimer = null, chartTf = "15m", chartGeom = null;

const dirCls = v => v > 0 ? "up" : v < 0 ? "down" : "flat";
const dirGlyph = v => v > 0 ? "▲" : v < 0 ? "▼" : "─";
const pct = (v, d=2) => v == null ? "—" : (v > 0 ? "+" : "") + Number(v).toFixed(d) + "%";
const signed = v => v == null ? "—" : (v > 0 ? "+" : "") + v;
// bars carry UTC epoch seconds; only the label is JST
const jst = ts => new Date(ts * 1000).toLocaleString("ja-JP",
  {timeZone: "Asia/Tokyo", month: "2-digit", day: "2-digit",
   hour: "2-digit", minute: "2-digit"});

function showTab(name) {
  for (const t of ["console", "market"]) {
    const view = document.getElementById("view-" + t);
    const btn = document.getElementById("tab-" + t);
    if (view) view.hidden = (t !== name);
    if (btn) btn.className = (t === name) ? "on" : "";
  }
  if (name === "market") {
    refreshMarket();
    if (!marketTimer) marketTimer = setInterval(refreshMarket, 30000);
  } else if (marketTimer) { clearInterval(marketTimer); marketTimer = null; }
}

// Slope arrow. SVG y grows downward, so a rising slope (positive angle) is
// drawn as a negative rotation.
function arrowSvg(angle) {
  if (angle == null) return '<span class="flat">—</span>';
  return `<span class="${dirCls(angle)}" title="傾き ${Number(angle).toFixed(0)}°">` +
    `<svg class="arw" viewBox="0 0 24 24" aria-hidden="true">` +
    `<g transform="rotate(${(-angle).toFixed(1)} 12 12)">` +
    `<path d="M4 12h14M13 7l5 5-5 5"/></g></svg></span>`;
}

// The tooltip lists every vote, including the ones that had too little data:
// +2 out of 2 votes is not the same fact as +2 out of 3.
function trendCell(t) {
  if (!t || t.score == null) return '<span class="flat">— <span class="sub">データ不足</span></span>';
  const v = t.votes || {};
  const tip = Object.keys(VOTE_NAME).map(k =>
      `${VOTE_NAME[k]}: ${v[k] == null ? "データ不足" : signed(v[k])}`).join(" / ") +
    `\n有効票 ${t.votes_available}/3` + (t.rsi != null ? ` / RSI ${t.rsi}` : "");
  return `<span class="${dirCls(t.score)}" title="${tip}">${dirGlyph(t.score)} ` +
    `${t.strength || ""} <span class="mono">${signed(t.score)}</span> ` +
    `<span class="bar"><i style="width:${Math.abs(t.score) / 3 * 100}%"></i></span></span>` +
    (t.votes_available < 3 ? ` <span class="sub">${t.votes_available}/3票</span>` : "");
}

function volCell(v) {
  if (!v || v.atr_pct == null) return '<span class="flat">—</span>';
  return `<span class="mono">${Number(v.atr_pct).toFixed(2)}%</span> ` +
    `<span class="sub mono">${fmt(v.atr, 0)}円</span> ${arrowSvg(v.angle_deg)}`;
}

function volumeCell(v) {
  if (!v) return '<span class="flat">—</span>';
  return `${arrowSvg(v.angle_deg)} <span class="mono sub">${signed(v.score)}</span>`;
}

// OI is a single series, not a per-timeframe one, so it lives beside the table
// rather than pretending to have a row per timeframe.
function renderOi(oi) {
  const el = document.getElementById("m-oi");
  if (!el) return;
  if (!oi) { el.innerHTML = '<span class="empty">OIスナップショット未収集</span>'; return; }
  const row = (k, v) => `<div class="row"><span class="k">${k}</span><span class="mono">${v}</span></div>`;
  el.innerHTML =
    `<div class="row"><span class="k">OKX USDT建 OI</span><span>${arrowSvg(oi.angle_deg)} ` +
      `<span class="mono ${dirCls(oi.score)}">${signed(oi.score)}</span></span></div>` +
    row("現在値", fmt(oi.last, 0)) +
    (oi.ls_ratio != null ? row("L/S比", fmt(oi.ls_ratio, 2)) : "") +
    (oi.dvol != null ? row("DVOL", fmt(oi.dvol, 2)) : "") +
    row("記録", `${oi.points}点 / ${oi.history_hours != null ? fmt(oi.history_hours, 1) + "時間" : "—"}`) +
    `<div class="sub" style="font-size:11px">15分毎。OI系ゲートの判定基準は30日分 ` +
    `(KNOWLEDGE §4) — 未到達なので、これは読み値であってシグナルではない。</div>`;
}

function renderTfBar() {
  const el = document.getElementById("m-tfs");
  const ch = marketData && marketData.chart;
  if (!el) return;
  el.innerHTML = ch ? Object.keys(ch.tfs).map(tf =>
    `<button class="${tf === chartTf ? "on" : ""}" onclick="setChartTf('${tf}')">` +
    `${ch.tfs[tf].label}</button>`).join("") : "";
}

function setChartTf(tf) { chartTf = tf; renderTfBar(); renderChart(); }

function renderChart() {
  const ch = marketData && marketData.chart;
  const p = ch ? ch.tfs[chartTf] : null;
  chartGeom = drawChart(p, document.getElementById("m-chart"));
  const sub = document.getElementById("m-chart-sub");
  if (sub) sub.textContent = p
    ? `${p.label} / ${p.bars.length}本` + (p.dropped ? ` / 表示範囲外の取引 ${p.dropped}件` : "")
    : "データなし";
  const lg = document.getElementById("m-legend");
  if (lg) lg.innerHTML = p ? [
    '<span><b class="up">▲</b> ロング建て</span>',
    '<span><b class="down">▼</b> ショート建て</span>',
    '<span><b>✕</b> 決済 (色 = 損益の符号 / 灰 = 不明)</span>',
    '<span>小さいマーカー = スキャルパー</span>',
    p.range ? `<span>帯 = 直近${p.range.window_min}分レンジ ` +
      `${fmt(p.range.low, 0)}〜${fmt(p.range.high, 0)}</span>` : "",
  ].join("") : "";
}

function renderMarket(d) {
  marketData = d;
  const s = d.state, strip = document.getElementById("m-strip");
  const src = d.sources || {};
  const meta = `<span class="sub">${d.product} · ローソク足 ${fmt(src.candles, 0)}行 / ` +
    `取引 ${fmt((src.bot_events || 0) + (src.scalp_events || 0), 0)}件 · ` +
    `更新 ${new Date(d.generated_at * 1000).toLocaleTimeString("ja-JP")}</span>`;
  if (strip && !s) {
    strip.innerHTML = '<span class="empty">ローソク足データなし ' +
      '(data/candles_FX_BTC_JPY.csv 未収集)</span>' + meta;
  } else if (strip) {
    const r = s.radar || {};
    // s.state == null means the feed is stale: say the collector stopped
    // instead of labelling day-old candles 静穏レンジ.
    const statePill = s.stale || !s.state
      ? `<span class="pill stale" title="最終足 ${jst(s.last_ts)} JST — ` +
        `収集が停止している可能性 (${fmt(s.age_sec, 0)}秒経過)"><i></i>` +
        `データ停止 ${age(s.age_sec)}</span>`
      : `<span class="pill ${STATE_CLS[s.state] || ""}" title="嵐 = |30分log収益| ≥ 0.8% / ` +
        `静穏レンジ = |30分| < 0.4% かつ 直近10分に |1分| ≥ 0.15% なし / ` +
        `ブレイク = 直近15分に240分高安を更新"><i></i>${s.state}` +
        `${s.approx ? ` <span class="sub">${s.approx}</span>` : ""}</span>`;
    strip.innerHTML =
      statePill +
      `<span class="pill${r.armed ? " warn" : ""}" title="${r.reason || ""}"><i></i>` +
        `レーダー: ${r.armed ? "武装中" : "待機"}` +
        `${r.window ? ` <span class="sub">${r.window}</span>` : ""}</span>` +
      `<span><span class="k">価格</span><span class="big mono">${fmt(s.last_price, 0)}</span></span>` +
      `<span><span class="k">30分</span>` +
        `<span class="mono ${dirCls(s.ret_30m_pct)}">${pct(s.ret_30m_pct)}</span></span>` +
      `<span><span class="k">24時間</span>` +
        `<span class="mono ${dirCls(s.ret_24h_pct)}">${pct(s.ret_24h_pct)}</span></span>` +
      `<span class="sub">足 ${age(s.age_sec)}</span>` +
      (d.flow ? `<span><span class="k">買い比率 ${d.flow.window_min}分</span>` +
        `<span class="mono ${dirCls(d.flow.buy_pct - 50)}">${fmt(d.flow.buy_pct, 1)}%</span></span>` : "") +
      meta;
  }

  const tfs = d.timeframes || [];
  const table = document.getElementById("t-tf");
  const shown = tfs.filter(t => t.bars > 0);
  if (table) table.innerHTML = shown.length ?
    "<tr><th>時間足</th><th>トレンド</th><th>ボラ (値幅)</th><th>出来高</th><th class='num'>終値</th></tr>" +
    shown.map(t => `<tr><td>${t.label} <span class="sub">${t.bars}本</span></td>` +
      `<td>${trendCell(t.trend)}</td><td>${volCell(t.volatility)}</td>` +
      `<td>${volumeCell(t.volume)}</td>` +
      `<td class="num mono">${fmt(t.last_close, 0)}</td></tr>`).join("")
    : "<tr><td class='empty'>ローソク足データなし</td></tr>";

  renderOi(d.oi);
  if (d.chart && !d.chart.tfs[chartTf]) chartTf = d.chart.default_tf;
  renderTfBar();
  renderChart();
  return d;
}

// Candlestick chart. No libraries: bars, the 240m range band, and the trade
// markers, drawn at devicePixelRatio so the hairlines stay crisp.
function drawChart(payload, canvas, width) {
  if (!canvas || !canvas.getContext) return null;
  const ctx = canvas.getContext("2d");
  const bars = (payload && payload.bars) || [];
  const W = Math.max(320, width ||
    (canvas.parentElement && canvas.parentElement.clientWidth) || 760);
  const H = 340;
  const dpr = (typeof window !== "undefined" && window.devicePixelRatio) || 1;
  canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
  canvas.style.width = W + "px"; canvas.style.height = H + "px";
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);
  if (!bars.length) {
    ctx.fillStyle = MC.flat; ctx.font = "13px system-ui";
    ctx.fillText("チャートデータなし", 14, 30);
    return null;
  }
  const padL = 10, padR = 72, padT = 12, padB = 24;
  const plotW = W - padL - padR, plotH = H - padT - padB;
  let hi = -Infinity, lo = Infinity;
  for (const b of bars) { if (b.h > hi) hi = b.h; if (b.l < lo) lo = b.l; }
  const rg = payload.range;
  if (rg) { hi = Math.max(hi, rg.high); lo = Math.min(lo, rg.low); }
  for (const m of payload.markers || []) {
    if (m.price > hi) hi = m.price;
    if (m.price < lo) lo = m.price;
  }
  const pad = (hi - lo) * 0.06 || Math.max(1, Math.abs(hi) * 0.001);
  hi += pad; lo -= pad;
  const span = (hi - lo) || 1;
  const y = p => padT + (hi - p) / span * plotH;
  const step = plotW / bars.length;
  const cw = Math.max(1, Math.min(14, step * 0.66));
  const xc = i => padL + step * (i + 0.5);

  if (rg) {  // trailing range band
    ctx.fillStyle = MC.band;
    ctx.fillRect(padL, y(rg.high), plotW, Math.max(1, y(rg.low) - y(rg.high)));
    ctx.strokeStyle = MC.accent; ctx.lineWidth = 1; ctx.setLineDash([4, 4]);
    for (const p of [rg.high, rg.low]) {
      const yy = Math.round(y(p)) + 0.5;
      ctx.beginPath(); ctx.moveTo(padL, yy); ctx.lineTo(padL + plotW, yy); ctx.stroke();
    }
    ctx.setLineDash([]);
  }

  ctx.font = "11px ui-monospace, Consolas, monospace"; ctx.textAlign = "left";
  for (let k = 0; k <= 4; k++) {   // price grid + right-hand axis
    const p = lo + span * k / 4, yy = Math.round(y(p)) + 0.5;
    ctx.strokeStyle = MC.grid;
    ctx.beginPath(); ctx.moveTo(padL, yy); ctx.lineTo(padL + plotW, yy); ctx.stroke();
    ctx.fillStyle = MC.flat;
    ctx.fillText(Math.round(p).toLocaleString("ja-JP"), padL + plotW + 6, yy + 4);
  }
  ctx.textAlign = "center"; ctx.fillStyle = MC.flat;
  for (const i of [0, Math.floor(bars.length / 2), bars.length - 1]) {
    const x = Math.min(Math.max(xc(i), padL + 34), padL + plotW - 34);
    ctx.fillText(jst(bars[i].ts), x, H - 8);
  }

  for (let i = 0; i < bars.length; i++) {
    const b = bars[i], x = Math.round(xc(i)) + 0.5;
    ctx.strokeStyle = ctx.fillStyle = (b.c >= b.o) ? MC.up : MC.down;
    ctx.globalAlpha = b.partial ? 0.5 : 1;   // the still-forming bar is dimmed
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x, y(b.h)); ctx.lineTo(x, y(b.l)); ctx.stroke();
    const top = y(Math.max(b.o, b.c)), bot = y(Math.min(b.o, b.c));
    ctx.fillRect(x - cw / 2, top, cw, Math.max(1, bot - top));
    ctx.globalAlpha = 1;
  }

  for (const m of payload.markers || []) {
    const x = xc(m.bar), yy = y(m.price);
    const small = m.source === "scalp", s = small ? 4.5 : 7;
    ctx.globalAlpha = small ? 0.8 : 1;
    if (m.kind === "entry") {
      const long = String(m.side || "").toUpperCase() === "LONG";
      ctx.fillStyle = long ? MC.up : MC.down;
      ctx.beginPath();
      if (long) {
        ctx.moveTo(x, yy - s); ctx.lineTo(x + s, yy + s * 0.8); ctx.lineTo(x - s, yy + s * 0.8);
      } else {
        ctx.moveTo(x, yy + s); ctx.lineTo(x + s, yy - s * 0.8); ctx.lineTo(x - s, yy - s * 0.8);
      }
      ctx.closePath(); ctx.fill();
    } else {
      ctx.strokeStyle = m.pnl == null ? MC.flat : (m.pnl > 0 ? MC.up : MC.down);
      ctx.lineWidth = small ? 1.4 : 2;
      ctx.beginPath();
      ctx.moveTo(x - s, yy - s); ctx.lineTo(x + s, yy + s);
      ctx.moveTo(x + s, yy - s); ctx.lineTo(x - s, yy + s);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }
  return {padL: padL, padR: padR, step: step, bars: bars, W: W, H: H, hi: hi, lo: lo};
}

function chartHover(ev) {
  const tip = document.getElementById("m-tip"), g = chartGeom;
  if (!tip) return;
  if (!g) { tip.style.display = "none"; return; }
  const rect = ev.currentTarget.getBoundingClientRect();
  const x = ev.clientX - rect.left;
  const i = Math.floor((x - g.padL) / g.step);
  if (i < 0 || i >= g.bars.length) { tip.style.display = "none"; return; }
  const b = g.bars[i];
  tip.innerHTML = `${jst(b.ts)} JST${b.partial ? " (形成中)" : ""}\n` +
    `始 ${fmt(b.o, 0)}   高 ${fmt(b.h, 0)}\n安 ${fmt(b.l, 0)}   終 ${fmt(b.c, 0)}\n` +
    `出来高 ${fmt(b.v, 3)}`;
  tip.style.display = "block";
  tip.style.left = Math.min(Math.max(x - 60, 8), g.W - 150) + "px";
  tip.style.top = "18px";
}

(function initMarket() {
  const c = document.getElementById("m-chart");
  if (c && c.addEventListener) {
    c.addEventListener("mousemove", chartHover);
    c.addEventListener("mouseleave", () => {
      const t = document.getElementById("m-tip");
      if (t) t.style.display = "none";
    });
  }
  if (typeof window !== "undefined" && window.addEventListener) {
    window.addEventListener("resize", () => { if (marketData) renderChart(); });
  }
})();

async function refreshMarket() {
  let d;
  try { d = await (await fetch("/api/market")).json(); }
  catch {
    const s = document.getElementById("m-strip");
    if (s) s.innerHTML = '<span class="empty">接続エラー</span>';
    return;
  }
  renderMarket(d);
}

refresh();
setInterval(refresh, 5000);
</script>
</body></html>
"""


# ---------------------------------------------------------------------------
# /api/market cache
#
# collect_market re-parses every candle in data/ (tens of thousands of rows).
# The page polls it every 30s per open tab, so the answer is cached and only
# rebuilt when one of the files it reads has actually changed — with a floor of
# MARKET_TTL seconds so a busy collector cannot make every poll a full re-parse.
# ---------------------------------------------------------------------------
MARKET_FILES = (f"data/candles_{PRODUCT}.csv", f"data/flow_{PRODUCT}.csv",
                "data/oi_snapshots.csv", "logs/bot.jsonl",
                "data/scalp_paper.jsonl")
MARKET_TTL = 15.0
_market_lock = threading.Lock()
_market_cache: dict[str, object] = {"key": None, "at": 0.0, "body": b"", "root": None}


def _market_key(root: str = ".") -> tuple:
    """(mtime_ns, size) of every file collect_market reads; missing -> None.

    The root is part of the key so a differently-rooted call (tests) can never
    be answered from another root's cache.
    """
    out: list = [str(root)]
    for rel in MARKET_FILES:
        try:
            st = (Path(root) / rel).stat()
            out.append((st.st_mtime_ns, st.st_size))
        except OSError:
            out.append(None)
    return tuple(out)


def market_body(root: str = ".", now: float | None = None) -> bytes:
    """The /api/market JSON, from cache when nothing it reads has changed."""
    now = time.monotonic() if now is None else now
    with _market_lock:
        cached = _market_cache["body"] if _market_cache["root"] == str(root) else b""
        if cached and (now - _market_cache["at"]) < MARKET_TTL:
            return cached
        key = _market_key(root)
        if cached and key == _market_cache["key"]:
            _market_cache["at"] = now      # unchanged files: re-arm the TTL
            return cached
        body = json.dumps(collect_market(root)).encode()
        _market_cache.update({"key": key, "at": now, "body": body, "root": str(root)})
        return body


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/status"):
            body = json.dumps(collect_status(".")).encode()
            ctype = "application/json"
        elif self.path.startswith("/api/market"):
            body = market_body(".")
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
