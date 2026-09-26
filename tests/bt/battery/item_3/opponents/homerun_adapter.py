"""Survey candidate 91 `braedonsaunders/homerun` for the item 3 battery.

Install: the item 2 scene-keeper's venv item_2/c91 (a .pth to the clone's backend/;
record venvs/item_2/logs/i2_r1_scenekeeper_install_91.log).  Only the pure functions of
backend/services/backtest/ are called (walk_forward.walk_forward_split,
metrics.block_bootstrap_ci / deflated_sharpe_from_moments / max_drawdown); the job
runner, CPCV runner and the web UI need the tool's database and front-end build and
are not started (see NO).
"""
from __future__ import annotations

import datetime as D
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _i3_base import Base, NotExpressible  # noqa: E402

from services.backtest.metrics import block_bootstrap_ci, deflated_sharpe_from_moments, deflated_sharpe_ratio, max_drawdown  # noqa: E402
from services.backtest.walk_forward import WalkForwardConfig, walk_forward_split  # noqa: E402

NS = 1_000_000_000
DAY = 86400 * NS


def _dt(t_ns: int) -> D.datetime:
    return D.datetime.fromtimestamp(t_ns / NS, tz=D.timezone.utc)


def _ns(dt: D.datetime) -> int:
    return round(dt.timestamp() * NS)


class Homerun(Base):
    name = "opp_homerun"
    WHAT = "homerun の backend/services/backtest の関数(予測市場の bot の検証の部品)。"
    NO = {
        "calendar_split": "日付で Train / Val / OOS に切る口が無い。walk_forward_split(walk_forward.py 74 行)は期間を窓の数で等分するだけ",
        "walk_forward_eval": "学習区間で選び評価区間で測る窓ごとの評価は run_walk_forward(walk_forward.py 267 行)で、道具自身のバックテスト(DB の上の"
                             "unified_runner)を回す形。窓の幅は学習 = 評価の等幅だけで、この要求の学習 5 日・評価 2 日を渡せない",
        "purged_split": "embargo は窓の間の秒数の空き(walk_forward.py 32 行・cpcv.py 118-138 行)で、ラベルの終わりで学習の行を除く purge の口が無い",
        "cpcv": "run_cpcv(cpcv.py 203 行)は各組合せで道具自身のバックテストを回す関数で、学習の行の集合も経路の組み立ても返さない(時間の窓だけ、"
                "ラベルによる purge なし)",
        "cpcv_paths": "同上。cpcv.py の経路は C(N, K) の組合せそのもの(1 組合せ = 1 経路)で、AFML の φ 本の経路を組み立てる口が無い",
        "mde": "MDE・検出力の関数が無い",
        "pbo": "cpcv.py 166-168 行が自分で「古典的な López de Prado の PBO は IS で最良の設定を選ぶ手順が要るので、ここで PBO と呼ぶのは誤り」と書き、"
               "経路の頑健さだけを出す。性能の行列から PBO を出す口が無い",
        "iter_ledger": "n_trials は呼ぶ側が渡す引数(metrics.py 294 行・unified_runner.py 561 行)。試行を累積して数える台帳の口が無い",
        "sealed_read": "封印区間の口が無い",
        "run": "実行の記録は job_runner(job_runner.py 117 行 run_id = uuid.uuid4().hex[:16])が道具の DB(models.database の BacktestRun)に書く形で、"
               "DB を起こさずに呼べない。git の SHA・データの sha256 の欄も見当たらない",
        "auto_repro": "2 回回して比べる口が無い(当たりは種の説明文)",
        "trade_metrics": "compute_metrics(metrics.py 662 行)の欄(66-94 行)に 1 件ごとの bp・分位・負の割合・露出あたりが無い。_percentile(430 行)は"
                         "裾の指標の内部の関数",
        "fill_metrics": "instant_fill_rate(unified_runner.py 432 行)は子注文の即時の埋まりの率で、指値の約定率・取り逃しとは別。fill_calibration.py は DB の記録を読む",
        "markout": "markout の関数が無い(当たりは adverse_selection_multiplier = 約定の模型の定数)",
        "cost_breakdown": "matching_engine.py の手数料は Polymarket の手数料の模型で、与えた約定から種類ごとの内訳を出す口が無い",
        "exit_reasons": "決済理由の集計の口が無い",
        "dashboard": "画面は frontend/(React の TSX、BacktestStudio.tsx ほか)で、組み立て(npm)と backend の API サーバ(DB つき)が要る。"
                     "導入したのは backend/services の関数だけで、実行の一覧と項目別タブの画面を起こせない",
    }

    def op_walk_forward(self, inp):
        tr, te, st = inp["train_days"], inp["test_days"], inp["step_days"]
        if not (tr == te == st) or inp.get("mode") != "rolling":
            raise NotExpressible("walk_forward: walk_forward_split の転がる窓は学習 = 評価 = 進みの等幅だけ(walk_forward.py 99-129 行 _rolling_windows、"
                                 f"fold_w = 期間 / (窓の数 + 1))。この要求は学習 {tr} 日・評価 {te} 日・進み {st} 日")
        rows = inp["rows"]
        start = rows[0] // DAY * DAY
        end = (rows[-1] // DAY + 1) * DAY
        total = (end - start) // DAY
        if total % tr:
            raise NotExpressible(f"walk_forward: 期間 {total} 日が窓の幅 {tr} 日で割り切れない")
        wins = walk_forward_split(start=_dt(start), end=_dt(end),
                                  config=WalkForwardConfig(mode="rolling", n_folds=total // tr - 1, embargo_seconds=0.0))
        return {"folds": [{"train": {"bounds": [_ns(w.train_start), _ns(w.train_end)]},
                           "test": {"bounds": [_ns(w.test_start), _ns(w.test_end)]}} for w in wins],
                "note": f"期間 [{_dt(start)}, {_dt(end)}) を n_folds = {total // tr - 1} で渡した"}

    def op_block_bootstrap(self, inp):
        lo, hi = block_bootstrap_ci(inp["x"], statistics.fmean, n_resamples=inp["n_resamples"],
                                    confidence=1 - inp["alpha"], seed=inp["seed"])
        if lo is None:
            raise NotExpressible("block_bootstrap: 道具が区間を返さなかった(None)")
        return {"ci": [lo, hi], "note": "ブロックの長さを渡す引数が無い(metrics.py 184 行)。道具が自己相関から平均の長さを決めた(_mean_block_length、163 行)"}

    def op_dsr(self, inp):
        if abs(inp["var_trials"] - 1.0 / inp["T"]) > 1e-15:
            raise NotExpressible("dsr: 試行の SR の分散を渡す引数が無い(metrics.py 289-296 行。道具は 1/T を使う = 324-326 行)")
        r = deflated_sharpe_from_moments(annualized_sharpe=inp["sr"], skew=inp["skew"], excess_kurtosis=inp["kurtosis"] - 3.0,
                                         n_observations=inp["T"], n_trials=inp["n_trials"], periods_per_year=1)
        return {"dsr": r["deflated_sharpe"], "note": "periods_per_year = 1(SR は 1 期あたり)、尖度は超過の数え方に直して渡した(− 3)。"
                "試行の SR の分散は道具の固定 1/T で、要求の V と同じ値"}

    def op_dsr_returns(self, inp):
        if abs(inp["var_trials"] - 1.0 / len(inp["returns"])) > 1e-15:
            raise NotExpressible("dsr_returns: 試行の SR の分散を渡す引数が無い(道具は 1/T を使う = metrics.py 324-326 行)")
        r = deflated_sharpe_ratio(inp["returns"], n_trials=inp["n_trials"], periods_per_year=1)
        return {"dsr": r["deflated_sharpe"], "note": "deflated_sharpe_ratio(metrics.py 358 行)に系列をそのまま渡した(periods_per_year = 1)"}

    def op_drawdown(self, inp):
        usd, frac, _dur = max_drawdown([(_dt(t), v) for t, v in zip(inp["t_ns"], inp["equity"])])
        return {"max_dd_abs": usd, "max_dd_pct": frac * 100.0}


TARGET = Homerun()
