"""第 5 周の表を JSON から生成する(手打ちしない)。`ROUND5_PREREG.md` §3:

    表 M-a: (a') 門 `s19/b24` 理由別の分解(足 × 強さ)。年別の出口の遅れ(理由別)も付ける
    表 M-b: (a') 全 13 門 × 足 6、強さ「両方」「弱い」: 理由別の出口の遅れ
    表 M-c: (c)-iii 層別(向き・比・ヒゲ長・ボラ・年・保有・理由)
    表 M-d: (c)-iii 経路(全体・決済理由別・局所ボラ別)

土台 2(原典 / H1+H2a)× 取引所 2。Binance は 2017 が終値の古い足を含むため、
年別の内訳が出る場所には 2017 を除いた値も並べる(D6.5.3)。

    PYTHONPATH=src:scripts python scripts/render_k1_round5.py > docs/PHASE2/K1/ROUND5_TABLES.md
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "docs" / "PHASE2" / "K1"
VENUES = (("BitMEX", K1), ("Binance", K1 / "binance"))
BASES = (("原典", ""), ("H1+H2a", "_flip_noinval"))
RESIDUAL_BASES = (("H1", "_flipbody"), ("H1+H2a", "_flip_noinval"))
FEET = (1, 3, 5, 15, 30, 60)
STRENGTHS = (("both", "両方"), ("weak", "弱い"), ("strong", "強い"))
REASONS = (("invalidated", "無効化"), ("opposite_weak", "反対の弱い"), ("reversed", "ドテン"))
GATE = "s19/b24"


def f(x, d=2):
    return "—" if x is None else f"{x:+.{d}f}"


def load(path: Path):
    return json.loads(path.read_text("utf-8")) if path.exists() else None


# ---------------------------------------------------------------- M-a


def t_ma(venue: str, base_name: str, d: dict) -> None:
    print(f"### 表 M-a({venue}、土台 {base_name}) — 門 `{GATE}`: 理由別の分解(bp / 取引、区間なし)\n")
    print("| 足 | 強さ | 理由 | n | EE 平均 | 入口の遅れ | 出口の遅れ |")
    print("|---|---|---|---|---|---|---|")
    for ft in FEET:
        for st, lab in STRENGTHS:
            c = d["cells"].get(f"{ft}|{GATE}|{st}")
            if not c:
                continue
            for rk, rlab in REASONS:
                rc = c["reasons"].get(rk)
                if not rc:
                    continue
                print(f"| {ft} 分 | {lab} | {rlab} | {rc['n']:,} | {f(rc['ee_mean_bp'])} | "
                      f"{f(rc['entry_delay_bp'])} | {f(rc['exit_delay_bp'])} |")
            dc = c["decomp_bp"]
            print(f"| {ft} 分 | {lab} | **セル全体** | {c['n']:,} | — | {f(dc['entry_delay'])} | {f(dc['exit_delay'])} |")
    print()


def t_ma_yearly(venue: str, base_name: str, d: dict) -> None:
    print(f"### 表 M-a(年別、{venue}、土台 {base_name}) — 門 `{GATE}`: 出口の遅れ(ED − EE)を理由別・年別に(bp / 取引)"
          + ("。右端は 2017 を除く全期間(取引数で重み付け)" if venue == "Binance" else "") + "\n")
    years = sorted({y for c in d["cells"].values() for rc in c["reasons"].values() for y in rc["per_year"]})
    head = "| 足 | 強さ | 理由 | " + " | ".join(years) + (" | 2017 除く |" if venue == "Binance" else " |")
    print(head)
    print("|---|---|---|" + "---|" * (len(years) + (1 if venue == "Binance" else 0)))
    for ft in FEET:
        for st, lab in STRENGTHS:
            c = d["cells"].get(f"{ft}|{GATE}|{st}")
            if not c:
                continue
            for rk, rlab in REASONS:
                rc = c["reasons"].get(rk)
                if not rc:
                    continue
                row = []
                s_ex = n_ex = 0.0
                for y in years:
                    p = rc["per_year"].get(y)
                    if not p:
                        row.append("—")
                        continue
                    ed = p["ed_mean_bp"] - p["ee_mean_bp"]
                    row.append(f"{f(ed)} ({p['n']:,})")
                    if y != "2017":
                        s_ex += ed * p["n"]
                        n_ex += p["n"]
                line = f"| {ft} 分 | {lab} | {rlab} | " + " | ".join(row)
                if venue == "Binance":
                    line += f" | **{f(s_ex / n_ex) if n_ex else '—'}** |"
                else:
                    line += " |"
                print(line)
    print()


# ---------------------------------------------------------------- M-b


def t_mb(venue: str, base_name: str, d: dict) -> None:
    print(f"### 表 M-b({venue}、土台 {base_name}) — 全 13 門 × 足 6: 理由別の出口の遅れ(強さ「両方」「弱い」、bp / 取引、n)\n")
    print("| 門 | 足 | 強さ | 無効化 出口遅れ(n) | 反対の弱い 出口遅れ(n) | ドテン 出口遅れ(n) |")
    print("|---|---|---|---|---|---|")
    gates = d["family"]["gates"]
    for g in gates:
        for ft in FEET:
            for st, lab in (("both", "両方"), ("weak", "弱い")):
                c = d["cells"].get(f"{ft}|{g}|{st}")
                if not c:
                    continue
                cols = []
                for rk, _rlab in REASONS:
                    rc = c["reasons"].get(rk)
                    cols.append(f"{f(rc['exit_delay_bp'])} ({rc['n']:,})" if rc else "—")
                print(f"| `{g}` | {ft} 分 | {lab} | " + " | ".join(cols) + " |")
    print()


# ---------------------------------------------------------------- M-c / M-d


LAYER_ORDER = (
    ("direction", "向き", ("buy", "sell")),
    ("wick_body_ratio", "ヒゲ/実体比", ("(1,1.5]", "(1.5,2]", "(2,3]", "(3,+)")),
    ("wick_length", "ヒゲ長", ("[19,24)", "[24,40)", "[40,80)", "[80,+)")),
    ("local_vol", "局所ボラ三分位", ("low", "mid", "high")),
    ("hold", "保有本数", ("[1,3)", "[3,10)", "[10,30)", "[30,+)")),
    ("exit_reason", "決済理由", ("invalidated", "opposite_weak", "reversed")),
)


def t_mc(venue: str, base_name: str, d: dict) -> None:
    print(f"### 表 M-c({venue}、土台 {base_name}) — 残りの「強い」(門 `{GATE}`)の層別。"
          f"bp / 取引、区間は日ブロックブートストラップ 200 回\n")
    print("| 足 | 層 | 区分 | n | 平均 bp | [区間] | 総損益 bp |")
    print("|---|---|---|---|---|---|---|")
    for ft in FEET:
        c = d["cells"].get(f"{ft}|{GATE}|strong")
        if not c:
            continue
        m = c["mechanism"]
        print(f"| {ft} 分 | **機構(全体)** | — | {m['n']:,} | {f(m['mean_bp'])} | "
              f"[{f(m['ci95_bp'][0])}, {f(m['ci95_bp'][1])}] | — |")
        for lname, llab, order in LAYER_ORDER:
            buckets = c["layers"].get(lname, {})
            labels = list(order) + sorted(set(buckets) - set(order))
            for blab in labels:
                b = buckets.get(blab)
                if not b:
                    continue
                print(f"| {ft} 分 | {llab} | {blab} | {b['n']:,} | {f(b['mean_bp'])} | "
                      f"[{f(b['ci95_bp'][0])}, {f(b['ci95_bp'][1])}] | {f(b['total_bp'], 1)} |")
        # 年層は別扱い(見出しの並びを年昇順に)
        yb = c["layers"].get("year", {})
        for y in sorted(yb):
            b = yb[y]
            print(f"| {ft} 分 | 年 | {y} | {b['n']:,} | {f(b['mean_bp'])} | "
                  f"[{f(b['ci95_bp'][0])}, {f(b['ci95_bp'][1])}] | {f(b['total_bp'], 1)} |")
    print()


def t_md(venue: str, base_name: str, d: dict) -> None:
    print(f"### 表 M-d({venue}、土台 {base_name}) — 残りの「強い」の経路(門 `{GATE}`)。"
          "入口足の終値から h 本後の終値まで、決済を無視して持ち続けた場合の符号付きリターン bp(n)\n")
    horizons = d.get("path_horizons") or [1, 2, 3, 5, 10, 20, 50]
    head_h = [str(h) for h in horizons]
    print("| 足 | 区分 | " + " | ".join(f"h={h}" for h in head_h) + " |")
    print("|---|---|" + "---|" * len(head_h))
    for ft in FEET:
        c = d["cells"].get(f"{ft}|{GATE}|strong")
        if not c:
            continue
        p = c["path"]

        def row(label, series):
            cells_ = []
            for h in head_h:
                x = series.get(h)
                cells_.append(f"{f(x['mean_bp'])} ({x['n']:,})" if x and x["mean_bp"] is not None else "—")
            print(f"| {ft} 分 | {label} | " + " | ".join(cells_) + " |")

        row("全体", p["overall"])
        for rk, rlab in REASONS:
            row(f"決済理由: {rlab}", p["by_exit_reason"].get(rk, {}))
        for vt, vlab in (("low", "局所ボラ 低"), ("mid", "局所ボラ 中"), ("high", "局所ボラ 高")):
            row(vlab, p["by_local_vol"].get(vt, {}))
    print()


def main() -> None:
    print("# 第 5 周 — (a') 出口の遅れの決済理由別分解 / (c)-iii 残りの「強い」の層別(生成物。`ROUND5_PREREG.md` §3)\n")
    print("単位 bp、経費なし。区間は日ブロックブートストラップ 200 回(種はセル名 × 層 × 区分、"
          "M-a/M-b は第 13 部と同じ取引の再集計なので区間は出していない)。"
          "総損益 = n × 平均。判定・帰無・MDE・判定バーは作っていない。\n")

    for venue, dirpath in VENUES:
        for base_name, tag in BASES:
            p = dirpath / f"round5_exit_reason{tag}.json"
            d = load(p)
            if d is None:
                print(f"- {venue} 土台 {base_name}: 未実行(`{p.name}`)\n")
                continue
            repro = d.get("reproduction_gate") or []
            ok = sum(1 for r in repro if r["ok"])
            print(f"## {venue}、土台 {base_name} — 期間 {d['explore'][0]} 〜 {d['explore'][1]}、"
                  f"再現ゲート {ok}/{len(repro)}\n")
            t_ma(venue, base_name, d)
            t_ma_yearly(venue, base_name, d)
            t_mb(venue, base_name, d)

    for venue, dirpath in VENUES:
        for base_name, tag2 in RESIDUAL_BASES:
            p = dirpath / f"round5_residual_strong{tag2}.json"
            d = load(p)
            if d is None:
                print(f"- {venue} 土台 {base_name}(残りの強い): 未実行(`{p.name}`)\n")
                continue
            print(f"## {venue}、土台 {base_name}(残りの強い) — 期間 {d['explore'][0]} 〜 {d['explore'][1]}\n")
            t_mc(venue, base_name, d)
            t_md(venue, base_name, d)


if __name__ == "__main__":
    main()
