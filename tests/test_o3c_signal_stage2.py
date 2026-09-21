"""`scripts/o3c_signal_stage2.py`(段2: 後半5,000件に Jev V1 + 前半で固定した logistic を
一度だけ当てる道具)の試験。

**測るもの**(委任文 `docs/DATA/delegations/20260920_o3c_signal_v4_stage2_prompt.md`
【作るもの】4)
  1. 再開の冪等性(既に answers.jsonl にある print_id は Jev を呼び直さない。
     2 回目の実行で行が重複しない)。
  2. logistic の予測が定数ファイル(config の係数・凍結した経験分布 npz)だけから
     決まる(`build_ecdf` を後半に対して呼ばない。無関係な列を変えても同じ)。
  3. 位置(1 件目 / 連鎖の中)で使う材料・係数が切り替わる。
  4. 判定語が出力(表・ソース)に無い。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

_spec_sc = importlib.util.spec_from_file_location(
    "o3c_signal_continue", ROOT / "scripts" / "o3c_signal_continue.py")
sc = importlib.util.module_from_spec(_spec_sc)
assert _spec_sc.loader is not None
_spec_sc.loader.exec_module(sc)

_spec_s2 = importlib.util.spec_from_file_location(
    "o3c_signal_stage2", ROOT / "scripts" / "o3c_signal_stage2.py")
s2 = importlib.util.module_from_spec(_spec_s2)
assert _spec_s2.loader is not None
_spec_s2.loader.exec_module(s2)

js = s2.js
lg = s2.lg
NAN = float("nan")


# ---------------------------------------------------------------------------
# 合成データ: 後半・1 件目(b1)+ 後半・連鎖の中(b2)を持つ最小の StateBuilder
# ---------------------------------------------------------------------------
def _write_gz_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, compression="gzip")


def _build_dataset(tmp_path: Path):
    day = "2024-01-02"
    t0 = sc.day_start_ms(day) + 3_600_000
    ts1 = t0                       # 後半・1件目(cand_1 == 0)
    ts2 = t0 + 10_000               # 後半・連鎖の中(cand_1 == 1)

    prints_df = pd.DataFrame([
        {"kind": "print", "print_id": "b1", "day": day, "side": "BUY", "ts_ms": ts1,
         "t0_ms": ts1, "p0": 100.0, "notional": 500_000.0, "dist_node_bp": 0.0,
         "oi_covered": 0, "bundle_id": ""},
        {"kind": "print", "print_id": "b2", "day": day, "side": "BUY", "ts_ms": ts2,
         "t0_ms": ts2, "p0": 101.0, "notional": 300_000.0, "dist_node_bp": 0.0,
         "oi_covered": 0, "bundle_id": ""},
    ])
    rows_path = tmp_path / "rows_prints.csv.gz"
    _write_gz_csv(rows_path, prints_df)

    # FEATURES_FIRST = cand_14, cand_8, cand_C3, cand_C4, cand_11, cand_A6, cand_R1,
    #                  cand_9, cand_15, cand_N2(add_n2_column で足す)
    # FEATURES_CHAIN = cand_F5, cand_1, cand_F3, cand_14, cand_A6, cand_C4, cand_15,
    #                  cand_11, cand_C3, cand_8, cand_2
    def mat_row(pid, side, ts_ms, cand_1, **extra):
        r = {"print_id": pid, "day": day, "side": side, "half": "後半", "ts_ms": ts_ms,
            "cand_1": cand_1, "cand_2": 1.0, "cand_3": NAN, "cand_5p": NAN,
            "cand_6": 0.0, "cand_8": 2.0, "cand_9": 3.0, "cand_10": NAN,
            "cand_11": 4.0, "cand_12": NAN, "cand_13": NAN, "cand_14": 5.0,
            "cand_15": 6.0, "cand_F3": 7.0, "cand_F4": NAN, "cand_A3": NAN,
            "cand_A4": NAN, "cand_A5": NAN, "cand_A6": 8.0, "cand_A9": 0.0,
            "cand_C3": 9.0, "cand_C4": 10.0, "cand_R1": 11.0, "cand_F5": 12.0,
            "cand_A9_count": 0.0}
        r.update(extra)
        return r

    materials_df = pd.DataFrame([
        mat_row("b1", "BUY", ts1, 0.0),
        mat_row("b2", "BUY", ts2, 1.0),
    ])
    materials_path = tmp_path / "rows_materials.csv.gz"
    _write_gz_csv(materials_path, materials_df)

    def cont_row(pid, label_60):
        r = {"print_id": pid}
        for n in sc.MAT_NUMS:
            r[sc.MAT_COL[n]] = 1.0
        r[sc.MAT_COL[6]] = "UTC 00-06"
        r["mat1_elapsed_since_burst_s"] = 0.0
        r["mat3_notional_raw"] = 1.0
        r["mat8_amt_5bp"] = NAN
        r["mat8_amt_20bp"] = NAN
        r["mat8_covered"] = 0.0
        r["mat10_funding_rate"] = 0.0
        r["label_60"] = label_60
        return r

    continue_df = pd.DataFrame([cont_row("b1", 1.0), cont_row("b2", 0.0)])
    continue_path = tmp_path / "rows_continue.csv.gz"
    _write_gz_csv(continue_path, continue_df)

    return rows_path, materials_path, continue_path, day, ts1, ts2


def _make_builder(tmp_path):
    rows_path, materials_path, continue_path, day, ts1, ts2 = _build_dataset(tmp_path)
    bands = {  # 中身は使わない(V1 の文を作るだけ)。型の要る鍵だけ埋める
        "notional": [1.0, 2.0, 3.0, 4.0], "chain_notional": [1.0, 2.0, 3.0, 4.0],
        "last10s_notional": [1.0, 2.0, 3.0, 4.0], "oi_ahead_20bp": [1.0, 2.0, 3.0, 4.0],
        "trade_count_60s": [1.0, 2.0, 3.0, 4.0], "vol_ratio_c4": [1.0, 2.0, 3.0, 4.0],
        "oi_slope_1h": [-2.0, -1.0, 1.0, 2.0], "day_extreme_c3_quartiles": [1.0, 2.0, 3.0],
    }
    sb = js.StateBuilder(materials_path=materials_path, continue_path=continue_path,
                         rows_path=rows_path, data_root=tmp_path / "unused", bands=bands)
    times = np.arange(ts1 - 400_000, ts2 + 400_000, 1000, dtype=np.int64)
    prices = 100.0 + 0.0001 * (times - times[0])
    qtys = np.ones(times.size)

    def fake_load_window5(data_root, day_, cache, back_ms, fwd_ms):
        return times, prices, qtys, [], [day_]

    return sb, fake_load_window5


def _write_frozen_logit_fixture(tmp_path):
    """`compute_logit_probs` が読む config/ecdf をテスト専用の小さいものに差し替える。"""
    rng = np.random.default_rng(0)
    ecdf_first = {f: np.sort(rng.normal(size=50) + i) for i, f in enumerate(lg.FEATURES_FIRST)}
    ecdf_chain = {f: np.sort(rng.normal(size=50) + i) for i, f in enumerate(lg.FEATURES_CHAIN)}
    ecdf_first_path = tmp_path / "ecdf_first.npz"
    ecdf_chain_path = tmp_path / "ecdf_chain.npz"
    np.savez(ecdf_first_path, **ecdf_first)
    np.savez(ecdf_chain_path, **ecdf_chain)

    cfg_first = {"係数": {"切片": 0.5, **{f: 0.1 * (i + 1) for i, f in enumerate(lg.FEATURES_FIRST)}}}
    cfg_chain = {"係数": {"切片": -0.3, **{f: -0.1 * (i + 1) for i, f in enumerate(lg.FEATURES_CHAIN)}}}
    cfg_first_path = tmp_path / "logit_first.yaml"
    cfg_chain_path = tmp_path / "logit_chain.yaml"
    cfg_first_path.write_text(yaml.safe_dump(cfg_first, allow_unicode=True))
    cfg_chain_path.write_text(yaml.safe_dump(cfg_chain, allow_unicode=True))
    return ecdf_first_path, ecdf_chain_path, cfg_first_path, cfg_chain_path


# ---------------------------------------------------------------------------
# (2)(3) logistic の予測が定数ファイルだけから決まる・位置で切り替わる
# ---------------------------------------------------------------------------
def test_logit_probs_use_frozen_files_only_and_switch_by_position(tmp_path, monkeypatch):
    sb, fake = _make_builder(tmp_path)
    monkeypatch.setattr(js, "load_window5", fake)

    ecdf_first_path, ecdf_chain_path, cfg_first_path, cfg_chain_path = \
        _write_frozen_logit_fixture(tmp_path)
    monkeypatch.setattr(lg, "ECDF_FIRST", ecdf_first_path)
    monkeypatch.setattr(lg, "ECDF_CHAIN", ecdf_chain_path)
    monkeypatch.setattr(lg, "CONFIG_FIRST", cfg_first_path)
    monkeypatch.setattr(lg, "CONFIG_CHAIN", cfg_chain_path)

    # `build_ecdf` を後半に対して 1 度も呼ばないこと(反証者7 D5)を、
    # 呼ばれたら例外にする形で検査する。
    calls = {"n": 0}
    orig_build_ecdf = lg.build_ecdf

    def _spy_build_ecdf(*a, **kw):
        calls["n"] += 1
        return orig_build_ecdf(*a, **kw)

    monkeypatch.setattr(lg, "build_ecdf", _spy_build_ecdf)

    mat = pd.read_csv(tmp_path / "rows_materials.csv.gz", low_memory=False)
    df_back = mat[mat["half"] == "後半"].reset_index(drop=True)
    logit_prob_of = s2.compute_logit_probs(sb, df_back)

    assert calls["n"] == 0, "後半に build_ecdf を呼んでいる(反証者7 D5 違反)"
    assert set(logit_prob_of) == {"b1", "b2"}
    assert 0.0 <= logit_prob_of["b1"] <= 1.0
    assert 0.0 <= logit_prob_of["b2"] <= 1.0

    # 手計算(apply_frozen_rank + predict を直接呼ぶ)と一致すること
    ecdf_first = lg.load_ecdf_npz(ecdf_first_path)
    beta_first = s2.load_beta(cfg_first_path, lg.FEATURES_FIRST)
    df_first = df_back[df_back["print_id"] == "b1"].reset_index(drop=True)
    df_first = lg.add_n2_column(sb, df_first)
    X1 = lg.apply_frozen_rank(ecdf_first, lg.FEATURES_FIRST, df_first)
    want_b1 = float(lg.predict(X1, beta_first)[0])
    assert logit_prob_of["b1"] == pytest.approx(want_b1)

    ecdf_chain = lg.load_ecdf_npz(ecdf_chain_path)
    beta_chain = s2.load_beta(cfg_chain_path, lg.FEATURES_CHAIN)
    df_chain = df_back[df_back["print_id"] == "b2"].reset_index(drop=True)
    X2 = lg.apply_frozen_rank(ecdf_chain, lg.FEATURES_CHAIN, df_chain)
    want_b2 = float(lg.predict(X2, beta_chain)[0])
    assert logit_prob_of["b2"] == pytest.approx(want_b2)

    # 位置で違う入力(材料の並び)・違う係数が使われている(b1 と b2 の材料の並びが違う)
    assert lg.FEATURES_FIRST != lg.FEATURES_CHAIN


def test_logit_probs_unaffected_by_unrelated_column(tmp_path, monkeypatch):
    """logistic の入力に無い列を書き換えても予測は変わらない(定数ファイルだけで決まる)。"""
    sb, fake = _make_builder(tmp_path)
    monkeypatch.setattr(js, "load_window5", fake)
    ecdf_first_path, ecdf_chain_path, cfg_first_path, cfg_chain_path = \
        _write_frozen_logit_fixture(tmp_path)
    monkeypatch.setattr(lg, "ECDF_FIRST", ecdf_first_path)
    monkeypatch.setattr(lg, "ECDF_CHAIN", ecdf_chain_path)
    monkeypatch.setattr(lg, "CONFIG_FIRST", cfg_first_path)
    monkeypatch.setattr(lg, "CONFIG_CHAIN", cfg_chain_path)

    mat = pd.read_csv(tmp_path / "rows_materials.csv.gz", low_memory=False)
    df_back = mat[mat["half"] == "後半"].reset_index(drop=True)
    probs_a = s2.compute_logit_probs(sb, df_back)

    df_back2 = df_back.copy()
    df_back2["cand_13"] = 999_999.0  # logistic の入力に含まれない列
    probs_b = s2.compute_logit_probs(sb, df_back2)
    assert probs_a == probs_b


def test_position_of():
    assert s2.position_of(0.0) == "1件目"
    assert s2.position_of(0) == "1件目"
    assert s2.position_of(1.0) == "連鎖の中"
    assert s2.position_of(3.0) == "連鎖の中"


# ---------------------------------------------------------------------------
# (1) 再開の冪等性
# ---------------------------------------------------------------------------
class _FakeClient:
    def __init__(self):
        self.calls = 0
        self.seen_states = []

    def evaluate(self, state, questions):
        self.calls += 1
        self.seen_states.append(state)
        return {"answers": {"next_print_within_60s": {"noul": 0.5}},
               "usage": {"input_tokens": 42}}

    def close(self):
        pass


def test_resume_does_not_recall_jev_and_has_no_duplicate_lines(tmp_path, monkeypatch):
    sb, fake = _make_builder(tmp_path)
    monkeypatch.setattr(js, "load_window5", fake)
    prints = [{"print_id": "b1", "day": "2024-01-02", "side": "BUY", "group": "0"},
             {"print_id": "b2", "day": "2024-01-02", "side": "BUY", "group": "1-2"}]
    logit_prob_of = {"b1": 0.4, "b2": 0.6}
    label_of = {"b1": 1.0, "b2": 0.0}
    out_path = tmp_path / "answers.jsonl"

    fc1 = _FakeClient()
    note1 = s2.run_stage2(sb, prints, logit_prob_of, label_of, out_path=out_path,
                          rate_per_sec=1000.0, client=fc1)
    assert note1["呼び出し数"] == 2
    assert fc1.calls == 2
    lines1 = out_path.read_text().splitlines()
    assert len(lines1) == 2

    # 中断→再開を模す: 同じ出力ファイルに対してもう一度実行
    fc2 = _FakeClient()
    note2 = s2.run_stage2(sb, prints, logit_prob_of, label_of, out_path=out_path,
                          rate_per_sec=1000.0, client=fc2)
    assert note2["呼び出し数"] == 0
    assert note2["再開で読み飛ばした件数"] == 2
    assert fc2.calls == 0
    lines2 = out_path.read_text().splitlines()
    assert len(lines2) == 2  # 重複していない
    pids = [json.loads(ln)["print_id"] for ln in lines2]
    assert sorted(pids) == ["b1", "b2"]


def test_resume_partial_only_calls_remaining(tmp_path, monkeypatch):
    sb, fake = _make_builder(tmp_path)
    monkeypatch.setattr(js, "load_window5", fake)
    prints = [{"print_id": "b1", "day": "2024-01-02", "side": "BUY", "group": "0"},
             {"print_id": "b2", "day": "2024-01-02", "side": "BUY", "group": "1-2"}]
    logit_prob_of = {"b1": 0.4, "b2": 0.6}
    label_of = {"b1": 1.0, "b2": 0.0}
    out_path = tmp_path / "answers.jsonl"
    out_path.write_text(json.dumps({"print_id": "b1", "位置": "1件目",
                                    "logit_prob": 0.4, "label_60": 1.0,
                                    "jev_prob": 0.3, "input_tokens": 10,
                                    "latency_s": 0.1}) + "\n")

    fc = _FakeClient()
    note = s2.run_stage2(sb, prints, logit_prob_of, label_of, out_path=out_path,
                         rate_per_sec=1000.0, client=fc)
    assert note["呼び出し数"] == 1
    assert note["再開で読み飛ばした件数"] == 1
    assert fc.calls == 1
    lines = out_path.read_text().splitlines()
    assert len(lines) == 2
    pids = [json.loads(ln)["print_id"] for ln in lines]
    assert sorted(pids) == ["b1", "b2"]


def test_run_stage2_records_position_and_fields(tmp_path, monkeypatch):
    sb, fake = _make_builder(tmp_path)
    monkeypatch.setattr(js, "load_window5", fake)
    prints = [{"print_id": "b1", "day": "2024-01-02", "side": "BUY", "group": "0"},
             {"print_id": "b2", "day": "2024-01-02", "side": "BUY", "group": "1-2"}]
    logit_prob_of = {"b1": 0.4, "b2": 0.6}
    label_of = {"b1": 1.0, "b2": 0.0}
    out_path = tmp_path / "answers.jsonl"
    fc = _FakeClient()
    s2.run_stage2(sb, prints, logit_prob_of, label_of, out_path=out_path,
                 rate_per_sec=1000.0, client=fc)
    recs = {json.loads(ln)["print_id"]: json.loads(ln) for ln in out_path.read_text().splitlines()}
    assert recs["b1"]["位置"] == "1件目"
    assert recs["b2"]["位置"] == "連鎖の中"
    for pid in ("b1", "b2"):
        r = recs[pid]
        assert r["jev_prob"] == 0.5
        assert r["input_tokens"] == 42
        assert r["logit_prob"] == logit_prob_of[pid]
        assert r["label_60"] == label_of[pid]
        assert "latency_s" in r


# ---------------------------------------------------------------------------
# (4) 判定語
# ---------------------------------------------------------------------------
def test_no_banned_words_in_source():
    src = (ROOT / "scripts" / "o3c_signal_stage2.py").read_text()
    sc.check_no_banned(src, "source")


def test_no_banned_words_in_built_tables(tmp_path):
    answers_path = tmp_path / "answers.jsonl"
    with answers_path.open("w", encoding="utf-8") as fh:
        for i in range(30):
            rec = {"print_id": f"p{i}", "位置": "1件目" if i % 2 == 0 else "連鎖の中",
                  "jev_prob": (i % 10) / 10.0, "logit_prob": ((i + 3) % 10) / 10.0,
                  "label_60": float(i % 2), "input_tokens": 100 + i,
                  "latency_s": 0.2 + 0.01 * i}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    md = s2.build_stage2_tables(out_dir=tmp_path)
    sc.check_no_banned(md, "stage2_tables.md")


# ---------------------------------------------------------------------------
# `paper_logs/` を開かない
# ---------------------------------------------------------------------------
def test_source_never_opens_paper_logs():
    """`paper_logs` という文字列が出るのは説明文(docstring)だけで、実際にそれを
    開くコードは無い(`o3c_jev_state.py` の同名試験と同じ流儀)。"""
    src = (ROOT / "scripts" / "o3c_signal_stage2.py").read_text().splitlines()
    hits = [ln for ln in src if "paper_logs" in ln]
    assert hits and all("開かない" in ln for ln in hits), hits
