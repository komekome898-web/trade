#!/usr/bin/env python3
"""カード 9 (a) の全期間の走らせ(2023-06-25〜2024-10-14)の出力から、RESULTS.md・MANIFEST.md の表を作る。

- 読むだけ(入力のファイルを書き換えない。書き出しは標準出力だけ)。ネットワークを使わない。
- 測り直しはしない。`scripts/c9_run_a.py` がすでに書いた出力(`--in` の直下と、`chunks/scurve`・
  `chunks/controls` の見出し)と、`control_iv.py` の出力(`--iv`)を読み、並べ替え・絞り込み・既存の列どうしの
  引き算と、走らせと同じ集計関数 `dist_stats`(+ 日等重み平均の SE)を当てるだけ。
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
from bot.research import liq_cascade_v2 as v2  # noqa: E402
from bot.research.liq_cascade_v2 import dist_stats  # noqa: E402  (走らせと同じ集計の式)

DEFAULT_IN = REPO / "data" / "c9_run_a" / "full_20230625_20241014"
DEFAULT_IV = HERE / "control_iv_out"   # control_iv.py の出力
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
    esc = lambda x: str(x).replace("|", "\\|")  # noqa: E731  (GFM の表の中の縦棒)
    out = ["| " + " | ".join(esc(c) for c in cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(esc(fmt(r[c])) for c in cols) + " |")
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
def manifest(src: Path, ivdir: Path | None = None) -> str:
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
    if ivdir is not None and ivdir.exists():
        rr = []
        for dd in (ivdir, ivdir.parent / "control_ivh_out", ivdir.parent / "three_way_m_out", ivdir.parent / "control_iv_days_out"):
            if not dd.exists():
                continue
            for p in sorted(x for x in dd.iterdir() if x.is_file()):
                n, how = count_rows(p)
                rr.append({"ファイル": f"run_a/{dd.name}/{p.name}", "バイト": p.stat().st_size, "sha256": sha256(p),
                           "行数": ("-" if n < 0 else n), "数え方": how})
        out.append(block("manifest_iv", "第 2 稿・第 3 稿の追加の計算の出力(`control_iv.py`・`control_ivh.py`・`three_way_m.py`)", md(pd.DataFrame(rr))))
    sc = sorted((src / "chunks" / "scurve").glob("*.npz"))
    if sc:
        rr = []
        for p in sc:
            z = np.load(p)
            rr.append({"ファイル": f"chunks/scurve/{p.name}", "バイト": p.stat().st_size, "sha256": sha256(p),
                       "点の数(s の長さ)": int(z["s"].size), "列(遅れ × h)": int(z["v"].shape[1]) if z["v"].ndim == 2 else 0})
        df = pd.DataFrame(rr)
        tot = pd.DataFrame([{"ファイル": f"合計 {len(df)} ファイル", "バイト": int(df["バイト"].sum()), "sha256": "",
                             "点の数(s の長さ)": int(df["点の数(s の長さ)"].sum()), "列(遅れ × h)": ""}])
        out.append(block("manifest_scurve", f"`{src.relative_to(REPO)}/chunks/scurve/`(t8 の元。監査の聞く 22 で載せた)",
                         md(pd.concat([tot, df], ignore_index=True))))
    log = src.parent / "full.log"
    if log.exists():
        out.append(block("manifest_log", "走らせの記録",
                         md(pd.DataFrame([{"ファイル": str(log.relative_to(REPO)),
                                           "バイト": log.stat().st_size,
                                           "sha256": sha256(log),
                                           "行数": sum(1 for _ in open(log, encoding="utf-8"))}]))))
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# 集計の式(走らせの dist_stats に、日等重み平均の SE を足す。監査の直す 8)
# --------------------------------------------------------------------------- #
ST_COLS = ["n", "q25", "q50", "q75", "share_pos", "share_neg", "pooled_mean", "se_pooled_cluster",
           "day_eq_mean", "se_day_eq", "n_days"]
ST_SHORT = ["n", "q50", "pooled_mean", "se_pooled_cluster", "day_eq_mean", "se_day_eq", "n_days"]
PER = {"作る": "前半(標本内、列 period = 作る)", "測る": "後半(標本内、列 period = 測る)"}


def st(vals, days) -> dict:
    """`dist_stats` の値に、`se_day_eq`(日ごとの平均の標準偏差(ddof=1)÷ √日数 = 日等重み平均の SE)を足す。
    `pooled_mean` = 1 件ごとの平均(走らせの列 `mean`)、`se_pooled_cluster` = その日クラスタ SE
    (走らせの列 `se_day_cluster`。日等重み平均の SE ではない)。"""
    v = np.asarray(vals, dtype=float)
    d = np.asarray(days, dtype=object)
    s = dist_stats(v, d)
    ok = np.isfinite(v)
    se_eq = np.nan
    if ok.sum():
        dm = pd.Series(v[ok]).groupby(pd.Series(d[ok].astype(str))).mean().to_numpy()
        if dm.size > 1:
            se_eq = float(dm.std(ddof=1) / np.sqrt(dm.size))
    return {"n": s["n"], "q25": s["q25"], "q50": s["q50"], "q75": s["q75"],
            "share_pos": s["share_pos"], "share_neg": s["share_neg"], "pooled_mean": s["mean"],
            "se_pooled_cluster": s["se_day_cluster"], "day_eq_mean": s["day_eq_mean"],
            "se_day_eq": se_eq, "n_days": s["n_days"]}


def auc(score, y) -> float:
    s = np.asarray(score, float)
    y = np.asarray(y, float)
    ok = np.isfinite(s) & np.isfinite(y)
    s, y = s[ok], y[ok]
    n1, n0 = int((y == 1).sum()), int((y == 0).sum())
    if n1 == 0 or n0 == 0:
        return np.nan
    r = pd.Series(s).rank().to_numpy()
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


BOOT_B, BOOT_SEED = 200, 20261003


def boot_q(vals, days, qs=(25, 50, 75), b=BOOT_B, seed=BOOT_SEED) -> dict:
    """日ブロックのブートストラップ(日を置換ありで引き直す)で、分位の SE を出す(監査 3 回目の直す 8)。"""
    v = np.asarray(vals, float)
    d = np.asarray(days, dtype=object).astype(str)
    ok = np.isfinite(v)
    v, d = v[ok], d[ok]
    if v.size == 0:
        return {q: np.nan for q in qs}
    u, inv = np.unique(d, return_inverse=True)
    groups = [np.flatnonzero(inv == i) for i in range(u.size)]
    rng = np.random.default_rng(seed)
    est = {q: [] for q in qs}
    for _ in range(b):
        pick = rng.integers(0, u.size, u.size)
        idx = np.concatenate([groups[i] for i in pick])
        qv = np.percentile(v[idx], qs)
        for q, x in zip(qs, qv):
            est[q].append(x)
    return {q: float(np.std(est[q], ddof=1)) for q in qs}


def klass(diff, se, real_abs) -> str:
    """区分の規則(監査 4 回目の止める 1 を受けたリードの決定、第 5 稿): まず (x)「|対の差| > 2 × SE なら 2SE の外、それ以外は
    2SE の内」を当て、次に (y)「MDE(= 2.8 × SE)が |実| 以上なら MDE ≥ |実|、未満なら MDE < |実|」を当てる。
    |実| < SE は区分にせず、別の列の印にする(`small`)。SE が無い行は「SE が無い」。"""
    if not (np.isfinite(se) and np.isfinite(diff)):
        return "SE が無い"
    x = "2SE の外" if abs(diff) > 2 * se else "2SE の内"
    if not np.isfinite(real_abs):
        return x
    y = "MDE ≥ |実|" if 2.8 * se >= real_abs else "MDE < |実|"
    return f"{x}・{y}"


def small(se, real_abs) -> str:
    """|実| が対の差の SE より小さい行の印(区分を上書きしない)。"""
    if np.isfinite(se) and np.isfinite(real_abs) and real_abs < se:
        return "印"
    return ""


def tables(src: Path, ivdir: Path) -> str:
    out: list[str] = []
    nblk = []

    def B(name, source, df_or_text):
        body = md(df_or_text) if isinstance(df_or_text, pd.DataFrame) else df_or_text
        if isinstance(df_or_text, pd.DataFrame):
            nblk.append((name, len(df_or_text), int(df_or_text.shape[0] * df_or_text.shape[1])))
        out.append(block(name, source, body))

    meta = json.loads((src / "run_meta.json").read_text(encoding="utf-8"))
    model = json.loads((src / "three_way_model.json").read_text(encoding="utf-8"))
    ivm = json.loads((ivdir / "control_iv_meta.json").read_text(encoding="utf-8"))
    R = pd.read_csv(src / "dist_reaction.csv")
    Pd = pd.read_csv(src / "dist_policy.csv")
    L = pd.read_csv(src / "label_counts.csv")
    AC = pd.read_csv(src / "policy_action_counts.csv")
    JC = pd.read_csv(src / "policy_judge_counts.csv")
    CAL = pd.read_csv(src / "three_way_calibration.csv")

    xk = [f"{k}_{h}" for h in H_ALL for k in ("react", "mfe", "mae", "giveback")]
    M4 = v2.MAT_COL[4]
    pcols = ["print_id", "day", "side", "sign", "qty", "before_seal", "opened_before", "period",
             "m10_signed", "m60_signed", "mat1_same_side_count_60s_and_elapsed", "mat8_covered", "cont_60",
             M4, "mat4_bounce_bp", v2.MAT_COL[12], "p0_lag_ms", "ts_ms", "t0_ms", "p0", "avg_price"] + \
        [f"g{g}_pos_post" for g in (30, 60, 180)] + [f"g{g}_qty_so_far" for g in (30, 60, 180)] + xk
    P = pd.read_csv(src / "anchors_prints.csv.gz", usecols=pcols, dtype={"day": str, "print_id": str})
    P["scene"] = np.where(P["mat1_same_side_count_60s_and_elapsed"].fillna(0) >= 1, "連鎖の中", "1件目")
    P["a10"], P["a60"] = P["m10_signed"].abs(), P["m60_signed"].abs()
    C = pd.read_csv(src / "controls.csv.gz", usecols=["kind", "day", "anchor_ms", "ref_id", "day_offset"] + xk,
                    dtype={"day": str, "ref_id": str})
    IV = pd.read_csv(ivdir / "controls_iv.csv.gz", dtype={"day": str, "ref_id": str})
    RA = pd.read_csv(ivdir / "prints_reanchor.csv.gz", dtype={"day": str, "print_id": str})
    REP = pd.read_csv(ivdir / "ii_reproduction.csv.gz", dtype={"print_id": str})
    # L-920: 連鎖の損益(レグの和)は %(pnl_pct)。前の出力は pnl_bp(bp)なので / 100 して読む
    CA = v2.with_legacy_columns(pd.read_csv(src / "policy_cascades.csv.gz", dtype={"day": str}),
                                keep={"pnl_pct"})
    CA["incl"] = np.where(CA["entered"] == 1, CA["pnl_pct"], np.where(CA["missing"] == 1, np.nan, 0.0))
    CA["per"] = CA["period"].map(PER)
    LG = pd.read_csv(src / "policy_legs.csv.gz", dtype={"day": str})
    TP = pd.read_csv(src / "three_way_probs.csv.gz", dtype={"day": str})
    c2 = C[C["kind"] == "(ii)合わせた時刻"]
    ivhdir, twdir = ivdir.parent / "control_ivh_out", ivdir.parent / "three_way_m_out"
    IVH = pd.read_csv(ivhdir / "controls_ivh.csv.gz", dtype={"day": str, "ref_id": str})
    PVv = pd.read_csv(ivhdir / "prints_versions.csv.gz", dtype={"day": str, "print_id": str})
    IVV = pd.read_csv(ivhdir / "controls_iv_versions.csv.gz", dtype={"day": str, "ref_id": str})
    CZ = pd.read_csv(ivhdir / "iv_unmatched_cause.csv.gz", dtype={"day": str, "print_id": str})
    ivhm = json.loads((ivhdir / "control_ivh_meta.json").read_text(encoding="utf-8"))
    TPM = pd.read_csv(twdir / "three_way_m_probs.csv.gz", dtype={"day": str})
    MM = json.loads((twdir / "three_way_m_model.json").read_text(encoding="utf-8"))
    CALM = pd.read_csv(twdir / "three_way_m_calibration.csv")
    dydir = ivdir.parent / "control_iv_days_out"
    IVD0 = pd.read_csv(dydir / "controls_iv_d0.csv.gz", dtype={"day": str, "ref_id": str})
    IVD7 = pd.read_csv(dydir / "controls_iv_d7.csv.gz", dtype={"day": str, "ref_id": str})
    GBN = pd.read_csv(dydir / "grid_band_noliq.csv")
    CZ5 = pd.read_csv(dydir / "ivh_unmatched_cause.csv.gz", dtype={"day": str, "print_id": str})
    dym = json.loads((dydir / "control_iv_days_meta.json").read_text(encoding="utf-8"))
    CA3 = v2.with_legacy_columns(pd.read_csv(twdir / "policy_cascades_3m.csv.gz", dtype={"day": str}),
                                 keep={"pnl_pct"})
    p3m = json.loads((twdir / "policy_3m_meta.json").read_text(encoding="utf-8"))
    G = {"実": P, "対照(i)": C[C["kind"] == "(i)無作為"], "対照(ii)": c2, "対照(iv)": IV, "対照(iv-h)": IVH}

    # ---- t0 走らせの数 ----
    tm = meta["対照の取れた数"]
    rows = [("期間", " 〜 ".join(meta["期間"]), "run_meta 期間"), ("暦日", meta["日数"], "run_meta 日数"),
            ("清算の生の行 / 一意化したプリント", f'{meta["一意化"]["生の行"]} / {meta["一意化"]["一意"]}', "run_meta 一意化"),
            ("多重度 2 の組 / 4 の組", f'{meta["一意化"]["多重度"]["2"]} / {meta["一意化"]["多重度"]["4"]}', "run_meta 一意化.多重度"),
            ("プリントのある日", int(P["day"].nunique()), "anchors_prints.day"),
            ("期間の中でプリントの無い日",
             ", ".join(sorted(set(pd.date_range(*meta["期間"]).strftime("%Y-%m-%d")) - set(P["day"]))),
             "期間の暦日 − anchors_prints.day"),
            ("束 g=30 / 60 / 180", " / ".join(str(meta["束の数"][g]) for g in ("30", "60", "180")), "run_meta 束の数")]
    for k in ("(i)無作為", "(ii)合わせた時刻", "(iii)プラセボ_g30", "(iii)プラセボ_g60", "(iii)プラセボ_g180"):
        rows.append((f"対照 {k} 取れた / 求めた", f'{tm[k]["取れた"]} / {tm[k]["求めた"]}', f"run_meta 対照の取れた数.{k}"))
    rows.append(("対照 (iv) 取れた / 求めた", f'{ivm["対照(iv)取れた"]} / {ivm["プリント"]}', "control_iv_meta.json"))
    rows.append(("対照 (iv-h) 取れた / 求めた", f'{ivhm["対照(iv-h)取れた"]} / {ivhm["プリント"]}', "control_ivh_meta.json"))
    rows.append(("control_ivh.py の所要_秒", ivhm["所要_秒"], "control_ivh_meta.json"))
    rows.append(("対照 (ii) 日のずれ別(0,−1,+1,−2,+2,−3,+3)",
                 " / ".join(str(tm["(ii)日のずれ別"][o]) for o in ("0", "-1", "1", "-2", "2", "-3", "3")), "run_meta"))
    rows.append(("対照 (iv) 日のずれ別(同じ順)",
                 " / ".join(str(ivm["対照(iv)日のずれ別"][o]) for o in ("0", "-1", "1", "-2", "2", "-3", "3")),
                 "control_iv_meta.json"))
    rep = ivm["(ii)の再現"]
    rows.append(("(ii) の再現: 走らせで取れた / 台本で取れた / 時刻が同じ / 時刻が違う / 片方だけ",
                 f'{rep["走らせで取れた"]} / {rep["この台本で取れた"]} / {rep["両方で取れて時刻が同じ"]} / '
                 f'{rep["両方で取れて時刻が違う"]} / {rep["片方だけ取れた"]}', "control_iv_meta.json (ii)の再現"))
    mx = max((v["最大の差_bp"] or 0) for v in ivm["版Aのreactと走らせのreactの一致"].values())
    nn = sum(v["片方だけNaN"] for v in ivm["版Aのreactと走らせのreactの一致"].values())
    rows.append(("起点 版A の react と走らせの react: 最大の差(bp)/ 片方だけ NaN の数(12 本の和)", f"{mx:.3g} / {nn}",
                 "control_iv_meta.json 版Aのreactと走らせのreactの一致"))
    nb = int((P["before_seal"] == 0).sum())
    rows.append(("2023-12-18 以降(bitFlyer の封印の境の後)のプリント / 全部 / 割合 / 日",
                 f'{nb} / {len(P)} / {nb / len(P):.3f} / {P.loc[P["before_seal"] == 0, "day"].nunique()}', "anchors_prints.before_seal = 0"))
    rows.append(("後半(列 period = 測る)のプリントのうち 2023-12-18 以降の割合",
                 f'{float((P.loc[P["period"] == "測る", "before_seal"] == 0).mean()):.3f}', "anchors_prints.period・before_seal"))
    rows.append(("対照 (iv) 同じ日だけの版 / ±7 日の版 取れた / 求めた",
                 f'{dym["取れた"]["d0"]} / {dym["取れた"]["d7"]} / {len(P)}', "control_iv_days_meta.json"))
    rows.append(("control_iv_days.py / three_way_m_policy.py の所要_秒", f'{dym["所要_秒"]} / {p3m["所要_秒"]}',
                 "control_iv_days_meta.json・policy_3m_meta.json"))
    rows.append(("新の 3 択の確率の、three_way_m.py との最大の差", p3m["確率の一致(three_way_m_probs との最大の差)"], "policy_3m_meta.json"))
    OC = v2.with_legacy_columns(pd.read_csv(twdir / "policy_cascades_3m_oldcheck.csv.gz",
                                            dtype={"day": str}), keep={"pnl_pct"})
    RUNC = v2.with_legacy_columns(pd.read_csv(src / "policy_cascades.csv.gz", dtype={"day": str}),
                                  keep={"pnl_pct"})
    RUNC = RUNC[(RUNC["policy"] == "規則_3択") & RUNC["day"].isin(set(OC["day"]))]
    MC = OC.merge(RUNC, on=["bundle_id", "gap_s", "delay_s", "type"], suffixes=("_n", "_r"))
    rows.append(("three_way_m_policy.py を旧の 13 本で流した確かめ: 日 / 行 / 走らせの行 / 一致した組 / pnl の最大の差 / entered の違い",
                 f'{OC["day"].nunique()} / {len(OC)} / {len(RUNC)} / {len(MC)} / {np.nanmax(np.abs(MC["pnl_pct_n"] - MC["pnl_pct_r"])):.3g} / {int((MC["entered_n"] != MC["entered_r"]).sum())}',
                 "three_way_m_out/policy_cascades_3m_oldcheck.csv.gz と policy_cascades.csv.gz"))
    rows.append(("約定の欠けた日(窓の中)", ", ".join(meta["約定の欠けた日(窓の中)"]), "run_meta"))
    rows.append(("清算の zip が無く (iv) の候補から外した日", ", ".join(ivm["清算のzipが無く候補から外した日"]),
                 "control_iv_meta.json"))
    rows.append(("規則_3択 前半(作る)/ 後半(測る)", f'{"〜".join(model["作る日"])} / {"〜".join(model["測る日"])}',
                 "three_way_model.json"))
    rows.append(("run_meta の所要_秒.段2 合計 / 全体 / 最大メモリ_MB",
                 f'{meta["所要_秒"]["段2 合計"]} / {meta["所要_秒"]["全体"]} / {meta["最大メモリ_MB(ru_maxrss)"]}',
                 "run_meta(3 回目の起動だけの値)"))
    rows.append(("control_iv.py の所要_秒", ivm["所要_秒"], "control_iv_meta.json"))
    B("t0_meta", "`run_meta.json`・`control_iv_meta.json`・`anchors_prints.csv.gz`(右端の列)",
      pd.DataFrame(rows, columns=["項目", "値", "出所"]))

    # ---- t0s 設定値と出所の 3 分類(監査の直す 14) ----
    lg_mod = v2.logit_module()
    rows = [
        ("対照 (ii)(iv) の前後に清算無しの幅", f"±{v2.CTRL2_NO_LIQ_MS // 60000} 分", "仮定", "前の O-3c の Q7 の委任先(CONTINUE 設計 120 行)。引き継ぎはリードの決定(設計 §6 の 6)"),
        ("対照 (ii)(iv) の帯", f"{v2.CTRL2_N_BANDS} 分位", "仮定", "同上"),
        ("対照 (ii)(iv) の格子", f"{v2.CTRL_GRID_MS // 1000} 秒", "仮定", "同上"),
        ("対照 (ii)(iv)(iv-h) の日のずれ", f"±{max(v2.CTRL2_DAY_OFFSETS)} 日(第 4 稿で同じ日だけ・±7 日の (iv) を足した)", "仮定", "リード(決定 第 2 稿の 2)"),
        ("対照 (iv) の大きさの帯(|m10|・|m60|)", f"{v2.CTRL2_N_BANDS} 分位", "仮定", "リード(この回の指示「|m10| と |m60| の水準(10 分位)」)"),
        ("対照 (iii) の規模の許容", f"±{v2.PLACEBO_TOL:.0%}", "仮定", "前の段 0 の委任先(liq_response.sample_placebo_windows の size_tolerance。その docstring に「判断の置き所」)"),
        ("対照 (i)(iii) の清算からの余白", f"±{v2.CTRL_MARGIN_MS // 60000} 分", "仮定", "段 A の対照 (i) の委任先"),
        ("値の穴", f"{v2.STALENESS_MS // 1000} 秒", "仮定", "前の道具の STALENESS_MS"),
        ("3 択の帯の幅", "0.02", "仮定", "リード(L-277 のオーナーの指摘「0.1刻みの帯で判断してるからわからんねやろ」を受けて、o3c_signal_value.BAND_STEP)"),
        ("3 択の区別の幅", "2 SE", "仮定", "前の道具(o3c_signal_value.calibration_table)"),
        ("3 択の分割数", f"{lg_mod.N_FOLDS}", "仮定", "前の道具(o3c_signal_logit.N_FOLDS)"),
        ("3 択の L2", f"{lg_mod.L2_LAMBDA:g}", "仮定", "前の道具(o3c_signal_logit.L2_LAMBDA)"),
        ("束ね方 g", "/".join(map(str, v2.GAPS_S)) + " 秒", "仮定", "段 A の委任先(設計 §3.1)"),
        ("遅れ d", "/".join(map(str, v2.DELAYS_S)) + " 秒", "仮定", "前の方策の段のリード(設計 §3.1)"),
        ("見る時間 h", f"{len(v2.HORIZONS_S)} 本", "仮定", "前の段の格子の和 + W1 C4(設計 §3.1)"),
        ("s の上限", f"{v2.S_MAX} 秒", "仮定", "設計 §3.1(g の最大)"),
        ("1 枚 = 100 USD", "100", "実測", "置き場の metrics からの計算(README_TOOL_A)。銘柄を指した一次資料は未確認"),
        ("清算の向き(SELL = ロングの強制決済)", "-", "一次資料", "Binance の文書の逐語(CARD.md 98 行の引用)"),
        ("3 分位の切り(t4m・t6d・t9)", "3", "仮定", "リード(設計 §9-4「3 分位」)。t4m の m・材料 4 への当てはめは作業者"),
        ("上位 10 日の除き方(t6e)", "10 日 × 正/負/絶対値", "仮定", "作業者(監査の直す 4 の「上位 10 日」に合わせた)"),
        ("起点 版C の +1 秒(t1r・t2v)", "1 秒", "仮定", "作業者(状態機械の遅れ 1 秒と同じ)。リードが追認(監査の聞く 24)"),
        ("起点 版D(押した向きの成行の最初の約定)", "-", "仮定", "作業者(止める 2 の (b) で、プリントと対照に同じ規則で置ける起点として)"),
        ("MDE の 2.8(t2・t2stat・t6f)", "2.8 × SE", "仮定", "慣用の値(両側 5%・検出力 80%)。作業者が置き、リードが追認(聞く 24)"),
        ("(iv)(iv-h) の候補から清算の zip の無い日を外す", "-", "仮定", "作業者(監査 1 回目の直す 10)。リードが追認(聞く 24)"),
        ("(iv-h) の時の帯", "UTC の 0〜23 時", "仮定", "リード(この回の指示「帯 = 今の (iv) の帯 × 時」)"),
        ("区分の (x) の境", "2 × SE", "仮定", "リード(監査 3 回目の止める 1 への応答で 2SE と決め、4 回目の止める 1 を受けて (x) を先に当てる順にした)"),
        ("「実の値動きが SE より小さい」の印の境", "|実| < SE", "仮定", "リード(同上。区分ではなく印)"),
        ("分位の SE の日ブロック再抽出", f"{BOOT_B} 回・種 {BOOT_SEED}", "仮定", "作業者。別の種で SE が安定するかは確かめていない"),
        ("(iv) の日の幅の版", "同じ日だけ / ±7 日", "仮定", "リード(監査 3 回目の止める 3・直す 14 への指示)。±7 日の 7 は指示の値"),
        ("トリム平均の落とす割合", "両側 1%・5%・10%", "仮定", "作業者(監査 4 回目の直す 4 が挙げた割合に合わせた)"),
        ("新の 3 択の手順の確かめ", "後半の全 239 日", "仮定", "作業者(第 4 稿は 5 日。監査 4 回目の直す 13 で全日にした)"),
        ("3 択の作り直しで足した材料 |m10|・|m60|", "2 本", "仮定", "リード(この回の指示。代替の記録の回答者 A の 1 位)"),
    ]
    B("t0s_settings", "`liq_cascade_v2` の定数・`o3c_signal_logit` の定数を台本で読んだ(値の列)。分類は 一次資料 / 実測 / 仮定(KNOWN_ANSWERS 80 行)",
      pd.DataFrame(rows, columns=["設定", "値", "出所の分類", "誰の・どこの"]))

    # ---- t1 値動き: 実 vs (i)(ii)(iv) ----
    rows = []
    for h in H_ALL:
        for gname, df in G.items():
            rows.append({"h": H_LABEL[h], "群": gname} | st(df[f"react_{h}"], df["day"]))
    B("t1_react", "実 = `anchors_prints.csv.gz`、(i)(ii) = `controls.csv.gz`、(iv) = `control_iv_out/controls_iv.csv.gz` の react_h。"
      "集計は `st`(dist_stats + se_day_eq)。実は清算の向き、対照は直前 10 秒の変位の向きに正", pd.DataFrame(rows))

    # ---- t1r 起点を変えた react ----
    rows = []
    RAm = RA.merge(P[["print_id", "avg_price"]], on="print_id")
    for h in H_ALL:
        for v_, lab in (("A", "版A 走らせと同じ(ts 以後の最初)"), ("B", "版B 版A の約定より厳密に後の最初"),
                        ("C", "版C ts + 1 秒 以後の最初")):
            rows.append({"h": H_LABEL[h], "起点": lab} | st(RA[f"react{v_}_{h}"], RA["day"]))
    for h in H_ALL:
        rows.append({"h": H_LABEL[h], "起点": "版D ts 以後の、清算の向きの成行の最初"} | st(PVv[f"reactD_{h}"], PVv["day"]))
    rows = sorted(rows, key=lambda r: (H_ALL.index([k for k, v in H_LABEL.items() if v == r["h"]][0]), r["起点"]))
    B("t1r_reanchor", "版A・B・C = `control_iv_out/prints_reanchor.csv.gz`、版D = `control_ivh_out/prints_versions.csv.gz`(react の規則は走らせと同じ。版A は走らせの react と一致、t0)",
      pd.DataFrame(rows))
    rows = []
    RAm = RAm.merge(PVv[["print_id", "t0_D", "p0_D"]], on="print_id")
    for v_ in ("A", "B", "C", "D"):
        lag = (RAm[f"t0_{v_}"] - RAm["ts_ms"]).to_numpy(float)
        rows.append({"起点": v_, "起点の時刻 − ts の中央値(ms)": float(np.nanmedian(lag)),
                     "95 分位(ms)": float(np.nanpercentile(lag, 95)),
                     "起点の価格 = average_price の割合": float(
                         (np.abs(RAm[f"p0_{v_}"] - RAm["avg_price"]) / RAm["avg_price"] < 1e-9).mean())})
    B("t1r_lag", "`prints_reanchor.csv.gz` の t0_*・p0_* と `anchors_prints.csv.gz` の ts_ms・avg_price", pd.DataFrame(rows))

    # ---- t1b mfe/mae/giveback ----
    rows = []
    for k in ("mfe", "mae", "giveback"):
        for h in (10, 60, 300, 3600):
            for gname, df in G.items():
                s = st(df[f"{k}_{h}"], df["day"])
                rows.append({"量": k, "h": H_LABEL[h], "群": gname, "n": s["n"], "q25": s["q25"], "q50": s["q50"],
                             "q75": s["q75"], "day_eq_mean": s["day_eq_mean"], "se_day_eq": s["se_day_eq"]})
    B("t1b_excursion", "t1 と同じファイルの mfe・mae・giveback(h = 10 秒・60 秒・5 分・60 分)。**群ごとに母集団が違う**(実 = 全プリント、(iv)(iv-h) = 取れた分だけ。同じ母集団の版は t1b_same)", pd.DataFrame(rows))
    rows = []
    for lab, cc in (("(iv)", IV), ("(iv-h)", IVH)):
        sub = P[P["print_id"].isin(set(cc["ref_id"]))]
        for k in ("mfe", "mae", "giveback"):
            for h in (10, 60, 300, 3600):
                for gl, df in ((f"実({lab} が取れたプリント)", sub), (f"対照{lab}", cc)):
                    s = st(df[f"{k}_{h}"], df["day"])
                    rows.append({"組": lab, "量": k, "h": H_LABEL[h], "群": gl, "n": s["n"], "q50": s["q50"],
                                 "pooled_mean": s["pooled_mean"], "day_eq_mean": s["day_eq_mean"], "se_day_eq": s["se_day_eq"]})
    B("t1b_same", "t1b を、対照が取れたプリントだけ(同じ母集団)にした版。実 = `anchors_prints.csv.gz` の該当の print_id", pd.DataFrame(rows))

    # ---- t2 対の差 (ii)(iv) ----
    Pi = P.set_index("print_id")
    pairs = {}
    for lab, cc in (("(ii)", c2), ("(iv)", IV), ("(iv-h)", IVH)):
        M = cc.merge(P[["print_id", "day", "before_seal", "scene"] + xk], left_on="ref_id", right_on="print_id",
                     suffixes=("_c", "_p"))
        pairs[lab] = M
    rows = []
    for h in H_ALL:
        for lab, M in pairs.items():
            d = M[f"react_{h}_p"].to_numpy(float) - M[f"react_{h}_c"].to_numpy(float)
            s = st(d, M["day_p"])
            rows.append({"h": H_LABEL[h], "対照": lab} | s | {"q75−q25": s["q75"] - s["q25"],
                        "MDE(day_eq)": 2.8 * s["se_day_eq"], "MDE(pooled)": 2.8 * s["se_pooled_cluster"]})
    B("t2_paired", "対照の `ref_id` を `anchors_prints.csv.gz` の `print_id` につないだ組。値 = react_h(プリント)− react_h(対照)、日 = プリントの日。MDE = 2.8 × SE(仮定、t0s)",
      pd.DataFrame(rows))

    both = set(pairs["(ii)"]["print_id"]) & set(pairs["(iv)"]["print_id"])
    rows = []
    for h in (5, 10, 60, 300, 900, 3600, 14400):
        for lab, M in pairs.items():
            m = M["print_id"].isin(both)
            d = M.loc[m, f"react_{h}_p"].to_numpy(float) - M.loc[m, f"react_{h}_c"].to_numpy(float)
            rows.append({"h": H_LABEL[h], "値": f"対の差 {lab}"} | st(d, M.loc[m, "day_p"]))
        M = pairs["(iv)"][pairs["(iv)"]["print_id"].isin(both)]
        rows.append({"h": H_LABEL[h], "値": "実のプリントの react(同じプリント)"} | st(M[f"react_{h}_p"], M["day_p"]))
    B("t2s_samepop", f"(ii) と (iv) の両方が取れたプリント {len(both)} 件に限った対の差(母集団をそろえた比べ)",
      pd.DataFrame(rows))

    # ---- t2stat 止める 1: 統計ごとの向きと分類(監査 3 回目の止める 1・直す 8) ----
    rows = []
    for lab in ("(iv)", "(iv-h)"):
        M = pairs[lab]
        for h in (60, 300, 900, 3600, 14400):
            x, y = M[f"react_{h}_p"].to_numpy(float), M[f"react_{h}_c"].to_numpy(float)
            dd = M["day_p"]
            sx, sy, sd = st(x, dd), st(y, dd), st(x - y, dd)
            for stat, se_key in (("pooled_mean", "se_pooled_cluster"), ("day_eq_mean", "se_day_eq")):
                se = sd[se_key]
                rows.append({"対照": lab, "h": H_LABEL[h], "n": sd["n"], "統計": stat, "実(同じプリント)": sx[stat], "対照の値": sy[stat],
                             "対の差": sd[stat], "対の差の SE": se, "SE の種類": se_key, "MDE = 2.8×SE": 2.8 * se,
                             "|実の react|": abs(sx[stat]), "区分": klass(sd[stat], se, abs(sx[stat])), "実の値動きが SE より小さい": small(se, abs(sx[stat]))})
            bq = boot_q(x - y, dd)
            for q in (25, 50, 75):
                stat = f"q{q}"
                se = bq[q]
                rows.append({"対照": lab, "h": H_LABEL[h], "n": sd["n"], "統計": f"{stat}(対の差の分布の分位)", "実(同じプリント)": sx[stat],
                             "対照の値": sy[stat], "対の差": sd[stat], "対の差の SE": se, "SE の種類": "日ブロックの再抽出",
                             "MDE = 2.8×SE": 2.8 * se, "|実の react|": abs(sx[stat]), "区分": (klass(sd[stat], se, abs(sx[stat])) if q == 50 else "区分を当てない(差の分布の広がりの分位)"), "実の値動きが SE より小さい": (small(se, abs(sx[stat])) if q == 50 else "")})
            # 実と対照の中央値の差(周辺の中央値の差)と、その日ブロックの SE
            u = M["day_p"].astype(str).to_numpy()
            uu, inv = np.unique(u, return_inverse=True)
            groups = [np.flatnonzero(inv == i) for i in range(uu.size)]
            rng = np.random.default_rng(BOOT_SEED)
            fx, fy = np.isfinite(x), np.isfinite(y)
            est = []
            for _ in range(BOOT_B):
                idx = np.concatenate([groups[i] for i in rng.integers(0, uu.size, uu.size)])
                est.append(np.median(x[idx][fx[idx]]) - np.median(y[idx][fy[idx]]))
            se = float(np.std(est, ddof=1))
            md_ = float(np.median(x[fx]) - np.median(y[fy]))
            rows.append({"対照": lab, "h": H_LABEL[h], "n": sd["n"], "統計": "q50 の差(実の中央値 − 対照の中央値)", "実(同じプリント)": sx["q50"],
                         "対照の値": sy["q50"], "対の差": md_, "対の差の SE": se, "SE の種類": "日ブロックの再抽出",
                         "MDE = 2.8×SE": 2.8 * se, "|実の react|": abs(sx["q50"]), "区分": klass(md_, se, abs(sx["q50"])), "実の値動きが SE より小さい": small(se, abs(sx["q50"]))})
            rows.append({"対照": lab, "h": H_LABEL[h], "n": sd["n"], "統計": "q75−q25(幅)", "実(同じプリント)": sx["q75"] - sx["q25"],
                         "対照の値": sy["q75"] - sy["q25"], "対の差": np.nan, "対の差の SE": np.nan, "SE の種類": "",
                         "MDE = 2.8×SE": np.nan, "|実の react|": np.nan, "区分": "対の差が無い行"})
    B("t2stat", "t2 の (iv)・(iv-h) の組を統計ごとに並べ、区分を機械で当てた。「実(同じプリント)」= 対照が取れたプリントの react_h、「対照の値」= 対照の react_h、"
      "「対の差」= 1 組ごとの差の統計。分位の SE は日ブロックの再抽出(日を置換ありで 200 回、種 20261003)。"
      "区分 = (x) |対の差| > 2 SE なら「2SE の外」/ それ以外「2SE の内」、(y) MDE(2.8 × SE)≥ |実| なら「MDE ≥ |実|」/ それ以外「MDE < |実|」。"
      "|実| < SE の行は区分を変えず、列「実の値動きが SE より小さい」に印(`klass`・`small`)。q25・q75 の行は差の分布の広がりの分位なので区分を当てない", pd.DataFrame(rows))

    from scipy.stats import trim_mean
    rows = []
    for lab in ("(iv)", "(iv-h)"):
        M = pairs[lab]
        for h in (60, 300, 900, 3600, 14400):
            d = (M[f"react_{h}_p"] - M[f"react_{h}_c"]).to_numpy(float)
            d = d[np.isfinite(d)]
            r = {"対照": lab, "h": H_LABEL[h], "n": d.size, "平均(pooled_mean)": float(d.mean())}
            for c in (0.01, 0.05, 0.10):
                r[f"{int(c * 100)}% トリム平均(両側)"] = float(trim_mean(d, c))
            r["中央値"] = float(np.median(d))
            rows.append(r)
    B("t2trim", "t2 の (iv)・(iv-h) の組ごとの対の差(react_h(プリント)− react_h(対照))の平均と、両側を 1%・5%・10% ずつ落としたトリム平均"
      "(`scipy.stats.trim_mean`、1 件ごと、日の重みなし)と中央値。監査 4 回目の直す 4", pd.DataFrame(rows))

    rows = []
    for lab in ("(iv)", "(iv-h)"):
        M = pairs[lab]
        for scn in ("1件目", "連鎖の中"):
            mm = M[M["scene"] == scn]
            for h in (5, 10, 60, 300, 900, 3600, 14400):
                d = mm[f"react_{h}_p"].to_numpy(float) - mm[f"react_{h}_c"].to_numpy(float)
                s = st(d, mm["day_p"])
                sx = st(mm[f"react_{h}_p"], mm["day_p"])
                rows.append({"対照": lab, "場面": scn, "h": H_LABEL[h]} | {k: s[k] for k in ST_SHORT} |
                            {"q25": s["q25"], "q75": s["q75"], "MDE(day_eq)": 2.8 * s["se_day_eq"],
                             "実の react の day_eq_mean": sx["day_eq_mean"],
                             "区分(day_eq_mean)": klass(s["day_eq_mean"], s["se_day_eq"], abs(sx["day_eq_mean"])),
                             "印(day_eq_mean)": small(s["se_day_eq"], abs(sx["day_eq_mean"])),
                             "実の react の pooled_mean": sx["pooled_mean"],
                             "区分(pooled_mean)": klass(s["pooled_mean"], s["se_pooled_cluster"], abs(sx["pooled_mean"])),
                             "印(pooled_mean)": small(s["se_pooled_cluster"], abs(sx["pooled_mean"]))})
    B("t2first", "t2 の (iv)・(iv-h) の組を、プリントの場面(1件目 = 直前 60 秒に同じ側の清算が無い / 連鎖の中)で分けた。区分は t2stat と同じ規則(|実| = その場面の実の react)", pd.DataFrame(rows))

    rows = []
    VV = {"(iv)": IVV.merge(PVv, left_on="ref_id", right_on="print_id", suffixes=("_c", "_p")),
          "(iv-h)": IVH.merge(PVv, left_on="ref_id", right_on="print_id", suffixes=("_c", "_p"))}
    for lab, M in VV.items():
        A = pairs[lab]
        for v_ in ("A", "B", "C", "D"):
            for h in (5, 10, 60, 300, 3600):
                if v_ == "A":
                    xr, yr, dd = A[f"react_{h}_p"].to_numpy(float), A[f"react_{h}_c"].to_numpy(float), A["day_p"]
                else:
                    xr, yr = M[f"react{v_}_{h}_p"].to_numpy(float), M[f"react{v_}_{h}_c"].to_numpy(float)
                    dd = M["day_p"] if "day_p" in M else M["day"]
                sx, s = st(xr, dd), st(xr - yr, dd)
                for stat, se_key in (("pooled_mean", "se_pooled_cluster"), ("day_eq_mean", "se_day_eq")):
                    rows.append({"対照": lab, "起点の版(両側に同じ規則)": v_, "h": H_LABEL[h], "統計": stat, "n": s["n"],
                                 "実の react": sx[stat], "対の差": s[stat], "SE": s[se_key], "MDE": 2.8 * s[se_key],
                                 "区分": klass(s[stat], s[se_key], abs(sx[stat])), "実の値動きが SE より小さい": small(s[se_key], abs(sx[stat]))})
    B("t2v_anchor", "起点の版をプリントと対照の両側に同じ規則で当てた対の差。版A = 起点の時刻以後の最初の約定(走らせ)、B = A の約定より厳密に後、"
      "C = +1 秒以後、D = 押した向きの成行の最初の約定。B・C・D = `control_ivh_out/prints_versions.csv.gz` と `controls_iv_versions.csv.gz`・`controls_ivh.csv.gz`。"
      "「実の react」= 同じ版の起点でのプリントの react。区分は t2stat と同じ規則",
      pd.DataFrame(rows))

    rows = []
    PL = P[["print_id", "ts_ms", "t0_ms"]].merge(PVv[["print_id", "t0_B", "t0_C", "t0_D"]], on="print_id")
    lag_sets = [("プリント(全部)", "A", (PL["t0_ms"] - PL["ts_ms"]).to_numpy(float))] + \
        [("プリント(全部)", v_, (PL[f"t0_{v_}"] - PL["ts_ms"]).to_numpy(float)) for v_ in ("B", "C", "D")] + \
        [("対照 (iv)", "A", (IV["t0_ms"] - IV["anchor_ms"]).to_numpy(float))] + \
        [("対照 (iv)", v_, (IVV[f"t0_{v_}"] - IVV["anchor_ms"]).to_numpy(float)) for v_ in ("B", "C", "D")] + \
        [("対照 (iv-h)", "A", (IVH["t0_ms"] - IVH["anchor_ms"]).to_numpy(float))] + \
        [("対照 (iv-h)", v_, (IVH[f"t0_{v_}"] - IVH["anchor_ms"]).to_numpy(float)) for v_ in ("B", "C", "D")]
    for who, v_, lag in lag_sets:
        lag = lag[np.isfinite(lag) & (lag >= 0)]
        rows.append({"起点を置く側": who, "版": v_, "n": lag.size, "中央値(秒)": np.median(lag) / 1000,
                     "95 分位(秒)": np.percentile(lag, 95) / 1000, "最大(秒)": lag.max() / 1000})
    B("t2v_lag", "起点の時刻(プリント = 清算の時刻 ts、対照 = 格子の時刻 anchor_ms)から、起点の約定までの遅れ(監査 3 回目の直す 4)。"
      "版A = `anchors_prints.csv.gz` の t0_ms・`controls_iv(h).csv.gz` の t0_ms、B・C・D = `prints_versions`・`controls_iv_versions`・`controls_ivh` の t0_*",
      pd.DataFrame(rows))

    rows = []
    for lab, M in VV.items():
        A = pairs[lab]
        cz = (A["cand_a10"] == 0).to_numpy() if "cand_a10" in A else np.zeros(len(A), bool)
        srcc = IV if lab == "(iv)" else IVH
        czM = (M["ref_id"].map(dict(zip(srcc["ref_id"], srcc["cand_a10"]))) == 0).to_numpy()
        rows.append({"対照": lab, "版": "-", "h": "-", "統計": "|m10| = 0 の対照の数 / 全部", "n": f"{int(cz.sum())} / {len(A)}",
                     "対の差": np.nan, "SE": np.nan, "MDE": np.nan, "区分": ""})
        for v_ in ("A", "D"):
            for h in (5, 10, 60, 300, 3600):
                if v_ == "A":
                    m = ~cz
                    xr, yr, dd = A.loc[m, f"react_{h}_p"].to_numpy(float), A.loc[m, f"react_{h}_c"].to_numpy(float), A.loc[m, "day_p"]
                else:
                    m = ~czM
                    xr, yr = M.loc[m, f"reactD_{h}_p"].to_numpy(float), M.loc[m, f"reactD_{h}_c"].to_numpy(float)
                    dd = M.loc[m, "day_p"] if "day_p" in M else M.loc[m, "day"]
                sx, s_ = st(xr, dd), st(xr - yr, dd)
                rows.append({"対照": lab, "版": v_, "h": H_LABEL[h], "統計": "day_eq_mean(|m10| = 0 の対照を除く)", "n": s_["n"],
                             "対の差": s_["day_eq_mean"], "SE": s_["se_day_eq"], "MDE": 2.8 * s_["se_day_eq"],
                             "区分": klass(s_["day_eq_mean"], s_["se_day_eq"], abs(sx["day_eq_mean"])), "実の値動きが SE より小さい": small(s_["se_day_eq"], abs(sx["day_eq_mean"]))})
    B("t2dir0", "対照の向き dir は直前 10 秒の変位の符号で、変位が 0 のときは +1(`liq_cascade_v2.pre_state_arrays` の dir10 の規約)。"
      "|m10| = 0 の対照では向きが規約で決まり、版D の「押した向きの成行」もその規約の向きになる。その対照を除いた対の差(監査 3 回目の直す 5)",
      pd.DataFrame(rows))

    hp = pd.to_datetime(P["ts_ms"], unit="ms", utc=True).dt.hour
    h4 = pd.to_datetime(IV["anchor_ms"], unit="ms", utc=True).dt.hour
    h5 = pd.to_datetime(IVH["anchor_ms"], unit="ms", utc=True).dt.hour
    hp4 = pd.to_datetime(P.loc[P["print_id"].isin(set(IV["ref_id"])), "ts_ms"], unit="ms", utc=True).dt.hour
    rows = [{"UTC の時": hh, "プリント 全部": float((hp == hh).mean()), "プリント (iv) が取れた": float((hp4 == hh).mean()),
             "対照 (iv)": float((h4 == hh).mean()), "対照 (iv-h)": float((h5 == hh).mean())} for hh in range(24)]
    B("t2hour", "時刻(UTC の時)ごとの割合。プリント = `anchors_prints.csv.gz` の ts_ms、対照 = anchor_ms", pd.DataFrame(rows))

    # 大きさのつり合い
    REPm = REP.merge(P[["print_id", "a10", "a60"]], on="print_id")
    got2 = REPm["anchor_new"].notna()
    got4 = P["print_id"].isin(set(IV["ref_id"]))
    rows = [
        {"群": "実 全プリント", "n": len(P), "|m10| 中央値": P["a10"].median(), "|m60| 中央値": P["a60"].median()},
        {"群": "実 (ii) が取れたプリント(流し直しの集合。t2 の 48039 とは違う)", "n": int(got2.sum()), "|m10| 中央値": REPm.loc[got2, "a10"].median(),
         "|m60| 中央値": REPm.loc[got2, "a60"].median()},
        {"群": "対照 (ii)(流し直しで選んだ候補)", "n": int(got2.sum()), "|m10| 中央値": REPm.loc[got2, "cand_a10"].median(),
         "|m60| 中央値": REPm.loc[got2, "cand_a60"].median()},
        {"群": "実 (iv) が取れたプリント", "n": int(got4.sum()), "|m10| 中央値": P.loc[got4, "a10"].median(),
         "|m60| 中央値": P.loc[got4, "a60"].median()},
        {"群": "対照 (iv)(合わせた候補)", "n": len(IV), "|m10| 中央値": IV["cand_a10"].median(),
         "|m60| 中央値": IV["cand_a60"].median()},
        {"群": "実 (iv-h) が取れたプリント", "n": len(IVH), "|m10| 中央値": IVH["print_a10"].median(),
         "|m60| 中央値": IVH["print_a60"].median()},
        {"群": "対照 (iv-h)(合わせた候補)", "n": len(IVH), "|m10| 中央値": IVH["cand_a10"].median(),
         "|m60| 中央値": IVH["cand_a60"].median()},
    ]
    B("t2bal_magnitude", "直前の値動きの大きさ(bp)。実 = `anchors_prints` の |m10_signed|・|m60_signed|、"
      "(ii) の候補 = `control_iv_out/ii_reproduction.csv.gz` の cand_a10・cand_a60(同じ選び方を流し直して記録、t0 で一致を確かめた)、"
      "(iv) = `controls_iv.csv.gz` の cand_a10・cand_a60", pd.DataFrame(rows))
    cut10 = np.array(ivm["帯の境"]["a10"])
    bnd = v2.band_of(IV["print_a10"].to_numpy(float), cut10)
    rows = []
    for b_ in range(10):
        m = bnd == b_
        q = lambda c: IV.loc[m, c].quantile([0.25, 0.5, 0.75]).to_numpy()  # noqa: E731
        pa, ca, p6, c6 = q("print_a10"), q("cand_a10"), q("print_a60"), q("cand_a60")
        rows.append({"|m10| の帯(10 分位)": b_ + 1, "n": int(m.sum()),
                     "プリント |m10| q25/q50/q75": " / ".join(f"{x:.3g}" for x in pa),
                     "候補 |m10| q25/q50/q75": " / ".join(f"{x:.3g}" for x in ca),
                     "プリント |m60| q50": p6[1], "候補 |m60| q50": c6[1],
                     "|m10| の差(プリント − 候補)の中央値": float((IV.loc[m, "print_a10"] - IV.loc[m, "cand_a10"]).median())})
    B("t2res_band", "`controls_iv.csv.gz` の print_a10・cand_a10・print_a60・cand_a60 を、プリントの |m10| の帯(t0 の (iv) の境)ごとに並べた(帯の中の残差)",
      pd.DataFrame(rows))

    # 取れなかった群の偏り(直す 2)
    rows = []
    for lab, got in (("(ii)", P["print_id"].isin(set(c2["ref_id"]))), ("(iv)", got4),
                     ("(iv-h)", P["print_id"].isin(set(IVH["ref_id"])))):
        for gl, m in (("取れた", got), ("取れなかった", ~got)):
            sub = P[m.to_numpy()]
            s36 = st(sub["react_3600"], sub["day"])
            top = sub["day"].value_counts().head(5)
            rows.append({"対照": lab, "群": gl, "プリント": len(sub), "|m10| 中央値": sub["a10"].median(),
                         "|m60| 中央値": sub["a60"].median(), "連鎖の中の割合": float((sub["scene"] == "連鎖の中").mean()),
                         "react 60分 q50": s36["q50"], "react 60分 day_eq_mean": s36["day_eq_mean"],
                         "react 60分 se_day_eq": s36["se_day_eq"],
                         "多い日 上位 5": "; ".join(f"{d}={n}" for d, n in top.items())})
    B("t2u_unmatched", "`anchors_prints.csv.gz` を、対照が取れたか(`controls.csv.gz` / `controls_iv.csv.gz` / `controls_ivh.csv.gz` の ref_id にあるか)で分けた",
      pd.DataFrame(rows))
    # 直す 7: |m10| の 10 分位ごとの取れた割合と、取れない原因
    pb10 = v2.band_of(P["a10"].to_numpy(float), cut10)
    CZm = CZ.set_index("print_id")
    rows = []
    for b_ in range(10):
        m = pb10 == b_
        ids = set(P.loc[m, "print_id"])
        g4 = len(ids & set(IV["ref_id"]))
        g5 = len(ids & set(IVH["ref_id"]))
        cz = CZm.loc[CZm.index.isin(ids)]
        rows.append({"|m10| の帯(10 分位)": b_ + 1, "プリント": int(m.sum()), "(iv) 取れた": g4, "(iv) 取れた割合": g4 / max(int(m.sum()), 1),
                     "(iv-h) 取れた": g5, "(iv-h) 取れた割合": g5 / max(int(m.sum()), 1),
                     "(iv) 取れず: 帯が欠け": int((cz["帯が欠け"] == 1).sum()),
                     "(iv) 取れず: ±3 日の格子に同じ帯の時刻が無い": int(((cz["帯が欠け"] == 0) & (cz["n_all_pm3"] == 0)).sum()),
                     "(iv) 取れず: 前後 15 分に清算無しの条件で消えた": int(((cz["n_all_pm3"] > 0) & (cz["n_noliq_pm3"] == 0)).sum()),
                     "(iv) 取れず: 清算の zip の無い日にだけあった": int(((cz["n_noliq_pm3"] > 0) & (cz["n_cand_pm3"] == 0)).sum()),
                     "(iv) 取れず: 候補はあったが先に使われた": int((cz["n_cand_pm3"] > 0).sum())})
    df = pd.DataFrame(rows)
    tot = {c: (df[c].sum() if df[c].dtype != object else "") for c in df.columns}
    tot["|m10| の帯(10 分位)"] = "合計"
    tot["(iv) 取れた割合"] = df["(iv) 取れた"].sum() / df["プリント"].sum()
    tot["(iv-h) 取れた割合"] = df["(iv-h) 取れた"].sum() / df["プリント"].sum()
    B("t2dec", "プリントの |m10| の帯(t0 の (iv) の境)ごとの取れた割合と、(iv) が取れなかった原因。原因 = `control_ivh_out/iv_unmatched_cause.csv.gz`。"
      "原因は上の列から順に当てる排他の分類。「先に使われた」は、プリントを日の順・日の中の時刻の順に処理して候補を置換なしで取る貪欲法の結果で、処理の順に依る"
      "(±3 日の 10 秒格子で帯 4 つが同じ時刻を、清算の条件なし / 前後 15 分に清算無し / それに zip のある日、で数えた)",
      pd.concat([df, pd.DataFrame([tot])], ignore_index=True))

    # (iv-h) の取れなかった原因(監査 3 回目の直す 9)
    CZ5m = CZ5.set_index("print_id")
    rows = []
    for b_ in range(10):
        ids = set(P.loc[pb10 == b_, "print_id"])
        cz = CZ5m.loc[CZ5m.index.isin(ids)]
        rows.append({"|m10| の帯(10 分位)": b_ + 1, "(iv-h) 取れず": len(cz),
                     "帯が欠け": int((cz["帯が欠け"] == 1).sum()),
                     "±3 日の格子に同じ帯・同じ時の時刻が無い": int(((cz["帯が欠け"] == 0) & (cz["n_all_pm3"] == 0)).sum()),
                     "前後 15 分に清算無しの条件で消えた": int(((cz["n_all_pm3"] > 0) & (cz["n_noliq_pm3"] == 0)).sum()),
                     "清算の zip の無い日にだけあった": int(((cz["n_noliq_pm3"] > 0) & (cz["n_cand_pm3"] == 0)).sum()),
                     "候補はあったが先に使われた": int((cz["n_cand_pm3"] > 0).sum())})
    df = pd.DataFrame(rows)
    tot = {c: df[c].sum() for c in df.columns}
    tot["|m10| の帯(10 分位)"] = "合計"
    B("t2dec_h", "(iv-h) が取れなかったプリントの原因(帯 5 つ = (iv) の 4 つ + UTC の時)。`control_iv_days_out/ivh_unmatched_cause.csv.gz`。"
      "数え方と貪欲法の順序依存は t2dec と同じ", pd.concat([df, pd.DataFrame([tot])], ignore_index=True))

    # 帯ごとの無清算の割合(監査 3 回目の止める 3)
    rows = []
    for b_ in range(10):
        ids = set(P.loc[pb10 == b_, "print_id"])
        cz = CZm.loc[CZm.index.isin(ids)]
        g = GBN[GBN["a10_band"] == b_ + 1].iloc[0]
        rows.append({"|m10| の帯(10 分位)": b_ + 1, "格子の時刻(全日、材料が有限)": int(g["格子の時刻(材料が有限)"]),
                     "うち前後 15 分に清算無し": int(g["うち前後15分に清算無し"]), "格子の無清算の割合": float(g["無清算の割合"]),
                     "(iv) が取れなかったプリントの ±3 日の同帯の格子(の和)": int(cz["n_all_pm3"].sum()),
                     "うち清算無し(の和)": int(cz["n_noliq_pm3"].sum()),
                     "その割合": float(cz["n_noliq_pm3"].sum() / max(cz["n_all_pm3"].sum(), 1))})
    B("t2noliq", "左 3 列 = 走らせの全日の 10 秒格子(材料が有限)を |m10| の帯で数えた(`control_iv_days_out/grid_band_noliq.csv`)。"
      "右 3 列 = (iv) が取れなかったプリントごとの ±3 日の同じ帯 4 つの格子の数の和(`iv_unmatched_cause.csv.gz` の n_all・n_noliq)",
      pd.DataFrame(rows))

    # 日の幅を変えた (iv)(監査 3 回目の止める 3・直す 14)
    VAR = {"(iv) ±3 日(第 2 稿)": IV, "(iv) 同じ日だけ": IVD0, "(iv) ±7 日": IVD7}
    rows = []
    for b_ in range(10):
        m = pb10 == b_
        ids = set(P.loc[m, "print_id"])
        r = {"|m10| の帯(10 分位)": b_ + 1, "プリント": int(m.sum())}
        for vl, df_ in VAR.items():
            n_ = len(ids & set(df_["ref_id"]))
            r[f"{vl} 取れた"] = n_
            r[f"{vl} 割合"] = n_ / max(int(m.sum()), 1)
        rows.append(r)
    df = pd.DataFrame(rows)
    tot = {"|m10| の帯(10 分位)": "合計", "プリント": int(df["プリント"].sum())}
    for vl in VAR:
        tot[f"{vl} 取れた"] = int(df[f"{vl} 取れた"].sum())
        tot[f"{vl} 割合"] = tot[f"{vl} 取れた"] / tot["プリント"]
    B("t2days_n", "日の幅を変えた (iv) の取れた数(帯は t0 の (iv) の境)。同じ日だけ・±7 日 = `control_iv_days_out/controls_iv_d0.csv.gz`・`controls_iv_d7.csv.gz`",
      pd.concat([df, pd.DataFrame([tot])], ignore_index=True))
    rows = []
    common = set(IV["ref_id"]) & set(IVD0["ref_id"]) & set(IVD7["ref_id"])
    for vl, df_ in VAR.items():
        df_ = df_[df_["ref_id"].isin(common)]
        M = df_.merge(P[["print_id", "day"] + xk], left_on="ref_id", right_on="print_id", suffixes=("_c", "_p"))
        if "day_offset" in M:
            rows.append({"版": vl, "h": "-", "統計": "日のずれ 0 の割合", "n": len(M), "実の react": np.nan,
                         "対の差": float((M["day_offset"] == 0).mean()), "SE": np.nan, "MDE": np.nan, "区分": ""})
        for h in (5, 60, 300, 3600, 14400):
            x, y = M[f"react_{h}_p"].to_numpy(float), M[f"react_{h}_c"].to_numpy(float)
            sx, s_ = st(x, M["day_p"]), st(x - y, M["day_p"])
            for stat, se_key in (("pooled_mean", "se_pooled_cluster"), ("day_eq_mean", "se_day_eq")):
                rows.append({"版": vl, "h": H_LABEL[h], "統計": stat, "n": s_["n"], "実の react": sx[stat], "対の差": s_[stat],
                             "SE": s_[se_key], "MDE": 2.8 * s_[se_key], "区分": klass(s_[stat], s_[se_key], abs(sx[stat])), "実の値動きが SE より小さい": small(s_[se_key], abs(sx[stat]))})
    B("t2days_diff", f"日の幅を変えた (iv) の対の差を、**3 つの版のすべてで対照が取れた共通のプリント {len(common)} 件だけ**で出した(監査 4 回目の止める 2)。"
      "値 = react_h(プリント)− react_h(対照)、日 = プリントの日。「実の react」= 共通のプリントの react(3 つの版で同じ)。区分は t2stat と同じ規則",
      pd.DataFrame(rows))

    # (ii) の候補が清算の zip の無い日から来た数(直す 10)
    noz = set(ivm["清算のzipが無く候補から外した日"])
    cd2 = pd.to_datetime(c2["anchor_ms"], unit="ms", utc=True).dt.strftime("%Y-%m-%d")
    cd4 = pd.to_datetime(IV["anchor_ms"], unit="ms", utc=True).dt.strftime("%Y-%m-%d")
    vc = cd2[cd2.isin(noz)].value_counts().sort_index()
    rows = [{"対照": "(ii)", "候補の日": d, "行": int(n)} for d, n in vc.items()]
    rows.append({"対照": "(ii)", "候補の日": "合計", "行": int(vc.sum())})
    rows.append({"対照": "(iv)", "候補の日": "合計", "行": int(cd4.isin(noz).sum())})
    cd5 = pd.to_datetime(IVH["anchor_ms"], unit="ms", utc=True).dt.strftime("%Y-%m-%d")
    rows.append({"対照": "(iv-h)", "候補の日": "合計", "行": int(cd5.isin(noz).sum())})
    B("t2z_nozip", "対照の時刻(anchor_ms)の UTC の日が、清算の zip が無い日(t0)に入る行の数", pd.DataFrame(rows))

    # ---- t3 プラセボ ----
    rows = []
    for g in (30, 60, 180):
        m = P[f"g{g}_pos_post"].isin(["最後", "単発"]).to_numpy()
        cg = C[C["kind"] == f"(iii)プラセボ_g{g}"]
        for h in (10, 60, 300, 3600, 86400):
            rows.append({"g": g, "h": H_LABEL[h], "群": "実_束の最後(最後+単発、事後)"} | st(P.loc[m, f"react_{h}"], P.loc[m, "day"]))
            rows.append({"g": g, "h": H_LABEL[h], "群": f"対照(iii)プラセボ_g{g}"} | st(cg[f"react_{h}"], cg["day"]))
    B("t3_placebo", "実 = `anchors_prints.csv.gz` の g{g}_pos_post が 最後・単発、対照 = `controls.csv.gz` の (iii)", pd.DataFrame(rows))

    # ---- t4 側・位置 ----
    rows = []
    for h in (10, 60, 300, 3600):
        for lab, m in (("SELL", P["side"] == "SELL"), ("BUY", P["side"] == "BUY")) + tuple(
                (f"g60 位置 {p}(事後)", P["g60_pos_post"] == p) for p in ("単発", "最初", "途中", "最後")):
            rows.append({"h": H_LABEL[h], "群": lab} | st(P.loc[m, f"react_{h}"], P.loc[m, "day"]))
    B("t4_side_pos", "`anchors_prints.csv.gz` の side・g60_pos_post で分けた react_h", pd.DataFrame(rows))

    # ---- t4m 上がりすぎ下がりすぎの量の 3 分位(直す 13) ----
    rows = []
    for col, lab in (("m10_signed", "m10(直前 10 秒、清算の向き)"), ("m60_signed", "m60(直前 60 秒、清算の向き)"),
                     (M4, "材料 4 連鎖の最初からの値動き"), ("mat4_bounce_bp", "材料 4 直前の同じ側のプリントからの値動き")):
        x = P[col].to_numpy(float)
        cuts = v2.tertile_cuts(x)
        b = np.where(np.isfinite(x), np.searchsorted(cuts, x, side="right"), -1)
        for t_ in range(3):
            m = b == t_
            for h in (60, 3600):
                s = st(P.loc[m, f"react_{h}"], P.loc[m, "day"])
                rows.append({"分け": lab, "3分位": t_ + 1, "境": " / ".join(f"{c:.4g}" for c in cuts), "h": H_LABEL[h]} |
                            {k: s[k] for k in ST_SHORT})
        rows.append({"分け": lab, "3分位": "欠け", "境": "", "h": "-", "n": int((b < 0).sum())})
    B("t4m_overshoot", "`anchors_prints.csv.gz` の m10_signed・m60_signed・材料 4 の 2 列。3 分位の境は全期間のプリントから(`tertile_cuts`)",
      pd.DataFrame(rows))

    # ---- t5 ラベル ----
    B("t5_label", "`label_counts.csv`(そのまま)", L)
    rows = []
    for s_ in ("1件目", "連鎖の中"):
        for per in ("作る", "測る"):
            m = (P["scene"] == s_) & (P["period"] == per)
            rows.append({"場面": s_, "期間": PER[per], "プリント": int(m.sum()), "続く(cont_60)の割合": float(P.loc[m, "cont_60"].mean())})
    B("t5b_scene", "`anchors_prints.csv.gz` の mat1(≥ 1 = 連鎖の中)・period・cont_60", pd.DataFrame(rows))

    # ---- t6 方策 ----
    CA3["incl"] = np.where(CA3["entered"] == 1, CA3["pnl_pct"], np.where(CA3["missing"] == 1, np.nan, 0.0))
    CA3["per"] = CA3["period"].map(PER)
    CA = pd.concat([CA, CA3], ignore_index=True)
    order = {"全部順張り": 0, "全部逆張り": 1, "規則_材料1": 2, "規則_3択": 3, "規則_3択_新15本": 3.5, "完全な判断": 4}

    def pol_rows(sub, extra=None):
        rows = []
        for (pol, typ), g in sorted(sub.groupby(["policy", "type"]), key=lambda kv: (order[kv[0][0]], kv[0][1])):
            s = st(g["incl"], g["day"])
            dsum = g.groupby("day")["incl"].sum()
            rows.append((extra or {}) | {"policy": pol, "type": typ, "連鎖の数": len(g), "入った連鎖": int(g["entered"].sum())} |
                        s | {"総和": float(g["incl"].sum()), "正の日の割合": float((dsum > 0).mean())})
        return rows

    s60 = CA[(CA["gap_s"] == 60) & (CA["delay_s"] == 1) & (CA["period"] == "測る")]
    B("t6_policy_g60d1", "`policy_cascades.csv.gz`(後半、g = 60、遅れ 1 秒、連鎖 1 本、入らない = 0、値の欠け = NaN)。pnl は建玉の向きに正",
      pd.DataFrame(pol_rows(s60)))
    rows = []
    for (pol, typ), g in sorted(s60[s60["entered"] == 1].groupby(["policy", "type"]), key=lambda kv: (order[kv[0][0]], kv[0][1])):
        rows.append({"単位": "連鎖 1 本(入った連鎖だけ)", "policy": pol, "type": typ} | {k: v for k, v in st(g["pnl_pct"], g["day"]).items() if k in ST_SHORT})
    l60 = LG[(LG["gap_s"] == 60) & (LG["delay_s"] == 1) & (LG["period"] == "測る")]
    for (pol, typ), g in sorted(l60.groupby(["policy", "type"]), key=lambda kv: (order[kv[0][0]], kv[0][1])):
        rows.append({"単位": "1 レグ", "policy": pol, "type": typ} | {k: v for k, v in st(g["pnl_bp"] / 100, g["day"]).items() if k in ST_SHORT})   # 1 レグ bp → % で表の単位をそろえる(L-920)
    LG3 = pd.read_csv(twdir / "policy_legs_3m.csv.gz", dtype={"day": str})
    l3 = LG3[(LG3["gap_s"] == 60) & (LG3["delay_s"] == 1)]
    for (pol, typ), g in l3.groupby(["policy", "type"]):
        rows.append({"単位": "1 レグ", "policy": pol, "type": typ} | {k: v for k, v in st(g["pnl_bp"] / 100, g["day"]).items() if k in ST_SHORT})   # 1 レグ bp → % で表の単位をそろえる(L-920)
    B("t6a_units", "同じ条件の、入った連鎖だけ(`policy_cascades`)と 1 レグ(`policy_legs.csv.gz`、新の 3 択は `three_way_m_out/policy_legs_3m.csv.gz`)", pd.DataFrame(rows))
    rows = []
    for (g_, d_), sub in CA[CA["period"] == "測る"].groupby(["gap_s", "delay_s"]):
        for r in pol_rows(sub, {"g": g_, "d": d_}):
            rows.append({k: r[k] for k in ("g", "d", "policy", "type", "連鎖の数", "q50", "pooled_mean", "se_pooled_cluster",
                                           "day_eq_mean", "se_day_eq", "総和", "正の日の割合")})
    B("t6b_policy_all", "`policy_cascades.csv.gz`(後半、g × 遅れ の全部、入らない = 0)", pd.DataFrame(rows))
    rows = []
    for per in ("作る", "測る"):
        sub = CA[(CA["gap_s"] == 60) & (CA["delay_s"] == 1) & (CA["period"] == per) & (CA["policy"] != "規則_3択")]
        for r in pol_rows(sub, {"期間": PER[per]}):
            rows.append({k: r[k] for k in ("期間", "policy", "type", "連鎖の数", "q50", "pooled_mean", "se_pooled_cluster",
                                           "day_eq_mean", "se_day_eq", "総和", "正の日の割合")})
    B("t6c_policy_period", "`policy_cascades.csv.gz`(g = 60、遅れ 1 秒、前半と後半。規則_3択 は後半にしか無い)", pd.DataFrame(rows))
    rows = []
    one = s60[s60["policy"] == "全部逆張り"]               # 束 1 本 = 1 行(方策ごとに同じ束が並ぶので 1 つで境を作る)
    cuts = v2.tertile_cuts(one["qty_total"].to_numpy(float))
    bq = np.searchsorted(cuts, s60["qty_total"].to_numpy(float), side="right")
    for t_ in range(3):
        for r in pol_rows(s60[bq == t_], {"束の総量 3分位(事後)": t_ + 1}):
            rows.append({k: r[k] for k in ("束の総量 3分位(事後)", "policy", "type", "連鎖の数", "q50", "pooled_mean",
                                           "day_eq_mean", "se_day_eq", "総和")})
    B("t6d_policy_qty", "`policy_cascades.csv.gz`(後半、g = 60、遅れ 1 秒)を束の総量 qty_total の 3 分位(後半の g = 60 の束から。走らせの dist_policy と同じ境)で分けた", pd.DataFrame(rows))

    # ---- t6e 全部逆張り の偏り(直す 4) ----
    rows = []
    for (per, g_, d_), sub in CA[CA["policy"] == "全部逆張り"].groupby(["period", "gap_s", "delay_s"]):
        ds = sub.groupby("day")["incl"].sum()
        s = st(sub["incl"], sub["day"])
        top_pos = ds.sort_values(ascending=False).head(10).index
        top_neg = ds.sort_values().head(10).index
        top_abs = ds.abs().sort_values(ascending=False).head(10).index

        def ex(idx):
            x = sub[~sub["day"].isin(idx)]
            return float(x["incl"].sum()), float(x["incl"].mean())
        rows.append({"期間": PER[per], "g": g_, "d": d_, "連鎖": len(sub), "総和": float(sub["incl"].sum()),
                     "pooled_mean": s["pooled_mean"], "day_eq_mean": s["day_eq_mean"], "se_day_eq": s["se_day_eq"],
                     "正の日の割合": float((ds > 0).mean()),
                     "正の上位10日を除いた総和": ex(top_pos)[0], "負の上位10日を除いた総和": ex(top_neg)[0],
                     "絶対値の上位10日を除いた総和": ex(top_abs)[0],
                     "正の上位10日を除いた pooled_mean": ex(top_pos)[1], "負の上位10日を除いた pooled_mean": ex(top_neg)[1]})
    B("t6e_fade_conc", "`policy_cascades.csv.gz`(policy = 全部逆張り、入らない = 0)。上位 10 日 = 日の合計の大きい順(正・負・絶対値の 3 通り)",
      pd.DataFrame(rows))

    # ---- t6f 規則_3択 − 全部逆張り の対の差と MDE(直す 19) ----
    rows = []
    base = CA[(CA["policy"] == "全部逆張り") & (CA["period"] == "測る")][["bundle_id", "gap_s", "delay_s", "day", "incl"]]
    for pol3, typ in (("規則_3択", "A"), ("規則_3択", "B"), ("規則_3択_新15本", "A"), ("規則_3択_新15本", "B")):
        tw = CA[(CA["policy"] == pol3) & (CA["type"] == typ)][["bundle_id", "gap_s", "delay_s", "incl"]]
        M = tw.merge(base, on=["bundle_id", "gap_s", "delay_s"], suffixes=("_3", "_f"))
        for (g_, d_), sub in M.groupby(["gap_s", "delay_s"]):
            d = sub["incl_3"].to_numpy(float) - sub["incl_f"].to_numpy(float)
            s = st(d, sub["day"])
            rows.append({"3 択": "旧(13 本)" if pol3 == "規則_3択" else "新(15 本)", "type": typ, "g": g_, "d": d_, "対": len(sub), "差の総和": float(np.nansum(d)),
                         "pooled_mean": s["pooled_mean"], "se_pooled_cluster": s["se_pooled_cluster"],
                         "day_eq_mean": s["day_eq_mean"], "se_day_eq": s["se_day_eq"],
                         "day_eq_mean ÷ se_day_eq": s["day_eq_mean"] / s["se_day_eq"],
                         "MDE(day_eq)= 2.8×se_day_eq": 2.8 * s["se_day_eq"],
                         "MDE(pooled)= 2.8×se_pooled_cluster": 2.8 * s["se_pooled_cluster"]})
    B("t6f_3way_vs_fade", "`policy_cascades.csv.gz` の同じ bundle_id・g・遅れ で、規則_3択(旧 13 本・新 15 本、型 A・B)− 全部逆張り(後半、入らない = 0)。新 = `three_way_m_out/policy_cascades_3m.csv.gz`。"
      "MDE の 2.8 = 1.96 + 0.84(両側 5%・検出力 80% の慣用の値。仮定、作業者が置き、リードが追認)", pd.DataFrame(rows))

    # ---- t7 行動・判断 ----
    a = AC[(AC["policy"] == "規則_3択") & (AC["gap_s"] == 60) & (AC["delay_s"] == 1)].sort_values(["type", "行動"])
    a = a.assign(**{"3 択": "旧(13 本)"})
    an = pd.DataFrame([{"gap_s": k.split("|")[0], "delay_s": k.split("|")[1], "policy": k.split("|")[2], "type": k.split("|")[3],
                        "行動": k.split("|")[4], "件数": v, "3 択": "新(15 本)"} for k, v in p3m["行動の数"].items()
                       if k.startswith("60|1|")]).sort_values(["type", "行動"])
    B("t7_actions", "旧 = `policy_action_counts.csv`、新 = `three_way_m_out/policy_3m_meta.json` の行動の数(規則_3択、g = 60、遅れ 1 秒)",
      pd.concat([a, an], ignore_index=True)[["3 択", "type", "行動", "件数"]])
    rows = []
    jm = model["判断の件数(プリント)"]
    for g in (30, 60, 180):
        for typ in ("A", "B"):
            j = JC[(JC["policy"] == "規則_3択") & (JC["gap_s"] == g) & (JC["delay_s"] == 1) & (JC["type"] == typ)]
            d = dict(zip(j["判断"], j["件数"]))
            rows.append({"出所": f"policy_judge_counts g={g} 遅れ1 型{typ}", "止まる": d.get("止まる", 0),
                         "わからない": d.get("わからない", 0), "続く": d.get("続く", 0)})
    rows.append({"出所": "three_way_model.json 判断の件数(後半)", "止まる": jm["測る_止まる"], "わからない": jm["測る_わからない"],
                 "続く": jm["測る_続く"]})
    B("t7b_judge_check", "`policy_judge_counts.csv`(2 回目の起動の段 3)と `three_way_model.json`(3 回目の起動の作り直し)", pd.DataFrame(rows))

    # ---- t8 s 秒の曲線(chunks/scurve の npz から。直す 8・9) ----
    sc_cols = [(d, h) for d in v2.DELAYS_S for h in v2.HORIZONS_S]
    files = sorted((src / "chunks" / "scurve").glob("*.npz"))
    s_all = np.concatenate([np.load(p)["s"].astype(np.int64) for p in files])
    d_all = np.concatenate([np.full(np.load(p)["s"].size, p.stem, dtype=object) for p in files])
    rows = []
    for h in (10, 60, 300, 3600):
        c = sc_cols.index((1, h))
        v_all = np.concatenate([np.load(p)["v"][:, c] for p in files]).astype(float)
        for s in (1, 5, 10, 30, 60, 120, 180):
            m = s_all == s
            rows.append({"h": H_LABEL[h], "s": s} | st(v_all[m], d_all[m]))
    B("t8_scurve", "`chunks/scurve/<日>.npz`(走らせが書いた s 秒の曲線の点。`dist_s_curve.csv` の元)。遅れ 1 秒。fade の建玉の向きに正。"
      "s ごとに母集団が違う", pd.DataFrame(rows))
    rows = []
    for h in (10, 60, 300, 3600):
        for gname in ("対照(i)", "対照(ii)", "対照(iv)"):
            df = G[gname]
            s = st(-df[f"react_{h}"], df["day"])
            rows.append({"h": H_LABEL[h], "群": gname + " の −react(起点で直前の向きの逆に入った形)"} | {k: s[k] for k in ST_SHORT})
    B("t8c_ref", "同じ入りの時刻の対照は無い。参考に、対照の時刻で直前 10 秒の向きの逆に入った値動き(= −react_h)を並べた。"
      "入りの時刻(清算から s + 1 秒後)はそろっていない", pd.DataFrame(rows))

    # ---- t9 量の 3 分位 ----
    rows = []
    for col, name in [("qty", "1件の数量(枚)"), (v2.MAT_COL[12], "材料12 直前60秒の最大との比")] + \
            [(f"g{g}_qty_so_far", f"g{g}_連鎖のここまでの数量(枚)") for g in (30, 60, 180)]:
        x = P[col].to_numpy(float)
        cuts = v2.tertile_cuts(x)
        b = np.where(np.isfinite(x), np.searchsorted(cuts, x, side="right"), -1)
        for t_ in range(3):
            m = b == t_
            for h in (60, 3600):
                s = st(P.loc[m, f"react_{h}"], P.loc[m, "day"])
                rows.append({"分け": name, "3分位": t_ + 1, "境": " / ".join(f"{c:.6g}" for c in cuts), "h": H_LABEL[h]} |
                            {k: s[k] for k in ST_SHORT})
    B("t9_size", "`anchors_prints.csv.gz`(3 分位の境は `tertile_cuts`。`dist_size_split.csv` と同じ作り)", pd.DataFrame(rows))

    # ---- t10 3 択(旧 = 走らせの材料 13 本 / 新 = |m10|・|m60| を足した 15 本。止める 3) ----
    VERS = (("旧(13 本)", model, TP, CAL), ("新(15 本、|m10|・|m60| を足した)", MM, TPM, CALM))
    rows = []
    for vl, mdl, _tp, _cal in VERS:
        for s_, v in mdl["場面"].items():
            rows.append({"版": vl, "場面": s_, "件数(前半)": v["件数(作る)"], "基準率(前半)": v["基準率(作る)"], "分割数": v["分割数"],
                         "わからないの帯": str(v["わからないの帯"]), "基準率を跨ぐ帯(区別できない帯が無いときだけ使う境)": str(v["基準率を跨ぐ帯"])})
    B("t10b_band", "旧 = `three_way_model.json`、新 = `run_a/three_way_m_out/three_way_m_model.json` の 場面", pd.DataFrame(rows))
    B("t10_calib", "旧: `three_way_calibration.csv`(前半の out-of-fold 確率。列「区分」は対の差の区分と紛れるので「帯の判断」と名前だけ替えた)", CAL.rename(columns={"区分": "帯の判断"}))
    B("t10_calib_m", "新: `three_way_m_out/three_way_m_calibration.csv`(同じく列の名前だけ替えた)", CALM.rename(columns={"区分": "帯の判断"}))
    rows = []
    for vl, _m, tp, _c in VERS:
        for (per, s_, j), g in tp.groupby(["期間", "場面", "判断"]):
            rows.append({"版": vl, "期間": PER[per], "場面": s_, "判断": j, "プリント": len(g), "続く(cont_60)の割合": float(g["cont_60"].mean())})
    B("t10d_judge_hit", "旧 = `three_way_probs.csv.gz`、新 = `three_way_m_probs.csv.gz`(期間・場面・判断ごとの事後のラベル cont_60 の割合。前半は模型を作った行そのもの)",
      pd.DataFrame(rows))
    rows = []
    for vl, mdl, tp, _c in VERS:
        for (per, s_), g in tp.groupby(["期間", "場面"]):
            base = mdl["場面"][s_]["基準率(作る)"]
            maj = 1 if base >= 0.5 else 0
            y = g["cont_60"].to_numpy(float)
            dec = g["判断"].isin(["止まる", "続く"]).to_numpy()
            pred = (g["判断"] == "続く").to_numpy().astype(float)
            rows.append({"版": vl, "期間": PER[per], "場面": s_, "プリント": len(g),
                         "3択が止まる/続くと言った行": int(dec.sum()),
                         "その行での 3択の当たり": float((pred[dec] == y[dec]).mean()),
                         "その行での 基準率の分類の当たり": float((maj == y[dec]).mean()),
                         "基準率の分類(前半の基準率で多い側)": "続く" if maj else "止まる",
                         "全行での 基準率の分類の当たり": float((maj == y).mean()),
                         "AUC(続くの確率 対 cont_60)": auc(g["続くの確率"], y)})
    B("t10e_vs_base", "旧・新の判断を、基準率の分類(場面ごとに前半の基準率で多い側をいつも言う)と同じ行で比べた。AUC は順位(Mann–Whitney)",
      pd.DataFrame(rows))
    rows = []
    for vl, mdl, _t, _c in VERS:
        for s_, v in mdl["場面"].items():
            for k, b_ in v["係数"].items():
                rows.append({"版": vl, "場面": s_, "材料": k, "係数": b_})
    B("t10c_coef", "旧・新の 場面.係数(入力は中央順位 0〜1、L2 1e-3 のニュートン法。係数 = 順位が 0 から 1 に動いたときの対数オッズの変化)",
      pd.DataFrame(rows))

    # ---- t11 月 ----
    P["month"] = P["day"].str[:7]
    rows = []
    for mth, g in P.groupby("month"):
        s = st(g["react_3600"], g["day"])
        r = {"月": mth, "プリント": len(g), "日": g["day"].nunique(), "react 60分 q50": s["q50"],
             "pooled_mean": s["pooled_mean"], "se_pooled_cluster": s["se_pooled_cluster"],
             "day_eq_mean": s["day_eq_mean"], "se_day_eq": s["se_day_eq"]}
        for lab, M in pairs.items():
            mm = M[M["day_p"].str[:7] == mth]
            d = mm["react_3600_p"].to_numpy(float) - mm["react_3600_c"].to_numpy(float)
            sd = st(d, mm["day_p"])
            r[f"対{lab}の差 n"] = sd["n"]
            r[f"対{lab}の差 day_eq_mean"] = sd["day_eq_mean"]
            r[f"対{lab}の差 se_day_eq"] = sd["se_day_eq"]
        rows.append(r)
    B("t11_month", "`anchors_prints.csv.gz` の react_3600(60 分)を年月で分けた。対の差は t2 と同じ組(この表は (ii)・(iv)・(iv-h))", pd.DataFrame(rows))
    rows = []
    for mth, g in P.groupby("month"):
        s = st(g["react_60"], g["day"])
        r = {"月": mth, "プリント": len(g), "react 60秒 q50": s["q50"], "pooled_mean": s["pooled_mean"],
             "se_pooled_cluster": s["se_pooled_cluster"], "day_eq_mean": s["day_eq_mean"], "se_day_eq": s["se_day_eq"]}
        for lab in ("(ii)", "(iv)"):
            M = pairs[lab]
            mm = M[M["day_p"].str[:7] == mth]
            sd = st(mm["react_60_p"].to_numpy(float) - mm["react_60_c"].to_numpy(float), mm["day_p"])
            r[f"対{lab}の差 day_eq_mean"] = sd["day_eq_mean"]
            r[f"対{lab}の差 se_day_eq"] = sd["se_day_eq"]
        rows.append(r)
    B("t11s_month_60s", "`anchors_prints.csv.gz` の react_60(60 秒)を年月で分けた(第 1 稿にあった 60 秒の月の表を戻した)", pd.DataFrame(rows))
    CA["month"] = CA["day"].str[:7]
    sub = CA[(CA["gap_s"] == 60) & (CA["delay_s"] == 1)]
    rows = []
    for mth, g in sub.groupby("month"):
        r = {"月": mth}
        for pol, typ in (("全部逆張り", "-"), ("規則_材料1", "A"), ("規則_3択", "A")):
            gg = g[(g["policy"] == pol) & (g["type"] == typ)]
            if len(gg):
                s = st(gg["incl"], gg["day"])
                r[f"{pol} pooled_mean"] = s["pooled_mean"]
                r[f"{pol} day_eq_mean"] = s["day_eq_mean"]
                r[f"{pol} 総和"] = float(gg["incl"].sum())
        rows.append(r)
    B("t11b_month_policy", "`policy_cascades.csv.gz`(g = 60、遅れ 1 秒、入らない = 0)を年月で分けた", pd.DataFrame(rows))

    # ---- t12 封印の境・開いた日 ----
    rows = []
    for col in ("before_seal", "opened_before"):
        for v in (1, 0):
            m = P[col] == v
            for h in (60, 3600):
                rows.append({"列": col, "値": v, "h": H_LABEL[h], "値の種類": "実の react"} |
                            {k: x for k, x in st(P.loc[m, f"react_{h}"], P.loc[m, "day"]).items() if k in ST_SHORT})
                for lab, M in pairs.items():
                    mm = M[M["print_id"].isin(set(P.loc[m, "print_id"]))]
                    d = mm[f"react_{h}_p"].to_numpy(float) - mm[f"react_{h}_c"].to_numpy(float)
                    rows.append({"列": col, "値": v, "h": H_LABEL[h], "値の種類": f"対{lab}の差"} |
                                {k: x for k, x in st(d, mm["day_p"]).items() if k in ST_SHORT})
    B("t12_seal", "`anchors_prints.csv.gz` の before_seal(2023-12-18 より前)・opened_before(9 月に開いた 16 日)", pd.DataFrame(rows))

    # ---- t13 日の集中 ----
    cnt = P.groupby("day").size().sort_values(ascending=False)
    top = cnt.head(10)
    rows = [{"日": d, "プリント": int(n), "全体に占める割合": n / len(P)} for d, n in top.items()]
    rows.append({"日": "上位 10 日の合計", "プリント": int(top.sum()), "全体に占める割合": top.sum() / len(P)})
    rows.append({"日": "1 日あたりの中央値", "プリント": float(cnt.median()), "全体に占める割合": np.nan})
    B("t13_topdays", "`anchors_prints.csv.gz` の day ごとの行数", pd.DataFrame(rows))

    # ---- t14 --resume ----
    dup = c2[c2["anchor_ms"].duplicated(keep=False)]
    gd = dup.groupby("anchor_ms")["day"].agg(["min", "max", "count"])
    rows = [{"項目": "対照 (ii) の行", "値": len(c2)}, {"項目": "時刻の種類", "値": int(c2["anchor_ms"].nunique())},
            {"項目": "2 回以上使われた時刻", "値": int(len(gd))}, {"項目": "その時刻を使った行", "値": int(len(dup))},
            {"項目": "使われた回数が 2 でない時刻", "値": int((gd["count"] != 2).sum())},
            {"項目": f"再開前(< {RESUME_FIRST_DAY})と再開後に跨る時刻", "値": int(((gd["min"] < RESUME_FIRST_DAY) & (gd["max"] >= RESUME_FIRST_DAY)).sum())},
            {"項目": "重なった行の日の範囲", "値": f'{dup["day"].min()} 〜 {dup["day"].max()}'},
            {"項目": "対照 (i) / (iii) g30 / g60 / g180 の時刻の重なり(行)", "値": " / ".join(
                str(int(C[C["kind"] == k]["anchor_ms"].duplicated().sum())) for k in
                ("(i)無作為", "(iii)プラセボ_g30", "(iii)プラセボ_g60", "(iii)プラセボ_g180"))},
            {"項目": "対照 (iv) の時刻の重なり(行。1 回の起動で作った)", "値": int(IV["anchor_ms"].duplicated().sum())}]
    B("t14_resume", "`controls.csv.gz`・`controls_iv.csv.gz`", pd.DataFrame(rows))
    dif = REP[(REP["anchor_new"] != REP["anchor_run"]) & ~(REP["anchor_new"].isna() & REP["anchor_run"].isna())]
    rows = [{"項目": "走らせの (ii) と、1 回の起動で流し直した (ii) で時刻が違う(片方だけを含む)プリント", "値": len(dif)},
            {"項目": f"そのうち再開より前の日(< {RESUME_FIRST_DAY})", "値": int((dif["day"] < RESUME_FIRST_DAY).sum())},
            {"項目": "違う日の範囲", "値": f'{dif["day"].min()} 〜 {dif["day"].max()}'},
            {"項目": "違うプリントの多い日 上位 5", "値": "; ".join(f"{d}={n}" for d, n in dif["day"].value_counts().head(5).items())}]
    B("t14r_rerun_diff", "`control_iv_out/ii_reproduction.csv.gz`(anchor_run = 走らせ、anchor_new = control_iv.py が同じ規則で 1 回の起動で選んだ時刻)",
      pd.DataFrame(rows))
    second = dup[dup["day"] >= RESUME_FIRST_DAY].index
    rows = []
    M = pairs["(ii)"]
    M2 = M[~M["ref_id"].isin(c2.loc[second, "ref_id"])]
    for lab, mm in (("全部", M), ("再開後の重なった行を除く", M2)):
        for h in (10, 60, 300, 3600):
            d = mm[f"react_{h}_p"].to_numpy(float) - mm[f"react_{h}_c"].to_numpy(float)
            rows.append({"対の差 (ii)": lab, "h": H_LABEL[h]} | {k: x for k, x in st(d, mm["day_p"]).items() if k in ST_SHORT})
    B("t14c_resume_effect", f"t2 の (ii) の組。「除く」= 重なった時刻のうち day ≥ {RESUME_FIRST_DAY} の行を落とした", pd.DataFrame(rows))

    # ---- t15 2023-07-15 ----
    heads = {}
    for p in sorted((src / "chunks" / "controls").glob("*.csv.gz")):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            heads[p.name[:10]] = f.readline().rstrip("\r\n").split(",")
    rows = [{"項目": "見出しに day_offset が無い日", "値": ", ".join(sorted(d for d, h in heads.items() if "day_offset" not in h))},
            {"項目": "2023-07-15 のプリント", "値": int((P["day"] == "2023-07-15").sum())},
            {"項目": "(ii) を 1 件も取れなかった日", "値": ", ".join(sorted(set(C["day"]) - set(c2["day"])))},
            {"項目": "最終の (ii) の行で day_offset が空", "値": int(c2["day_offset"].isna().sum())},
            {"項目": "最終の (ii) 以外の行で day_offset が空でない", "値": int(C[C["kind"] != "(ii)合わせた時刻"]["day_offset"].notna().sum())}]
    B("t15_0715", "`chunks/controls/<日>.csv.gz` の見出しと `controls.csv.gz`", pd.DataFrame(rows))

    # ---- t16 限界の数 ----
    rows = [{"項目": "m10_signed > 0 / < 0 / = 0 の割合",
             "値": " / ".join(f"{x:.4g}" for x in ((P["m10_signed"] > 0).mean(), (P["m10_signed"] < 0).mean(), (P["m10_signed"] == 0).mean()))},
            {"項目": "mat8_covered = 1 の割合", "値": float((P["mat8_covered"] == 1).mean())},
            {"項目": "react 1 日 / 1 週 が NaN のプリント", "値": f'{int(P["react_86400"].isna().sum())} / {int(P["react_604800"].isna().sum())}'},
            {"項目": "起点の時刻 = ts の割合(版A)", "値": float((P["t0_ms"] == P["ts_ms"]).mean())},
            {"項目": "起点の価格 = average_price の割合(版A)", "値": float((np.abs(P["p0"] - P["avg_price"]) / P["avg_price"] < 1e-9).mean())}]
    B("t16_limits", "`anchors_prints.csv.gz`", pd.DataFrame(rows))

    # ---- tchk 走らせの dist_* との一致(この台本の集計が走らせと同じか) ----
    rows = []
    for h in H_ALL:
        r = R[(R["群"] == "実_全プリント") & (R["量"] == "react") & (R["h_s"] == h)].iloc[0]
        s = st(P[f"react_{h}"], P["day"])
        rows.append({"表": "dist_reaction 実_全プリント react", "h": H_LABEL[h],
                     "|Δq50|": abs(s["q50"] - r["q50"]), "|Δday_eq_mean|": abs(s["day_eq_mean"] - r["day_eq_mean"]),
                     "|Δse(pooled)|": abs(s["se_pooled_cluster"] - r["se_day_cluster"])})
    for _, r in Pd[(Pd["期間"] == "測る") & (Pd["gap_s"] == 60) & (Pd["delay_s"] == 1) &
                   (Pd["単位"] == "連鎖1本(入らないを0で含める)")].iterrows():
        g = s60[(s60["policy"] == r["policy"]) & (s60["type"] == r["type"])]
        s = st(g["incl"], g["day"])
        rows.append({"表": f"dist_policy {r['policy']} {r['type']}", "h": "-", "|Δq50|": abs(s["q50"] - r["q50"]),
                     "|Δday_eq_mean|": abs(s["day_eq_mean"] - r["day_eq_mean"]),
                     "|Δse(pooled)|": abs(s["se_pooled_cluster"] - r["se_day_cluster"])})
    B("tchk_recompute", "この台本が生の行から作った値と、走らせの `dist_reaction.csv`・`dist_policy.csv` の差(CSV は 8 桁で丸めてある)",
      pd.DataFrame(rows))

    # ---- t0c 行とセルの数(直す 11) ----
    rows = []
    for name in ("dist_reaction.csv", "dist_size_split.csv", "dist_policy.csv", "dist_s_curve.csv",
                 "policy_action_counts.csv", "policy_judge_counts.csv", "label_counts.csv", "three_way_calibration.csv"):
        df = pd.read_csv(src / name)
        rows.append({"もの": f"走らせの {name}", "行": len(df), "セル(行 × 列)": int(df.size)})
    rows.append({"もの": "この文書の表のうち t0c 以外(BLOCK の数 = " + str(len(nblk)) + "。t0c 自身の行とセルは含まない)", "行": sum(r for _, r, _ in nblk),
                 "セル(行 × 列)": sum(c for _, _, c in nblk)})
    B("t0c_counts", "走らせの集計表と、この文書の表の行・セルの数(台本で数えた)", pd.DataFrame(rows))
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--in", dest="src", default=str(DEFAULT_IN))
    ap.add_argument("--iv", default=str(DEFAULT_IV))
    ap.add_argument("--section", choices=("tables", "manifest", "all"), default="all")
    a = ap.parse_args(argv)
    src = Path(a.src).resolve()
    if a.section in ("manifest", "all"):
        print(manifest(src, Path(a.iv).resolve()))
    if a.section in ("tables", "all"):
        print(tables(src, Path(a.iv).resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
