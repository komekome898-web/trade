/* The バックテスト tab of scripts/dashboard.py: theme tree -> strategy -> family dropdowns -> one road run.
   Data: /api/backtest/catalog, /summary/<id>, /chart/<id>?from&to&interval&max_bars&range&instrument,
   /table/<id>/<table>?..., /trace/<id>/<table>/<row>, /file/<id>/<record.json|SCHEMA.json>.
   A run is the road record (road/, 版 road-record-7): signals, orders, fills, fx, ledger_fills, trades, summary.
   The chart library (TradingView lightweight-charts, Apache-2.0) is served from /static/, so the tab works without a network. */
(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const esc = s => String(s == null ? "—" : s).replace(/[&<>"']/g,
    c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const BUY = "#4da3ff", SELL = "#ff5a5f", WIN = "#7bd88f", LOSE = "#ffb347", AVG = "#c792ea";
  const SER = {pessimistic: {cum: "#ffd84d", pos: "#b9a6ff"}, optimistic: {cum: "#4cc8cf", pos: "#7bd88f"}};
  const RANGE_JA = {pessimistic: "悲観側", optimistic: "楽観側", both: "両方(重ねる)"};
  const FRAMES = [60, 300, 900, 3600, 14400, 86400];
  const FRAME_NAME = {60: "1分", 300: "5分", 900: "15分", 3600: "1時間", 14400: "4時間", 86400: "日足"};
  const TABLES = [["signals", "合図"], ["orders", "注文"], ["fills", "約定"], ["fx", "USDJPY"], ["ledger_fills", "帳簿の約定"],
                  ["trades", "取引"], ["summary", "まとめ"]];
  const LAYERS = [["signals", "合図の帯"], ["orders", "指値の線"], ["fills", "約定の矢印"], ["avg", "平均の建値"], ["trades", "取引の囲み"]];
  const KIND_JA = {filled: "約定", canceled: "取り消し", venue_closed: "取引所が閉じた(期限など)", rejected: "拒否", zero: "量が 0 で出さない",
                   partial: "一部約定のまま", open: "データの終わりまで出たまま"};
  const MAX_LABEL = 150;

  let CAT = null, STRAT = null, SEL = {}, VER = 0, RUN = null, SUM = null, SEQ = 0;
  let VIEW = "chart";
  const scope = {inst: null, range: "pessimistic"};
  const TBL = {table: "trades", sort: null, desc: false, filters: [], page: 0, size: 100, data: null};
  const PX = {price: null, candle: null, pos: null, pnl: null, series: {}, bars: [], interval: 0, winFrom: 0, winTo: 0, loLimit: 0,
              hiLimit: 0, data: null, hits: [], timer: null, restoring: false, syncing: false, sig: "", raf: 0, sel: null, poll: 0,
              opts: {layers: {signals: true, orders: true, fills: true, avg: true, trades: true}, labels: false, frame: "auto"}};
  window.btState = PX;  // for the browser probe of the tab (no page logic reads it)

  // ---- helpers -----------------------------------------------------------------------------------------------
  const num = (v, d) => v == null ? "—" : Number(v).toLocaleString("ja-JP", {maximumFractionDigits: d == null ? 0 : d, minimumFractionDigits: 0});
  const signed = (v, d) => v == null ? "—" : (v > 0 ? "+" : "") + num(v, d);
  const p2 = n => String(n).padStart(2, "0");
  const utc = (s, withTime) => {
    const d = new Date(s * 1000);
    const day = d.getUTCFullYear() + "-" + p2(d.getUTCMonth() + 1) + "-" + p2(d.getUTCDate());
    return withTime ? day + " " + p2(d.getUTCHours()) + ":" + p2(d.getUTCMinutes()) : day;
  };
  const utcSec = s => utc(s, true) + ":" + p2(new Date(s * 1000).getUTCSeconds());
  const nsTime = v => /^\d{15,}$/.test(v) ? utcSec(Number(BigInt(v) / 1000000n) / 1000) : "";
  const width = n => n >= 86400 ? (n / 86400) + "日足" : n >= 3600 ? (n / 3600) + "時間足" : (n / 60) + "分足";
  const FETCH_MS = 150000;
  // Every request has a time limit and says why it failed: the page never stays black without a reason.
  function getJSON(url, ms) {
    const ctl = new AbortController(), lim = ms || FETCH_MS, t0 = Date.now();
    const timer = setTimeout(() => ctl.abort(), lim);
    return fetch(url, {signal: ctl.signal}).then(r => r.text().then(txt => {
      let j = null;
      try { j = JSON.parse(txt); } catch (e) { /* not JSON */ }
      if (!r.ok) throw new Error(`HTTP ${r.status} ${(j && j.error) || r.statusText || txt.slice(0, 200)}(${url.split("?")[0]})`);
      if (j === null) throw new Error(`応答が JSON でない(HTTP ${r.status}、${url.split("?")[0]})`);
      return j;
    })).catch(err => {
      if (err && err.name === "AbortError") throw new Error(`時間切れ(${Math.round((Date.now() - t0) / 1000)} 秒待った。${url.split("?")[0]})`);
      if (err instanceof TypeError) throw new Error(`サーバーに接続できない(${err.message}。${url.split("?")[0]})`);
      throw err;
    }).finally(() => clearTimeout(timer));
  }
  const BUSY = {};
  function busy(id, text) {
    idle(id);
    const t0 = Date.now(), el = $(id);
    if (!el) return;
    const tick = () => { el.innerHTML = `<span class="busy">${esc(text)}(${Math.round((Date.now() - t0) / 1000)} 秒経過)</span>`; };
    tick(); BUSY[id] = setInterval(tick, 1000);
  }
  function idle(id) { if (BUSY[id]) { clearInterval(BUSY[id]); delete BUSY[id]; } }
  function banner(where, err) {
    const el = $("bt-banner");
    const msg = `${where}: ${err && err.message ? err.message : err}`;
    if (el) { el.hidden = false; el.textContent = "バックテストの画面でエラー — " + msg; }
    try { console.error(msg, err); } catch (e) { /* no console */ }
  }
  window.addEventListener("error", e => { if (!$("view-backtest").hidden) banner("画面の処理(JS の例外)", e.error || e.message); });
  window.addEventListener("unhandledrejection", e => { if (!$("view-backtest").hidden) banner("画面の処理(未処理の失敗)", e.reason); });
  const enc = encodeURIComponent;

  // ---- the tree ----------------------------------------------------------------------------------------------
  function allStrategies() { return CAT.themes.flatMap(t => t.strategies); }
  function renderTree() {
    let h = "";
    for (const th of CAT.themes) {
      if (!th.strategies.length) continue;
      h += `<details${th.id === "legacy" ? "" : " open"}><summary>${esc(th.title)}${th.fake ? ' <span class="n fake">作り物</span>' : ""}</summary>` +
        `<div class="sum">${esc(th.summary)}</div>`;
      for (const st of th.strategies) {
        const un = (st.unavailable || []).length;
        h += `<button class="st" data-sid="${esc(st.id)}">${esc(st.title)} <span class="n">${st.n_runs} 本${un ? "・表示できない " + un + " 本" : ""}</span></button>`;
      }
      h += "</details>";
    }
    const br = CAT.broken || [];
    if (br.length) {
      h += `<details open><summary>読めない record.json ${br.length} 本(理由つき。隠していない)</summary><ul class="bt-broken">` +
        br.map(b => `<li><b>${esc(b.run_id.slice(0, 12))}</b> — ${esc(b.reason)}</li>`).join("") + "</ul></details>";
    }
    $("bt-tree").innerHTML = h || '<span class="empty">実行がまだ無い</span>';
    $("bt-tree").querySelectorAll("button.st").forEach(b => b.onclick = () => selectStrategy(b.dataset.sid));
  }

  function selectStrategy(sid) {
    STRAT = allStrategies().find(s => s.id === sid);
    if (!STRAT) return;
    $("bt-tree").querySelectorAll("button.st").forEach(b => b.classList.toggle("on", b.dataset.sid === sid));
    renderHead();
    const first = STRAT.runs.find(r => r.run_id === STRAT.default_run_id) || STRAT.runs[0];
    if (!first) {
      SEL = {}; VER = 0; SEQ++; RUN = null; SUM = null;
      for (const id of ["bt-family", "bt-scope", "bt-stats", "bt-views", "bt-v-chart", "bt-v-table", "bt-v-record", "bt-trace"]) $(id).hidden = true;
      return;
    }
    SEL = Object.assign({}, first.axes);
    VER = 0;
    renderFamily("");
    chooseRun();
  }

  function renderHead() {
    const s = STRAT;
    const th = CAT.themes.find(t => t.strategies.includes(s));
    const axSrc = s.axes.map(a => `<li>${esc(a.label)}: ${esc(a.source)}</li>`).join("");
    $("bt-head").innerHTML = `<div class="bt-crumb">${esc(th ? th.title : "")}</div><h2>${esc(s.title)}${s.fake ? ' <span class="n fake">作り物</span>' : ""}</h2>` +
      `<ul class="bt-desc">${s.description.map(t => `<li>${esc(t.text)} <span class="src">[出所: ${esc(t.source)}]</span></li>`).join("")}</ul>` +
      `<details class="bt-src"><summary>族の軸の出所</summary><ul>${axSrc || "<li>(この戦略の走らせは族の軸が 1 つも違わない / 1 本だけ)</li>"}</ul></details>` +
      renderUnavailable(s);
  }
  function renderUnavailable(s) {
    const un = s.unavailable || [];
    if (!un.length) return "";
    return `<details class="bt-unav" open><summary>表示できない走らせ ${un.length} 本(理由つき。隠していない)</summary><ul>` +
      un.map(u => `<li><b>${esc(u.run_id.slice(0, 12))}</b> — ${esc(u.reason)}</li>`).join("") + "</ul></details>";
  }

  // ---- the family dropdowns ----------------------------------------------------------------------------------
  const primary = () => STRAT.axes.filter(a => !a.secondary);
  const secondary = () => STRAT.axes.find(a => a.secondary);
  const matching = sel => STRAT.runs.filter(r => primary().every(a => r.axes[a.key] === sel[a.key]));

  function renderFamily(msg) {
    const box = $("bt-family");
    const ax = primary();
    if (!ax.length) { box.hidden = true; return; }
    box.hidden = false;
    let h = '<div class="bt-axes">';
    for (const a of ax) {
      const cur = SEL[a.key];
      const ent = a.values.find(v => v.value === cur);
      if (a.fixed || a.values.length === 1) {
        h += `<div class="fixed">${esc(a.label)}(この戦略では固定)<b>${esc(ent ? ent.label : cur)}</b></div>`;
      } else {
        h += `<label>${esc(a.label)}<select data-axis="${esc(a.key)}">` + a.values.map(v => {
          const reach = matching(Object.assign({}, SEL, {[a.key]: v.value})).length > 0;
          return `<option value="${esc(v.value)}"${v.value === cur ? " selected" : ""}>${esc(v.label)}${reach ? "" : "(この組み合わせの実行は無い)"}</option>`;
        }).join("") + "</select></label>";
      }
    }
    const cands = matching(SEL), sec = secondary();
    if (cands.length > 1 && sec) {
      h += `<label>${esc(sec.label)}(同じ設定の実行が ${cands.length} 本)<select data-axis="__ver">` +
        cands.map((r, i) => `<option value="${i}"${i === VER ? " selected" : ""}>${esc(r.axes[sec.key].slice(0, 12))} / ${esc(r.run_id.slice(0, 8))}</option>`).join("") + "</select></label>";
    }
    h += "</div>";
    if (msg) h += `<div class="bt-msg">${esc(msg)}</div>`;
    box.innerHTML = h;
    box.querySelectorAll("select").forEach(sel => sel.onchange = () => {
      if (sel.dataset.axis === "__ver") { VER = Number(sel.value); chooseRun(); renderFamily(""); }
      else onAxis(sel.dataset.axis, sel.value);
    });
  }

  function onAxis(key, value) {
    const want = Object.assign({}, SEL, {[key]: value});
    let msg = "";
    if (!matching(want).length) {  // no run has this combination: take the run that has the value and keeps most of the other choices
      const ax = primary();
      let best = null, bestScore = -1;
      for (const r of STRAT.runs) {
        if (r.axes[key] !== value) continue;
        const score = ax.filter(a => a.key !== key && r.axes[a.key] === SEL[a.key]).length;
        if (score > bestScore) { best = r; bestScore = score; }
      }
      const changed = ax.filter(a => a.key !== key && best.axes[a.key] !== SEL[a.key]).map(a => {
        const e = a.values.find(v => v.value === best.axes[a.key]);
        return `${a.label}を「${e ? e.label : best.axes[a.key]}」に`;
      });
      msg = "選んだ組み合わせの実行は無い。" + (changed.length ? changed.join("・") + "変えて、近い実行を出した。" : "近い実行を出した。");
      SEL = Object.assign({}, best.axes);
    } else {
      SEL = want;
    }
    VER = 0;
    renderFamily(msg);
    chooseRun();
  }

  function chooseRun() {
    const c = matching(SEL);
    const r = c[Math.min(VER, c.length - 1)];
    if (r) loadRun(r.run_id, false);
  }

  // ---- one run: the summary, the scope bar, the headline numbers -----------------------------------------------
  function hideRunParts() {
    for (const id of ["bt-scope", "bt-stats", "bt-views", "bt-v-chart", "bt-v-table", "bt-v-record", "bt-trace"]) $(id).hidden = true;
  }
  function loadRun(id, keepScope) {
    const my = ++SEQ;
    RUN = id;
    if (!keepScope) { scope.inst = null; }
    $("bt-banner").hidden = true;
    hideRunParts();
    const run = STRAT && STRAT.runs.find(r => r.run_id === id);
    if (STRAT && STRAT.kind === "legacy") { renderLegacy(id); return; }
    $("bt-stats").hidden = false;
    busy("bt-stats", "実行の要約を読み込み中");
    let url = "/api/backtest/summary/" + enc(id) + "?range=" + enc(scope.range === "both" ? "pessimistic" : scope.range);
    if (scope.inst) url += "&instrument=" + enc(scope.inst);
    getJSON(url).then(sum => {
      if (my !== SEQ) return;
      idle("bt-stats");
      SUM = sum;
      if (sum.legacy) { renderLegacy(id); return; }
      if (sum.unavailable || sum.blocked) {
        $("bt-stats").innerHTML = `<div class="warn">${esc(sum.unavailable || sum.blocked)}</div>`;
        return;
      }
      scope.inst = sum.instrument;
      if (scope.range !== "both" && sum.ranges.indexOf(scope.range) < 0) scope.range = sum.ranges[0];
      renderScope();
      renderStats();
      $("bt-views").hidden = false;
      renderViews();
      showView(VIEW);
      $("bt-trace").hidden = true;
    }).catch(err => {
      if (my !== SEQ) return;
      idle("bt-stats");
      $("bt-stats").innerHTML = `<div class="warn">読み込めなかった: ${esc(err.message)}</div>`;
      banner("実行の要約", err);
    });
    return run;
  }

  function renderLegacy(id) {
    const s = $("bt-stats");
    s.hidden = false;
    s.innerHTML = `<div class="warn">古い形の走らせ(道の記録 road/ が無い)。チャートと表は出さない。実行 ID ${esc(id)}</div>` +
      `<div class="bt-notes">pipeline の trades.json・metrics.json の取引は FIFO の数え方で、道の数え方(建玉 0 → 0 を 1 取引)ではないため、道の画面では使わない。` +
      ` <a href="/backtest/run/${esc(id)}" target="_blank" style="color:var(--accent)">古い 10 個の詳細タブの単独ページを開く</a></div>`;
  }

  function renderScope() {
    const box = $("bt-scope");
    box.hidden = false;
    let h = '<div class="bt-axes">';
    if (SUM.instruments.length > 1) {
      h += `<label>銘柄<select id="bt-s-inst">${SUM.instruments.map(i => `<option${i === scope.inst ? " selected" : ""}>${esc(i)}</option>`).join("")}</select></label>`;
    } else {
      h += `<div class="fixed">銘柄<b>${esc(scope.inst)}</b></div>`;
    }
    const opts = SUM.ranges.map(r => [r, RANGE_JA[r] || r]);
    if (SUM.ranges.length > 1) opts.push(["both", RANGE_JA.both]);
    h += `<label>約定の範囲(楽観側・悲観側)<select id="bt-s-range">${opts.map(([v, l]) => `<option value="${esc(v)}"${v === scope.range ? " selected" : ""}>${esc(l)}</option>`).join("")}</select></label>`;
    h += `<div class="fixed">実行<b class="mono">${esc(SUM.run_id.slice(0, 12))}</b></div>`;
    h += `<div class="fixed">戦略<b>${esc(SUM.strategy.title)}${SUM.strategy.fake ? "(作り物)" : ""}</b></div>`;
    h += "</div>";
    if (SUM.purpose === "動作確認") h += '<div class="bt-notes"><span class="warn">動作確認の実行。相場の結論には使わない。</span></div>';
    if (SUM.strategy.fake) h += '<div class="bt-notes"><span class="warn">作り物の走らせ(表示の確かめ用)。戦略は本物ではない。</span></div>';
    box.innerHTML = h;
    const si = $("bt-s-inst");
    if (si) si.onchange = e => { scope.inst = e.target.value; loadRun(RUN, true); };
    $("bt-s-range").onchange = e => {
      scope.range = e.target.value;
      TBL.page = 0;
      renderStats();
      showView(VIEW, true);
    };
  }

  const FMT = {
    int: v => num(v, 0), yen: v => v == null ? "—" : signed(v, 2) + " 円", pct: v => v == null ? "—" : (v * 100).toFixed(1) + "%",
    plain: v => v == null ? "—" : num(v, 2)
  };
  function qline(d, unit) {
    if (!d) return "—";
    const names = {0: "最小", 5: "5%", 25: "25%", 50: "中央", 75: "75%", 95: "95%", 100: "最大"};
    return d.map(([q, v]) => `${names[q] || q}: ${num(v, 2)}`).join(" / ") + (unit ? " " + unit : "");
  }
  function renderStats() {
    const box = $("bt-stats"), S = SUM, rs = S.ranges;
    const shown = scope.range === "both" ? rs : [scope.range];
    let h = `<h3>見出しの数 <span class="n">銘柄 ${esc(S.instrument)}・期間 ${utc(S.period.first_s)} 〜 ${utc(S.period.last_incl_s)}(UTC・終わりの日を含む)</span></h3>`;
    h += `<div class="bt-notes">出所: <b>road/summary.json</b>(まとめ。帳簿のツールが作った数)と、<b>trades・ledger_fills・orders・signals・fills の表</b>から画面が計算した数。` +
      `<b>経費(手数料)は帳簿の損益に入っていない(L-741)</b>。損益はすべて円、経費の前。</div>`;
    // summary.json rows (not for a run that crosses the seal boundary: its numbers are the whole run's)
    if (S.summary_cut) {
      h += `<div class="bt-notes warn">${esc(S.summary_cut_reason)}。下の数は境より前の行だけから計算した。</div>`;
    } else {
      h += '<table class="bt-t"><tr><th>summary.json</th><th>銘柄</th><th>約定の範囲</th><th>約定の数</th><th>閉じた取引</th><th>損益の合計(円)</th><th>途中の取引</th><th>画面の計算との一致</th></tr>';
      for (const r of S.summary_rows) {
        const hd = S.headline[r.range];
        const same = hd ? (hd.trades.closed === Number(r.closed_trades) && hd.fills.count === Number(r.fill_count) &&
          hd.trades.open === Number(r.open_trades) && Math.abs((hd.trades.pnl_sum || 0) - Number(r.pnl_jpy)) < 1e-6 ? "一致" : "<span class='warn'>不一致</span>") : "—";
        h += `<tr><td></td><td>${esc(r.instrument)}</td><td>${esc(RANGE_JA[r.range] || r.range)}</td><td class="num">${esc(r.fill_count)}</td><td class="num">${esc(r.closed_trades)}</td>` +
          `<td class="num">${esc(r.pnl_jpy)}</td><td class="num">${esc(r.open_trades)}</td><td>${same}</td></tr>`;
      }
      h += "</table>";
    }
    // computed
    const rows = [];
    const row = (label, f, formula) => rows.push([label, shown.map(r => f(S.headline[r])), formula]);
    row("閉じた取引の数", x => FMT.int(x.trades.closed), x => x.trades.formulas.closed);
    row("途中の取引の数", x => FMT.int(x.trades.open), "trades の status が closed でない行数");
    row("勝ち / 負け / ±0", x => `${num(x.trades.wins)} / ${num(x.trades.losses)} / ${num(x.trades.flat)}`, x => x.trades.formulas.wins);
    row("勝率", x => FMT.pct(x.trades.win_rate), "勝ち ÷ 閉じた取引の数");
    row("損益の合計(円)", x => FMT.yen(x.trades.pnl_sum), x => x.trades.formulas.pnl_sum);
    row("1 取引の損益の平均(円)", x => FMT.yen(x.trades.pnl_mean), "損益の合計 ÷ 閉じた取引の数");
    row("損益の分布(円)", x => qline(x.trades.pnl_dist), x => x.trades.formulas.pnl_dist);
    row("保有時間の分布(分)", x => qline(x.trades.hold_min_dist), x => x.trades.formulas.hold_min_dist);
    row("段の数の分布(取引の数)", x => x.trades.levels_dist.map(([k, v]) => `${k}段: ${num(v)}`).join(" / ") || "—", x => x.trades.formulas.levels_dist);
    row("最大の落ち込み(円)", x => num(x.drawdown.max, 2), x => x.drawdown.formula);
    row("合図の数", x => FMT.int(x.signals.count), x => x.signals.formulas.count);
    row("閉じた取引のあった合図 / 無かった合図", x => `${num(x.signals.with_closed_trade)} / ${num(x.signals.without_closed_trade)}`, x => x.signals.formulas.with_closed_trade);
    row("合図あたりの損益(平均・円)", x => FMT.yen(x.signals.pnl_per_signal_mean), x => x.signals.formulas.pnl_per_signal_mean);
    row("合図あたりの損益の分布(円)", x => qline(x.signals.pnl_per_signal_dist), "合図ごとの損益(上の式)の同じパーセンタイル");
    row("注文の行数 / 量が 0 で出さない段 / 出した注文", x => `${num(x.orders.count)} / ${num(x.orders.zero_qty)} / ${num(x.orders.sent)}`, x => x.orders.formulas.zero_qty);
    row("約定しなかった注文の数", x => FMT.int(x.orders.unfilled), x => x.orders.formulas.unfilled);
    row("約定しなかった注文の割合", x => FMT.pct(x.orders.unfilled_ratio), x => x.orders.formulas.unfilled_ratio);
    row("約定しなかった注文の内訳", x => Object.entries(x.orders.unfilled_by).map(([k, v]) => `${KIND_JA[k] || k}: ${num(v)}`).join(" / "),
        "orders の閉じ方(取り消し・取引所が閉じた・拒否・データの終わりまで出たまま)ごとの数");
    row("約定の数", x => FMT.int(x.fills.count), "fills の行数");
    row("maker / taker", x => Object.entries(x.fills.liquidity).map(([k, v]) => `${k}: ${num(v)}`).join(" / ") || "—", x => x.fills.formulas.liquidity);
    row("約定の当て方(fill_case)", x => Object.entries(x.fills.case).map(([k, v]) => `${k}: ${num(v)}`).join(" / ") || "—", "fills の fill_case ごとの数");
    row("手数料の合計(帳簿の損益に入っていない)", x => num(x.fills.fee_sum, 4), x => x.fills.formulas.fee_sum);
    h += '<table class="bt-t"><tr><th>画面が表から計算した数</th>' + shown.map(r => `<th>${esc(RANGE_JA[r] || r)}</th>`).join("") + "<th>計算式(出所の表と列)</th></tr>";
    for (const [label, vals, f] of rows) {
      const formula = typeof f === "function" ? f(S.headline[shown[0]]) : f;
      h += `<tr><td>${esc(label)}</td>` + vals.map(v => `<td class="num">${esc(v)}</td>`).join("") + `<td class="formula">${esc(formula)}</td></tr>`;
    }
    h += "</table>";
    h += `<div class="bt-notes">${S.road.counts_cut ? "表の行数(境の前に出す行だけ)" : "表の行数"}: ` + Object.entries(S.road.tables).map(([k, v]) => `${esc(k)} ${num(v)}`).join(" / ") + `(道の記録の版 ${esc(S.road.version)})</div>`;
    box.innerHTML = h;
  }

  // ---- the three views ---------------------------------------------------------------------------------------
  function renderViews() {
    const box = $("bt-views");
    box.innerHTML = [["chart", "チャート"], ["table", "表(7 つ・全部の列)"], ["record", "記録(record.json・SCHEMA.json)"]]
      .map(([k, l]) => `<button data-v="${k}" class="${k === VIEW ? "on" : ""}">${l}</button>`).join("");
    box.querySelectorAll("button").forEach(b => b.onclick = () => showView(b.dataset.v));
  }
  function showView(v, rescope) {
    VIEW = v;
    $("bt-views").querySelectorAll("button").forEach(b => b.classList.toggle("on", b.dataset.v === v));
    $("bt-v-chart").hidden = v !== "chart";
    $("bt-v-table").hidden = v !== "table";
    $("bt-v-record").hidden = v !== "record";
    if (v === "chart") {
      renderNotes(); renderFrameBar(); buildCharts();
      if (PX.focus) { const f = PX.focus; PX.focus = null; focusTime(f[0], f[1]); } else fetchChart(null, null, true, SEQ);
    }
    if (v === "table") loadTable();
    if (v === "record") loadRecord();
  }

  // ---- chart -------------------------------------------------------------------------------------------------
  function renderNotes() {
    const p = SUM.price;
    let h = "";
    if (p.available) h += `<span class="${p.same_source ? "" : "warn"}">価格: ${esc(p.note)}</span>`;
    else h += `<span class="warn">チャートは出せない: ${esc(p.reason)}。下の建玉と累計損益だけ出す。</span>`;
    h += ` / 価格は ${esc(SUM.seal_boundary_iso)} より前だけ(封印の境)。時刻は UTC。`;
    if (SUM.purpose === "動作確認") h += ' <span class="warn">動作確認の実行。相場の結論には使わない。</span>';
    $("bt-price-note").innerHTML = h;
  }

  // 表示の足 (the chart's bar width) is chosen apart from 測定に使った足 (the bar the run was measured on)
  function renderFrameBar() {
    const o = PX.opts, avail = SUM.price.available;
    let h = '<span class="k">表示の足</span> ';
    h += `<button data-f="auto" class="${o.frame === "auto" ? "on" : ""}"${avail ? "" : " disabled"}>自動</button>`;
    for (const f of FRAMES) h += `<button data-f="${f}" class="${o.frame === f ? "on" : ""}"${avail ? "" : " disabled"}>${FRAME_NAME[f]}</button>`;
    h += ` <span class="k" id="bt-frame-now"></span>`;
    h += ` <span class="k">測定に使った足: ${SUM.measure_interval_s ? esc(FRAME_NAME[SUM.measure_interval_s] || (SUM.measure_interval_s / 60) + "分") : "記録なし"}(実行の記録 data[].spec.bar.interval_s。表示の足とは別)</span>`;
    $("bt-frame").innerHTML = h;
    $("bt-frame").querySelectorAll("button").forEach(b => b.onclick = () => {
      o.frame = b.dataset.f === "auto" ? "auto" : Number(b.dataset.f);
      renderFrameBar();
      refetchKeep();
    });
    showFrameNow();
  }
  function showFrameNow() {
    const el = $("bt-frame-now");
    if (el && PX.interval) el.textContent = `(いまの表示: ${FRAME_NAME[PX.interval] || width(PX.interval)}${PX.opts.frame === "auto" ? "・自動" : "・固定"})`;
  }

  function lineOpts(color, w, step) {
    return {color, lineWidth: w, lineType: step ? 1 : 0, priceLineVisible: false, lastValueVisible: false};
  }
  function buildCharts() {
    const LC = window.LightweightCharts;
    if (!LC) { $("bt-price-note").innerHTML += '<br><span class="warn">チャート描画ライブラリ(/static/lightweight-charts.standalone.production.js)を読み込めなかった。</span>'; return; }
    const hasPrice = SUM.price.available;
    $("bt-pricewrap").hidden = !hasPrice;
    if (!PX.price) {
      const common = {
        layout: {background: {type: "solid", color: "#0a0d13"}, textColor: "#9aa7bd", fontFamily: "system-ui, sans-serif"},
        grid: {vertLines: {color: "#151c29"}, horzLines: {color: "#151c29"}},
        rightPriceScale: {borderColor: "#2a3550", minimumWidth: 92},
        timeScale: {borderColor: "#2a3550", timeVisible: true, secondsVisible: false, rightOffset: 2, minBarSpacing: 0.02},
        crosshair: {mode: 0},
      };
      PX.price = LC.createChart($("bt-price"), Object.assign({width: $("bt-price").clientWidth || 900, height: 470}, common));
      PX.candle = PX.price.addCandlestickSeries({upColor: "#cfd8e6", downColor: "#4b566a", borderVisible: false,
        wickUpColor: "#cfd8e6", wickDownColor: "#4b566a", priceLineVisible: false, lastValueVisible: false});
      PX.pos = LC.createChart($("bt-pos"), Object.assign({width: $("bt-pos").clientWidth || 900, height: 110}, common));
      PX.pnl = LC.createChart($("bt-pnl"), Object.assign({width: $("bt-pnl").clientWidth || 900, height: 160}, common));
      for (const r of ["pessimistic", "optimistic"]) {
        PX.series[r] = {pos: PX.pos.addLineSeries(lineOpts(SER[r].pos, 2, true)), cum: PX.pnl.addLineSeries(lineOpts(SER[r].cum, 2, true))};
      }
      PX.price.timeScale().subscribeVisibleLogicalRangeChange(r => { onRange(r); syncLower(r, "price"); });
      PX.pos.timeScale().subscribeVisibleLogicalRangeChange(r => syncLower(r, "pos"));
      PX.pnl.timeScale().subscribeVisibleLogicalRangeChange(r => syncLower(r, "pnl"));
      new ResizeObserver(resize).observe($("bt-v-chart"));
      $("bt-pricewrap").addEventListener("mousemove", onMove);
      $("bt-pricewrap").addEventListener("mouseleave", () => { $("bt-tip").style.display = "none"; });
      $("bt-pricewrap").addEventListener("click", onClick);
      loop();
    }
    resize();
    renderPanel();
    renderLegend();
  }

  function resize() {
    if (!PX.price || $("bt-v-chart").hidden) return;
    const w = Math.max(300, $("bt-v-chart").clientWidth - 34);
    PX.price.applyOptions({width: w, height: 470});
    PX.pos.applyOptions({width: w, height: 110});
    PX.pnl.applyOptions({width: w, height: 160});
    const cv = $("bt-overlay"), dpr = window.devicePixelRatio || 1;
    cv.style.width = w + "px"; cv.style.height = "470px";
    cv.width = Math.round(w * dpr); cv.height = Math.round(470 * dpr);
    PX.sig = "";
  }

  function renderPanel() {
    const panel = $("bt-panel"), o = PX.opts;
    let h = LAYERS.map(([k, l]) => `<label><input type="checkbox" data-layer="${k}"${o.layers[k] ? " checked" : ""}> ${l}</label>`).join("");
    h += `<label><input type="checkbox" id="bt-o-labels"${o.labels ? " checked" : ""}> 取引の損益の数字(${MAX_LABEL} 件まで)</label>`;
    h += '<div class="grp"><button id="bt-o-fit">実行の期間</button> <span class="hint" id="bt-o-warn"></span></div>';
    panel.innerHTML = h;
    panel.querySelectorAll("input[data-layer]").forEach(c => c.onchange = e => { o.layers[c.dataset.layer] = e.target.checked; PX.sig = ""; });
    $("bt-o-labels").onchange = e => { o.labels = e.target.checked; PX.sig = ""; };
    $("bt-o-fit").onclick = () => fetchChart(null, null, true, SEQ);
  }

  function renderLegend() {
    const both = scope.range === "both";
    $("bt-legend").innerHTML =
      `<span><i style="border-color:${BUY}"></i>買い(青)</span><span><i style="border-color:${SELL}"></i>売り(赤)</span>` +
      `<span>合図の帯: 向き long = 青み / short = 赤み(ホバーで種類・値・消失の理由)</span>` +
      `<span>指値の線: 実線 = 約定 / 破線 = 取り消し / 点線 = 取引所が閉じた / 細かい破線 = 拒否 / × = 量 0 で出さない / 長い破線 = 出たまま。成行は線なし(約定の矢印だけ)</span>` +
      `<span>矢印: 約定(買い = 上向き青、売り = 下向き赤)。塗り = maker、枠だけ = taker</span>` +
      `<span><i style="border-color:${AVG}"></i>平均の建値(帳簿の約定の avg_px_after)</span>` +
      `<span>囲み: 取引(建玉 0 → 0)。緑 = 勝ち、橙 = 負け、破線の枠 = 途中</span>` +
      `<span><i style="border-color:${SER.pessimistic.cum}"></i>累計損益${both ? "(悲観側)" : ""}</span>` +
      (both ? `<span><i style="border-color:${SER.optimistic.cum}"></i>累計損益(楽観側)。楽観側の印は薄く描く</span>` : "") +
      `<span>ホイールで拡大・縮小、ドラッグで移動、印をクリックで関連する行をたどる</span>`;
  }

  // time <-> logical index of the bars on screen. A bar is named by its START, an event is stamped at the END of the bar it
  // belongs to: the shift of -0.5 puts a time stamped at a bar's end on that bar's right edge (its close).
  function logicalOfTime(t) {
    const b = PX.bars, n = b.length;
    if (!n) return 0;
    let x;
    if (t <= b[0][0]) x = (t - b[0][0]) / PX.interval;
    else if (t >= b[n - 1][0]) x = n - 1 + (t - b[n - 1][0]) / PX.interval;
    else {
      let lo = 0, hi = n - 1;
      while (hi - lo > 1) { const m = (lo + hi) >> 1; if (b[m][0] <= t) lo = m; else hi = m; }
      x = lo + Math.min((t - b[lo][0]) / PX.interval, 0.999);
    }
    return x - 0.5;
  }
  function timeOfLogical(x) {
    x = x + 0.5;
    const b = PX.bars, n = b.length;
    if (x <= 0) return b[0][0] + x * PX.interval;
    if (x >= n - 1) return b[n - 1][0] + (x - (n - 1)) * PX.interval;
    const i = Math.floor(x);
    return b[i][0] + (x - i) * (b[i + 1][0] - b[i][0]);
  }
  function xOf(t) {
    const ts = PX.price.timeScale(), c0 = ts.logicalToCoordinate(0), c1 = ts.logicalToCoordinate(100);
    if (c0 == null || c1 == null) return null;
    return c0 + logicalOfTime(t) * (c1 - c0) / 100;
  }

  const barsPerView = () => Math.max(200, Math.min(1000, Math.round(($("bt-price").clientWidth || 900) / 2.5)));
  function pickInterval(span) {
    if (PX.opts.frame !== "auto") return PX.opts.frame;
    const bpv = barsPerView();
    for (const i of FRAMES) if (span / i <= bpv) return i;
    return FRAMES[FRAMES.length - 1];
  }

  function fetchChart(from, to, fit, my, keep) {
    if (!SUM) return;
    if (fit) {
      const vf = SUM.period.first_s, vt = SUM.period.last_s, span = Math.max(vt - vf, 60);
      from = vf - span; to = vt + span; keep = [vf, vt];
    }
    let url = `/api/backtest/chart/${enc(RUN)}?max_bars=${barsPerView() * 3}&interval=${pickInterval(Math.max((to - from) / 3, 60))}`;
    if (from != null) url += `&from=${from}&to=${to}`;
    url += `&range=${enc(scope.range)}&instrument=${enc(scope.inst)}`;
    busy("bt-chart-busy", "チャートのデータを読み込み中");
    return getJSON(url).then(d => {
      if (my !== SEQ) return;
      idle("bt-chart-busy"); $("bt-chart-busy").innerHTML = "";
      applyChart(d, keep);
      if (d.building) {  // the price store is being made in the background (first time only): poll, then draw the chart
        const b = d.building;
        const stage = b.stage === "reading" ? "1 分足のファイルを読んでいます" : b.stage === "folding" ? `足を作っています(足 ${b.frame}/${b.frames})` :
          b.stage === "saving" ? `キャッシュに保存しています(足 ${b.frame}/${b.frames})` :
          b.stage === "queued" ? "順番待ちです(別の銘柄を作っています)" : "開始しています";
        $("bt-chart-busy").innerHTML = `<span class="busy">価格のキャッシュを作っています(初回だけ)。銘柄 ${esc(b.label || b.market)}、${esc(stage)}、経過 ${esc(b.elapsed_s)} 秒。` +
          `建玉と累計損益は先に出ています。できたら自動でチャートを出します。</span>`;
        clearTimeout(PX.poll);
        PX.poll = setTimeout(() => { if (my === SEQ) fetchChart(from, to, fit, my, keep); }, 3000);
      }
    }).catch(err => {
      if (my !== SEQ) return;
      idle("bt-chart-busy");
      $("bt-chart-busy").innerHTML = `<span class="warn">チャートの取得に失敗: ${esc(err.message)}</span>`;
      banner("チャートの取得", err);
    });
  }
  function visibleTimes() {
    const lr = PX.price.timeScale().getVisibleLogicalRange();
    return lr && PX.bars.length ? [timeOfLogical(lr.from), timeOfLogical(lr.to)] : null;
  }
  function refetchKeep() {
    if (!SUM || !SUM.price.available) return;
    const v = visibleTimes();
    if (!v) { fetchChart(null, null, true, SEQ); return; }
    const span = v[1] - v[0];
    fetchChart(v[0] - span, v[1] + span, false, SEQ, v);
  }

  function applyChart(d, keep) {
    PX.data = d; PX.bars = d.bars; PX.interval = d.interval_s;
    PX.winFrom = d.from_s; PX.winTo = d.to_s; PX.loLimit = d.chart_lo_s; PX.hiLimit = d.chart_hi_s;
    PX.restoring = true;
    const showPrice = SUM.price.available && !d.building;
    $("bt-pricewrap").hidden = !showPrice;
    if (showPrice) resize();
    PX.candle.setData(SUM.price.available ? d.bars.map(b => ({time: b[0], open: b[1], high: b[2], low: b[3], close: b[4]})) : []);
    setLower();
    showFrameNow();
    const warn = $("bt-o-warn");
    if (warn) {
      const tm = [];
      for (const r of d.shown_ranges) for (const [k, n] of Object.entries(d.layers[r].too_many)) tm.push(`${(LAYERS.find(x => x[0] === k) || [k, k])[1]} ${num(n)} 件`);
      const c = d.layers[d.shown_ranges[0]].counts;
      warn.textContent = tm.length ? `この範囲に多すぎる: ${[...new Set(tm)].join("、")}(上限は層ごと)。拡大すると出る` :
        `表示中: 合図 ${num(c.signals)}・注文 ${num(c.orders)}・約定 ${num(c.fills)}・取引 ${num(c.trades)}(${width(d.interval_s)})`;
    }
    const old = $("bt-narrow"); if (old) old.remove();
    if (d.narrowed) $("bt-price-note").insertAdjacentHTML("beforeend", ` <span class="warn" id="bt-narrow">この足(${esc(width(d.interval_s))})では ${num(d.narrowed.max_bars)} 本までしか出せない(この範囲だと ${num(d.narrowed.requested_bars)} 本)ので範囲を狭めた。</span>`);
    if (SUM.price.available && d.bars.length) {
      let done = false;
      if (keep) {
        const kf = Math.max(keep[0], d.from_s), kt = Math.min(keep[1], d.to_s);
        if (kt > kf) {
          try { PX.price.timeScale().setVisibleLogicalRange({from: logicalOfTime(kf), to: logicalOfTime(kt)}); done = true; } catch (e) { /* outside data */ }
        }
      }
      if (!done) PX.price.timeScale().fitContent();
    } else {
      PX.pos.timeScale().fitContent(); PX.pnl.timeScale().fitContent();
    }
    setTimeout(() => {
      PX.restoring = false; PX.sig = "";
      const lr = SUM.price.available ? PX.price.timeScale().getVisibleLogicalRange() : null;
      if (lr) syncLower(lr, "price");
    }, 300);
  }

  // position and cumulative profit: one point per bar on screen (so the charts share the time axis), else the sent points
  function lowerRows(pts) {
    if (PX.bars.length && SUM.price.available) {
      const rows = []; let j = 0, cur = pts.length ? pts[0][1] : 0;
      for (const b of PX.bars) {
        while (j < pts.length && pts[j][0] <= b[0]) { cur = pts[j][1]; j++; }
        rows.push({time: b[0], value: cur});
      }
      return rows;
    }
    return pts.map(p => ({time: p[0], value: p[1]}));
  }
  function setLower() {
    const d = PX.data;
    if (!d) return;
    for (const r of ["pessimistic", "optimistic"]) {
      const L = d.layers[r], S = PX.series[r];
      S.pos.setData(L ? lowerRows(L.pos) : []);
      S.cum.setData(L ? lowerRows(L.cum) : []);
    }
    PX.pnl.applyOptions({localization: {priceFormatter: v => num(v, 0)}});
  }
  function syncLower(r, from) {
    if (!r || PX.syncing || PX.restoring || !SUM || !SUM.price.available) return;
    PX.syncing = true;
    try {
      if (from !== "price") PX.price.timeScale().setVisibleLogicalRange(r);
      if (from !== "pos") PX.pos.timeScale().setVisibleLogicalRange(r);
      if (from !== "pnl") PX.pnl.timeScale().setVisibleLogicalRange(r);
    } catch (e) { /* not ready */ }
    PX.syncing = false;
  }

  function onRange() {
    if (PX.restoring || !PX.bars.length || !SUM || !SUM.price.available) return;
    clearTimeout(PX.timer);
    PX.timer = setTimeout(() => {
      const v = visibleTimes();
      if (!v) return;
      const vf = Math.max(PX.loLimit, v[0]), vt = Math.min(PX.hiLimit, v[1]);
      if (!(vt > vf)) return;
      const span = vt - vf, want = pickInterval(span), tol = PX.interval;
      const okL = PX.winFrom <= PX.loLimit + 1 || vf >= PX.winFrom - tol, okR = PX.winTo >= PX.hiLimit - 1 || vt <= PX.winTo + tol;
      if (want === PX.interval && okL && okR) return;
      fetchChart(vf - span, vt + span, false, SEQ, [vf, vt]);
    }, 280);
  }

  // move the chart to a time (a row picked in a table or in the trace)
  function focusTime(t0, t1) {
    if (t0 == null) return;
    if (VIEW !== "chart") { PX.focus = [t0, t1]; showView("chart"); return; }
    if (!SUM.price.available || !PX.price) return;
    const end = t1 == null ? t0 : t1;
    const pad = Math.max((end - t0) * 0.5, 30 * 60);
    const f = t0 - pad, t = end + pad, span = t - f;
    fetchChart(f - span, t + span, false, SEQ, [f, t]);
  }

  // ---- the layers --------------------------------------------------------------------------------------------
  function loop() {
    PX.raf = requestAnimationFrame(loop);
    if (!PX.price || $("view-backtest").hidden || $("bt-v-chart").hidden || !PX.data || !SUM || !SUM.price.available) return;
    const ts = PX.price.timeScale();
    const sig = [ts.logicalToCoordinate(0), ts.logicalToCoordinate(100), PX.candle.priceToCoordinate(1), PX.candle.priceToCoordinate(1000000),
      $("bt-overlay").width, PX.bars.length, JSON.stringify(PX.opts.layers), PX.opts.labels, PX.interval, PX.sel, PX.data.from_s,
      PX.data.shown_ranges.join()].join("|");
    if (sig === PX.sig) return;
    PX.sig = sig;
    draw();
  }

  const segDist = (mx, my, x1, y1, x2, y2) => {
    const dx = x2 - x1, dy = y2 - y1, L = dx * dx + dy * dy;
    let u = L ? ((mx - x1) * dx + (my - y1) * dy) / L : 0;
    u = Math.max(0, Math.min(1, u));
    return Math.hypot(mx - (x1 + u * dx), my - (y1 + u * dy));
  };

  function draw() {
    const cv = $("bt-overlay"), ctx = cv.getContext("2d"), dpr = window.devicePixelRatio || 1, d = PX.data;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    PX.hits = [];
    if (!PX.bars.length) return;
    const w = cv.width / dpr, h = cv.height / dpr;
    const plotW = w - PX.price.priceScale("right").width(), plotH = h - PX.price.timeScale().height();
    ctx.save();
    ctx.beginPath(); ctx.rect(0, 0, plotW, plotH); ctx.clip();
    const per = SUM.period;
    ctx.font = "11px system-ui, sans-serif";
    ctx.setLineDash([2, 4]); ctx.lineWidth = 1;
    [["開始", per.first_s], ["終了", per.last_s]].forEach(([name, t], k) => {
      const x = xOf(t);
      if (x == null || x < 0 || x > plotW) return;
      ctx.strokeStyle = "#c9d3e3"; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, plotH); ctx.stroke();
      ctx.fillStyle = "#c9d3e3"; ctx.textAlign = k === 0 ? "left" : "right";
      ctx.fillText(`${name} ${utc(t, true)}`, x + (k === 0 ? 4 : -4), plotH - 6);
    });
    ctx.setLineDash([]);
    const rs = d.shown_ranges, both = rs.length > 1;
    for (const rg of [...rs].reverse()) drawRange(ctx, rg, d.layers[rg], plotW, plotH, both && rg === "optimistic");
    ctx.restore();
  }

  function drawRange(ctx, rg, L, plotW, plotH, faint) {
    const on = PX.opts.layers, Y = p => PX.candle.priceToCoordinate(p), o = PX.opts;
    const a = faint ? 0.5 : 1;
    const isSel = (tbl, row) => PX.sel === tbl + ":" + row + ":" + rg;
    const hit = (type, extra) => PX.hits.push(Object.assign({type, rg}, extra));
    // signals: a band over the time the signal was on
    if (on.signals) for (const s of L.signals) {
      const x1 = xOf(s.t0), x2 = xOf(s.t1);
      if (x1 == null || x2 == null || x2 < 0 || x1 > plotW) continue;
      const long = s.direction === "long";
      ctx.globalAlpha = a;
      ctx.fillStyle = long ? "rgba(77,163,255,.11)" : "rgba(255,90,95,.11)";
      const xa = Math.max(x1, -5), xb = Math.min(Math.max(x2, xa + 1.5), plotW + 5);
      ctx.fillRect(xa, 0, xb - xa, plotH);
      ctx.strokeStyle = long ? "rgba(77,163,255,.55)" : "rgba(255,90,95,.55)";
      ctx.lineWidth = isSel("signals", s.row) ? 2.5 : 1;
      ctx.setLineDash(s.open ? [5, 4] : []);
      ctx.beginPath(); ctx.moveTo(x1, 0); ctx.lineTo(x1, plotH); ctx.stroke();
      if (!s.open) { ctx.beginPath(); ctx.moveTo(x2, 0); ctx.lineTo(x2, plotH); ctx.stroke(); }
      ctx.setLineDash([]);
      if (xb - xa > 46) { ctx.fillStyle = long ? "#8fc3ff" : "#ff9a9d"; ctx.textAlign = "left"; ctx.fillText(`${s.kind}・${s.direction}`, xa + 3, 12); }
      ctx.globalAlpha = 1;
      hit("signals", {x1: xa, x2: xb, y1: 0, y2: 18, row: s.row, s});
    }
    // trades: a box from the first to the last fill over the prices of its fills
    if (on.trades) {
      const labels = o.labels && L.trades.length <= MAX_LABEL;
      for (const t of L.trades) {
        if (t.lo == null) continue;
        const x1 = xOf(t.t0), x2 = xOf(t.t1), ya = Y(t.hi), yb = Y(t.lo);
        if (x1 == null || x2 == null || ya == null || yb == null || x2 < 0 || x1 > plotW) continue;
        const win = (t.pnl || 0) > 0, col = t.pnl == null ? "#aab" : win ? "123,216,143" : "255,179,71";
        const top = Math.min(ya, yb) - 7, bot = Math.max(ya, yb) + 7, xb = Math.max(x2, x1 + 3);
        ctx.globalAlpha = a;
        ctx.fillStyle = `rgba(${col},.10)`; ctx.fillRect(x1, top, xb - x1, bot - top);
        ctx.strokeStyle = `rgba(${col},.85)`; ctx.lineWidth = isSel("trades", t.row) ? 2.5 : 1.2;
        ctx.setLineDash(t.open ? [5, 3] : []); ctx.strokeRect(x1, top, xb - x1, bot - top); ctx.setLineDash([]);
        if (labels) { ctx.fillStyle = win ? WIN : LOSE; ctx.textAlign = "left"; ctx.fillText(signed(t.pnl, 1) + "円", xb + 4, top + 10); }
        ctx.globalAlpha = 1;
        hit("trades", {x1, x2: xb, y1: top, y2: bot, row: t.row, t});
      }
    }
    // orders: a horizontal line at the sent price from placed to closed
    if (on.orders) for (const od of L.orders) {
      const x1 = xOf(od.t0), x2 = xOf(od.t1), y = Y(od.px);
      if (x1 == null || x2 == null || y == null || (x2 < 0) || (x1 > plotW)) continue;
      const col = od.side === "buy" ? BUY : SELL;
      ctx.globalAlpha = a * 0.85; ctx.strokeStyle = col; ctx.fillStyle = col;
      ctx.lineWidth = isSel("orders", od.row) ? 3 : 1.3;
      if (od.kind === "zero") {  // 量が 0 で出さない: a hollow cross where the line would have started
        ctx.beginPath(); ctx.moveTo(x1 - 4, y - 4); ctx.lineTo(x1 + 4, y + 4); ctx.moveTo(x1 - 4, y + 4); ctx.lineTo(x1 + 4, y - 4); ctx.stroke();
        ctx.beginPath(); ctx.arc(x1, y, 7, 0, 6.2832); ctx.setLineDash([2, 2]); ctx.stroke(); ctx.setLineDash([]);
        ctx.globalAlpha = 1;
        hit("orders", {x1: x1 - 7, y1: y, x2: x1 + 7, y2: y, row: od.row, o: od});
        continue;
      }
      const dash = {filled: [], canceled: [6, 4], venue_closed: [1, 4], rejected: [2, 2], partial: [], open: [10, 4]}[od.kind] || [];
      ctx.setLineDash(dash);
      ctx.beginPath(); ctx.moveTo(x1, y); ctx.lineTo(Math.max(x2, x1 + 2), y); ctx.stroke(); ctx.setLineDash([]);
      ctx.beginPath(); ctx.arc(x1, y, 2.4, 0, 6.2832); ctx.fill();  // placed
      if (od.kind === "canceled" || od.kind === "rejected") {
        ctx.beginPath(); ctx.moveTo(x2 - 3.5, y - 3.5); ctx.lineTo(x2 + 3.5, y + 3.5); ctx.moveTo(x2 - 3.5, y + 3.5); ctx.lineTo(x2 + 3.5, y - 3.5); ctx.stroke();
      } else if (od.kind === "venue_closed") {
        ctx.beginPath(); ctx.moveTo(x2, y - 5); ctx.lineTo(x2, y + 5); ctx.stroke();
      }
      ctx.globalAlpha = 1;
      hit("orders", {x1, y1: y, x2: Math.max(x2, x1 + 2), y2: y, row: od.row, o: od});
    }
    // average entry price: a step line (the ledger's avg_px_after), a gap where the position is 0
    if (on.avg && L.avg.length) {
      ctx.globalAlpha = a; ctx.strokeStyle = AVG; ctx.lineWidth = 1.8;
      const pts = L.avg, end = xOf(PX.data.to_s);
      for (let i = 0; i < pts.length; i++) {
        const v = pts[i][1];
        if (v == null) continue;
        const x1 = xOf(pts[i][0]), x2 = i + 1 < pts.length ? xOf(pts[i + 1][0]) : end, y = Y(v);
        if (x1 == null || x2 == null || y == null) continue;
        ctx.beginPath(); ctx.moveTo(x1, y); ctx.lineTo(x2, y);
        if (i + 1 < pts.length && pts[i + 1][1] != null) { const y2 = Y(pts[i + 1][1]); if (y2 != null) ctx.lineTo(x2, y2); }
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }
    // fills: arrows (buy up / sell down), filled = maker, outline = taker
    if (on.fills) for (const f of L.fills) {
      const x = xOf(f.t), y = Y(f.px);
      if (x == null || y == null || x < -10 || x > plotW + 10) continue;
      const col = f.side === "buy" ? BUY : SELL, up = f.side === "buy", sel = isSel("fills", f.row);
      ctx.globalAlpha = a; ctx.strokeStyle = sel ? "#fff" : col; ctx.fillStyle = col; ctx.lineWidth = sel ? 2.2 : 1.4;
      const s = sel ? 7 : 5, hgt = sel ? 12 : 9;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - s, y + (up ? hgt : -hgt)); ctx.lineTo(x + s, y + (up ? hgt : -hgt)); ctx.closePath();
      if (f.liquidity === "maker") ctx.fill();
      ctx.stroke();
      ctx.globalAlpha = 1;
      hit("fills", {x, y: y + (up ? 5 : -5), row: f.row, f});
    }
  }

  function tipText(h) {
    const rj = RANGE_JA[h.rg] || h.rg;
    if (h.type === "fills") {
      const f = h.f;
      return `約定 ${f.id}  ${f.side === "buy" ? "買い" : "売り"}  ${f.liquidity}(${rj})\n${utcSec(f.t)}\n値段 ${num(f.px, 2)}  量 ${f.qty}\n` +
        `注文 ${f.order}  合図 ${f.signal}\n当て方 ${f.case || "(tier の決まり)"}${f.rule ? "・" + f.rule : ""}\nクリックで関連する行をたどる`;
    }
    if (h.type === "orders") {
      const o = h.o;
      return `注文 ${o.id}  ${o.side === "buy" ? "買い" : "売り"}(${rj})\n${KIND_JA[o.kind] || o.kind}${o.state ? "・状態 " + o.state : ""}\n` +
        `送った指値 ${num(o.px, 2)}  量 ${o.qty || "—"}  約定した量 ${o.filled || "0"}\n出した ${utcSec(o.t0)}${o.open ? "" : "\n閉じた/約定 " + utcSec(o.t1)}\n` +
        `合図 ${o.signal}  段数 ${o.levels || "—"}${o.exit_kind ? "  決済の種類 " + o.exit_kind : ""}${o.close_reason ? "\n閉じた理由 " + o.close_reason : ""}\nクリックで関連する行をたどる`;
    }
    if (h.type === "trades") {
      const t = h.t;
      return `取引 ${t.id}  ${t.direction}  段 ${t.levels}  ${t.status === "closed" ? "閉じた" : "途中"}(${rj})\n${utcSec(t.t0)} 〜 ${t.open ? "(途中)" : utcSec(t.t1)}\n` +
        `損益 ${signed(t.pnl, 2)} 円  合図 ${t.signal}\n保有 ${t.hold_ns ? num(Number(t.hold_ns) / 6e10, 1) + " 分" : "—"}\nクリックで関連する行をたどる`;
    }
    const s = h.s;
    return `合図 ${s.id}  ${s.kind}  ${s.direction}(${rj})\n${utcSec(s.t0)} 〜 ${s.open ? "(データの終わりまで)" : utcSec(s.t1)}\n` +
      `見た値 ${s.value}\n消失の理由 ${s.reason}\nクリックで関連する行をたどる`;
  }
  function hitAt(mx, my) {
    let best = null, bd = 1e9;
    const prio = {fills: 0, orders: 1, trades: 2, signals: 3};
    for (const h of PX.hits) {
      let dist = null;
      if (h.type === "fills") { dist = Math.hypot(mx - h.x, my - h.y); if (dist > 9) dist = null; }
      else if (h.type === "orders") { dist = segDist(mx, my, h.x1, h.y1, h.x2, h.y2); if (dist > 5) dist = null; }
      else if (h.type === "trades") { if (mx >= h.x1 && mx <= h.x2 && my >= h.y1 && my <= h.y2) dist = 20; }
      else if (mx >= h.x1 && mx <= h.x2 && my >= h.y1 && my <= h.y2) dist = 30;
      if (dist == null) continue;
      const score = prio[h.type] * 100 + dist;
      if (score < bd) { bd = score; best = h; }
    }
    return best;
  }
  function onMove(ev) {
    const tip = $("bt-tip");
    const r = $("bt-pricewrap").getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top;
    const h = PX.hits.length ? hitAt(mx, my) : null;
    if (!h) { tip.style.display = "none"; return; }
    tip.textContent = tipText(h);
    tip.style.display = "block";
    tip.style.left = Math.min(mx + 14, r.width - 300) + "px"; tip.style.top = Math.min(my + 14, r.height - 150) + "px";
  }
  function onClick(ev) {
    const r = $("bt-pricewrap").getBoundingClientRect();
    const h = hitAt(ev.clientX - r.left, ev.clientY - r.top);
    if (!h) return;
    selectRow(h.type, h.row, h.rg);
  }

  // ---- the tables --------------------------------------------------------------------------------------------
  function tableRange() { return scope.range === "both" ? "all" : scope.range; }
  function loadTable() {
    const box = $("bt-v-table");
    let h = '<div class="bt-views sub">' + TABLES.map(([k, l]) => `<button data-t="${k}" class="${k === TBL.table ? "on" : ""}">${l}</button>`).join("") + "</div>";
    h += '<div id="bt-tbl-body"></div>';
    box.innerHTML = h;
    box.querySelectorAll("button[data-t]").forEach(b => b.onclick = () => {
      TBL.table = b.dataset.t; TBL.sort = null; TBL.desc = false; TBL.filters = []; TBL.page = 0; loadTable();
    });
    const my = SEQ;
    busy("bt-tbl-body", "表を読み込み中");
    let url = `/api/backtest/table/${enc(RUN)}/${TBL.table}?instrument=${enc(scope.inst)}&range=${enc(tableRange())}&page=${TBL.page}&size=${TBL.size}`;
    if (TBL.sort) url += `&sort=${enc(TBL.sort)}&dir=${TBL.desc ? "desc" : "asc"}`;
    if (TBL.filters.length) url += `&f=${enc(JSON.stringify(TBL.filters))}`;
    getJSON(url).then(d => {
      if (my !== SEQ) return;
      idle("bt-tbl-body");
      TBL.data = d;
      renderTable();
    }).catch(err => { idle("bt-tbl-body"); const b = $("bt-tbl-body"); if (b) b.innerHTML = `<div class="warn">表を読み込めなかった: ${esc(err.message)}</div>`; banner("表", err); });
  }
  const OPS = [["contains", "含む"], ["eq", "="], ["ne", "≠"], ["gt", ">"], ["ge", "≥"], ["lt", "<"], ["le", "≤"], ["empty", "空"], ["nonempty", "空でない"]];
  function renderTable() {
    const d = TBL.data, body = $("bt-tbl-body");
    const cols = d.columns;
    let h = `<div class="bt-notes">${esc(d.table_ja)}(${esc(d.table)}): 表の全 ${num(d.total)} 行のうち、いまの銘柄・範囲(${esc(d.range === "all" ? "両方" : RANGE_JA[d.range] || d.range)})で絞った ${num(d.matched)} 行。` +
      `列は SCHEMA.json の ${cols.length} 列を全部出している(列名にカーソルで単位と意味)。時刻は UTC の ns の整数(下の小さい字は読みやすくした UTC)。封印の境より後の行は出さない。</div>`;
    h += '<div class="bt-filter"><label>絞り込み <select id="bt-f-col">' + cols.map(c => `<option>${esc(c.name)}</option>`).join("") + "</select></label>" +
      '<select id="bt-f-op">' + OPS.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join("") + "</select>" +
      '<input id="bt-f-val" placeholder="値"> <button id="bt-f-add">追加</button>';
    h += TBL.filters.map((f, i) => `<span class="chip">${esc(f[0])} ${esc((OPS.find(o => o[0] === f[1]) || [0, f[1]])[1])} ${esc(f[2])} <a data-rm="${i}">×</a></span>`).join("");
    h += TBL.filters.length ? ' <button id="bt-f-clear">全部外す</button>' : "";
    h += "</div>";
    h += '<div class="bt-pager">' + `<button id="bt-p-prev"${d.page <= 0 ? " disabled" : ""}>前へ</button> ページ ${d.page + 1} / ${d.pages} ` +
      `<button id="bt-p-next"${d.page + 1 >= d.pages ? " disabled" : ""}>次へ</button> 1 ページ <select id="bt-p-size">` +
      [50, 100, 300, 1000].map(n => `<option${n === TBL.size ? " selected" : ""}>${n}</option>`).join("") + "</select> 行</div>";
    h += '<div class="bt-tblwrap"><table class="bt-data"><thead><tr><th>#</th>' + cols.map(c => {
      const arrow = TBL.sort === c.name ? (TBL.desc ? " ▼" : " ▲") : "";
      return `<th data-col="${esc(c.name)}" title="${esc(c.unit)}: ${esc(c.desc)}">${esc(c.name)}${arrow}<div class="u">${esc(c.unit)}</div></th>`;
    }).join("") + "</tr></thead><tbody>";
    d.rows.forEach((r, i) => {
      h += `<tr data-row="${esc(d.row_ids[i])}" class="${PX.sel === d.table + ":" + d.row_ids[i] + ":" + (r[1] || "") ? "sel" : ""}"><td class="num">${d.row_ids[i]}</td>` + r.map((v, k) => {
        const c = cols[k], ts = c.unit === "ns" ? nsTime(v) : "";
        return `<td class="${c.numeric ? "num" : ""}">${esc(v === "" ? "" : v)}${ts ? `<div class="u">${ts}</div>` : ""}</td>`;
      }).join("") + "</tr>";
    });
    h += "</tbody></table></div>";
    if (!d.rows.length) h += '<div class="empty">この絞り込みに合う行は無い</div>';
    body.innerHTML = h;
    body.querySelectorAll("th[data-col]").forEach(th => th.onclick = () => {
      if (TBL.sort === th.dataset.col) TBL.desc = !TBL.desc; else { TBL.sort = th.dataset.col; TBL.desc = false; }
      TBL.page = 0; loadTable();
    });
    $("bt-f-add").onclick = () => {
      const op = $("bt-f-op").value, val = $("bt-f-val").value;
      if (op !== "empty" && op !== "nonempty" && val === "") return;
      TBL.filters.push([$("bt-f-col").value, op, val]); TBL.page = 0; loadTable();
    };
    $("bt-f-val").onkeydown = e => { if (e.key === "Enter") $("bt-f-add").click(); };
    body.querySelectorAll("a[data-rm]").forEach(a => a.onclick = () => { TBL.filters.splice(Number(a.dataset.rm), 1); TBL.page = 0; loadTable(); });
    const cl = $("bt-f-clear"); if (cl) cl.onclick = () => { TBL.filters = []; TBL.page = 0; loadTable(); };
    $("bt-p-prev").onclick = () => { TBL.page = Math.max(0, TBL.page - 1); loadTable(); };
    $("bt-p-next").onclick = () => { TBL.page += 1; loadTable(); };
    $("bt-p-size").onchange = e => { TBL.size = Number(e.target.value); TBL.page = 0; loadTable(); };
    body.querySelectorAll("tbody tr").forEach(tr => tr.onclick = () => {
      if (d.table === "summary") return;
      const rowId = Number(tr.dataset.row), cells = tr.querySelectorAll("td");
      selectRow(d.table, rowId, cells[2] ? cells[2].childNodes[0].textContent : null);
    });
  }

  // ---- following the numbers (the trace) ---------------------------------------------------------------------
  function selectRow(table, row, rg) {
    if (table === "fx" || table === "summary") return;
    const my = SEQ;
    PX.sel = table + ":" + row + ":" + (rg || "");
    PX.sig = "";
    const box = $("bt-trace");
    box.hidden = false;
    busy("bt-trace", "行をたどっています");
    getJSON(`/api/backtest/trace/${enc(RUN)}/${table}/${row}?instrument=${enc(scope.inst)}`).then(tr => {
      if (my !== SEQ) return;
      idle("bt-trace");
      PX.sel = table + ":" + row + ":" + tr.range;
      PX.sig = "";
      renderTrace(tr);
    }).catch(err => { idle("bt-trace"); box.innerHTML = `<div class="warn">たどれなかった: ${esc(err.message)}</div>`; banner("行をたどる", err); });
  }
  function renderTrace(tr) {
    const box = $("bt-trace"), nm = Object.fromEntries(TABLES);
    let h = `<h3>選んだ行: ${esc(nm[tr.table])}(${esc(tr.table)})の ${tr.row} 行目 <span class="n">${esc(tr.instrument)}・${esc(RANGE_JA[tr.range] || tr.range)}</span></h3>`;
    h += '<div class="bt-trace-top">';
    if (tr.t_s != null) h += `<button id="bt-tr-go">チャートでこの時刻を見る(${esc(utcSec(tr.t_s))})</button> `;
    h += `<button id="bt-tr-close">閉じる</button></div>`;
    h += '<table class="bt-t kv">' + Object.entries(tr.record).map(([k, v]) => `<tr><td>${esc(k)}</td><td class="mono">${esc(v)}${/_t_ns$|^t_ns$|^venue_t_ns$/.test(k) && nsTime(v) ? ` <span class="u">${nsTime(v)}</span>` : ""}</td></tr>`).join("") + "</table>";
    h += '<div class="bt-links">';
    for (const l of tr.links) {
      h += `<details${l.count ? " open" : ""}><summary>${esc(l.label)}(${esc(l.table)}): ${num(l.count)} 行${l.count > l.rows.length ? `(先頭の ${l.rows.length} 行だけ出している)` : ""}</summary>`;
      if (l.rows.length) {
        h += '<div class="bt-tblwrap"><table class="bt-data"><thead><tr><th>#</th>' + l.columns.map(c => `<th>${esc(c)}</th>`).join("") + "</tr></thead><tbody>";
        l.rows.forEach((r, i) => { h += `<tr data-tt="${esc(l.table)}" data-tr="${esc(l.row_ids[i])}"><td class="num">${l.row_ids[i]}</td>` + r.map(v => `<td>${esc(v)}</td>`).join("") + "</tr>"; });
        h += "</tbody></table></div>";
      }
      h += "</details>";
    }
    h += "</div>";
    box.innerHTML = h;
    box.querySelectorAll("tr[data-tt]").forEach(tr2 => tr2.onclick = () => selectRow(tr2.dataset.tt, Number(tr2.dataset.tr), tr.range));
    const go = $("bt-tr-go"); if (go) go.onclick = () => focusTime(tr.t_s, tr.t_end_s);
    $("bt-tr-close").onclick = () => { box.hidden = true; PX.sel = null; PX.sig = ""; };
    box.scrollIntoView({block: "nearest"});
  }

  // ---- record.json and SCHEMA.json ---------------------------------------------------------------------------
  function loadRecord() {
    const box = $("bt-v-record"), my = SEQ;
    busy("bt-v-record", "record.json と SCHEMA.json を読み込み中");
    Promise.all([getJSON(`/api/backtest/file/${enc(RUN)}/record.json`), getJSON(`/api/backtest/file/${enc(RUN)}/SCHEMA.json`)]).then(([rec, sch]) => {
      if (my !== SEQ) return;
      idle("bt-v-record");
      const S = sch.json;
      let h = `<h3>道の記録の版 ${esc(S.version)}</h3><div class="bt-notes">${esc(S.form)}<br>${esc(S.keys)}<br>${esc(S.read_from)}</div>`;
      h += "<h3>表と列(road/SCHEMA.json)</h3>";
      for (const [t, spec] of Object.entries(S.tables)) {
        h += `<details><summary>${esc(t)}(${esc(spec.file)}・${esc(spec.kind)}): ${esc(spec.row)}</summary><table class="bt-t"><tr><th>列</th><th>単位</th><th>意味</th></tr>` +
          spec.columns.map(c => `<tr><td class="mono">${esc(c[0])}</td><td>${esc(c[1])}</td><td>${esc(c[2])}</td></tr>`).join("") + "</table></details>";
      }
      h += `<details><summary>fill_rules(約定の決まりの説明)</summary><ul>${(S.fill_rules || []).map(x => `<li>${esc(x)}</li>`).join("")}</ul></details>`;
      h += `<details><summary>limits(検査で塞ぎ切れないこと)</summary><ul>${(S.limits || []).map(x => `<li>${esc(x)}</li>`).join("")}</ul></details>`;
      h += `<details><summary>SCHEMA.json そのまま</summary><pre>${esc(JSON.stringify(S, null, 1))}</pre></details>`;
      h += `<details open><summary>record.json そのまま</summary><pre>${esc(JSON.stringify(rec.json, null, 1))}</pre></details>`;
      box.innerHTML = h;
    }).catch(err => { idle("bt-v-record"); box.innerHTML = `<div class="warn">読み込めなかった: ${esc(err.message)}</div>`; banner("記録", err); });
  }

  // ---- start -------------------------------------------------------------------------------------------------
  window.btInit = function () {
    if (CAT) { resize(); PX.sig = ""; return Promise.resolve(); }
    busy("bt-tree", "テーマの一覧を読み込み中");
    return getJSON("/api/backtest/catalog").then(c => {
      idle("bt-tree");
      CAT = c;
      renderTree();
      const first = allStrategies().find(s => s.kind === "road") || allStrategies()[0];
      if (first) selectStrategy(first.id);
      else $("bt-head").innerHTML = '<span class="empty">実行がまだ無い</span>';
    }).catch(err => { idle("bt-tree"); $("bt-tree").innerHTML = `<span class="empty">読み込めなかった: ${esc(err.message)}</span>`; banner("テーマの一覧", err); });
  };
})();
