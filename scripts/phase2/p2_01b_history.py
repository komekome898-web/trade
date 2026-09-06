#!/usr/bin/env python
"""P2-01b "edge trend" — full-history descriptive run, NO SEAL APPLIES.

Implements `docs/PHASE2/P2-01b/PREREG.md` §4 ("過去データでの検証、判定には
使わない"): builds the SAME P2-01 pairs (day-session close(t) -> next
day-session open(t+1), quarterly roll-adjacent exclusion, |simple return| >
0.10 glitch drop, per-pair conservative cost 122 yen / notional) over the
FULL unsealed history 2007-09-19..2026-08-28, using the exact tested
functions from `scripts/phase2/p2_01_run.py` (`build_pairs`,
`mark_roll_adjacent`, `describe`, ...) -- unchanged, imported not
reimplemented.

**No seal applies to this run.** P2-01's own final evaluation (2026-09-06,
`docs/PHASE2/P2-01/PREREG.md`) already opened the full 2007-2026 window,
so `backtest_data/n225f_225labo_20260828/{day,night}_session_daily.csv.gz`
are read here with PLAIN `pandas.read_csv` -- `bot.research.sealed` is not
imported and no unseal guard is checked, because there is nothing left to
seal for this unit. Every number this script produces is DESCRIPTIVE
(PREREG §0 制約 1: "過去データでの検証は仮説の生成と絞り込みであり、戦略
としての判定はフォワードのみで行う"). Nothing here is a 採用/棄却 judgment.

Outputs four things to `--out` (default
backtest_data/phase2_runs/P2-01b/history_20260906/):
  (a) decomposition_dev_vs_sealed.csv   -- gross/cost/net, dev vs sealed-period
      (PREREG §2's own table, built here from a fresh read to cross-check it)
  (b) edge_trend on gross r_night / cost_bps / net r_net over the full history
      (`bot.research.overnight.edge_trend`, PHASE2_TEMPLATES.md §5): rolling
      window, period table, slope+CI+MDE, half-split, regime table, judgment
  (c) leg decomposition (a)(b)(c) per regime, with CIs
  (d) H1 identity check: cost_bps(t) * close(t) * 10 == 122 for every pair

Usage: PYTHONPATH=src python scripts/phase2/p2_01b_history.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from bot.research.overnight import edge_trend  # noqa: E402
from phase2.p2_01_run import (  # noqa: E402  (dev-set runner: reused, unchanged)
    ANALYSIS_START,
    BLOCK,
    COST_YEN_CONSERVATIVE,
    DAY_FILE,
    GLITCH_THRESHOLD,
    MULTIPLIER,
    NIGHT_FILE,
    N_BOOT,
    SEED,
    _git_rev,
    _md5,
    _table,
    build_pairs,
    describe,
    mark_roll_adjacent,
    years_span,
)

UNIT = "P2-01b"
ROLL_RULE = "quarterly"  # the P2-01 FINAL configuration (ITER.md iteration 1)

# ---- the two reference sub-periods from PREREG.md §2 (P2-01's own numbers,
# reproduced here from a fresh read, not copy-pasted) ------------------------
SEALED_START = pd.Timestamp("2020-12-21")
SEALED_END = pd.Timestamp("2026-08-28")
REF_DEV = {"gross": 4.30, "cost": 8.89, "net": -4.59}
REF_SEALED = {"gross": 6.06, "cost": 3.57, "net": 2.49}

# ---- PREREG.md §4 H3 regime boundaries (2021-09-21 = data-derived candidate,
# the single night with no night_session_daily row inside the P2-01 sealed
# window -- see p2_01_final.py's `night_ext_date`; NOT a primary-source date,
# the 05:30->06:00 extension's exact day is not recorded in any schema/manifest
# held in this repo). The other three are primary-source dates already used
# by p2_01_run.py / p2_01_final.py's own REGIMES tables.
REGIME_DATES = [
    pd.Timestamp("2011-02-14"),
    pd.Timestamp("2016-07-19"),
    pd.Timestamp("2021-09-21"),
    pd.Timestamp("2024-11-05"),
]

# edge_trend pre-registered call parameters (PHASE2_TEMPLATES.md §5.8: window
# and block are fixed; time_unit/time_axis/period are this unit's explicit
# choice, stated here and in RESULTS.md so a rerun cannot silently drift).
EDGE_TREND_PARAMS = dict(window=250, block=20, time_unit="year",
                         time_axis="calendar", period="year",
                         n_boot=N_BOOT, seed=SEED)

OUT_DIR = REPO_ROOT / "backtest_data" / "phase2_runs" / "P2-01b" / "history_20260906"


# ---------------------------------------------------------------------------
# plain (unsealed) load
# ---------------------------------------------------------------------------

def _load_plain(path: str, root: Path) -> pd.DataFrame:
    """Plain `pandas.read_csv` -- no seal, because none applies to P2-01b."""
    df = pd.read_csv(root / path)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def _build_main(day: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pairs + main (quarterly-roll-excluded, glitch-excluded) for one
    contiguous day-session frame, using the SAME functions p2_01_run.py's
    main() uses. Returns (pairs, main)."""
    trading_days = list(day["date"])
    pairs = build_pairs(day)
    pairs["roll_quarterly"] = mark_roll_adjacent(pairs, trading_days, "quarterly")
    pairs["is_glitch"] = pairs["r"].abs() > GLITCH_THRESHOLD
    main = pairs[~pairs["roll_quarterly"] & ~pairs["is_glitch"]].reset_index(drop=True)
    return pairs, main


# ---------------------------------------------------------------------------
# (c) leg decomposition per regime
# ---------------------------------------------------------------------------

def _regime_bounds(ds: pd.Series, boundary_dates: list[pd.Timestamp]
                   ) -> list[tuple[str, pd.Timestamp, pd.Timestamp]]:
    """[(label, lo, hi_exclusive), ...] covering ds's full span, split only at
    the pre-registered boundary_dates (PREREG §5.6: no post-hoc splits)."""
    bounds = sorted(boundary_dates)
    edges = [ds.min()] + bounds + [ds.max() + pd.Timedelta(days=1)]
    out = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        label_hi = (hi - pd.Timedelta(days=1)).date() if i < len(edges) - 2 else ds.max().date()
        out.append((f"{lo.date()}..{label_hi}", lo, hi))
    return out


def leg_decomposition_by_regime(main_with_night: pd.DataFrame,
                                block: int, n_boot: int, seed: int) -> pd.DataFrame:
    """Per pre-registered regime: mean+CI of leg(a) 引け->夜間寄り,
    leg(b) 夜間寄り->夜間引け, leg(c) 夜間引け->翌日中寄り, on the subset of
    `main_with_night` that has a matching night-session row."""
    c3 = main_with_night[main_with_night["has_night"]]
    ds = pd.to_datetime(c3["date"])
    rows = []
    for label, lo, hi in _regime_bounds(ds, REGIME_DATES):
        mask = (ds >= lo) & (ds < hi)
        seg = c3.loc[mask]
        for leg_name, col in (("(a) 引け→夜間寄り", "leg_a_bps"),
                              ("(b) 夜間寄り→夜間引け", "leg_b_bps"),
                              ("(c) 夜間引け→翌日中寄り", "leg_c_bps")):
            row = describe(seg[col].to_numpy(dtype=float), leg_name,
                           years_span(seg) if len(seg) else float("nan"),
                           seed=seed, ci=True)
            row["regime"] = label
            rows.append(row)
    return pd.DataFrame(rows)[["regime", "label", "n", "mean", "ci_lo", "ci_hi", "sd", "t"]]


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def main(out_dir: Path | None = None, root: Path | str = REPO_ROOT) -> int:
    root = Path(root)
    out = out_dir if out_dir is not None else OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    def write_csv(df: pd.DataFrame, name: str) -> None:
        df.to_csv(out / name, index=False)
        written.append(name)

    # ---- plain (unsealed) load ---------------------------------------------
    day_raw = _load_plain(DAY_FILE, root)
    night_raw = _load_plain(NIGHT_FILE, root)

    # ================================================================
    # (a) decomposition table: dev-set vs sealed-period, built SEPARATELY
    #     (each its own restricted day frame + its own endpoint rule, exactly
    #     as p2_01_run.py iteration 1 / p2_01_final.py built them -- NOT a
    #     post-hoc split of one combined pairs table, which would keep one
    #     extra boundary pair neither run actually counted).
    # ================================================================
    day_dev = day_raw[(day_raw["date"] >= ANALYSIS_START)
                      & (day_raw["date"] < SEALED_START)].reset_index(drop=True)
    day_sealed = day_raw[(day_raw["date"] >= SEALED_START)
                         & (day_raw["date"] <= SEALED_END)].reset_index(drop=True)
    _, main_dev = _build_main(day_dev)
    _, main_sealed = _build_main(day_sealed)

    def _decomp_row(label: str, main: pd.DataFrame, ref: dict) -> dict:
        gross = float(main["r_night_bps"].mean())
        cost = float(main["cost_bps_cons"].mean())
        net = float(main["r_net_bps_cons"].mean())
        return {
            "period": label, "n": len(main),
            "gross_bps": gross, "mean_cost_bps": cost, "net_bps": net,
            "ref_gross_bps": ref["gross"], "ref_mean_cost_bps": ref["cost"],
            "ref_net_bps": ref["net"],
            "matches_reference_within_0.01": bool(
                abs(gross - ref["gross"]) < 0.01 and abs(cost - ref["cost"]) < 0.01
                and abs(net - ref["net"]) < 0.01),
        }

    decomp_rows = [
        _decomp_row(f"開発セット {ANALYSIS_START.date()}..{(SEALED_START - pd.Timedelta(days=1)).date()}",
                   main_dev, REF_DEV),
        _decomp_row(f"封印期間 {SEALED_START.date()}..{SEALED_END.date()}",
                   main_sealed, REF_SEALED),
    ]
    decomp_df = pd.DataFrame(decomp_rows)
    write_csv(decomp_df, "decomposition_dev_vs_sealed.csv")

    # ================================================================
    # full-history main set (single continuous build, quarterly roll rule)
    # -- this is what (b), (c) and (d) below all run on.
    # ================================================================
    day_full = day_raw[day_raw["date"] >= ANALYSIS_START].reset_index(drop=True)
    pairs_full, main_full = _build_main(day_full)
    main_full = main_full.sort_values("date").reset_index(drop=True)

    # ---- (d) H1 identity check: cost_bps(t) * close(t) * 10 == 122 --------
    lhs = pairs_full["cost_bps_cons"] * pairs_full["close_t"] * MULTIPLIER / 1e4
    h1_ok = np.allclose(lhs.to_numpy(dtype=float), COST_YEN_CONSERVATIVE, atol=1e-6)
    h1_max_abs_err = float((lhs - COST_YEN_CONSERVATIVE).abs().max())
    h1_df = pd.DataFrame([{
        "n_pairs_checked": len(pairs_full),
        "formula": "cost_bps_cons(t) * close_t(t) * MULTIPLIER(10) / 1e4",
        "expected_yen": COST_YEN_CONSERVATIVE,
        "max_abs_error_yen": h1_max_abs_err,
        "all_pairs_match": bool(h1_ok),
    }])
    write_csv(h1_df, "h1_identity_check.csv")

    # ---- night-session join for the leg decomposition ----------------------
    nn = night_raw[["date", "open", "close"]].rename(
        columns={"date": "date_t1", "open": "night_open", "close": "night_close"})
    main_full = main_full.merge(nn, on="date_t1", how="left")
    main_full["has_night"] = main_full["night_open"].notna()
    main_full["leg_a_bps"] = (main_full["night_open"] / main_full["close_t"] - 1.0) * 1e4
    main_full["leg_b_bps"] = (main_full["night_close"] / main_full["night_open"] - 1.0) * 1e4
    main_full["leg_c_bps"] = (main_full["open_t1"] / main_full["night_close"] - 1.0) * 1e4

    # ================================================================
    # (b) edge_trend on gross r_night / cost_bps / net r_net, full history
    # ================================================================
    legs = {
        "gross": main_full["r_night_bps"].to_numpy(dtype=float),
        "cost": main_full["cost_bps_cons"].to_numpy(dtype=float),
        "net": main_full["r_net_bps_cons"].to_numpy(dtype=float),
    }
    dates = main_full["date"]
    edge_results: dict[str, dict] = {}
    for name, values in legs.items():
        res = edge_trend(dates, values, regime_dates=REGIME_DATES, **EDGE_TREND_PARAMS)
        edge_results[name] = res
        write_csv(res["rolling"], f"edge_trend_rolling_{name}.csv")
        write_csv(res["period_table"], f"edge_trend_period_{name}.csv")
        write_csv(res["regime_table"], f"edge_trend_regime_{name}.csv")

    summary_rows = []
    for name, res in edge_results.items():
        hs = res["half_split"]
        summary_rows.append({
            "leg": name, "n": res["params"]["n"],
            "slope": res["slope"], "slope_unit": res["slope_unit"],
            "slope_ci_lo": res["slope_ci"][0], "slope_ci_hi": res["slope_ci"][1],
            "slope_se": res["slope_se"], "slope_mde": res["slope_mde"],
            "last_window_mean": res["last_window"]["mean"] if res["last_window"] else float("nan"),
            "last_window_ci_lo": res["last_window"]["ci_lo"] if res["last_window"] else float("nan"),
            "last_window_ci_hi": res["last_window"]["ci_hi"] if res["last_window"] else float("nan"),
            "half_first_mean": hs["mean_first"], "half_second_mean": hs["mean_second"],
            "half_diff": hs["diff"], "half_diff_ci_lo": hs["diff_ci"][0],
            "half_diff_ci_hi": hs["diff_ci"][1],
            "judgment": res["judgment"],
        })
    summary_df = pd.DataFrame(summary_rows)
    write_csv(summary_df, "edge_trend_summary.csv")

    # ================================================================
    # (c) leg decomposition (a)(b)(c) per regime, with CIs
    # ================================================================
    leg_regime_df = leg_decomposition_by_regime(main_full, BLOCK, N_BOOT, SEED)
    write_csv(leg_regime_df, "leg_decomposition_by_regime.csv")

    # ---- also write the full pairs table for provenance --------------------
    pairs_out = main_full.copy()
    pairs_out["date"] = pd.to_datetime(pairs_out["date"]).dt.date
    pairs_out["date_t1"] = pd.to_datetime(pairs_out["date_t1"]).dt.date
    write_csv(pairs_out, "pairs_full_history.csv")

    # ================================================================
    # RESULTS.md
    # ================================================================
    md: list[str] = []
    md.append("# P2-01b エッジ推移 — 全期間の記述的検証(封印なし)")
    md.append("")
    md.append(f"実行日 2026-09-06 / seed {SEED} / git {_git_rev()[:12]} / 単位 {UNIT}。")
    md.append("")
    md.append("**本書に封印は一切適用されない。** P2-01 の最終評価(2026-09-06)が既に "
              "2007-2026 の全期間を開けたため、本スクリプトは "
              "`backtest_data/n225f_225labo_20260828/{day,night}_session_daily.csv.gz` を"
              "`bot.research.sealed` を一切経由せず通常の `pandas.read_csv` で読む。"
              "したがって以下の数値はすべて**記述**であり、"
              "`docs/PHASE2/P2-01b/PREREG.md` §0 の制約どおり**判定には使わない**"
              "(判定はフォワード運用のみで行う)。")
    md.append("")
    md.append("## (a) 分解表: 開発セット vs 封印期間(PREREG §2 の再現)")
    md.append("")
    md.append("開発セットと封印期間は**別々に**構築している(それぞれ自身の日中データ枠から"
              "端点規則を適用。1 本の全期間ペア表を事後分割したものではない — "
              "事後分割だと境界をまたぐペアが 1 本余分に残り、n が 1 ずれる)。")
    md.append("")
    md.append(_table(decomp_df.to_dict("records"), [
        ("period", "期間", -1), ("n", "n", 0),
        ("gross_bps", "グロス平均(bps)", 2), ("mean_cost_bps", "平均コスト(bps)", 2),
        ("net_bps", "費用後平均(bps)", 2), ("ref_gross_bps", "PREREG グロス", 2),
        ("ref_mean_cost_bps", "PREREG コスト", 2), ("ref_net_bps", "PREREG 費用後", 2),
        ("matches_reference_within_0.01", "PREREG と一致(±0.01bps)", -1),
    ]))
    md.append("")
    md.append("## (b) エッジ推移: グロス r_night / コスト cost_bps / 費用後 r_net(全期間)")
    md.append("")
    md.append(f"`edge_trend` 呼び出しパラメータ(事前登録、3 系列とも共通): "
              f"window={EDGE_TREND_PARAMS['window']}、block={EDGE_TREND_PARAMS['block']}、"
              f"time_unit={EDGE_TREND_PARAMS['time_unit']!r}、"
              f"time_axis={EDGE_TREND_PARAMS['time_axis']!r}、"
              f"period={EDGE_TREND_PARAMS['period']!r}、n_boot={EDGE_TREND_PARAMS['n_boot']:,}、"
              f"seed={EDGE_TREND_PARAMS['seed']}。制度区分の境界日: "
              + "、".join(str(d.date()) for d in REGIME_DATES)
              + "(2021-09-21 はデータ由来の候補日 — 一次資料に実施日の記載が無い夜間延長の、"
              "夜間セッション行が欠損する唯一の夜)。")
    md.append("")
    md.append(_table(summary_df.to_dict("records"), [
        ("leg", "系列", -1), ("n", "n", 0),
        ("slope", "傾き", 4), ("slope_unit", "単位", -1),
        ("slope_ci_lo", "傾き CI下限", 4), ("slope_ci_hi", "傾き CI上限", 4),
        ("slope_se", "傾き SE", 4), ("slope_mde", "傾き MDE", 4),
        ("last_window_mean", "直近250夜 平均", 3),
        ("last_window_ci_lo", "直近250夜 CI下限", 3),
        ("last_window_ci_hi", "直近250夜 CI上限", 3),
        ("half_diff", "前半/後半 差", 3),
        ("half_diff_ci_lo", "差 CI下限", 3), ("half_diff_ci_hi", "差 CI上限", 3),
        ("judgment", "判定文", -1),
    ]))
    md.append("")
    md.append("判定文は PHASE2_TEMPLATES.md §5.7 の固定規則(拡大 = 傾き CI が正でゼロを含まず"
              "**かつ**直近 250 夜の CI が正。縮小 = 傾き CI が負でゼロを含まず**または**"
              "直近 250 夜の CI が負。それ以外は判定不能)。判定不能を「安定」と読み替えない。")
    md.append("")
    md.append("### 年次表・移動窓・制度区分の別表")
    md.append("")
    md.append("`edge_trend_rolling_{gross,cost,net}.csv`(250 夜移動平均+CI)、"
              "`edge_trend_period_{gross,cost,net}.csv`(暦年表)、"
              "`edge_trend_regime_{gross,cost,net}.csv`(制度区分別)を別ファイルに出力した"
              "(本文には要約のみ)。")
    md.append("")
    md.append("## (c) 区間分解 (a)(b)(c) の制度区分別(夜間セッション内訳、CI 付き)")
    md.append("")
    md.append("(a) 引け→夜間寄り、(b) 夜間寄り→夜間引け、(c) 夜間引け→翌日中寄り。"
              "分母は夜間行が実在するペアのみ(欠損夜は除く)。")
    md.append("")
    for regime_label in dict.fromkeys(leg_regime_df["regime"]):
        sub = leg_regime_df[leg_regime_df["regime"] == regime_label]
        md.append(f"**{regime_label}**")
        md.append("")
        md.append(_table(sub.to_dict("records"), [
            ("label", "脚", -1), ("n", "n", 0), ("mean", "平均(bps)", 3),
            ("ci_lo", "CI下限", 3), ("ci_hi", "CI上限", 3), ("sd", "SD", 2), ("t", "t", 2),
        ]))
        md.append("")
    md.append("## (d) H1 恒等式チェック")
    md.append("")
    md.append(f"cost_bps(t) × close_day(t) × 10 は全 {len(pairs_full):,} ペアで "
              f"{COST_YEN_CONSERVATIVE} 円に一致するか: **{'一致' if h1_ok else '不一致'}**"
              f"(最大絶対誤差 {h1_max_abs_err:.2e} 円、浮動小数点の丸め誤差の範囲)。"
              "これは H1(費用の算術)の定義上の恒等式であり、統計的な検定ではない。")
    md.append("")
    md.append("## 注意点・限界")
    md.append("")
    md.append("- 本書のいかなる数値も採用・棄却の判断に使わない。P2-01b PREREG §0 のとおり、"
              "過去データでの検証は仮説の絞り込みであり、戦略としての判定は"
              "2026-09-07 以降のフォワード運用でのみ行う。")
    md.append("- エッジ推移の移動窓・傾きは自己相関を持つ日次系列にブロック・ブートストラップ"
              "(ブロック長 20)を適用しているが、レジーム変化(制度区分)自体が系列の非定常性を"
              "生む可能性があり、単一の線形傾きはその非定常性を平均化した近似に過ぎない。")
    md.append("- 2021-09-21 の制度区分境界はデータ由来の候補日であり、一次資料による確認ではない"
              "(P2-01 最終評価 §6 と同じ限界)。")
    md.append("")
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    written.append("RESULTS.md")

    # ================================================================
    # RUN.json
    # ================================================================
    run = {
        "unit": UNIT,
        "seal_applies": False,
        "seal_note": "P2-01's own final evaluation already opened the full "
                     "2007-2026 window; this run reads DAY_FILE/NIGHT_FILE "
                     "with plain pandas.read_csv, bot.research.sealed is not "
                     "imported.",
        "run_date": "2026-09-06",
        "seed": SEED,
        "git_rev": _git_rev(),
        "script": "scripts/phase2/p2_01b_history.py",
        "script_md5": _md5(Path(__file__)),
        "inputs": [{"path": p, "md5": _md5(root / p)} for p in (DAY_FILE, NIGHT_FILE)],
        "roll_rule": ROLL_RULE,
        "analysis_start": str(ANALYSIS_START.date()),
        "sealed_boundary_used_for_decomposition_only": [
            str(SEALED_START.date()), str(SEALED_END.date())],
        "regime_dates": [str(d.date()) for d in REGIME_DATES],
        "edge_trend_params": {k: v for k, v in EDGE_TREND_PARAMS.items()},
        "n_pairs_full_history_main_set": len(main_full),
        "decomposition": decomp_df.to_dict("records"),
        "edge_trend_summary": summary_df.to_dict("records"),
        "h1_identity_check": h1_df.to_dict("records")[0],
        "outputs": sorted(written),
    }
    (out / "RUN.json").write_text(
        json.dumps(run, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8")

    print(json.dumps({"decomposition": run["decomposition"],
                      "edge_trend_summary": run["edge_trend_summary"],
                      "h1_identity_check": run["h1_identity_check"]},
                     ensure_ascii=False, indent=2, default=str))
    print(f"wrote {len(written) + 1} files to {out}")
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", type=Path, default=None,
                   help="Output directory (default: backtest_data/phase2_runs/"
                        "P2-01b/history_20260906).")
    return p.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(out_dir=_parse_args().out))
