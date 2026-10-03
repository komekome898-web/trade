#!/usr/bin/env python3
"""カード 9 (a) の全期間の走らせ(2023-06-25〜2024-10-14)の出力から、RESULTS.md・MANIFEST.md の表を作る。

- 読むだけ(入力のファイルを書き換えない。書き出しは標準出力だけ)。ネットワークを使わない。
- 測り直しはしない。`scripts/c9_run_a.py` がすでに書いた出力(`--in` の直下。`chunks/` は 2023-07-15 の
  見出しの確認にだけ使う)を読み、並べ替え・絞り込み・既存の列どうしの引き算と、走らせと同じ
  集計関数 `bot.research.liq_cascade_v2.dist_stats` を当てるだけ。
- 判定語は書かない。

    PYTHONPATH=src python3 docs/RESEARCH/cards/c9_liquidation_cascade/run_a/make_tables.py \
        --in data/c9_run_a/full_20230625_20241014 --section tables
    (--section manifest で MANIFEST.md の表、--section all で両方)

出力は Markdown の塊。塊の頭に `<!-- BLOCK:名前 -->`、終わりに `<!-- /BLOCK -->` を付ける。
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "src"))
from bot.research.liq_cascade_v2 import dist_stats  # noqa: E402  (走らせと同じ集計の式)

DEFAULT_IN = REPO / "data" / "c9_run_a" / "full_20230625_20241014"
H_ALL = (1, 5, 10, 30, 60, 300, 900, 1800, 3600, 14400, 86400, 604800)
H_LABEL = {1: "1秒", 5: "5秒", 10: "10秒", 30: "30秒", 60: "60秒", 300: "5分", 900: "15分",
           1800: "30分", 3600: "60分", 14400: "240分", 86400: "1日", 604800: "1週"}
RESUME_FIRST_DAY = "2024-02-29"   # full.log 251 行「[resume …] L-584」の直後の最初の日
COPIED = ("dist_policy.csv", "dist_reaction.csv", "dist_s_curve.csv", "dist_size_split.csv",
          "label_counts.csv", "policy_action_counts.csv", "policy_judge_counts.csv",
          "three_way_calibration.csv", "three_way_model.json", "run_meta.json")
DIST_COLS = ["n", "q25", "q50", "q75", "share_pos", "share_neg", "day_eq_mean",
             "se_day_cluster", "n_days"]


# --------------------------------------------------------------------------- #
def fmt(x) -> str:
    if x is None:
        return ""
    if isinstance(x, (bool, np.bool_)):
        return str(int(x))
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    if isinstance(x, (float, np.floating)):
        if not np.isfinite(x):
            return "NaN"
        if float(x).is_integer() and abs(x) < 1e12:
            return str(int(x))
        return f"{x:.4g}"
    return str(x)


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(fmt(r[c]).replace("|", "/") for c in cols) + " |")
    return "\n".join(out)


def block(name: str, source: str, body: str) -> str:
    return f"<!-- BLOCK:{name} -->\n出所: {source}\n\n{body}\n<!-- /BLOCK -->\n"


def ds_row(vals, days) -> dict:
    d = dist_stats(np.asarray(vals, dtype=float), np.asarray(days, dtype=object))
    return {k: d[k] for k in DIST_COLS}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def count_rows(p: Path) -> tuple[int, str]:
    """(データの行数, 数え方)。CSV は見出しを除いた行数、jsonl は行数、json は '-'。"""
    if p.suffix == ".json":
        return -1, "json(行の表ではない)"
    opener = gzip.open if p.suffix == ".gz" else open
    n = 0
    with opener(p, "rt", encoding="utf-8", newline="") as f:
        for _ in f:
            n += 1
    if ".jsonl" in p.name:
        return n, "行数(1 行 = 1 プリント)"
    # CSV: 物理行 − 見出し 1 行。引用符の中の改行が無いことは、manifest_check の別の出所との突き合わせで確かめる
    return n - 1, "見出しを除いた行数"


# --------------------------------------------------------------------------- #
def manifest(src: Path) -> str:
    rows = []
    for p in sorted(x for x in src.iterdir() if x.is_file()):
        n, how = count_rows(p)
        rows.append({"ファイル": p.name, "バイト": p.stat().st_size, "sha256": sha256(p),
                     "行数": ("-" if n < 0 else n), "数え方": how,
                     "run_a/ に写したか": ("写した" if p.name in COPIED else "写していない")})
    df = pd.DataFrame(rows)
    out = [block("manifest", f"`{src.relative_to(REPO)}/` の直下(`chunks/` を除く)のファイルを "
                 "`sha256`(hashlib)と行数(gzip を開いて数えた)で並べた", md(df))]
    # 写したものが元と同じか
    chk = []
    for name in COPIED:
        a, b = src / name, HERE / name
        chk.append({"ファイル": name, "元の sha256": sha256(a),
                    "run_a/ の sha256": (sha256(b) if b.exists() else "(無い)"),
                    "一致": int(b.exists() and sha256(a) == sha256(b))})
    out.append(block("manifest_copy", "同じ台本で、元と `run_a/` の写しの sha256 を比べた",
                     md(pd.DataFrame(chk))))
    # 行数を別の出所と突き合わせる
    meta = json.loads((src / "run_meta.json").read_text(encoding="utf-8"))
    nrow = {r["ファイル"]: r["行数"] for r in rows}
    Pd = pd.read_csv(src / "dist_policy.csv")
    n_casc = int(Pd[Pd["単位"] == "連鎖1本(入らないを0で含める)"]["連鎖の数"].sum())
    n_legs = int(Pd[Pd["単位"] == "1レグ"]["n"].sum() + Pd[Pd["単位"] == "1レグ"]["n_nan"].sum())
    ctl = sum(v["取れた"] for k, v in meta["対照の取れた数"].items() if isinstance(v, dict) and "取れた" in v)
    chk = [
        ("anchors_prints.csv.gz", nrow["anchors_prints.csv.gz"], meta["一意化"]["一意"], "run_meta 一意化.一意"),
        ("jev_states.jsonl.gz", nrow["jev_states.jsonl.gz"], meta["一意化"]["一意"], "run_meta 一意化.一意"),
        ("three_way_probs.csv.gz", nrow["three_way_probs.csv.gz"], meta["一意化"]["一意"], "run_meta 一意化.一意"),
        ("controls.csv.gz", nrow["controls.csv.gz"], ctl, "run_meta 対照の取れた数 の 取れた の和"),
        ("anchors_bundles.csv.gz", nrow["anchors_bundles.csv.gz"], sum(meta["束の数"].values()), "run_meta 束の数 の和"),
        ("policy_cascades.csv.gz", nrow["policy_cascades.csv.gz"], n_casc,
         "dist_policy.csv 単位 = 連鎖1本(入らないを0で含める) の 連鎖の数 の和"),
        ("policy_legs.csv.gz", nrow["policy_legs.csv.gz"], n_legs, "dist_policy.csv 単位 = 1レグ の n + n_nan の和"),
    ]
    out.append(block("manifest_check", "上の表の行数と、別の出所(右端)から数えた数を並べた",
                     md(pd.DataFrame([{"ファイル": a, "上の表の行数": b, "別の出所の数": c, "一致": int(b == c),
                                       "別の出所": d} for a, b, c, d in chk]))))
    log = src.parent / "full.log"
    if log.exists():
        out.append(block("manifest_log", "走らせの記録",
                         md(pd.DataFrame([{"ファイル": str(log.relative_to(REPO)),
                                           "バイト": log.stat().st_size,
                                           "sha256": sha256(log),
                                           "行数": sum(1 for _ in open(log, encoding="utf-8"))}]))))
    return "\n".join(out)


# --------------------------------------------------------------------------- #
def tables(src: Path) -> str:
    out: list[str] = []
    meta = json.loads((src / "run_meta.json").read_text(encoding="utf-8"))
    model = json.loads((src / "three_way_model.json").read_text(encoding="utf-8"))
    R = pd.read_csv(src / "dist_reaction.csv")
    S = pd.read_csv(src / "dist_size_split.csv")
    Pd = pd.read_csv(src / "dist_policy.csv")
    SC = pd.read_csv(src / "dist_s_curve.csv")
    L = pd.read_csv(src / "label_counts.csv")
    AC = pd.read_csv(src / "policy_action_counts.csv")
    JC = pd.read_csv(src / "policy_judge_counts.csv")
    CAL = pd.read_csv(src / "three_way_calibration.csv")

    rk = [f"react_{h}" for h in H_ALL]
    pcols = ["print_id", "day", "side", "sign", "before_seal", "opened_before", "period",
             "m10_signed", "mat1_same_side_count_60s_and_elapsed", "mat8_covered", "cont_60",
             "g30_pos_post", "g60_pos_post", "g180_pos_post", "p0_lag_ms"] + rk
    P = pd.read_csv(src / "anchors_prints.csv.gz", usecols=pcols, dtype={"day": str})
    C = pd.read_csv(src / "controls.csv.gz",
                    usecols=["kind", "day", "anchor_ms", "ref_id", "day_offset"] + rk,
                    dtype={"day": str, "ref_id": str})
    CA = pd.read_csv(src / "policy_cascades.csv.gz", dtype={"day": str})

    # ---- 0. 走らせの数(run_meta.json) ----
    tm = meta["対照の取れた数"]
    rows = [
        ("期間", " 〜 ".join(meta["期間"]), "期間"),
        ("暦日", meta["日数"], "日数"),
        ("清算の生の行", meta["一意化"]["生の行"], "一意化.生の行"),
        ("一意化したプリント", meta["一意化"]["一意"], "一意化.一意"),
        ("多重度 2 の組 / 多重度 4 の組", f'{meta["一意化"]["多重度"]["2"]} / {meta["一意化"]["多重度"]["4"]}',
         "一意化.多重度"),
        ("プリントのある日", int(P["day"].nunique()), "anchors_prints.day の種類(台本で数えた)"),
        ("期間の中でプリントの無い日",
         ", ".join(sorted(set(pd.date_range(meta["期間"][0], meta["期間"][1]).strftime("%Y-%m-%d"))
                          - set(P["day"]))), "期間の暦日から anchors_prints.day を引いた(台本で数えた)"),
        ("束 g=30 / 60 / 180", " / ".join(str(meta["束の数"][g]) for g in ("30", "60", "180")), "束の数"),
    ]
    for k in ("(i)無作為", "(ii)合わせた時刻", "(iii)プラセボ_g30", "(iii)プラセボ_g60", "(iii)プラセボ_g180"):
        rows.append((f"対照 {k} 取れた / 求めた", f'{tm[k]["取れた"]} / {tm[k]["求めた"]}',
                     f"対照の取れた数.{k}"))
    rows.append(("対照 (ii) 日のずれ別(0,−1,+1,−2,+2,−3,+3)",
                 " / ".join(str(tm["(ii)日のずれ別"][o]) for o in ("0", "-1", "1", "-2", "2", "-3", "3")),
                 "対照の取れた数.(ii)日のずれ別"))
    rows.append(("約定の欠けた日(窓の中)", ", ".join(meta["約定の欠けた日(窓の中)"]), "約定の欠けた日(窓の中)"))
    rows.append(("規則_3択 作る日 / 測る日", f'{"〜".join(model["作る日"])} / {"〜".join(model["測る日"])}',
                 "three_way_model.json 作る日・測る日"))
    rows.append(("run_meta の resume", meta["resume"], "resume"))
    rows.append(("run_meta の所要_秒.段2 合計 / 全体", f'{meta["所要_秒"]["段2 合計"]} / {meta["所要_秒"]["全体"]}',
                 "所要_秒(3 回目の起動だけの値)"))
    rows.append(("run_meta の最大メモリ_MB", meta["最大メモリ_MB(ru_maxrss)"], "最大メモリ_MB(ru_maxrss)"))
    out.append(block("t0_meta", "`run_meta.json`(列は右端)。プリントのある日だけ `anchors_prints.csv.gz` の `day`",
                     md(pd.DataFrame(rows, columns=["項目", "値", "run_meta.json の鍵"]))))

    # ---- 1. 値動き: 実の全プリント vs 対照 (i)(ii) ----
    sel = R[(R["量"] == "react") & R["群"].isin(["実_全プリント", "対照(i)無作為", "対照(ii)合わせた時刻"])].copy()
    sel["h"] = sel["h_s"].map(H_LABEL)
    sel = sel.sort_values(["h_s", "群"])
    out.append(block("t1_react", "`dist_reaction.csv`(量 = react、群 = 実_全プリント・対照(i)無作為・対照(ii)合わせた時刻)。"
                     "react = 起点の約定から h 後の値動き(bp)、実は清算の向き、対照は直前 10 秒の変位の向きに正",
                     md(sel[["h", "群"] + DIST_COLS])))

    sel = R[R["量"].isin(["mfe", "mae", "giveback"]) & R["h_s"].isin([10, 60, 300, 3600]) &
            R["群"].isin(["実_全プリント", "対照(i)無作為", "対照(ii)合わせた時刻"])].copy()
    sel["h"] = sel["h_s"].map(H_LABEL)
    sel = sel.sort_values(["量", "h_s", "群"])
    out.append(block("t1b_excursion", "`dist_reaction.csv`(量 = mfe・mae・giveback、h = 10 秒・60 秒・5 分・60 分)",
                     md(sel[["量", "h", "群", "n", "q25", "q50", "q75", "day_eq_mean", "se_day_cluster"]])))

    # ---- 2. 対照 (ii) との対の差(プリント − 合わせた時刻) ----
    c2 = C[C["kind"] == "(ii)合わせた時刻"].copy()
    M = c2.merge(P[["print_id", "day", "before_seal"] + rk], left_on="ref_id", right_on="print_id",
                 suffixes=("_c", "_p"))
    rows = []
    for h in H_ALL:
        d = M[f"react_{h}_p"].to_numpy(float) - M[f"react_{h}_c"].to_numpy(float)
        rows.append({"h": H_LABEL[h]} | ds_row(d, M["day_p"].to_numpy(object)))
    out.append(block("t2_paired_ii",
                     "`controls.csv.gz`(kind = (ii)合わせた時刻)の `ref_id` を `anchors_prints.csv.gz` の `print_id` に"
                     f"つないだ {len(M)} 組。値 = react_h(プリント)− react_h(対照)、日 = プリントの日。集計は `dist_stats`",
                     md(pd.DataFrame(rows))))

    # ---- 3. 対照 (iii) プラセボ vs 束の最後(最後 + 単発、事後) ----
    rows = []
    for g in (30, 60, 180):
        m = P[f"g{g}_pos_post"].isin(["最後", "単発"]).to_numpy()
        cg = C[C["kind"] == f"(iii)プラセボ_g{g}"]
        for h in (10, 60, 300, 3600, 86400):
            rows.append({"g": g, "h": H_LABEL[h], "群": "実_束の最後(最後+単発)"} |
                        ds_row(P.loc[m, f"react_{h}"], P.loc[m, "day"]))
            rows.append({"g": g, "h": H_LABEL[h], "群": f"対照(iii)プラセボ_g{g}"} |
                        ds_row(cg[f"react_{h}"], cg["day"]))
    out.append(block("t3_placebo",
                     "実 = `anchors_prints.csv.gz` の `g{g}_pos_post` が 最後 か 単発 の行の react_h、"
                     "対照 = `controls.csv.gz` の kind = (iii)プラセボ_g{g} の react_h(窓の中の値動きの向きに正)。集計は `dist_stats`",
                     md(pd.DataFrame(rows))))

    # ---- 4. 側・位置(事後) ----
    grp = ["実_側SELL", "実_側BUY", "実_g60_位置単発(事後)", "実_g60_位置最初(事後)",
           "実_g60_位置途中(事後)", "実_g60_位置最後(事後)"]
    sel = R[(R["量"] == "react") & R["群"].isin(grp) & R["h_s"].isin([10, 60, 300, 3600])].copy()
    sel["h"] = sel["h_s"].map(H_LABEL)
    sel["o"] = sel["群"].map({g: i for i, g in enumerate(grp)})
    sel = sel.sort_values(["h_s", "o"])
    out.append(block("t4_side_pos", "`dist_reaction.csv`(量 = react、群 = 側・g=60 の位置(事後)、h = 10 秒・60 秒・5 分・60 分)",
                     md(sel[["h", "群"] + DIST_COLS])))

    # ---- 5. ラベル(続く) ----
    lab = L.copy()
    out.append(block("t5_label", "`label_counts.csv`(そのまま)", md(lab)))
    sc = np.where(P["mat1_same_side_count_60s_and_elapsed"].fillna(0) >= 1, "連鎖の中", "1件目")
    rows = []
    for s_ in ("1件目", "連鎖の中"):
        for per in ("作る", "測る"):
            m = (sc == s_) & (P["period"] == per).to_numpy()
            rows.append({"場面": s_, "期間": per, "プリント": int(m.sum()),
                         "続く(cont_60)の割合": float(P.loc[m, "cont_60"].mean())})
    for s_, v in model["場面"].items():
        rows.append({"場面": s_, "期間": "作る(three_way_model.json の基準率)", "プリント": v["件数(作る)"],
                     "続く(cont_60)の割合": v["基準率(作る)"]})
    out.append(block("t5b_scene",
                     "`anchors_prints.csv.gz` の `mat1_same_side_count_60s_and_elapsed`(≥ 1 = 連鎖の中、0 か欠け = 1件目、"
                     "`liq_cascade_v2.scene_of` と同じ)・`period`・`cont_60`。下 2 行は `three_way_model.json`",
                     md(pd.DataFrame(rows))))

    # ---- 6. 方策(状態機械) ----
    order = {"全部順張り": 0, "全部逆張り": 1, "規則_材料1": 2, "規則_3択": 3, "完全な判断": 4}
    q = Pd[(Pd["期間"] == "測る") & (Pd["gap_s"] == 60) & (Pd["delay_s"] == 1)].copy()
    q["o"] = q["policy"].map(order)
    q = q.sort_values(["単位", "o", "type"])
    keep = ["単位", "policy", "type", "連鎖の数", "入った連鎖", "値の欠け", "n", "q25", "q50", "q75",
            "share_pos", "share_neg", "day_eq_mean", "se_day_cluster", "daysum_mean", "daysum_se"]
    out.append(block("t6_policy_g60d1",
                     "`dist_policy.csv`(期間 = 測る、gap_s = 60、delay_s = 1、単位 = 連鎖1本(入らないを0で含める)・"
                     "連鎖1本(入った連鎖だけ)・1レグ)。pnl_bp は建玉の向きに正",
                     md(q[q["単位"].isin(["連鎖1本(入らないを0で含める)", "連鎖1本(入った連鎖だけ)", "1レグ"])][keep])))

    q = Pd[(Pd["期間"] == "測る") & (Pd["単位"] == "連鎖1本(入らないを0で含める)")].copy()
    q["o"] = q["policy"].map(order)
    q = q.sort_values(["gap_s", "delay_s", "o", "type"])
    out.append(block("t6b_policy_all",
                     "`dist_policy.csv`(期間 = 測る、単位 = 連鎖1本(入らないを0で含める)、g × 遅れ の全部)",
                     md(q[["gap_s", "delay_s", "policy", "type", "連鎖の数", "入った連鎖", "q50",
                           "share_pos", "share_neg", "day_eq_mean", "se_day_cluster"]])))

    q = Pd[(Pd["gap_s"] == 60) & (Pd["delay_s"] == 1) & (Pd["単位"] == "連鎖1本(入らないを0で含める)") &
           (Pd["policy"] != "規則_3択")].copy()
    q["o"] = q["policy"].map(order)
    q = q.sort_values(["o", "type", "期間"])
    out.append(block("t6c_policy_period",
                     "`dist_policy.csv`(gap_s = 60、delay_s = 1、単位 = 連鎖1本(入らないを0で含める)、作る と 測る を並べた。"
                     "規則_3択 は 測る にしか無い)",
                     md(q[["policy", "type", "期間", "連鎖の数", "q50", "share_pos", "day_eq_mean",
                           "se_day_cluster", "n_days"]])))

    q = Pd[(Pd["期間"] == "測る") & (Pd["gap_s"] == 60) & (Pd["delay_s"] == 1) &
           Pd["単位"].str.contains("束の総量3分位")].copy()
    q["o"] = q["policy"].map(order)
    q = q.sort_values(["o", "type", "単位"])
    out.append(block("t6d_policy_qty",
                     "`dist_policy.csv`(期間 = 測る、gap_s = 60、delay_s = 1、単位 = 束の総量の 3 分位(事後))",
                     md(q[["policy", "type", "単位", "n", "q50", "share_pos", "day_eq_mean", "se_day_cluster"]])))

    # ---- 7. 規則_3択 の行動と判断の数 / 判断の数の突き合わせ ----
    a = AC[(AC["policy"] == "規則_3択") & (AC["gap_s"] == 60) & (AC["delay_s"] == 1)].copy()
    a = a.sort_values(["type", "行動"])
    out.append(block("t7_actions", "`policy_action_counts.csv`(policy = 規則_3択、gap_s = 60、delay_s = 1)",
                     md(a[["type", "行動", "件数"]])))
    rows = []
    jm = model["判断の件数(プリント)"]
    for g in (30, 60, 180):
        for typ in ("A", "B"):
            j = JC[(JC["policy"] == "規則_3択") & (JC["gap_s"] == g) & (JC["delay_s"] == 1) & (JC["type"] == typ)]
            d = dict(zip(j["判断"], j["件数"]))
            rows.append({"出所": f"policy_judge_counts g={g} 遅れ1 型{typ}", "止まる": d.get("止まる", 0),
                         "わからない": d.get("わからない", 0), "続く": d.get("続く", 0)})
    rows.append({"出所": "three_way_model.json 判断の件数(測る)", "止まる": jm["測る_止まる"],
                 "わからない": jm["測る_わからない"], "続く": jm["測る_続く"]})
    out.append(block("t7b_judge_check",
                     "`policy_judge_counts.csv`(段 3 = 2 回目の起動で書いた chunks/meta3 の和)と "
                     "`three_way_model.json`(3 回目の起動で作り直した模型)の判断の数",
                     md(pd.DataFrame(rows))))

    # ---- 8. s 秒の曲線 ----
    q = SC[(SC["delay_s"] == 1) & SC["s"].isin([1, 5, 10, 30, 60, 120, 180]) &
           SC["h_s"].isin([10, 60, 300, 3600])].copy()
    q["h"] = q["h_s"].map(H_LABEL)
    q = q.sort_values(["h_s", "s"])
    out.append(block("t8_scurve", "`dist_s_curve.csv`(delay_s = 1、s = 1・5・10・30・60・120・180 秒、h = 10 秒・60 秒・5 分・60 分)。"
                     "値 = fade の建玉の向きの値動き(bp)。s ごとに母集団が違う(次の同じ側のプリントが s 秒より後のものだけ)",
                     md(q[["h", "s"] + DIST_COLS])))

    # ---- 9. 量の 3 分位 ----
    q = S[(S["量"] == "react") & S["h_s"].isin([60, 3600])].copy()
    q["h"] = q["h_s"].map(H_LABEL)
    q = q.sort_values(["h_s", "分け", "3分位"])
    out.append(block("t9_size", "`dist_size_split.csv`(量 = react、h = 60 秒・60 分)。境 = 3 分位の境(全期間のプリントから。CSV の `|` は表の都合で `/` にした)",
                     md(q[["h", "分け", "3分位", "境", "n", "q50", "share_pos", "day_eq_mean", "se_day_cluster"]])))

    # ---- 10. 3 択の較正表 ----
    out.append(block("t10_calib", "`three_way_calibration.csv`(そのまま。作る期間の out-of-fold 確率)", md(CAL)))
    rows = []
    for s_, v in model["場面"].items():
        rows.append({"場面": s_, "件数(作る)": v["件数(作る)"], "基準率(作る)": v["基準率(作る)"],
                     "分割数": v["分割数"], "わからないの帯": str(v["わからないの帯"]),
                     "基準率を跨ぐ帯": str(v["基準率を跨ぐ帯"])})
    out.append(block("t10b_band", "`three_way_model.json` 場面", md(pd.DataFrame(rows))))
    rows = []
    for s_, v in model["場面"].items():
        for k, b in v["係数"].items():
            rows.append({"場面": s_, "材料": k, "係数": b})
    TP = pd.read_csv(src / "three_way_probs.csv.gz", dtype={"day": str})
    rows = []
    for (per, s_, j), g in TP.groupby(["期間", "場面", "判断"]):
        rows.append({"期間": per, "場面": s_, "判断": j, "プリント": len(g),
                     "続く(cont_60)の割合": float(g["cont_60"].mean()),
                     "続くの確率の中央値": float(g["続くの確率"].median())})
    out.append(block("t10d_judge_hit",
                     "`three_way_probs.csv.gz`(期間・場面・判断ごとに、事後のラベル cont_60 の割合)。"
                     "作る期間の判断は模型を作った行そのものへの当てはめ(out-of-fold ではない)",
                     md(pd.DataFrame(rows))))
    out.append(block("t10c_coef", "`three_way_model.json` 場面.係数(入力は中央順位、L2 1e-3 のニュートン法)",
                     md(pd.DataFrame(rows))))

    # ---- 11. 月ごと ----
    P["month"] = P["day"].str[:7]
    rows = []
    for mth, g in P.groupby("month"):
        r = {"月": mth, "プリント": len(g), "プリントのある日": g["day"].nunique(),
             "SELL の割合": float((g["side"] == "SELL").mean())}
        for h in (60, 3600):
            d = ds_row(g[f"react_{h}"], g["day"])
            r[f"react {H_LABEL[h]} q50"] = d["q50"]
            r[f"react {H_LABEL[h]} 日等重み平均"] = d["day_eq_mean"]
            r[f"react {H_LABEL[h]} 日クラスタSE"] = d["se_day_cluster"]
        rows.append(r)
    out.append(block("t11_month_react", "`anchors_prints.csv.gz` を `day` の年月で分け、react_60・react_3600 に `dist_stats`",
                     md(pd.DataFrame(rows))))

    CA["month"] = CA["day"].str[:7]
    sub = CA[(CA["gap_s"] == 60) & (CA["delay_s"] == 1)].copy()
    sub["incl"] = np.where(sub["entered"] == 1, sub["pnl_bp"], np.where(sub["missing"] == 1, np.nan, 0.0))
    rows = []
    pols = [("全部順張り", "-"), ("全部逆張り", "-"), ("規則_材料1", "A"), ("完全な判断", "A"), ("規則_3択", "A")]
    for mth, g in sub.groupby("month"):
        r = {"月": mth, "束(g=60)": int(((g["policy"] == "全部逆張り")).sum())}
        for pol, typ in pols:
            gg = g[(g["policy"] == pol) & (g["type"] == typ)]
            if not len(gg):
                r[f"{pol}{'' if typ == '-' else '_' + typ} 日等重み平均"] = np.nan
                continue
            d = ds_row(gg["incl"], gg["day"])
            r[f"{pol}{'' if typ == '-' else '_' + typ} 日等重み平均"] = d["day_eq_mean"]
        rows.append(r)
    out.append(block("t11b_month_policy",
                     "`policy_cascades.csv.gz`(gap_s = 60、delay_s = 1)を `day` の年月で分け、"
                     "連鎖 1 本の pnl_bp(入らない = 0、値の欠け = NaN。`c9_run_a.aggregate` と同じ作り)の日等重み平均",
                     md(pd.DataFrame(rows))))

    # ---- 12. 封印の境・9 月に開いた日 ----
    rows = []
    for col, lab_ in (("before_seal", "before_seal"), ("opened_before", "opened_before")):
        for v in (1, 0):
            m = (P[col] == v).to_numpy()
            for h in (60, 3600):
                rows.append({"列": lab_, "値": v, "h": H_LABEL[h], "プリントのある日": int(P.loc[m, "day"].nunique())} |
                            ds_row(P.loc[m, f"react_{h}"], P.loc[m, "day"]))
            mm = (M["before_seal"] == v).to_numpy() if col == "before_seal" else None
            if mm is not None:
                for h in (60, 3600):
                    d = M.loc[mm, f"react_{h}_p"].to_numpy(float) - M.loc[mm, f"react_{h}_c"].to_numpy(float)
                    rows.append({"列": lab_ + "(対 (ii) の差)", "値": v, "h": H_LABEL[h],
                                 "プリントのある日": int(M.loc[mm, "day_p"].nunique())} |
                                ds_row(d, M.loc[mm, "day_p"]))
    out.append(block("t12_seal", "`anchors_prints.csv.gz` の `before_seal`・`opened_before` で分けた react_h。"
                     "「対 (ii) の差」は表 t2 と同じ対の差を `before_seal` で分けた",
                     md(pd.DataFrame(rows))))

    # ---- 13. 偏り(日の集中) ----
    cnt = P.groupby("day").size().sort_values(ascending=False)
    top = cnt.head(10)
    rows = [{"日": d, "プリント": int(n), "全体に占める割合": n / len(P)} for d, n in top.items()]
    rows.append({"日": "上位 10 日の合計", "プリント": int(top.sum()), "全体に占める割合": top.sum() / len(P)})
    rows.append({"日": "1 日あたりの中央値(プリントのある日)", "プリント": float(cnt.median()), "全体に占める割合": np.nan})
    out.append(block("t13_topdays", "`anchors_prints.csv.gz` の `day` ごとの行数", md(pd.DataFrame(rows))))

    rows = []
    for pol, typ in pols:
        for per in ("作る", "測る"):
            gg = sub[(sub["policy"] == pol) & (sub["type"] == typ) & (sub["period"] == per)]
            if not len(gg):
                continue
            ds_ = gg.groupby("day")["incl"].sum()
            tot = float(ds_.sum())
            top10 = ds_.reindex(ds_.abs().sort_values(ascending=False).index).head(10)
            rows.append({"方策": pol + ("" if typ == "-" else "_" + typ), "期間": per, "日の数": len(ds_),
                         "連鎖の pnl の総和(bp)": tot, "|日の合計| の上位 10 日の和(bp)": float(top10.sum()),
                         "上位 10 日を除いた総和(bp)": tot - float(top10.sum()),
                         "上位 10 日": ",".join(top10.index[:10])})
    out.append(block("t13b_policy_conc",
                     "`policy_cascades.csv.gz`(gap_s = 60、delay_s = 1、入らない = 0)の日ごとの合計。"
                     "上位 10 日 = 日の合計の絶対値の大きい順",
                     md(pd.DataFrame(rows))))

    # ---- 14. --resume の限り(対照 (ii) の使った候補の印) ----
    dup = c2[c2["anchor_ms"].duplicated(keep=False)]
    gd = dup.groupby("anchor_ms")["day"].agg(["min", "max", "count"])
    straddle = int(((gd["min"] < RESUME_FIRST_DAY) & (gd["max"] >= RESUME_FIRST_DAY)).sum())
    rows = [
        {"項目": "対照 (ii) の行", "値": len(c2)},
        {"項目": "対照 (ii) の時刻(anchor_ms)の種類", "値": int(c2["anchor_ms"].nunique())},
        {"項目": "2 回以上使われた時刻の数", "値": int(len(gd))},
        {"項目": "その時刻を使った行", "値": int(len(dup))},
        {"項目": "使われた回数が 2 でない時刻", "値": int((gd["count"] != 2).sum())},
        {"項目": f"再開前の日(< {RESUME_FIRST_DAY})と再開後の日(≥ {RESUME_FIRST_DAY})に跨る時刻", "値": straddle},
        {"項目": "重なった行の日の範囲", "値": f'{dup["day"].min()} 〜 {dup["day"].max()}'},
        {"項目": "対照 (i) の時刻の重なり(行)", "値": int(C[C["kind"] == "(i)無作為"]["anchor_ms"].duplicated().sum())},
    ]
    for g in (30, 60, 180):
        cg = C[C["kind"] == f"(iii)プラセボ_g{g}"]
        rows.append({"項目": f"対照 (iii) g={g} の時刻の重なり(行)", "値": int(cg["anchor_ms"].duplicated().sum())})
    out.append(block("t14_resume", "`controls.csv.gz` の kind・anchor_ms・day。再開の日は `full.log` 251〜253 行",
                     md(pd.DataFrame(rows))))
    vc = dup["day"].value_counts().sort_index()
    out.append(block("t14b_resume_days", "表 t14 の重なった行の `day` ごとの数",
                     md(pd.DataFrame({"日": vc.index, "行": vc.values}))))

    second = dup[dup["day"] >= RESUME_FIRST_DAY].index
    rows = []
    for lab_, cc in (("全部", c2), ("再開後の重なった行を除く", c2.drop(index=second))):
        for h in (10, 60, 300, 3600):
            rows.append({"対照 (ii)": lab_, "h": H_LABEL[h]} | ds_row(cc[f"react_{h}"], cc["day"]))
    M2 = M[~M["ref_id"].isin(c2.loc[second, "ref_id"])]
    for lab_, mm in (("対の差・全部", M), ("対の差・再開後の重なった行を除く", M2)):
        for h in (10, 60, 300, 3600):
            d = mm[f"react_{h}_p"].to_numpy(float) - mm[f"react_{h}_c"].to_numpy(float)
            rows.append({"対照 (ii)": lab_, "h": H_LABEL[h]} | ds_row(d, mm["day_p"]))
    out.append(block("t14c_resume_effect", "`controls.csv.gz`(kind = (ii))と表 t2 の対。"
                     f"「除く」= 重なった時刻のうち day ≥ {RESUME_FIRST_DAY} の行を落とした",
                     md(pd.DataFrame(rows))))

    # ---- 15. 2023-07-15(つなぎの段の列の不揃い) ----
    ch = src / "chunks" / "controls"
    heads = {}
    for p in sorted(ch.glob("*.csv.gz")):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            heads[p.stem.replace(".csv", "")] = f.readline().rstrip("\r\n").split(",")
    lack = sorted(d for d, h in heads.items() if "day_offset" not in h)
    d15 = C[C["day"] == "2023-07-15"]
    rows = [
        {"項目": "chunks/controls の日のファイル", "値": len(heads)},
        {"項目": "見出しに day_offset が無い日", "値": ", ".join(lack) if lack else "(無い)"},
        {"項目": "2023-07-15 のプリント", "値": int((P["day"] == "2023-07-15").sum())},
        {"項目": "2023-07-15 の対照の行(kind ごと)", "値": "; ".join(f"{k}={v}" for k, v in d15["kind"].value_counts().items())},
        {"項目": "対照 (ii) を 1 件も取れなかった日(最終の controls.csv.gz で)",
         "値": ", ".join(sorted(set(C["day"]) - set(c2["day"])))},
        {"項目": "最終の controls.csv.gz の (ii) の行で day_offset が空の行", "値": int(c2["day_offset"].isna().sum())},
        {"項目": "最終の controls.csv.gz の (ii) 以外の行で day_offset が空でない行",
         "値": int(C[C["kind"] != "(ii)合わせた時刻"]["day_offset"].notna().sum())},
    ]
    out.append(block("t15_0715", "`chunks/controls/<日>.csv.gz` の見出し行と `controls.csv.gz`", md(pd.DataFrame(rows))))

    # ---- 16. 限界の数 ----
    rows = []
    m10 = P["m10_signed"]
    rows.append({"項目": "プリントの直前 10 秒の値動きが清算の向き(m10_signed > 0)", "値": float((m10 > 0).mean())})
    rows.append({"項目": "同じく逆向き(m10_signed < 0)", "値": float((m10 < 0).mean())})
    rows.append({"項目": "同じく 0", "値": float((m10 == 0).mean())})
    rows.append({"項目": "同じく欠け", "値": float(m10.isna().mean())})
    rows.append({"項目": "材料 8 の建玉の桶が覆う(mat8_covered = 1)プリントの割合", "値": float((P["mat8_covered"] == 1).mean())})
    for h in (86400, 604800):
        rows.append({"項目": f"実のプリントの react_{h}({H_LABEL[h]})が NaN の行", "値": int(P[f"react_{h}"].isna().sum())})
    rows.append({"項目": "起点の約定の遅れ p0_lag_ms の中央値 / 95 分位(ms)",
                 "値": f'{np.nanpercentile(P["p0_lag_ms"], 50):.4g} / {np.nanpercentile(P["p0_lag_ms"], 95):.4g}'})
    P2 = pd.read_csv(src / "anchors_prints.csv.gz", usecols=["ts_ms", "t0_ms", "p0", "avg_price"])
    rows.append({"項目": "起点の約定の時刻が清算の時刻と同じ(t0_ms = ts_ms)プリントの割合",
                 "値": float((P2["t0_ms"] == P2["ts_ms"]).mean())})
    rows.append({"項目": "起点の価格が清算の average_price と同じ(相対差 < 1e-9)プリントの割合",
                 "値": float((np.abs(P2["p0"] - P2["avg_price"]) / P2["avg_price"] < 1e-9).mean())})
    out.append(block("t16_limits", "`anchors_prints.csv.gz` の `m10_signed`・`mat8_covered`・`react_86400`・`react_604800`・"
                     "`p0_lag_ms`・`ts_ms`・`t0_ms`・`p0`・`avg_price`",
                     md(pd.DataFrame(rows))))
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--in", dest="src", default=str(DEFAULT_IN))
    ap.add_argument("--section", choices=("tables", "manifest", "all"), default="all")
    a = ap.parse_args(argv)
    src = Path(a.src).resolve()
    if a.section in ("manifest", "all"):
        print(manifest(src))
    if a.section in ("tables", "all"):
        print(tables(src))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
