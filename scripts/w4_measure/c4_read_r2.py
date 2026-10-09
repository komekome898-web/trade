#!/usr/bin/env python3
"""マチルダ(レンジ、カード 4)段 1 の族 A・B 84 本(`limit_sim/families_r2/`)の読みの表を作る。

読み方の決まり(結果の表を見る前に、この台本と `tests/research/test_c4_read_r2.py` で固めた。
research-protocol §0.7 の 7「読み方の決まりは測る前に台本の試験として固める」。走らせは済んでいたので
「測る前」ではなく「84 本を並べて見る前」。v37 の 1 本(良い側)の summary・analysis はこの台本を書く前に見た):

R1 比べる単位: 変種と v37 の差を、同じ側どうし(良い側と良い側、悪い側と悪い側)で取る。1 日あたりに直す
   (日数は各走らせの summary の `all.days`)。
R2 2 つの軸を分ける(L-578「**・小勝ちの増幅 ・大負けの避け方 この両方の観点から最適化する**」):
   小勝ち = 勝った取引の損益の和、大負け = 損益が −0.1 % 以下の取引の損益の和(`c4_limit_batch.py` の定義をそのまま使う。
   L-920 の前は同じ線を「−10bp」と書いていた。損益の率は bp と呼ばず % で持つ)。
   あわせて損益(全取引の和)と、ブレイクで閉じた取引の損益(INTENT_MAP §11-5 P-1)を出す。
R3 向きのラベル: 軸ごとに、良い側の差と悪い側の差の符号が同じなら「増える / 減る(両側)」、違えば
   「側で割れる(1 分足では決まらない)」、両側とも差が 0 なら「同じ」。大きさの境は置かない(根拠の無い値を置かない、A-12)。
   大きさは表の数字で読む。
R4 年ごとの安定: 2016〜2023 の 8 年(2015 年は 33 日しか無いので外す)で、年の損益の差(変種 − v37)の符号が、
   全期間の差の符号と同じ年の数を、側ごとに「n/8」で出す。
R5 決まらない足: 決まらない足に当たらなかった取引だけ(`decided_only`)の損益の差の符号が、全取引の差の符号と同じかを
   側ごとに出す。
R6 大負けの境: INTENT_MAP §10-1 は「v37 の負けの多い側から 1% の境」と決めたが、走らせの analysis は −0.1 %(前の書き方で −10bp)で切った。
   v37 の両側の取引の損益の 1% 分位を出し、−0.1 % と並べる(境を後から動かさない。並べるだけ)。

出力: <families_r2>/READ/TABLES.md と read.json。数字は手で書かない(research-protocol §1.2)。

    python3 scripts/w4_measure/c4_read_r2.py [--root <families_r2>]
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DEFAULT_ROOT = os.path.join(REPO, "docs", "RESEARCH", "cards", "c4_owner_matilda_range", "limit_sim", "families_r2")
SIDES = ("good", "bad")
YEARS = tuple(range(2016, 2024))
AXES = ("small_win", "big_loss", "pnl", "closed_by_break")
AXIS_JA = {"small_win": "小勝ち", "big_loss": "大負け", "pnl": "損益", "closed_by_break": "ブレイクで閉じた損益"}


_P_KEY = re.compile(r"^(.*)_bp$")


def _scale100(v):
    """`*_bp` の鍵の中身(数・数の並び・{ci, se, mde} のような入れ物)の数を全部 / 100 する。"""
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        return v / 100
    if isinstance(v, list):
        return [_scale100(x) for x in v]
    if isinstance(v, dict):
        return {k: _scale100(x) for k, x in v.items()}
    return v


def to_pct(o):
    """L-920 より前の出力の損益の鍵 `*_bp`(損益の率 × 1 万)を `*_pct`(%)に直す。新しい出力(`*_pct`)はそのまま。
    summary.json・analysis.json の `*_bp` の鍵はどれも損益(c4_limit_run・c4_limit_batch の定義)なので全部を直す。"""
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            m = _P_KEY.match(k) if isinstance(k, str) else None
            if m:
                out[m.group(1) + "_pct"] = _scale100(v)
            else:
                out[k] = to_pct(v)
        return out
    if isinstance(o, list):
        return [to_pct(x) for x in o]
    return o


def load_run(d: str) -> dict:
    with open(os.path.join(d, "summary.json"), encoding="utf-8") as fh:
        s = to_pct(json.load(fh))
    with open(os.path.join(d, "analysis.json"), encoding="utf-8") as fh:
        a = to_pct(json.load(fh))
    days = float(s["all"]["days"])
    small = sum(v["small_win_sum_pct"] for v in a["by_year"].values())
    big = sum(v["big_loss_sum_pct"] for v in a["by_year"].values())
    return {
        "days": days,
        "trades": int(s["all"]["trades"]),
        "wins": int(s["all"]["wins"]),
        "avg_win_pct": float(s["all"]["avg_win_pct"]),
        "undecided_share": float(s["all"]["trades_with_undecided"]) / max(1, int(s["all"]["trades"])),
        "per_day": {
            "trades": s["all"]["trades"] / days,
            "small_win": small / days,
            "big_loss": big / days,
            "pnl": float(s["all"]["sum_pct"]) / days,
            "closed_by_break": a["by_break"]["closed_by_break"]["sum_pct"] / days,
        },
        "year_pnl": {int(y): float(v["sum_pct"]) for y, v in a["by_year"].items()},
        "decided_pnl": float(a["decided_only"]["sum_pct"]),
        "by_reason": a["by_reason"],
        "analysis": a,
    }


def label(dg: float, db: float) -> str:
    """R3。良い側の差・悪い側の差から向きのラベル。"""
    if dg == 0 and db == 0:
        return "同じ"
    if dg > 0 and db > 0:
        return "増える(両側)"
    if dg < 0 and db < 0:
        return "減る(両側)"
    return "側で割れる"


def year_agreement(var: dict, base: dict) -> int:
    """R4。8 年のうち、年の損益の差の符号が全期間の差の符号と同じ年の数。"""
    total = var["per_day"]["pnl"] * var["days"] - base["per_day"]["pnl"] * base["days"]
    sgn = np.sign(total)
    n = 0
    for y in YEARS:
        d = var["year_pnl"].get(y, 0.0) - base["year_pnl"].get(y, 0.0)
        if np.sign(d) == sgn and sgn != 0:
            n += 1
    return n


def decided_same(var: dict, base: dict) -> bool:
    """R5。決まらない足に当たらなかった取引だけの差の符号が、全取引の差の符号と同じか。"""
    total = var["per_day"]["pnl"] * var["days"] - base["per_day"]["pnl"] * base["days"]
    dec = var["decided_pnl"] - base["decided_pnl"]
    return bool(np.sign(total) == np.sign(dec))


def compare(runs: dict) -> list[dict]:
    """runs[(名前, 側)] = load_run の値。v37 を基準に全変種の差の行を返す。"""
    names = sorted({n for n, _ in runs if n != "v37"})
    out = []
    for n in names:
        if not all((n, s) in runs for s in SIDES):
            continue
        row = {"name": n, "family": n.split("_")[0]}
        for ax in AXES:
            dg = runs[(n, "good")]["per_day"][ax] - runs[("v37", "good")]["per_day"][ax]
            db = runs[(n, "bad")]["per_day"][ax] - runs[("v37", "bad")]["per_day"][ax]
            row[ax] = {"d_good": dg, "d_bad": db, "label": label(dg, db)}
        dtg = runs[(n, "good")]["per_day"]["trades"] - runs[("v37", "good")]["per_day"]["trades"]
        dtb = runs[(n, "bad")]["per_day"]["trades"] - runs[("v37", "bad")]["per_day"]["trades"]
        row["trades"] = {"d_good": dtg, "d_bad": dtb, "label": label(dtg, dtb)}
        row["years_good"] = year_agreement(runs[(n, "good")], runs[("v37", "good")])
        row["years_bad"] = year_agreement(runs[(n, "bad")], runs[("v37", "bad")])
        row["decided_good"] = decided_same(runs[(n, "good")], runs[("v37", "good")])
        row["decided_bad"] = decided_same(runs[(n, "bad")], runs[("v37", "bad")])
        out.append(row)
    return out


def v37_quantile(root: str) -> dict:
    """R6。v37 の両側の取引の損益の 1% 分位。"""
    q = {}
    for s in SIDES:
        with gzip.open(os.path.join(root, f"v37_{s}", "trades.json.gz"), "rt", encoding="utf-8") as fh:
            o = json.load(fh)
        pnl = np.asarray(o["pnl_pct"], dtype=float) if "pnl_pct" in o else np.asarray(o["pnl_bp"], dtype=float) / 100
        q[s] = {"q01_pct": float(np.quantile(pnl, 0.01)), "share_le_minus0p1": float((pnl <= -0.1).mean()), "n": int(pnl.size)}
    return q


def _f(x: float, nd: int = 3) -> str:
    if x != 0 and abs(x) < 0.0005:
        return f"{x:+.6f}"  # 0 に近い差を「+0.000」と見せてラベルと食い違わないように(% にしたので前の桁の 2 つ下まで)
    return f"{x:+.{nd}f}"


def render(runs: dict, rows: list[dict], q: dict) -> str:
    L = ["# マチルダ(レンジ)段 1 の族 A・B 84 本の読みの表", "",
         "`scripts/w4_measure/c4_read_r2.py` が出した。読み方の決まり R1〜R6 はその台本の docstring。単位は %/日(段で割った損益の率(%)を 1 日あたりに直した和。L-920 で bp は値動き率だけの名前)。", ""]
    L += ["## 表 1: 走らせごとの値(1 日あたり)", "",
          "| 変種 | 側 | 取引/日 | 勝ち率 | 平均の勝ち(%) | 小勝ち | 大負け | 損益 | ブレイクで閉じた損益 | 決まらない足に当たった取引の割合 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for (n, s) in sorted(runs, key=lambda k: (k[0] != "v37", k[0], k[1])):
        r = runs[(n, s)]
        p = r["per_day"]
        L.append(f"| {n} | {'良' if s == 'good' else '悪'} | {p['trades']:.1f} | {r['wins'] / max(1, r['trades']):.3f} | {r['avg_win_pct']:.5f} | "
                 f"{p['small_win']:.3f} | {p['big_loss']:.3f} | {p['pnl']:.3f} | {p['closed_by_break']:.3f} | {r['undecided_share']:.3f} |")
    L += ["", "## 表 2: v37 との差(1 日あたり。良い側 / 悪い側)と向きのラベル(R3)・年の一致(R4)・決まらない足を除いても同じ向きか(R5)", "",
          "| 変種 | 取引/日の差 | 小勝ちの差 | 向き | 大負けの差 | 向き | 損益の差 | 向き | ブレイクで閉じた損益の差 | 年の一致(良 / 悪) | 決まった取引だけでも同じ向き(良 / 悪) |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['name']} | {_f(r['trades']['d_good'])} / {_f(r['trades']['d_bad'])} | "
                 f"{_f(r['small_win']['d_good'])} / {_f(r['small_win']['d_bad'])} | {r['small_win']['label']} | "
                 f"{_f(r['big_loss']['d_good'])} / {_f(r['big_loss']['d_bad'])} | {r['big_loss']['label']} | "
                 f"{_f(r['pnl']['d_good'])} / {_f(r['pnl']['d_bad'])} | {r['pnl']['label']} | "
                 f"{_f(r['closed_by_break']['d_good'])} / {_f(r['closed_by_break']['d_bad'])} | "
                 f"{r['years_good']}/8 / {r['years_bad']}/8 | {'はい' if r['decided_good'] else 'いいえ'} / {'はい' if r['decided_bad'] else 'いいえ'} |")
    L += ["", "注: 大負けは負の数。大負けの差が正 = 大負けが小さくなった(避けられた)。", ""]
    L += ["## 表 3: 大負けの境(R6)", "", "| 側 | v37 の取引の損益の 1% 分位(%) | −0.1 % 以下の取引の割合 | 取引の数 |", "|---|---|---|---|"]
    for s in SIDES:
        L.append(f"| {'良' if s == 'good' else '悪'} | {q[s]['q01_pct']:.4f} | {q[s]['share_le_minus0p1']:.4f} | {q[s]['n']} |")
    for key, title in (("by_break", "表 4: v37 の取引をブレイクとの関係で分けた損益(P-1)"),
                       ("by_hold", "表 5: v37 の取引を保有の分で分けた損益(P-4)"),
                       ("ratio_fixed_bins", "表 6: v37 の取引を比(窓の幅 ÷ 平均実体)の固定の境で分けた損益(P-2)")):
        L += ["", f"## {title}", "", "| 側 | 区分 | 取引 | 勝ち | 損益の和 | 小勝ちの和 | 大負けの和 |", "|---|---|---|---|---|---|---|"]
        for s in SIDES:
            a = runs[("v37", s)]["analysis"][key]
            items = a.items() if key == "by_break" else [(f"{x.get('lo', x.get('bin'))}〜{x.get('hi', '')}" if key == "by_hold" else str(x["bin"]), x) for x in a["rows"]]
            for k, v in items:
                L.append(f"| {'良' if s == 'good' else '悪'} | {k} | {v['trades']} | {v['wins']} | {v['sum_pct']:.2f} | {v['small_win_sum_pct']:.2f} | {v['big_loss_sum_pct']:.2f} |")
    L += derived_lines(runs, rows)
    return "\n".join(L) + "\n"


def derived_lines(runs: dict, rows: list[dict]) -> list[str]:
    """表 7: 報告と知見台帳に写す派生の数(84 本を並べて見た後に足した出力。読み方の決まり R1〜R6 は変えていない)。"""
    L = ["", "## 表 7: 読みに使う派生の数", ""]
    for s in SIDES:
        a = runs[("v37", s)]["analysis"]
        bb = a["by_break"]
        n_all = runs[("v37", s)]["trades"]
        L.append(f"- v37 {'良' if s == 'good' else '悪'}: ブレイクで閉じた取引 {bb['closed_by_break']['trades']} 件"
                 f"(全取引の {bb['closed_by_break']['trades'] / n_all:.4f})の損益 {bb['closed_by_break']['sum_pct']:.2f}%、"
                 f"ほかの取引 {bb['other']['sum_pct']:.2f}%")
        per = [x["sum_pct"] / x["trades"] for x in a["ratio_fixed_bins"]["rows"] if x["trades"]]
        L.append(f"- v37 {'良' if s == 'good' else '悪'}: 比の区分 1〜10 の 1 取引あたりの損益(%) "
                 + " / ".join(f"{v:+.5f}" for v in per))
    for ax in AXES:
        n_same = sum(1 for r in rows if r[ax]["label"] in ("増える(両側)", "減る(両側)", "同じ"))
        L.append(f"- 軸「{AXIS_JA[ax]}」の向きが両側でそろった変種: {n_same}/{len(rows)}")
    dup = [r["name"] for r in rows if r["name"] == "A2_step2_n1"]
    if dup:
        L.append("- A2_step1_n1 と A2_step2_n1 は段が 1 つなので段の間隔が効かず、同じ走らせになる(下の数は 2 本を別に数えている)")
    for n in ("v37", "A1_center_5_1", "A1_center_4_3", "A1_center_3_2", "A1_center_2_0.8", "A3_w20_b5_body", "A3_w40_b5_body",
              "A1_v37_entry5", "A5_alert1", "B1_delay0"):
        for s in SIDES:
            if (n, s) not in runs:
                continue
            r = runs[(n, s)]
            br = r["by_reason"]
            L.append(f"- {n} {'良' if s == 'good' else '悪'}: 平均の勝ち {r['avg_win_pct']:.5f}%・勝ち率 {r['wins'] / max(1, r['trades']):.3f}・"
                     f"取引 {r['per_day']['trades']:.1f}/日・決まらない足に当たった取引の割合 {r['undecided_share']:.3f}・"
                     f"終わり方「時間」{br.get('時間', {}).get('trades', 0)} 件 {br.get('時間', {}).get('sum_pct', 0.0):.2f}%・"
                     f"「利確2」{br.get('利確2', {}).get('trades', 0)} 件 {br.get('利確2', {}).get('sum_pct', 0.0):.2f}%・"
                     f"「反対のブレイク」{br.get('反対のブレイク', {}).get('trades', 0)} 件 {br.get('反対のブレイク', {}).get('sum_pct', 0.0):.2f}%")
    n8 = sum(1 for r in rows if r["years_good"] == 8 and r["years_bad"] == 8)
    L.append(f"- 年の一致が両側とも 8/8 の変種: {n8}/{len(rows)}")
    both_pos = [r["name"] for r in rows
                if runs[(r["name"], "good")]["per_day"]["pnl"] > 0 and runs[(r["name"], "bad")]["per_day"]["pnl"] > 0]
    L.append(f"- 損益が両側とも正の変種: {len(both_pos)}/{len(rows)}" + (f"({', '.join(both_pos)})" if both_pos else ""))
    L.append(f"- v37 の損益: 良 {runs[('v37', 'good')]['per_day']['pnl']:.3f} / 悪 {runs[('v37', 'bad')]['per_day']['pnl']:.3f} %/日")
    wq = runs[("v37", "good")]["analysis"]["width_over_close_deciles"]["rows"][0]
    L.append(f"- v37 良の幅 ÷ 終値の十分位 1 の下端: {wq['lo']:.6f}(幅の門の下限 150 ÷ 1152502 = {150 / 1152502:.6f})")
    gap = runs[("v37", "good")]["per_day"]["pnl"] - runs[("v37", "bad")]["per_day"]["pnl"]
    L.append(f"- v37 の良い側と悪い側の損益の差: {gap:.3f} %/日")
    return L


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    a = ap.parse_args(argv)
    runs = {}
    for d in sorted(os.listdir(a.root)):
        p = os.path.join(a.root, d)
        if not os.path.isfile(os.path.join(p, "analysis.json")):
            continue
        name, side = d.rsplit("_", 1)
        runs[(name, side)] = load_run(p)
    rows = compare(runs)
    q = v37_quantile(a.root)
    out = os.path.join(a.root, "READ")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write(render(runs, rows, q))
    slim = {f"{n}_{s}": {k: v for k, v in r.items() if k != "analysis"} for (n, s), r in runs.items()}
    with open(os.path.join(out, "read.json"), "w", encoding="utf-8") as fh:
        json.dump({"runs": slim, "compare": rows, "v37_quantile": q}, fh, ensure_ascii=False, indent=1)
    print(f"runs {len(runs)} compare {len(rows)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
