"""Reproduction of survey candidate 15 `Mendl-Labs/BacktestingCore` for the item 3 battery.

Why a reproduction: the tool could not be installed (item 0, tests/bt/battery/item_0/opponents/RUNNABILITY.tsv
candidate 15: its workspace dependency ultra-logger needs credentials), so, per 委任文 §3「動かせない候補の検討と
再現」, its mechanisms that this battery's scenes measure are rewritten minimally, line for line, from the primary
source (material (b), read only, never executed):
    https://github.com/Mendl-Labs/BacktestingCore  commit f8d81ee0b4b65f6fbbf205d011ad2e815054fbc7
    (git clone --depth 1 on 2026-09-25, log scratchpad/bt/i3_r1_scenekeeper/read/i3_r1_scenekeeper_read.log)
Every function below carries the file and lines it transcribes (SRC = the URL prefix above + /blob/<commit>/).
Nothing is added and nothing is weakened; a value the source leaves to the caller is taken from the request
and the choice is stated in the observation's note.  Requests whose mechanism the source does not have, or has
only as a stub, raise NotExpressible with the lines that show it (NO).
"""
from __future__ import annotations

import datetime as D
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _i3_base import Base, NotExpressible  # noqa: E402

NS = 1_000_000_000
DAY = 86400 * NS
SRC = "https://github.com/Mendl-Labs/BacktestingCore/blob/f8d81ee0b4b65f6fbbf205d011ad2e815054fbc7/"


# --- walkforward/src/window.rs L14-L48 (generate_windows) -----------------------------------------------
def generate_windows(start: D.date, end: D.date, train_size: int, test_size: int, step_size: int,
                     embargo_days: int, anchored: bool):
    windows = []
    train_start = start
    embargo = D.timedelta(days=embargo_days)
    while True:
        if anchored:  # L28-L31
            train_end = start + D.timedelta(days=train_size) + D.timedelta(days=len(windows) * step_size)
        else:  # L32-L33
            train_end = train_start + D.timedelta(days=train_size)
        test_start = train_end + embargo  # L35
        test_end = test_start + D.timedelta(days=test_size)  # L36
        if test_end > end:  # L37-L39
            break
        windows.append((start if anchored else train_start, train_end, test_start, test_end))  # L40-L45
        train_start = train_start + D.timedelta(days=step_size)  # L46
    return windows


# --- walkforward/src/runner.rs L280-L298 (extract_data / in_range): the UTC date of a row, half-open [start, end)
def extract_rows(rows_ns, start: D.date, end: D.date):
    return [t for t in rows_ns if start <= D.datetime.fromtimestamp(t / NS, tz=D.timezone.utc).date() < end]


# --- walkforward/src/lib.rs L559-L610 (create_cpcv_folds) ------------------------------------------------
def create_cpcv_folds(data_length: int, n_folds: int, purge_gap_days: int):
    fold_size = data_length // n_folds  # L565
    purge_samples = min(purge_gap_days, fold_size // 4)  # L566
    folds = []
    for fold_id in range(n_folds):
        fold_start = fold_id * fold_size  # L571
        fold_end = data_length if fold_id == n_folds - 1 else (fold_id + 1) * fold_size  # L572-L576
        purge_start = fold_start - purge_samples if fold_start >= purge_samples else 0  # L579-L583
        purge_end = min(fold_end + purge_samples, data_length)  # L584
        test = list(range(fold_start, fold_end))  # L586
        purged = list(range(purge_start, fold_start)) + list(range(fold_end, purge_end))  # L587-L589
        train = [i for i in range(data_length) if i not in test and i not in purged]  # L592-L594
        folds.append({"train": train, "test": test, "purged": purged})
    return folds


# --- walkforward/src/lib.rs L532-L557 (generate_combinations): lexicographic k-subsets ---------------------
def generate_combinations(n: int, k: int):
    out, comb = [], [0] * k

    def rec(start, index):
        if index == k:
            out.append(list(comb))
            return
        for i in range(start, n - k + index + 1):  # L553: start..=(n - k + index)
            comb[index] = i
            rec(i + 1, index + 1)

    rec(0, 0)
    return out


# --- walkforward/src/lib.rs L206-L216 (CPCVConfig::total_combinations) -------------------------------------
def total_combinations(n: int, k: int) -> int:
    if k > n:
        return 0
    r = 1
    for i in range(k):
        r = r * (n - i) // (i + 1)
    return r


# --- walkforward/src/lib.rs L629-L645 (train indices of one combination) -----------------------------------
def combination_train(folds, test_fold_ids, data_length):
    test = {i for f in test_fold_ids for i in folds[f]["test"]}
    purged = {i for f in test_fold_ids for i in folds[f]["purged"]}
    return [i for i in range(data_length) if i not in test and i not in purged], sorted(test)


# --- walkforward/src/lib.rs L715-L760 (calculate_pbo, calculate_median) -------------------------------------
def calculate_median(values):
    if not values:
        return 0.0
    s = sorted(values)
    mid = len(s) // 2
    return (s[mid - 1] + s[mid]) / 2.0 if len(s) % 2 == 0 else s[mid]


def calculate_pbo(in_sample, out_of_sample):
    if len(in_sample) != len(out_of_sample) or not in_sample:
        return 0.5  # L718-L720
    n = len(in_sample)
    is_ranked = sorted(enumerate(in_sample), key=lambda x: -x[1])  # L725-L728 (sort descending, stable)
    median_rank = n // 2  # L730
    overfit = 0
    for rank, (combo_idx, _v) in enumerate(is_ranked):  # L733-L744
        if rank < median_rank:
            if out_of_sample[combo_idx] < calculate_median(out_of_sample):
                overfit += 1
    return overfit / max(median_rank, 1)  # L747


# --- metrics/src/significance.rs L237-L252 (expected_max_normal), L255-L269 (erfc), L274-L333 (probit) -------
_A = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02,
      -3.066479806614716e+01, 2.506628277459239e+00]
_B = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01,
      -1.328068155288572e+01]
_C = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00,
      4.374664141464968e+00, 2.938163982698783e+00]
_D = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]


def probit(p):
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    if abs(p - 0.5) < 1e-15:
        return 0.0
    p_low = 0.02425
    p_high = 1.0 - p_low
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / \
            ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0)
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((_A[0] * r + _A[1]) * r + _A[2]) * r + _A[3]) * r + _A[4]) * r + _A[5]) * q / \
            (((((_B[0] * r + _B[1]) * r + _B[2]) * r + _B[3]) * r + _B[4]) * r + 1.0)
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / \
        ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0)


def expected_max_normal(n):
    if n <= 1:
        return 0.0
    z = probit(1.0 - 1.0 / n)
    em = 0.5772156649
    ln_n = math.log(n)
    return z + em / (z * math.sqrt(2.0 * ln_n)) if ln_n > 0.0 and abs(z) > 1e-12 else z


def erfc(x):
    sign = -1.0 if x < 0.0 else 1.0
    a = abs(x)
    t = 1.0 / (1.0 + 0.3275911 * a)
    poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))))
    result = poly * math.exp(-a * a)
    return 2.0 - result if sign < 0.0 else result


# --- metrics/src/significance.rs L135-L205 (deflated_sharpe_ratio from a stated Sharpe) ----------------------
def dsr_significance(observed_sharpe, n_trials, n_days, sharpe_std, periods_per_year):
    if not (math.isfinite(periods_per_year) and periods_per_year > 0.0):
        periods_per_year = 365.0  # L142-L146
    if n_days == 0 or sharpe_std <= 0.0:
        return 0.5  # L161-L163
    e_max = expected_max_normal(n_trials)  # L166
    expected_max_sharpe = e_max * sharpe_std  # L168
    daily_obs = observed_sharpe / math.sqrt(periods_per_year)  # L171
    daily_emax = expected_max_sharpe / math.sqrt(periods_per_year)  # L172
    se = math.sqrt(1.0 / n_days)  # L174
    t = (daily_obs - daily_emax) / max(se, 1e-12)  # L175
    d = 0.5 * erfc(-t / math.sqrt(2.0))  # L178
    if abs(-t / math.sqrt(2.0)) >= 27.0:  # L194-L202
        return min(max(d, 1e-15), 1.0 - 1e-15)
    return d


# --- metrics/src/performance.rs L226-L266 (deflated_sharpe_ratio from returns), L306-L355 (mean, std ddof 0) --
def _normal_cdf_perf(x):  # performance.rs L260-L266
    P = 0.3275911
    A = [0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429]
    t = 1.0 / (1.0 + P * abs(x))
    poly = t * (A[0] + t * (A[1] + t * (A[2] + t * (A[3] + t * A[4]))))
    erf_approx = 1.0 - poly * math.exp(-x * x / 2.0)
    return 0.5 * (1.0 + (1.0 if x >= 0.0 else -1.0) * erf_approx)


def dsr_performance(num_trials, returns):
    n = len(returns)
    if n < 4 or num_trials == 0:
        return None  # L228-L230
    mean = sum(returns) / n  # L234 (simd_mean L306-L311)
    std = math.sqrt(sum((x - mean) ** 2 for x in returns) / n)  # L235 (simd_std_dev: sum_sq / n, L325 / L354)
    if std < 1e-10:
        return None
    sr = mean / std  # L239
    skew = sum(((x - mean) / std) ** 3 for x in returns) / n  # L241
    exk = sum(((x - mean) / std) ** 4 for x in returns) / n - 3.0  # L242
    g = 0.5772156649015329
    sr_star = (1.0 - g + g * math.log(num_trials)) / math.sqrt(n - 1.0)  # L247
    se_sq = (1.0 - skew * sr + ((exk + 2.0) / 4.0) * sr * sr) / (n - 1.0)  # L250
    if se_sq <= 0.0:
        return None
    return _normal_cdf_perf((sr - sr_star) / math.sqrt(se_sq))  # L255-L256


# --- metrics/src/risk.rs L12-L34 (max_drawdown): fraction of the running peak --------------------------------
def max_drawdown(equity):
    if not equity:
        return None
    mdd, peak = 0.0, equity[0]
    for v in equity:
        if v > peak:
            peak = v
        if peak <= 0.0:
            continue
        mdd = max(mdd, min(max((peak - v) / peak, 0.0), 1.0))
    return mdd


class BacktestingCore(Base):
    name = "opp_repro_15"
    SEARCH_AS = "read_15"
    WHAT = "候補 15 の再現(一次資料 " + SRC + " を読むだけで書き写した)。"
    NO = {
        "calendar_split": "日付で Train / Val / OOS に切る口が無い。OOS の欄(backtest/src/engine.rs L52-L78)は walk-forward の窓の評価の集計",
        "walk_forward_eval": "窓ごとの評価 run_backtest_with_params(walkforward/src/runner.rs L357-L376)は「Placeholder」の定数の指標を返し、"
                             "最適化の適合度(L336-L341)はデータを見ない。道具台帳 §2.4 の形 4(名乗るだけで実装に無い)なので再現しない",
        "cpcv_paths": "CPCV は組合せごとに別々に評価するだけ(walkforward/src/lib.rs L612-L700)で、全群を覆う経路を組み立てる口が無い",
        "block_bootstrap": "再抽出は 1 点ずつの復元抽出(backtest/src/statistical_significance.rs L199-L206)で、ブロックの口が無い",
        "mde": "MDE の関数が無い(当たりの python_validation.rs L86 は窓ごとの検出力の説明文)",
        "verdict": "判定(backtest/src/verdict.rs L27-L30 Promising / Underperformed / Inconclusive)は Sharpe の閾値(L125)と観測数の下限"
                   "(L65-L72)で決まり、欲しい効果と MDE を入力に取らない(L40-L110 の入力の欄)",
        "iter_ledger": "試行の数は 1 回の実行の中の遺伝的最適化の評価の数(backtest/src/engine.rs L280-L281 ga_trial_count)で、実行をまたいで累積する台帳が無い",
        "iter_dsr": "同上",
        "sealed_read": "封印区間の口が無い(grep の当たり 0)",
        "data_read": "封印区間の口が無い(grep の当たり 0)",
        "run": "実行の記録(git の SHA・データの sha256・種・版)の口が無い。run_id|sha256|git の当たりは monte_carlo.rs の種の混ぜ(L305-L306)だけ",
        "run_ids": "同上",
        "auto_repro": "config/src/lib.rs L1616-L1623 は乱数の種の固定(再現のための設定)で、2 回回して比べる口ではない",
        "trade_metrics": "分位の当たりは tail_ratio(metrics/src/advanced.rs L81-L106 の 95 / 5 分位の比)だけで、1 件ごとの bp の分布・負の割合・露出あたりの口が無い",
        "markout": "adverse_selection_rate は往復のうち損の割合(backtest/src/collectors.rs L582)で、時間窓ごとの markout ではない",
        "cost_breakdown": "費用の欄は total_commission / total_slippage / total_market_impact(walkforward/src/runner.rs L371-L374 の欄)で、maker / taker の手数料・"
                          "スプレッド・資金調達の内訳の口が無い",
        "exit_reasons": "exit_reason は取引ごとの欄(backtest/src/types.rs L143)で、理由ごとに集計する口が無い",
        "dashboard": "画面は実行ごとの静的な HTML の報告(backtest/src/html_export.rs)で、実行の一覧とタブを持たず、Plotly を CDN から読む(L208)",
        "wiring_test": "配線の試験の口が無い(画面は静的な HTML の書き出し)",
    }

    def op_walk_forward(self, inp):
        if inp.get("mode") != "rolling":
            raise NotExpressible("walk_forward: mode は rolling / anchored だけ")
        rows = inp["rows"]
        start = D.datetime.fromtimestamp(rows[0] / NS, tz=D.timezone.utc).date()
        end = D.datetime.fromtimestamp(rows[-1] / NS, tz=D.timezone.utc).date() + D.timedelta(days=1)
        ws = generate_windows(start, end, inp["train_days"], inp["test_days"], inp["step_days"], 0, False)
        return {"folds": [{"train": extract_rows(rows, a, b), "test": extract_rows(rows, c, d)} for a, b, c, d in ws],
                "note": f"期間 [{start}, {end})(行の最初の日から最後の日の翌日)を渡した"}

    def _fold_count(self, n, test_rows):
        k = len(test_rows)
        if k == 0 or n % k or test_rows[0] % k or test_rows != list(range(test_rows[0], test_rows[0] + k)):
            raise NotExpressible("purged_split: 評価の行が等分の折り目(lib.rs L565-L576)の 1 つに重ならない")
        return n // k, test_rows[0] // k

    def op_purged_split(self, inp):
        n = len(inp["rows"])
        n_folds, fid = self._fold_count(n, inp["test_rows"])
        folds = create_cpcv_folds(n, n_folds, inp["embargo_rows"])
        return {"train_idx": folds[fid]["train"],
                "note": f"評価の行を {n_folds} 等分の {fid} 番目の折り目として渡し、purge_gap_days = embargo の行数 {inp['embargo_rows']}"
                        "(道具の唯一の間隔の引数で、lib.rs L187-L188 の説明は「embargo period」)。ラベルの終わりを渡す口は無い"}

    def op_cpcv(self, inp):
        n = len(inp["rows"])
        folds = create_cpcv_folds(n, inp["n_groups"], inp["embargo_rows"])
        combos = generate_combinations(inp["n_groups"], inp["n_test_groups"])
        want = sorted(inp["want_train_for"])
        if want not in combos:
            raise NotExpressible("cpcv: 求めた評価の群の組が組合せに無い")
        train, _test = combination_train(folds, want, n)
        return {"n_splits": total_combinations(inp["n_groups"], inp["n_test_groups"]), "train_idx": train,
                "note": "経路の数を出す口は無い(lib.rs L612-L700 は組合せを別々に評価する)。purge_gap_days = embargo の行数"}

    def op_pbo(self, inp):
        M, S = inp["matrix"], inp["n_blocks"]
        if inp.get("metric") != "mean":
            raise NotExpressible("pbo: 性能の物差しは利用者の評価の関数が決める。この再現が書いたのは平均だけ")
        n = len(M)
        folds = create_cpcv_folds(n, S, 0)
        is_s, oos_s = [], []
        for test_ids in generate_combinations(S, S // 2):  # lib.rs L623-L650: every combination, test = the combination
            train, test = combination_train(folds, test_ids, n)

            def perf(rows, j):
                return sum(M[r][j] for r in rows) / len(rows)

            # eval_fn (user code, lib.rs L646-L650): choose the strategy best on train, report its train and test score
            best = max(range(len(M[0])), key=lambda j: (perf(train, j), -j))
            is_s.append(perf(train, best))
            oos_s.append(perf(test, best))
        return {"pbo": calculate_pbo(is_s, oos_s),
                "note": "評価の関数(利用者の書く部分)= 学習の側の平均が最大の戦略を選び、学習と評価の平均を返す。PBO は道具の式(lib.rs L715-L747)"}

    def op_dsr(self, inp):
        return {"dsr": dsr_significance(inp["sr"], inp["n_trials"], inp["T"], math.sqrt(inp["var_trials"]), 1.0),
                "note": "significance.rs L135 の deflated_sharpe_ratio(observed_sharpe = SR、n_trials = N、n_days = T、sharpe_std = √V、"
                        "periods_per_year = 1)。歪度と尖度を渡す口は無い"}

    def op_dsr_returns(self, inp):
        v = dsr_performance(inp["n_trials"], inp["returns"])
        if v is None:
            raise NotExpressible("dsr_returns: 道具が値を返さなかった(None)")
        return {"dsr": v, "note": "performance.rs L226 の deflated_sharpe_ratio(エンジンが使う方 = engine.rs L280-L281)。V を渡す口は無い(SR* は L247 の式)"}

    def op_drawdown(self, inp):
        return {"max_dd_pct": max_drawdown(inp["equity"]) * 100.0, "note": "risk.rs L12 は割合を返す。% にした。額の口は無い"}

    def op_fill_metrics(self, inp):
        filled = {f["order_id"] for f in inp["fills"]}
        placed = len(inp["orders"])
        n_filled = sum(1 for o in inp["orders"] if o["id"] in filled)
        return {"fill_rate": n_filled / placed if placed else 0.0,  # collectors.rs L419-L423
                "note": "取り逃しの数は結果に残さない(collectors.rs L519-L522「logged but not stored」)"}


TARGET = BacktestingCore()
