"""当方の現状 (the environment as it stands) for the item 3 battery.

What "the current environment" is, for this item (REQUIREMENTS.md §4):
  - the old engine src/bot/backtest/ (engine.run_backtest, metrics.compute_metrics,
    walk_forward.split_data / evaluate_on_splits),
  - the research helpers in src/bot/research/ that the requirement names or that
    already implement one of the item's functions: sealed.load_sealed (the 4 gates)
    and overnight.block_bootstrap_ci (a moving-block bootstrap),
  - the dashboard scripts/dashboard.py and its tests tests/test_dashboard.py.
One-off research scripts (scripts/research_*.py, scripts/measure_*.py, scripts/phase2/)
are not part of the environment: they are per-study code, not a reusable engine
(REQUIREMENTS.md §4, the row for ブロック・ブートストラップ).

Each request is handed to one of these through its public API; when none has a
mouth for it, NotExpressible names what was looked for and where.
"""
from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
REPO = HERE.parents[4]

from i3_protocol import NotExpressible, Refused  # noqa: E402

_NO = {
    "calendar_split": "旧 walk_forward.split_data(train_frac, val_frac)(src/bot/backtest/walk_forward.py 20-32 行)は行の数の割合で"
                      "切るだけで、日付・時間帯を渡す引数が無い",
    "walk_forward": "旧 walk_forward.evaluate_on_splits(同 36-53 行)は split_data の 3 分割を 1 回回すだけで、窓を切り直す口が無い",
    "walk_forward_eval": "同上(窓を切り直す口が無い)",
    "purged_split": "src/bot/backtest/ と src/bot/research/ に purge・embargo の口が無い(grep -rn 'purg\\|embargo' の当たり 0)",
    "cpcv": "src/bot/backtest/ と src/bot/research/ に CPCV の口が無い(grep -rni 'cpcv\\|combinatorial' の当たり 0)",
    "cpcv_paths": "同上(CPCV の口が無い)",
    "mde": "src/bot/ に MDE の関数が無い(grep -rniE 'def .*(mde|minimum_detectable)' src/ の当たり 0。規則は research-protocol §4.1 の文だけ)",
    "verdict": "src/bot/ に 陰性 / 不明 / 陽性 を分ける関数が無い(規則は research-protocol §5 の文だけ)",
    "dsr": "src/bot/ に deflated Sharpe の関数が無い(grep -rniE 'deflated.?sharpe' src/ の当たり 0。'deflat' の当たり 5 件は gz_members.py の gzip の deflate)",
    "dsr_returns": "src/bot/ に deflated Sharpe の関数が無い(grep -rniE 'deflated.?sharpe' src/ の当たり 0)",
    "pbo": "src/bot/ に PBO の関数が無い(grep -rniw 'pbo' src/ の当たり 0。'overfitting' の当たり 2 件は walk_forward.py 2 行と sealed.py 5 行の説明文)",
    "iter_ledger": "src/bot/ に周回数の台帳の口が無い(ITER.md は research-protocol の文の規則だけ。grep -rn 'ITER' src/ の当たり 0)",
    "iter_dsr": "周回数の台帳と deflated Sharpe の口が無い",
    "data_read": "旧エンジンにファイルの読み口が無い(engine.run_backtest は足の DataFrame を受け取る)。封印を知る普通の読み口も無い",
    "run": "旧エンジンに実行記録の口が無い(src/bot/backtest/ に sha256・git・run_id の文字列が 0 件。run_backtest は BacktestResult を返すだけ)",
    "run_ids": "旧エンジンに実行 ID が無い(同上)",
    "auto_repro": "旧エンジンに 2 回回して比べる口が無い(同上)",
    "trade_metrics": "旧 metrics.compute_metrics(trade_pnls, equity_curve)(src/bot/backtest/metrics.py 29-31 行)は円の損益の列を"
                     "受けて 12 個のスカラーを返すだけで、1 件ごとの bp・分位・負の割合・露出の時間の欄が無い(10-23 行)",
    "fill_metrics": "旧 metrics に約定率・取り逃しの欄が無い(metrics.py 10-23 行。入力に注文が無い)",
    "markout": "旧 metrics に markout の欄が無い(metrics.py 10-23 行)",
    "cost_breakdown": "旧 metrics は total_fees_jpy の合計 1 つだけ(metrics.py 23 行)で、種類ごとの内訳の口が無い",
    "exit_reasons": "旧エンジンは往復ごとに reason を記録する(engine.py 239 行)が、compute_metrics は reason を受け取らず"
                    "(metrics.py 29 行)、理由ごとの集計の口が無い",
}


def _import_dashboard():
    spec = importlib.util.spec_from_file_location("i3_current_dashboard", REPO / "scripts" / "dashboard.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CurrentImpl:
    name = "current_impl"

    def run(self, inp: dict) -> dict:
        op = inp["op"]
        if op == "block_bootstrap":
            import numpy as np
            from bot.research.overnight import block_bootstrap_ci
            lo, hi = block_bootstrap_ci(np.asarray(inp["x"], dtype=float), block=inp["block_len"],
                                        n_boot=inp["n_resamples"], seed=inp["seed"], alpha=inp["alpha"])
            return {"ci": [lo, hi]}
        if op == "drawdown":
            import pandas as pd
            from bot.backtest.metrics import compute_metrics
            m = compute_metrics([], pd.Series(inp["equity"], dtype=float))
            return {"max_dd_pct": m.max_drawdown_pct}  # no absolute drawdown field (metrics.py 10-23)
        if op == "sealed_read":
            from bot.research.sealed import SealedDataError, load_sealed
            os.environ.pop("PHASE2_FINAL_EVAL", None)
            os.environ.update(inp["env"])
            try:
                df = load_sealed(os.path.join(inp["root"], inp["path"]), inp["unit"], inp["token"], root=inp["root"])
            except SealedDataError as exc:
                raise Refused(f"SealedDataError: {exc}")
            return {"v": [int(x) for x in df["v"].tolist()]}
        if op == "dashboard":
            return self._dashboard(inp)
        if op == "wiring_test":
            return self._wiring(inp)
        raise NotExpressible(_NO.get(op, f"{op} の口が無い"))

    def _dashboard(self, inp):
        from http.server import ThreadingHTTPServer
        dash = _import_dashboard()
        srv = ThreadingHTTPServer(("127.0.0.1", 0), dash.Handler)
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            html = urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}/", timeout=20).read().decode("utf-8")
        finally:
            srv.shutdown()
            srv.server_close()
        nav = re.search(r'<nav class="tabs">(.*?)</nav>', html, re.S)
        tabs = re.findall(r"<button[^>]*>([^<]*)</button>", nav.group(1)) if nav else []
        raise NotExpressible(f"GET / の最上段のタブは {tabs} で「バックテスト」が無い(scripts/dashboard.py 197-200 行)。"
                             "実行を書き出す口も無いので、実行の一覧・項目別タブを読めない")

    def _wiring(self, inp):
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([str(HERE.parent / "wiring_break"), str(REPO / "src"), env.get("PYTHONPATH", "")])
        env.pop("I3_WIRING_BREAK", None)
        if inp.get("break"):
            env["I3_WIRING_BREAK"] = inp["break"]
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(REPO / "tests" / "test_dashboard.py")],
                           cwd=str(REPO), env=env, capture_output=True, text=True, timeout=240)
        return {"passed": r.returncode == 0, "note": "tests/test_dashboard.py(当方のダッシュボードの配線の試験の全部)"}


TARGET = CurrentImpl()
