"""K1 取引所横断 — 段階 1(`docs/PHASE2/K1/XVENUE_PREREG.md` §3 Deliverable B)。

海外取引所(既定 Binance BTCUSDT 現物)のヒゲのシグナルを、bitFlyer FX_BTC_JPY の価格で
値付けする。**設計は変えない**(封印の判定と同じ H1+H2a+H3、弱いだけが主統計)。
変えるのはシグナルを取る取引所と、約定に使う価格の取引所だけ。

読み込み・結合:
    signal_bars = k1_source.load_bars(signal_source, start, end)
    price_bars  = k1_source.load_bars(price_source,  start, end)
    UTC の分で内部結合(どちらかに無い分は落とす)→ 足への畳み込みは結合後、
    両取引所を同じ窓で行う(結合済みの分の集合が両取引所で同一なので、
    `measure_katsuo_dispersion.fold()` を別々に掛けても同じバケツになる。テストで確認)。

族 = 足 6 × 門 13 × 強さ 3 = 234 セル(`measure_katsuo_effect.gates()` と同一)。

セルごと:
    design:    sg = delay_signals(signals(signal_bars, s, b, flip_body=True))     # H3
               simulate(signal_bars, sg, keep, use_invalid=False, prices=price_close)  # H2a
    sameclose: sg = signals(signal_bars, s, b, flip_body=True)                     # H3 無し
               simulate(signal_bars, sg, keep, use_invalid=False, prices=price_close)
    (`sameclose` は H3 を外すだけで、約定は自動的に「海外の足 i の確定と同時刻の bitFlyer 足 i
    の終値」になる — delay を外すとループの添字がそのままそちらにずれるため)。

出すもの:
    xvenue/effect_{sig}_to_{price}.json[_YYYY_YYYY]        … 設計
    xvenue/effect_{sig}_to_{price}_sameclose.json[_YYYY_YYYY] … 参考列 (iii)
    xvenue/alignment.json                                   … 結合の統計(既定期間のみ)

再現ゲート(`--gate`): 結合していない Binance の生の足に `prices=None` を渡した設計セルが
`docs/PHASE2/K1/binance/effect_flip_noinval_delay.json` の全 234 セルと一致すること
(n と平均 bp、2e-3 以内)。

ボラ三分位(`--vol-terciles`): 主統計セル(門 `s19/b24`、足 5・15、弱い)について、
シグナル取引所側の局所ボラ(直前 100 本の |log(close/close[-1])| × 1e4 の平均、
`measure_katsuo_robustness.FootData.vol_prev` と同じ定義)で三分位に分け、
境目は (1) BitMEX 固定値(`FRESH_BITFLYER_PREREG.md` §2 の第 15 部の値)と
(2) この設計の Binance 2018-2019 の取引の vol_prev から決めた値、の 2 列で年別に出す。

    PYTHONPATH=src:scripts python scripts/measure_katsuo_xvenue.py \
        --signal-source binance --price-source bitflyer
    PYTHONPATH=src:scripts python scripts/measure_katsuo_xvenue.py --gate
    PYTHONPATH=src:scripts python scripts/measure_katsuo_xvenue.py --vol-terciles
"""
from __future__ import annotations

import argparse
import json
import math
import random
from datetime import date, datetime, timezone
from pathlib import Path

import k1_source
import measure_katsuo_dispersion as base
import measure_katsuo_effect as eff
import measure_katsuo_robustness as rb

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "docs" / "PHASE2" / "K1" / "xvenue"
BINANCE_REF = REPO / "docs" / "PHASE2" / "K1" / "binance" / "effect_flip_noinval_delay.json"

# Binance の手元データが始まる日(k1_source.SOURCES["binance"]["start"])を bitFlyer の
# 範囲(2017-01-01〜2026-08-31)と交わらせた既定期間(プレレジ §2、段階 1)
DEFAULT_START = date(2017, 8, 17)
DEFAULT_END = date(2026, 8, 31)

# 段階 2(Bybit、XVENUE_PREREG.md §2)の既定期間。シグナル取引所ごとに既定の範囲・命名が違う
# ("bybit" 未消費期間 2022-01-01〜2026-08-31)ので、signal_source をキーに切り替える。
# 無いキー(binance/bitflyer)は従来どおり DEFAULT_START/END を使う(挙動不変)。
DEFAULT_RANGES = {
    "bybit": (date(2022, 1, 1), date(2026, 8, 31)),
}


def default_range(signal_source: str) -> tuple[date, date]:
    return DEFAULT_RANGES.get(signal_source, (DEFAULT_START, DEFAULT_END))

FEET = eff.FEET                    # (1, 3, 5, 15, 30, 60)
MAIN_FEET = (5, 15)
MAIN_GATE_SMALL, MAIN_GATE_BIG = 19.0, 24.0
MAIN_GATE_LABEL = "s19/b24"
VOL_TRAIN_START_YEAR = 2018         # Binance 2018-2019(この設計の取引で境目を決める)
VOL_TRAIN_END_YEAR = 2019
BITMEX_FIXED_EDGES = {5: (21.79, 35.17), 15: (29.58, 48.68)}   # 第 15 部の固定値(既存の数値。再計算しない)


def year_of(ts: int) -> int:
    return datetime.fromtimestamp(ts, tz=timezone.utc).year


# ---------------------------------------------------------------------------
# 結合
# ---------------------------------------------------------------------------

def join_minutes(sig_rows, price_rows):
    """UTC の分で内部結合。どちらかに無い分は落とす。

    戻り値: (sig_joined, price_joined, common_ts)。`sig_joined[k]`/`price_joined[k]` は
    同じ分 `common_ts[k]` の行(お互いの `(o,h,l,c)` は別物、時刻だけ揃っている)。
    """
    sig_map = {r[0]: r for r in sig_rows}
    price_map = {r[0]: r for r in price_rows}
    common_ts = sorted(set(sig_map) & set(price_map))
    sig_joined = [sig_map[t] for t in common_ts]
    price_joined = [price_map[t] for t in common_ts]
    return sig_joined, price_joined, common_ts, sig_map, price_map


def alignment_stats(sig_rows, price_rows, common_ts, signal_source, price_source, start, end):
    sig_years, price_years, both_years = {}, {}, {}
    for r in sig_rows:
        y = year_of(r[0])
        sig_years[y] = sig_years.get(y, 0) + 1
    for r in price_rows:
        y = year_of(r[0])
        price_years[y] = price_years.get(y, 0) + 1
    for t in common_ts:
        y = year_of(t)
        both_years[y] = both_years.get(y, 0) + 1
    years = sorted(set(sig_years) | set(price_years) | set(both_years))
    per_year = {}
    for y in years:
        ns, npc, nb = sig_years.get(y, 0), price_years.get(y, 0), both_years.get(y, 0)
        per_year[str(y)] = {
            "minutes_signal": ns,
            "minutes_price": npc,
            "minutes_both": nb,
            "dropped_share_signal": round(1 - nb / ns, 4) if ns else None,
            "dropped_share_price": round(1 - nb / npc, 4) if npc else None,
        }
    ns_t, npc_t, nb_t = len(sig_rows), len(price_rows), len(common_ts)
    return {
        "note": ("UTC の分の内部結合。どちらかの取引所に無い分は落とす。dropped_share は"
                 "その取引所側の分のうち結合後に残らなかった割合。"),
        "signal_source": signal_source, "price_source": price_source,
        "range": [start.isoformat(), end.isoformat()],
        "totals": {"minutes_signal": ns_t, "minutes_price": npc_t, "minutes_both": nb_t,
                    "dropped_share_signal": round(1 - nb_t / ns_t, 4) if ns_t else None,
                    "dropped_share_price": round(1 - nb_t / npc_t, 4) if npc_t else None},
        "per_year": per_year,
    }


def fold_joined(sig_joined, price_joined, foot):
    """結合済みの分を両取引所で同じ窓で畳み込む。時刻が完全に一致することを assert する。"""
    sig_bars = base.fold(sig_joined, foot)
    price_bars = base.fold(price_joined, foot)
    sig_ts = [b[0] for b in sig_bars]
    price_ts = [b[0] for b in price_bars]
    assert sig_ts == price_ts, (
        f"foot={foot}: 結合後に同じ窓で畳んだのに時刻が一致しない "
        f"(sig {len(sig_ts)} 本 vs price {len(price_ts)} 本) — 結合が壊れている"
    )
    return sig_bars, price_bars


# ---------------------------------------------------------------------------
# セルの要約(measure_katsuo_effect.main() の中身と同じ形の辞書を作る)
# ---------------------------------------------------------------------------

def summarize_cell(foot, gate_label, keep, tr, ts, years, rng):
    if len(tr) < 30:
        return None
    rs = [r for _i, r, _h, _w in tr]
    n = len(rs)
    mean = sum(rs) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in rs) / (n - 1)) if n > 1 else float("nan")
    lo, hi = eff.block_bootstrap(tr, ts, rng)
    srt = sorted(rs)
    quant = {k: round(srt[min(n - 1, int(q * (n - 1)))], 2) for k, q in
             (("p05", 0.05), ("p25", 0.25), ("p50", 0.50), ("p75", 0.75), ("p95", 0.95))}
    per_year = {}
    for y in sorted(set(years)):
        ys = [r for i, r, _h, _w in tr if years[i] == y]
        if ys:
            per_year[str(y)] = {"n": len(ys), "mean_bp": round(sum(ys) / len(ys), 3)}
    why: dict[str, int] = {}
    for _i, _r, _h, w in tr:
        why[w] = why.get(w, 0) + 1
    return {
        "foot": foot, "gate": gate_label, "strength": keep,
        "n": n, "mean_bp": round(mean, 3), "ci95_bp": [round(lo, 3), round(hi, 3)],
        "sd_bp": round(sd, 1), "quantiles_bp": quant,
        "hold_median": sorted(h for _i, _r, h, _w in tr)[n // 2],
        "exit_reasons": why, "per_year": per_year,
    }


# ---------------------------------------------------------------------------
# 設計 + 参考列(iii)
# ---------------------------------------------------------------------------

def run_design(signal_source, price_source, start, end):
    print(f"シグナル={signal_source} 価格={price_source} 期間 {start} 〜 {end}")
    sig_rows = k1_source.load_bars(signal_source, start, end)
    sig_load = dict(k1_source.last_load)
    price_rows = k1_source.load_bars(price_source, start, end)
    price_load = dict(k1_source.last_load)
    sig_joined, price_joined, common_ts, _sm, _pm = join_minutes(sig_rows, price_rows)
    print(f"  結合: シグナル側 {len(sig_rows):,} 分 / 価格側 {len(price_rows):,} 分 "
          f"/ 両方 {len(common_ts):,} 分")
    alignment = alignment_stats(sig_rows, price_rows, common_ts, signal_source, price_source, start, end)

    gs = eff.gates()
    rng_design = random.Random(eff.SEED)
    rng_ref = random.Random(eff.SEED)
    cells_design, cells_ref = {}, {}
    for foot in FEET:
        sig_bars, price_bars = fold_joined(sig_joined, price_joined, foot)
        ts = [b[0] for b in sig_bars]
        years = [year_of(t) for t in ts]
        price_close = [b[4] for b in price_bars]
        for g in gs:
            sg_design = eff.delay_signals(eff.signals(sig_bars, g[0], g[1], flip_body=True))    # H3
            sg_ref = eff.signals(sig_bars, g[0], g[1], flip_body=True)                          # H3 無し
            for keep in eff.STRENGTHS:
                k = None if keep == "both" else keep
                tr_d = eff.simulate(sig_bars, sg_design, k, use_invalid=False, prices=price_close)
                cd = summarize_cell(foot, eff.label(g), keep, tr_d, ts, years, rng_design)
                if cd:
                    cells_design[f"{foot}|{eff.label(g)}|{keep}"] = cd
                tr_r = eff.simulate(sig_bars, sg_ref, k, use_invalid=False, prices=price_close)
                cr = summarize_cell(foot, eff.label(g), keep, tr_r, ts, years, rng_ref)
                if cr:
                    cells_ref[f"{foot}|{eff.label(g)}|{keep}"] = cr
        print(f"  {foot:>3}分 完了(セル {sum(1 for k in cells_design if k.startswith(f'{foot}|'))} 件)")

    common = {
        "explore": [start.isoformat(), end.isoformat()],
        "signal_source": signal_source, "price_source": price_source,
        "load": {"signal": sig_load, "price": price_load},
        "alignment": alignment,
        "flip_body": True, "use_invalid": False,
        "bootstrap_reps": eff.BOOTSTRAP, "seed": eff.SEED,
        "family": {"feet": list(FEET), "gates": [eff.label(g) for g in gs], "strengths": list(eff.STRENGTHS)},
    }
    design_payload = dict(common)
    design_payload["note"] = ("K1 取引所横断 段階 1・設計(H1+H2a+H3): シグナルは signal_source の足、"
                               "決済判断・強さもすべて signal_source、約定価格だけ price_source。"
                               "帰無・MDE・判定バーは作っていない。経費は引いていない。")
    design_payload["delay_entry"] = True
    design_payload["cells"] = cells_design

    ref_payload = dict(common)
    ref_payload["note"] = ("参考列(iii): 設計と同じシグナル・強さだが H3(1 本遅らせ)を外し、"
                            "約定は price_source の同じ添字の足の終値(= signal_source の足 i の確定と"
                            "同時刻。取れない価格)。")
    ref_payload["delay_entry"] = False
    ref_payload["cells"] = cells_ref

    return design_payload, ref_payload, alignment


def write_json(payload, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  → {path}")


# ---------------------------------------------------------------------------
# 再現ゲート
# ---------------------------------------------------------------------------

def run_gate(start, end):
    ref = json.loads(BINANCE_REF.read_text("utf-8"))["cells"]
    print(f"再現ゲート: Binance 生の足(結合なし)に prices=None、期間 {start} 〜 {end}")
    seconds = k1_source.load_bars("binance", start, end)
    gs = eff.gates()
    repro = []
    for foot in FEET:
        bars = base.fold(seconds, foot)
        ts = [b[0] for b in bars]
        for g in gs:
            sg = eff.delay_signals(eff.signals(bars, g[0], g[1], flip_body=True))
            for keep in eff.STRENGTHS:
                k = None if keep == "both" else keep
                tr = eff.simulate(bars, sg, k, use_invalid=False, prices=None)
                key = f"{foot}|{eff.label(g)}|{keep}"
                rc = ref.get(key)
                if rc is None:
                    continue
                n = len(tr)
                mean = (sum(r for _i, r, _h, _w in tr) / n) if n else float("nan")
                ok = rc["n"] == n and n > 0 and abs(rc["mean_bp"] - mean) < 2e-3
                repro.append({"key": key, "ok": ok, "n": n, "n_ref": rc["n"],
                              "mean": round(mean, 3) if n else None, "mean_ref": rc["mean_bp"]})
    n_ok = sum(r["ok"] for r in repro)
    print(f"再現ゲート {n_ok}/{len(repro)} 一致")
    payload = {
        "note": ("再現ゲート: 結合していない Binance の生の足に prices=None を渡した設計セル(H1+H3、"
                 "use_invalid=False)が binance/effect_flip_noinval_delay.json の全セルと一致すること "
                 "(n と平均 bp、2e-3 以内)。"),
        "range": [start.isoformat(), end.isoformat()],
        "reference_file": str(BINANCE_REF.relative_to(REPO)),
        "reproduction_gate": repro,
        "pass": n_ok == len(repro) == 234,
        "n_ok": n_ok, "n_total": len(repro),
    }
    write_json(payload, OUT_DIR / "gate_result.json")
    if n_ok != len(repro) or len(repro) != 234:
        raise SystemExit(f"再現ゲート不一致: {n_ok}/{len(repro)}(234 セル中)")
    return payload


# ---------------------------------------------------------------------------
# ボラ三分位
# ---------------------------------------------------------------------------

def edges_from_vol(vals):
    vals = [v for v in vals if v == v]  # drop nan
    if not vals:
        return None
    srt = sorted(vals)
    n = len(srt)

    def q(p):
        k = (n - 1) * p
        lo, hi = math.floor(k), math.ceil(k)
        return srt[int(k)] if lo == hi else srt[lo] * (hi - k) + srt[hi] * (k - lo)
    return float(q(1 / 3)), float(q(2 / 3))


def bucket_of(v, edges):
    if edges is None or v != v:
        return None
    q1, q2 = edges
    if v < q1:
        return "low"
    if v < q2:
        return "mid"
    return "high"


def per_year_tercile(trades_year_ret_vol, edges, years):
    out = {}
    for y in years:
        buckets = {"low": [], "mid": [], "high": []}
        for yy, r, v in trades_year_ret_vol:
            if yy != y:
                continue
            b = bucket_of(v, edges)
            if b is not None:
                buckets[b].append(r)
        out[str(y)] = {
            name: {"n": len(rs), "mean_bp": round(sum(rs) / len(rs), 3) if rs else None,
                   "total_bp": round(sum(rs), 1) if rs else 0.0}
            for name, rs in buckets.items()
        }
    return out


def run_vol_terciles(signal_source, price_source, start, end):
    print(f"ボラ三分位: シグナル={signal_source} 価格={price_source} 期間 {start} 〜 {end}")
    sig_rows = k1_source.load_bars(signal_source, start, end)
    price_rows = k1_source.load_bars(price_source, start, end)
    sig_joined, price_joined, common_ts, _sm, _pm = join_minutes(sig_rows, price_rows)

    # signal_source の 訓練窓(2018-2019)自身の取引から境目 (2) を作れるのは Binance だけ
    # (Bybit 等は 2022 以降しかデータが無く、訓練窓が空になる)。事前登録どおり、境目 (2) は
    # 「この設計の Binance 2018-2019 の取引」で固定 — signal_source が Binance でなければ
    # 既存の vol_terciles.json(段階 1 の出力、再計算しない)から読む
    binance_ref_edges = None
    if signal_source != "binance":
        ref_path = OUT_DIR / "vol_terciles.json"
        if ref_path.exists():
            ref = json.loads(ref_path.read_text("utf-8"))
            binance_ref_edges = {int(k): tuple(v["edges_bp_own"]) for k, v in ref["feet"].items()
                                  if v.get("edges_bp_own")}

    result = {
        "note": ("K1 取引所横断・ボラ三分位(主統計セル: 門 s19/b24、足 5・15、弱い)。"
                 "局所ボラは signal_source 側(直前 100 本の |log(close/close[-1])| × 1e4 の平均、"
                 "measure_katsuo_robustness.FootData.vol_prev と同一定義)。"
                 "edges_bp_own は「この設計の Binance " f"{VOL_TRAIN_START_YEAR}-{VOL_TRAIN_END_YEAR}"
                 "の取引の vol_prev から決めた境目」固定(事前登録どおり)。signal_source=binance は自前の"
                 f"{VOL_TRAIN_START_YEAR}-{VOL_TRAIN_END_YEAR}取引から直接計算、他ソース(訓練窓にデータが"
                 "無い)は既存 vol_terciles.json の値を再利用(再計算しない)。edges_bp_bitmex_fixed は"
                 "第 15 部の BitMEX 固定値(再計算しない既存の数値)。"),
        "signal_source": signal_source, "price_source": price_source,
        "gate": MAIN_GATE_LABEL, "design": {"flip_body": True, "use_invalid": False, "delay_entry": True, "keep": "weak"},
        "vol_window": rb.VOL_WINDOW,
        "edges_train_years": [VOL_TRAIN_START_YEAR, VOL_TRAIN_END_YEAR],
        "bitmex_fixed_edges_bp": {str(k): list(v) for k, v in BITMEX_FIXED_EDGES.items()},
        "range": [start.isoformat(), end.isoformat()],
        "feet": {},
    }
    for foot in MAIN_FEET:
        sig_bars, price_bars = fold_joined(sig_joined, price_joined, foot)
        ts = [b[0] for b in sig_bars]
        price_close = [b[4] for b in price_bars]
        sig = eff.delay_signals(eff.signals(sig_bars, MAIN_GATE_SMALL, MAIN_GATE_BIG, flip_body=True))
        trades = eff.simulate(sig_bars, sig, "weak", use_invalid=False, prices=price_close)
        fd = rb.FootData(sig_bars)
        all_trades = []
        for entry_i, r, _hold, _why in trades:
            v = float(fd.vol_prev[entry_i])
            y = year_of(ts[entry_i])
            all_trades.append((y, r, v))
        train = [t for t in all_trades if VOL_TRAIN_START_YEAR <= t[0] <= VOL_TRAIN_END_YEAR]
        if signal_source == "binance":
            edges_own = edges_from_vol([v for _y, _r, v in train])
            edges_own_basis = "self (this run's Binance 2018-2019 trades)"
        else:
            edges_own = binance_ref_edges.get(foot) if binance_ref_edges else None
            edges_own_basis = ("docs/PHASE2/K1/xvenue/vol_terciles.json (stored Binance 2018-2019 "
                                "edges, not recomputed; signal_source has no 2018-2019 data)")
        n_no_vol = sum(1 for _y, _r, v in all_trades if v != v)
        years = sorted(set(y for y, _r, _v in all_trades))
        result["feet"][str(foot)] = {
            "n_bars": len(sig_bars),
            "edges_bp_own": [round(edges_own[0], 2), round(edges_own[1], 2)] if edges_own else None,
            "edges_bp_own_basis": edges_own_basis,
            "edges_bp_bitmex_fixed": list(BITMEX_FIXED_EDGES[foot]),
            "n_no_vol": n_no_vol,
            "n_trades_total": len(all_trades),
            f"n_trades_{VOL_TRAIN_START_YEAR}_{VOL_TRAIN_END_YEAR}": len(train),
            "per_year_own_edges": per_year_tercile(all_trades, edges_own, years),
            "per_year_bitmex_fixed_edges": per_year_tercile(all_trades, BITMEX_FIXED_EDGES[foot], years),
        }
        print(f"  {foot}分: own edges {result['feet'][str(foot)]['edges_bp_own']} bp"
              f"({edges_own_basis})"
              f" / 取引 {len(all_trades):,} 件(訓練 {len(train):,} 件) / vol 無し {n_no_vol:,} 件")

    # 段階 1(signal_source=binance)は既存名 vol_terciles.json のまま(既に参照済み)。
    # 他ソース(段階 2 の bybit など)は接頭辞を付けて別ファイルにする
    out_name = "vol_terciles.json" if signal_source == "binance" else f"{signal_source}_vol_terciles.json"
    write_json(result, OUT_DIR / out_name)
    return result


# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--signal-source", choices=("binance", "bitflyer", "bybit"), default="binance")
    ap.add_argument("--price-source", choices=("binance", "bitflyer", "bybit"), default="bitflyer")
    ap.add_argument("--start", type=date.fromisoformat, default=None)
    ap.add_argument("--end", type=date.fromisoformat, default=None)
    ap.add_argument("--gate", action="store_true", help="再現ゲートのみ実行")
    ap.add_argument("--vol-terciles", action="store_true", help="ボラ三分位のみ実行")
    args = ap.parse_args()

    def_start, def_end = default_range(args.signal_source)
    start = args.start if args.start is not None else def_start
    end = args.end if args.end is not None else def_end

    if args.gate:
        run_gate(start, end)
        return

    if args.vol_terciles:
        run_vol_terciles(args.signal_source, args.price_source, start, end)
        return

    design, ref, alignment = run_design(args.signal_source, args.price_source, start, end)

    full_range = start == def_start and end == def_end
    suffix = "" if full_range else f"_{start.year}_{end.year}"
    base_name = f"effect_{args.signal_source}_to_{args.price_source}"
    write_json(design, OUT_DIR / f"{base_name}{suffix}.json")
    write_json(ref, OUT_DIR / f"{base_name}_sameclose{suffix}.json")
    if full_range:
        # 段階 1(binance)は既存名 alignment.json のまま(参照済み)。他ソースは接頭辞を付ける
        align_name = "alignment.json" if args.signal_source == "binance" else f"{args.signal_source}_alignment.json"
        write_json(alignment, OUT_DIR / align_name)

    print(f"\nセル 設計 {len(design['cells'])} 件 / 参考列 {len(ref['cells'])} 件")


if __name__ == "__main__":
    main()
