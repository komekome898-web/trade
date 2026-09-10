"""`robustness.json`(K1 深掘り §1 の診断)を Markdown の表にする。**手打ちしない。**

規約 `.claude/skills/research-protocol` §1.2「数字は生成であって入力ではない」。

**族の全水準を載せる**(足 6 × 強さ strong/weak を必ず全部。切り詰めない)。
h は既定で 1/3/5、`--h` で全ホライズンも出せる。

    PYTHONPATH=src:scripts python scripts/render_k1_robustness.py \
        --dir docs/PHASE2/K1/binance > docs/PHASE2/K1/binance/ROBUSTNESS_TABLES.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LABEL = {"strong": "強い", "weak": "弱い", "both": "両方"}
HOURBIN = {str(i): f"{i * 3:02d}-{i * 3 + 3:02d}" for i in range(8)}
WDAY = {"0": "月", "1": "火", "2": "水", "3": "木", "4": "金", "5": "土", "6": "日"}


def star(ci) -> str:
    """95% 区間が 0 を跨がないなら `*`。"""
    if not ci or ci[0] is None or ci[1] is None:
        return ""
    return "*" if (ci[0] > 0 or ci[1] < 0) else ""


def fm(v, d=2):
    return "—" if v is None else f"{v:+.{d}f}"


def fu(v, d=2):
    return "—" if v is None else f"{v:.{d}f}"


def mc(d):
    """`{mean_bp, ci95_bp, n}` を 1 マスに。"""
    if not d:
        return "—"
    return f"{fm(d.get('mean_bp'))}{star(d.get('ci95_bp'))} ({d.get('n', 0):,})"


def ci(d, key="ci95_bp", mark=True):
    v = d.get(key) if d else None
    if not v or v[0] is None:
        return "—"
    return f"[{v[0]:+.2f}, {v[1]:+.2f}]{star(v) if mark else ''}"


def rows(doc, gate, strengths, h):
    """(足, 強さ, セル) を族の順に。存在しないセルは飛ばす。"""
    for foot in doc["feet"]:
        for st in strengths:
            c = doc["cells"].get(f"{foot}|{gate}|{st}|{h}")
            if c:
                yield foot, st, c


def table(header, lines):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += lines
    return "\n".join(out)


def head(foot, st):
    return [f"{foot} 分", LABEL[st]]


# ---------------------------------------------------------------- 表

def t_d1(doc, gate, strengths, hs):
    lines = []
    for foot in doc["feet"]:
        for st in strengths:
            c0 = None
            cells = []
            for h in hs:
                c = doc["cells"].get(f"{foot}|{gate}|{st}|{h}")
                c0 = c0 or c
                cells.append(f"{fm(c['d1']['mean_bp'])}{star(c['d1']['ci95_bp'])} "
                             f"{ci(c['d1'], mark=False)}" if c else "—")
            if c0:
                lines.append("| " + " | ".join(head(foot, st)
                                               + [f"{c0['d1']['n']:,}", f"{c0['d1']['days']:,}"]
                                               + cells) + " |")
    return table(["足", "強さ", "n(h=先頭)", "日数"] + [f"h={h}" for h in hs], lines)


def t_d2(doc, gate, strengths, h):
    lines = []
    for foot, st, c in rows(doc, gate, strengths, h):
        d1, d2 = c["d1"], c["d2"]
        lines.append("| " + " | ".join(
            head(foot, st) + [f"{d1['n']:,}",
                              f"{d2['blocks']['day']:,}/{d2['blocks']['week']:,}/{d2['blocks']['month']:,}",
                              fm(d1["mean_bp"]), ci(d1),
                              ci(d2, "day_1000"), ci(d2, "week_200"),
                              ci(d2, "week_1000"), ci(d2, "month_200")]) + " |")
    return table(["足", "強さ", "n", "日/週/月ブロック数", "平均 bp",
                  "日 200(D1)", "日 1000", "週 200", "週 1000", "月 200"], lines)


def t_d3(doc, gate, strengths, hs):
    lines = []
    for foot in doc["feet"]:
        for st in strengths:
            cells = []
            for h in hs:
                c = doc["cells"].get(f"{foot}|{gate}|{st}|{h}")
                d3 = c and c.get("d3")
                if not c:
                    cells += ["—", "—"]
                elif not d3:
                    cells += [fm(c["d1"]["mean_bp"]), "—"]
                else:
                    cells += [fm(c["d1"]["mean_bp"]),
                              f"{fm(d3['mean_bp'])}{star(d3['ci95_bp'])}"]
            lines.append("| " + " | ".join(head(foot, st) + cells) + " |")
    cols = []
    for h in hs:
        cols += [f"h={h} D1", f"h={h} 遅らせ"]
    return table(["足", "強さ"] + cols, lines)


def t_d4(doc, gate, strengths, hs):
    lines = []
    for foot in doc["feet"]:
        for st in strengths:
            cells = []
            share = "—"
            for h in hs:
                c = doc["cells"].get(f"{foot}|{gate}|{st}|{h}")
                if not c:
                    cells += ["—", "—"]
                    continue
                d4 = c["d4"]
                share = f"{d4['stale_share'] * 100:.3f}%" if d4["stale_share"] is not None else "—"
                cells += [fm(c["d1"]["mean_bp"]),
                          f"{fm(d4['mean_bp'])}{star(d4['ci95_bp'])}"]
            lines.append("| " + " | ".join(head(foot, st) + [share] + cells) + " |")
    cols = []
    for h in hs:
        cols += [f"h={h} 全部", f"h={h} 除外後"]
    return table(["足", "強さ", "古い終値の割合"] + cols, lines)


def t_d4_year(doc, gate, strengths, h, years):
    lines = []
    for foot, st, c in rows(doc, gate, strengths, h):
        py = c["d4"]["per_year"]
        cells = []
        for y in years:
            p = py.get(y)
            cells.append("—" if not p else
                         f"{p['stale_share'] * 100:.2f}% / {fm(p['mean_bp'])}")
        lines.append("| " + " | ".join(head(foot, st) + cells) + " |")
    return table(["足", "強さ"] + [f"{y}(割合/除外後 bp)" for y in years], lines)


def t_d5(doc, gate, strengths, hs):
    lines = []
    for foot in doc["feet"]:
        for st in strengths:
            cells = []
            ny = "—"
            for h in hs:
                c = doc["cells"].get(f"{foot}|{gate}|{st}|{h}")
                if not c:
                    cells += ["—", "—"]
                    continue
                d5 = c["d5"]
                ny = str(d5["n_years"])
                cells += [str(d5["same_sign_years"]["week_parity"]),
                          str(d5["same_sign_years"]["half"])]
            lines.append("| " + " | ".join(head(foot, st) + [ny] + cells) + " |")
    cols = []
    for h in hs:
        cols += [f"h={h} 週奇偶", f"h={h} 上下半期"]
    return table(["足", "強さ", "年数"] + cols, lines)


def t_bins(doc, gate, strengths, h, path, names, extra_cols=()):
    """`cell[path]['bins']` の層を横に並べる汎用の表。"""
    lines = []
    for foot, st, c in rows(doc, gate, strengths, h):
        b = c[path]["bins"]
        cells = [mc(b.get(k)) for k in names]
        for col in extra_cols:
            cells.append(" / ".join(fu(b[k][col]) if k in b else "—" for k in names))
        lines.append("| " + " | ".join(head(foot, st) + cells) + " |")
    return table(["足", "強さ"] + list(names.values() if isinstance(names, dict) else names)
                 + [f"{c}(層の順)" for c in extra_cols], lines)


def t_bins_year(doc, gate, strengths, h, path, keys, years):
    lines = []
    for foot, st, c in rows(doc, gate, strengths, h):
        py = c[path]["per_year"]
        for y in years:
            b = py.get(y, {})
            if not b:
                continue
            lines.append("| " + " | ".join(head(foot, st) + [y]
                                           + [mc(b.get(k)) for k in keys]) + " |")
    return table(["足", "強さ", "年"] + list(keys), lines)


def t_d10(doc, gate, years):
    lines = []
    for foot in doc["feet"]:
        comp = doc["per_year_components"].get(f"{foot}|{gate}")
        if not comp:
            continue
        for y in years:
            p = comp.get(y)
            if not p:
                continue
            lines.append("| " + " | ".join([
                f"{foot} 分", y, f"{p['n_bars']:,}", fu(p["realized_vol_bp"]),
                f"{p['n_signals']:,}",
                "—" if p["signal_share"] is None else f"{p['signal_share'] * 100:.2f}%",
                fu(p["mean_wbp"]), fu(p["mean_abs_body_bp"]), f"{p['n_strong']:,}",
                "—" if p["strong_body_gt_wick_share"] is None
                else f"{p['strong_body_gt_wick_share'] * 100:.2f}%"]) + " |")
    return table(["足", "年", "全足数", "realized vol bp", "シグナル数", "通過率",
                  "平均ヒゲ bp", "平均 実体 bp(絶対値)", "強い数", "実体>ヒゲ(強い内)"], lines)


def t_d11(doc, gate, strengths, h):
    lines = []
    for foot, st, c in rows(doc, gate, strengths, h):
        d = c["d11"]
        lines.append("| " + " | ".join(head(foot, st) + [f"{d['n']:,}", fm(d["mean_bp"]),
                                                         fm(d["trim_1pct_bp"]),
                                                         fm(d["winsor_1pct_bp"]),
                                                         fm(d["trim_5pct_bp"]),
                                                         fm(d["winsor_5pct_bp"])]) + " |")
    return table(["足", "強さ", "n", "平均", "1% トリム", "1% ウィンザー",
                  "5% トリム", "5% ウィンザー"], lines)


def t_d11_year(doc, gate, strengths, h, years):
    lines = []
    for foot, st, c in rows(doc, gate, strengths, h):
        py = c["d11"]["per_year"]
        for y in years:
            p = py.get(y)
            if not p:
                continue
            lines.append("| " + " | ".join(head(foot, st) + [y, f"{p['n']:,}",
                                                             fm(p["mean_bp"]),
                                                             fm(p["trim_1pct_bp"]),
                                                             fm(p["winsor_1pct_bp"]),
                                                             fm(p["trim_5pct_bp"]),
                                                             fm(p["winsor_5pct_bp"])]) + " |")
    return table(["足", "強さ", "年", "n", "平均", "1% トリム", "1% ウィンザー",
                  "5% トリム", "5% ウィンザー"], lines)


# ---------------------------------------------------------------- 本体

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default=str(REPO / "docs" / "PHASE2" / "K1"))
    ap.add_argument("--src", default=None)
    ap.add_argument("--h", type=int, nargs="+", default=[1, 3, 5])
    ap.add_argument("--gates", nargs="+", default=None)
    ap.add_argument("--strengths", nargs="+", default=["strong", "weak"])
    ap.add_argument("--no-year-tables", action="store_true",
                    help="年別の表(D4/D8/D9/D9b/D11)を省く")
    args = ap.parse_args()
    src = Path(args.src) if args.src else Path(args.dir) / "robustness.json"
    doc = json.loads(src.read_text("utf-8"))
    gates = args.gates or doc["gates"]
    hs = [h for h in args.h if h in doc["horizons"]]
    years = sorted({y for c in doc["cells"].values() for y in c["d1"]["per_year"]})
    wick = [f"[{a:g},{b:g})" for a, b in zip(doc["bootstrap"]["wick_bins"],
                                             doc["bootstrap"]["wick_bins"][1:])]
    wick.append(f"[{doc['bootstrap']['wick_bins'][-1]:g},+)")
    ratio = [f"[{a:g},{b:g})" for a, b in zip(doc["bootstrap"]["ratio_bins"],
                                              doc["bootstrap"]["ratio_bins"][1:])]
    ratio.append(f"[{doc['bootstrap']['ratio_bins'][-1]:g},+)")

    gate_ok = sum(1 for x in doc["reproduction_gate"] if x["ok"])
    gate_n = sum(1 for x in doc["reproduction_gate"] if x["ok"] is not None)
    print(f"# K1 深掘り §1 — 診断の表({doc['source']})\n")
    print(f"出所 `{doc['source']}` / 期間 {doc['explore'][0]} 〜 {doc['explore'][1]} / "
          f"セル {len(doc['cells'])} 件 / 種 {doc['seed']}。\n")
    print(f"**D1 の再現ゲート: {gate_ok}/{gate_n} 一致**"
          f"(参照 `{Path(doc['reference']).name}`。n・平均・区間・年別が全部一致)。\n")
    print("すべての表で `*` = その 95% 区間が 0 を跨がない。単位は bp、経費は引いていない。"
          "`(n)` は件数。**足 6 × 強さ 2 を全部載せている(切り詰めていない)。**\n")
    print(f"表示するホライズン: {', '.join('h=' + str(h) for h in hs)}"
          f"(族は {', '.join(str(h) for h in doc['horizons'])})。\n")

    for gate in gates:
        print(f"\n---\n\n# 門 `{gate}`\n")

        print("## D1 基準線(第 4 部と同じ量・同じ乱数)\n")
        print("シグナルの足から h 本先の終値までの符号付きリターン。"
              "区間は日ブロックブートストラップ 200 回。\n")
        print(t_d1(doc, gate, args.strengths, doc["horizons"]))

        print("\n## D2 区間の頑健性(ブロックの取り方を変える)\n")
        print("同じ材料・同じ平均に対して、復元抽出するブロックを 日 / 週 / 月 に変えたときの"
              "95% 区間。`*` は 0 を跨がない。\n")
        for h in hs:
            print(f"\n**h={h}**\n")
            print(t_d2(doc, gate, args.strengths, h))

        print("\n## D3 1 本遅らせた入口\n")
        print("`sig × (close[i+h]/close[i+1] − 1) × 10⁴`。シグナル足の終値という"
              "1 つのプリントを経由しない(h≥2 のみ)。\n")
        print(t_d3(doc, gate, args.strengths, hs))

        print("\n## D4 古い終値の除外\n")
        print("`close[i] == close[i−1]` のシグナル足を落としたときの平均。\n")
        print(t_d4(doc, gate, args.strengths, hs))
        if not args.no_year_tables:
            for h in hs:
                print(f"\n**h={h} 年別(古い終値の割合 / 除外後の平均 bp)**\n")
                print(t_d4_year(doc, gate, args.strengths, h, years))

        print("\n## D5 分割の一致(年内)\n")
        print("年ごとに ISO 週の奇偶 / 上半期・下半期 で 2 つに割り、"
              "**2 つの平均の符号が一致した年の数**。\n")
        print(t_d5(doc, gate, args.strengths, hs))

        print("\n## D6 時間帯(UTC 3 時間 × 8 区分)\n")
        fb = ", ".join(HOURBIN[str(b)] for b in
                       doc["cells"][next(iter(doc["cells"]))]["d6"]["funding_bins"])
        print(f"各マスは 平均 bp と (件数)。BitMEX の資金調達時刻(04/12/20 UTC)を含む区分: {fb}。\n")
        for h in hs:
            print(f"\n**h={h}**\n")
            print(t_bins(doc, gate, args.strengths, h, "d6", HOURBIN))

        print("\n## D7 曜日(UTC)\n")
        print("各マスは 平均 bp と (件数)。\n")
        for h in hs:
            print(f"\n**h={h}**\n")
            print(t_bins(doc, gate, args.strengths, h, "d7", WDAY))

        print("\n## D8 ボラ区分(直前 100 本、先読み無し)\n")
        print("`vol_prev` = 直前 100 本の |終値対数リターン| の平均 bp。"
              "三分位は **足 × 門 × 全シグナル足(strong+weak)の全期間分布**で切る。\n")
        for h in hs:
            print(f"\n**h={h}**\n")
            print(t_bins(doc, gate, args.strengths, h, "d8",
                         {"low": "低", "mid": "中", "high": "高"},
                         extra_cols=("mean_vol_prev", "mean_wbp")))
            if not args.no_year_tables:
                print(f"\n**h={h} 年 × ボラ区分**\n")
                print(t_bins_year(doc, gate, args.strengths, h, "d8",
                                  ["low", "mid", "high"], years))

        print("\n## D9 ヒゲ層\n")
        print("層は `WICK_BINS`。各マスは 平均 bp と (件数)。\n")
        for h in hs:
            print(f"\n**h={h}**\n")
            print(t_bins(doc, gate, args.strengths, h, "d9", wick,
                         extra_cols=("mean_wbp", "mean_r_over_wbp")))
            print("\n`mean_r_over_wbp` は `r_h / wbp` の平均。**派生量**であって bp ではない。\n")
            if not args.no_year_tables:
                print(f"\n**h={h} 年 × ヒゲ層**\n")
                print(t_bins_year(doc, gate, args.strengths, h, "d9", wick, years))

        print("\n## D9b 実体比の層\n")
        print("層は `RATIO_BINS`(`|実体| / 勝った側のヒゲ`)。各マスは 平均 bp と (件数)。\n")
        for h in hs:
            print(f"\n**h={h}**\n")
            print(t_bins(doc, gate, args.strengths, h, "d9b", ratio,
                         extra_cols=("mean_ratio",)))
            if not args.no_year_tables:
                print(f"\n**h={h} 年 × 実体比の層**\n")
                print(t_bins_year(doc, gate, args.strengths, h, "d9b", ratio, years))

        print("\n## D10 年の成分表\n")
        print("**引き算をしない。**横に並べるだけ。realized vol は"
              "**全足**(シグナルの有無に関わらず)の |bp リターン| の平均。\n")
        print(t_d10(doc, gate, years))

        print("\n## D11 裾を落とした平均\n")
        print("両側 1% / 5% をトリム(落とす)/ ウィンザー(端の値に丸める)した平均。区間は出さない。\n")
        for h in hs:
            print(f"\n**h={h}**\n")
            print(t_d11(doc, gate, args.strengths, h))
            if not args.no_year_tables:
                print(f"\n**h={h} 年別**\n")
                print(t_d11_year(doc, gate, args.strengths, h, years))


if __name__ == "__main__":
    main()
