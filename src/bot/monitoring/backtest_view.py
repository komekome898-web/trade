"""The dashboard's バックテスト tab (item 3, old item 10: 「実行の一覧 → 実行ごとの項目別タブ:
概要 / 前提(約定・遅延・費用・データ)/ 損益 / 取引 / 約定の質 / 費用 / 分布 / 検証 / 再現性 /
データ品質。日本語。CDN を使わない。…目的が `動作確認` の実行は全タブに「動作確認の実行。
相場の結論には使わない」を出す」).

Reads only the run directories that bot.bt.repro wrote (`<runs_dir>/<run_id>/`
with record.json, repro.json and the exports) and renders them on the
server: every tab's HTML and its plain text are made here, so what the page
shows is what the API serves (no chart library, no external URL).

    list_runs(runs_dir)          -> [{run_id, purpose, instrument, setup, trades, ...}]
    run_view(runs_dir, run_id)   -> {run_id, purpose, warning, tabs: [{label, text, html}], values}
    run_page(view)               -> a complete HTML page of one run (no script)
"""
from __future__ import annotations

import html
import json
import os
import re
from typing import Any, Optional

TABS = ("概要", "前提", "損益", "取引", "約定の質", "費用", "分布", "検証", "再現性", "データ品質")
SMOKE = "動作確認"
WARNING = "動作確認の実行。相場の結論には使わない"
_RUN_ID = re.compile(r"^[0-9a-f]{64}$")


class BacktestViewError(ValueError):
    pass


def _load(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _run_dir(runs_dir: str, run_id: str) -> str:
    if type(run_id) is not str or not _RUN_ID.match(run_id):
        raise BacktestViewError(f"not a run id: {run_id!r}")
    d = os.path.join(runs_dir, run_id)
    if not (os.path.isfile(os.path.join(d, "record.json")) and os.path.isfile(os.path.join(d, "repro.json"))):
        raise BacktestViewError(f"no finished run {run_id}")
    return d


def list_runs(runs_dir: str) -> list[dict]:
    out = []
    if not os.path.isdir(runs_dir):
        return out
    for name in sorted(os.listdir(runs_dir)):
        try:
            d = _run_dir(runs_dir, name)
        except BacktestViewError:
            continue
        rec = _load(os.path.join(d, "record.json"))
        n = None
        mp = os.path.join(d, "metrics.json")
        if os.path.isfile(mp):
            n = _load(mp)["data"]["trades"].get("n")
        out.append({"run_id": name, "purpose": rec.get("purpose"), "instrument": (rec.get("config") or {}).get("instrument"),
                    "setup": (rec.get("setup") or {}).get("name"), "seed": rec.get("seed"), "trades": n,
                    "git_sha": rec.get("git_sha")})
    return out


def _esc(x: Any) -> str:
    return html.escape("—" if x is None else str(x))


def _num(x: Any, d: int = 6) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{d}g}"
    return str(x)


def _table(rows: list[tuple], head: Optional[tuple] = None) -> str:
    h = "".join(f"<th>{_esc(c)}</th>" for c in head) if head else ""
    body = "".join("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table>{'<tr>' + h + '</tr>' if h else ''}{body}</table>"


def _kv(pairs: list[tuple[str, Any]]) -> tuple[str, str]:
    return _table([(k, v) for k, v in pairs]), "\n".join(f"{k}: {v}" for k, v in pairs)


def _export(d: str, kind: str) -> Optional[Any]:
    p = os.path.join(d, f"{kind}.json")
    return _load(p)["data"] if os.path.isfile(p) else None


def run_view(runs_dir: str, run_id: str) -> dict:
    d = _run_dir(runs_dir, run_id)
    rec = _load(os.path.join(d, "record.json"))
    repro = _load(os.path.join(d, "repro.json"))
    m = _export(d, "metrics") or {}
    trades = _export(d, "trades") or []
    fills = _export(d, "fills") or []
    quality = _export(d, "data_quality") or {}
    validation = _export(d, "validation")
    cfg = rec.get("config") or {}
    tr = m.get("trades") or {}
    tabs: dict[str, tuple[str, str]] = {}

    tabs["概要"] = _kv([("実行 ID", run_id), ("目的", rec.get("purpose")), ("商品", cfg.get("instrument")),
                       ("手順", (rec.get("setup") or {}).get("name")), ("種", rec.get("seed")),
                       ("往復の数", tr.get("n")), ("実現損益(円)", _num((m.get("pnl_jpy") or {}).get("realized"))),
                       ("1 件ごとの bp の平均", _num(tr.get("mean_bp")))])
    data_rows = [(x.get("path"), (rec.get("data_sha256") or {}).get(x.get("path"))) for x in rec.get("data") or []]
    h1, t1 = _kv([("約定の模型", json.dumps(cfg.get("fill"), ensure_ascii=False)),
                  ("遅延(ns)", json.dumps(cfg.get("latency_ns"), ensure_ascii=False)),
                  ("費用", json.dumps(cfg.get("costs"), ensure_ascii=False)),
                  ("核の部品", json.dumps((rec.get("components") or {}).get("models"), ensure_ascii=False)),
                  ("注記", json.dumps((rec.get("components") or {}).get("notes"), ensure_ascii=False))])
    tabs["前提"] = (h1 + "<h3>データ</h3>" + _table(data_rows, ("ファイル", "sha256")),
                   t1 + "\nデータ: " + "; ".join(f"{p} {s}" for p, s in data_rows))
    dd = m.get("drawdown") or {}
    tabs["損益"] = _kv([("実現損益(円)", _num((m.get("pnl_jpy") or {}).get("realized"))),
                       ("手数料の合計(円)", _num((m.get("pnl_jpy") or {}).get("fees"))),
                       ("最大ドローダウン(円)", _num(dd.get("max_dd_abs"))),
                       ("最大ドローダウン(率)", _num(dd.get("max_dd_pct"))), ("率の注記", dd.get("pct_note"))])
    trows = [(t.get("id"), t.get("side"), _num(t.get("qty")), _num(t.get("entry_px")), _num(t.get("exit_px")),
              _num(t.get("pnl")), t.get("reason")) for t in trades]
    head = ("往復", "向き", "数量", "入り", "出", "損益(円)", "決済理由")
    tabs["取引"] = (_table(trows, head), f"往復 {len(trows)} 件\n" + "\n".join(" ".join(map(str, r)) for r in trows))
    fm = m.get("fills") or {}
    mo = m.get("markout") or {}
    h2, t2 = _kv([("注文", fm.get("orders")), ("約定率", _num(fm.get("fill_rate"))), ("取り逃し", fm.get("missed")),
                  ("一部約定", fm.get("partial")), ("数量の約定率", _num(fm.get("qty_fill_rate"))),
                  ("markout の基準", mo.get("reference")), ("markout の単位", mo.get("unit"))])
    mrows = [(h, ", ".join(_num(v) for v in vals)) for h, vals in (mo.get("values") or {}).items()]
    tabs["約定の質"] = (h2 + _table(mrows, ("時間窓(秒)", "約定ごとの markout")),
                      t2 + "\n" + "\n".join(f"markout {h} 秒: {v}" for h, v in mrows))
    c = m.get("costs") or {}
    tabs["費用"] = _kv([("maker 手数料(円)", _num(c.get("maker_fee"))), ("taker 手数料(円)", _num(c.get("taker_fee"))),
                       ("スプレッド(円)", _num(c.get("spread"))), ("スプレッドの注記", c.get("spread_note")),
                       ("資金調達(円)", _num(c.get("funding"))), ("資金調達の注記", c.get("funding_note"))])
    q = tr.get("quantiles") or {}
    bps = tr.get("per_trade_bp") or []
    h3, t3 = _kv([("件数", tr.get("n")), ("負の割合", _num(tr.get("neg_frac"))), ("分位の流儀", tr.get("quantile_method")),
                  ("建玉の時間の合計(時)", _num(tr.get("trade_hours"))), ("bp/時", _num(tr.get("bp_per_hour")))])
    tabs["分布"] = (h3 + _table([(p, _num(v)) for p, v in q.items()], ("分位", "bp"))
                   + "<h3>1 件ごとの bp</h3><p>" + _esc(", ".join(_num(b) for b in bps)) + "</p>",
                   t3 + "\n分位: " + ", ".join(f"{p}={_num(v)}" for p, v in q.items())
                   + "\n1 件ごとの bp: " + ", ".join(_num(b) for b in bps))
    if validation is None:
        msg = "この実行に検証の結果は付いていない(bot.bt.validation の結果を実行の validation に渡すと、ここに出る)"
        tabs["検証"] = (f"<p>{_esc(msg)}</p>", msg)
    else:
        txt = json.dumps(validation, ensure_ascii=False, indent=1, sort_keys=True)
        tabs["検証"] = (f"<pre>{_esc(txt)}</pre>", "検証の結果\n" + txt)
    h4, t4 = _kv([("実行 ID(内容のハッシュ)", run_id), ("git の SHA", rec.get("git_sha")),
                  ("差分のハッシュ", rec.get("diff_hash")), ("種", rec.get("seed")), ("版", rec.get("version")),
                  ("事前登録の sha256", rec.get("prereg_sha256")),
                  ("自動の再現の確認", f"{repro.get('runs')} 回の実行で{'一致' if repro.get('identical') else '不一致'}")])
    frows = sorted((repro.get("sha256") or {}).items())
    tabs["再現性"] = (h4 + _table(frows, ("出力のファイル", "sha256")), t4 + "\n" + "\n".join(f"{a} {b}" for a, b in frows))
    man = quality.get("manifest") or {}
    qrows = [(f.get("given"), f.get("rows_read"), f.get("rows_kept"), f.get("sealed_unit"), f.get("sha256"))
             for f in man.get("files") or []]
    arows = [(n, len(v)) for n, v in (quality.get("anomalies") or {}).items()]
    crows = [(n, ", ".join(v) if v else "(走った検査なし)") for n, v in (quality.get("checks") or {}).items()]
    tabs["データ品質"] = (_table(qrows, ("ファイル", "読んだ行", "残した行", "封印の単位", "sha256"))
                       + _table(arows, ("データセット", "異常の件数")) + _table(crows, ("データセット", "走った検査")),
                       "ファイル: " + "; ".join(f"{r[0]} 読 {r[1]} 残 {r[2]}" for r in qrows)
                       + "\n異常: " + "; ".join(f"{a} {b} 件" for a, b in arows)
                       + "\n検査: " + "; ".join(f"{a}: {b}" for a, b in crows))

    smoke = rec.get("purpose") == SMOKE
    out_tabs = []
    for label in TABS:
        body_html, body_text = tabs[label]
        if smoke:
            body_html = f'<p class="bt-warn">{_esc(WARNING)}</p>' + body_html
            body_text = WARNING + "\n" + body_text
        out_tabs.append({"label": label, "text": body_text, "html": body_html})
    return {"run_id": run_id, "purpose": rec.get("purpose"), "warning": WARNING if smoke else None,
            "tabs": out_tabs, "values": {"per_trade_bp": bps, "neg_frac": tr.get("neg_frac")}}


PAGE_STYLE = ("body{font-family:system-ui,sans-serif;margin:16px;background:#fff;color:#111}"
              "table{border-collapse:collapse;margin:8px 0}td,th{border:1px solid #ccc;padding:2px 6px}"
              ".bt-warn{background:#fff3cd;border:1px solid #d39e00;padding:6px}section{margin:12px 0}")


def run_page(view: dict) -> str:
    """One run as a complete page: every tab as a section, no script."""
    secs = "".join(f'<section data-tab="{_esc(t["label"])}"><h2>{_esc(t["label"])}</h2>{t["html"]}</section>'
                   for t in view["tabs"])
    return (f'<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>バックテスト {_esc(view["run_id"][:12])}'
            f'</title><style>{PAGE_STYLE}</style></head><body><h1>バックテスト 実行 {_esc(view["run_id"])}</h1>'
            f'<p><a href="/">一覧に戻る</a></p>{secs}</body></html>')
