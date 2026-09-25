"""Survey candidate `mlflow` (no catalogue number; REQUIREMENTS.md §3.3 C3-7/8/9) for the item 3 battery.

Install: venv item_3/mlflow, mlflow==3.16.1 from PyPI (the version the tools survey inspected,
docs/DATA/probes/20260922_tools_1_run8.log 35-61); pre-install check and install log
venvs/item_3/logs/i3_r1_scenekeeper_install_mlflow.log.  Telemetry is off
(MLFLOW_DISABLE_TELEMETRY=true, DO_NOT_TRACK=true, set by the runner); the tracking store is a
sqlite file under the request's scratch root (the file store refuses: probes run8 line 67).

What the tool is: an experiment tracker.  It does not run a backtest; a "run" here is what
the tool records when the user's code logs the request's run spec to it (seed as a param,
the config as a logged dict, the purpose as a tag).  Only what the tool itself records and
returns (get_run, load_dict, search_runs) is reported.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _i3_base import Base  # noqa: E402

logging.getLogger("mlflow").setLevel(logging.ERROR)
import mlflow  # noqa: E402
from mlflow.tracking import MlflowClient  # noqa: E402


class Mlflow(Base):
    name = "opp_mlflow"
    WHAT = "mlflow は実験の記録係(パラメータ・指標・成果物・札・実行の識別子)で、バックテストも統計の検証も持たない。"
    NO = {
        "auto_repro": "2 回の実行を比べて一致を判定する口が無い(当たり 44 ファイルは模型の評価器・自動記録・技能の文書。"
                      "run の比較は画面で人が見る形)",
        "iter_dsr": "試行の数は数えられる(search_runs)が、deflated Sharpe の関数が無い",
        "dashboard": "mlflow の画面(mlflow ui / server)は実験と実行の一覧・実行ごとの概要・指標・成果物の画面で、「バックテスト」タブと"
                     "要件の 10 項目のタブを持たない。画面は組み立て済みの JavaScript が描くので、配った HTML からタブの名を読めない",
    }

    def _uri(self, root, sub=""):
        d = os.path.join(root, sub) if sub else root
        os.makedirs(d, exist_ok=True)
        return f"sqlite:///{os.path.join(d, 'mlflow.db')}"

    def _log(self, root, run):
        with mlflow.start_run() as r:
            mlflow.log_param("seed", run["seed"])
            mlflow.log_dict(run["config"], "config.json")
            if "purpose" in run:
                mlflow.set_tag("purpose", run["purpose"])
            if "prereg" in run:
                mlflow.log_artifact(os.path.join(root, run["prereg"]))
        return r.info.run_id

    def _record(self, run_id):
        c = MlflowClient()
        info = c.get_run(run_id)
        rec = {"config": mlflow.artifacts.load_dict(f"runs:/{run_id}/config.json")}
        if "seed" in info.data.params:
            rec["seed"] = json.loads(info.data.params["seed"])  # params are stored as strings
        if "mlflow.source.git.commit" in info.data.tags:
            rec["git_sha"] = info.data.tags["mlflow.source.git.commit"]
        if "purpose" in info.data.tags:
            rec["purpose"] = info.data.tags["purpose"]
        return rec

    def op_run(self, inp):
        mlflow.set_tracking_uri(self._uri(inp["root"]))
        mlflow.set_experiment("i3")
        k = int(inp.get("repeat", 1))
        ids = [self._log(inp["root"], inp["run"]) for _ in range(k)]
        recs = [self._record(i) for i in ids]
        return {"run_id": ids[0], "record": recs[0], "records": recs,
                "note": "記録に data_sha256・diff_hash・version・prereg_sha256 の欄は無い(mlflow が自分で付けるのは git の commit の札など)"}

    def op_run_ids(self, inp):
        mlflow.set_tracking_uri(self._uri(inp["root"]))
        mlflow.set_experiment("i3")
        ids = []
        for run, pause in zip(inp["runs"], inp["sleep_before_s"]):
            time.sleep(pause)
            ids.append(self._log(inp["root"], run))
        return {"ids": ids}

    def op_iter_ledger(self, inp):
        uri = self._uri(inp["root"], inp["ledger_dir"])
        mlflow.set_tracking_uri(uri)
        exp = mlflow.set_experiment("iter")

        def add(trials):
            for t in trials:
                with mlflow.start_run():
                    mlflow.log_param("design", t["design"])
                    mlflow.log_metric("sr", t["sr"])

        def count(client):
            return len(client.search_runs([exp.experiment_id], max_results=1000))

        add(inp["first"])
        c1 = count(MlflowClient(uri))
        c2 = count(MlflowClient(tracking_uri=uri))  # a fresh reader of the same store
        add(inp["more"])
        c3 = count(MlflowClient(tracking_uri=uri))
        return {"counts": [c1, c2, c3]}


TARGET = Mlflow()
