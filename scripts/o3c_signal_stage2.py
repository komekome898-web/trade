#!/usr/bin/env python3
"""段2: 後半5,000件に Jev V1 と前半で固定した logistic を一度だけ当てる(2026-09-20)。

委任文: `docs/DATA/delegations/20260920_o3c_signal_v4_stage2_prompt.md`
設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md` §7.4〜§7.6(特に §7.5.1)
段1: `docs/PHASE2/O3C/SIGNAL/V4_STAGE1_REPORT_2026-09-20.md`
反証者: `docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW7_2026-09-20.md`(D5: `apply_frozen_rank` だけを
使い、後半に `build_ecdf`/帯の再計算を呼ばない)

**この道具がすること**
  (a) 選定 `backtest_data/o3c_signal_continue_20260920/jev/selection_manifest.json` の
      5,000 件(呼び出し順 = 選定順)それぞれに、Jev V1(`o3c_jev_state.JEV_QUESTIONS_V1` +
      `StateBuilder.build_state_sentences`)を 1 回(`jev-1.13.0`、`keep_alive=True`、2 件/秒)。
  (b) 同じ 5,000 件に、前半で固定した logistic の予測(位置〈1 件目 / 連鎖の中〉で係数・
      経験分布・材料の並びを切り替える。`o3c_signal_logit.apply_frozen_rank` で
      `logit_ecdf_{first,chain}.npz` から順位を引くだけ ── 後半に対して `build_ecdf` は
      1 度も呼ばない)。
  (c) `data/jev/v4/stage2/answers.jsonl` に 1 行ずつ追記(再開可能: 既に書かれている
      print_id は読み飛ばし、Jev を呼び直さない)。

**帯・経験分布・係数はここでは 1 つも計算しない。** `StateBuilder()` は既定で
`config/o3c_jev_state_bands.yaml` を読むだけ(存在するので再計算しない)。logistic は
`config/o3c_signal_logit_{first,chain}.yaml` の係数と `logit_ecdf_{first,chain}.npz` を
読むだけ。

**探索段なので判定語を 1 つも書かない。`paper_logs/` は開かない。**
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

_HERE = Path(__file__).resolve().parent
REPO_ROOT = _HERE.parent

_spec_js = importlib.util.spec_from_file_location(
    "o3c_jev_state", _HERE / "o3c_jev_state.py")
js = importlib.util.module_from_spec(_spec_js)
assert _spec_js.loader is not None
_spec_js.loader.exec_module(js)

_spec_lg = importlib.util.spec_from_file_location(
    "o3c_signal_logit", _HERE / "o3c_signal_logit.py")
lg = importlib.util.module_from_spec(_spec_lg)
assert _spec_lg.loader is not None
_spec_lg.loader.exec_module(lg)

_spec_calib = importlib.util.spec_from_file_location(
    "o3c_signal_calib", _HERE / "o3c_signal_calib.py")
calib = importlib.util.module_from_spec(_spec_calib)
assert _spec_calib.loader is not None
_spec_calib.loader.exec_module(calib)

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from jev.client import JevClient, JevError  # noqa: E402
from jev.redact import assert_clean  # noqa: E402

check_no_banned = js.check_no_banned

SELECTION_PATH = (REPO_ROOT / "backtest_data" / "o3c_signal_continue_20260920"
                  / "jev" / "selection_manifest.json")
OUT_DIR = REPO_ROOT / "data" / "jev" / "v4" / "stage2"
ANSWERS_PATH = OUT_DIR / "answers.jsonl"
JEV_MODEL = "jev-1.13.0"
RATE_PER_SEC = 2.0
QUESTION_ID = "next_print_within_60s"


# ===========================================================================
# 1. 選定(呼び出し順 = 選定順)
# ===========================================================================
def load_selection(path: Path = SELECTION_PATH) -> list[dict]:
    d = json.loads(path.read_text())
    return d["prints"]


# ===========================================================================
# 2. logistic(前半で固定した係数・経験分布を読むだけ。§7.5.1・反証者7 D5)
# ===========================================================================
def load_beta(config_path: Path, features: list[str]) -> np.ndarray:
    doc = yaml.safe_load(config_path.read_text())
    coef = doc["係数"]
    return np.array([coef["切片"]] + [coef[f] for f in features], dtype=float)


def compute_logit_probs(sb, df_back: pd.DataFrame) -> dict[str, float]:
    """print_id -> logistic の予測。位置(cand_1==0 か否か)で材料・係数・経験分布を
    切り替える(設計 §7.4)。`apply_frozen_rank` だけを使い、`build_ecdf` は呼ばない
    (反証者7 D5)。"""
    out: dict[str, float] = {}
    ecdf_first = lg.load_ecdf_npz(lg.ECDF_FIRST)
    ecdf_chain = lg.load_ecdf_npz(lg.ECDF_CHAIN)
    beta_first = load_beta(lg.CONFIG_FIRST, lg.FEATURES_FIRST)
    beta_chain = load_beta(lg.CONFIG_CHAIN, lg.FEATURES_CHAIN)

    cand1 = pd.to_numeric(df_back["cand_1"], errors="coerce")
    df_first = df_back[cand1 == 0].reset_index(drop=True)
    df_chain = df_back[cand1 > 0].reset_index(drop=True)

    if len(df_first):
        df_first = lg.add_n2_column(sb, df_first)
        X = lg.apply_frozen_rank(ecdf_first, lg.FEATURES_FIRST, df_first)
        p = lg.predict(X, beta_first)
        out.update(dict(zip(df_first["print_id"].tolist(), p.tolist())))

    if len(df_chain):
        X = lg.apply_frozen_rank(ecdf_chain, lg.FEATURES_CHAIN, df_chain)
        p = lg.predict(X, beta_chain)
        out.update(dict(zip(df_chain["print_id"].tolist(), p.tolist())))
    return out


def position_of(cand_1: float) -> str:
    return "1件目" if float(cand_1) == 0 else "連鎖の中"


# ===========================================================================
# 3. 再開: 既に answers.jsonl にある print_id は読み飛ばす(Jev を呼び直さない)
# ===========================================================================
def already_done(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        pid = rec.get("print_id")
        if pid:
            done.add(pid)
    return done


# ===========================================================================
# 4. 本体(Jev 5,000 回だけ。再開可能)
# ===========================================================================
def run_stage2(sb, prints: list[dict], logit_prob_of: dict, label_of: dict,
              out_path: Path = ANSWERS_PATH, rate_per_sec: float = RATE_PER_SEC,
              client=None) -> dict:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = already_done(out_path)
    skipped_at_start = sum(1 for p in prints if p["print_id"] in done)
    own_client = client is None
    if client is None:
        client = JevClient(model=JEV_MODEL, log_dir=str(OUT_DIR / "calls"),
                           keep_alive=True)
    n_calls, n_err = 0, 0
    t_last = 0.0
    try:
        with out_path.open("a", encoding="utf-8") as fh_out:
            for p in prints:
                pid = p["print_id"]
                if pid in done:
                    continue
                row = sb.row_dict(pid)
                position = position_of(row["cand_1"])
                state = sb.build_state_sentences(pid)
                state_str = json.dumps(state, ensure_ascii=False, sort_keys=True,
                                       default=str)
                assert_clean(state_str)
                dt = time.time() - t_last
                if dt < 1.0 / rate_per_sec:
                    time.sleep(1.0 / rate_per_sec - dt)
                t_last = time.time()
                n_calls += 1
                rec: dict = {"print_id": pid, "位置": position,
                            "logit_prob": logit_prob_of.get(pid),
                            "label_60": label_of.get(pid)}
                t0c = time.time()
                try:
                    resp = client.evaluate(state, js.JEV_QUESTIONS_V1)
                    rec["latency_s"] = round(time.time() - t0c, 3)
                    usage = resp.get("usage") or {}
                    ans = resp.get("answers", {}).get(QUESTION_ID, {})
                    rec["jev_prob"] = ans.get("noul")
                    rec["input_tokens"] = usage.get("input_tokens")
                except JevError as e:
                    n_err += 1
                    rec["latency_s"] = round(time.time() - t0c, 3)
                    rec["error"] = str(e)
                fh_out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh_out.flush()
                done.add(pid)
    finally:
        if own_client:
            client.close()
    return {"呼び出し数": n_calls, "エラー数": n_err, "対象件数": len(prints),
           "再開で読み飛ばした件数": skipped_at_start}


# ===========================================================================
# 5. 較正・順位分離・一致・較正の良さ の表(answers.jsonl を読むだけ。数値は
#    data/jev/ にだけ置く)
# ===========================================================================
def _bin_table(prob: np.ndarray, y: np.ndarray, bin_width: float) -> list[dict]:
    """`calib.py` の 20 本固定の帯とは別に、表示用の較正表(0.01 刻み / 0.05 刻み)を
    作る単純な等幅ビン。**設計に無い判断**: 少数帯を外さず全帯をそのまま出す
    (件数 20 未満を外す規則は §7.5.1 が「較正の良さ」の値の計算にだけ課したもので、
    この記述用の表には適用していない)。"""
    n_bins = int(round(1.0 / bin_width))
    ok = np.isfinite(prob) & np.isfinite(y)
    prob, y = prob[ok], y[ok]
    idx = np.clip(np.floor(prob / bin_width + 1e-9).astype(int), 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        mask = idx == b
        n_b = int(mask.sum())
        if n_b == 0:
            continue
        rows.append({"帯": b, "下端": round(b * bin_width, 4),
                     "上端": round((b + 1) * bin_width, 4),
                     "件数": n_b, "実際に続いた割合": float(y[mask].mean())})
    return rows


def _fmt_bin_table(rows: list[dict]) -> str:
    lines = ["| 下端 | 上端 | 件数 | 実際に続いた割合 |", "|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['下端']} | {r['上端']} | {r['件数']} | "
                     f"{r['実際に続いた割合']:.4f} |")
    return "\n".join(lines)


def _threshold_rows(prob: np.ndarray, y: np.ndarray,
                    thresholds=(0.5, 0.6, 0.7, 0.8)) -> list[dict]:
    rows = []
    for thr in thresholds:
        mask = prob >= thr
        n = int(mask.sum())
        prec = float(y[mask].mean()) if n else float("nan")
        rows.append({"閾値": thr, "適合率": prec, "件数": n})
    return rows


def _fmt_excluded(goodness: dict) -> str:
    if not goodness["外した帯"]:
        return "無し"
    return ", ".join(f"[{b['範囲'][0]:.2f},{b['範囲'][1]:.2f}) n={b['件数']}"
                     for b in goodness["外した帯"])


def build_stage2_tables(out_dir: Path = OUT_DIR) -> str:
    answers_path = out_dir / "answers.jsonl"
    recs = [json.loads(ln) for ln in answers_path.read_text(encoding="utf-8").splitlines()
           if ln.strip()]
    df = pd.DataFrame(recs)
    df["jev_prob"] = pd.to_numeric(df.get("jev_prob"), errors="coerce")
    df["logit_prob"] = pd.to_numeric(df.get("logit_prob"), errors="coerce")
    df["label_60"] = pd.to_numeric(df.get("label_60"), errors="coerce")
    df["input_tokens"] = pd.to_numeric(df.get("input_tokens"), errors="coerce")
    df["latency_s"] = pd.to_numeric(df.get("latency_s"), errors="coerce")

    # 基準率(委任文【作るもの】2): 後半全体の続く割合 / この5,000件の続く割合
    mat = pd.read_csv(js.DEFAULT_MATERIALS, low_memory=False, usecols=["print_id", "half"])
    cont_df = pd.read_csv(js.DEFAULT_CONTINUE_ROWS, usecols=["print_id", "label_60"],
                          low_memory=False)
    back = mat[mat["half"] == "後半"].merge(cont_df, on="print_id", how="left")
    base_rate_backhalf = float(pd.to_numeric(back["label_60"], errors="coerce").mean())
    base_rate_5000 = float(df["label_60"].mean())

    lines: list[str] = [
        "# 段2(後半5,000件)の表 — 数値は data/jev/ にだけ置く(リポジトリに入れない)",
        "",
        "委任文: `docs/DATA/delegations/20260920_o3c_signal_v4_stage2_prompt.md`",
        "設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md` §7.5・§7.5.1",
        "", "## 基準率", "",
        f"- 後半全体(母集団 {len(back)} 件)の続く割合(label_60): {base_rate_backhalf:.4f}",
        f"- この5,000件の続く割合(label_60): {base_rate_5000:.4f}", "",
    ]

    lat_all = df["latency_s"].to_numpy(float)
    lat_all = lat_all[np.isfinite(lat_all)]
    tok_all = df["input_tokens"].to_numpy(float)
    tok_all = tok_all[np.isfinite(tok_all)]
    lines += ["## 遅延・入力トークン(全 5,000 回、Jev)", "",
             f"- 遅延 p50 {np.percentile(lat_all, 50):.3f} / p90 "
             f"{np.percentile(lat_all, 90):.3f} / p99 "
             f"{np.percentile(lat_all, 99):.3f} 秒(n={lat_all.size})",
             f"- 入力トークン平均 {tok_all.mean():.1f}(n={tok_all.size})", ""]

    for pos_key in ("1件目", "連鎖の中"):
        sub = df[df["位置"] == pos_key].copy()
        y = sub["label_60"].to_numpy(float)
        jev = sub["jev_prob"].to_numpy(float)
        logit = sub["logit_prob"].to_numpy(float)
        lat = sub["latency_s"].to_numpy(float)
        lat = lat[np.isfinite(lat)]
        tok = sub["input_tokens"].to_numpy(float)
        tok = tok[np.isfinite(tok)]

        lines += [f"## {pos_key}(n={len(sub)})", "",
                 f"- 遅延 p50 {np.percentile(lat, 50):.3f} / p90 "
                 f"{np.percentile(lat, 90):.3f} / p99 "
                 f"{np.percentile(lat, 99):.3f} 秒(n={lat.size})",
                 f"- 入力トークン平均 {tok.mean():.1f}(n={tok.size})", ""]

        for name, prob in (("Jev", jev), ("logistic", logit)):
            ok = np.isfinite(prob) & np.isfinite(y)
            p_ok, y_ok = prob[ok], y[ok]
            pos_side = p_ok[y_ok == 1]
            neg_side = p_ok[y_ok == 0]
            sep = (js.mats.separation_prob(pos_side, neg_side)
                  if pos_side.size and neg_side.size else float("nan"))
            sep_se = js._bootstrap_sep_se(pos_side, neg_side)
            thr_rows = _threshold_rows(p_ok, y_ok)
            goodness = calib.calibration_goodness(p_ok, y_ok)

            lines += [f"### {pos_key}: {name}", "",
                     f"- 順位分離: {sep:.4f}(ブートストラップ SE {sep_se:.4f})",
                     "", "#### 較正 0.01 刻み", "",
                     _fmt_bin_table(_bin_table(p_ok, y_ok, 0.01)), "",
                     "#### 較正 0.05 刻み", "",
                     _fmt_bin_table(_bin_table(p_ok, y_ok, 0.05)), "",
                     "#### 閾値ごとの適合率", "",
                     "| 閾値 | 適合率 | 件数 |", "|---|---|---|"]
            for r in thr_rows:
                prec_s = f"{r['適合率']:.4f}" if r["適合率"] == r["適合率"] else "NaN"
                lines.append(f"| {r['閾値']} | {prec_s} | {r['件数']} |")
            lines += ["",
                     f"- 較正の良さ(§7.5.1、値が小さいほど良い): {goodness['値']}",
                     f"- 外した帯(件数20未満): {_fmt_excluded(goodness)}", ""]

        ok_both = np.isfinite(jev) & np.isfinite(logit)
        jj, ll, y_both = jev[ok_both], logit[ok_both], y[ok_both]
        agree = float(((jj >= 0.5) == (ll >= 0.5)).mean()) if jj.size else float("nan")
        rank_corr = (pd.Series(jj).corr(pd.Series(ll), method="spearman")
                    if jj.size > 1 else float("nan"))
        jev_goodness_b = calib.calibration_goodness(jj, y_both)
        logit_goodness_b = calib.calibration_goodness(ll, y_both)
        choice = calib.choose_better(jev_goodness_b, logit_goodness_b)

        lines += [f"### {pos_key}: Jev と logistic の一致・相関(n={jj.size})", "",
                 f"- 一致(閾値 0.5): {agree:.4f}",
                 f"- 順位相関(Spearman): {rank_corr:.4f}",
                 f"- 較正の良さ(§7.5.1、共通母集団で再計算)Jev: {jev_goodness_b['値']} / "
                 f"logistic: {logit_goodness_b['値']}",
                 f"- choose_better の答え(このpositionの較正の良さから): {choice}", ""]

    md = "\n".join(lines)
    check_no_banned(md, "stage2_tables.md")
    return md


# ===========================================================================
# main
# ===========================================================================
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="段2: 後半5,000件に Jev V1 + logistic")
    ap.add_argument("--stage", choices=("run", "tables"), default="run")
    ap.add_argument("--rate-per-sec", type=float, default=RATE_PER_SEC)
    a = ap.parse_args(argv)

    if a.stage == "tables":
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        md = build_stage2_tables()
        (OUT_DIR / "tables.md").write_text(md)
        print(f"表を書いた -> {OUT_DIR / 'tables.md'}", flush=True)
        return 0

    t0 = time.time()
    sb = js.StateBuilder()
    prints = load_selection()
    print(f"選定 {len(prints)} 件を読んだ", flush=True)

    mat = pd.read_csv(js.DEFAULT_MATERIALS, low_memory=False)
    cont_df = pd.read_csv(js.DEFAULT_CONTINUE_ROWS, usecols=["print_id", "label_60"],
                          low_memory=False)
    sel_ids = {p["print_id"] for p in prints}
    df_back = mat[(mat["half"] == "後半") & (mat["print_id"].isin(sel_ids))].reset_index(drop=True)
    df_back = df_back.merge(cont_df, on="print_id", how="left")
    if len(df_back) != len(sel_ids):
        raise SystemExit(f"[止め] 選定 {len(sel_ids)} 件のうち材料の表に無いものがある "
                         f"(見つかった {len(df_back)} 件)")
    label_of = dict(zip(df_back["print_id"], df_back["label_60"]))

    print("logistic の予測を計算中(前半で固定した係数・経験分布を読むだけ)", flush=True)
    logit_prob_of = compute_logit_probs(sb, df_back)
    print(f"logistic 完了 {time.time() - t0:.0f}s", flush=True)

    note = run_stage2(sb, prints, logit_prob_of, label_of, rate_per_sec=a.rate_per_sec)
    note["経過秒"] = round(time.time() - t0, 1)
    (OUT_DIR / "run_notes.json").write_text(json.dumps(note, ensure_ascii=False, indent=2))
    print(f"Jev 呼び出し {note['呼び出し数']} 件、エラー {note['エラー数']} 件、"
         f"再開で読み飛ばした {note['再開で読み飛ばした件数']} 件、"
         f"{note['経過秒']}秒 -> {OUT_DIR}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
