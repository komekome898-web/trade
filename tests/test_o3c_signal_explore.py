"""`scripts/o3c_signal_explore.py`(清算を起点とした値動きの探索段の読みの道具)の試験。

**測るもの**
  - 対照の符号付け: `r_h` = `bp_{h}m` × 相手の束の side の符号。対照行の
    `bp_{h}m_reactdir` 列は使わない(合成の表ではそこに毒 999 を入れてある)。
    mfe / mae は相手が SELL のとき入れ替わって反転すること。
  - 3 分位の境界を清算行から作り、対照にも同じ境界を当てること(own 方式)。
  - Q1(反転の割合)・Q2(平均 ± SE と差)・Q3(mfe / mae / 反転の割合)の集計の式を、
    道具の内部を使わない独立な計算と突き合わせる。
  - 単調性の語(上がる / 下がる / 単調でない)。
  - 標準化が `scripts/o3c_reaction_r2.py` の `standardize` と**同じ値**になること。
  - 出力先が既にあれば何も書かずに止まること。
  - 入力の MD5 が走行の `MD5SUMS` と食い違えば、出力を 1 枚も書かずに止まること。
  - `tables.md` に判定の語(差あり / 検出されず / 陽性 / 陰性 / 有意)が 1 つも出ないこと。

**この試験は実物の表を読まない。**すべて小さな合成の表で測る。
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location(
    "o3c_signal_explore", ROOT / "scripts" / "o3c_signal_explore.py"
)
ex = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(ex)
r2 = ex.r2

H = list(ex.HORIZONS)
N_LIQ = 60
N_CTL = 60
N_MIXED = 4
POISON = 999.0
BASE_MS = 1_700_000_000_000


# =============================================================================
# 合成の表
# =============================================================================
def _columns() -> list[str]:
    cols = ["kind", "cascade_id", "side", "time_ms", "bundle_width_ms",
            "bundle_n_events_dedup", "bundle_total_notional", "bin_pct",
            "dist_node_bp", "dist_vwap_bp", "implied_leverage", "doi_pre_1h"]
    for h in H:
        cols += [f"bp_{h}m", f"bp_{h}m_reactdir",
                 f"mfe_{h}m_reactdir", f"mae_{h}m_reactdir"]
    cols.append("matched_liq_id")
    return cols


def liq_bp(i: int, h: int) -> float:
    return float(((i * 7 + h) % 21) - 10) + h * 0.1


def ctl_bp(i: int, h: int) -> float:
    return float(((i * 5 + h) % 17) - 8) + h * 0.05


def liq_side(i: int) -> str:
    return "SELL" if i % 2 else "BUY"


def liq_sign(i: int) -> float:
    return -1.0 if liq_side(i) == "SELL" else 1.0


def _liq_row(i: int) -> dict:
    s = liq_sign(i)
    row = {
        "kind": "liq", "cascade_id": f"liq_{i:03d}", "side": liq_side(i),
        "time_ms": BASE_MS + (i % 24) * 3_600_000 + 60_000,
        "bundle_width_ms": 100 * (i + 1),
        "bundle_n_events_dedup": 1 + i % 7,
        "bundle_total_notional": 1000.0 * (i + 1),
        "bin_pct": float(i % 10),
        "dist_node_bp": float(i + 1) * 0.5 * (1 if i % 3 else -1),
        "dist_vwap_bp": -float(i + 1),
        "implied_leverage": float(5 + i % 20),
        "doi_pre_1h": -1000.0 + i * 37.0,
        "matched_liq_id": "",
    }
    for h in H:
        v = liq_bp(i, h)
        row[f"bp_{h}m"] = v
        row[f"bp_{h}m_reactdir"] = v * s
        row[f"mfe_{h}m_reactdir"] = abs(v) + 2.0
        row[f"mae_{h}m_reactdir"] = -(abs(v) + 1.0)
    return row


def _ctl_row(i: int, partner: str) -> dict:
    row = {
        "kind": "control_matched", "cascade_id": f"ctl_{i:03d}", "side": "",
        "time_ms": BASE_MS + ((i + 3) % 24) * 3_600_000 + 120_000,
        "bundle_width_ms": "", "bundle_n_events_dedup": "",
        "bundle_total_notional": "",
        "bin_pct": float((i + 3) % 10),
        "dist_node_bp": float(i + 2) * 0.4 * (1 if i % 4 else -1),
        "dist_vwap_bp": -(float(i) + 0.5),
        "implied_leverage": "",
        "doi_pre_1h": -900.0 + i * 41.0,
        "matched_liq_id": partner,
    }
    for h in H:
        v = ctl_bp(i, h)
        row[f"bp_{h}m"] = v
        row[f"bp_{h}m_reactdir"] = POISON           # 毒(使ってはいけない列)
        row[f"mfe_{h}m_reactdir"] = abs(v) + 2.0    # sign = +1 で入っている上向き
        row[f"mae_{h}m_reactdir"] = -(abs(v) + 1.0)  # 同 下向き
    return row


def write_run(d: Path, *, break_md5: bool = False) -> None:
    """1 走行ぶんの `table.csv` / `table_mixed.csv` / `MD5SUMS` を書く。"""
    d.mkdir(parents=True, exist_ok=True)
    cols = _columns()
    rows = [_liq_row(i) for i in range(N_LIQ)]
    rows += [_ctl_row(i, f"liq_{i:03d}") for i in range(N_CTL)]
    # 相手が混在の束の対照(落とされるはず)
    rows += [_ctl_row(N_CTL + j, f"mix_{j:03d}") for j in range(N_MIXED)]
    with (d / "table.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with (d / "table_mixed.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["kind", "cascade_id", "side"])
        w.writeheader()
        for j in range(N_MIXED):
            w.writerow({"kind": "liq", "cascade_id": f"mix_{j:03d}", "side": "BUY"})
    lines = []
    for name in ("table.csv", "table_mixed.csv"):
        h = hashlib.md5((d / name).read_bytes()).hexdigest()
        if break_md5 and name == "table.csv":
            h = "0" * 32
        lines.append(f"{h}  {name}")
    (d / "MD5SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_runs_dir(base: Path, *, break_md5_on: str | None = None) -> Path:
    for name in ex.ALL_RUNS:
        write_run(base / name, break_md5=(break_md5_on == name))
    return base


@pytest.fixture()
def runs_dir(tmp_path: Path) -> Path:
    return write_runs_dir(tmp_path / "runs")


@pytest.fixture()
def main_run(runs_dir: Path) -> "ex.Run":
    return ex.Run(runs_dir / ex.MAIN_RUN, full=True)


# =============================================================================
# 1. 対照の符号付け
# =============================================================================
def test_control_uses_partner_side_sign(main_run):
    run = main_run
    assert run.n_liq_rows == N_LIQ
    assert run.n_mat_rows == N_CTL + N_MIXED
    assert run.n_mat_dropped_mixed == N_MIXED
    assert int(run.ctl_i.size) == N_CTL
    assert run.n_partner_missing == 0
    for h in H:
        got = run.r_ctl[h]
        want = np.array([ctl_bp(i, h) * liq_sign(i) for i in range(N_CTL)])
        assert np.allclose(got, want)
        # 毒の列(`bp_{h}m_reactdir` = 999)を使っていない
        assert not np.any(np.isclose(np.abs(got), POISON))


def test_control_mfe_mae_swap_on_sell(main_run):
    run = main_run
    for h in H:
        for i in range(N_CTL):
            v = ctl_bp(i, h)
            mfe0, mae0 = abs(v) + 2.0, -(abs(v) + 1.0)
            if liq_side(i) == "SELL":
                want_mfe, want_mae = -mae0, -mfe0
            else:
                want_mfe, want_mae = mfe0, mae0
            assert run.mfe_ctl[h][i] == pytest.approx(want_mfe)
            assert run.mae_ctl[h][i] == pytest.approx(want_mae)
            assert run.mfe_ctl[h][i] >= run.mae_ctl[h][i]


def test_liquidation_side_and_partner_attributes(main_run):
    run = main_run
    # 対照の side は相手の束の side
    assert list(run.side_ctl) == [liq_side(i) for i in range(N_CTL)]
    # 対照に列が無い属性は相手の束の値
    assert np.allclose(run.attr_ctl["bundle_total_notional"],
                       [1000.0 * (i + 1) for i in range(N_CTL)])
    assert np.allclose(run.attr_ctl["implied_leverage"],
                       [float(5 + i % 20) for i in range(N_CTL)])
    # 対照にも列がある属性はその行自身の値
    assert np.allclose(run.attr_ctl["bin_pct"],
                       [float((i + 3) % 10) for i in range(N_CTL)])


# =============================================================================
# 2. 3 分位の境界と own 方式
# =============================================================================
def test_tertile_cuts_come_from_liquidation_rows(main_run):
    run = main_run
    name = "bin_pct"
    vl = run.attr_liq[name]
    vc = run.attr_ctl[name]
    lo, hi = ex.tertile_cuts(vl)
    want = np.nanpercentile(vl[np.isfinite(vl)], [100.0 / 3.0, 200.0 / 3.0])
    assert (lo, hi) == pytest.approx(tuple(float(x) for x in want))
    # 対照の切り値は対照自身の分位ではなく、清算行の切り値である
    lo_c, hi_c = ex.tertile_cuts(vc)
    groups = [g for g in ex.attribute_groups(run) if g["属性"] == name]
    assert len(groups) == 3
    m1 = groups[0]["mask_ctl"]
    assert np.array_equal(m1, (vc <= lo) & np.isfinite(vc))
    if not math.isclose(lo, lo_c):
        assert not np.array_equal(m1, (vc <= lo_c) & np.isfinite(vc))
    # 3 つの群は清算行を漏れなく重複なく分ける(有限な行について)
    cover = groups[0]["mask_liq"] | groups[1]["mask_liq"] | groups[2]["mask_liq"]
    assert np.array_equal(cover, np.isfinite(vl))
    assert int(np.sum(groups[0]["mask_liq"] & groups[1]["mask_liq"])) == 0
    assert int(np.sum(groups[1]["mask_liq"] & groups[2]["mask_liq"])) == 0


def test_tertile_mask_boundaries():
    v = np.array([1.0, 2.0, 3.0, 4.0, float("nan")])
    lo, hi = 2.0, 3.0
    assert list(ex.tertile_mask(v, lo, hi, 1)) == [True, True, False, False, False]
    assert list(ex.tertile_mask(v, lo, hi, 2)) == [False, False, True, False, False]
    assert list(ex.tertile_mask(v, lo, hi, 3)) == [False, False, False, True, False]


def test_hour_bands(main_run):
    run = main_run
    groups = [g for g in ex.attribute_groups(run) if g["属性"] == ex.ATTR_HOUR]
    assert len(groups) == 4
    total = sum(int(np.sum(g["mask_liq"])) for g in groups)
    assert total == N_LIQ
    want_h0 = np.array([(BASE_MS + (i % 24) * 3_600_000 + 60_000) // 3_600_000 % 24
                        for i in range(N_LIQ)])
    assert np.allclose(run.hour_liq, want_h0)


# =============================================================================
# 3. Q1 / Q2 / Q3 の集計の式
# =============================================================================
def A(x):
    """表の文字列は 6 桁で丸めてあるので、その桁で突き合わせる。"""
    return pytest.approx(x, abs=1e-6)


def _hand_mean_se(v: np.ndarray) -> tuple[int, float, float]:
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    n = v.size
    m = v.mean()
    se = v.std(ddof=1) / math.sqrt(n)
    return n, float(m), float(se)


def test_q1_direction_formula(main_run):
    run = main_run
    over = ex.overall_group(run)
    rows = ex.build_q1(run, [over])
    assert len(rows) == len(H)
    for row in rows:
        h = row["h"]
        a = np.array([liq_bp(i, h) * liq_sign(i) for i in range(N_LIQ)])
        b = np.array([ctl_bp(i, h) * liq_sign(i) for i in range(N_CTL)])
        p1 = float((a < 0).mean())
        p2 = float((b < 0).mean())
        assert float(row["反転の割合(清算)"]) == A(p1)
        assert float(row["反転の割合(対照)"]) == A(p2)
        assert float(row["差(清算 − 対照)"]) == A(p1 - p2)
        assert float(row["SE(清算)"]) == A(math.sqrt(p1 * (1 - p1) / N_LIQ))
        assert int(row["n(清算)"]) == N_LIQ
        assert int(row["n(対照)"]) == N_CTL


def test_q2_size_formula(main_run):
    run = main_run
    groups = [g for g in ex.attribute_groups(run) if g["属性"] == "bin_pct"]
    rows = ex.build_q2(run, groups)
    assert len(rows) == 3 * len(H)
    g0 = groups[0]
    idx_l = np.flatnonzero(g0["mask_liq"])
    idx_c = np.flatnonzero(g0["mask_ctl"])
    for row in rows:
        if row["群"] != g0["群"]:
            continue
        h = row["h"]
        n1, m1, s1 = _hand_mean_se([liq_bp(i, h) * liq_sign(i) for i in idx_l])
        n2, m2, s2 = _hand_mean_se([ctl_bp(i, h) * liq_sign(i) for i in idx_c])
        assert int(row["n(清算)"]) == n1
        assert int(row["n(対照)"]) == n2
        assert float(row["平均bp(清算)"]) == A(m1)
        assert float(row["平均bp(対照)"]) == A(m2)
        assert float(row["SE(清算)"]) == A(s1)
        assert float(row["差(清算 − 対照)"]) == A(m1 - m2)
        assert float(row["SE(差)"]) == A(math.sqrt(s1 ** 2 + s2 ** 2))


def test_q3_horizon_shape_formula(main_run):
    run = main_run
    rows = ex.build_q3(run, [ex.overall_group(run)], ex.MAIN_RUN)
    assert len(rows) == 2 * len(H)
    for row in rows:
        h = row["h"]
        if row["区分"] == "清算":
            rv = np.array([liq_bp(i, h) * liq_sign(i) for i in range(N_LIQ)])
            mfe = np.array([abs(liq_bp(i, h)) + 2.0 for i in range(N_LIQ)])
            mae = np.array([-(abs(liq_bp(i, h)) + 1.0) for i in range(N_LIQ)])
        else:
            rv = np.array([ctl_bp(i, h) * liq_sign(i) for i in range(N_CTL)])
            mfe = np.array([(abs(ctl_bp(i, h)) + 1.0) if liq_side(i) == "SELL"
                            else (abs(ctl_bp(i, h)) + 2.0) for i in range(N_CTL)])
            mae = np.array([-(abs(ctl_bp(i, h)) + 2.0) if liq_side(i) == "SELL"
                            else -(abs(ctl_bp(i, h)) + 1.0) for i in range(N_CTL)])
        n, m, se = _hand_mean_se(rv)
        assert int(row["n"]) == n
        assert float(row["平均bp"]) == A(m)
        assert float(row["SE(平均)"]) == A(se)
        assert float(row["mfe平均"]) == A(mfe.mean())
        assert float(row["mae平均"]) == A(mae.mean())
        assert float(row["反転の割合"]) == A(float((rv < 0).mean()))


def test_d1_group_is_lowest_tertile_of_doi(main_run):
    run = main_run
    g = ex.d1_group(run)
    vl = run.attr_liq["doi_pre_1h"]
    lo, _hi = ex.tertile_cuts(vl)
    assert np.array_equal(g["mask_liq"], (vl <= lo) & np.isfinite(vl))
    vc = run.attr_ctl["doi_pre_1h"]
    assert np.array_equal(g["mask_ctl"], (vc <= lo) & np.isfinite(vc))


# =============================================================================
# 4. 単調性の語
# =============================================================================
def test_monotone_word():
    assert ex.monotone_word([1.0, 2.0, 3.0]) == ex.MONO_UP
    assert ex.monotone_word([3.0, 2.0, 1.0]) == ex.MONO_DOWN
    assert ex.monotone_word([1.0, 3.0, 2.0]) == ex.MONO_NONE
    assert ex.monotone_word([1.0, 1.0, 1.0]) == ex.MONO_NONE
    assert ex.monotone_word([1.0, 2.0, float("nan")]) == ex.MONO_UNKNOWN
    assert ex.monotone_word([1.0, 2.0]) == ex.MONO_UNKNOWN


def test_q2_monotone_column_matches_the_three_group_means(main_run):
    run = main_run
    groups = [g for g in ex.attribute_groups(run) if g["属性"] == "bin_pct"]
    rows = ex.build_q2(run, groups)
    for h in H:
        got = [r for r in rows if r["h"] == h]
        means = [float(r["平均bp(清算)"]) for r in
                 sorted(got, key=lambda r: r["群"])]
        word = ex.monotone_word(means)
        assert {r["単調性(清算の平均)"] for r in got} == {word}


def test_q2_monotone_is_not_applicable_for_side(main_run):
    run = main_run
    groups = [g for g in ex.attribute_groups(run) if g["属性"] == ex.ATTR_SIDE]
    rows = ex.build_q2(run, groups)
    assert {r["単調性(清算の平均)"] for r in rows} == {ex.MONO_NA}


# =============================================================================
# 5. 標準化が `o3c_reaction_r2.standardize` と同じ値になる
# =============================================================================
class _Shim:
    """`r2.standardize` に渡すための最小の入れ物(距離と値だけを持つ)。"""

    def __init__(self, dist: np.ndarray, vals: np.ndarray):
        self._d = dist
        self._v = vals

    def dist(self, idx, col="dist_vwap_bp"):
        return self._d[idx]


def test_standardized_diff_equals_r2_standardize(main_run):
    run = main_run
    over = ex.overall_group(run)
    d1 = run.dist_liq[over["mask_liq"]]
    d2 = run.dist_ctl[over["mask_ctl"]]
    for h in H:
        v1 = run.r_liq[h][over["mask_liq"]]
        v2 = run.r_ctl[h][over["mask_ctl"]]
        st, se, edges = ex.standardized_diff(v1, d1, v2, d2)

        shim = _Shim(np.concatenate([d1, d2]), np.concatenate([v1, v2]))
        i1 = np.arange(d1.size)
        i2 = np.arange(d1.size, d1.size + d2.size)
        st_r2 = r2.standardize(shim, i1, i2,
                               col_liq=lambda t, i: t._v[i],
                               col_ctl=lambda t, i: t._v[i],
                               edges=edges)
        assert st.delta == pytest.approx(st_r2.delta, nan_ok=True)
        assert st.mean_d1 == pytest.approx(st_r2.mean_d1, nan_ok=True)
        assert st.mean_c == pytest.approx(st_r2.mean_c, nan_ok=True)
        assert st.n1 == st_r2.n1 and st.n2 == st_r2.n2
        # SE は帯の重みを固定した解析式(手計算と突き合わせる)
        var = 0.0
        for k in range(r2.N_BANDS):
            a, b = st.parts1[k], st.parts2[k]
            var += st.w[k] ** 2 * (a.var(ddof=1) / a.size + b.var(ddof=1) / b.size)
        assert se == pytest.approx(math.sqrt(var))


def test_standardized_edges_come_from_liquidation_rows(main_run):
    run = main_run
    over = ex.overall_group(run)
    d1 = run.dist_liq[over["mask_liq"]]
    _st, _se, edges = ex.standardized_diff(
        run.r_liq[1][over["mask_liq"]], d1,
        run.r_ctl[1][over["mask_ctl"]], run.dist_ctl[over["mask_ctl"]])
    assert edges == r2.band_edges(d1)
    assert r2.edges_strictly_increasing(edges)


# =============================================================================
# 6. 止まるところ
# =============================================================================
def test_stops_when_out_dir_exists(runs_dir: Path, tmp_path: Path):
    out = tmp_path / "already"
    out.mkdir()
    before = sorted(p.name for p in out.iterdir())
    assert ex.run_all(runs_dir, out) == 1
    assert sorted(p.name for p in out.iterdir()) == before == []


def test_stops_when_input_md5_does_not_match(tmp_path: Path):
    runs = write_runs_dir(tmp_path / "runs", break_md5_on=ex.MAIN_RUN)
    out = tmp_path / "out"
    with pytest.raises(SystemExit):
        ex.run_all(runs, out)
    assert not out.exists()


def test_check_banned_raises():
    with pytest.raises(SystemExit):
        ex.check_banned("この行には 差あり と書いてある", "試験")


# =============================================================================
# 7. 通しで走らせる
# =============================================================================
def test_end_to_end(runs_dir: Path, tmp_path: Path):
    out = tmp_path / "out"
    assert ex.run_all(runs_dir, out) == 0
    names = [ex.Q1_NAME, ex.Q2_NAME, ex.Q3_NAME, ex.SENS_NAME, ex.STD_NAME,
             ex.SUMMARY_NAME, ex.TABLES_NAME, "MD5SUMS"]
    for n in names:
        assert (out / n).exists(), n

    # MD5SUMS が実物と合う
    for line in (out / "MD5SUMS").read_text(encoding="utf-8").splitlines():
        h, _, name = line.partition("  ")
        assert hashlib.md5((out / name).read_bytes()).hexdigest() == h

    # 行数(属性の数 × 群の数 × h)
    def rows(name):
        with (out / name).open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    n_groups = len(ex.ATTRS_NUM) * 3 + 2 + len(ex.HOUR_BANDS)
    assert len(rows(ex.Q1_NAME)) == (1 + n_groups) * len(H)
    assert len(rows(ex.Q2_NAME)) == n_groups * len(H)
    assert len(rows(ex.Q3_NAME)) == 2 * 2 * len(H)        # 全体 + D1 相当、清算 / 対照
    assert len(rows(ex.SENS_NAME)) == len(ex.SENSITIVITY_RUNS) * 2 * len(H)
    assert len(rows(ex.STD_NAME)) == (1 + n_groups) * len(H)

    # 判定の語が 1 つも出ない(全部の出力について見る)
    for n in names:
        text = (out / n).read_text(encoding="utf-8")
        for w in ex.BANNED_WORDS:
            assert w not in text, f"{n} に {w}"


def test_tables_md_has_no_verdict_words(runs_dir: Path, tmp_path: Path):
    out = tmp_path / "out"
    assert ex.run_all(runs_dir, out) == 0
    text = (out / ex.TABLES_NAME).read_text(encoding="utf-8")
    for w in ("差あり", "検出されず", "陽性", "陰性", "有意"):
        assert w not in text
    # 表そのものは出ている
    assert "Q1 向き" in text and "Q3 時間軸" in text


def test_summary_records_inputs_and_missing(runs_dir: Path, tmp_path: Path):
    import json
    out = tmp_path / "out"
    assert ex.run_all(runs_dir, out) == 0
    s = json.loads((out / ex.SUMMARY_NAME).read_text(encoding="utf-8"))
    assert set(s["入力の MD5"]) == set(ex.ALL_RUNS)
    for name in ex.ALL_RUNS:
        got = hashlib.md5((runs_dir / name / "table.csv").read_bytes()).hexdigest()
        assert s["入力の MD5"][name]["table.csv"] == got
    assert s["件数(主の走行)"]["清算行"] == N_LIQ
    assert s["件数(主の走行)"]["対照行(使った)"] == N_CTL
    assert s["件数(主の走行)"]["相手が mixed で落とした対照行"] == N_MIXED
    assert "欠測(主の走行)" in s
    assert s["表に列が無いので作らなかった属性"] == ["recent_volatility"]
