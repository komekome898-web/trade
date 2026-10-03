"""カツオ(カード 2)の指値の再現の「参照」(weak_f<足>_close_a)と、段階 G・K1 第 17 部の年ごとの値を並べる(読むだけ)。

    PYTHONPATH=src python3 scripts/w4_measure/c2_k1_year_compare.py
    → docs/RESEARCH/cards/c2_owner_xvenue_wick/limit_sim/runs/READ_K1YEAR/TABLES.md

リードの持ち越し(limit_sim/runs/READ/RESULTS.md §0・§3 の 5「参照と K1・段階 G の差を年ごとに並べる」)。
走らせ(バックテスト)は回さない。既存の出力のファイルだけを読む。ネットワークは使わない。評価・判定はしない。

読むもの(すべて既存の出力):
  参照   docs/RESEARCH/cards/c2_owner_xvenue_wick/limit_sim/runs/weak_f{5,15,30,60}_close_a/
         summary.json(years[年].trades・sum_bp。年 = 出の時刻の暦年)・trades.json.gz(建ての年で数え直す)・
         run_record.json(区切りごとの参照の行・足の数)
  段階 G docs/PHASE2/K1/NEWENV_G/cells.json(per_year の n・total_bp)・runs_index.json、
         backtest_runs_shared/k1_newenv_g/<run_id>/trades.json.gz(数え直しの照合と 2021-05 の行)、
         backtest_data/k1_newenv_g_20261001/FOLD_MANIFEST.json(読んだ行の数だけ)
  K1     results/PHASE2/K1/xvenue/effect_binance_to_bitflyer.json(cells["<足>|s19/b24|weak"].per_year の n・mean_bp、
         alignment.per_year)
封印: 年は 2017〜2023 だけを読む(range(2017, 2024) の鍵だけを引く)。K1 の出力は 2026-08-31 までの 1 本の実行なので、
それより後の年の鍵・升全体の n・平均・区間・決済理由の件数は引かない(決済理由は種類の名前だけ)。
"""
from __future__ import annotations

import gzip
import json
import math
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from bot.research.katsuo_limit_sim import K1_BIG_BP, K1_SMALL_BP  # noqa: E402  門の値(読むだけ)

NS = 1_000_000_000
FEET = (5, 15, 30, 60)
YEARS = tuple(range(2017, 2024))  # 封印の境より前の年だけ
GATE = "s19/b24"
CARD = "docs/RESEARCH/cards/c2_owner_xvenue_wick"
REF_DIR = CARD + "/limit_sim/runs/weak_f{foot}_close_a"
G_DIR = "docs/PHASE2/K1/NEWENV_G"
G_RUNS = "backtest_runs_shared/k1_newenv_g"
G_RUNS_CLOSE = "backtest_runs_shared/k1_newenv_g_close"
G_FOLD = "backtest_data/k1_newenv_g_20261001/FOLD_MANIFEST.json"
K1_JSON = "results/PHASE2/K1/xvenue/effect_binance_to_bitflyer.json"
OUT = CARD + "/limit_sim/runs/READ_K1YEAR/TABLES.md"


def rd(path: str):
    p = os.path.join(ROOT, path)
    if path.endswith(".gz"):
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def yr(ns: int) -> int:
    return datetime.fromtimestamp(ns / NS, tz=timezone.utc).year


def ym(ns: int) -> str:
    return datetime.fromtimestamp(ns / NS, tz=timezone.utc).strftime("%Y-%m")


def iso(ns: int) -> str:
    return datetime.fromtimestamp(ns / NS, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fn(x) -> str:
    return "—" if x is None else f"{x:,}"


def fb(x) -> str:
    return "—" if x is None else f"{x:+,.2f}"


def sub(a, b):
    return None if a is None or b is None else a - b


# ---------------------------------------------------------------- 参照
def ref_load(foot: int) -> dict:
    d = REF_DIR.format(foot=foot)
    s = rd(d + "/summary.json")
    p = s["params"]
    want = {"design": "k1", "entry": "a", "fill": "close", "side_keep": "weak", "vol_gate": False, "series": "a",
            "foot_min": foot}
    bad = {k: (p.get(k), v) for k, v in want.items() if p.get(k) != v}
    if bad:
        raise SystemExit(f"止める: {d}/summary.json の params が想定と違う {bad}")
    t = rd(d + "/trades.json.gz")
    fns = foot * 60 * NS
    n = len(t["pnl_bp"])
    entry_year: dict = {}
    entry_month: dict = {}
    off_grid = 0
    for i in range(n):
        e = t["entry_t_ns"][i]
        if e % fns != 0:
            off_grid += 1
        y = yr(e - fns)  # 段階 G の stats と同じ: 建てた約定の時刻 − 足の長さ = 建てた足の始まり
        entry_year.setdefault(y, []).append(t["pnl_bp"][i])
        entry_month.setdefault(ym(e - fns), []).append(t["pnl_bp"][i])
    exit_year = {}
    for y in YEARS:
        v = s["years"].get(str(y))
        exit_year[y] = None if v is None else (v["trades"], v["sum_bp"], v.get("exit_reasons", {}))
    rr = rd(d + "/run_record.json")
    return {"summary": s, "params": p, "period": s["period"], "n": n, "off_grid": off_grid,
            "entry_year": {y: (len(v), math.fsum(v)) for y, v in entry_year.items()},
            "entry_month": {m: (len(v), math.fsum(v)) for m, v in entry_month.items()},
            "exit_year": exit_year, "all": (s["all"]["trades"], s["all"]["sum_bp"]),
            "first_entry": min(t["entry_t_ns"]) if n else None, "chunks": rr["chunks"],
            "ref_files": rr["inputs"]["references"]}


# ---------------------------------------------------------------- 段階 G
def g_trades_by(run_id: str, foot: int):
    tr = rd(f"{G_RUNS}/{run_id}/trades.json.gz")["data"]
    fns = foot * 60 * NS
    by_y, by_m = {}, {}
    for x in tr:
        sig = 1 if x["side"] == "buy" else -1
        r = sig * (x["exit_px"] / x["entry_px"] - 1.0) * 1e4
        st = x["entry_t_ns"] - fns
        by_y.setdefault(yr(st), []).append(r)
        by_m.setdefault(ym(st), []).append(r)
    first = min(x["entry_t_ns"] for x in tr) if tr else None
    reasons = sorted({x["reason"] for x in tr})
    return ({y: (len(v), math.fsum(v)) for y, v in by_y.items()},
            {m: (len(v), math.fsum(v)) for m, v in by_m.items()}, first, reasons)


def g_load(cells: dict, idx: dict, foot: int) -> dict:
    """段階 G の升。5・15 分は design|full、30・60 分は design|full が無いので design|2022_20231217。"""
    full = f"design|full|{foot}|{GATE}|weak"
    alt = f"design|2022_20231217|{foot}|{GATE}|weak"
    key = full if full in cells else (alt if alt in cells else None)
    if key is None:
        return {"key": None}
    c = cells[key]
    per = {}
    for y in YEARS:
        v = c["per_year"].get(str(y))
        per[y] = None if v is None else (v["n"], v["total_bp"])
    rid = c["run_id"]
    by_y, by_m, first, reasons = g_trades_by(rid, foot)
    return {"key": key, "range": idx[key]["range"], "run_id": rid, "per_year": per, "recount": by_y,
            "month": by_m, "first_entry": first, "reasons_trades": reasons,
            "reasons_cells": sorted(c.get("exit_reasons", {}).keys())}


# ---------------------------------------------------------------- K1
def k1_load(k1: dict, foot: int) -> dict:
    key = f"{foot}|{GATE}|weak"
    c = k1["cells"].get(key)
    if c is None:
        return {"key": key, "per_year": {y: None for y in YEARS}, "missing": True}
    per = {}
    for y in YEARS:
        v = (c.get("per_year") or {}).get(str(y))
        # 総損益 = 年別 n × 年別平均(RESULT.md 11.7、XVENUE_TABLES.md と同じ作り)。mean_bp は小数 3 桁に丸めた値
        per[y] = None if v is None else (v["n"], v["n"] * v["mean_bp"], v["mean_bp"])
    # K1 の 2023 は 12-31 までの分(封印の境 2023-12-18 の後)を含むので出さない(関門 ② の 1 回目の聞く 1。
    # 段階 G との差が封印の後の約 2 週間を差し引きで取り出す形になるため)。
    per[2023] = None
    return {"key": key, "per_year": per, "missing": False, "reasons": sorted((c.get("exit_reasons") or {}).keys())}


# ---------------------------------------------------------------- 書き出し
def mark(y: int, foot: int, g: dict) -> str:
    m = []
    if y == 2017:
        m.append("読み始めが違う(§1 の「期間」の行)")
    if y == 2023:
        m.append("比べられない(2023 は区間が違う: 参照 〜12-17 15:00Z・段階 G 〜12-18 00:00Z。K1 は 12-31 までの分を含むので出さない)")
    if g.get("key", "") and "2022_20231217" in g["key"] and y >= 2022:
        m.append("段階 G は 2022-01-01 から読み始めた別の実行")
    return "。".join(m)


def main() -> int:
    cells = rd(G_DIR + "/cells.json")
    idx = rd(G_DIR + "/runs_index.json")
    k1 = rd(K1_JSON)
    fold = rd(G_FOLD)
    L = []
    w = L.append
    w("# カツオの指値の再現の「参照」と段階 G・K1 第 17 部の年ごとの値(台本の出力)")
    w("")
    w("生成: `PYTHONPATH=src python3 scripts/w4_measure/c2_k1_year_compare.py`(読むだけ。走らせは回していない。"
      "ネットワークなし)。この文書の数はすべて台本が出した。評価・判定はしない。")
    w("")
    w("リードの持ち越し: `limit_sim/runs/READ/RESULTS.md` §0「参照の形の数字が K1・段階 G とどれだけ違うかを年ごとの"
      "合計で並べる」、§3 の 5「参照と K1・段階 G の差を年ごとに並べる」。食い違いの例は "
      "`docs/AUDITOR/VERDICTS/2026-10-03_c2_limit_sim_critic.md` の 2(2021-05 の 15 分)。")
    w("")
    w("## 0. 読んだもの・言葉の決め")
    w("")
    w("| 列 | 出所 | 年の数え方 | 損益の和 |")
    w("|---|---|---|---|")
    w(f"| 参照(出の年) | `{REF_DIR.format(foot='<足>')}/summary.json` の `years[年].trades`・`sum_bp` | "
      "出の時刻の暦年(UTC。`scripts/w4_measure/c2_limit_run.py` の説明「年 = 取引は出の時刻の暦年」) | 保存された和 |")
    w(f"| 参照(建ての年) | 同じ置き場の `trades.json.gz`(`pnl_bp` は小数 4 桁に丸めて保存) | "
      "建てた足の始まりの暦年 = `entry_t_ns − 足の長さ`(段階 G の `scripts/k1_newenv_g_tables.py: stats` と同じ式) | "
      "台本が `pnl_bp` を足した |")
    w(f"| 段階 G | `{G_DIR}/cells.json` の `per_year[年].n`・`total_bp`(升は §2 の各足の見出しの下) | 建てた足の始まりの暦年(同上) | 保存された和 |")
    w(f"| K1 第 17 部 | `{K1_JSON}` の `cells[\"<足>|{GATE}|weak\"].per_year[年].n`・`mean_bp` | "
      "建てた足の年(`docs/PHASE2/K1/NEWENV_G/INTENT_MAP.md` X-15、`scripts/measure_katsuo_xvenue.py: summarize_cell`) | "
      "**n × mean_bp を台本が計算**(K1 の出力に和は無い。mean_bp は小数 3 桁に丸めてあるので、"
      "誤差は最大 n × 0.0005 bp。`XVENUE_TABLES.md` の総損益も同じ作り) |")
    w("")
    w("差の向き(全部の表で同じ): **「参照 − 段階 G」「参照 − K1」「段階 G − K1」**。参照は建ての年の列を使う"
      "(段階 G・K1 と年の数え方を揃えるため)。出の年の列は summary.json の値をそのまま並べるだけで、差には使わない。")
    w("")
    w("封印: 年は 2017〜2023 だけを読んだ。K1 の出力は 2026-08-31 までの 1 本の実行で、2024 年以降の鍵と、升全体の"
      "n・平均・区間・決済理由の件数(2024 年以降を含む)は読んでいない。")
    w("")

    refs = {f: ref_load(f) for f in FEET}
    gs = {f: g_load(cells, idx, f) for f in FEET}
    k1s = {f: k1_load(k1, f) for f in FEET}

    # ---------------- 表 1: 設計の要素
    w("## 1. 3 つの設計の要素")
    w("")
    w("「同じ / 違う」は要素ごとに、右の出所に書いてある規則が同じかどうかの事実だけ。")
    w("")
    p5 = refs[5]["params"]
    w("| 要素 | 参照(weak_f<足>_close_a) | 段階 G | K1 第 17 部 | 同じ / 違う |")
    w("|---|---|---|---|---|")
    w(f"| 合図の取引所 | series `{p5['series']}` = {p5['series_desc']}(summary.json `params`) | Binance BTCUSDT 現物"
      f"(`{G_FOLD}` の入力、TABLES.md の冒頭) | `signal_source` = `{k1['signal_source']}`(`{K1_JSON}`) | 同じ |")
    w(f"| 約定の取引所 | bitFlyer FX_BTC_JPY の 1 分足(`scripts/w4_measure/common.py` FX_DIR) | bitFlyer FX_BTC_JPY"
      f" | `price_source` = `{k1['price_source']}` | 同じ |")
    w("| データのファイル(2017〜2023) | `backtest_data/binance_BTCUSDT_1m_20170801_20231231/`・"
      "`backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/`(common.py BIN_DIR・FX_DIR) | 同じ 2 つの置き場の写し"
      "(FOLD_MANIFEST.json の `path`・`copy_of.source`) | 同じ 2 つの置き場(`scripts/k1_source.py` 63・69 行)。"
      "2024 年以降は別のファイルも読む | 同じ(2017〜2023) |")
    w("| 足 | " + "・".join(str(f) for f in FEET) + " 分(各 summary.json `params.foot_min`) | 5・15 分は 2017-08-17〜の 1 本の実行"
      "(`design|full`)。30・60 分は 2022-01-01〜の実行だけ(§4) | `family.feet` = "
      + "・".join(str(x) for x in k1["family"]["feet"]) + " 分 | 30・60 分の 2017〜2021 は段階 G に無い |")
    w(f"| 門 | 小門 {K1_SMALL_BP:g}・大門 {K1_BIG_BP:g} bp(`src/bot/research/katsuo_limit_sim.py` の K1_SMALL_BP・"
      f"K1_BIG_BP。説明に「門 s19/b24」) | `{GATE}`(cells.json の升の名前) | `{GATE}` の升(`family.gates` の 1 つ) | 同じ |")
    w(f"| 強さ | `side_keep` = `{p5['side_keep']}`(弱いだけ) | weak(INTENT_MAP X-5) | 升 `…|weak` | 同じ |")
    w(f"| H1(実体 ≥ ヒゲ は実体を逆張り) | design `{p5['design']}` の k1_signal(flip_body。katsuo_limit_sim.py の説明) | "
      f"X-2 ○ | `flip_body` = {k1['flip_body']} | 同じ |")
    w(f"| H2a(先端の無効化なし、反対の合図で降りる) | 無効化の枝を通らない(katsuo_limit_sim.py の説明) | X-3 ○ | "
      f"`use_invalid` = {k1['use_invalid']} | 同じ |")
    w(f"| H3(行動を 1 本遅らせる) | entry `{p5['entry']}` = 次に閉じた足の区切りで行動(katsuo_limit_sim.py の説明"
      "「入り方 a はすべて K1 の H3 と同じ」) | X-4 ○ | `delay_entry` = " + str(k1["delay_entry"]) + " | 同じ |")
    w("| 反対の弱い合図 | 閉じるだけ(ドテンしない。katsuo_limit_sim.py の説明「keep=\"weak\" では 207 行が通らない」) | "
      "X-3「弱い = 決済のみ」 | measure_katsuo_effect.py simulate(強いときだけドテン) | 同じ |")
    w(f"| 相場の門 | `vol_gate` = {p5['vol_gate']}(門なし) | なし | なし | 同じ |")
    w(f"| 約定の形 | `fill` = `{p5['fill']}`: 行動の時刻の直前の bitFlyer の 1 分足の終値(出来高 > 0 の足だけ。"
      "katsuo_limit_sim.py 371 行) | 次の足(結合・畳み後の bitFlyer の足)の終値(X-9) | 次の足の終値(XVENUE_PREREG.md §1、"
      "RESULT.md 第 17 部) | 足の終値という形は同じ。足の作り方が違う(次の行) |")
    w("| 合図の足の作り方 | Binance の 1 分足を全部、UTC の時計の区切りで畳む(`_advance`)。bitFlyer に分足が無い分も"
      "合図の足に入る | UTC の分の内部結合の後に両取引所を同じ窓で畳む(X-6・X-8) | 同じ(内部結合。XVENUE_PREREG.md §2) | "
      "**違う**(批評家の 2 の (b)) |")
    w("| Binance の約定の無い分(`n_trades == 0`) | 落とさない(`load_reference` は時刻・範囲・値の数の形だけを見る。"
      "§5 で 2018〜2022 の行の数が FOLD_MANIFEST の `rows_kept_in_range` と同じ) | 落とす(X-7、`synthetic` → drop) | 落とす"
      "(`load.signal.dropped_n_trades_0`) | **違う** |")
    w("| bitFlyer の約定の無い分 | `no_trade`(4 本値が空)を落とし(common.py BAR_RESOLVE)、さらに出来高 ≤ 0 の足を飛ばす"
      "(katsuo_limit_sim.py 371 行) | 4 本値が空の行を落とす(X-7) | 4 本値が空の行を落とす(`load.price.dropped_null_ohlc`) | "
      "出来高 0 で 4 本値がある足の扱いが違うかは未確認 |")
    r5, g5 = refs[5], gs[5]
    w(f"| 期間 | {refs[5]['period'][0]}〜{refs[5]['period'][1]}(summary.json `period`。4 つの足で同じ) | "
      f"5・15 分 `design|full`: 2017-08-17〜2023-12-18T00:00Z(TABLES.md・FOLD_MANIFEST.json `cut`)。"
      f"最初の取引の建て: 5 分 {iso(gs[5]['first_entry'])}・15 分 {iso(gs[15]['first_entry'])} | "
      f"`explore` = {k1['explore'][0]}〜(2023 年の後も続く 1 本の実行) | **違う**(2017 の読み始め・2023 の終わり) |")
    ref_end = {f: sorted(set().union(*[set((refs[f]['exit_year'][y] or (0, 0, {}))[2].keys()) for y in YEARS]))
               for f in FEET}
    w(f"| 期間の終わりの持ち高 | 最後の終値で閉じる(`finish`、終わり方「期間の終わり」)。summary.json の終わり方の種類: "
      + "; ".join(f"{f} 分 {ref_end[f]}" for f in FEET)
      + f" | 閉じない(決済理由の種類: " + "; ".join(f"{f} 分 {gs[f]['reasons_cells']}" for f in FEET)
      + ") | 閉じない(measure_katsuo_effect.py simulate は close() でだけ取引を足す。決済理由の種類: "
      + "; ".join(f"{f} 分 {k1s[f].get('reasons')}" for f in FEET) + ") | **違う**(取引 1 本の差になりうる) |")
    w("| 経費・建玉 | 経費なし、1 単位 | 費用 0 / 0、1 単位(X-14) | 経費前、1 単位 | 同じ |")
    w("| 年の数え方 | summary.json は出の年。この文書の「参照(建ての年)」は建てた足の始まりの年 | 建てた足の始まりの年(X-15) | "
      "建てた足の年 | summary.json の年だけが違う |")
    w("")

    # ---------------- 表 2: 年ごと
    w("## 2. 足 × 年の取引の数と損益の和(bp)")
    w("")
    w("「—」= その升に値が無い(§4)。差は §0 の向き。")
    w("")
    for f in FEET:
        R, G, K = refs[f], gs[f], k1s[f]
        w(f"### {f} 分")
        w("")
        w(f"段階 G の升: `{G['key']}`(run_id `{G['run_id'][:12]}…`)。K1 の升: `{K['key']}`。")
        w("")
        w("取引の数")
        w("")
        w("| 年 | 参照(出の年) | 参照(建ての年) | 段階 G | K1 | 参照 − 段階 G | 参照 − K1 | 段階 G − K1 | 印 |")
        w("|---|---|---|---|---|---|---|---|---|")
        for y in YEARS:
            ex = R["exit_year"][y][0] if R["exit_year"][y] else None
            en = R["entry_year"].get(y, (None, None))[0]
            gv = G["per_year"][y][0] if G["per_year"].get(y) else None
            kv = K["per_year"][y][0] if K["per_year"].get(y) else None
            w(f"| {y} | {fn(ex)} | {fn(en)} | {fn(gv)} | {fn(kv)} | {fn(sub(en, gv))} | {fn(sub(en, kv))} | "
              f"{fn(sub(gv, kv))} | {mark(y, f, G)} |")
        w("")
        w("損益の和(bp)")
        w("")
        w("| 年 | 参照(出の年) | 参照(建ての年) | 段階 G | K1(n × mean_bp) | 参照 − 段階 G | 参照 − K1 | 段階 G − K1 | 印 |")
        w("|---|---|---|---|---|---|---|---|---|")
        for y in YEARS:
            ex = R["exit_year"][y][1] if R["exit_year"][y] else None
            en = R["entry_year"].get(y, (None, None))[1]
            gv = G["per_year"][y][1] if G["per_year"].get(y) else None
            kv = K["per_year"][y][1] if K["per_year"].get(y) else None
            w(f"| {y} | {fb(ex)} | {fb(en)} | {fb(gv)} | {fb(kv)} | {fb(sub(en, gv))} | {fb(sub(en, kv))} | "
              f"{fb(sub(gv, kv))} | {mark(y, f, G)} |")
        w("")

    # ---------------- 表 3: 2021-05 の 15 分
    w("## 3. 批評家の例: 2021-05 の 15 分(建てた足の始まりの月)")
    w("")
    w("批評家の数(指摘 2 の写し): K1 415 取引 +250.93bp、再現 404 取引 −4772.67bp。下は台本が数えた値。"
      "K1 には取引ごとの出力が無いので月の値は出せない(年ごとの n・mean_bp だけ)。")
    w("")
    w("**批評家の数と下の表は、測った物が両側とも違う。下の表は批評家の数の再現ではない。** 批評家の数の作り"
      "(この作業のセッションのスクラッチパッド `critic_c2/` にあり、リポジトリには無い): "
      "K1 の側は `critic_c2/k1ref.py` が K1 の関数(`k1_source.load_bars` → `join_minutes` → `fold_joined` → "
      "`delay_signals` → `simulate(…, \"weak\", use_invalid=False, prices=…)`)を **2021-05-01〜06-01 の 1 か月だけ**、"
      "持ち高 0 から回したもの。再現の側は `critic_c2/m2105_f15/summary.json`(`period` 2021-05-01〜2021-06-01、"
      "entry a、fill_side good、`params` に `fill` の鍵が無い。【推定】参照の形(fill)を足す前のコードで回した指値の形)。"
      "下の表は、参照(足の終値の形)と段階 G の `design|full`(2017-08-17 から 1 本で読んだ実行)の取引を、"
      "建てた足の始まりの月で数えたもの。")
    w("")
    w("| 足 | 月 | 参照 取引 | 参照 損益の和 | 段階 G 取引 | 段階 G 損益の和 | 参照 − 段階 G 取引 | 参照 − 段階 G 損益 |")
    w("|---|---|---|---|---|---|---|---|")
    for f in (5, 15):
        rm = refs[f]["entry_month"].get("2021-05", (None, None))
        gm = gs[f]["month"].get("2021-05", (None, None))
        w(f"| {f} 分 | 2021-05 | {fn(rm[0])} | {fb(rm[1])} | {fn(gm[0])} | {fb(gm[1])} | {fn(sub(rm[0], gm[0]))} | "
          f"{fb(sub(rm[1], gm[1]))} |")
    w("")

    # ---------------- 表 4: 照合
    w("## 4. 照合と、値が無い升")
    w("")
    w("### 4-1 台本の数え直しの照合")
    w("")
    w("| 足 | 参照: 年の取引の和 = all.trades | 参照: 建ての年の損益の和 − all.sum_bp(許す幅 = 取引の数 × 0.00005) | "
      "参照: entry_t_ns が足の区切りに無い取引 | 段階 G: trades.json.gz を数え直した年ごとの n・和 = cells.json |")
    w("|---|---|---|---|---|")
    for f in FEET:
        R, G = refs[f], gs[f]
        sy = sum(R["exit_year"][y][0] for y in YEARS if R["exit_year"][y])
        se = math.fsum(v[1] for v in R["entry_year"].values())
        ne = sum(v[0] for v in R["entry_year"].values())
        tol = R["n"] * 0.00005
        okg = all((G["recount"].get(y) is None and G["per_year"][y] is None) or
                  (G["recount"].get(y) is not None and G["per_year"][y] is not None and
                   G["recount"][y][0] == G["per_year"][y][0] and abs(G["recount"][y][1] - G["per_year"][y][1]) < 1e-6)
                  for y in YEARS)
        w(f"| {f} 分 | {sy:,} / {R['all'][0]:,}(建ての年の和 {ne:,}) | {se - R['all'][1]:+.4f}(幅 {tol:.4f}) | "
          f"{R['off_grid']} | {okg} |")
    w("")
    w("### 4-2 値が無い升(探した場所と確かめ)")
    w("")
    w(f"- 段階 G の 30・60 分の 2017〜2021: `{G_DIR}/runs_index.json` の升のうち足が 30・60 のもの(台本が引いた):")
    rows = sorted({(v["mode"], v["range"], v["foot"]) for v in idx.values() if v["foot"] in (30, 60)})
    w(f"  `{rows}`")
    w(f"- 同じく `{G_DIR}/cells.json` の鍵で足が 30・60 で門 `{GATE}` のもの: "
      f"`{sorted(k for k in cells if k.split('|')[2] in ('30', '60') and k.split('|')[3] == GATE)}`")
    sh = rd(G_RUNS_CLOSE + "/SHARED.json")
    w(f"- `{G_RUNS_CLOSE}/SHARED.json` の実行の終わりの時刻(直した後の口で回し直した実行): "
      f"`{[r.get('end') for r in sh.get('runs', [])]}`(FIXES.md §6・§12 によれば 5・15 分の 2018〜2021 の升)")
    for f in FEET:
        miss = [y for y in YEARS if k1s[f]["per_year"].get(y) is None]
        w(f"- K1 の {f} 分 `{k1s[f]['key']}`: 升が{'無い' if k1s[f]['missing'] else 'ある'}。"
          f"2017〜2023 で per_year の無い年: {miss if miss else 'なし'}")
    w("")

    # ---------------- 表 5: 入力の行の数
    w("## 5. 入力の行の数(足の作り方の違いの手がかり)")
    w("")
    w("参照の行 = 参照の run_record.json の区切りごとの `ref_rows`(Binance の 1 分足、4 本値の 1 系列分)と `bars`"
      "(bitFlyer、`no_trade` を落とした後)。段階 G = FOLD_MANIFEST.json の各入力の `rows_kept_in_range`(範囲の中の行)・`events_after_policy`(方針の後)。"
      "K1 = `alignment.per_year`(分の内部結合の前後の分の数)。参照の値は 15 分の走らせのもの(区切りの行の数は"
      "足に依らない読みなので 4 つで同じかを右端で示す)。")
    w("")
    fold_bin = {}
    fold_bf = {}
    for x in fold["inputs"]:
        y0 = int(x["range"][0][:4])
        if "binance_BTCUSDT" in x["path"]:
            fold_bin[y0] = x
        elif "tmp_bitflyer" in x["path"]:
            fold_bf[y0] = x
    alg = k1["alignment"]["per_year"]
    w("| 年 | 参照 Binance 行 | 段階 G Binance 範囲の中の行 / 方針の後 / synthetic | K1 Binance の分 / 結合後の分 | "
      "参照 bitFlyer 足 | 段階 G bitFlyer 方針の後 | K1 bitFlyer の分 | 参照の行の数が 4 つの足で同じ |")
    w("|---|---|---|---|---|---|---|---|")
    for y in YEARS:
        ch = {f: [c for c in refs[f]["chunks"] if c["range"][0][:4] == str(y)] for f in FEET}
        c15 = ch[15][0] if ch[15] else None
        same = len({(c[0]["ref_rows"], c[0]["bars"]) for c in ch.values() if c}) == 1
        fb_ = fold_bin.get(y)
        ff_ = fold_bf.get(y)
        a = alg.get(str(y)) if y != 2023 else None  # K1 の 2023 は封印の後の分を含むので出さない
        w(f"| {y} | {fn(c15['ref_rows'] if c15 else None)} | "
          f"{fn(fb_['rows_kept_in_range'] if fb_ else None)} / {fn(fb_['events_after_policy'] if fb_ else None)} / "
          f"{fn((fb_ or {}).get('anomalies', {}).get('synthetic'))} | "
          f"{fn(a['minutes_signal'] if a else None)} / {fn(a['minutes_both'] if a else None)} | "
          f"{fn(c15['bars'] if c15 else None)} | {fn(ff_['events_after_policy'] if ff_ else None)} | "
          f"{fn(a['minutes_price'] if a else None)} | {same} |")
    w("")
    w(f"参照の区切りの範囲(15 分): `{[c['range'] for c in refs[15]['chunks']]}`。2017 の参照は 2017-08-17T15:00Z から、"
      "段階 G・K1 の 2017 は Binance のファイルの最初(FOLD_MANIFEST の `first_ts`)から。2023 の参照は 12-17T15:00Z まで、"
      "段階 G は 12-18T00:00Z まで、K1 は 12-31 まで(K1 の 2023 の行は封印の境の後の分を含む)。")
    w("")

    out = os.path.join(ROOT, OUT)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
