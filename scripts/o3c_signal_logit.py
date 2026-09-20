#!/usr/bin/env python3
"""V4 の比較相手 = 前半で固定した logistic(設計 §7.4)。

決定表(`SIGNAL_MATERIALS_DESIGN_2026-09-20.md` §7.1)で「残す」「逆で与える」
「向きを criteria に」とした材料を、前半の五分位の順位(0.1/0.3/0.5/0.7/0.9、
欠測 0.5)にしたものを入力に、ニュートン法(L2 1e-3、sklearn は使わない)で
前半全件に当てはめる。係数は `config/o3c_signal_logit_first.yaml` /
`_chain.yaml` に書く。前半 5-fold out-of-fold の順位分離・的中(0.5)・
閾値ごとの適合率は `data/jev/v4/logit_firsthalf.md` に書く(数値はリポジトリに
入れない、委任文の指定)。

委任文: `docs/DATA/delegations/20260920_o3c_signal_v4_prompt.md` 段1【作るもの】3
設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md` §7.4

**探索段なので判定語を 1 つも書かない。`paper_logs/` は開かない。**
"""
from __future__ import annotations

import importlib.util
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

_HERE = Path(__file__).resolve().parent
REPO_ROOT = _HERE.parent
NAN = float("nan")

_spec_js = importlib.util.spec_from_file_location(
    "o3c_jev_state", _HERE / "o3c_jev_state.py")
js = importlib.util.module_from_spec(_spec_js)
assert _spec_js.loader is not None
_spec_js.loader.exec_module(js)

price_at_or_before = js.price_at_or_before
n2_position = js.n2_position
check_no_banned = js.check_no_banned

OUT_DIR = REPO_ROOT / "data" / "jev" / "v4"
CONFIG_FIRST = REPO_ROOT / "config" / "o3c_signal_logit_first.yaml"
CONFIG_CHAIN = REPO_ROOT / "config" / "o3c_signal_logit_chain.yaml"

L2_LAMBDA = 1e-3
N_FOLDS = 5
CV_SEED = 20260920
MAX_ITER = 100
TOL = 1e-8

# ---------------------------------------------------------------------------
# 決定表(設計 §7.1)の「残す/逆で与える/向きを criteria に」の材料。
# **設計に無い判断**(§4・報告参照):
#   - N1 は cand_C3 と同一の数値(§7.2「C3 の『距離0』を言葉にしたもの」)なので、
#     logistic の入力には重複して足さない(C3 が既にある)。N2 だけ足す。
#   - 「先の建玉」(材料 8 と 5' を 1 つの文にまとめたもの)は、logistic では
#     代表値として `cand_8` を使う(5' は欠測 70〜92% のため単独では扱いにくい、
#     §5.2 参照)。
# ---------------------------------------------------------------------------
FEATURES_FIRST = ["cand_14", "cand_8", "cand_C3", "cand_C4", "cand_11",
                  "cand_A6", "cand_R1", "cand_9", "cand_15", "cand_N2"]
FEATURES_CHAIN = ["cand_F5", "cand_1", "cand_F3", "cand_14", "cand_A6", "cand_C4",
                  "cand_15", "cand_11", "cand_C3", "cand_8", "cand_2"]


# ===========================================================================
# 1. 五分位の順位(0.1/0.3/0.5/0.7/0.9、欠測 0.5)
# ===========================================================================
def quintile_rank(values: np.ndarray) -> tuple[np.ndarray, list]:
    """帯の中心を順位の値にする(5 段、`o3c_jev_state.py` の帯の切り方と同じ
    q=0.2,0.4,0.6,0.8)。欠測は 0.5。"""
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return np.full(values.shape, 0.5), [NAN, NAN, NAN, NAN]
    cuts = [float(np.quantile(finite, q)) for q in (0.2, 0.4, 0.6, 0.8)]
    band = np.searchsorted(cuts, values, side="right")
    rank = (band.astype(float) + 0.5) / 5.0
    rank[~np.isfinite(values)] = 0.5
    return rank, cuts


def build_matrix(df: pd.DataFrame, features: list) -> tuple[np.ndarray, dict]:
    """切片列(1 列目、全て 1)+ 各材料の五分位の順位。切り値はこの df(=渡された
    集団)自身の分布から計算する(呼び出し側が前半だけに絞って渡す)。"""
    cols = []
    cuts_by_feat: dict = {}
    for f in features:
        v = pd.to_numeric(df[f], errors="coerce").to_numpy(float)
        r, cuts = quintile_rank(v)
        cols.append(r)
        cuts_by_feat[f] = cuts
    X = np.column_stack([np.ones(len(df))] + cols)
    return X, cuts_by_feat


# ===========================================================================
# 2. ニュートン法(L2 正則化、切片は正則化しない。sklearn は使わない)
# ===========================================================================
def newton_logistic(X: np.ndarray, y: np.ndarray, l2: float = L2_LAMBDA,
                    max_iter: int = MAX_ITER, tol: float = TOL) -> np.ndarray:
    n, p = X.shape
    beta = np.zeros(p)
    reg = np.full(p, l2)
    reg[0] = 0.0  # 切片は正則化しない
    for _ in range(max_iter):
        z = np.clip(X @ beta, -30, 30)
        pr = 1.0 / (1.0 + np.exp(-z))
        g = X.T @ (pr - y) + reg * beta
        w = np.maximum(pr * (1 - pr), 1e-9)
        H = (X * w[:, None]).T @ X + np.diag(reg)
        try:
            delta = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            delta = np.linalg.lstsq(H, g, rcond=None)[0]
        beta = beta - delta
        if np.max(np.abs(delta)) < tol:
            break
    return beta


def predict(X: np.ndarray, beta: np.ndarray) -> np.ndarray:
    z = np.clip(X @ beta, -30, 30)
    return 1.0 / (1.0 + np.exp(-z))


def separation_auc(prob_pos: np.ndarray, prob_neg: np.ndarray) -> float:
    """`o3c_signal_materials.py: separation_prob` と同じ U 統計量(y=1 側の
    確率の方が y=0 側より大きい確率)。"""
    return js.mats.separation_prob(prob_pos, prob_neg)


def kfold_indices(n: int, k: int, seed: int) -> list:
    rng = np.random.default_rng(seed)
    idx = np.arange(n)
    rng.shuffle(idx)
    return np.array_split(idx, k)


def precision_at(prob: np.ndarray, y: np.ndarray, thr: float) -> tuple[float, int]:
    mask = prob >= thr
    n = int(mask.sum())
    if n == 0:
        return NAN, 0
    return float(y[mask].mean()), n


# ===========================================================================
# 3. 前半だけに絞ってから当てはめる(後半の値を変えても同じになることの検査に使う)
# ===========================================================================
def fit_beta_front_half(df_all: pd.DataFrame, features: list,
                        label_col: str = "label_60") -> np.ndarray:
    """`half == '前半'` の行だけで `newton_logistic` を当てはめる。"""
    df_fh = df_all[df_all["half"] == "前半"].reset_index(drop=True)
    X, _cuts = build_matrix(df_fh, features)
    y = pd.to_numeric(df_fh[label_col], errors="coerce").to_numpy(float)
    ok = np.isfinite(y)
    return newton_logistic(X[ok], y[ok])


# ===========================================================================
# 4. 場面(1 件目 / 連鎖の中)ごとに当てはめて OOF を測る
# ===========================================================================
def run_scene(df_fh: pd.DataFrame, features: list, scene: str,
              label_col: str = "label_60") -> dict:
    X, cuts_by_feat = build_matrix(df_fh, features)
    y_all = pd.to_numeric(df_fh[label_col], errors="coerce").to_numpy(float)
    ok = np.isfinite(y_all)
    pid_all = df_fh["print_id"].to_numpy(object)
    pid = pid_all[ok]
    X, y = X[ok], y_all[ok].astype(int)
    n = X.shape[0]

    beta_full = newton_logistic(X, y.astype(float))

    folds = kfold_indices(n, N_FOLDS, CV_SEED)
    oof_prob = np.full(n, NAN)
    for i in range(N_FOLDS):
        test_idx = folds[i]
        train_idx = np.concatenate([folds[j] for j in range(N_FOLDS) if j != i])
        beta_f = newton_logistic(X[train_idx], y[train_idx].astype(float))
        oof_prob[test_idx] = predict(X[test_idx], beta_f)

    sep = separation_auc(oof_prob[y == 1], oof_prob[y == 0])
    base_rate = float(y.mean())
    hit_05 = float(((oof_prob >= 0.5).astype(int) == y).mean())
    thr_rows = [{"閾値": thr, "適合率": (lambda pc: pc[0])(precision_at(oof_prob, y, thr)),
                "件数": precision_at(oof_prob, y, thr)[1]}
               for thr in (0.6, 0.7, 0.8)]

    yaml_doc = {
        "_由来": (f"scripts/o3c_signal_logit.py の newton_logistic()。前半全件"
                f"({n} 件、{scene})で当てはめ(ニュートン法、L2 {L2_LAMBDA}、"
                "sklearn 不使用)。入力は前半の五分位の順位(0.1/0.3/0.5/0.7/0.9、"
                "欠測 0.5)。切り値・係数の順序は「材料」の並びと対応。"),
        "場面": scene,
        "件数": n,
        "材料": features,
        "五分位の切り値": cuts_by_feat,
        "係数": {"切片": float(beta_full[0]),
              **{f: float(b) for f, b in zip(features, beta_full[1:])}},
    }
    report = {
        "場面": scene, "件数": n, "基準率(label_60、前半)": base_rate,
        "5fold_out_of_fold_順位分離": sep,
        "的中(閾値0.5)": hit_05,
        "閾値ごとの適合率": thr_rows,
    }
    oof_by_pid = {str(p): float(v) for p, v in zip(pid, oof_prob)}
    return {"yaml": yaml_doc, "report": report, "oof_by_pid": oof_by_pid}


# ===========================================================================
# 5. N2(1 件目だけ。`o3c_jev_state.py` の n2_position を使う)
# ===========================================================================
def add_n2_column(sb, df_first: pd.DataFrame) -> pd.DataFrame:
    df_first = df_first.reset_index(drop=True).copy()
    n2 = np.full(len(df_first), NAN)
    for i, r in df_first.iterrows():
        day = str(r["day"])
        ts = int(r["ts_ms"])
        side = str(r["side"])
        times, prices = sb._trades_for_day(day)
        p_pre, _ = price_at_or_before(times, prices, ts - 1)
        n2[i] = n2_position(times, prices, ts, side, p_pre)
    df_first["cand_N2"] = n2
    return df_first


# ===========================================================================
# main
# ===========================================================================
def _fmt_report_md(res_first: dict, res_chain: dict) -> str:
    lines = ["# logistic(前半、out-of-fold)— 数値は data/jev/ にだけ置く", "",
            "委任文: `docs/DATA/delegations/20260920_o3c_signal_v4_prompt.md` 段1",
            "設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md` §7.4",
            ""]
    for res in (res_first, res_chain):
        r = res["report"]
        lines += [f"## {r['場面']}", "",
                 f"- 件数: {r['件数']}",
                 f"- 基準率(label_60、前半): {r['基準率(label_60、前半)']:.4f}",
                 f"- 5-fold out-of-fold 順位分離: {r['5fold_out_of_fold_順位分離']:.4f}",
                 f"- 的中(閾値0.5): {r['的中(閾値0.5)']:.4f}", "",
                 "| 閾値 | 適合率 | 件数 |", "|---|---|---|"]
        for row in r["閾値ごとの適合率"]:
            prec = row["適合率"]
            prec_s = f"{prec:.4f}" if prec == prec else "NaN"
            lines.append(f"| {row['閾値']} | {prec_s} | {row['件数']} |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    t0 = time.time()
    sb = js.StateBuilder()

    mat_df = pd.read_csv(js.DEFAULT_MATERIALS, low_memory=False)
    cont_df = pd.read_csv(js.DEFAULT_CONTINUE_ROWS, usecols=["print_id", "label_60"],
                          low_memory=False)
    df = mat_df.merge(cont_df, on="print_id", how="left")
    df_fh = df[df["half"] == "前半"].reset_index(drop=True)
    cand1 = pd.to_numeric(df_fh["cand_1"], errors="coerce")
    df_first = df_fh[cand1 == 0].reset_index(drop=True)
    df_chain = df_fh[cand1 > 0].reset_index(drop=True)
    print(f"前半 1件目 {len(df_first)} 件・連鎖の中 {len(df_chain)} 件", flush=True)

    df_first = add_n2_column(sb, df_first)
    print(f"N2 計算 {time.time() - t0:.0f}s", flush=True)

    res_first = run_scene(df_first, FEATURES_FIRST, "1件目")
    res_chain = run_scene(df_chain, FEATURES_CHAIN, "連鎖の中")

    CONFIG_FIRST.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FIRST.write_text(yaml.safe_dump(res_first["yaml"], allow_unicode=True,
                                           sort_keys=False))
    CONFIG_CHAIN.write_text(yaml.safe_dump(res_chain["yaml"], allow_unicode=True,
                                           sort_keys=False))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    md = _fmt_report_md(res_first, res_chain)
    (OUT_DIR / "logit_firsthalf.md").write_text(md)

    for p in (CONFIG_FIRST, CONFIG_CHAIN):
        check_no_banned(p.read_text(), p.name)

    # print_id -> OOF 予測(数値なので data/jev/ にだけ置く。V4 の下見の表が読む)
    import json
    oof = {"1件目": res_first["oof_by_pid"], "連鎖の中": res_chain["oof_by_pid"]}
    (OUT_DIR / "logit_oof.json").write_text(json.dumps(oof, ensure_ascii=False))

    print(f"完了 {time.time() - t0:.0f}s -> {CONFIG_FIRST}, {CONFIG_CHAIN}, "
         f"{OUT_DIR / 'logit_firsthalf.md'}, {OUT_DIR / 'logit_oof.json'}",
         flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
