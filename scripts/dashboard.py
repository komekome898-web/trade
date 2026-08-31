#!/usr/bin/env python3
"""Local operations dashboard — serves http://127.0.0.1:8300 with live bot
state, scalp trades, kill-switch status and data-collection health.

Read-only over local files and binds to localhost only. Two READ-ONLY public
bitFlyer endpoints are polled for the マーケット tab — /v1/board for the depth
panel and /v1/executions for the live 1m tail. No auth, no keys, no order
endpoints; both are cached for at least PUBLIC_TTL seconds and both fail soft,
so the page renders offline exactly as it did before they existed. Worst case
they add 2 requests per PUBLIC_TTL seconds (0.4 req/s) against the 500 per
5 minutes per-IP public budget the bot also draws on.

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

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bot.monitoring.aggregate import collect_status  # noqa: E402
from bot.monitoring.market_view import (  # noqa: E402
    PRODUCT, attach_board, bars_from_executions, collect_market,
)

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
  .pill.retired i { background: var(--muted); } .pill.retired { color: var(--muted); }
  #updated { margin-left: auto; color: var(--muted); font-size: 12px; }
  main { padding: 20px; max-width: 1200px; margin: 0 auto;
         display: flex; flex-direction: column; gap: 20px; }
  .banner {
    background: color-mix(in srgb, var(--crit) 16%, var(--panel));
    border: 1px solid var(--crit); border-radius: 8px; padding: 12px 16px;
    display: none;
  }
  /* 168px, not 150: the widest tile value (ポジション: LONG 0.013 @ 11,234,567)
     is auto-shrunk to fit the NARROWEST tile, and at 150px that dropped it to
     ~12px. See TILE_W in the script — the two numbers are one decision. */
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(168px, 1fr)); gap: 12px; }
  .tile { background: var(--panel); border: 1px solid var(--line);
          border-radius: 8px; padding: 12px 14px; }
  .tile .k { color: var(--muted); font-size: 11px; letter-spacing: .06em;
             text-transform: uppercase; }
  /* A 小窓 that wraps to two lines pushes every row below it down and the
     tile grid stops lining up. The value therefore NEVER wraps: it is one
     line, clipped with an ellipsis as a last resort, and the font is stepped
     down to the string's own length by tileFont() so the clip is never
     actually reached at realistic values (¥1,234,567 / 12,345,678 /
     LONG 0.013 @ 11,234,567). The full text stays in the title attribute. */
  .tile .v { font-size: 22px; margin-top: 4px;
             white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .tile .v.pos { color: var(--ok); } .tile .v.neg { color: var(--crit); }
  .tile .v .sub { font-size: .55em; }
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
  /* collectors / gates: a progress bar sized by the pre-registered bar */
  .prog { display: inline-block; width: 90px; height: 6px; border-radius: 3px;
          background: color-mix(in srgb, var(--line) 70%, transparent);
          vertical-align: middle; overflow: hidden; margin-right: 8px; }
  .prog i { display: block; height: 100%; background: var(--accent); }
  .prog.done i { background: var(--ok); }
  .gates { display: flex; align-items: center; gap: 10px 20px; flex-wrap: wrap;
           padding: 10px 14px; }
  .gates .g { display: flex; align-items: center; gap: 8px; font-size: 12.5px; }
  .gates .g .k { color: var(--muted); }

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
  /* higher-timeframe direction strip: the trend table, compressed to chips and
     parked where the eye already is while scalping the 1m chart */
  .dirstrip { display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
              padding: 10px 14px 0; }
  .dirstrip .k { color: var(--muted); font-size: 11px; letter-spacing: .06em;
                 text-transform: uppercase; margin-right: 2px; }
  .chip { background: var(--bg); border: 1px solid var(--line); border-radius: 999px;
          color: var(--muted); font: inherit; font-size: 12px; padding: 2px 10px;
          cursor: pointer; font-variant-numeric: tabular-nums; }
  .chip.up { color: var(--ok); border-color: color-mix(in srgb, var(--ok) 45%, var(--line)); }
  .chip.down { color: var(--crit); border-color: color-mix(in srgb, var(--crit) 45%, var(--line)); }
  .chip.flat { color: var(--muted); }
  .chartwrap { position: relative; padding: 10px 14px 6px; }
  canvas { display: block; width: 100%; font-variant-numeric: tabular-nums; }
  .tip { position: absolute; pointer-events: none; display: none; z-index: 3;
         background: var(--bg); border: 1px solid var(--line); border-radius: 6px;
         padding: 6px 9px; font-size: 11.5px; white-space: pre;
         font-variant-numeric: tabular-nums; }
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
  <section>
    <h2>判定ゲート (確定済み判定と係属中の必要サンプル)</h2>
    <div class="gates" id="gates"></div>
  </section>
  <div class="grid2">
    <section>
      <h2>メインBOT: 最近の判断</h2>
      <div class="scroll"><table id="t-dec"></table></div>
    </section>
    <section>
      <h2>バーストスキャル(退役・棄却済み 第16報)</h2>
      <div class="scroll"><table id="t-scalp"></table></div>
    </section>
  </div>
  <section>
    <h2>BTC長期チャートと市場加熱度 <span class="sub">月次・2015年〜 / 表示専用(方向予測は棄却済み)</span></h2>
    <div class="chartwrap"><canvas id="a-chart"></canvas><div class="tip" id="a-tip"></div></div>
    <div class="legend" id="a-legend"></div>
  </section>
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
    <div class="dirstrip" id="m-dir"></div>
    <div class="tfbar" id="m-tfs"></div>
    <div class="chartwrap"><canvas id="m-chart"></canvas><div class="tip" id="m-tip"></div></div>
    <div class="legend" id="m-legend"></div>
  </section>
</main>
<script>
const fmt = (v, d=1) => v == null ? "—" : Number(v).toLocaleString("ja-JP", {maximumFractionDigits: d});
const age = s => s == null ? "—" : s < 90 ? `${Math.round(s)}秒前` : s < 5400 ? `${Math.round(s/60)}分前` : `${(s/3600).toFixed(1)}時間前`;
const stateLabel = {ok: "稼働中", warn: "遅延", down: "停止?", missing: "未起動", killed: "停止(Kill)", retired: "退役"};

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

// ---- tiles -----------------------------------------------------------------
// The tile value is one line, always (see .tile .v in the CSS). The font is
// stepped down to whatever the string actually is, so 「12,345,678」 and
// 「LONG 0.013 @ 11,234,567」 fit the same 168px 小窓 that holds 「PAPER」.
// TILE_W is the narrowest tile's content box (grid minmax 168px, 14px padding
// each side); TILE_CH is the monospace advance in em; the .sub run is .55em of
// the value (CSS), plus one space.
const TILE_W = 140, TILE_CH = 0.6, TILE_SUB = 0.55;
const TILE_MAX = 22, TILE_MIN = 11;
function tileFont(v, sub) {
  const units = TILE_CH * (String(v == null ? "" : v).length +
    (sub ? TILE_SUB * (String(sub).length + 1) : 0));
  if (!(units > 0)) return TILE_MAX;
  return Math.max(TILE_MIN, Math.min(TILE_MAX, TILE_W / units));
}
function tile(k, v, cls="", sub="") {
  const px = tileFont(v, sub).toFixed(1);
  const full = sub ? `${v} ${sub}` : String(v == null ? "" : v);
  return `<div class="tile"><div class="k">${k}</div>` +
    `<div class="v mono ${cls}" style="font-size:${px}px" title="${full}">${v}` +
    (sub ? ` <span class="sub">${sub}</span>` : "") + `</div></div>`;
}
function pnlCls(v) { return v > 0 ? "pos" : v < 0 ? "neg" : ""; }

// 収集の鮮度 (aggregate.py: ingest). data/tape shards carry their UTC day in
// the filename, so the value is that date and the sub-run is the file's age;
// data/venues has no date and shows the age alone. A missing file/directory
// is 未収集 — the tile renders, offline or not.
function ingestTile(k, v) {
  if (!v) return tile(k, "未収集");
  const day = v.date ? v.date.slice(5).replace("-", "/") : null;
  return tile(k, day || age(v.age_sec), "", day ? age(v.age_sec) : "");
}

// Position tile. A size on its own does not say whether the bot is winning:
// the entry price (status.json entry_price, portfolio.avg_entry_price) rides
// along as the sub-run. Flat is spelled out rather than shown as 0.0000.
function positionTile(b) {
  const size = b.position_size;
  if (!size) return tile("ポジション", "フラット");
  const side = size > 0 ? "LONG" : "SHORT";
  return tile("ポジション", `${side} ${fmt(Math.abs(size), 4)}`, "",
    b.entry_price != null ? `@ ${fmt(b.entry_price, 0)}` : "");
}

// Risk overlay (bot/strategy/composite.py: size_factor). null = the running
// strategy has no overlay, which is not the same as an overlay sitting at full
// size — so the tile is omitted entirely rather than shown as x1.00.
function overlayTile(ov) {
  if (ov == null) return "";
  const brake = ov.factor != null && ov.factor < 1;
  return tile("リスクオーバーレイ", `x${fmt(ov.factor, 2)}`, brake ? "neg" : "",
    `連敗 ${fmt(ov.consecutive_losses, 0)} / DD ${fmt(ov.dd_pct, 2)}%`);
}

// API状態 (bot/exchange/resilience.py). condition は NORMAL/DEGRADED/CRITICAL、
// p95 は data/api_health.csv の直近15分、health は /v1/gethealth の生文字列。
// DEGRADED 以上は赤 — 2019年の「板が重くて注文が通らない」を可視化するタイル。
function apiTile(a) {
  if (a == null) return "";
  const bad = a.condition && a.condition !== "NORMAL";
  const p95 = a.p95_ms != null ? fmt(a.p95_ms, 0) + "ms" : "—";
  // health は 3 ポーリング分で失効する。失効後は「不明」であって「正常」ではない。
  const age = a.health_age_sec != null ? `(${fmt(a.health_age_sec, 0)}秒前)` : "";
  const health = a.health ? a.health : `健全度不明${age}`;
  // status.json が古い(BOT停止/ハング)ときは CSV 最終行の値。断りを入れる。
  const stale = a.stale ? " ⚠️停止中の記録" : "";
  return tile("API状態", `${a.condition || "—"}${stale}`, bad ? "neg" : "",
    `p95 ${p95} / ${health}`);
}

// ON1 フォワード・ペーパー (aggregate.py: on1; docs/PREREG_on1_forward.md)。
// 日経225マイクロのオーバーナイト紙上取引。null = 台帳未生成 (fetch_all が
// scripts/paper_on1.py を書くまで) — その間も「未稼働」タイルで存在は見せる。
// guard は PREREG §3 の警告/停止線の現在値 (OK / 警告 / 停止)。
function on1Tiles(o) {
  if (o == null) return tile("ON1 紙上 (日経ON)", "未稼働");
  if (!o.trades) return tile("ON1 紙上 (日経ON)", "取引0", "", `スキップ ${o.skipped ?? 0}`);
  const guardBad = o.guard && o.guard !== "OK";
  const fr = o.friction_yen != null ? ` / 摩擦 ${fmt(o.friction_yen, 1)}円` : "";
  return tile("ON1 紙上損益", `${fmt(o.cum_net_yen, 0)}円`, pnlCls(o.cum_net_yen),
              `${fmt(o.mean_net_bps, 1)}bps ${o.trades}回`) +
         tile("ON1 監視線", o.guard || "—", guardBad ? "neg" : "pos",
              `〜${(o.last_exit_date || "").slice(4, 6)}/${(o.last_exit_date || "").slice(6, 8)}${fr}`);
}

// 市場加熱度 (aggregate.py: attention; docs/SURVEY_ATTENTION_DATA.md)。
// Wikipedia閲覧数(日本語/英語)とGDELT報道量のローリング365日Zスコア + F&G。
// 表示専用 — これらからの方向予測は no-go として記録済み。F&G は約6〜7割が
// 価格由来の合成指数なので「注目」ではなく参考値として末尾に置く。
// z>2 は過熱(赤)。null = 未収集(fetch_all が fetch_attention.py を書くまで)。
function attentionTile(a) {
  if (a == null) return tile("市場加熱度", "未収集");
  if (a.z_wp_ja == null && a.z_wp_en == null) return tile("市場加熱度", "蓄積中");
  const z = a.z_wp_ja != null ? a.z_wp_ja : a.z_wp_en;
  const hot = z >= 2;
  const parts = [];
  if (a.z_wp_en != null) parts.push(`EN ${a.z_wp_en >= 0 ? "+" : ""}${fmt(a.z_wp_en, 1)}`);
  if (a.z_gdelt != null) parts.push(`報道 ${a.z_gdelt >= 0 ? "+" : ""}${fmt(a.z_gdelt, 1)}`);
  if (a.fng != null) parts.push(`F&G ${fmt(a.fng, 0)}`);
  return tile("市場加熱度 (注目Z)", `${z >= 0 ? "+" : ""}${fmt(z, 1)}σ`,
              hot ? "neg" : "", parts.join(" / "));
}

// ---- BTC長期チャート + 市場加熱度 (aggregate.py: attention_chart) ------------
// 上段: BTC/USD 月次終値の対数スケール折れ線 (アクセント1色)。
// 下段: 注目Zスコアの「正の部分のみ」を積み上げた加熱バー (JA/EN/報道の3系列、
// パレットは検証済み: #c08a20/#4a86d1/#d16a9e、セグメント間2pxギャップが
// CVD境界ペアの二次符号)。2軸重ね書きはしない — パネルを分けて各1軸。
// 表示専用: これらからの方向予測は no-go として記録済み (SURVEY_ATTENTION_DATA)。
const A_COLORS = { ja: "#c08a20", en: "#4a86d1", gd: "#d16a9e" };
const A_LABELS = { ja: "注目 日本語WP", en: "注目 英語WP", gd: "報道量 GDELT" };
let aSeries = [];

function drawAttentionChart() {
  const canvas = document.getElementById("a-chart");
  if (!canvas || !aSeries.length) return;
  const css = getComputedStyle(document.documentElement);
  const ink = css.getPropertyValue("--ink").trim(), muted = css.getPropertyValue("--muted").trim();
  const grid = css.getPropertyValue("--line").trim(), accent = css.getPropertyValue("--accent").trim();
  const panel = css.getPropertyValue("--panel").trim();
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.parentElement.clientWidth - 28, H = 320;
  canvas.style.width = W + "px"; canvas.style.height = H + "px";
  canvas.width = W * dpr; canvas.height = H * dpr;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);
  ctx.font = "11px ui-monospace, monospace";

  const padL = 46, padR = 8, padT = 6, xAxisH = 18, panelGap = 14;
  const priceH = Math.round((H - padT - xAxisH - panelGap) * 0.58);
  const barsH = H - padT - xAxisH - panelGap - priceH;
  const priceY0 = padT, priceY1 = padT + priceH;
  const barsY0 = priceY1 + panelGap, barsY1 = barsY0 + barsH;
  const n = aSeries.length, slot = (W - padL - padR) / n;
  const xOf = i => padL + slot * (i + 0.5);

  // -- price panel (log scale, one series, one axis)
  const prices = aSeries.map(r => r.p).filter(p => p > 0);
  const lo = Math.min(...prices), hi = Math.max(...prices);
  const yOfP = p => priceY1 - (Math.log(p) - Math.log(lo)) / (Math.log(hi) - Math.log(lo)) * priceH;
  ctx.strokeStyle = grid; ctx.fillStyle = muted; ctx.lineWidth = 1;
  for (const t of [300, 1000, 3000, 10000, 30000, 100000]) {
    if (t < lo || t > hi) continue;
    const y = yOfP(t);
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
    ctx.textAlign = "right";
    ctx.fillText(t >= 1000 ? "$" + (t/1000) + "k" : "$" + t, padL - 5, y + 3.5);
  }
  ctx.strokeStyle = accent; ctx.lineWidth = 2; ctx.beginPath();
  let started = false;
  aSeries.forEach((r, i) => {
    if (r.p == null) return;
    const x = xOf(i), y = yOfP(r.p);
    if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // -- heat bars panel (stacked positive z, one axis)
  const heat = aSeries.map(r =>
    Math.max(r.ja || 0, 0) + Math.max(r.en || 0, 0) + Math.max(r.gd || 0, 0));
  const zMax = Math.max(2, Math.ceil(Math.max(...heat)));
  const yOfZ = z => barsY1 - z / zMax * barsH;
  ctx.strokeStyle = grid; ctx.fillStyle = muted; ctx.lineWidth = 1;
  for (let t = 0; t <= zMax; t += (zMax > 4 ? 2 : 1)) {
    const y = yOfZ(t);
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
    ctx.textAlign = "right"; ctx.fillText("+" + t + "σ", padL - 5, y + 3.5);
  }
  const barW = Math.max(1, slot - 2);          // >=2px gap between bars
  aSeries.forEach((r, i) => {
    let yBase = barsY1;
    for (const k of ["ja", "en", "gd"]) {      // fixed stacking order
      const z = Math.max(r[k] || 0, 0);
      if (z <= 0) continue;
      const hPx = barsY1 - yOfZ(z);
      const yTop = yBase - hPx;
      ctx.fillStyle = A_COLORS[k];
      ctx.fillRect(xOf(i) - barW / 2, yTop, barW, Math.max(hPx - 2, 1));
      yBase = yTop;                            // 2px surface gap between segments
    }
  });

  // -- x axis: January of each year
  ctx.fillStyle = muted; ctx.textAlign = "center";
  aSeries.forEach((r, i) => {
    if (r.m.endsWith("-01")) ctx.fillText(r.m.slice(0, 4), xOf(i), H - 4);
  });

  // -- legend (chips carry identity; text stays in ink tokens)
  const legend = document.getElementById("a-legend");
  legend.innerHTML =
    `<span><i style="background:${accent}"></i>BTC/USD (対数)</span>` +
    Object.keys(A_COLORS).map(k =>
      `<span><i style="background:${A_COLORS[k]}"></i>${A_LABELS[k]}</span>`).join("") +
    `<span class="empty">加熱バー = 正のZのみ積算</span>`;

  // -- hover: crosshair + tooltip
  canvas.onmousemove = (ev) => {
    const rect = canvas.getBoundingClientRect();
    const i = Math.min(n - 1, Math.max(0, Math.round((ev.clientX - rect.left - padL) / slot - 0.5)));
    const r = aSeries[i];
    const tip = document.getElementById("a-tip");
    const zLine = k => r[k] != null ?
      `<span style="color:${A_COLORS[k]}">●</span> ${A_LABELS[k]} ${r[k] >= 0 ? "+" : ""}${r[k].toFixed(1)}σ` : null;
    tip.innerHTML = `<b>${r.m}</b><br>BTC $${fmt(r.p, 0)}<br>` +
      ["ja", "en", "gd"].map(zLine).filter(Boolean).join("<br>");
    tip.style.display = "block";
    tip.style.left = Math.min(ev.clientX - rect.left + 14, W - 150) + "px";
    tip.style.top = "10px";
    drawAttentionChart();                       // redraw base, then crosshair
    const c2 = canvas.getContext("2d");
    c2.setTransform(dpr, 0, 0, dpr, 0, 0);
    c2.strokeStyle = muted; c2.lineWidth = 1; c2.setLineDash([3, 3]);
    c2.beginPath(); c2.moveTo(xOf(i), padT); c2.lineTo(xOf(i), barsY1); c2.stroke();
    c2.setLineDash([]);
  };
  canvas.onmouseleave = () => {
    document.getElementById("a-tip").style.display = "none";
    drawAttentionChart();
  };
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
    positionTile(b) +
    tile("約定回数", fmt(b.trade_count, 0) + " 回") +
    tile("スキャル損益 / 回数", `${fmt(d.scalp.total_pnl_jpy, 0)}円`, pnlCls(d.scalp.total_pnl_jpy),
         `${d.scalp.trades}回`) +
    on1Tiles(d.on1) +
    attentionTile(d.attention) +
    tile("エラー数", fmt(b.error_count, 0)) +
    apiTile(d.api_health) +
    overlayTile(d.overlay) +
    ingestTile("収集: ticker", (d.ingest || {}).ticker) +
    ingestTile("収集: board_top", (d.ingest || {}).board_top) +
    ingestTile("収集: venues", (d.ingest || {}).venues);

  renderGates(d.gates || []);

  // long-horizon attention chart: redraw only when the monthly series changed
  const aNew = d.attention_chart || [];
  if (JSON.stringify(aNew) !== JSON.stringify(aSeries)) {
    aSeries = aNew;
    drawAttentionChart();
  }

  // 最近の判断: times in JST, reasons in Japanese, and — for the rows that
  // were actually trades — the fill price and, on an exit, the realized P&L.
  // All four are computed server-side (monitoring/aggregate.py) because
  // whether a filled order opened or closed depends on the whole log.
  const dec = d.decisions || [];
  document.getElementById("t-dec").innerHTML = dec.length ?
    "<tr><th>時刻 (JST)</th><th>シグナル</th><th>判断</th>" +
    "<th class='num'>約定価格</th><th class='num'>損益</th><th>理由</th></tr>" +
    dec.map(r => `<tr><td class="mono">${r.time_jst || ""}</td>` +
      `<td>${r.signal_ja || r.strategy_signal || ""}</td>` +
      `<td>${r.decision_ja || r.decision || ""}</td>` +
      `<td class="num mono">${r.fill_price != null ? fmt(r.fill_price, 0) : ""}</td>` +
      `<td class="num mono ${r.realized_pnl_jpy != null ? dirCls(r.realized_pnl_jpy) : ""}">` +
        `${r.realized_pnl_jpy != null ?
           (r.realized_pnl_jpy > 0 ? "+" : "") + fmt(r.realized_pnl_jpy, 1) + "円" : ""}</td>` +
      `<td title="${r.reason || ""}">${(r.reason_ja || r.reason || "").slice(0, 60)}</td></tr>`).join("")
    : "<tr><td class='empty'>判断ログなし(シグナル待ちは正常です)</td></tr>";

  const sc = d.scalp.recent || [];
  document.getElementById("t-scalp").innerHTML = sc.length ?
    "<tr><th>時刻</th><th>イベント</th><th>方向</th><th class='num'>価格</th><th class='num'>損益</th></tr>" +
    sc.map(r => `<tr><td class="mono">${new Date(r.ts * 1000).toLocaleTimeString("ja-JP")}</td>` +
      `<td>${r.event}</td><td>${r.side || ""}</td>` +
      `<td class="num mono">${fmt(r.price, 0)}</td>` +
      `<td class="num mono">${r.pnl_jpy != null ? fmt(r.pnl_jpy, 1) : ""}</td></tr>`).join("")
    : "<tr><td class='empty'>イベントなし(退役済み — 記録のみ)</td></tr>";

  // データ収集: the plain collectors first (no pre-registered bar on them),
  // then one row per pending gate carrying 必要量 / 進捗 / 残り時間.
  const col = Object.entries(d.collectors || {});
  document.getElementById("t-col").innerHTML =
    "<tr><th>データ</th><th>最終更新</th><th class='num'>サイズ</th>" +
    "<th>必要量</th><th>進捗</th><th class='num'>残り時間</th></tr>" +
    col.map(([k, v]) => `<tr><td>${k}</td><td>${v ? age(v.age_sec) : "未収集"}</td>` +
      `<td class="num mono">${v ? fmt(v.size / 1e6, 1) + " MB" : "—"}</td>` +
      `<td class="sub">—</td><td class="sub">—</td><td class="num sub">—</td></tr>`).join("") +
    (d.gates || []).map(g => gateRow(g, d)).join("");
}

const UNIT_JA = {trades: "回", rows: "行", days: "日"};

// The remaining time is a projection at the rate the data has ACTUALLY been
// arriving (aggregate/gates.py: units accumulated / seconds observed), so it
// is always prefixed ≈. No rate — nothing collected yet, or the collector has
// never run — is "—", never an optimistic guess.
function eta(sec) {
  if (sec == null) return "—";
  if (sec <= 0) return "到達済み";
  if (sec < 86400) return `≈${(sec / 3600).toFixed(1)}時間`;
  if (sec < 86400 * 90) return `≈${(sec / 86400).toFixed(1)}日`;
  return `≈${(sec / 86400 / 30.44).toFixed(1)}ヶ月`;
}

function progBar(g) {
  return `<span class="prog${g.done ? " done" : ""}">` +
    `<i style="width:${Math.max(0, Math.min(100, g.pct || 0))}%"></i></span>`;
}

// A gate that has been formally judged (report in docs/, KNOWLEDGE §3/§5) is
// a settled fact: 判定済み + the registered numbers, never a progress bar —
// a bar would read as "still collecting toward a verdict" when the verdict
// already exists.
function verdictText(g) {
  return `判定済み: ${g.verdict}(${g.verdict_detail})— ${g.verdict_note}`;
}

function gateRow(g, d) {
  const u = UNIT_JA[g.unit] || "";
  const dec = g.unit === "days" ? 1 : 0;
  // the OI row keeps the live readings it always carried in its label
  const extra = g.key === "oi" ? oiValues(d.oi_snapshot) : "";
  const head = `<tr><td>${g.label}${extra}</td>` +
    `<td>${g.age_sec != null ? age(g.age_sec) : "未収集"}</td>` +
    `<td class="num mono sub">${g.detail || "—"}</td>` +
    `<td class="sub" title="${g.bar}">${g.bar}</td>`;
  if (g.verdict) {
    return head +
      `<td><span class="down">${verdictText(g)}</span> ` +
        `<span class="sub mono">${fmt(g.have, dec)}${u}収集済み</span></td>` +
      `<td class="num sub">—</td></tr>`;
  }
  return head +
    `<td>${progBar(g)}<span class="mono">${fmt(g.have, dec)}/${fmt(g.need, dec)}${u}</span> ` +
      `<span class="sub mono">${g.pct != null ? fmt(g.pct, 0) + "%" : "—"}</span></td>` +
    `<td class="num mono">${eta(g.eta_sec)}</td></tr>`;
}

// OI/DVOL snapshot recorder (scripts/record_oi.py): one row per collector run.
function oiValues(oi) {
  if (!oi) return "";
  const last = oi.last || {};
  const vals = [
    last.dvol ? `DVOL ${fmt(last.dvol, 2)}` : null,
    last.okx_usdt_oi ? `OKX OI ${fmt(last.okx_usdt_oi, 0)}` : null,
    last.okx_ls_ratio ? `L/S ${fmt(last.okx_ls_ratio, 2)}` : null,
  ].filter(Boolean).join(" / ");
  return vals ? ` <span class="sub">${vals}</span>` : "";
}

// 判定ゲート strip: the same numbers as the collectors table, compressed to
// one glanceable line — n/required for every pending pre-registered sample.
function renderGates(gates) {
  const el = document.getElementById("gates");
  if (!el) return;
  if (!gates.length) { el.innerHTML = '<span class="empty">係属ゲートなし</span>'; return; }
  el.innerHTML = gates.map(g => {
    const u = UNIT_JA[g.unit] || "";
    const dec = g.unit === "days" ? 1 : 0;
    if (g.verdict) {
      return `<span class="g" title="${verdictText(g)}">` +
        `<span class="k">${g.label}</span>` +
        `<span class="down">判定済み ${g.verdict}</span>` +
        `<span class="sub">${g.verdict_note}</span></span>`;
    }
    return `<span class="g" title="${g.bar} / 残り ${eta(g.eta_sec)}">` +
      `<span class="k">${g.label}</span>${progBar(g)}` +
      `<span class="mono${g.done ? " up" : ""}">${fmt(g.have, dec)}/${fmt(g.need, dec)}${u}</span>` +
      `<span class="sub mono">${eta(g.eta_sec)}</span></span>`;
  }).join("");
}
// ===========================================================================
// マーケットタブ — /api/market (bot/monitoring/market_view.collect_market)
// ===========================================================================
const MC = {up: "#46b87a", down: "#e0604f", flat: "#93a0b8", accent: "#4cc8cf",
            grid: "rgba(34,48,80,.9)", gridMajor: "rgba(147,160,184,.42)",
            band: "rgba(76,200,207,.07)", vol: "rgba(147,160,184,.45)",
            depthBid: "rgba(70,184,122,.55)", depthAsk: "rgba(224,96,79,.55)",
            depthLine: "rgba(147,160,184,.55)"};
const STATE_CLS = {"嵐": "storm", "ブレイク": "brk", "静穏レンジ": "calm", "通常": ""};
const VOTE_NAME = {ema_cross: "EMA12/48", ema_slope: "EMA48の傾き", rsi: "RSI14"};
// The 1m chart is where the scalping happens; the higher frames are read for
// direction, so they live in the chip strip above it, not in the chart.
const DIR_TFS = ["15m", "1h", "4h", "1d"];
const FAST_TF = "1m", FAST_POLL_MS = 10000, SLOW_POLL_MS = 30000;
let marketData = null, marketTimer = null, chartTf = "1m", chartGeom = null;

const dirCls = v => v > 0 ? "up" : v < 0 ? "down" : "flat";
const dirGlyph = v => v > 0 ? "▲" : v < 0 ? "▼" : "─";
const pct = (v, d=2) => v == null ? "—" : (v > 0 ? "+" : "") + Number(v).toFixed(d) + "%";
const signed = v => v == null ? "—" : (v > 0 ? "+" : "") + v;
// bars carry UTC epoch seconds; only the label is JST
const jst = ts => new Date(ts * 1000).toLocaleString("ja-JP",
  {timeZone: "Asia/Tokyo", month: "2-digit", day: "2-digit",
   hour: "2-digit", minute: "2-digit"});
const jstHm = ts => new Date(ts * 1000).toLocaleString("ja-JP",
  {timeZone: "Asia/Tokyo", hour: "2-digit", minute: "2-digit"});
const jstMd = ts => new Date(ts * 1000).toLocaleString("ja-JP",
  {timeZone: "Asia/Tokyo", month: "2-digit", day: "2-digit"});
// age() reads as "N ago"; a gap in the data is a duration, not a point in time
const dur = s => age(s).replace("前", "");

// A 1m scalp view is worthless at a 30s cadence; the slower frames do not move
// fast enough to be worth the extra polls.
function marketPollMs() { return chartTf === FAST_TF ? FAST_POLL_MS : SLOW_POLL_MS; }

function startMarketTimer() {
  if (marketTimer) clearInterval(marketTimer);
  marketTimer = setInterval(refreshMarket, marketPollMs());
}

function showTab(name) {
  for (const t of ["console", "market"]) {
    const view = document.getElementById("view-" + t);
    const btn = document.getElementById("tab-" + t);
    if (view) view.hidden = (t !== name);
    if (btn) btn.className = (t === name) ? "on" : "";
  }
  if (name === "market") {
    refreshMarket();
    startMarketTimer();
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

// Switching timeframe also switches the poll cadence: the 1m view is a live
// scalp view, the 4h view is not.
function setChartTf(tf) {
  const was = chartTf;
  chartTf = tf;
  renderTfBar();
  renderChart();
  if (marketTimer && marketPollMs() !== (was === FAST_TF ? FAST_POLL_MS : SLOW_POLL_MS)) {
    startMarketTimer();
  }
}

function showTrendTable() {
  const el = document.getElementById("t-tf");
  if (el && el.scrollIntoView) el.scrollIntoView({behavior: "smooth", block: "center"});
}

// The higher frames as chips — 「15分 ▲強」 — so the direction is readable
// without leaving the 1m chart. Clicking one jumps to the full table.
function renderDirStrip() {
  const el = document.getElementById("m-dir");
  if (!el) return;
  const by = {};
  for (const t of (marketData && marketData.timeframes) || []) by[t.tf] = t;
  const chips = DIR_TFS.map(tf => {
    const t = by[tf];
    if (!t || !t.trend || t.trend.score == null) return "";
    const s = t.trend.score;
    const tip = `${t.label}: スコア ${signed(s)} (有効票 ${t.trend.votes_available}/3)` +
      (t.trend.rsi != null ? ` / RSI ${t.trend.rsi}` : "");
    return `<button class="chip ${dirCls(s)}" title="${tip}" onclick="showTrendTable()">` +
      `${t.label} ${dirGlyph(s)}${s === 0 ? "" : (t.trend.strength || "")}</button>`;
  }).filter(Boolean).join("");
  el.innerHTML = chips ? '<span class="k">上位足の向き</span>' + chips : "";
}

function renderChart() {
  const ch = marketData && marketData.chart;
  const p = ch ? ch.tfs[chartTf] : null;
  chartGeom = drawChart(p, document.getElementById("m-chart"));
  const sub = document.getElementById("m-chart-sub");
  const live = p ? p.bars.filter(b => b.live).length : 0;
  if (sub) sub.textContent = p
    ? `${p.label} / ${p.bars.length}本` +
      (live ? ` / ライブ ${live}本` : "") +
      (p.dropped ? ` / 表示範囲外の取引 ${p.dropped}件` : "")
    : "データなし";
  const bd = marketData && marketData.board;
  const lg = document.getElementById("m-legend");
  if (lg) lg.innerHTML = p ? [
    '<span><b class="up">▲</b> ロング建て</span>',
    '<span><b class="down">▼</b> ショート建て</span>',
    '<span><b>✕</b> 決済 (色 = 損益の符号 / 灰 = 不明)</span>',
    '<span>小さいマーカー = スキャルパー</span>',
    p.range ? `<span>帯 = レンジ ${p.range.window_label} ` +
      `${fmt(p.range.low, 0)}〜${fmt(p.range.high, 0)}</span>` : "",
    `<span>下段 = 出来高 (<b class="up">緑</b>買い / <b class="down">赤</b>売り)</span>`,
    bd ? `<span>右 = 板 (<b class="down">赤</b>売り / <b class="up">緑</b>買い) ` +
      `スプレッド ${fmt(bd.spread, 0)}円 · ${boardAge(bd)}</span>`
       : '<span>右 = 板情報なし</span>',
    live ? '<span>半透明の足 = ライブ (公開約定から生成、CSV未確定)</span>' : "",
  ].join("") : "";
}

// The board snapshot carries the wall-clock second it was actually taken, so a
// frozen exchange shows as an ageing panel rather than as fresh depth.
function boardAge(bd) {
  if (!bd || bd.fetched_at == null) return "取得時刻不明";
  return "板 " + age(Date.now() / 1000 - bd.fetched_at);
}

function renderMarket(d) {
  marketData = d;
  const s = d.state, strip = document.getElementById("m-strip");
  const src = d.sources || {};
  const lv = d.live || {};
  const meta = `<span class="sub">${d.product} · ローソク足 ${fmt(src.candles, 0)}行 / ` +
    `取引 ${fmt((src.bot_events || 0) + (src.scalp_events || 0), 0)}件 · ` +
    // the CSV writer runs every ~15 min; these are the minutes the page built
    // itself from the public tape so the 1m view is not 15 minutes behind
    (lv.bars ? `ライブ追記 ${fmt(lv.bars, 0)}分` +
      // an hours-long hole means the収集 task is down: the tape keeps the price
      // live, but every window measured across the hole is refused, not faked
      (lv.gap_sec > 900 ? ` <b class="down">CSV欠落 ${dur(lv.gap_sec)}</b>` : "") +
      " · " : "公開約定の追記なし · ") +
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
  renderDirStrip();
  renderTfBar();
  renderChart();
  return d;
}

// Gridline label. 1m/15m read as clock time; the frames whose gridlines ARE
// days read as dates; a UTC midnight always gets its date, whatever the frame.
function gridTimeLabel(g, tf) {
  if (tf === "1d" || tf === "4h") return jstMd(g.ts);
  return g.major ? jstMd(g.ts) : jstHm(g.ts);
}

// Candlestick chart, no libraries. Three panes on ONE canvas so they cannot
// drift out of alignment: the price pane (trailing-range band, candles, trade
// markers), a volume pane under it sharing the x-axis, and an order-book depth
// panel beside it sharing the y-axis. The y-scale and both gridline ladders
// come from the server (market_view.chart_scale / time_grid): the depth panel
// aggregates the book onto exactly the price gridlines drawn here, and two
// independent "nice step" implementations would drift apart on the first tune.
function drawChart(payload, canvas, width) {
  if (!canvas || !canvas.getContext) return null;
  const ctx = canvas.getContext("2d");
  const bars = (payload && payload.bars) || [];
  const W = Math.max(320, width ||
    (canvas.parentElement && canvas.parentElement.clientWidth) || 760);
  const H = 420;
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

  // ---- geometry: price ~72% / volume ~20% of the body, depth ~15% of width
  const padL = 10, padR = 74, padT = 12, padB = 22, paneGap = 10;
  const fullW = W - padL - padR;
  const depthW = Math.max(46, Math.round(fullW * 0.15));
  const plotW = Math.max(80, fullW - depthW - 8);
  const bodyH = H - padT - padB;
  const volH = Math.max(38, Math.round(bodyH * 0.20));
  const priceH = bodyH - volH - paneGap;
  const volTop = padT + priceH + paneGap, volBot = volTop + volH;
  const depthX = padL + plotW + 8, depthRight = depthX + depthW;

  const sc = payload.scale || {};
  let hi = sc.hi, lo = sc.lo;
  if (hi == null || lo == null) {          // payload without a server scale
    hi = -Infinity; lo = Infinity;
    for (const b of bars) { if (b.h > hi) hi = b.h; if (b.l < lo) lo = b.l; }
    const pad = (hi - lo) * 0.06 || Math.max(1, Math.abs(hi) * 0.001);
    hi += pad; lo -= pad;
  }
  const span = (hi - lo) || 1;
  const y = p => padT + (hi - p) / span * priceH;
  const step = plotW / bars.length;
  const cw = Math.max(1, Math.min(14, step * 0.66));
  const xc = i => padL + step * (i + 0.5);
  const xl = i => padL + step * i;
  const vmax = payload.vmax || bars.reduce((m, b) => Math.max(m, b.v || 0), 0) || 1;

  const rg = payload.range;
  if (rg) {  // trailing range band, sized to this timeframe (range_windows)
    ctx.fillStyle = MC.band;
    ctx.fillRect(padL, y(rg.high), plotW, Math.max(1, y(rg.low) - y(rg.high)));
    ctx.strokeStyle = MC.accent; ctx.lineWidth = 1; ctx.setLineDash([4, 4]);
    for (const p of [rg.high, rg.low]) {
      const yy = Math.round(y(p)) + 0.5;
      ctx.beginPath(); ctx.moveTo(padL, yy); ctx.lineTo(padL + plotW, yy); ctx.stroke();
    }
    ctx.setLineDash([]);
  }

  // ---- price gridlines: they cross the depth panel too (shared y-axis)
  ctx.font = "11px ui-monospace, Consolas, monospace";
  ctx.lineWidth = 1;
  const grid = sc.grid || [];
  for (const p of grid) {
    const yy = Math.round(y(p)) + 0.5;
    if (yy < padT || yy > padT + priceH) continue;
    ctx.strokeStyle = MC.grid;
    ctx.beginPath(); ctx.moveTo(padL, yy); ctx.lineTo(depthRight, yy); ctx.stroke();
    ctx.textAlign = "left"; ctx.fillStyle = MC.flat;
    ctx.fillText(Math.round(p).toLocaleString("ja-JP"), W - padR + 6, yy + 4);
  }

  // ---- time gridlines on clock boundaries; UTC midnight gets a stronger line
  const tg = payload.time_grid || [];
  ctx.textAlign = "center";
  if (tg.length) {
    const stride = Math.max(1, Math.ceil(tg.length /
      Math.max(2, Math.floor(plotW / 74))));
    for (let k = 0; k < tg.length; k++) {
      const g0 = tg[k], x = Math.round(xl(g0.i)) + 0.5;
      if (x < padL || x > padL + plotW) continue;
      ctx.strokeStyle = g0.major ? MC.gridMajor : MC.grid;
      ctx.beginPath();
      ctx.moveTo(x, padT); ctx.lineTo(x, padT + priceH);
      ctx.moveTo(x, volTop); ctx.lineTo(x, volBot);
      ctx.stroke();
      if (k % stride === 0) {
        ctx.fillStyle = MC.flat;
        ctx.fillText(gridTimeLabel(g0, payload.tf),
          Math.min(Math.max(x, padL + 26), padL + plotW - 26), H - 6);
      }
    }
  } else {                                  // too short for a single boundary
    ctx.fillStyle = MC.flat;
    for (const i of [0, bars.length - 1]) {
      const x = Math.min(Math.max(xc(i), padL + 34), padL + plotW - 34);
      ctx.fillText(jst(bars[i].ts), x, H - 6);
    }
  }

  // ---- candles + volume columns (same x, same alpha, one pass)
  for (let i = 0; i < bars.length; i++) {
    const b = bars[i], x = Math.round(xc(i)) + 0.5;
    // the still-forming bar is dimmed; a bar whose volume is not the minute's
    // real volume — live (built here from the public tape, not yet in the CSV)
    // or truncated (the tape's oldest bucket, cut off where count ran out) —
    // is dimmed further
    ctx.globalAlpha = (b.live || b.truncated) ? 0.45 : (b.partial ? 0.6 : 1);
    ctx.strokeStyle = ctx.fillStyle = (b.c >= b.o) ? MC.up : MC.down;
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x, y(b.h)); ctx.lineTo(x, y(b.l)); ctx.stroke();
    const top = y(Math.max(b.o, b.c)), bot = y(Math.min(b.o, b.c));
    ctx.fillRect(x - cw / 2, top, cw, Math.max(1, bot - top));

    const bx = x - cw / 2, bw = Math.max(1, cw);
    if (b.bv != null && b.sv != null && (b.bv + b.sv) > 0) {
      // the taker split is real data (data/flow_*.csv or the live tape):
      // buy stacked from the axis, sell on top of it
      const hb = b.bv / vmax * volH, hs = b.sv / vmax * volH;
      if (hb > 0) { ctx.fillStyle = MC.up; ctx.fillRect(bx, volBot - hb, bw, Math.max(1, hb)); }
      if (hs > 0) { ctx.fillStyle = MC.down; ctx.fillRect(bx, volBot - hb - hs, bw, Math.max(1, hs)); }
    } else if (b.v > 0) {
      const hv = b.v / vmax * volH;         // no split known: one muted column
      ctx.fillStyle = MC.vol; ctx.fillRect(bx, volBot - hv, bw, Math.max(1, hv));
    }
    ctx.globalAlpha = 1;
  }
  ctx.strokeStyle = MC.grid;                // volume baseline
  ctx.beginPath(); ctx.moveTo(padL, volBot + 0.5); ctx.lineTo(padL + plotW, volBot + 0.5);
  ctx.stroke();
  ctx.textAlign = "left"; ctx.fillStyle = MC.flat;
  ctx.fillText(fmt(vmax, 2), W - padR + 6, volTop + 10);
  ctx.fillText("出来高", W - padR + 6, volBot - 1);

  drawDepth(ctx, payload.depth, y, depthX, depthW, padT, priceH);

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
  return {padL: padL, padR: padR, step: step, bars: bars, W: W, H: H,
          hi: hi, lo: lo, plotW: plotW, priceH: priceH, padT: padT,
          volTop: volTop, volH: volH, depthX: depthX, depthW: depthW,
          vmax: vmax, gridLines: grid.length, timeLines: tg.length};
}

// Order-book depth beside the price pane: bars grow LEFT from the right edge,
// asks (above mid) red, bids (below mid) green, on the price buckets the
// gridlines already draw. The thin step line is cumulative depth away from mid
// — where the book actually thickens, not just where one level sits.
function drawDepth(ctx, dp, y, depthX, depthW, padT, priceH) {
  const right = depthX + depthW, paneTop = padT, paneBot = padT + priceH;
  if (!dp || !dp.buckets || !dp.buckets.length || !(dp.max > 0)) {
    ctx.fillStyle = MC.flat; ctx.font = "10.5px system-ui"; ctx.textAlign = "center";
    ctx.fillText("板情報なし", depthX + depthW / 2, padT + priceH / 2);
    return;
  }
  // A depth bucket sits at a PRICE, and the price pane only shows a window of
  // prices: board_depth's ladder starts below the pane's lo and ends above its
  // hi (it is floor/ceil'd onto the gridline step), and a board fetched while
  // price ran away can sit further out still. Every rect is therefore clipped
  // to the pane — un-clipped, the edge buckets painted over the volume pane
  // below and the label gutter above.
  const clamp = v => Math.min(paneBot, Math.max(paneTop, v));
  const bar = (yy, h, w, fill) => {
    const top = clamp(yy), bot = clamp(yy + h);
    if (!(bot > top)) return;
    ctx.fillStyle = fill;
    ctx.fillRect(right - w, top, w, bot - top);
  };
  for (const bk of dp.buckets) {
    const yTop = y(bk.p + dp.step), yBot = y(bk.p);
    if (yBot <= paneTop || yTop >= paneBot) continue;   // wholly off the pane
    const half = Math.max(1, (yBot - yTop) / 2 - 0.5);
    if (bk.ask > 0) bar(yTop, half, Math.max(1, bk.ask / dp.max * depthW), MC.depthAsk);
    if (bk.bid > 0) {
      bar(yTop + half + 1, half, Math.max(1, bk.bid / dp.max * depthW), MC.depthBid);
    }
  }
  const mid = dp.mid, total = Math.max(dp.ask_sum || 0, dp.bid_sum || 0);
  if (mid == null || !(total > 0)) return;
  ctx.strokeStyle = MC.depthLine; ctx.lineWidth = 1; ctx.setLineDash([]);
  const walk = (list, key, upward) => {
    let cum = 0, started = false;
    ctx.beginPath();
    for (const bk of list) {
      cum += bk[key];
      const x = right - Math.min(1, cum / total) * depthW;
      const a = clamp(upward ? y(bk.p) : y(bk.p + dp.step));
      const z = clamp(upward ? y(bk.p + dp.step) : y(bk.p));
      if (started) { ctx.lineTo(x, a); } else { ctx.moveTo(x, a); started = true; }
      ctx.lineTo(x, z);
    }
    if (started) ctx.stroke();
  };
  walk(dp.buckets.filter(b => b.ask > 0 && b.p + dp.step > mid)
         .sort((a, b) => a.p - b.p), "ask", true);
  walk(dp.buckets.filter(b => b.bid > 0 && b.p < mid)
         .sort((a, b) => b.p - a.p), "bid", false);
}

function chartHover(ev) {
  const tip = document.getElementById("m-tip"), g = chartGeom;
  if (!tip) return;
  if (!g) { tip.style.display = "none"; return; }
  const rect = ev.currentTarget.getBoundingClientRect();
  const x = ev.clientX - rect.left;
  const i = Math.floor((x - g.padL) / g.step);
  if (x > g.padL + g.plotW || i < 0 || i >= g.bars.length) {
    tip.style.display = "none"; return;     // over the depth panel / the gutter
  }
  const b = g.bars[i];
  const split = (b.bv != null && b.sv != null)
    ? `\n買 ${fmt(b.bv, 3)}  売 ${fmt(b.sv, 3)}` : "";
  // 不完全(取得上限): the tape's oldest bucket starts where count ran out, so
  // its volume is a floor — the number is shown, with what it is worth
  const flags = (b.live ? " (ライブ)" : b.partial ? " (形成中)" : "") +
    (b.truncated ? " 不完全(取得上限)" : "");
  tip.innerHTML = `${jst(b.ts)} JST${flags}\n` +
    `始 ${fmt(b.o, 0)}   高 ${fmt(b.h, 0)}\n安 ${fmt(b.l, 0)}   終 ${fmt(b.c, 0)}\n` +
    `出来高 ${fmt(b.v, 3)}` + split;
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
    window.addEventListener("resize", () => { if (marketData) renderChart(); if (aSeries.length) drawAttentionChart(); });
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
# public bitFlyer reads (board + execution tape)
#
# Both are best-effort by construction: on ANY failure the last good snapshot
# is served with its real age, and if there has never been one the caller gets
# None and the page draws its empty state. Nothing here may raise into a
# request handler — a dead exchange must not take the local console down.
# ---------------------------------------------------------------------------
BF_PUBLIC = "https://api.bitflyer.com"
PUBLIC_TIMEOUT = 3.0
PUBLIC_TTL = 5.0          # minimum seconds between two calls to one endpoint
EXEC_COUNT = 500          # /v1/executions max per call

_session = requests.Session()
_public_lock = threading.Lock()
# one entry per endpoint: the last GOOD payload, when it was taken, and when we
# last tried (so a hard-down endpoint is still only retried every PUBLIC_TTL)
_public_cache: dict[str, dict] = {
    "board": {"data": None, "fetched_at": None, "tried_at": None, "error": None},
    "executions": {"data": None, "fetched_at": None, "tried_at": None, "error": None},
}


def _public_get(name: str, path: str, params: dict, now: float | None = None):
    """GET one public endpoint at most once per PUBLIC_TTL; never raises."""
    now = time.time() if now is None else now
    with _public_lock:
        slot = _public_cache[name]
        tried = slot["tried_at"]
        if tried is not None and (now - tried) < PUBLIC_TTL:
            return slot["data"]
        slot["tried_at"] = now
    data = error = None
    try:
        r = _session.get(f"{BF_PUBLIC}{path}", params=params, timeout=PUBLIC_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:                      # network, HTTP, JSON — all soft
        error = f"{type(exc).__name__}: {exc}"[:200]
    with _public_lock:
        slot = _public_cache[name]
        if data is not None:
            slot.update({"data": data, "fetched_at": now, "error": None})
        else:
            slot["error"] = error                 # keep the stale data and its age
        return slot["data"]


def fetch_board(now: float | None = None):
    """The public order book, or the last one we got (or None)."""
    return _public_get("board", "/v1/board", {"product_code": PRODUCT}, now)


def fetch_executions(now: float | None = None) -> list:
    """The public execution tape tail, or the last one we got (or [])."""
    data = _public_get("executions", "/v1/executions",
                       {"product_code": PRODUCT, "count": EXEC_COUNT}, now)
    return data if isinstance(data, list) else []


def live_bars(now: float | None = None) -> list[dict]:
    """The last few 1m buckets off the execution tape (empty when offline)."""
    return bars_from_executions(fetch_executions(now))


def board_fetched_at() -> float | None:
    with _public_lock:
        return _public_cache["board"]["fetched_at"]


# ---------------------------------------------------------------------------
# /api/market cache
#
# collect_market re-parses every candle in data/ (tens of thousands of rows) —
# ~0.7s on the live dataset, far too much to redo per poll. The payload is
# therefore cached and rebuilt only when the files it reads changed OR the live
# 1m tail moved, with a floor of MARKET_TTL seconds either way. The board is
# NOT part of that key: it is attached to the cached payload on every request,
# which is microseconds, so depth stays as fresh as the fetch cache allows.
#
# MARKET_TTL must stay BELOW the 1m view's poll period (FAST_POLL_MS, 10s) or
# every other fast poll is answered from a payload the TTL refuses to rebuild —
# a 10s poll against a 15s floor served the same 1m tail twice, then a fresh
# one, forever. The execution tape is fetched only on the paths that can
# actually use it, so a TTL-fresh answer costs no /v1/executions call at all.
# ---------------------------------------------------------------------------
MARKET_FILES = (f"data/candles_{PRODUCT}.csv", f"data/flow_{PRODUCT}.csv",
                "data/oi_snapshots.csv", "logs/bot.jsonl",
                "data/scalp_paper.jsonl")
MARKET_TTL = 8.0
_market_lock = threading.Lock()
_market_cache: dict[str, object] = {"key": None, "at": 0.0, "payload": None,
                                    "root": None}


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


def _live_key(bars: list[dict]) -> tuple:
    """What about the live tail would change the payload if it changed."""
    if not bars:
        return ()
    last = bars[-1]
    return (len(bars), last["ts"], last["close"], round(last["volume"], 6))


def market_body(root: str = ".", now: float | None = None) -> bytes:
    """The /api/market JSON: cached files + live tail, board attached fresh."""
    now = time.monotonic() if now is None else now
    # the board is NOT deferred like the tape below: it is not part of the
    # cache key precisely so the depth panel never waits on a candle file, so
    # every path attaches it. fetch_board is PUBLIC_TTL-capped (one HTTP call
    # per 5s however often the page polls) and stays OUTSIDE _market_lock, so a
    # slow exchange cannot make a second tab queue behind it.
    board = fetch_board()
    with _market_lock:
        cached = (_market_cache["payload"]
                  if _market_cache["root"] == str(root) else None)
        if cached is None or (now - _market_cache["at"]) >= MARKET_TTL:
            # the tape is fetched HERE and not before: on a TTL-fresh path the
            # cached payload is served unchanged, so the /v1/executions call
            # would have bought nothing but a slot in the public rate budget
            live = live_bars()
            key = _market_key(root) + _live_key(live)
            if cached is not None and key == _market_cache["key"]:
                _market_cache["at"] = now   # nothing moved: re-arm the TTL
            else:
                cached = collect_market(root, live_bars=live)
                _market_cache.update({"key": key, "at": now, "payload": cached,
                                      "root": str(root)})
        attach_board(cached, board, now=board_fetched_at())
        return json.dumps(cached).encode()


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
