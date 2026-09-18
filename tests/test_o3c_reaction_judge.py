"""段 A の結果の読み(`scripts/o3c_reaction_judge.py`)の試験。

**判定区間を開ける前に書いた。**合成データだけで測る(判定区間の出力は 1 度も開かない)。

測るもの:
  1. 分岐(不明(n < 30) / 差あり(+)(−) / 検出されず)が合成データで正しく出ること
  2. §9.1 のブートストラップが**日クラスタ**で引いていること(種を固定すれば再現すること)
  3. §4.3 の 576 行がちょうど出ること(群 48 × 系統 2 × h 6)
  4. §4 の内訳表どおり、W に依らない 12 群が W = 8h の走行からだけ 576 に入ること
     (W = 24h 側の同じ 12 群は観測のみの表に出ること)
  5. 関門が閉じていると表を 1 枚も書かないこと
  6. 禁じた語(予測できる / 使える / 有効 / 差なし / 陰性)が出力に 1 つも無いこと

**走行前の再監査で決めた 7 点**もここで測る(どの試験がどれを測るかは各試験の docstring)。
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location(
    "o3c_reaction_judge", ROOT / "scripts" / "o3c_reaction_judge.py"
)
judge = importlib.util.module_from_spec(_spec)
sys.modules["o3c_reaction_judge"] = judge
_spec.loader.exec_module(judge)

H = judge.HORIZONS


# --------------------------------------------------------------------------
# 合成データ
# --------------------------------------------------------------------------
def _columns() -> list[str]:
    cols = [
        "kind", "day", "cascade_id", "side", "direction",
        "bin_pct", "dist_node_bp_liqdir", "dist_vwap_bp_liqdir",
        "oi_dist_node_bp_liqdir", "oi_dist_vwap_bp_liqdir", "implied_leverage",
        "bundle_n_events_dedup", "bundle_total_qty_accum",
        "doi_pre_1h", "doi_pre_4h", "doi_in",
        "reach_back_vwap_sec", "reach_back_node_sec",
        "reach_node_up_sec", "reach_node_dn_sec",
    ]
    for h in H:
        cols += [f"bp_{h}m", f"bp_{h}m_reactdir", f"mfe_{h}m_reactdir",
                 f"mae_{h}m_reactdir", f"doi_post_{h}m",
                 f"reach_back_vwap_{h}m", f"reach_back_node_{h}m",
                 f"reach_node_up_{h}m", f"reach_node_dn_{h}m"]
    return cols


LIQ_ONLY = ("side", "dist_node_bp_liqdir", "dist_vwap_bp_liqdir",
            "oi_dist_node_bp_liqdir", "oi_dist_vwap_bp_liqdir",
            "implied_leverage", "bundle_n_events_dedup", "bundle_total_qty_accum")


def _row(kind, day, cid, side, d, i, reach) -> dict:
    r = {"kind": kind, "day": day, "cascade_id": cid, "side": side,
         "direction": "down" if side == "SELL" else ("up" if side == "BUY" else "none"),
         "bin_pct": (i * 7) % 90,
         "doi_pre_1h": ((i % 7) - 3) * 1000.0,
         "doi_pre_4h": ((i % 5) - 2) * 1000.0,
         "doi_in": ((i % 3) - 1) * 100.0,
         "reach_back_vwap_sec": 100.0 + i, "reach_back_node_sec": 120.0 + i,
         "reach_node_up_sec": 140.0 + i, "reach_node_dn_sec": 160.0 + i}
    if kind == "liq":
        r.update({"dist_node_bp_liqdir": (i % 11) - 5, "dist_vwap_bp_liqdir": (i % 13) - 6,
                  "oi_dist_node_bp_liqdir": (i % 9) - 4,
                  "oi_dist_vwap_bp_liqdir": (i % 17) - 8,
                  "implied_leverage": 1.0 + (i % 19),
                  "bundle_n_events_dedup": 1 + (i % 5),
                  "bundle_total_qty_accum": 10.0 + (i % 13)})
    else:
        for c in LIQ_ONLY:
            r[c] = ""
    for h in H:
        v = reach(kind, d, i, h)
        r[f"reach_back_vwap_{h}m"] = v
        r[f"reach_back_node_{h}m"] = v
        r[f"bp_{h}m"] = 1.0 + (i % 3)
        r[f"bp_{h}m_reactdir"] = 1.0 + (i % 3)
        r[f"mfe_{h}m_reactdir"] = 2.0 + (i % 3)
        r[f"mae_{h}m_reactdir"] = -1.0 - (i % 3)
        r[f"doi_post_{h}m"] = 100.0 * (i % 4)
        r[f"reach_node_up_{h}m"] = (i + h) % 2
        r[f"reach_node_dn_{h}m"] = (i + h + 1) % 2
    return r


def make_run(path: Path, *, days: int, per_day: int, reach, window_hours: int = 8,
             n_buy: int = 10_000) -> Path:
    """合成の走行ディレクトリを作る。

    `reach(kind, day_i, row_i, h)` が戻り到達 2 系統の 0/1 を返す。
    `n_buy` は BUY の束の数の上限(C_BUY の束の数を 30 未満にするために使う)。
    """
    path.mkdir(parents=True, exist_ok=True)
    cols = _columns()
    rows: list[dict] = []
    cid = 0
    buy_left = n_buy
    for d in range(days):
        day = f"2024-{1 + d // 28:02d}-{1 + d % 28:02d}"
        for i in range(per_day):
            side = "BUY" if (i % 2 == 0 and buy_left > 0) else "SELL"
            buy_left -= 1 if side == "BUY" else 0
            rows.append(_row("liq", day, f"binance_cm_real_{cid:06d}", side, d, i, reach))
            cid += 1
        for i in range(per_day):
            rows.append(_row("control_uniform", day,
                             f"control_uniform_{day}_{i:05d}", "", d, i, reach))
            rows.append(_row("control_matched", day,
                             f"control_matched_{day}_{i:05d}", "", d, i, reach))
    with (path / "table.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    with (path / "table_mixed.csv").open("w", encoding="utf-8", newline="") as fh:
        csv.DictWriter(fh, fieldnames=cols).writeheader()
    (path / "summary.json").write_text(
        json.dumps({"params": {"window_hours": window_hours, "gap_ms": 60000}}),
        encoding="utf-8")
    return path


def open_gate(root: Path) -> Path:
    """関門を通す台帳を作る(試験用。`--root` で差し替える)。"""
    log = root / "docs" / "AUDITOR" / "ACTION_LOG.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"> 指摘の本文 {i} 行目。これは監査役が書いた文である。" for i in range(1, 10))
    log.write_text(f"## 試験\n\n監査対象: {judge.UNIT}/結果\n**監査役**: `owner-auditor`\n\n"
                   f"{body}\n\n判定: 通す\n", encoding="utf-8")
    return root


# --- 4 分岐を出すための反応の作り方 ---------------------------------------
def reach_four_branches(kind, d, i, h):
    if h == 5:        # 差あり(+): 実群はほぼ 1、対照はほぼ 0
        if kind == "liq":
            return 0 if d == 0 else 1
        if kind == "control_matched":
            return 1 if d == 1 else 0
        return 0
    if h == 240:      # 差あり(−): 向きを逆にしただけ
        if kind == "liq":
            return 1 if d == 0 else 0
        if kind == "control_matched":
            return 0 if d == 1 else 1
        return 0
    if h == 15:       # 検出されず: 日でまとまった 0.6 対 0.5(差 0.1 ≥ MDE だが |t| は小さい)
        if kind == "liq":
            return 1 if d < 36 else 0
        if kind == "control_matched":
            return 1 if d < 30 else 0
        return 0
    # h = 1 / 30 / 60 → 検出されず(差 0 < MDE)
    return i % 2


def run_judge(tmp_path: Path, *, reach=reach_four_branches, reps=500,
              w24_reach=None, days=60, per_day=40, n_buy=10_000, root=None,
              out=None, seed=1):
    r8 = make_run(tmp_path / "run_w8", days=days, per_day=per_day, reach=reach,
                  window_hours=8, n_buy=n_buy)
    r24 = make_run(tmp_path / "run_w24", days=days, per_day=per_day,
                   reach=w24_reach or reach, window_hours=24, n_buy=n_buy)
    out = out or (tmp_path / "out")
    root = root if root is not None else open_gate(tmp_path / "root")
    code = judge.main([
        "--run-w8", str(r8), "--run-w24", str(r24),
        "--sample-w8", str(r8), "--sample-w24", str(r24),
        "--out-dir", str(out), "--root", str(root), "--reps", str(reps),
        "--seed", str(seed),
    ])
    return code, out


def read_rows(out: Path, name="judgment_576.csv") -> list[dict]:
    return list(csv.DictReader((out / name).open(encoding="utf-8", newline="")))


# ==========================================================================
# 1. 4 分岐
# ==========================================================================
def test_decide_has_exactly_three_branches_in_order():
    """**決定 2**: 分岐は 3 つ。上から順に当てる(純関数として測る)。"""
    # (1) 欠測を引いた後の実群 n < 30 は t や差によらず「不明(n < 30)」
    assert judge.decide(29, 99.0, 0.7, 0.01) == ("不明(n < 30)", "n < 30")
    # (2) |t| ≥ 3.925 → 差あり(符号つき)
    assert judge.decide(100, 4.0, 0.5, 0.01)[0] == "差あり(+)"
    assert judge.decide(100, -4.0, -0.5, 0.01)[0] == "差あり(−)"
    # バーの直下は差ありにしない
    assert judge.decide(100, 3.9, 0.5, 0.01)[0].startswith("検出されず")
    # (3) それ以外 → 検出されず(MDE を必ず書く)
    assert judge.decide(100, 1.0, 0.005, 0.01)[0] == "検出されず(MDE = 0.010000)"
    assert judge.decide(100, 1.0, 0.05, 0.01)[0] == "検出されず(MDE = 0.010000)"
    assert judge.decide(100, 1.0, 0.05, float("nan"))[0] == "検出されず(MDE = 未算出)"
    # 「差なし」「陰性」は 1 つも出さない
    for args in [(29, 99.0, 0.7, 0.01), (100, 4.0, 0.5, 0.01), (100, 1.0, 0.05, 0.01)]:
        assert "差なし" not in judge.decide(*args)[0]
        assert "陰性" not in judge.decide(*args)[0]


def test_ci_is_the_normal_approximation_and_matches_the_t_bar():
    """**決定 1**: CI = 差 ± 3.925 × SE。|t| ≥ 3.925 と CI が 0 を除外は同値。"""
    lo, hi = judge.ci_normal(1.0, 0.2)          # t = 5.0
    assert abs(lo - (1.0 - 3.925 * 0.2)) < 1e-12
    assert abs(hi - (1.0 + 3.925 * 0.2)) < 1e-12
    assert lo > 0                                # 0 を除外
    lo, hi = judge.ci_normal(1.0, 0.3)          # t = 3.33 < 3.925
    assert lo < 0 < hi                           # 0 をまたぐ


def test_three_branches_come_out_on_synthetic_data(tmp_path):
    """合成データで 3 分岐(と両方の符号)が出ること。"""
    code, out = run_judge(tmp_path, n_buy=20)   # BUY は 20 束 = C_BUY が n < 30
    assert code == 0
    rows = read_rows(out)
    by = {(r["観測量"], r["群"], r["h"]): r for r in rows}

    v = by[("reach_back_vwap_5m", "全体", "5")]
    assert v["判定"] == "差あり(+)", v
    assert abs(float(v["t"])) >= judge.BAR_T and float(v["CI下限"]) > 0

    v = by[("reach_back_vwap_240m", "全体", "240")]
    assert v["判定"] == "差あり(−)", v
    assert float(v["CI上限"]) < 0

    v = by[("reach_back_vwap_15m", "全体", "15")]
    assert v["判定"].startswith("検出されず"), v
    assert v["MDEとの比較"] == "≥" and abs(float(v["t"])) < judge.BAR_T

    v = by[("reach_back_vwap_1m", "全体", "1")]
    assert v["判定"].startswith("検出されず") and v["MDEとの比較"] == "<", v

    buy = [r for r in rows if r["群"] == "C_BUY"]
    assert len(buy) == 12
    assert {r["判定"] for r in buy} == {"不明(n < 30)"}
    assert {r["検出力"] for r in buy} == {"n < 30"}


def test_n_under_30_is_measured_on_the_liq_rows_left_after_missing(tmp_path):
    """**決定 2 の (1)**: n < 30 は群の束の数ではなく、その検定の実群 n1 で当てる。"""
    def mostly_missing(kind, d, i, h):
        if h == 1 and kind == "liq" and i >= 1:
            return ""            # 全体群の束は 2,400 だが h=1 の実群 n1 は 60
        return i % 2

    code, out = run_judge(tmp_path, reach=mostly_missing, reps=100, days=20, per_day=40)
    assert code == 0
    rows = {(r["観測量"], r["群"]): r for r in read_rows(out)}
    v = rows[("reach_back_vwap_1m", "全体")]
    assert int(v["n1"]) == 20 and v["判定"] == "不明(n < 30)" and v["検出力"] == "n < 30"
    # 同じ群でも欠測の無い h では n1 が大きく、n < 30 にならない
    v2 = rows[("reach_back_vwap_5m", "全体")]
    assert int(v2["n1"]) == 800 and v2["判定"] != "不明(n < 30)"


def test_tertile_cuts_follow_the_rule(tmp_path):
    """**決定 3**: nanpercentile [100/3, 200/3]、同点は下側、欠測はどの群にも入れない。"""
    import numpy as np
    vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, np.nan])
    lo, hi = judge.tertile_cuts(vals)
    assert (lo, hi) == tuple(np.nanpercentile(vals[:6], [100 / 3, 200 / 3]))
    # 同点は `<=` で下側
    assert judge._quantile_label(lo, (lo, hi)) == 1
    assert judge._quantile_label(hi, (lo, hi)) == 2
    # 欠測はどの群にも入れない(0 = どの分位でもない)
    assert judge._quantile_label(float("nan"), (lo, hi)) == 0
    # 切り値 2 つが等しければ中の群は空になる
    assert judge._quantile_label(5.0, (5.0, 5.0)) == 1
    assert judge._quantile_label(6.0, (5.0, 5.0)) == 3
    assert judge._quantile_label(5.0, (float("nan"), float("nan"))) == 0


def test_empty_groups_are_still_written_as_rows(tmp_path):
    """**決定 3**: 空の群も 576 行に出す(不明(n < 30) として)。"""
    def one_value(kind, d, i, h):
        return i % 2

    # 1 日 1 束にすると軸の値が全部同じになり、切り値 2 つが等しくなる = 中の群が空になる
    code, out = run_judge(tmp_path, reach=one_value, reps=50, days=10, per_day=1)
    assert code == 0
    rows = read_rows(out)
    assert len(rows) == 576
    empty = [r for r in rows if int(r["n1"]) == 0]
    assert empty, "空の群が 1 つも無いので、この試験は空の群を測れていない"
    assert {r["判定"] for r in empty} == {"不明(n < 30)"}


def test_mde_takes_alpha_directly_and_uses_the_sample_p_and_s():
    """**決定 4**: α を直接渡す。p・s は渡した標本の行から取り、n は走行後の件数。"""
    import numpy as np
    a = np.array([1.0] * 30 + [0.0] * 70)      # p1 = 0.30
    b = np.array([1.0] * 20 + [0.0] * 80)      # p2 = 0.20
    got = judge.mde("prop", a, b, 1000, 1000, alpha=judge.ALPHA)
    want = judge.MDE_Z * (0.3 * 0.7 / 1000 + 0.2 * 0.8 / 1000) ** 0.5
    assert abs(got - want) < 1e-12
    # α を緩めれば MDE は小さくなる(倍率で読み替えていないこと)
    assert judge.mde("prop", a, b, 1000, 1000, alpha=0.05) < got
    # n は走行後の件数なので、n を増やせば MDE は小さくなる(p・s は変えない)
    assert judge.mde("prop", a, b, 4000, 4000, alpha=judge.ALPHA) < got


# ==========================================================================
# 2. ブートストラップ(日クラスタ・種の固定)
# ==========================================================================
def test_bootstrap_is_reproducible_with_the_same_seed(tmp_path):
    code1, out1 = run_judge(tmp_path / "a", reps=300, seed=1)
    code2, out2 = run_judge(tmp_path / "b", reps=300, seed=1)
    assert code1 == 0 and code2 == 0
    h1 = hashlib.md5((out1 / "judgment_576.csv").read_bytes()).hexdigest()
    h2 = hashlib.md5((out2 / "judgment_576.csv").read_bytes()).hexdigest()
    assert h1 == h2
    # 種を変えれば引き方が変わる(実際に引いていることの確認)
    _, out3 = run_judge(tmp_path / "c", reps=300, seed=2)
    h3 = hashlib.md5((out3 / "judgment_576.csv").read_bytes()).hexdigest()
    assert h3 != h1


def test_bootstrap_clusters_by_day_not_by_row(tmp_path):
    """同じ行の集まりでも、値が**日でまとまっている**方が |t| は小さくなる。

    行ごとに引いていたら 2 つの走行の |t| はほぼ同じになる。日で引いているので、
    まとまっている方は標準誤差が大きくなり、|t| がはっきり小さくなる。
    """
    def clustered(kind, d, i, h):          # 日ごとに 0 か 1(日でまとまっている)
        if kind == "liq":
            return 1 if d < 36 else 0
        if kind == "control_matched":
            return 1 if d < 30 else 0
        return 0

    def spread(kind, d, i, h):             # 同じ割合を全部の日に散らす
        if kind == "liq":
            return 1 if i < 24 else 0      # 40 行中 24 行 = 0.6
        if kind == "control_matched":
            return 1 if i < 20 else 0      # 40 行中 20 行 = 0.5
        return 0

    _, out_c = run_judge(tmp_path / "c", reach=clustered, reps=500)
    _, out_s = run_judge(tmp_path / "s", reach=spread, reps=500)

    def pick(o):
        return next(r for r in read_rows(o)
                    if r["観測量"] == "reach_back_vwap_1m" and r["群"] == "全体")

    rc, rs = pick(out_c), pick(out_s)
    assert abs(float(rc["差(ii)"]) - 0.1) < 1e-9
    assert abs(float(rs["差(ii)"]) - 0.1) < 1e-9
    assert abs(float(rc["t"])) < abs(float(rs["t"])) / 2.0, (rc["t"], rs["t"])


# ==========================================================================
# 3. 576 行
# ==========================================================================
def test_the_judgment_table_has_exactly_576_rows(tmp_path):
    code, out = run_judge(tmp_path, reps=200)
    assert code == 0
    rows = read_rows(out)
    assert len(rows) == 576 == judge.N_TESTS
    assert len({r["群"] for r in rows}) == 48 == judge.N_GROUPS
    assert len({r["観測量"] for r in rows}) == 12          # 2 系統 × h 6
    assert {r["h"] for r in rows} == {str(h) for h in H}
    # 群ごとに 2 系統 × h 6 = 12 行ちょうど
    assert set(Counter(r["群"] for r in rows).values()) == {12}
    # 列の順(§10.1)
    assert list(rows[0].keys()) == judge.JUDGE_HEADER
    # §10.2: 観測のみの表には t と 判定 の列を置かない
    obs = read_rows(out, "observation_only.csv")
    assert "t" not in obs[0] and "判定" not in obs[0]
    assert list(obs[0].keys()) == judge.OBS_HEADER
    # 48 群 × 観測 43 系統 + 決定 6 の W24h 側 12 群 × 判定 12 系統
    assert len(obs) == 43 * 48 + 12 * 12
    # 前進到達はどちらの表にも入れない(§4.3)
    assert not [r for r in rows + obs if "fwd" in r["観測量"]]


def test_f1_reading_counts_the_signed_verdicts(tmp_path):
    """**決定 5**: 整合 / 反証 / 混在 / 不明 を 差あり の符号の件数で決める。"""
    def cell(v):
        return {"判定": v}

    assert judge.f1_reading([cell("差あり(+)")] * 3 + [cell("検出されず(MDE = 1)")] * 9
                            ).startswith("F1 と整合")
    assert judge.f1_reading([cell("差あり(−)")] * 2 + [cell("検出されず(MDE = 1)")] * 10
                            ).startswith("F1 の反証")
    assert judge.f1_reading([cell("差あり(+)")] * 2 + [cell("差あり(−)")] * 10
                            ).startswith("混在")
    r = judge.f1_reading([cell("不明(n < 30)")] * 4 + [cell("検出されず(MDE = 1)")] * 8)
    assert r.startswith("不明") and "不明(n < 30) 4" in r and "検出されず 8" in r


def test_f1_cells_are_twelve_and_the_reading_is_one_of_the_four(tmp_path):
    code, out = run_judge(tmp_path, reps=200)
    assert code == 0
    cells = read_rows(out, "f1_12cells.csv")
    assert len(cells) == 12
    assert {c["群"] for c in cells} == {"D_Q1"}
    assert {c["走行"] for c in cells} == {judge.RUN_W8}
    reading = (out / "f1_reading.txt").read_text(encoding="utf-8")
    assert any(reading.split(": ", 1)[1].startswith(w)
               for w in ("F1 と整合", "F1 の反証", "混在", "不明"))
    # §10.3 の欄の形
    why = read_rows(out, "why_frame.csv")
    assert [w["読み"] for w in why] == list(judge.WHY_READINGS)
    assert list(why[0].keys()) == judge.WHY_HEADER
    assert all(v for w in why for v in w.values())          # 空欄にしない


# ==========================================================================
# 4. W に依らない 12 群は W = 8h の走行から
# ==========================================================================
def test_w_independent_groups_come_only_from_the_w8_run(tmp_path):
    def w24_reach(kind, d, i, h):      # W = 24h の走行は全部 0(取り違えたら分かる)
        return 0

    code, out = run_judge(tmp_path, reps=200, w24_reach=w24_reach)
    assert code == 0
    rows = read_rows(out)
    flat = [r for r in rows if r["走行"] == judge.RUN_W8]
    wide = [r for r in rows if r["走行"] == judge.RUN_W24]
    # A1〜A5・E の W8h 側 18 群 + W に依らない 12 群 = 30 群 × 12 行
    assert len(flat) == 30 * 12 and len(wide) == 18 * 12
    assert all("W24h" in r["群"] for r in wide)
    flat_only = {r["群"] for r in flat if "W8h" not in r["群"]}
    assert flat_only == {"全体", "B1_Q1", "B1_Q2", "B1_Q3", "B2_Q1", "B2_Q2", "B2_Q3",
                         "D_Q1", "D_Q2", "D_Q3", "C_SELL", "C_BUY"}
    assert len(flat_only) == 12
    # W に依らない群の値は W = 8h の走行のもの(全部 0 の W = 24h の走行ではない)
    total = next(r for r in rows if r["群"] == "全体" and r["観測量"] == "reach_back_vwap_5m")
    assert float(total["実群"]) > 0.9
    # W = 24h の群は 0 になっている = 取り違えていない
    w24 = next(r for r in rows
               if r["群"] == "A1_W24h_Q1" and r["観測量"] == "reach_back_vwap_5m")
    assert float(w24["実群"]) == 0.0

    # 決定 6: W24h 側の同じ 12 群は観測のみの表に出る(t と判定の列なし)
    obs = read_rows(out, "observation_only.csv")
    extra = [r for r in obs if r["走行"] == judge.RUN_W24 and "W24h" not in r["群"]]
    assert len(extra) == 12 * 12
    assert {r["群"] for r in extra} == flat_only
    assert {r["観測量"] for r in extra} == {
        c.format(h=h) for c, _ in judge.JUDGE_SYSTEMS for h in H}
    assert all("t" not in r and "判定" not in r for r in extra)
    assert all(float(r["実群"]) == 0.0 for r in extra)   # W = 24h の走行から来ている


# ==========================================================================
# 5. 関門
# ==========================================================================
def test_no_table_is_written_when_the_gate_is_closed(tmp_path, capsys):
    root = tmp_path / "root"           # 台帳そのものが無い = 関門は閉じている
    root.mkdir()
    out = tmp_path / "out"
    with pytest.raises(SystemExit) as e:
        run_judge(tmp_path, reps=50, root=root, out=out)
    assert e.value.code == 1
    assert "[止め]" in capsys.readouterr().err
    assert not out.exists(), "関門が閉じているのに出力ディレクトリができている"


def test_the_gate_is_wired_and_has_no_bypass_flag():
    text = (ROOT / "scripts" / "o3c_reaction_judge.py").read_text(encoding="utf-8")
    assert "_research_audit_gate" in text and 'require_audit(UNIT, "結果"' in text
    assert "--no-gate" not in text and "--no-audit-gate" not in text
    # 関門は表を書く前に呼ぶ(呼び出しが最初の write_csv より前にあること)
    assert (text.index("pass_audit_gate(Path(a.root)")
            < text.index('write_csv(out / "judgment_576.csv"'))


def test_a_stop_verdict_in_the_log_keeps_the_tables_unwritten(tmp_path):
    root = open_gate(tmp_path / "root")
    log = root / "docs" / "AUDITOR" / "ACTION_LOG.md"
    log.write_text(log.read_text(encoding="utf-8") + "\n判定: 止める\n", encoding="utf-8")
    out = tmp_path / "out"
    with pytest.raises(SystemExit) as e:
        run_judge(tmp_path, reps=50, root=root, out=out)
    assert e.value.code == 1
    assert not out.exists()


# ==========================================================================
# 6. 判定語を書かない / MD5SUMS
# ==========================================================================
def test_no_verdict_words_anywhere_in_the_output(tmp_path):
    code, out = run_judge(tmp_path, reps=100)
    assert code == 0
    for p in sorted(out.iterdir()):
        text = p.read_text(encoding="utf-8")
        for w in judge.FORBIDDEN:
            assert w not in text, f"{p.name} に判定語「{w}」がある"


def test_md5sums_uses_relative_paths_without_dot_slash(tmp_path):
    code, out = run_judge(tmp_path, reps=100)
    assert code == 0
    lines = (out / "MD5SUMS").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 6
    for ln in lines:
        digest, name = ln.split("  ", 1)
        assert not name.startswith("./") and "/" not in name
        assert hashlib.md5((out / name).read_bytes()).hexdigest() == digest


def test_summary_records_the_frozen_settings(tmp_path):
    code, out = run_judge(tmp_path, reps=100, seed=1)
    assert code == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert s["seed"] == 1 and s["reps"] == 100
    assert s["検定の数"] == 576 and s["群の数"] == 48
    assert s["バー"]["|t|"] == 3.925 and s["バー"]["最低イベント数"] == 30
    assert abs(s["CI水準"]["alpha"] - 0.05 / 576) < 1e-15
    assert s["CI水準"]["クラスタ"] == "UTC 日"
    assert "正規近似" in s["CI水準"]["方法"]           # 決定 1
    assert s["分岐"] == ["不明(n < 30)", "差あり(+)", "差あり(−)", "検出されず(MDE = X)"]
    assert len(s["群ごと"]) == 48
    assert s["走行"]["gap60_w8"]["window_hours"] == 8
    assert s["走行"]["gap60_w24"]["window_hours"] == 24
    # 決定 7: 全体分布の水準を根拠にした文を書いていない
    assert any("水準を根拠にした文" in n for n in s["注記"])


def test_stdout_does_not_state_the_level_of_the_overall_group(tmp_path, capsys):
    """**決定 7**: 「全体」群の水準は表の列にだけ出し、標準出力には書かない。"""
    code, out = run_judge(tmp_path, reps=50)
    assert code == 0
    printed = capsys.readouterr().out
    rows = read_rows(out)
    total = next(r for r in rows if r["群"] == "全体" and r["観測量"] == "reach_back_vwap_5m")
    assert total["実群"]                      # 列には出ている(差の入力)
    assert total["実群"] not in printed       # 標準出力には出していない
    assert "全体" not in printed


# ==========================================================================
# 群の作り方(§4 / §6.1)
# ==========================================================================
def test_matched_control_inherits_the_group_from_its_paired_bundle(tmp_path):
    """束の行にしか無い列で切る群では、合わせた対照は 1 対 1 の相手から受け継ぐ。

    一様対照は相手が無いのでその群に入らない(= 対照 (i) と 差 (i) が空)。
    """
    code, out = run_judge(tmp_path, reps=100)
    assert code == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    g = {x["群"]: x for x in s["群ごと"]}
    for name in ("C_SELL", "B1_Q1", "B2_Q1"):
        assert g[name]["対照は1対1の束から受け継いだか"] is True
        assert g[name]["n_control_uniform"] == 0
        assert g[name]["n_control_matched"] > 0
    # 対照行にも値がある軸(bin_pct / doi_pre_1h)は受け継がない
    for name in ("A1_W8h_Q1", "D_Q1"):
        assert g[name]["対照は1対1の束から受け継いだか"] is False
        assert g[name]["n_control_uniform"] > 0
    rows = read_rows(out)
    assert all(not r["差(i)"] for r in rows if r["群"] == "C_SELL")
    assert any(r["差(i)"] for r in rows if r["群"] == "D_Q1")


def test_the_prereg_group_counts_are_reproduced_on_the_sample_run():
    """事前登録 §8.2 の実測(実群 D1 75 / D2 75 / D3 74、対照 54 / 69 / 88 + NA 2)を再現する。

    **標本 6 日の出力だけを見る。判定区間の出力は開かない。**
    """
    smp = ROOT / "backtest_data" / "o3c_reaction_20260918_sample" / "gap60_w8"
    if not (smp / "table.csv").exists():
        pytest.skip("標本 6 日の出力が無い")
    run = judge.Run(judge.RUN_W8, smp)
    run24 = judge.Run(judge.RUN_W24, smp.parent / "gap60_w24")
    groups = {g.name: g for g in judge.build_groups(run, run24)}
    liq = [int(judge.membership(run, "liq", groups[f"D_Q{q}"]).sum()) for q in (1, 2, 3)]
    mat = [int(judge.membership(run, "control_matched", groups[f"D_Q{q}"]).sum())
           for q in (1, 2, 3)]
    assert liq == [75, 75, 74]
    assert mat == [54, 69, 88]
    assert sum(mat) + 2 == 213        # NA 2 = doi_pre_1h が空の合わせた対照
    assert abs(run.w_sell() - 117 / 224) < 1e-12   # §6.1 の参考値 0.5223
