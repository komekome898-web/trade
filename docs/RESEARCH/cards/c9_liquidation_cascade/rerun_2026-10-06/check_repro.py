#!/usr/bin/env python3
"""カード 9 の走らせ直し(2026-10-06)の検め: (1) 元の走らせの再現 (2) 主(気配)の値の検め。

委任文: `docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_rerun_impl.md`(担当 C の (4))。
批評家 1 回目(`docs/AUDITOR/VERDICTS/2026-10-06_c9_rerun_critic1.md`)の問 3 を受けた形。

(1) 再現: 新しい走らせの日ごとの連鎖・レグの行を、元の走らせの `chunks/` の同じ日の行と比べる。
- `--fill-side quote` の走らせでは、1 回目(どちらの側でも)の結果を元と同じ列で書いた
  `chunks/{cascades,legs,cascades3,legs3}_any/` を使う(主の付け方でレグの数・`hold_s` が変わっても
  落ちない)。既定・`any --leg-path` の走らせでは `chunks/{cascades,legs,cascades3,legs3}/` を使う。
- 突き合わせの鍵: (side, gap_s, start_ms, delay_s, policy, type)。`bundle_id` は読んだ範囲の束の
  通し番号を含むので比べない。`start_ms` は `chunks/bundles/<日>.csv.gz` から引く。レグは鍵の中の
  並び順で突き合わせる。比べる列は元の見出しの列すべて(`bundle_id` と `--ignore` を除く)を、CSV の
  文字列のまま(どちらも `%.8g`)。
(2) 主の値の検め(`quote` の走らせのとき。新しい走らせの `chunks/legs*/` と `chunks/cascades*/`):
- 遅れ `in_lag_ms`・`out_lag_ms` ≤ 0、気配の古さ `*_quote_age_ms` = −遅れ、かつ ≤ 300,000
- `order_in` = 束の側の向き(SELL −1・BUY +1)×(順張り +1・逆張り −1)、`order_out` = −`order_in`
- `pnl_bp` = `order_in` ×(`out_px` − `in_px`)÷ `in_px` × 1e4(差 ≤ 1e-6 × max(1, |pnl_bp|))
- `path_ok` = 1 の行で `mfe_bp` ≥ 0 ≥ `mae_bp`
- 連鎖の行の `pnl_bp` = その連鎖のレグの `pnl_bp` の和(値の欠けの無い連鎖、同じ許し幅)
- `in_px`・`out_px`・`in_fill_ms`・`out_fill_ms` = 気配の表(`--quotes-dir` の `days/<日>.csv.gz`)を
  `liq_cascade_fill.QuoteBook` で引き直した値(買いは売り気配・売りは買い気配、批評家 2 回目)
(3) 付け方ごとの値の欠けの数(`quote` のとき): 主(気配)・元の付け方・(b)・(a) ごとに、欠けた連鎖の数と、
その連鎖のレグの数、レグの損益の列が NaN のレグの数。

**境の守り**: 元の走らせの置き場(`--orig`)は 2023-12-16 までの日しか開かない(`read_orig` が
2023-12-17 以後の日を開こうとしたら止める)。2023-12-17 以後の日は、新しい出力だけを数え(元とは
比べない)、主の値の検めと欠けの数だけを出す(批評家 2 回目の [止める])。

    python3 docs/RESEARCH/cards/c9_liquidation_cascade/rerun_2026-10-06/check_repro.py \
        --orig data/c9_run_a/full_20230625_20241014 --new <新しい走らせ> \
        --start 2023-07-01 --end 2023-07-02 --ignore period --skip-policy 規則_3択

違いか検めの外れが 1 つでもあれば終了コード 1。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bot.research import liq_cascade_fill as fill  # noqa: E402

KEY = ["side", "gap_s", "start_ms", "delay_s", "policy", "type"]
#: 元の走らせの置き場で開いてよい最後の日(封印の境 2023-12-17T15:00Z を越えない最後の日まるごと)
ORIG_LAST_DAY = "2023-12-16"
METHODS = (("主(気配)", "missing", None), ("元の付け方", "missing_anyside", "pnl_bp_anyside"),
           ("(b) 直前の同じ側の約定", "missing_taker_prev", "pnl_bp_taker_prev"),
           ("(a) 以後で最初の同じ側の約定", "missing_taker_wait", "pnl_bp_taker_wait"))
SIDE_SIGN = {"SELL": -1, "BUY": 1}
DIR_SIGN = {"順張り": 1, "逆張り": -1}
STALENESS_MS = 300_000


def days_between(a: str, b: str) -> list[str]:
    d, e = date.fromisoformat(a), date.fromisoformat(b)
    out = []
    while d <= e:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def read(p: Path) -> pd.DataFrame:
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, dtype=str, keep_default_na=False)


def read_orig(root: Path, sub: str, day: str) -> pd.DataFrame:
    """元の走らせの置き場の日ごとのファイル。2023-12-17 以後の日は開かずに止める。"""
    if day > ORIG_LAST_DAY:
        raise SystemExit(f"[止め] 元の走らせの {day} の出力は開かない(境 2023-12-17T15:00Z より後の"
                         f"約定から計算した値を含みうる)")
    return read(Path(root) / sub / f"{day}.csv.gz")


def cat(paths) -> pd.DataFrame:
    parts = [p if isinstance(p, pd.DataFrame) else read(p) for p in paths]
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def with_start(df: pd.DataFrame, bundles: pd.DataFrame) -> pd.DataFrame:
    if not len(df):
        return df
    m = dict(zip(bundles["bundle_id"], bundles["start_ms"]))
    df = df.copy()
    df["start_ms"] = df["bundle_id"].map(m)
    if "side" not in df.columns:
        df["side"] = df["bundle_id"].map(dict(zip(bundles["bundle_id"], bundles["side"])))
    if df["start_ms"].isna().any():
        raise SystemExit("[止め] 束の表に無い bundle_id がある")
    df["_ord"] = df.groupby(KEY, sort=False).cumcount().astype(str)
    return df


def compare(orig: pd.DataFrame, new: pd.DataFrame, cols: list[str], skip_policy: set) -> dict:
    if len(orig):
        orig = orig[~orig["policy"].isin(skip_policy)]
    if len(new):
        new = new[~new["policy"].isin(skip_policy)]
    res = {"元の行": int(len(orig)), "新しい行": int(len(new))}
    if not len(orig) and not len(new):
        return res | {"突き合わせた行": 0, "片方だけの行": 0, "違う値": {}}
    if not len(orig) or not len(new):
        return res | {"突き合わせた行": 0, "片方だけの行": int(len(orig) + len(new)), "違う値": {}}
    k = KEY + ["_ord"]
    j = orig.merge(new, on=k, how="outer", suffixes=("_o", "_n"), indicator=True)
    res["片方だけの行"] = int((j["_merge"] != "both").sum())
    b = j[j["_merge"] == "both"]
    res["突き合わせた行"] = int(len(b))
    diff = {}
    for c in cols:
        lo, ln = f"{c}_o", f"{c}_n"
        if lo not in b.columns or ln not in b.columns:
            diff[c] = "列が無い"
            continue
        n = int((b[lo].astype(str) != b[ln].astype(str)).sum())
        if n:
            diff[c] = n
    res["違う値"] = diff
    return res


def _f(s: pd.Series) -> np.ndarray:
    return pd.to_numeric(s, errors="coerce").to_numpy(float)


def main_value_checks(legs: pd.DataFrame, cascades: pd.DataFrame) -> dict:
    """主(気配)の値の検め。外れの数を返す(0 なら通った)。"""
    out: dict = {"レグ": int(len(legs))}
    if not len(legs):
        return out | {"外れ": {}}
    bad: dict = {}
    il, ol = _f(legs["in_lag_ms"]), _f(legs["out_lag_ms"])
    ia, oa = _f(legs["in_quote_age_ms"]), _f(legs["out_quote_age_ms"])
    ok = np.isfinite(il) & np.isfinite(ol)
    bad["遅れ > 0"] = int(((il > 0) | (ol > 0))[ok].sum())
    bad["古さ ≠ −遅れ"] = int(((ia != -il) | (oa != -ol))[ok].sum())
    bad["古さ > 300 秒"] = int(((ia > STALENESS_MS) | (oa > STALENESS_MS))[ok].sum())
    oi, oo = _f(legs["order_in"]), _f(legs["order_out"])
    want = np.array([SIDE_SIGN[s] * DIR_SIGN[d] for s, d in zip(legs["side"], legs["leg_dir"])],
                    dtype=float)
    bad["order_in ≠ 側 × 向き"] = int((oi != want)[ok].sum())
    bad["order_out ≠ −order_in"] = int((oo != -oi)[ok].sum())
    pin, pout, pnl = _f(legs["in_px"]), _f(legs["out_px"]), _f(legs["pnl_bp"])
    calc = oi * (pout - pin) / pin * 1e4
    tol = 1e-6 * np.maximum(1.0, np.abs(pnl))
    bad["pnl_bp ≠ 値段から計算"] = int((np.abs(calc - pnl) > tol)[ok].sum())
    pok = _f(legs["path_ok"]) == 1
    mfe, mae = _f(legs["mfe_bp"]), _f(legs["mae_bp"])
    bad["mfe < 0 または mae > 0"] = int(((mfe < 0) | (mae > 0))[pok].sum())
    out["遅れの読めたレグ"] = int(ok.sum())
    out["path_ok のレグ"] = int(pok.sum())
    if len(cascades):
        c = cascades[cascades["missing"] == "0"]
        lg = legs.copy()
        lg["_p"] = _f(lg["pnl_bp"])
        s = lg.groupby(KEY)["_p"].sum()
        cc = c.set_index(KEY)
        cp = _f(cc["pnl_bp"])
        got = s.reindex(cc.index).fillna(0.0).to_numpy(float)
        tol2 = 1e-6 * np.maximum(1.0, np.abs(cp))
        bad["連鎖の pnl_bp ≠ レグの和"] = int((np.abs(got - cp) > tol2).sum())
        out["欠けの無い連鎖"] = int(len(c))
    out["外れ"] = {k: v for k, v in bad.items() if v}
    return out


def quote_checks(legs: pd.DataFrame, qb) -> dict:
    """`in_px`・`out_px`・`in_fill_ms`・`out_fill_ms` を気配の表から引き直した値と比べる。"""
    out: dict = {"レグ": int(len(legs))}
    if not len(legs):
        return out | {"外れ": {}}
    bad = {"in_px・in_fill_ms ≠ 気配の表": 0, "out_px・out_fill_ms ≠ 気配の表": 0}
    n = 0
    for r in legs.itertuples(index=False):
        if r.in_lag_ms == "" or r.out_lag_ms == "":
            continue
        n += 1
        for side, tgt, px, t, o in (("in", r.in_target_ms, r.in_px, r.in_fill_ms, r.order_in),
                                    ("out", r.out_target_ms, r.out_px, r.out_fill_ms,
                                     r.order_out)):
            want_px, want_t = qb.lookup(int(float(o)), int(float(tgt)))
            if want_t is None or float(px) != want_px or int(float(t)) != want_t:
                bad[f"{side}_px・{side}_fill_ms ≠ 気配の表"] += 1
    out["引き直したレグ"] = n
    out["外れ"] = {k: v for k, v in bad.items() if v}
    return out


def missing_counts(legs: pd.DataFrame, cascades: pd.DataFrame) -> dict:
    """付け方ごとの値の欠けの数(連鎖・その連鎖のレグ・損益の列が NaN のレグ)。"""
    out = {}
    lk = legs.set_index(KEY).index if len(legs) else None
    for name, mcol, lcol in METHODS:
        if not len(cascades) or mcol not in cascades.columns:
            continue
        mc = cascades[cascades[mcol] == "1"]
        mk = set(mc.set_index(KEY).index.tolist()) if len(mc) else set()
        nl = int(sum(1 for k in lk.tolist() if k in mk)) if lk is not None else 0
        nan_l = (int((pd.to_numeric(legs[lcol], errors="coerce").isna()).sum())
                 if lcol is not None and len(legs) and lcol in legs.columns else None)
        out[name] = {"欠けた連鎖": int(len(mc)), "欠けた連鎖のレグ": nl,
                     "損益の列が NaN のレグ": nan_l}
    return out


def add_counts(total: dict, part: dict) -> None:
    for name, v in part.items():
        t = total.setdefault(name, {})
        for k, x in v.items():
            if x is not None:
                t[k] = t.get(k, 0) + x


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--orig", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--ignore", nargs="*", default=[],
                    help="比べない列(短い走らせでは period が元と違う: 作る/測る の境が違うため)")
    ap.add_argument("--skip-policy", nargs="*", default=[],
                    help="比べない方策(走らせの期間が違うと 規則_3択 の模型が元と違う)")
    ap.add_argument("--quotes-dir", default=str(REPO_ROOT / "data" / "c9_bookticker"),
                    help="気配の表の置き場(quote の走らせの in_px・out_px の突き合わせ)")
    args = ap.parse_args(argv)
    O, N = Path(args.orig) / "chunks", Path(args.new) / "chunks"
    meta = json.loads((Path(args.new) / "run_meta.json").read_text(encoding="utf-8"))
    quote = meta.get("走らせ直し_2026-10-06", {}).get("fill_side") == "quote"
    sfx = "_any" if quote else ""
    skip = set(args.skip_policy)
    out = {"quote": quote, "比べた置き場": f"chunks/*{sfx}/", "日": {}}
    bad = 0
    totals: dict = {}
    for day in days_between(args.start, args.end):
        bn = read(N / "bundles" / f"{day}.csv.gz")
        dres: dict = {}
        if day <= ORIG_LAST_DAY:
            bo = read_orig(O, "bundles", day)
            for name, alt in (("cascades", "cascades3"), ("legs", "legs3")):
                fo = cat([read_orig(O, name, day), read_orig(O, alt, day)])
                fn = cat([N / f"{name}{sfx}" / f"{day}.csv.gz",
                          N / f"{alt}{sfx}" / f"{day}.csv.gz"])
                cols = [c for c in fo.columns if c not in {"bundle_id", *args.ignore, *KEY}]
                r = compare(with_start(fo, bo), with_start(fn, bn), cols, skip)
                dres[name] = r
                bad += r["片方だけの行"] + sum(v if isinstance(v, int) else 1
                                           for v in r["違う値"].values())
        else:
            dres["元と比べない日(新しい出力だけ)"] = {
                "連鎖": int(len(cat([N / "cascades" / f"{day}.csv.gz",
                                    N / "cascades3" / f"{day}.csv.gz"]))),
                "レグ": int(len(cat([N / "legs" / f"{day}.csv.gz", N / "legs3" / f"{day}.csv.gz"])))}
        if quote:
            lg = with_start(cat([N / "legs" / f"{day}.csv.gz", N / "legs3" / f"{day}.csv.gz"]), bn)
            cs = with_start(cat([N / "cascades" / f"{day}.csv.gz",
                                 N / "cascades3" / f"{day}.csv.gz"]), bn)
            mv = main_value_checks(lg, cs)
            dres["主の値の検め"] = mv
            bad += sum(mv["外れ"].values())
            nd = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
            qc = quote_checks(lg, fill.QuoteBook.load(Path(args.quotes_dir), [day, nd]))
            dres["気配の表との突き合わせ"] = qc
            bad += sum(qc["外れ"].values())
            mc = missing_counts(lg, cs)
            dres["付け方ごとの値の欠け"] = mc
            add_counts(totals, mc)
        out["日"][day] = dres
    if quote:
        out["付け方ごとの値の欠け(合計)"] = totals
    out["違いと外れの合計"] = bad
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
