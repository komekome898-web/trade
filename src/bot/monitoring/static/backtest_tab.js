/* The バックテスト tab of scripts/dashboard.py: theme tree -> strategy -> family dropdowns -> one run's chart.
   Data: /api/backtest/catalog, /api/backtest/summary/<id>, /api/backtest/chart/<id>?from&to&interval&max_bars&range,
   /api/backtest/run/<id> (the ten detail tabs). The chart library (TradingView lightweight-charts, Apache-2.0) is
   served from /static/, so the tab works without a network. */
(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const esc = s => String(s == null ? "—" : s).replace(/[&<>"']/g,
    c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const BUY = "#4da3ff", SELL = "#ff5a5f", WIN = "#7bd88f", LOSE = "#ffb347", CUM = "#ffd84d";
  const MAX_TRADES_LABEL = 150;
  const FRAMES = [60, 300, 900, 3600, 14400, 86400];
  const FRAME_NAME = {60: "1分", 300: "5分", 900: "15分", 3600: "1時間", 14400: "4時間", 86400: "日足"};

  let CAT = null, STRAT = null, SEL = {}, VER = 0, RUN = null, SUM = null, SEQ = 0;
  let detailRun = null, btView = null;
  const PX = {price: null, candle: null, pnl: null, pnlSeries: null, bars: [], interval: 0, base: 60, intervals: [60],
              winFrom: 0, winTo: 0, loLimit: 0, hiLimit: 0, data: null, segs: [], timer: null, restoring: false,
              syncing: false, sig: "", raf: 0, opts: {arrows: true, labels: false, unit: "ccy", range: null, frame: "auto"}};

  window.btState = PX;  // for the browser probe of the tab (no page logic reads it)
  // ---- helpers -----------------------------------------------------------------------------------------------
  const num = (v, d) => v == null ? "—" : Number(v).toLocaleString("ja-JP", {maximumFractionDigits: d == null ? 0 : d, minimumFractionDigits: 0});
  const signed = (v, d) => v == null ? "—" : (v > 0 ? "+" : "") + num(v, d);
  const utc = (s, withTime) => {
    const d = new Date(s * 1000), p = n => String(n).padStart(2, "0");
    const day = d.getUTCFullYear() + "-" + p(d.getUTCMonth() + 1) + "-" + p(d.getUTCDate());
    return withTime ? day + " " + p(d.getUTCHours()) + ":" + p(d.getUTCMinutes()) : day;
  };
  const width = n => n >= 86400 ? (n / 86400) + "日足" : n >= 3600 ? (n / 3600) + "時間足" : (n / 60) + "分足";
  function moneyDigits(ccy, v) { return Math.abs(v) < 1000 && ccy !== "JPY" ? 2 : 0; }
  const unitName = () => (SUM && SUM.currency) ? (SUM.currency === "JPY" ? "円" : SUM.currency) : "通貨の記録なし";
  // Every request has a time limit and says why it failed (HTTP status, the server's error text, time-out, no connection):
  // the page never stays black without a reason.
  const FETCH_MS = 150000;
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
  // "読み込み中" with the seconds waited, for as long as the request runs
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

  // ---- the tree ----------------------------------------------------------------------------------------------
  function renderTree() {
    let h = "";
    for (const th of CAT.themes) {
      if (!th.strategies.length) continue;
      h += `<details open><summary>${esc(th.title)}${th.owner_origin ? ' <span class="n">オーナー由来</span>' : ""}</summary><div class="sum">${esc(th.summary)}</div>`;
      for (const st of th.strategies) {
        const un = (st.unavailable || []).length;
        h += `<button class="st" data-sid="${esc(st.id)}">${esc(st.title)} <span class="n">${st.n_runs} 本${un ? "・選べない " + un + " 本" : ""}</span></button>`;
      }
      h += "</details>";
    }
    $("bt-tree").innerHTML = h || '<span class="empty">実行がまだ無い</span>';
    $("bt-tree").querySelectorAll("button.st").forEach(b => b.onclick = () => selectStrategy(b.dataset.sid));
  }
  function allStrategies() { return CAT.themes.flatMap(t => t.strategies); }

  function selectStrategy(sid) {
    STRAT = allStrategies().find(s => s.id === sid);
    if (!STRAT) return;
    $("bt-tree").querySelectorAll("button.st").forEach(b => b.classList.toggle("on", b.dataset.sid === sid));
    renderHead();
    const first = STRAT.runs.find(r => r.run_id === STRAT.default_run_id) || STRAT.runs[0];
    if (!first) {  // a card with nothing to show yet (no measurement, or every variant not exported / being written)
      SEL = {}; VER = 0; SEQ++; RUN = null; SUM = null;
      $("bt-family").hidden = true; $("bt-chartbox").hidden = true; $("bt-stats").innerHTML = "";
      return;
    }
    SEL = Object.assign({}, first.axes);
    VER = 0;
    renderFamily("");
    chooseRun();
  }

  function renderHead() {
    const s = STRAT;
    const axSrc = s.axes.map(a => `<li>${esc(a.label)}: ${esc(a.source)}</li>`).join("");
    $("bt-head").innerHTML = `<div class="bt-crumb">${esc(s.theme)}</div><h2>${esc(s.title)}</h2>` +
      `<ul class="bt-desc">${s.description.map(t => `<li>${esc(t)}</li>`).join("")}</ul>` +
      `<details class="bt-src"><summary>説明の出所</summary><ul>${s.sources.map(t => `<li>${esc(t)}</li>`).join("")}${axSrc}</ul></details>` +
      renderUnavailable(s);
  }
  // card variants that cannot be chosen: being written (準備中), not exported, the check did not match, and what the manifest excludes
  function renderUnavailable(s) {
    const un = s.unavailable || [], ex = s.excluded || [];
    let h = "";
    if (!s.runs.length && s.card) h += '<div class="bt-msg">この組に、いま表示できる変種は無い。</div>';
    if (un.length)
      h += `<details class="bt-unav" ${s.runs.length ? "" : "open"}><summary>選べない変種 ${un.length} 本(理由つき)</summary><ul>` +
        un.map(u => `<li><b>${esc(u.axes_text)}</b>(${esc(u.variant)}) — ${esc(u.state_label)}${u.reason && u.reason !== u.state_label ? ": " + esc(u.reason) : ""}</li>`).join("") + "</ul></details>";
    if (ex.length)
      h += `<details class="bt-unav" open><summary>対象外 ${ex.length} 件</summary><ul>` +
        ex.map(u => `<li><b>${esc(u.variant)}</b> — ${esc(u.reason)}</li>`).join("") + "</ul></details>";
    return h;
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
    let h = '<div class="bt-axes">', notes = [];
    for (const a of ax) {
      const cur = SEL[a.key];
      const ent = a.values.find(v => v.value === cur);
      if (a.fixed) {
        h += `<div class="fixed">${esc(a.label)}(この戦略では固定)<b>${esc(ent ? ent.label : cur)}</b></div>`;
      } else {
        h += `<label>${esc(a.label)}<select data-axis="${esc(a.key)}">` + a.values.map(v => {
          const reach = matching(Object.assign({}, SEL, {[a.key]: v.value})).length > 0;
          return `<option value="${esc(v.value)}"${v.value === cur ? " selected" : ""}>${esc(v.label)}${reach ? "" : "(この組み合わせの実行は無い)"}</option>`;
        }).join("") + "</select></label>";
      }
      if (ent && ent.note) notes.push(`${a.label} ${ent.label}: ${ent.note}`);
    }
    const cands = matching(SEL), sec = secondary();
    if (cands.length > 1 && sec) {
      h += `<label>${esc(sec.label)}(同じ設定の実行が ${cands.length} 本)<select data-axis="__ver">` +
        cands.map((r, i) => `<option value="${i}"${i === VER ? " selected" : ""}>${esc(r.axes[sec.key])} / ${esc(r.run_id.slice(0, 8))}</option>`).join("") + "</select></label>";
    }
    h += "</div>";
    if (notes.length) h += `<div class="bt-axnote">${notes.map(esc).join("<br>")}</div>`;
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
    if (!matching(want).length) {
      // no run has this combination: take the run that has the chosen value and keeps most of the other choices
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
    if (r) loadRun(r.run_id);
  }

  // ---- one run -----------------------------------------------------------------------------------------------
  function loadRun(id, keepRange) {
    const my = ++SEQ;
    RUN = id;
    if (!keepRange) PX.opts.range = null;
    $("bt-stats").innerHTML = "";
    busy("bt-price-note", "実行の要約を読み込み中");
    $("bt-frame").innerHTML = "";
    $("bt-chartbox").hidden = false;
    $("bt-card-note").innerHTML = "";
    $("bt-banner").hidden = true;
    getJSON("/api/backtest/summary/" + encodeURIComponent(id) + (PX.opts.range ? "?range=" + encodeURIComponent(PX.opts.range) : "")).then(sum => {
      if (my !== SEQ) return;
      idle("bt-price-note");
      SUM = sum;
      if (sum.preparing) {  // in the manifest, but the files are not complete: shown as 準備中 (it will appear when they are)
        $("bt-pricewrap").hidden = true; $("bt-pnl").hidden = true; $("bt-pnl-cap").hidden = true; $("bt-legend").innerHTML = ""; $("bt-frame").innerHTML = "";
        $("bt-price-note").innerHTML = `<span class="warn">${esc(sum.preparing)}。書き足しが終わると表示できる(ページを開き直してください)。</span>`;
        return;
      }
      if (sum.blocked) {
        $("bt-pricewrap").hidden = true; $("bt-pnl").hidden = true; $("bt-pnl-cap").hidden = true; $("bt-legend").innerHTML = "";
        $("bt-price-note").innerHTML = `<span class="warn">${esc(sum.blocked)}</span>`;
        return;
      }
      $("bt-pnl").hidden = false; $("bt-pnl-cap").hidden = false;
      if (sum.ranges && sum.ranges.length && sum.ranges.indexOf(PX.opts.range) < 0) PX.opts.range = sum.range;
      if (sum.pnl_derived) PX.opts.unit = "bp";
      renderStats();
      renderNotes();
      renderFrameBar();
      buildCharts();
      return fetchChart(null, null, true, my);
    }).catch(err => {
      if (my !== SEQ) return;
      idle("bt-price-note");
      $("bt-price-note").innerHTML = `<span class="warn">読み込めなかった: ${esc(err.message)}</span>`;
      banner("実行の要約", err);
    });
    if ($("bt-detail").open) openBacktestRun(id);
  }
  const isCard = id => String(id).startsWith("cards/");

  // where a card variant's numbers come from and how far they were checked (manifest row / provenance.json, as written)
  function renderCardNote() {
    const c = SUM.card, box = $("bt-card-note");
    if (!c) { box.innerHTML = ""; return; }
    const li = a => (a || []).map(t => `<li>${esc(t)}</li>`).join("") || "<li>(なし)</li>";
    const hl = c.headline || {};
    box.innerHTML = `<div class="warn" id="bt-card-bpnote">${esc(c.bp_note || "")}</div>` +
      `<div>見出しの数の出所: 勝率 = ${esc(hl.win_rate || "—")} / 最大の落ち込み = ${esc(hl.max_dd || "—")} / 取引数 = ${esc(hl.n || "—")}` +
      `${hl.research_max_dd_bp != null ? "(研究の最大の落ち込み " + num(hl.research_max_dd_bp, 1) + " bp)" : ""}</div>` +
      `<details open><summary>照合の範囲(研究のカード ${esc(c.card)} / 変種 ${esc(c.variant)})</summary>` +
      `<div>照合した項目</div><ul>${li(c.verified_items)}</ul><div class="warn">照合していない項目</div><ul>${li(c.not_verified)}</ul>` +
      `<div>表示の条件: ${esc(c.display_ok_rule || "—")}</div>` +
      `<div>取引は研究の台本を走らせ直して作った(取引数 ${num(c.n_trades_manifest)} 件${c.n_trades_cut != null && c.n_trades_cut !== c.n_trades_manifest ? "、封印の境で切って " + num(c.n_trades_cut) + " 件" : ""}、損益は bp だけで通貨の額は無い)。</div>` +
      `<div>値付けの銘柄: ${esc(c.instrument || "—")}(出所: ${esc(c.instrument_source || "—")})</div>` +
      `<details><summary>取引の定義(provenance.json)</summary><div style="white-space:pre-wrap">${esc(c.trade_definition || "—")}</div>` +
      `<div>走らせ直しのコマンド: ${esc((c.research_cmd || []).join(" ")) || "—"}</div><div>データの置き場: ${esc((c.data_dirs_read || []).join(" / ")) || "—"}</div>` +
      `<div>封印: ${esc(c.seal || "—")}</div></details></details>`;
  }

  function renderStats() {
    const s = SUM.stats, u = unitName(), d = s.total == null ? 0 : moneyDigits(SUM.currency, s.total);
    const t = (k, v, cls, sub) => `<div class="tile"><div class="k">${k}</div><div class="v mono ${cls || ""}" style="font-size:20px;white-space:normal">${v}` +
      (sub ? ` <span class="sub">${sub}</span>` : "") + "</div></div>";
    const tot = s.total == null ? s.total_bp : s.total;
    $("bt-stats").innerHTML =
      t("取引数", num(s.n)) +
      t("勝率", s.win_rate == null ? "—" : (s.win_rate * 100).toFixed(1) + "%", "", `${num(s.wins)} 勝`) +
      t(`累計損益(${s.total == null ? "bp" : u})`, s.total == null ? signed(s.total_bp, 0) : signed(s.total, d), tot > 0 ? "pos" : tot < 0 ? "neg" : "", s.total == null ? "通貨の額は記録に無い" : `${signed(s.total_bp, 0)} bp`) +
      t(`最大の落ち込み(${s.max_dd == null ? "bp" : u})`, s.max_dd == null ? num(s.max_dd_bp, 0) : num(s.max_dd, d), "", s.max_dd == null ? "" : `${num(s.max_dd_bp, 0)} bp`) +
      t("期間(UTC・終わりの日を含む)", utc(SUM.period.first_s) + " 〜 " + utc(SUM.period.last_incl_s)) +
      (SUM.card ? t("カードの変種", esc(SUM.card.variant), "", esc(SUM.card.card)) : t("実行 ID", esc(SUM.run_id.slice(0, 10)), "", "内容のハッシュ"));
  }

  function renderNotes() {
    const p = SUM.price;
    let h = "";
    if (p.available) h += `<span class="${p.same_source ? "" : "warn"}">価格: ${esc(p.note)}</span>`;
    else h += `<span class="warn">チャートは出せない: ${esc(p.reason)}。累計損益だけ出す。</span>`;
    h += ` / 価格は ${esc(SUM.seal_boundary_iso)} より前だけ(封印の境)。時刻は UTC。`;
    if (SUM.pnl_derived) h += ' <span class="warn">この実行の記録は bp だけで、通貨の額は無い。</span>';
    if (SUM.purpose === "動作確認") h += ' <span class="warn">動作確認の実行。相場の結論には使わない。</span>';
    if (!SUM.card) h += ` <a href="/backtest/run/${esc(SUM.run_id)}" target="_blank" style="color:var(--accent)">この実行の単独ページ(実行 ID ${esc(SUM.run_id)})</a>`;
    $("bt-price-note").innerHTML = h;
    renderCardNote();
  }

  // 表示の足 (the chart's bar width) is chosen apart from 測定に使った足 (the bar the run was measured on)
  function renderFrameBar() {
    const o = PX.opts, avail = SUM.price.available;
    let h = '<span class="k">表示の足</span> ';
    h += `<button data-f="auto" class="${o.frame === "auto" ? "on" : ""}"${avail ? "" : " disabled"}>自動</button>`;
    for (const f of FRAMES) h += `<button data-f="${f}" class="${o.frame === f ? "on" : ""}"${avail ? "" : " disabled"}>${FRAME_NAME[f]}</button>`;
    h += ` <span class="k" id="bt-frame-now"></span>`;
    h += ` <span class="k">${SUM.card ? "測定に使った足: 変種の説明を参照(カードは足を自分で決める。表示の足とは別)" : "測定に使った足: " + (SUM.measure_interval_s ? esc(FRAME_NAME[SUM.measure_interval_s] || (SUM.measure_interval_s / 60) + "分") : "記録なし") + "(実行の記録 data[].spec.bar.interval_s。表示の足とは別)"}</span>`;
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

  // ---- charts ------------------------------------------------------------------------------------------------
  function buildCharts() {
    const LC = window.LightweightCharts;
    if (!LC) { $("bt-price-note").innerHTML += '<br><span class="warn">チャート描画ライブラリ(/static/lightweight-charts.standalone.production.js)を読み込めなかった。</span>'; return; }
    const hasPrice = SUM.price.available;
    $("bt-pricewrap").hidden = !hasPrice;
    $("bt-pnl").classList.toggle("alone", !hasPrice);
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
      PX.pnl = LC.createChart($("bt-pnl"), Object.assign({width: $("bt-pnl").clientWidth || 900, height: 170}, common));
      PX.pnlSeries = PX.pnl.addLineSeries({color: CUM, lineWidth: 2, lineType: 1, priceLineVisible: false});
      PX.price.timeScale().subscribeVisibleLogicalRangeChange(r => { onRange(r); syncPnl(r, true); });
      PX.pnl.timeScale().subscribeVisibleLogicalRangeChange(r => syncPnl(r, false));
      new ResizeObserver(resize).observe($("bt-chartbox"));
      $("bt-pricewrap").addEventListener("mousemove", onMove);
      $("bt-pricewrap").addEventListener("mouseleave", () => { $("bt-tip").style.display = "none"; });
      loop();
    }
    resize();
    renderPanel();
    renderLegend();
  }

  function resize() {
    if (!PX.price) return;
    const w = Math.max(300, $("bt-chartbox").clientWidth - 34);
    const h = SUM && !SUM.price.available ? 300 : 170;
    PX.price.applyOptions({width: w, height: 470});
    PX.pnl.applyOptions({width: w, height: h});
    const cv = $("bt-overlay"), dpr = window.devicePixelRatio || 1;
    cv.style.width = w + "px"; cv.style.height = "470px";
    cv.width = Math.round(w * dpr); cv.height = Math.round(470 * dpr);
    PX.sig = "";
  }

  function renderPanel() {
    const panel = $("bt-panel"), o = PX.opts, u = unitName(), noMoney = !!SUM.pnl_derived;
    let h = `<label><input type="checkbox" id="bt-o-arrows"${o.arrows ? " checked" : ""}> 線と矢印</label>` +
      `<label><input type="checkbox" id="bt-o-labels"${o.labels ? " checked" : ""}> 損益の数字(${MAX_TRADES_LABEL} 件まで)</label>` +
      `<div class="grp">損益の単位 <label style="display:inline"><input type="radio" name="bt-unit" value="ccy"${o.unit === "ccy" ? " checked" : ""}${noMoney ? " disabled" : ""}> ${esc(u)}</label>` +
      ` <label style="display:inline"><input type="radio" name="bt-unit" value="bp"${o.unit === "bp" ? " checked" : ""}> bp</label></div>`;
    if (noMoney) h += '<div class="hint">この実行の記録は bp だけ(通貨の額は無い)</div>';
    if (SUM.ranges && SUM.ranges.length > 1 && SUM.ranges_identical === false) {
      h += `<div class="grp">約定の幅 <select id="bt-o-range">` + SUM.ranges.map(r => `<option${r === o.range ? " selected" : ""}>${esc(r)}</option>`).join("") + "</select></div>";
    } else if (SUM.ranges && SUM.ranges.length > 1) {
      h += `<div class="hint">約定の幅 ${esc(SUM.ranges.join(" / "))} の取引は同じ</div>`;
    }
    h += '<div class="grp"><button id="bt-o-fit">実行の期間</button> <span class="hint" id="bt-o-warn"></span></div>';
    panel.innerHTML = h;
    $("bt-o-arrows").onchange = e => { o.arrows = e.target.checked; PX.sig = ""; };
    $("bt-o-labels").onchange = e => { o.labels = e.target.checked; PX.sig = ""; };
    document.querySelectorAll('input[name="bt-unit"]').forEach(r => r.onchange = e => { o.unit = e.target.value; setPnl(); renderLegend(); PX.sig = ""; });
    const rs = $("bt-o-range");
    if (rs) rs.onchange = e => { o.range = e.target.value; loadRun(RUN, true); };  // the headline numbers follow the range too
    $("bt-o-fit").onclick = () => fetchChart(null, null, true, SEQ);
  }

  function renderLegend() {
    const u = PX.opts.unit === "bp" ? "bp" : unitName();
    const bpn = SUM && SUM.card && SUM.card.bp_note ? `<span class="warn" id="bt-bpnote">${esc(SUM.card.bp_note)}</span>` : "";
    $("bt-legend").innerHTML = bpn +
      `<span><i style="border-color:${BUY}"></i>買い</span><span><i style="border-color:${SELL}"></i>売り</span>` +
      `<span><i style="border-color:#aab"></i>実線 = 勝ち</span><span><i style="border-top-style:dashed;border-color:#aab"></i>破線 = 負け</span>` +
      `<span><i style="border-color:${CUM}"></i>累計損益(${esc(u)})</span><span>点線の縦線 = 開始・終了</span><span>ホイールで拡大・縮小、ドラッグで移動</span>`;
    $("bt-pnl-cap").textContent = `累計損益(${u}。各取引の損益の合計)`;
  }

  // time <-> logical index of the bars on screen. A bar is named by its START, an event (a trade, the run's start and
  // end) is stamped at the END of the bar it belongs to: the bar's centre is at its start + half a bar, so the shift
  // of -0.5 puts a time stamped at a bar's end on that bar's right edge (its close).
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
  // x of a logical index. The chart's own logicalToCoordinate answers oddly just outside the data (a fraction between -1
  // and 0 came back as 0), so the index is placed on the straight line through two indices the chart can answer for.
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

  // the first view is the run's period; the loaded window reaches one span to each side so the chart can be moved
  // outside the run's period (to see the long course of the price)
  function fetchChart(from, to, fit, my, keep) {
    const o = PX.opts;
    if (fit) {
      const vf = SUM.period.first_s, vt = SUM.period.last_s, span = Math.max(vt - vf, 60);
      from = vf - span; to = vt + span; keep = [vf, vt];
    }
    let url = `/api/backtest/chart/${encodeURIComponent(RUN)}?max_bars=${barsPerView() * 3}&interval=${pickInterval(Math.max((to - from) / 3, 60))}`;
    if (from != null) url += `&from=${from}&to=${to}`;
    if (o.range) url += `&range=${encodeURIComponent(o.range)}`;
    busy("bt-chart-busy", "チャートのデータを読み込み中");
    return getJSON(url).then(d => {
      if (my !== SEQ) return;
      idle("bt-chart-busy"); $("bt-chart-busy").innerHTML = "";
      applyChart(d, fit, keep);
      if (d.building) {  // the price store is being made in the background (first time only): poll, then draw the chart
        const b = d.building;
        const stage = b.stage === "reading" ? "1 分足のファイルを読んでいます" : b.stage === "folding" ? `足を作っています(足 ${b.frame}/${b.frames})` :
          b.stage === "saving" ? `キャッシュに保存しています(足 ${b.frame}/${b.frames})` :
          b.stage === "queued" ? "順番待ちです(別の銘柄を作っています)" : "開始しています";
        $("bt-chart-busy").innerHTML = `<span class="busy">価格のキャッシュを作っています(初回だけ)。銘柄 ${esc(b.label || b.market)}、${esc(stage)}、経過 ${esc(b.elapsed_s)} 秒。` +
          `累計損益と見出しの数字は先に出ています。できたら自動でチャートを出します。</span>`;
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

  function applyChart(d, fit, keep) {
    PX.data = d; PX.bars = d.bars; PX.interval = d.interval_s;
    PX.winFrom = d.from_s; PX.winTo = d.to_s; PX.loLimit = d.chart_lo_s; PX.hiLimit = d.chart_hi_s;
    PX.restoring = true;
    $("bt-pricewrap").hidden = !!d.building || !SUM.price.available;  // while the store is being made: only the profit chart (alone)
    $("bt-pnl").classList.toggle("alone", !!d.building || !SUM.price.available);
    if (!d.building && SUM.price.available) resize();
    PX.candle.setData(SUM.price.available ? d.bars.map(b => ({time: b[0], open: b[1], high: b[2], low: b[3], close: b[4]})) : []);
    setPnl();
    showFrameNow();
    const warn = $("bt-o-warn");
    if (warn) warn.textContent = d.too_many ? `この範囲に取引が ${num(d.trades_in_range)} 件ある(線は ${num(d.max_trades)} 件まで)。拡大すると出る` :
      `表示中の取引 ${num(d.trades_in_range)} 件 / 全 ${num(d.trades_total)} 件・${width(d.interval_s)}`;
    const old = $("bt-narrow"); if (old) old.remove();
    if (d.narrowed) $("bt-price-note").insertAdjacentHTML("beforeend", ` <span class="warn" id="bt-narrow">この足(${esc(width(d.interval_s))})では ${num(d.narrowed.max_bars)} 本までしか出せない(この範囲だと ${num(d.narrowed.requested_bars)} 本)ので範囲を狭めた。範囲を狭めるか、表示の足を粗くしてください。</span>`);
    if (SUM.price.available && d.bars.length) {
      let done = false;
      if (keep) {
        const kf = Math.max(keep[0], d.from_s), kt = Math.min(keep[1], d.to_s);
        if (kt > kf) {
          try { PX.price.timeScale().setVisibleLogicalRange({from: logicalOfTime(kf), to: logicalOfTime(kt)}); done = true; } catch (e) { /* outside data */ }
        }
      }
      if (!done) PX.price.timeScale().fitContent();
    } else if (!SUM.price.available || d.building) {
      PX.pnl.timeScale().fitContent();
    }
    setTimeout(() => {
      PX.restoring = false; PX.sig = "";
      const lr = SUM.price.available ? PX.price.timeScale().getVisibleLogicalRange() : null;
      if (lr) syncPnl(lr, true);
    }, 300);
  }

  // cumulative profit and loss: one point per bar on screen (so both charts share the same time axis), else the sent points
  function setPnl() {
    const d = PX.data;
    if (!d || !PX.pnlSeries) return;
    const k = PX.opts.unit === "bp" ? 2 : 1;
    const pts = d.pnl, fmtF = k === 2 ? (v => num(v, 1)) : (v => num(v, moneyDigits(SUM.currency, v)));
    PX.pnlSeries.applyOptions({priceFormat: {type: "custom", formatter: fmtF, minMove: 0.01}});
    let rows;
    if (SUM.price.available && d.bars.length) {
      rows = []; let j = 0, cur = pts.length ? pts[0][k] : 0;
      for (const b of d.bars) {
        while (j < pts.length && pts[j][0] <= b[0]) { cur = pts[j][k]; j++; }
        rows.push({time: b[0], value: cur});
      }
    } else {
      rows = pts.map(p => ({time: p[0], value: p[k]}));
    }
    PX.pnlSeries.setData(rows);
  }

  function syncPnl(r, fromPrice) {
    if (!r || PX.syncing || PX.restoring || !SUM || !SUM.price.available) return;
    PX.syncing = true;
    try { (fromPrice ? PX.pnl : PX.price).timeScale().setVisibleLogicalRange(r); } catch (e) { /* not ready */ }
    PX.syncing = false;
  }

  // zoom / pan: fetch again when the view leaves the loaded window; with 表示の足 = 自動 also when another bar width fits
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

  // ---- the trade layer ---------------------------------------------------------------------------------------
  function loop() {
    PX.raf = requestAnimationFrame(loop);
    if (!PX.price || $("view-backtest").hidden || !PX.data || !SUM || !SUM.price.available) return;
    const ts = PX.price.timeScale();
    const sig = [ts.logicalToCoordinate(0), ts.logicalToCoordinate(100), PX.candle.priceToCoordinate(1), PX.candle.priceToCoordinate(1000000),
      $("bt-overlay").width, PX.bars.length, PX.opts.arrows, PX.opts.labels, PX.opts.unit, PX.data.trades.length, PX.interval].join("|");
    if (sig === PX.sig) return;
    PX.sig = sig;
    draw();
  }

  function draw() {
    const cv = $("bt-overlay"), ctx = cv.getContext("2d"), dpr = window.devicePixelRatio || 1, d = PX.data;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    PX.segs = [];
    if (!PX.bars.length) return;
    const w = cv.width / dpr, h = cv.height / dpr;
    const plotW = w - PX.price.priceScale("right").width(), plotH = h - PX.price.timeScale().height();
    ctx.save();
    ctx.beginPath(); ctx.rect(0, 0, plotW, plotH); ctx.clip();
    // start / end lines
    const per = SUM.period;
    ctx.font = "11px system-ui, sans-serif";
    ctx.setLineDash([2, 4]); ctx.lineWidth = 1;
    [["開始", per.first_s], ["終了", per.last_s]].forEach(([name, t], k) => {
      if (t == null) return;
      const x = xOf(t);
      if (x == null || x < 0 || x > plotW) return;
      ctx.strokeStyle = "#c9d3e3"; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, plotH); ctx.stroke();
      ctx.fillStyle = "#c9d3e3"; ctx.textAlign = k === 0 ? "left" : "right";
      ctx.fillText(`${name} ${utc(t, true)}`, x + (k === 0 ? 4 : -4), plotH - 6);
    });
    ctx.setLineDash([]);
    if (PX.opts.arrows) {
      const trades = d.trades, labels = PX.opts.labels && trades.length <= MAX_TRADES_LABEL, bp = PX.opts.unit === "bp";
      for (const t of trades) {
        const x1 = xOf(t.et), x2 = xOf(t.xt), y1 = PX.candle.priceToCoordinate(t.ep), y2 = PX.candle.priceToCoordinate(t.xp);
        if (x1 == null || x2 == null || y1 == null || y2 == null) continue;
        if ((x1 < -50 && x2 < -50) || (x1 > plotW + 50 && x2 > plotW + 50)) continue;
        const col = t.side > 0 ? BUY : SELL, win = (t.pnl == null ? t.bp : t.pnl) > 0;
        ctx.strokeStyle = col; ctx.fillStyle = col; ctx.lineWidth = win ? 1.6 : 1.2;
        ctx.globalAlpha = trades.length > 600 ? 0.65 : 1;
        ctx.setLineDash(win ? [] : [4, 3]);
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
        ctx.setLineDash([]);
        ctx.beginPath(); ctx.arc(x1, y1, 2.6, 0, 6.2832); ctx.fill();
        const ang = Math.atan2(y2 - y1, x2 - x1 || 0.0001), s = 7;
        ctx.beginPath(); ctx.moveTo(x2, y2);
        ctx.lineTo(x2 - s * Math.cos(ang - 0.45), y2 - s * Math.sin(ang - 0.45));
        ctx.lineTo(x2 - s * Math.cos(ang + 0.45), y2 - s * Math.sin(ang + 0.45));
        ctx.closePath(); ctx.fill();
        ctx.globalAlpha = 1;
        if (labels) {
          ctx.fillStyle = win ? WIN : LOSE; ctx.textAlign = "left";
          ctx.fillText(bp ? signed(t.bp, 1) + "bp" : signed(t.pnl, moneyDigits(SUM.currency, t.pnl)), x2 + 5, y2 - 4);
        }
        PX.segs.push({x1, y1, x2, y2, t});
      }
    }
    ctx.restore();
  }

  function onMove(ev) {
    const tip = $("bt-tip");
    if (!PX.opts.arrows || !PX.segs.length) { tip.style.display = "none"; return; }
    const r = $("bt-pricewrap").getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top;
    let best = null, bd = 6;
    for (const s of PX.segs) {
      const dx = s.x2 - s.x1, dy = s.y2 - s.y1, L = dx * dx + dy * dy;
      let u = L ? ((mx - s.x1) * dx + (my - s.y1) * dy) / L : 0;
      u = Math.max(0, Math.min(1, u));
      const dist = Math.hypot(mx - (s.x1 + u * dx), my - (s.y1 + u * dy));
      if (dist < bd) { bd = dist; best = s; }
    }
    if (!best) { tip.style.display = "none"; return; }
    const t = best.t, u = unitName();
    tip.textContent = `${t.side > 0 ? "買い" : "売り"}  ${t.pnl > 0 ? "勝ち" : t.pnl < 0 ? "負け" : "±0"}\n` +
      `建て ${utc(t.et, true)}  ${num(t.ep, 2)}\n決済 ${utc(t.xt, true)}  ${num(t.xp, 2)}\n` +
      `損益 ${signed(t.pnl, moneyDigits(SUM.currency, t.pnl))} ${u} / ${signed(t.bp, 1)} bp\n${SUM.card && SUM.card.bp_note ? "※" + SUM.card.bp_note + "\n" : ""}決済理由 ${t.reason == null ? "—" : t.reason}`;
    tip.style.display = "block";
    tip.style.left = Math.min(mx + 14, r.width - 260) + "px"; tip.style.top = Math.min(my + 14, r.height - 100) + "px";
  }

  // ---- the ten detail tabs (the server renders them; backtest_view.py) ---------------------------------------
  window.openBacktestRun = function (id) {
    detailRun = id;
    if (isCard(id)) {  // a card variant has no run record: the ten detail tabs do not exist for it
      btView = null;
      $("bt-title").textContent = "研究のカードの変種には、この 10 個の詳細タブが無い(上の「照合の範囲」を見てください)";
      $("bt-tabs").innerHTML = ""; $("bt-body").innerHTML = "";
      return Promise.resolve();
    }
    return fetch("/api/backtest/run/" + encodeURIComponent(id)).then(r => r.json()).then(v => {
      if (detailRun !== id) return;
      btView = v;
      $("bt-title").innerHTML = `実行 <span class="mono">${esc(v.run_id)}</span>(目的: ${esc(v.purpose)})`;
      $("bt-tabs").innerHTML = v.tabs.map((t, i) => `<button id="bt-tab-${i}" onclick="showBacktestTab(${i})">${esc(t.label)}</button>`).join("");
      window.showBacktestTab(0);
    });
  };
  window.showBacktestTab = function (i) {
    if (!btView) return;
    btView.tabs.forEach((t, k) => { const b = $("bt-tab-" + k); if (b) b.className = (k === i) ? "on" : ""; });
    $("bt-body").innerHTML = btView.tabs[i].html;
  };

  // ---- start -------------------------------------------------------------------------------------------------
  window.btInit = function () {
    if (CAT) { resize(); PX.sig = ""; return Promise.resolve(); }
    $("bt-detail").addEventListener("toggle", () => { if ($("bt-detail").open && RUN && detailRun !== RUN) openBacktestRun(RUN); });
    busy("bt-tree", "テーマの一覧を読み込み中");
    return getJSON("/api/backtest/catalog").then(c => {
      idle("bt-tree");
      CAT = c;
      renderTree();
      const first = allStrategies()[0];
      if (first) selectStrategy(first.id);
      else $("bt-head").innerHTML = '<span class="empty">実行がまだ無い</span>';
    }).catch(err => { idle("bt-tree"); $("bt-tree").innerHTML = `<span class="empty">読み込めなかった: ${esc(err.message)}</span>`; banner("テーマの一覧", err); });
  };
})();
