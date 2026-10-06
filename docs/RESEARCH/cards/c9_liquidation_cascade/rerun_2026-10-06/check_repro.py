#!/usr/bin/env python3
"""カード 9 の走らせ直し(2026-10-06)の再現の検め: 新しい走らせの日ごとの連鎖・レグの行が、
元の走らせ(`data/c9_run_a/full_20230625_20241014/chunks/`)の同じ日の行と同じかを見る。

委任文: `docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_rerun_impl.md`(担当 C の (4))。

- 突き合わせの鍵: (side, gap_s, start_ms, delay_s, policy, type)。`bundle_id` は読んだ範囲の
  束の通し番号を含むので、短い走らせでは元と違う(鍵に使わない、比べない)。`start_ms` は
  `chunks/bundles/<日>.csv.gz` から引く。レグは鍵の中の並び順(書かれた順)で突き合わせる。
- 比べる列: 元の見出しの列すべて(`bundle_id` と `--ignore` で外した列を除く)。値は CSV の文字列
  のまま(どちらも `%.8g` で書いてある)。
- 新しい走らせが `--fill-side taker` のときは、`pnl_bp` の代わりに `pnl_bp_anyside`
  (1 回目 = どちらの側でも)を元の `pnl_bp` と、`missing` の代わりに `missing_anyside` を元の
  `missing` と比べる(`hold_s` などは約定の側によらない列なのでそのまま比べる)。
  taker の `pnl_bp` が元と違う行の数は「参考」として数えるだけ。

    python3 docs/RESEARCH/cards/c9_liquidation_cascade/rerun_2026-10-06/check_repro.py \
        --orig data/c9_run_a/full_20230625_20241014 --new <新しい走らせ> \
        --start 2023-07-01 --end 2023-07-02 --ignore period --skip-policy 規則_3択

違いが 1 つでもあれば終了コード 1。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

KEY = ["side", "gap_s", "start_ms", "delay_s", "policy", "type"]


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


def with_start(df: pd.DataFrame, bundles: pd.DataFrame) -> pd.DataFrame:
    if not len(df):
        return df
    m = dict(zip(bundles["bundle_id"], bundles["start_ms"]))
    df = df.copy()
    df["start_ms"] = df["bundle_id"].map(m)
    if "side" not in df.columns:
        sm = dict(zip(bundles["bundle_id"], bundles["side"]))
        df["side"] = df["bundle_id"].map(sm)
    if df["start_ms"].isna().any():
        raise SystemExit("[止め] 束の表に無い bundle_id がある")
    df["_ord"] = df.groupby(KEY, sort=False).cumcount().astype(str)
    return df


def compare(orig: pd.DataFrame, new: pd.DataFrame, cols: list[str], taker: bool,
            skip_policy: set) -> dict:
    if len(orig):
        orig = orig[~orig["policy"].isin(skip_policy)]
    if len(new):
        new = new[~new["policy"].isin(skip_policy)]
    k = KEY + ["_ord"]
    res = {"元の行": int(len(orig)), "新しい行": int(len(new))}
    if not len(orig) and not len(new):
        return res | {"突き合わせた行": 0, "片方だけの行": 0, "違う値": {}}
    j = orig.merge(new, on=k, how="outer", suffixes=("_o", "_n"), indicator=True)
    res["片方だけの行"] = int((j["_merge"] != "both").sum())
    b = j[j["_merge"] == "both"]
    res["突き合わせた行"] = int(len(b))
    diff = {}
    for c in cols:
        cn = c
        if taker and c == "pnl_bp":
            cn = "pnl_bp_anyside"
        if taker and c == "missing":
            cn = "missing_anyside"
        lo = f"{c}_o" if f"{c}_o" in b.columns else c
        ln = f"{cn}_n" if f"{cn}_n" in b.columns else cn
        if lo not in b.columns or ln not in b.columns:
            diff[c] = "列が無い"
            continue
        n = int((b[lo].astype(str) != b[ln].astype(str)).sum())
        if n:
            diff[c] = n
    res["違う値"] = diff
    if taker and "pnl_bp_n" in b.columns:
        res["参考_takerのpnl_bpが元と違う行"] = int((b["pnl_bp_o"] != b["pnl_bp_n"]).sum())
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--orig", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--ignore", nargs="*", default=[],
                    help="比べない列(短い走らせでは period が元と違う: 作る/測る の境が違うため)")
    ap.add_argument("--skip-policy", nargs="*", default=[],
                    help="比べない方策(短い走らせでは 規則_3択 の模型が元と違う)")
    args = ap.parse_args(argv)
    O, N = Path(args.orig) / "chunks", Path(args.new) / "chunks"
    meta = json.loads((Path(args.new) / "run_meta.json").read_text(encoding="utf-8"))
    taker = meta.get("走らせ直し_2026-10-06", {}).get("fill_side") == "taker"
    skip = set(args.skip_policy)
    out = {"taker": taker, "日": {}}
    bad = 0
    for day in days_between(args.start, args.end):
        bo, bn = read(O / "bundles" / f"{day}.csv.gz"), read(N / "bundles" / f"{day}.csv.gz")
        dres = {}
        for name, alt in (("cascades", "cascades3"), ("legs", "legs3")):
            parts_o = [read(O / d / f"{day}.csv.gz") for d in (name, alt)]
            parts_n = [read(N / d / f"{day}.csv.gz") for d in (name, alt)]
            fo = pd.concat([p for p in parts_o if len(p)], ignore_index=True) \
                if any(len(p) for p in parts_o) else pd.DataFrame()
            fn = pd.concat([p for p in parts_n if len(p)], ignore_index=True) \
                if any(len(p) for p in parts_n) else pd.DataFrame()
            cols = [c for c in fo.columns if c not in {"bundle_id", *args.ignore, *KEY}]
            r = compare(with_start(fo, bo), with_start(fn, bn), cols, taker, skip)
            dres[name] = r
            bad += r["片方だけの行"] + sum(v if isinstance(v, int) else 1
                                       for v in r["違う値"].values())
        out["日"][day] = dres
    out["違いの合計"] = bad
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
