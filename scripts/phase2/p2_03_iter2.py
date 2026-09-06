"""P2-03 反復2(開発セットのみ)-- 事前登録済みの代替銘柄追加。

`docs/PHASE2/P2-03/ITER.md` 反復2 行 / `docs/PHASE2/P2-03/PREREG.md`
「代替銘柄(事前登録、実行前に取得・スナップショット)」節の実装。

TOPIX 連動の高価格 ETF 2 銘柄(1348.T = MAXIS TOPIX ETF, 1305.T = iFreeETF
TOPIX)を、反復0/1(`scripts/phase2/p2_03_run.py`)と**同一の規則1/2/3/5・
呼値帯コスト・単純収益・train/val 分割・ブロック・ブートストラップ(20営業日
x2,000回、seed 20260906)** で評価する。仮説の選択ではないため事前登録カウント
(N)は据え置き(ITER.md 反復2 の「追加構成数=0」参照)。

このスクリプトは `p2_03_run.py` を一切編集しない(挙動不変)。
`p2_03_run.build_series_result` をそのまま再利用する薄いラッパーで、
読み込み元(ファイルパス・封印ユニット)だけを差し替える:

  * 1348.T / 1305.T -- `backtest_data/jpx_etf_daily_20260906_topix_alt/`
    から `bot.research.sealed.load_unsealed(path, "P2-03b")` で読む
    (封印記録 `backtest_data/phase2_sealed/P2-03b/SEALED.json`、境界
    2022-03-05)。**`load_sealed` は一切呼ばない。**
  * 1321.T(参照系列)/ 1306.T(比較対象、反復1の価格水準補正込み)--
    従来どおり `backtest_data/jpx_etf_daily_20260905/` から
    `load_unsealed(path, "P2-03")` で読む。

出力: `backtest_data/phase2_runs/P2-03/iter2_20260906/`
  pairs_<SYM>.csv, rule_counts.csv, main_indicator.csv, summary_by_series.csv,
  sign_agreement.csv, residual_vs_1321.csv, correlation_with_1306.csv,
  train_val_split.csv, RUN.json, RESULTS.md

このスクリプトは判定(採用/棄却)を書かない。数値と件数のみ。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bot.research.sealed import load_unsealed, md5_of  # noqa: E402
from bot.research.overnight import EDGE_TREND_SLOPE_MDE_Z  # noqa: E402
from bot.constants import load_constants, require_source  # noqa: E402

import p2_03_run as base  # noqa: E402 -- 反復0/1 のコード経路をそのまま再利用

UNIT_MAIN = "P2-03"
UNIT_ALT = "P2-03b"

MAIN_SNAPSHOT_DIR = REPO_ROOT / "backtest_data" / "jpx_etf_daily_20260905"
ALT_SNAPSHOT_DIR = REPO_ROOT / "backtest_data" / "jpx_etf_daily_20260906_topix_alt"
RUNS_BASE_DIR = REPO_ROOT / "backtest_data" / "phase2_runs" / "P2-03"
ITER1_DIR = RUNS_BASE_DIR / "iter1_20260906"

ITERATION = 2


def default_out_dir() -> Path:
    return RUNS_BASE_DIR / f"iter{ITERATION}_20260906"


# 銘柄 -> (パス, 封印ユニット, 価格水準補正を適用するか)
# 1306.T のみ反復1と同じ補正(schema/jpx_etf_daily.json CORRECTION 2026-09-06)。
# 1348.T/1305.T は補正テーブルに存在しない銘柄なので False でも副作用なし
# (`base.PRICE_LEVEL_CORRECTIONS` は "1306.T" キーしか持たない)。
SYMBOL_SOURCES: dict[str, tuple[Path, str, bool]] = {
    "1306.T": (MAIN_SNAPSHOT_DIR / "1306.T.csv", UNIT_MAIN, True),
    "1321.T": (MAIN_SNAPSHOT_DIR / "1321.T.csv", UNIT_MAIN, False),
    "1348.T": (ALT_SNAPSHOT_DIR / "1348.T.csv", UNIT_ALT, False),
    "1305.T": (ALT_SNAPSHOT_DIR / "1305.T.csv", UNIT_ALT, False),
}
ALT_SYMBOLS = ["1348.T", "1305.T"]
REFERENCE_SYMBOL = "1321.T"
COMPARISON_SYMBOL = "1306.T"  # 同じ TOPIX 指数 -- 相関の対象

RUN_SEED = base.RUN_SEED  # 20260906
BOOT_N = base.BOOT_N  # 2000
BOOT_BLOCK = base.BOOT_BLOCK  # 20
TRAIN_END = base.TRAIN_END
VAL_START = base.VAL_START
VAL_END = base.VAL_END


def load_and_build(sym: str, bands, unit_map: dict[str, tuple[Path, str, bool]] | None = None) -> dict:
    """`p2_03_run.analyze_series` と同じ処理(`load_unsealed` -> `build_series_result`)
    を、銘柄ごとに異なる封印ユニット/パスへ差し替えて実行する薄いラッパー。

    `unit_map` 省略時は `SYMBOL_SOURCES`(本番の割当)を使う。テストから
    別ユニットを渡して封印違反(`SealedDataError`)を検証できるようにするため
    引数化してある。
    """
    sources = unit_map if unit_map is not None else SYMBOL_SOURCES
    path, unit, apply_correction = sources[sym]
    df = load_unsealed(path, unit)
    return base.build_series_result(sym, df, bands, apply_price_correction=apply_correction)


def mde_bps(sigma: float, n: int) -> float:
    """MDE = z(alpha=0.05 両側, power=0.8) * SE、SE = sigma/sqrt(n)。
    PREREG.md 表(監査3回目実測)と同じ式(`bot.research.overnight.EDGE_TREND_SLOPE_MDE_Z`
    を再利用。1306=5.10 / 1591=5.64 / 2516=12.82 / 1321=5.26bps と一致検算済み)。"""
    if n <= 0 or not np.isfinite(sigma):
        return float("nan")
    return float(EDGE_TREND_SLOPE_MDE_Z * sigma / np.sqrt(n))


def main(out_dir: Path | None = None) -> Path:
    out_dir = Path(out_dir) if out_dir is not None else default_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(RUN_SEED)

    constants = load_constants(REPO_ROOT)
    tick_const = require_source("jpx_cash_equity.etf_tick_size_yen_by_price_band", constants)
    bands = base.parse_tick_bands(tick_const.value)
    commission_const = require_source("jpx_cash_equity.sor_commission_yen", constants)
    assert commission_const.value == 0, "手数料が0円想定と食い違う -- コスト式の見直しが必要"

    symbols = [COMPARISON_SYMBOL, REFERENCE_SYMBOL] + ALT_SYMBOLS
    results: dict[str, dict] = {sym: load_and_build(sym, bands) for sym in symbols}

    # -- rule_counts.csv ----------------------------------------------------
    rule_rows = []
    for sym in symbols:
        res = results[sym]
        pairs = res["pairs"]
        rule_rows.append({
            "series": sym,
            "n_rows_dev": res["n_rows"],
            "n_pairs_total": len(pairs),
            "rule1_badprint_rows": res["n_badprint_rows"],
            "rule1_badprint_runs": len(res["badprint_events"]),
            "rule1_one_sided_info_rows": res["n_one_sided_info"],
            "rule2_split_rows": res["n_split_rows"],
            "rule3_null_rows": res["n_null_rows"],
            "rule5_ghost_rows": res["n_ghost_rows"],
            "n_pairs_excluded": int(pairs["excluded"].sum()),
            "n_pairs_valid_raw": int(pairs["valid_raw"].sum()),
            "n_pairs_clean": int(pairs["clean"].sum()),
        })
    pd.DataFrame(rule_rows).to_csv(out_dir / "rule_counts.csv", index=False)

    # -- main_indicator.csv (before/after x optimistic/conservative) -------
    indicator_rows = []
    for sym in symbols:
        pairs = results[sym]["pairs"]
        for stage, mask_col in (("before_exclusion", "valid_raw"), ("after_exclusion", "clean")):
            sub = pairs.loc[pairs[mask_col]]
            opt = base.mean_ci(sub["net_opt_bps"].to_numpy(), rng)
            cons = base.mean_ci(sub["net_cons_bps"].to_numpy(), rng)
            indicator_rows.append({"series": sym, "stage": stage, "cost_scenario": "optimistic", **opt})
            indicator_rows.append({"series": sym, "stage": stage, "cost_scenario": "conservative", **cons})
    indicator_df = pd.DataFrame(indicator_rows)
    indicator_df.to_csv(out_dir / "main_indicator.csv", index=False)

    # -- summary_by_series.csv (clean のみ): n / sigma / MDE / 平均 / コスト / 夜間-日中 --
    summary_rows = []
    for sym in symbols:
        pairs = results[sym]["pairs"]
        clean = pairs.loc[pairs["clean"]]
        r_night = clean["r_night_bps"].to_numpy(dtype=float)
        r_night_finite = r_night[np.isfinite(r_night)]
        n = int(len(r_night_finite))
        sigma = float(np.std(r_night_finite, ddof=1)) if n > 1 else float("nan")
        gross_ci = base.mean_ci(r_night, rng)
        cons_ci = base.mean_ci(clean["net_cons_bps"].to_numpy(), rng)
        diff = (clean["r_night_bps"] - clean["r_day_bps"]).to_numpy()
        diff_ci = base.mean_ci(diff, rng)
        mean_cost = float(clean["cost_cons_bps"].mean()) if len(clean) else float("nan")
        summary_rows.append({
            "series": sym,
            "n_clean": n,
            "sigma_r_night_bps": sigma,
            "mde_bps": mde_bps(sigma, n),
            "mean_gross_bps": gross_ci["mean_bps"], "gross_ci_lo": gross_ci["ci_lo"], "gross_ci_hi": gross_ci["ci_hi"],
            "mean_net_cons_bps": cons_ci["mean_bps"], "cons_ci_lo": cons_ci["ci_lo"], "cons_ci_hi": cons_ci["ci_hi"],
            "mean_cost_cons_bps": mean_cost,
            "night_minus_day_mean_bps": diff_ci["mean_bps"],
            "night_minus_day_ci_lo": diff_ci["ci_lo"], "night_minus_day_ci_hi": diff_ci["ci_hi"],
        })
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(out_dir / "summary_by_series.csv", index=False)

    # -- sign agreement vs 1321(gross r_night, clean) ------------------------
    ref_mean = summary_df.loc[summary_df["series"] == REFERENCE_SYMBOL, "mean_gross_bps"].iloc[0]
    sign_rows = []
    for sym in symbols:
        m = summary_df.loc[summary_df["series"] == sym, "mean_gross_bps"].iloc[0]
        sign_rows.append({"series": sym, "mean_gross_bps": m,
                           "sign_matches_1321": bool(np.sign(m) == np.sign(ref_mean)) if np.isfinite(m) and np.isfinite(ref_mean) else None})
    pd.DataFrame(sign_rows).to_csv(out_dir / "sign_agreement.csv", index=False)

    # -- residual vs 1321(共通日, clean) -------------------------------------
    frames = {}
    for sym in symbols:
        p = results[sym]["pairs"]
        s = p.loc[p["clean"], ["date_t", "r_night_bps"]].set_index("date_t")["r_night_bps"]
        s.name = sym
        frames[sym] = s
    ref_series = frames[REFERENCE_SYMBOL]
    residual_rows = []
    for sym in ALT_SYMBOLS + [COMPARISON_SYMBOL]:
        common = pd.concat([frames[sym], ref_series], axis=1, sort=True).dropna()
        common.columns = ["etf", "ref"]
        resid = (common["etf"] - common["ref"]).to_numpy()
        ci = base.mean_ci(resid, rng)
        residual_rows.append({"series": sym, "n_common": len(common), **ci})
    pd.DataFrame(residual_rows).to_csv(out_dir / "residual_vs_1321.csv", index=False)

    # -- correlation with 1306(同一指数, r_night, 共通日) --------------------
    comp_series = frames[COMPARISON_SYMBOL]
    corr_rows = []
    for sym in ALT_SYMBOLS + [REFERENCE_SYMBOL]:
        common = pd.concat([frames[sym], comp_series], axis=1, sort=True).dropna()
        common.columns = ["etf", "comp"]
        corr = float(common["etf"].corr(common["comp"])) if len(common) > 1 else float("nan")
        corr_rows.append({"series": sym, "vs": COMPARISON_SYMBOL, "n_common": len(common), "correlation": corr})
    pd.DataFrame(corr_rows).to_csv(out_dir / "correlation_with_1306.csv", index=False)

    # -- train / val split(暦日, 除外後)-- PREREG と同一境界 -----------------
    tv_rows = []
    for sym in symbols:
        pairs = results[sym]["pairs"]
        clean = pairs.loc[pairs["clean"]]
        train = clean.loc[clean["date_t"] <= TRAIN_END]
        val = clean.loc[(clean["date_t"] >= VAL_START) & (clean["date_t"] <= VAL_END)]
        for split_name, sub in (("train", train), ("val", val)):
            opt = base.mean_ci(sub["net_opt_bps"].to_numpy(), rng)
            cons = base.mean_ci(sub["net_cons_bps"].to_numpy(), rng)
            tv_rows.append({"series": sym, "split": split_name, "n": len(sub),
                             "mean_opt_bps": opt["mean_bps"], "opt_ci_lo": opt["ci_lo"], "opt_ci_hi": opt["ci_hi"],
                             "mean_cons_bps": cons["mean_bps"], "cons_ci_lo": cons["ci_lo"], "cons_ci_hi": cons["ci_hi"]})
    pd.DataFrame(tv_rows).to_csv(out_dir / "train_val_split.csv", index=False)

    # -- per-pair raw CSV -----------------------------------------------------
    for sym in symbols:
        safe = sym.replace(".", "")
        results[sym]["pairs"].to_csv(out_dir / f"pairs_{safe}.csv", index=False)

    # -- RUN.json: md5 vs P2-03b の封印記録 ----------------------------------
    seal_record = json.loads((REPO_ROOT / "backtest_data" / "phase2_sealed" / UNIT_ALT / "SEALED.json").read_text(encoding="utf-8"))
    seal_md5_by_path = {e["path"]: e["md5"] for e in seal_record["files"]}
    seal_md5_check = {}
    input_md5 = {}
    for sym in symbols:
        path, unit, _ = SYMBOL_SOURCES[sym]
        computed = md5_of(path)
        input_md5[sym] = computed
        if unit == UNIT_ALT:
            rel = str(path.relative_to(REPO_ROOT))
            sealed_md5 = seal_md5_by_path.get(rel)
            seal_md5_check[sym] = {"computed": computed, "sealed": sealed_md5, "match": computed == sealed_md5}

    run_meta = {
        "unit_alt": UNIT_ALT,
        "unit_main": UNIT_MAIN,
        "iteration": ITERATION,
        "iter_ledger_row": "2",
        "seed": RUN_SEED,
        "git_rev": base.git_rev(),
        "prereg_path": "docs/PHASE2/P2-03/PREREG.md",
        "iter_ledger_path": "docs/PHASE2/P2-03/ITER.md",
        "alt_snapshot_dir": str(ALT_SNAPSHOT_DIR.relative_to(REPO_ROOT)),
        "main_snapshot_dir": str(MAIN_SNAPSHOT_DIR.relative_to(REPO_ROOT)),
        "symbols": symbols,
        "alt_symbols": ALT_SYMBOLS,
        "reference_symbol": REFERENCE_SYMBOL,
        "comparison_symbol": COMPARISON_SYMBOL,
        "input_md5": input_md5,
        "seal_md5_check_alt": seal_md5_check,
        "boot_n": BOOT_N, "boot_block": BOOT_BLOCK,
        "train_end": str(TRAIN_END.date()), "val_start": str(VAL_START.date()), "val_end": str(VAL_END.date()),
        "n_per_series": {
            sym: {
                "n_rows_dev": results[sym]["n_rows"],
                "n_pairs_total": len(results[sym]["pairs"]),
                "n_pairs_excluded": int(results[sym]["pairs"]["excluded"].sum()),
                "n_pairs_clean": int(results[sym]["pairs"]["clean"].sum()),
            }
            for sym in symbols
        },
    }
    (out_dir / "RUN.json").write_text(json.dumps(run_meta, indent=2, ensure_ascii=False), encoding="utf-8")

    write_results_md(results, summary_df, indicator_df, sign_rows, residual_rows, corr_rows, tv_rows,
                      rule_rows, run_meta, out_dir)
    print(f"wrote outputs to {out_dir}")
    return out_dir


def _load_iter1_1306_summary() -> pd.Series | None:
    p = ITER1_DIR / "summary_by_series.csv"
    if not p.is_file():
        return None
    df = pd.read_csv(p)
    row = df.loc[df["series"] == "1306.T"]
    return row.iloc[0] if len(row) else None


def write_results_md(results, summary_df, indicator_df, sign_rows, residual_rows, corr_rows, tv_rows,
                      rule_rows, run_meta, out_dir: Path) -> None:
    lines = []
    lines.append("# P2-03 反復2(開発セットのみ)結果 -- 代替銘柄(1348.T/1305.T)、数値のみ・判定なし")
    lines.append("")
    lines.append(f"git rev: `{run_meta['git_rev']}` / seed: {run_meta['seed']} / "
                 f"train末={run_meta['train_end']} / val={run_meta['val_start']}..{run_meta['val_end']} / "
                 f"封印ユニット: 代替銘柄={run_meta['unit_alt']}(境界2022-03-05)、"
                 f"参照/比較銘柄={run_meta['unit_main']}")
    lines.append("")
    lines.append("読み手: 1348.T/1305.T は `bot.research.sealed.load_unsealed(path, \"P2-03b\")` のみ"
                 "(封印記録 `backtest_data/phase2_sealed/P2-03b/SEALED.json`)。1321.T(参照)と 1306.T"
                 "(比較、反復1の価格水準補正込み)は従来どおり `load_unsealed(path, \"P2-03\")`。"
                 "`load_sealed` は本スクリプトから一切呼んでいない。")
    lines.append("")

    lines.append("## 欠陥規則の件数(規則1/2/3/5、反復0/1と同一定義)")
    lines.append("")
    lines.append("| 系列 | 開発セット行数 | ペア数(生) | 規則1誤プリント行 | 規則1連数 | "
                 "規則1片側info | 規則2分割行 | 規則3null行 | 規則5幽霊行 | 除外ペア数 | "
                 "有効ペア(生) | 有効ペア(除外後) |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rule_rows:
        lines.append(f"| {r['series']} | {r['n_rows_dev']} | {r['n_pairs_total']} | "
                     f"{r['rule1_badprint_rows']} | {r['rule1_badprint_runs']} | {r['rule1_one_sided_info_rows']} | "
                     f"{r['rule2_split_rows']} | {r['rule3_null_rows']} | {r['rule5_ghost_rows']} | "
                     f"{r['n_pairs_excluded']} | {r['n_pairs_valid_raw']} | {r['n_pairs_clean']} |")
    lines.append("")

    lines.append("## 主指標: 除外前後 x 楽観/保守(bps/日、95%CI、ブロック・ブートストラップ 20営業日x2000回)")
    lines.append("")
    lines.append("| 系列 | 除外 | 費用 | n | 平均(bps) | CI下 | CI上 |")
    lines.append("|---|---|---|---|---|---|---|")
    for _, row in indicator_df.iterrows():
        lines.append(f"| {row['series']} | {row['stage']} | {row['cost_scenario']} | {row['n']} | "
                     f"{row['mean_bps']:.2f} | {row['ci_lo']:.2f} | {row['ci_hi']:.2f} |")
    lines.append("")

    lines.append("## 系列別サマリ(除外後のみ): n・σ・MDE・平均・コスト・夜間-日中差")
    lines.append("")
    lines.append("| 系列 | n | σ(bps) | MDE(bps) | 平均gross(bps) | CI | 平均net保守(bps) | CI | "
                 "平均コスト保守(bps,往復) | 夜間-日中平均(bps) | CI |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in summary_df.iterrows():
        lines.append(
            f"| {r['series']} | {r['n_clean']} | {r['sigma_r_night_bps']:.2f} | {r['mde_bps']:.2f} | "
            f"{r['mean_gross_bps']:.2f} | [{r['gross_ci_lo']:.2f}, {r['gross_ci_hi']:.2f}] | "
            f"{r['mean_net_cons_bps']:.2f} | [{r['cons_ci_lo']:.2f}, {r['cons_ci_hi']:.2f}] | "
            f"{r['mean_cost_cons_bps']:.2f} | {r['night_minus_day_mean_bps']:.2f} | "
            f"[{r['night_minus_day_ci_lo']:.2f}, {r['night_minus_day_ci_hi']:.2f}] |"
        )
    lines.append("")
    lines.append("**注意(呼値コストは開発セット全期間の平均)**: 1348.T/1305.T とも呼値1円が10,000円帯まで一律"
                 "(config/constants.yaml)のため、価格が低かった開発セット前半(2011年 ~760円台)ほどbps換算コストが"
                 "大きく、価格が上がった後半(2022年 ~2,000円台)ほど小さい。1348.T は前半平均17.90bps、後半平均11.49bps"
                 "(単純に前後半で二分)。ITER.md 記載の「往復4.6〜4.7bps」は2026-09-04時点の直近価格(1348.T "
                 "4,255円/1305.T 4,328円)によるフォワード時点の見積りであり、開発セット全体の実測平均"
                 "(本表の14.5〜14.7bps)とは異なる母集団(直近1点 vs 開発セット全ペア)である。")
    lines.append("")

    lines.append("## 符号一致(1321との符号一致、gross r_night、除外後)")
    lines.append("")
    lines.append("| 系列 | 平均gross r_night(bps) | 1321と符号一致 |")
    lines.append("|---|---|---|")
    for r in sign_rows:
        lines.append(f"| {r['series']} | {r['mean_gross_bps']:.2f} | {r['sign_matches_1321']} |")
    lines.append("")

    lines.append("## 1321に対する残差(r_night_etf - r_night_1321、共通日平均・CI)")
    lines.append("")
    lines.append("| 系列 | n(共通日) | 残差平均(bps) | CI下 | CI上 |")
    lines.append("|---|---|---|---|---|")
    for r in residual_rows:
        lines.append(f"| {r['series']} | {r['n_common']} | {r['mean_bps']:.2f} | {r['ci_lo']:.2f} | {r['ci_hi']:.2f} |")
    lines.append("")

    lines.append("## 1306.T との相関(同じ TOPIX 指数連動、r_night、共通日、pairwise。~1 を期待)")
    lines.append("")
    lines.append("| 系列 | 比較対象 | n(共通日) | 相関 |")
    lines.append("|---|---|---|---|")
    for r in corr_rows:
        lines.append(f"| {r['series']} | {r['vs']} | {r['n_common']} | {r['correlation']:.4f} |")
    lines.append("")

    lines.append("## train/val split(暦日、除外後)")
    lines.append("")
    lines.append(f"train = 開始..{run_meta['train_end']} / val = {run_meta['val_start']}..{run_meta['val_end']}")
    lines.append("")
    lines.append("| 系列 | split | n | 平均net楽観(bps) | CI | 平均net保守(bps) | CI |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in tv_rows:
        lines.append(f"| {r['series']} | {r['split']} | {r['n']} | {r['mean_opt_bps']:.2f} | "
                     f"[{r['opt_ci_lo']:.2f}, {r['opt_ci_hi']:.2f}] | {r['mean_cons_bps']:.2f} | "
                     f"[{r['cons_ci_lo']:.2f}, {r['cons_ci_hi']:.2f}] |")
    lines.append("")

    lines.append("## 横並び表: 1306(反復1、開発セット) vs 1348.T vs 1305.T")
    lines.append("")
    iter1_1306 = _load_iter1_1306_summary()
    row_1348 = summary_df.loc[summary_df["series"] == "1348.T"].iloc[0]
    row_1305 = summary_df.loc[summary_df["series"] == "1305.T"].iloc[0]
    row_1306_here = summary_df.loc[summary_df["series"] == "1306.T"].iloc[0]
    if iter1_1306 is not None:
        lines.append(f"(反復1出力 `{ITER1_DIR.relative_to(REPO_ROOT)}/summary_by_series.csv` の 1306.T 行と、"
                     "本反復で同一コード経路により再計算した 1306.T 行を突き合わせ済み -- "
                     f"平均net保守(bps): 反復1={iter1_1306['mean_net_cons_bps']:.2f} / "
                     f"本反復再計算={row_1306_here['mean_net_cons_bps']:.2f})")
        lines.append("")
    lines.append("| 項目 | 1306.T(反復1) | 1348.T | 1305.T |")
    lines.append("|---|---|---|---|")
    if iter1_1306 is not None:
        lines.append(f"| n | {int(iter1_1306['n_clean'])} | {int(row_1348['n_clean'])} | {int(row_1305['n_clean'])} |")
        lines.append(f"| σ(bps) | n/a(反復1未記録) | {row_1348['sigma_r_night_bps']:.2f} | {row_1305['sigma_r_night_bps']:.2f} |")
        lines.append(f"| MDE(bps) | {iter1_1306['mde_bps']:.2f} | {row_1348['mde_bps']:.2f} | {row_1305['mde_bps']:.2f} |")
        lines.append(f"| 平均gross楽観(bps) | {iter1_1306['mean_gross_bps']:.2f} | {row_1348['mean_gross_bps']:.2f} | {row_1305['mean_gross_bps']:.2f} |")
        lines.append(f"| 楽観CI | [{iter1_1306['gross_ci_lo']:.2f}, {iter1_1306['gross_ci_hi']:.2f}] | "
                     f"[{row_1348['gross_ci_lo']:.2f}, {row_1348['gross_ci_hi']:.2f}] | "
                     f"[{row_1305['gross_ci_lo']:.2f}, {row_1305['gross_ci_hi']:.2f}] |")
        lines.append(f"| 平均net保守(bps) | {iter1_1306['mean_net_cons_bps']:.2f} | {row_1348['mean_net_cons_bps']:.2f} | {row_1305['mean_net_cons_bps']:.2f} |")
        lines.append(f"| 保守CI | [{iter1_1306['cons_ci_lo']:.2f}, {iter1_1306['cons_ci_hi']:.2f}] | "
                     f"[{row_1348['cons_ci_lo']:.2f}, {row_1348['cons_ci_hi']:.2f}] | "
                     f"[{row_1305['cons_ci_lo']:.2f}, {row_1305['cons_ci_hi']:.2f}] |")
    lines.append(f"| 平均コスト保守(bps、往復) | (反復1 RESULTS.md 参照) | {row_1348['mean_cost_cons_bps']:.2f} | {row_1305['mean_cost_cons_bps']:.2f} |")
    lines.append("")
    lines.append("1306.T列は `iter1_20260906/summary_by_series.csv`(反復1、価格水準補正込み)をそのまま転記。"
                 "1348.T/1305.T は本反復で同一コード経路(`build_series_result`)・同一 train/val 境界・"
                 "同一ブートストラップ設定(20営業日x2,000回、seed 20260906)により算出。")
    lines.append("")

    lines.append("## 封印チェック(P2-03b、md5)")
    lines.append("")
    lines.append("| 系列 | 実測md5 | 封印記録md5 | 一致 |")
    lines.append("|---|---|---|---|")
    for sym, chk in run_meta["seal_md5_check_alt"].items():
        lines.append(f"| {sym} | `{chk['computed']}` | `{chk['sealed']}` | {chk['match']} |")
    lines.append("")

    lines.append("## 出力ファイル")
    lines.append("")
    lines.append("pairs_<SYM>.csv, rule_counts.csv, main_indicator.csv, summary_by_series.csv, "
                 "sign_agreement.csv, residual_vs_1321.csv, correlation_with_1306.csv, train_val_split.csv, RUN.json")
    lines.append("")
    lines.append("本ファイルは判定(採用/棄却)を含まない。数値と件数のみ。ITER.md 反復2 行への"
                 "追記はリードが数値監査の後に行う。")

    (out_dir / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=str, default=None,
                    help="出力ディレクトリ(既定: backtest_data/phase2_runs/P2-03/iter2_20260906/)")
    return p.parse_args(argv)


if __name__ == "__main__":
    _args = parse_args()
    main(out_dir=_args.out)
