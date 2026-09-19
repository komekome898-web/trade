"""`scripts/o3c_reaction_r2.py`(O-3c 段 A 2 周目の読みの道具)の試験。

**測るもの**
  - 標準化の式(Δ_h = Σ_k w_k (mean_D1,k − mean_C,k))と帯の切り方を、
    合成の表に対する**独立な計算**と突き合わせる(道具の内部を使い回さない)。
  - 対照の `r_h` が `bp_{h}m` に**相手の束の side の符号**を当てたものであること
    (対照行の `*_reactdir` 列は使わない。合成の表ではそこに毒(999)を入れてある)。
  - §6 の 7 分岐と F1′ の 4 分岐。
  - **関門が閉じていれば表を 1 枚も書かない**(`tests/test_audit_gates_wired.py` の型)。
  - `--power` が表を 1 枚も書かないこと。
  - 実物の表があれば、事前登録 §8 のサニティ #1〜#4 を実測する(無ければ skip)。

**この試験は判定の数値を 1 つも印字しない。**サニティは真偽だけを見る。
"""
from __future__ import annotations

import csv
import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location(
    "o3c_reaction_r2", ROOT / "scripts" / "o3c_reaction_r2.py"
)
r2 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(r2)

FULL = ROOT / "backtest_data" / "o3c_reaction_20260918_full" / "gap60_w8"
SAMPLE = ROOT / "backtest_data" / "o3c_reaction_20260918_sample" / "gap60_w8"
OBS1 = ROOT / "backtest_data" / "o3c_reaction_20260918_judge" / "observation_only.csv"


# =============================================================================
# 合成の表
# =============================================================================
POISON = 999.0        # 対照行の `*_reactdir` に入れる毒(道具が使っていないことを測る)


def make_tables(dirpath: Path, n_d1: int = 400, n_other: int = 120,
                n_ctl: int = 360, seed: int = 7) -> dict:
    """合成の `table.csv` / `table_mixed.csv` を書き、答え合わせ用の素材を返す。

    - 清算行: 先頭 `n_d1` 行が D1(`doi_pre_1h` = −20000 ≤ 切り値)、残りは D1 でない。
    - 合わせた対照: `matched_liq_id` で D1 の清算行を指す。1 行だけ mixed 束を指す
      (= 落ちるはず)。
    - 対照行の `bp_{h}m_reactdir` には毒を入れる(道具は `bp_{h}m` × 相手の符号を使う)。
    """
    dirpath.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    cols = sorted(r2.needed_columns())
    rows: list[dict] = []
    liq: list[dict] = []
    for i in range(n_d1 + n_other):
        d1 = i < n_d1
        side = "SELL" if i % 2 == 0 else "BUY"
        r = {c: "" for c in cols}
        r.update({
            "kind": "liq", "day": f"2024-01-{(i % 28) + 1:02d}",
            "cascade_id": f"L{i}", "matched_liq_id": "", "side": side,
            "doi_pre_1h": (-20000.0 - i) if d1 else (-1000.0 - i),
            "dist_vwap_bp": float(i + 1) * (1 if i % 3 else -1),
            "dist_node_bp": float((i * 7) % 401) + 0.5,
            "reach_back_vwap_240m": float((i % 5) < 3),
        })
        for h in r2.HORIZONS:
            r[f"bp_{h}m"] = float(rng.normal(0, 10))
            r[f"bp_{h}m_reactdir"] = float(rng.normal(-5, 10))
        rows.append(r)
        liq.append(r)

    mixed = [{"cascade_id": "MIX0", "side": "SELL"}]
    for j in range(n_ctl):
        partner = f"L{j % n_d1}" if j else "MIX0"     # 先頭 1 行だけ mixed 束を指す
        r = {c: "" for c in cols}
        r.update({
            "kind": "control_matched", "day": f"2024-01-{(j % 28) + 1:02d}",
            "cascade_id": f"C{j}", "matched_liq_id": partner, "side": "",
            "doi_pre_1h": -20000.0,
            "dist_vwap_bp": float((j * 3) % 401) + 0.25,
            "dist_node_bp": float((j * 11) % 401) + 0.75,
            "reach_back_vwap_240m": float((j % 4) < 2),
        })
        for h in r2.HORIZONS:
            r[f"bp_{h}m"] = float(rng.normal(1, 8))
            r[f"bp_{h}m_reactdir"] = POISON
        rows.append(r)

    with (dirpath / "table.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with (dirpath / "table_mixed.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["cascade_id", "side"])
        w.writeheader()
        for r in mixed:
            w.writerow(r)
    return {"rows": rows, "n_d1": n_d1}


def read_rows(dirpath: Path) -> list[dict]:
    with (dirpath / "table.csv").open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# --- 道具を使わない独立な実装(答え合わせ用)---------------------------------
def indep_groups(rows: list[dict]) -> tuple[list[dict], list[dict], dict]:
    side_by_id = {r["cascade_id"]: r["side"] for r in rows if r["kind"] == "liq"}
    side_by_id["MIX0"] = "SELL"
    d1 = [r for r in rows
          if r["kind"] == "liq" and float(r["doi_pre_1h"]) <= r2.CUT]
    c = [r for r in rows
         if r["kind"] == "control_matched"
         and float(r["doi_pre_1h"]) <= r2.CUT
         and r["matched_liq_id"] != "MIX0"]
    return d1, c, side_by_id


def indep_delta(d1: list[dict], c: list[dict], side_by_id: dict, h: int,
                dist_key: str = "dist_vwap_bp") -> tuple[float, float, float]:
    """Δ_h と mean_D1 / mean_C を、道具と別の素朴な実装で出す。"""
    ad = [abs(float(r[dist_key])) for r in d1]
    edges = list(np.nanpercentile(np.array(ad), np.linspace(0, 100, 11)))
    edges[0] = 0.0
    edges[-1] = r2.BIG
    num1 = num2 = 0.0
    tot = 0
    parts = []
    for k in range(10):
        lo, hi = edges[k], edges[k + 1]
        a = [float(r[f"bp_{h}m_reactdir"]) for r in d1
             if lo <= abs(float(r[dist_key])) < hi]
        b = []
        for r in c:
            if not (lo <= abs(float(r[dist_key])) < hi):
                continue
            sgn = -1.0 if side_by_id[r["matched_liq_id"]] == "SELL" else 1.0
            b.append(sgn * float(r[f"bp_{h}m"]))
        parts.append((a, b))
        tot += len(a)
    for a, b in parts:
        w = len(a) / tot
        num1 += w * (sum(a) / len(a))
        num2 += w * (sum(b) / len(b))
    return num1 - num2, num1, num2


# =============================================================================
# 1. 帯の切り方
# =============================================================================
def test_band_edges_are_the_deciles_with_0_and_big_ends():
    d = np.array([float(i) for i in range(1, 401)])
    e = r2.band_edges(d)
    ref = list(np.nanpercentile(d, np.linspace(0, 100, 11)))
    assert e[0] == 0.0 and e[-1] == r2.BIG
    assert e[1:-1] == pytest.approx(ref[1:-1])
    assert r2.edges_strictly_increasing(e)


def test_band_index_is_half_open_and_marks_nan_as_outside():
    edges = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, r2.BIG]
    d = np.array([0.0, 9.999, 10.0, 89.9, 90.0, 1e12, float("nan")])
    b = r2.band_index(d, edges)
    assert list(b[:5]) == [0, 0, 1, 8, 9]
    assert b[5] == -1          # 上端 1e9 以上は帯に入らない
    assert b[6] == -1          # NaN も入らない


# =============================================================================
# 2. 対照の符号(1 周目の規則)
# =============================================================================
def test_control_r_uses_partner_side_not_its_own_reactdir(tmp_path):
    make_tables(tmp_path / "run")
    tab = r2.Table(tmp_path / "run")
    c = tab.control_idx()
    got = tab.r_ctl(c, 5)
    rows = read_rows(tmp_path / "run")
    _, c_rows, side_by_id = indep_groups(rows)
    want = np.array([
        (-1.0 if side_by_id[r["matched_liq_id"]] == "SELL" else 1.0)
        * float(r["bp_5m"]) for r in c_rows
    ])
    assert got.size == want.size
    assert got == pytest.approx(want)
    assert not np.any(np.isclose(got, POISON))     # 毒を拾っていない
    # SELL の相手を持つ行は必ず生の bp と逆符号である
    raw = np.array([float(r["bp_5m"]) for r in c_rows])
    sell = np.array([side_by_id[r["matched_liq_id"]] == "SELL" for r in c_rows])
    assert np.all(np.sign(got[sell]) == -np.sign(raw[sell]))


def test_control_drops_rows_whose_partner_is_a_mixed_bundle(tmp_path):
    make_tables(tmp_path / "run")
    tab = r2.Table(tmp_path / "run")
    c = tab.control_idx()
    assert "MIX0" not in [tab.partner_id[tab._mat_pos[int(g)]] for g in c]
    assert len(c) == 359          # 360 行のうち mixed 相手の 1 行が落ちる


def test_liq_r_is_the_reactdir_column_as_is(tmp_path):
    make_tables(tmp_path / "run")
    tab = r2.Table(tmp_path / "run")
    d1 = tab.d1_idx()
    rows = read_rows(tmp_path / "run")
    d1_rows, _, _ = indep_groups(rows)
    assert len(d1) == len(d1_rows) == 400
    want = np.array([float(r["bp_15m_reactdir"]) for r in d1_rows])
    assert tab.r_liq(d1, 15) == pytest.approx(want)


# =============================================================================
# 3. 標準化の式
# =============================================================================
def test_standardize_matches_an_independent_computation(tmp_path):
    make_tables(tmp_path / "run")
    tab = r2.Table(tmp_path / "run")
    d1, c = tab.d1_idx(), tab.control_idx()
    edges = r2.band_edges(tab.dist(d1))
    rows = read_rows(tmp_path / "run")
    d1_rows, c_rows, side_by_id = indep_groups(rows)
    for h in r2.HORIZONS:
        st = r2.standardize(tab, d1, c,
                            col_liq=lambda t, i, h=h: t.r_liq(i, h),
                            col_ctl=lambda t, i, h=h: t.r_ctl(i, h),
                            edges=edges)
        want_d, want_m1, want_m2 = indep_delta(d1_rows, c_rows, side_by_id, h)
        assert st.delta == pytest.approx(want_d)
        assert st.mean_d1 == pytest.approx(want_m1)
        assert st.mean_c == pytest.approx(want_m2)
        assert sum(b["n_D1"] for b in st.bands) == st.n1
        assert st.w.sum() == pytest.approx(1.0)


def test_weights_sum_to_one_and_delta_is_nan_when_a_band_is_empty(tmp_path):
    """帯が空でも**その帯を落とさない**(落とすと標準化が別物になる)。"""
    v1 = np.array([1.0, 2.0, 3.0])
    b1 = np.array([0, 0, 1])
    v2 = np.array([1.0, 1.0])
    b2 = np.array([0, 0])          # 帯 1 に対照が居ない
    st = r2.Standardized(v1, b1, v2, b2, [0.0] * 10 + [r2.BIG])
    assert st.n1 == 3 and st.n2 == 2
    assert math.isnan(st.delta)
    se, reps = st.bootstrap(reps=10, seed=1)
    assert math.isnan(se) and reps == 0


def test_bootstrap_is_reproducible_and_counts_finite_replicates():
    rng = np.random.default_rng(3)
    v1 = rng.normal(0, 1, 500)
    v2 = rng.normal(0, 1, 500)
    b = np.tile(np.arange(10), 50)
    a1 = r2.Standardized(v1, b, v2, b, [0.0] * 10 + [r2.BIG])
    a2 = r2.Standardized(v1, b, v2, b, [0.0] * 10 + [r2.BIG])
    se1, n1 = a1.bootstrap(reps=200, seed=r2.SEED)
    se2, n2 = a2.bootstrap(reps=200, seed=r2.SEED)
    assert se1 == se2 and n1 == n2 == 200
    assert math.isfinite(se1) and se1 > 0


# =============================================================================
# 4. 7 分岐と 4 分岐(§6)
# =============================================================================
def test_decide_covers_the_seven_branches():
    z = r2.Z_ALPHA
    assert r2.decide(10, 100, 10, 100, 5.0, -1.0, 0.1) == r2.UNKNOWN_N
    assert r2.decide(100, 10, 100, 10, 5.0, -1.0, 0.1) == r2.UNKNOWN_N2
    # 帯の 1 つが 30 未満でも「不明」(帯は落とさない)
    assert r2.decide(100, 100, 29, 100, 5.0, -1.0, 0.1) == r2.UNKNOWN_N
    assert r2.decide(100, 100, 100, 29, 5.0, -1.0, 0.1) == r2.UNKNOWN_N2
    assert r2.decide(100, 100, 100, 100, float("nan"), -1.0, 0.1) == r2.UNKNOWN_T
    assert r2.decide(100, 100, 100, 100, -z, -1.0, 0.1) == "差あり(−)"
    assert r2.decide(100, 100, 100, 100, z, 1.0, 0.1) == "差あり(+)"
    assert r2.decide(100, 100, 100, 100, 0.5, -1.0, float("nan")) == r2.UNKNOWN_MDE
    v = r2.decide(100, 100, 100, 100, 0.5, -1.0, 2.5)
    assert v.startswith("検出されず(MDE = ") and v.endswith(" bp)")
    assert {r2.decide(100, 100, 100, 100, -z, -1.0, 0.1),
            r2.decide(100, 100, 100, 100, z, 1.0, 0.1)} <= set(
        ["差あり(+)", "差あり(−)"])


def test_decide_never_says_no_difference():
    for v in (r2.decide(100, 100, 100, 100, 0.5, -1.0, 2.5),
              r2.decide(100, 100, 100, 100, 0.5, -1.0, float("nan"))):
        assert "差なし" not in v and "陰性" not in v


def test_bar_near_marks_only_the_neighbourhood_of_z():
    z = r2.Z_ALPHA
    assert r2.bar_near(z) == "○"
    assert r2.bar_near(-(z - r2.BAR_NEAR_HALFWIDTH / 2)) == "○"
    assert r2.bar_near(z + 2 * r2.BAR_NEAR_HALFWIDTH) == ""
    assert r2.bar_near(float("nan")) == ""


def test_f1_reading_four_branches():
    def cells(verdicts):
        return [{"判定": v} for v in verdicts]
    assert r2.f1_reading(cells(["差あり(−)"] * 6)).startswith("F1′ と整合")
    assert r2.f1_reading(cells(["差あり(+)"] * 6)).startswith("F1′ の反証")
    assert r2.f1_reading(
        cells(["差あり(+)", "差あり(−)"] + ["検出されず(MDE = 1 bp)"] * 4)
    ).startswith("混在")
    assert r2.f1_reading(cells(["検出されず(MDE = 1 bp)"] * 6)).startswith("不明")
    assert r2.f1_reading(cells([r2.UNKNOWN_N] * 6)).startswith("不明")
    assert r2.f1_reading(cells(["差あり(−)"] * 5)).startswith("読めない")


# =============================================================================
# 5. 関門(閉じていれば表を 1 枚も書かない)
# =============================================================================
def _audit_record(root: Path, verdict: str = "判定: 通す") -> None:
    log = root / "docs" / "AUDITOR" / "ACTION_LOG.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"> 指摘の本文 {i} 行目。これは監査役が書いた文である。"
                     for i in range(1, 10))
    log.write_text(
        f"## 試験\n\n監査対象: {r2.UNIT}/{r2.STAGE}\n**監査役**: `owner-auditor`\n\n"
        f"{body}\n\n{verdict}\n", encoding="utf-8")


def _fake_observation_only(path: Path, run: Path) -> None:
    """合成の表に合わせた 1 周目の表(サニティ #2・#3 の突き合わせ先)。"""
    rows = read_rows(run)
    d1, c, side_by_id = indep_groups(rows)
    out = []
    for h in r2.HORIZONS:
        m1 = sum(float(r[f"bp_{h}m_reactdir"]) for r in d1) / len(d1)
        m2 = sum((-1.0 if side_by_id[r["matched_liq_id"]] == "SELL" else 1.0)
                 * float(r[f"bp_{h}m"]) for r in c) / len(c)
        out.append({"観測量": f"bp_{h}m_reactdir", "群": "D_Q1", "h": h,
                    "実群": f"{m1:.6f}", "対照(ii)": f"{m2:.6f}",
                    "走行": "gap60_w8"})
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["観測量", "群", "h", "実群", "対照(ii)", "走行"])
        w.writeheader()
        for r in out:
            w.writerow(r)


def _synthetic_argv(tmp_path: Path, out: Path) -> list[str]:
    return ["--judge", "--out-dir", str(out),
            "--table", str(tmp_path / "run"),
            "--table-w24", str(tmp_path / "run24"),
            "--sample", str(tmp_path / "sample"),
            "--observation-only", str(tmp_path / "obs1.csv"),
            "--root", str(tmp_path / "root")]


def _prepare(tmp_path: Path, monkeypatch) -> None:
    make_tables(tmp_path / "run")
    make_tables(tmp_path / "run24", seed=11)
    make_tables(tmp_path / "sample", n_d1=80, n_other=40, n_ctl=90, seed=13)
    _fake_observation_only(tmp_path / "obs1.csv", tmp_path / "run")
    # サニティ #1 / #4 の期待値は実物の表の値なので、合成の表に合わせて置き換える。
    monkeypatch.setattr(r2, "N1_PRE", 400)
    monkeypatch.setattr(r2, "N2_PRE", 359)
    tab = r2.Table(tmp_path / "run")
    st = r2.standardize(tab, tab.d1_idx(), tab.control_idx(),
                        col_liq=lambda t, i: t.plain(i, r2.SANITY4_COL),
                        col_ctl=lambda t, i: t.plain(i, r2.SANITY4_COL))
    monkeypatch.setattr(r2, "SANITY4_EXPECT", round(st.delta, 3))


def test_judge_writes_nothing_when_the_gate_is_closed(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    out = tmp_path / "out"
    (tmp_path / "root").mkdir()
    with pytest.raises(SystemExit) as e:
        r2.main(_synthetic_argv(tmp_path, out))
    assert e.value.code == 1
    assert not out.exists()


def test_judge_writes_nothing_when_the_last_verdict_is_stop(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    out = tmp_path / "out"
    _audit_record(tmp_path / "root", verdict="判定: 止める")
    with pytest.raises(SystemExit) as e:
        r2.main(_synthetic_argv(tmp_path, out))
    assert e.value.code == 1
    assert not out.exists()


def test_judge_writes_the_five_files_when_the_gate_is_open(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    out = tmp_path / "out"
    _audit_record(tmp_path / "root")
    monkeypatch.setattr(r2, "REPS", 50)      # 試験を軽くする(道具の既定は 2,000)
    assert r2.main(_synthetic_argv(tmp_path, out)) == 0
    for n in (r2.CELLS_NAME, r2.OBS_NAME, r2.BANDS_NAME, r2.SUMMARY_NAME, "MD5SUMS"):
        assert (out / n).exists(), n
    with (out / r2.CELLS_NAME).open(encoding="utf-8", newline="") as fh:
        cells = list(csv.DictReader(fh))
    assert [c["h"] for c in cells] == [str(h) for h in r2.HORIZONS]
    assert set(cells[0]) == set(r2.CELLS_HEADER)
    assert all(c["判定"] in r2.BRANCHES
               or c["判定"].startswith("検出されず(MDE = ") for c in cells)
    with (out / r2.BANDS_NAME).open(encoding="utf-8", newline="") as fh:
        bands = list(csv.DictReader(fh))
    assert len(bands) == r2.N_BANDS * len(r2.HORIZONS)
    with (out / r2.OBS_NAME).open(encoding="utf-8", newline="") as fh:
        obs = list(csv.DictReader(fh))
    assert {r["区分"] for r in obs} == {"(a)", "(b)", "(c)", "(d)", "(e)", "(e′)"}
    # (d) には「標準化する前の差」が 6 行ある(§4 の (d))
    assert sum(1 for r in obs
               if r["区分"] == "(d)" and r["内容"].startswith("標準化する前の差")) == 6
    # (e′) は対照 C の平均 ± SE(§5 の仮定の確認)
    assert sum(1 for r in obs if r["区分"] == "(e′)") == len(r2.HORIZONS)
    assert not (out / r2.STOPPED_NAME).exists()


def test_judge_refuses_an_existing_out_dir(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    out = tmp_path / "out"
    out.mkdir()
    _audit_record(tmp_path / "root")
    assert r2.main(_synthetic_argv(tmp_path, out)) == 1
    assert list(out.iterdir()) == []


def test_judge_writes_nothing_when_a_sanity_breaks(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    monkeypatch.setattr(r2, "N1_PRE", 12345)      # サニティ #1 を破る
    out = tmp_path / "out"
    _audit_record(tmp_path / "root")
    monkeypatch.setattr(r2, "REPS", 20)
    assert r2.main(_synthetic_argv(tmp_path, out)) == 1
    # §8: 表は 1 枚も書かず、`stopped.txt`(番号と検査の名前だけ)を書く
    assert sorted(p.name for p in out.iterdir()) == ["MD5SUMS", r2.STOPPED_NAME]
    text = (out / r2.STOPPED_NAME).read_text(encoding="utf-8")
    assert "#1" in text
    # 検査の名前(事前登録が書いた期待値)は出るが、**測った値は 1 つも出ない**
    assert "400" not in text and "359" not in text


def test_power_writes_no_tables_and_does_not_touch_the_gate(tmp_path, monkeypatch,
                                                            capsys):
    _prepare(tmp_path, monkeypatch)
    out = tmp_path / "out"
    # 台帳を置かない = 関門は閉じている。それでも `--power` は通る(表を書かないので)。
    assert r2.main(["--power", "--sample", str(tmp_path / "sample")]) == 0
    printed = capsys.readouterr().out
    assert "z = norm.ppf" in printed and "MDE" in printed
    assert not out.exists()
    assert not any(p.name in (r2.CELLS_NAME, r2.OBS_NAME, r2.BANDS_NAME)
                   for p in tmp_path.rglob("*"))


def test_power_and_judge_are_exclusive(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    assert r2.main(["--power", "--judge", "--out-dir", str(tmp_path / "o")]) == 2
    assert r2.main(["--sample", str(tmp_path / "sample")]) == 2


def test_out_dir_in_backtest_data_requires_the_repo_root():
    bad = r2.check_root_for_out_dir(ROOT / "backtest_data" / "x", Path("/tmp/elsewhere"))
    assert bad and "台帳" in bad[0]
    assert r2.check_root_for_out_dir(ROOT / "backtest_data" / "x", ROOT) == []
    assert r2.check_root_for_out_dir(Path("/tmp/x"), Path("/tmp/elsewhere")) == []


# =============================================================================
# 6. 実物の表(あれば)でサニティ #1〜#4 を実測する
# =============================================================================
real = pytest.mark.skipif(
    not ((FULL / "table.csv").exists() and (SAMPLE / "table.csv").exists()
         and OBS1.exists()),
    reason="実物の走行(gap60_w8 / 標本 / 1 周目の観測のみ)がこの環境に無い",
)


@real
def test_sanity_1_to_4_on_the_real_tables():
    """事前登録 §8 の #1〜#4。**真偽だけを見る**(判定の数値は 1 つも出さない)。"""
    tab = r2.Table(FULL)
    res, stop = r2.run_sanity(tab, OBS1, cells=[])
    got = {r["#"]: r for r in res}
    for i in (1, 2, 3, 4):
        assert got[i]["結果"] == "通る", f"#{i} {got[i]['詳細']}"
    assert not stop
