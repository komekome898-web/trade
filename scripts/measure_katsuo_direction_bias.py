"""**買いに偏る原因を段階に分ける。**

2026-09-09、オーナーの問い:

> では買いに偏った原因について考察すべきではありませんか?
> ・BITMEX が下ヒゲをつけやすい
> ・BTC の市場自体が下ヒゲをつけやすい
> ・ロジック自体が買いの頻度が多くなっている

**この 3 つは、測る場所が違う。** 建玉の買い比率は、次の段を順に通った結果である。

    段 A  足そのもの      … 下ヒゲ > 上ヒゲ の足の割合(門も強さも建玉も関係ない)
    段 B  門を通した後    … 長さの門 s/b を通ったシグナルの買い割合
    段 C  強さで絞った後  … 強い / 弱い それぞれの買い割合
    段 D  建玉機械の後    … 実際に建てた新規建玉の買い割合(これが 54.6% などの出所)

各段の**増分**が、その段の寄与である。

- 段 A で既に偏っていれば **市場・取引所の性質**(オーナーの候補 1・2)
- 段 A では偏らず段 B・C・D で偏るなら **ロジックの性質**(候補 3)

候補 1(BitMEX 固有)と候補 2(BTC 一般)を分けるには**別の取引所の同時期**が要る。
`backtest_data/binance_BTCUSDT_1m_20170801_20231231/`(Binance 現物 BTCUSDT の 1 分足、
2017-08-17 〜)を使い、**同じ期間に切り揃えて**段 A・段 B を並べる。

**この比較の限界(結果と一緒に必ず書くこと)**:

- BitMEX XBTUSD は**レバレッジ付き無期限先物**、Binance BTCUSDT は**現物**。
  「取引所の違い」と「先物と現物の違い」は分かれていない。
- 呼値が違う(BitMEX 0.5 USD / Binance 0.01 USD)。原典は `int()` で切り捨てて
  比較するので、**呼値の差が同点の出方を変える**。そのため段 A は
  **`int()` あり / なしの両方**を出す。
- 2017 年は Binance が 8/17 開始なので、比較窓は 2017-08-17 以降に切り揃える。

    PYTHONPATH=src python scripts/measure_katsuo_direction_bias.py
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from datetime import date, datetime, timezone
from pathlib import Path

import k1_source
import measure_katsuo_dispersion as base
import measure_katsuo_effect as eff

REPO = Path(__file__).resolve().parents[1]
BINANCE = REPO / "backtest_data" / "binance_BTCUSDT_1m_20170801_20231231"

EXPLORE_START = date(2017, 1, 1)
EXPLORE_END = date(2019, 12, 31)

# Binance BTCUSDT の最初の足。比較はここから先だけで行う。
MATCH_FROM = int(datetime(2017, 8, 17, 4, 0, tzinfo=timezone.utc).timestamp())

FEET = (1, 3, 5, 15, 30, 60)


# ------------------------------------------------------------------ 段 A ----

def stage_a(bars, years=None):
    """足そのものの向きの偏り。**門も強さも建玉も通していない。**

    `int()` で切り捨てて比べるのが原典。切り捨ては呼値の粗い取引所で同点を増やすので、
    切り捨て無しの比較も並べて出す。
    """
    out = {
        "bars": len(bars), "signed": 0,
        "trunc": {"buy": 0, "sell": 0, "tie": 0},   # int() あり(原典)
        "raw": {"buy": 0, "sell": 0, "tie": 0},     # int() なし
        "sum_top_bp": 0.0, "sum_under_bp": 0.0,
        "bull": 0, "bear": 0,
        "per_year": {},
    }
    for i, (_ts, o, h, l, c) in enumerate(bars):
        candle = c - o
        if candle == 0 or c <= 0:
            continue
        csign = 1 if candle > 0 else -1
        out["signed"] += 1
        out["bull" if csign == 1 else "bear"] += 1
        top, under = (h - c, o - l) if csign == 1 else (h - o, c - l)
        out["sum_top_bp"] += top / c * 1e4
        out["sum_under_bp"] += under / c * 1e4
        if int(top) > int(under):
            out["trunc"]["sell"] += 1
        elif int(under) > int(top):
            out["trunc"]["buy"] += 1
        else:
            out["trunc"]["tie"] += 1
        if years is not None:
            y = out["per_year"].setdefault(
                str(years[i]),
                {"buy": 0, "sell": 0, "tie": 0, "n": 0, "sum_top_bp": 0.0, "sum_under_bp": 0.0})
            y["n"] += 1
            y["sum_top_bp"] += top / c * 1e4
            y["sum_under_bp"] += under / c * 1e4
            y["sell" if int(top) > int(under) else
              ("buy" if int(under) > int(top) else "tie")] += 1
        if top > under:
            out["raw"]["sell"] += 1
        elif under > top:
            out["raw"]["buy"] += 1
        else:
            out["raw"]["tie"] += 1
    return out


# ------------------------------------------------------------ 段 B・段 C ----

def stage_bc(bars, small, big, years=None):
    """門を通した後(段 B)と、強さで割った後(段 C)の買い割合。"""
    sg = eff.signals(bars, small, big)
    out = {"sig_buy": 0, "sig_sell": 0,
           "strong_buy": 0, "strong_sell": 0,
           "weak_buy": 0, "weak_sell": 0,
           "per_year": {}}
    for i, (sig, _lc, _cs, strength) in enumerate(sg):
        if sig == 0:
            continue
        side = "buy" if sig == 1 else "sell"
        out[f"sig_{side}"] += 1
        out[f"{strength}_{side}"] += 1
        if years is not None:
            y = out["per_year"].setdefault(str(years[i]), {"buy": 0, "sell": 0})
            y[side] += 1
    return sg, out


# ------------------------------------------------------------------ 段 D ----

def stage_d(bars, sigs, keep=None, years=None):
    """建玉機械を回し、**実際に建てた新規建玉**の向きを数える。

    `measure_katsuo_effect.simulate` と**同じ 4 分岐**をたどるが、返すのは建玉の向きだけ。
    ドテンで建て直した分も新規建玉として数える(実際に持ったので)。

    **数える単位は「建てた足」である。** 決済した足ではない。年ごとに割るときも
    **入口の年**で割る(`measure_katsuo_effect` の `per_year` と同じ規則)。
    """
    pos = 0
    lcline = 0.0
    n = {"buy": 0, "sell": 0, "per_year": {}}

    def opened(i, sig):
        side = "buy" if sig == 1 else "sell"
        n[side] += 1
        if years is not None:
            n["per_year"].setdefault(str(years[i]), {"buy": 0, "sell": 0})[side] += 1

    for i, (sig, lc, csign, strength) in enumerate(sigs):
        c = bars[i][4]
        if c <= 0:
            continue
        actionable = sig != 0 and (keep is None or strength == keep)
        if not actionable:
            if pos != 0 and csign == -pos:
                if (pos == 1 and c <= lcline) or (pos == -1 and c >= lcline):
                    pos = 0
            continue
        if pos == sig:
            lcline = lc
        elif pos == -sig:
            pos = 0
            if strength == "strong":
                pos, lcline = sig, lc
                opened(i, sig)
        else:
            pos, lcline = sig, lc
            opened(i, sig)
    return n


# ------------------------------------------------------------- Binance -----

def load_binance_minutes(years):
    rows = []
    for y in years:
        path = BINANCE / f"binance_BTCUSDT_1m_{y}.csv.gz"
        if not path.exists():
            continue
        with gzip.open(path, "rt", newline="") as fh:
            reader = csv.reader(fh)
            next(reader, None)
            for r in reader:
                ts = int(datetime.fromisoformat(r[0]).timestamp())
                rows.append((ts, float(r[1]), float(r[2]), float(r[3]), float(r[4])))
    rows.sort(key=lambda x: x[0])
    return rows


# ------------------------------------------------------------------ 本体 ----

def share(d, a, b):
    tot = d[a] + d[b]
    return round(100.0 * d[a] / tot, 2) if tot else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--feet", type=int, nargs="+", default=list(FEET))
    ap.add_argument("--out", default=None)
    k1_source.add_source_args(ap)
    args = ap.parse_args()
    start, end = k1_source.resolve_range(args)
    if args.out is None:
        args.out = str(k1_source.out_dir(args.source) / "direction_bias.json")

    print(f"{args.source} 区間 {start} 〜 {end}(BitMEX の判定区間 2020-2021 には触れない)")
    seconds = k1_source.load_bars(args.source, start, end)
    print(f"  {args.source} バー {len(seconds):,} 行")
    # 取引所の比較(同窓の BitMEX vs Binance)は BitMEX を主データにしたときだけ行う。
    # Binance を主データにしたときは主データそのものが Binance なので、この比較は作らない
    venue_compare = args.source == "bitmex"
    if venue_compare:
        bmins = load_binance_minutes(range(start.year, end.year + 1))
        print(f"  Binance 分バー {len(bmins):,} 行(最初 "
              f"{datetime.utcfromtimestamp(bmins[0][0])} / 最後 "
              f"{datetime.utcfromtimestamp(bmins[-1][0])})")

    gs = eff.gates()
    result = {"feet": {}, "venue": {}, "match_from": MATCH_FROM,
              "source": args.source, "explore": [start.isoformat(), end.isoformat()],
              "load": k1_source.last_load}

    for foot in args.feet:
        bars = base.fold(seconds, foot)
        years = [datetime.utcfromtimestamp(b[0]).year for b in bars]
        a = stage_a(bars, years)
        cells = {}
        for g in gs:
            sg, bc = stage_bc(bars, g[0], g[1], years)
            bc["entry_both"] = stage_d(bars, sg, None, years)
            bc["entry_strong"] = stage_d(bars, sg, "strong", years)
            bc["entry_weak"] = stage_d(bars, sg, "weak", years)
            cells[eff.label(g)] = bc
        result["feet"][str(foot)] = {"stage_a": a, "gates": cells}

        if not venue_compare:
            print(f"  {foot:>3}分 | 段A 買い {share(a['trunc'], 'buy', 'sell'):.2f}%"
                  f"(切捨なし {share(a['raw'], 'buy', 'sell'):.2f}%)"
                  f" | 上ヒゲ平均 {a['sum_top_bp'] / max(a['signed'], 1):.1f}bp"
                  f" 下ヒゲ平均 {a['sum_under_bp'] / max(a['signed'], 1):.1f}bp")
            continue

        # ---- 取引所の比較(同じ窓に切り揃える)
        bm = [b for b in bars if b[0] >= MATCH_FROM]
        bn = base.fold([r for r in bmins if r[0] >= MATCH_FROM], foot)
        v = {"bitmex": {"stage_a": stage_a(bm)}, "binance": {"stage_a": stage_a(bn)}}
        for name, bb in (("bitmex", bm), ("binance", bn)):
            v[name]["gates"] = {eff.label(g): stage_bc(bb, g[0], g[1])[1] for g in gs}
        result["venue"][str(foot)] = v

        print(f"  {foot:>3}分 | 段A 買い {share(a['trunc'], 'buy', 'sell'):.2f}%"
              f"(切捨なし {share(a['raw'], 'buy', 'sell'):.2f}%)"
              f" | 上ヒゲ平均 {a['sum_top_bp'] / max(a['signed'], 1):.1f}bp"
              f" 下ヒゲ平均 {a['sum_under_bp'] / max(a['signed'], 1):.1f}bp"
              f" | 同窓 BitMEX {share(v['bitmex']['stage_a']['trunc'], 'buy', 'sell'):.2f}%"
              f" / Binance {share(v['binance']['stage_a']['trunc'], 'buy', 'sell'):.2f}%")

    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n→ {args.out}")


if __name__ == "__main__":
    main()
