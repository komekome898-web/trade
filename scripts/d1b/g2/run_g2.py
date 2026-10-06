#!/usr/bin/env python3
"""前提の直接の測り(D1b)担当 G2: # 4・5・6・7・8・11 の台本の入口。

委任文: docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_d1b_impl.md
問いの立て方: docs/DISCUSSIONS/2026-10-06_held_batches/D1B_FRAMINGS.md
本走らせのコマンドと見込みの時間: docs/DISCUSSIONS/2026-10-06_held_batches/d1b/G2_jobs.md

    # 件数の数え上げ(値動き・損益を計算しない。COUNTS.md を書く)
    PYTHONPATH=src python3 scripts/d1b/g2/run_g2.py --mode counts --items 4,5,6,7,8,11
    # 本走らせ(表 = <#>_<カード>/TABLES.md・tables.json)
    PYTHONPATH=src python3 scripts/d1b/g2/run_g2.py --mode full --items 4,5,6,7,8,11

行に無かった境・向きはリードの決め(2026-10-06、委任の報告 7 への答え)で台本の中に固定した(引数で替えない):
  # 4 の比の区分の境 = 前半の 1 回の離れの比の 3 分位 / # 7 の前の向き = window_move、幅の帯の境 = 前半の起点の w の 3 分位 /
  # 6 の対照 = 同じ時刻の週明けでない平日(火〜金)の 1 時間の平均 / # 11 の # 8 の組 = jst_day・15 分・約定・1 分目を除く /
  # 5 の相関 = 時刻 t ごとの日をまたいだ相関と、その t の平均。
# 4 の 1 回の離れごとの行と # 7 の起点ごとの行は git に入れない(リードの決め 7 と、その後の答え): --records-dir(既定 /tmp/d1b_g2)に書く。

期間: 既定は各カードの CARD.md「測る期間」(# 4・5・7・8・11 = 2015-11-28T15:00Z〜2023-12-17T15:00Z、
# 6 = 2017-08-01T15:00Z〜2022-12-31T15:00Z)。--lo・--hi は短い期間の確かめ用(両方の期間に同じ値を当てる)。
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import g2lib as L  # noqa: E402

DIRS = {4: "4_card4", 5: "5_card5", 6: "6_card6", 7: "7_card7", 8: "8_card8", 11: "11_cards5_7_8"}


def g2_item11_cell():
    import g2_item11
    return g2_item11.C8_CELL


# 読み(委任の報告 7 の 6 で、リードがその形で可とした。COUNTS.md と TABLES.md の頭に 1 行ずつ書く)
READINGS = {
    4: ["読み: 1 回の離れ = 同じ側に離れた決定の足が続く間の最初の足(直前の決定の足が同じ側に離れていなければ新しい 1 回)。",
        "読み: 対照(離れていない足)の向き = 中心の側(終値 > 中心なら下へ、< なら上へ。= は除く)。",
        "読み: 戻る前の一番深い不利な点に、戻った足そのものは入れない(足の中の順序が分からないため)。",
        "読み: 窓は期間の始まりより前の足で埋めない(カードと同じ温まり)。"],
    5: ["読み: ずらした 23 窓も、朝の窓と同じ日本時間の平日の日から始める(k が 15 以上の窓は次の日にかかる)。"],
    6: ["経路(一番深い不利な点): btc は bitFlyer の 1 分足の高値・安値、usdjpy は USDJPY の 1 分足の高値・安値(同じファイルの high・low の列。"
        "系列の宣言 usdjpy_high・usdjpy_low は、終値と同じ遅れ 60 秒でこの台本の中で足した。CARD.md は変えていない)。"
        "前の版の「参照の系列が終値しか持たない」は誤りだった(ファイルには high・low の列がある。批評家 1 回目の [止める])。",
        "読み: 起点の行(週明けの行・対照の始まりの行。btc は起点の時刻で終わる足)の高値・安値は経路に入れない(足の中の順序が分からないため)。"],
    7: ["読み: 窓は期間の始まりより前の足で埋めない(カードと同じ温まり。1 週の窓は最初の 1 週を数えない)。"],
    8: ["読み: H 分後の値段 = 始まりが t + H 分 以上の最初の決定の足の始値(空きの長さに上限を置かない。カードの約定の決まり)。",
        "読み: セッションの平均は期間の始まりより前の足を使わない(カードと同じ。最初のセッションは期間の始まりから)。"],
    11: [],
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("counts", "full"), required=True)
    ap.add_argument("--items", default="4,5,6,7,8,11")
    ap.add_argument("--lo")
    ap.add_argument("--hi")
    ap.add_argument("--out-root", default=L.OUT_ROOT)
    ap.add_argument("--records-dir", default="/tmp/d1b_g2")
    a = ap.parse_args(argv)
    items = sorted({int(x) for x in a.items.split(",")})
    bad = set(items) - set(DIRS)
    if bad:
        raise SystemExit(f"G2 の項目ではない: {sorted(bad)}")
    lo = L.iso_ns(a.lo or L.PERIOD_FX[0])
    hi = L.iso_ns(a.hi or L.PERIOD_FX[1])
    lo6 = L.iso_ns(a.lo or L.PERIOD_C6[0])
    hi6 = L.iso_ns(a.hi or L.PERIOD_C6[1])
    c8cell = g2_item11_cell()
    t0 = time.time()
    def log(m):
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576
        print(f"[{time.time() - t0:7.1f}s 最大RSS {rss:5.2f}GB] {m}", flush=True)

    need_fx = True  # どの項目も bitFlyer FX の 1 分足を読む
    glo, ghi = (min(lo, lo6), max(hi, hi6)) if 6 in items else (lo, hi)
    log(f"読み込み {L.ns_iso(glo)} 〜 {L.ns_iso(ghi)}")
    G = L.load_grid(glo, ghi, log=log) if need_fx else None
    meta = {"command": " ".join(sys.argv), "mode": a.mode, "grid": G.meta if G else None}
    g = G.slice(lo, hi) if (G is not None and (lo, hi) != (glo, ghi)) else G
    days = L.Days.of(lo, hi)
    meta["days"] = days.describe()

    def out(item, stem, md, obj):
        d = os.path.join(a.out_root, DIRS[item])
        obj = dict(obj, meta=meta, readings=READINGS[item])
        if stem == "TABLES" and READINGS[item]:
            md = md[:1] + [""] + READINGS[item] + md[1:]
        L.write_out(d, stem, md, obj)
        log(f"書いた {d}/{stem}.md")

    head = lambda item, what: ([f"# # {item} 件数の数え上げ(値動き・損益を計算していない)", "",  # noqa: E731
                                f"コマンド: `{meta['command']}`", "", f"期間: {what}", ""] + READINGS[item] + [""])
    import g2_item4, g2_item5, g2_item6, g2_item7, g2_item8, g2_item11  # noqa: E401,E402
    res = {}
    if a.mode == "counts":
        for item in items:
            if item == 4:
                c = g2_item4.count(g, days)
                md = head(4, days.describe()) + c["lines"]
                out(4, "COUNTS", md, {"counts": {k: v for k, v in c.items() if k != "lines"}})
            elif item == 5:
                c = g2_item5.count(g, days)
                md = head(5, days.describe()) + c["lines"] + ["", f"窓ごとの 日×分: {json.dumps(c['per_shift'])}"]
                out(5, "COUNTS", md, {"per_shift": c["per_shift"]})
            elif item == 6:
                g6, d6 = G.slice(lo6, hi6), L.Days.of(lo6, hi6)
                u_t, u_c, u_h, u_l, man = g2_item6.load_usdjpy(lo6, hi6)
                c = g2_item6.count(g6, d6, u_t, u_c)
                out(6, "COUNTS", head(6, d6.describe()) + c["lines"], {"weeks": c["weeks"], "usdjpy_manifest": man})
            elif item == 7:
                c = g2_item7.count(g, days, lo, hi)
                md = head(7, days.describe()) + c["lines"] + ["", f"窓ごと: {json.dumps(c['per_window'])}"]
                out(7, "COUNTS", md, {"per_window": c["per_window"]})
            elif item == 8:
                c = g2_item8.count(g, days)
                md = head(8, days.describe()) + c["lines"] + ["", f"区切りごとの決定の分: {json.dumps(c['per_hour'])}"]
                out(8, "COUNTS", md, {"per_hour": c["per_hour"]})
            elif item == 11:
                cls = L.prev_day_class(g)
                c = g2_item11.count(days, cls)
                out(11, "COUNTS", head(11, days.describe()) + c["lines"], {})
            log(f"# {item} 数え上げ 済み")
        return 0
    # full
    if 4 in items:
        r = g2_item4.run(g, days)
        md, obj = g2_item4.tables(r)
        out(4, "TABLES", md, obj)
        os.makedirs(a.records_dir, exist_ok=True)
        rp = os.path.join(a.records_dir, "4_card4_episodes.csv.gz")
        g2_item4.write_records(rp, r["records"])
        log(f"書いた {rp}(git の外)")
    if 5 in items or 11 in items:
        res[5] = g2_item5.run(g, days)
        if 5 in items:
            out(5, "TABLES", *g2_item5.tables(res[5]))
    if 6 in items:
        g6, d6 = G.slice(lo6, hi6), L.Days.of(lo6, hi6)
        u_t, u_c, u_h, u_l, man = g2_item6.load_usdjpy(lo6, hi6)
        r = g2_item6.run(g6, d6, u_t, u_c, u_h=u_h, u_l=u_l)
        md, obj = g2_item6.tables(r)
        out(6, "TABLES", md, dict(obj, usdjpy_manifest=man))
        g2_item6.write_records(os.path.join(a.out_root, DIRS[6], "weeks.csv.gz"), r)
    if 7 in items or 11 in items:
        res[7] = g2_item7.run(g, days, lo, hi)
        if 7 in items:
            out(7, "TABLES", *g2_item7.tables(res[7]))
            os.makedirs(a.records_dir, exist_ok=True)
            rp7 = os.path.join(a.records_dir, "7_card7_origins.csv.gz")
            g2_item7.write_records(rp7, res[7])
            log(f"書いた {rp7}(git の外)")
    if 8 in items or 11 in items:
        hours = g2_item8.HOURS if 8 in items else (c8cell[0],)
        res[8] = g2_item8.run(g, days, hours, keep_days_for={c8cell})
        if 8 in items:
            out(8, "TABLES", *g2_item8.tables(res[8]))
    if 11 in items:
        cls = L.prev_day_class(g)
        out(11, "TABLES", *g2_item11.tables(days, cls, res[5], res[7], res[8]))
    log("済み")
    return 0


if __name__ == "__main__":
    sys.exit(main())
