"""段 A の結果の読み(`scripts/o3c_reaction_judge.py`)の試験。

**判定区間を開ける前に書いた。**合成データだけで測る(判定区間の出力は 1 度も開かない)。

測るもの:
  1. **7 分岐**(不明(n < 30) / 不明(n2 < 30) / 不明(t 未算出) / 差あり(+) / 差あり(−) /
     不明(MDE 未算出) / 検出されず)が合成データで正しく出ること
  2. §9.1 のブートストラップが**日クラスタ**で引いていること(種を固定すれば再現すること)
  3. §4.3 の 576 行がちょうど出ること(群 48 × 系統 2 × h 6)
  4. §4 の内訳表どおり、W に依らない 12 群が W = 8h の走行からだけ 576 に入ること
     (W = 24h 側の同じ 12 群は観測のみの表に出ること)
  5. 関門が閉じていると表を 1 枚も書かないこと
  6. 禁じた語(予測できる / 使える / 有効 / 差なし / 陰性)が出力に 1 つも無いこと

**走行前の再監査で決めた 7 点**もここで測る(どの試験がどれを測るかは各試験の docstring)。

**走行前の再監査(6 回目)で足した機械**(§12 の節):
  - 凍結した入力 4 つ(`mmr` / `seed` / `bin_pct` / `match_order`)の突き合わせ(指摘 1)
  - 承認の L 番号を事前登録 §14.4 の欄から読む(指摘 2)
  - `REPS` / `SEED` を実行時にリテラルと突き合わせる(指摘 4)
  - 「検出されず」の MDE に単位を付ける(指摘 5)
  - 感度の表の MDE の列見出し(指摘 7)/ 軸の作り方を標本にも(指摘 8)
  - 標本側の `window_hours` と `gap_ms`(指摘 9)/ F1 の 12 セル(指摘 13)

**本ファイルの試験は `REPS = 2000` / `SEED = 1` のまま走る**(6 回目の指摘 4。
**前版は `frozen(reps=500)` で定数を差し替えていたが、その経路こそが閉じる対象だった**)。
**合成データを小さくして所要を抑えた**(既定の日数 60 → 40)。
"""
from __future__ import annotations

import contextlib
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
        "bin_pct",
        # 符号なしの大きさ(**実群にも対照にもある**。走行前の再監査(3 回目)の指摘 1)
        "dist_node_bp", "dist_vwap_bp", "oi_dist_node_bp", "oi_dist_vwap_bp",
        # 清算の向きに揃えた版(対照行では空)
        "dist_node_bp_liqdir", "dist_vwap_bp_liqdir",
        "oi_dist_node_bp_liqdir", "oi_dist_vwap_bp_liqdir", "implied_leverage",
        "bundle_n_events_dedup", "bundle_total_qty_accum",
        "doi_pre_1h", "doi_pre_4h", "doi_in",
        "reach_back_vwap_sec", "reach_back_node_sec",
        "reach_node_up_sec", "reach_node_dn_sec",
        "matched_liq_id",
    ]
    for h in H:
        cols += [f"bp_{h}m", f"bp_{h}m_reactdir", f"mfe_{h}m_reactdir",
                 f"mae_{h}m_reactdir", f"doi_post_{h}m",
                 f"reach_back_vwap_{h}m", f"reach_back_node_{h}m",
                 f"reach_node_up_{h}m", f"reach_node_dn_{h}m"]
    return cols


# 対照行では空になる列(`scripts/o3c_reaction.py` の実装をなぞる)。
# **符号なしの `dist_*` / `oi_dist_*` はここに入れない**(対照行にも値がある)。
LIQ_ONLY = ("side", "dist_node_bp_liqdir", "dist_vwap_bp_liqdir",
            "oi_dist_node_bp_liqdir", "oi_dist_vwap_bp_liqdir",
            "implied_leverage", "bundle_n_events_dedup", "bundle_total_qty_accum")

# 符号なしの大きさ -> 清算の向きに揃えた列(`o3c_oi_distance.LIQDIR_SOURCE` と同じ組)。
UNSIGNED = {"dist_node_bp": "dist_node_bp_liqdir",
            "dist_vwap_bp": "dist_vwap_bp_liqdir",
            "oi_dist_node_bp": "oi_dist_node_bp_liqdir",
            "oi_dist_vwap_bp": "oi_dist_vwap_bp_liqdir"}


def _unsigned(i: int) -> dict:
    return {"dist_node_bp": float((i % 11) - 5), "dist_vwap_bp": float((i % 13) - 6),
            "oi_dist_node_bp": float((i % 9) - 4), "oi_dist_vwap_bp": float((i % 17) - 8)}


def _row(kind, day, cid, side, d, i, reach, matched_liq_id="") -> dict:
    r = {"kind": kind, "day": day, "cascade_id": cid, "side": side,
         "direction": "down" if side == "SELL" else ("up" if side == "BUY" else "none"),
         "bin_pct": (i * 7) % 90,
         "doi_pre_1h": ((i % 7) - 3) * 1000.0,
         "doi_pre_4h": ((i % 5) - 2) * 1000.0,
         "doi_in": ((i % 3) - 1) * 100.0,
         "reach_back_vwap_sec": 100.0 + i, "reach_back_node_sec": 120.0 + i,
         "reach_node_up_sec": 140.0 + i, "reach_node_dn_sec": 160.0 + i,
         "matched_liq_id": matched_liq_id}
    r.update(_unsigned(i))              # 符号なしの大きさは kind によらず入る
    if kind == "liq":
        s = judge.LIQ_SIGN[side]        # SELL +1 / BUY −1
        r.update({dst: round(r[src] * s, 4) for src, dst in UNSIGNED.items()})
        r.update({"implied_leverage": 1.0 + (i % 19),
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


APPROVAL = "L-200"          # 試験用の「応答の L 番号」(事前登録の欄に書き写す値)
PREREG_FIELD = "   **応答の L 番号**: **{v}**\n"

# **決定 3・15(9 回目の指摘 3・15)**: 版の担保を 1 本にした関門のための固定値。
# **走行の `summary.json` と事前登録の欄と読みの道具の版が、3 つとも同じであることを
# 関門が要求する。**試験ではその 3 つをこの値にそろえる。
TOOL_COMMIT = "a" * 40
COMMIT_FIELD = "   **凍結した道具のコミット**: **{v}**\n"


@pytest.fixture(autouse=True)
def _stub_tool_version(monkeypatch):
    """**この試験環境の作業ツリーは必ず汚れている**(試験そのものが編集中の
    リポジトリで走る)ので、**(i) 自分の作業ツリー**と**読みの道具の版**だけを固定する。

    **関門そのものを外していない。**(i)〜(iii) の通る側・止まる側は
    `test_the_tool_version_gate_checks_the_worktree_and_the_six_runs` が
    **この固定を上書きして**両側とも測る(`monkeypatch` は後勝ちである)。
    """
    monkeypatch.setattr(judge, "git_status", lambda *a, **k: ("clean", []))
    monkeypatch.setattr(judge, "tool_commit", lambda *a, **k: TOOL_COMMIT)


def write_prereg(root: Path, value: str = APPROVAL,
                 commit: str | None = TOOL_COMMIT) -> Path:
    """**決定 2''''**: 事前登録 §14.4 の「応答の L 番号」の欄を持つ写しを置く。

    **迂回する旗は無い**ので、試験は `--root` を一時ディレクトリにして、
    そこへ事前登録の**行を差し替えた写し**を置く(走行前の再監査(6 回目)の指摘 2。
    リードの決定「**テスト(事前登録の行を一時ファイルで差し替えて検査。迂回旗なし)**」)。
    """
    p = root / judge.PREREG_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "# 試験用の事前登録の写し\n\n"
        "| 2 | `--approval` を事前登録の欄から読む | 「応答の L 番号」欄を読む。L-199 ではない |\n"
        "本文には「応答の L 番号」という語が別の意味でも出てくる(上の行 = §0.1 の表)。\n"
        "機械が読むのは下の欄の行だけである。\n\n"
        + PREREG_FIELD.format(v=value)
        + ("" if commit is None else "\n" + COMMIT_FIELD.format(v=commit)),
        encoding="utf-8")
    return p


def _params(*, mode: str, n_days: int, window_hours: float, gap_sec: int,
            mmr: float | None = judge.MMR_FIXED, seed: int = judge.RUN_SEED_FIXED,
            bin_pct: float = judge.BIN_PCT_FIXED,
            match_order: str = judge.MATCH_ORDER_FIXED,
            approval: str | None = APPROVAL,
            tool_commit: str | None = TOOL_COMMIT,
            tool_dirty: str = "clean") -> dict:
    """`scripts/o3c_reaction.py` が書く `params` と同じ鍵を作る(**決定 12''' + 1'''' + 2''''**)。

    日付そのものは検査に使われない(見るのは**日数**だけ)ので、並びだけを作る。
    **`mmr` / `seed` / `bin_pct` / `match_order` は判定 2 本・感度 4 本で突き合わせる**
    (走行前の再監査(6 回目)の指摘 1)。
    **`approval` は判定 2 本で突き合わせる**(同 指摘 2)。
    """
    p = {"mode": mode,
         "days": [f"day{i:04d}" for i in range(n_days)],
         "window_hours": float(window_hours),
         "gap_ms": int(gap_sec) * 1000,
         "bin_pct": bin_pct,
         "seed": seed,
         "mmr": mmr,
         "match_order": match_order}
    if approval is not None:
        p["approval"] = approval
    # **決定 3・15(9 回目の指摘 3・15)**: 走行の版と作業ツリーの状態
    # (`scripts/o3c_reaction.py` が `summary.json` の上位に書く鍵と同じ形)。
    out: dict = {"params": p,
                 "tool_dirty": {"状態": tool_dirty,
                                "汚れているか": tool_dirty != "clean",
                                "変更ファイル": []}}
    if tool_commit is not None:
        out["tool_commit"] = tool_commit
    return out


def as_sample(src: Path, dst: Path, *, window_hours: float = 8,
              gap_sec: int = 60) -> Path:
    """同じ表を「**標本の走行**」として置き直す(`summary.json` だけ差し替える)。

    **走行前の再監査(5 回目)の指摘 12。リードの決定**:
    「**標本で試すときは `--allow-sample-as-run` のような迂回旗を作らず、
    試験用に summary.json を差し替えた一時ディレクトリで検査する**」。
    表の中身は元のままなので、MDE の `p`・`s` は前版と同じ値になる。
    """
    dst.mkdir(parents=True, exist_ok=True)
    for n in ("table.csv", "table_mixed.csv"):
        if (src / n).exists():
            (dst / n).write_bytes((src / n).read_bytes())
    (dst / "summary.json").write_text(
        json.dumps(_params(mode="sample", n_days=judge.SAMPLE_N_DAYS,
                           window_hours=window_hours, gap_sec=gap_sec,
                           approval=None)),
        encoding="utf-8")
    return dst


@contextlib.contextmanager
def swapped(**attrs):
    """モジュールの属性を一時的に差し替える(**止まる側**を測るためだけに使う)。

    **走行前の再監査(6 回目)の指摘 4**: 前版はここに `frozen(reps=500)` があり、
    **試験のほぼ全部が `REPS` を差し替えて走っていた。****その経路こそが閉じる対象だった**
    (リードの決定「**テストは monkeypatch をやめ、合成データで 2,000 回そのまま走らせる**」)。
    **本版の試験は `REPS = 2000` / `SEED = 1` のまま走る。**
    この文脈管理子は、**差し替えたときに「[止め]」になること**を測る試験でだけ使う。
    """
    old = {k: getattr(judge, k) for k in attrs}
    for k, v in attrs.items():
        setattr(judge, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(judge, k, v)


def make_run(path: Path, *, days: int, per_day: int, reach, window_hours: int = 8,
             n_buy: int = 10_000, mixed_per_day: int = 0, mode: str = "full",
             gap_sec: int = 60, n_days_param: int | None = None,
             params_override: dict | None = None) -> Path:
    """合成の走行ディレクトリを作る。

    `reach(kind, day_i, row_i, h)` が戻り到達 2 系統の 0/1 を返す。
    `n_buy` は BUY の束の数の上限(C_BUY の束の数を 30 未満にするために使う)。
    `mixed_per_day` は 1 日あたり何個の束を mixed(= `table_mixed.csv` 側)にするか。
    その束にも合わせた対照は作られるので、**決定 8' で落とされる対照**が生まれる。
    """
    path.mkdir(parents=True, exist_ok=True)
    cols = _columns()
    rows: list[dict] = []
    mixed: list[dict] = []
    cid = 0
    buy_left = n_buy
    for d in range(days):
        day = f"2024-{1 + d // 28:02d}-{1 + d % 28:02d}"
        ids: list[str] = []
        for i in range(per_day):
            side = "BUY" if (i % 2 == 0 and buy_left > 0) else "SELL"
            buy_left -= 1 if side == "BUY" else 0
            cid_s = f"binance_cm_real_{cid:06d}"
            ids.append(cid_s)
            row = _row("liq", day, cid_s, side, d, i, reach)
            # 先頭の何個かを mixed にする(主表から外れ、table_mixed.csv 側に出る)。
            if i < mixed_per_day:
                row["side"], row["direction"] = "", "mixed"
                for c in LIQ_ONLY:
                    row[c] = ""
                mixed.append(row)
            else:
                rows.append(row)
            cid += 1
        for i in range(per_day):
            rows.append(_row("control_uniform", day,
                             f"control_uniform_{day}_{i:05d}", "", d, i, reach))
            rows.append(_row("control_matched", day,
                             f"control_matched_{day}_{i:05d}", "", d, i, reach,
                             matched_liq_id=ids[i]))
    with (path / "table.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    with (path / "table_mixed.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in mixed:
            w.writerow({c: r.get(c, "") for c in cols})
    n_days = (n_days_param if n_days_param is not None
              else (judge.JUDGMENT_N_DAYS if mode == "full" else judge.SAMPLE_N_DAYS))
    kw = dict(mode=mode, n_days=n_days, window_hours=window_hours, gap_sec=gap_sec)
    if mode != "full":
        kw["approval"] = None
    kw.update(params_override or {})
    (path / "summary.json").write_text(json.dumps(_params(**kw)), encoding="utf-8")
    return path


def open_gate(root: Path) -> Path:
    """関門を通す台帳と、事前登録の「応答の L 番号」の欄を作る(試験用。`--root` で差し替える)。"""
    write_prereg(root)
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
            return 1 if d < 24 else 0
        if kind == "control_matched":
            return 1 if d < 20 else 0
        return 0
    if h == 1:
        # 検出されず(差 0 < MDE): **日ごとに上下する**ので SE は 0 にならず、
        # 差そのものは 0 に近い(|t| < バー)。
        # **走行前の再監査(4 回目)の指摘 1 で足した**: 前版はここが実群も対照も
        # `i % 2` で、**日ごとの差が全く動かず SE = 0 → t が非有限**だった。
        # それを前版の `decide` は「検出されず」と書いていた(= 指摘 1 の型)。
        if kind == "liq":
            return 1 if i < 20 + 6 * ((d % 3) - 1) else 0
        if kind == "control_matched":
            return 1 if i < 20 else 0
        return 0
    # h = 30 / 60 → 実群も対照も同じ値で日ごとに動かない = SE 0 → **不明(t 未算出)**
    return i % 2


def sens_required_args(tmp_path: Path, have=()) -> list[str]:
    """**決定 2'''''(7 回目の指摘 2)**: `--sens` 4 本を必ず渡すための引数を作る。

    中身のある感度は呼び出し側が `have` に挙げたものだけで、**残りは「読めない感度」**
    として渡す(読めない感度はその表だけ書かれず、**判定の表は書かれる**)。
    **迂回する旗ではない**(道具の側の要求はそのまま、渡すものを試験が用意している)。
    """
    args: list[str] = []
    for nm in judge.SENS_REQUIRED:
        if nm in have:
            continue
        args += ["--sens", f"{nm}={tmp_path / 'sens_missing' / nm}"]
    return args


def _sens_specs(extra) -> list[str]:
    """`extra` に直書きされた `--sens NAME=DIR` の値だけを拾う。"""
    out, take = [], False
    for tok in extra:
        if take:
            out.append(str(tok))
            take = False
        take = str(tok) == "--sens"
    return out


def run_judge(tmp_path: Path, *, reach=reach_four_branches,
              w24_reach=None, days=40, per_day=40, n_buy=10_000, root=None,
              out=None, mixed_per_day=0, sens=None, extra=(),
              run_params=None, sample_params=None):
    r8 = make_run(tmp_path / "run_w8", days=days, per_day=per_day, reach=reach,
                  window_hours=8, n_buy=n_buy, mixed_per_day=mixed_per_day,
                  params_override=run_params)
    r24 = make_run(tmp_path / "run_w24", days=days, per_day=per_day,
                   reach=w24_reach or reach, window_hours=24, n_buy=n_buy,
                   mixed_per_day=mixed_per_day, params_override=run_params)
    # **決定 12'''**: 標本は `mode: sample` / 6 日の `summary.json` を持つ別のディレクトリ。
    s8 = as_sample(r8, tmp_path / "sample_w8", window_hours=8)
    s24 = as_sample(r24, tmp_path / "sample_w24", window_hours=24)
    if sample_params:
        for d, w in ((s8, 8), (s24, 24)):
            kw = dict(mode="sample", n_days=judge.SAMPLE_N_DAYS, window_hours=w,
                      gap_sec=60, approval=None)
            kw.update(sample_params)
            (d / "summary.json").write_text(json.dumps(_params(**kw)), encoding="utf-8")
    out = out or (tmp_path / "out")
    root = root if root is not None else open_gate(tmp_path / "root")
    argv = [
        "--run-w8", str(r8), "--run-w24", str(r24),
        "--sample-w8", str(s8), "--sample-w24", str(s24),
        "--out-dir", str(out), "--root", str(root),
    ]
    for nm in (sens or []):
        g, w = judge._sens_name_params(nm)
        d = make_run(tmp_path / f"sens_{nm}", days=days, per_day=per_day,
                     reach=reach, window_hours=w, n_buy=n_buy, gap_sec=g)
        argv += ["--sens", f"{nm}={d}"]
    # **決定 2'''''(走行前の再監査(7 回目)の指摘 2)**: `--sens` は 4 本とも必ず渡す
    # (1 本でも欠ければ「[止め]」)。**試験で中身まで作るのは呼び出し側が指定した本数だけで、
    # 残りは「読めない感度」として渡す**(読めない感度はその表だけ書かれず、
    # 判定の表は書かれる = この決定のもう半分。**その経路をほぼ全試験が通る**)。
    have = list(sens or []) + [s.split("=", 1)[0] for s in _sens_specs(extra)]
    argv += sens_required_args(tmp_path, have)
    argv += list(extra)
    # **決定 4''''**: `REPS` / `SEED` は差し替えない。**2,000 回・種 1 のまま走らせる。**
    code = judge.main(argv)
    return code, out


def read_rows(out: Path, name="judgment_576.csv") -> list[dict]:
    return list(csv.DictReader((out / name).open(encoding="utf-8", newline="")))


# ==========================================================================
# 1. 4 分岐
# ==========================================================================
def test_decide_has_exactly_seven_branches_in_order():
    """**決定 2 + 17' + 1'' + 20''**: **7 分岐**を上から順に当てる(純関数として測る)。

    **走行前の再監査(5 回目)の指摘 15 で名前を直した**(リードの決定「**テスト名を
    分岐の数に合わせて改名(`seven_branches` など)、docstring も直す**」)。
    **前版の名前は `..._three_branches_...` のままで、docstring も「決定 2 + 17' + 1'' + 20''」と
    書きながら数を書いていなかった。**
    7 分岐 = 不明(n < 30)/ 不明(n2 < 30)/ 不明(t 未算出)/ 差あり(+)/ 差あり(−)/
    不明(MDE 未算出)/ 検出されず(`judge.BRANCHES` の 7 語)。
    """
    assert len(judge.BRANCHES) == 7
    # (1) 欠測を引いた後の実群 n1 < 30 は t や差によらず「不明(n < 30)」
    assert judge.decide(29, 999, 99.0, 0.7, 0.01) == ("不明(n < 30)", "n < 30")
    # (2) **決定 20''**: 対照の n2 < 30 も「不明(n2 < 30)」
    assert judge.decide(100, 29, 99.0, 0.7, 0.01) == (judge.UNKNOWN_N2, "n2 < 30")
    assert judge.decide(29, 29, 99.0, 0.7, 0.01)[0] == judge.UNKNOWN_N   # n1 が先
    # (3) **決定 1''**: t が非有限なら「不明(t 未算出)」(検出されずにしない)
    assert judge.decide(100, 100, float("nan"), 0.7, 0.01) == (judge.UNKNOWN_T, "t 未算出")
    assert "検出されず" not in judge.decide(100, 100, float("nan"), 0.7, 0.01)[0]
    assert judge.decide(100, 100, float("inf"), 0.7, 0.01)[0] == judge.UNKNOWN_T
    # (4) |t| ≥ 3.925 → 差あり(符号つき)
    assert judge.decide(100, 100, 4.0, 0.5, 0.01)[0] == "差あり(+)"
    assert judge.decide(100, 100, -4.0, -0.5, 0.01)[0] == "差あり(−)"
    # バーの直下は差ありにしない
    assert judge.decide(100, 100, 3.9, 0.5, 0.01)[0].startswith("検出されず")
    # (6) それ以外 → 検出されず(MDE を必ず書く)
    assert judge.decide(100, 100, 1.0, 0.005, 0.01)[0] == "検出されず(MDE = 0.010000)"
    assert judge.decide(100, 100, 1.0, 0.05, 0.01)[0] == "検出されず(MDE = 0.010000)"
    # **決定 17'**: MDE が計算できないセルは「検出されず」ではなく「不明」
    assert judge.decide(100, 100, 1.0, 0.05, float("nan")) == (judge.UNKNOWN_MDE, "MDE 未算出")
    assert "検出されず" not in judge.decide(100, 100, 1.0, 0.05, float("nan"))[0]
    # 「差なし」「陰性」は 1 つも出さない
    for args in [(29, 999, 99.0, 0.7, 0.01), (100, 29, 99.0, 0.7, 0.01),
                 (100, 100, float("nan"), 0.7, 0.01), (100, 100, 4.0, 0.5, 0.01),
                 (100, 100, 1.0, 0.05, 0.01), (100, 100, 1.0, 0.05, float("nan"))]:
        assert "差なし" not in judge.decide(*args)[0]
        assert "陰性" not in judge.decide(*args)[0]


def test_bar_near_marks_only_the_band_around_the_bar():
    """**決定 14''**: `|t|` が z ± 0.065 に入る行に ○(観測のみ。判定は変えない)。"""
    z = judge.BAR_T
    assert judge.bar_near(z) == "○"
    assert judge.bar_near(-z) == "○"
    assert judge.bar_near(z - 0.06) == "○" and judge.bar_near(z + 0.06) == "○"
    assert judge.bar_near(z - 0.07) == "" and judge.bar_near(z + 0.07) == ""
    assert judge.bar_near(float("nan")) == ""
    # 印は判定を変えない(バーのすぐ下は「検出されず」のまま)
    assert judge.decide(100, 100, z - 0.01, 0.5, 0.01)[0].startswith("検出されず")
    assert judge.bar_near(z - 0.01) == "○"


def test_ci_is_the_normal_approximation_and_matches_the_t_bar():
    """**決定 1**: CI = 差 ± z × SE。|t| ≥ z と CI が 0 を除外は同値。"""
    lo, hi = judge.ci_normal(1.0, 0.2)          # t = 5.0
    assert abs(lo - (1.0 - judge.BAR_T * 0.2)) < 1e-12
    assert abs(hi - (1.0 + judge.BAR_T * 0.2)) < 1e-12
    assert lo > 0                                # 0 を除外
    lo, hi = judge.ci_normal(1.0, 0.3)          # t = 3.33 < z
    assert lo < 0 < hi                           # 0 をまたぐ


def test_there_is_only_one_z_for_the_bar_the_ci_and_the_mde():
    """**決定 12'**: z は 1 本(`norm.ppf(1 − α/2)`)。丸めた 3.925 を別に持たない。"""
    from statistics import NormalDist
    z = NormalDist().inv_cdf(1 - judge.ALPHA / 2)
    assert judge.BAR_T == judge.Z_ALPHA == z
    assert judge.BAR_T != 3.925                  # 丸めた値そのものではない
    assert abs(judge.BAR_T - 3.925) < 1e-3       # 丸め表示は 3.925
    assert judge.BAR_T_SHOWN == "3.925"
    # MDE の係数も同じ z から作る
    assert judge.MDE_Z == judge.Z_ALPHA + judge.Z_POWER
    import numpy as np
    a = np.array([1.0] * 30 + [0.0] * 70)
    b = np.array([1.0] * 20 + [0.0] * 80)
    got = judge.mde("prop", a, b, 1000, 1000)
    want = (z + judge.Z_POWER) * (0.3 * 0.7 / 1000 + 0.2 * 0.8 / 1000) ** 0.5
    assert abs(got - want) < 1e-15
    # **決定 15''**: `alpha` の引数(= 2 本目の z を作る枝)を消したこと
    import inspect
    assert "alpha" not in inspect.signature(judge.mde).parameters
    body = inspect.getsource(judge.mde).split('"""')[2]     # docstring を外した本体
    assert "inv_cdf" not in body, "mde() の中で z を作り直す枝が残っている"
    assert "MDE_Z" in body


def test_seven_branches_come_out_on_synthetic_data(tmp_path):
    """合成データで分岐(と両方の符号)が出ること。**分岐は 7 つである。**

    **走行前の再監査(4 回目)の指摘 1 で 1 つ増えた**: `t` が非有限のセル(h = 30 / 60)は
    「不明(t 未算出)」で、「検出されず」ではない。
    **5 回目の指摘 15 で名前を `seven_branches` に直した**(この試験が当てているのは
    差あり(+)/ 差あり(−)/ 検出されず / 不明(t 未算出)/ 不明(n < 30)の 5 つで、
    残る 2 つ(不明(n2 < 30)/ 不明(MDE 未算出))は別の試験が当てている
    = `test_n2_under_30_is_unknown_too` と `test_decide_has_exactly_seven_branches_in_order`)。
    """
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
    assert v["有限な複製の本数"] and int(v["有限な複製の本数"]) >= 2

    # **決定 1''**: SE が 0 になるセルは「不明(t 未算出)」(検出されずにしない)
    v = by[("reach_back_vwap_30m", "全体", "30")]
    assert v["判定"] == judge.UNKNOWN_T and v["検出力"] == "t 未算出", v
    assert "検出されず" not in v["判定"]

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

    code, out = run_judge(tmp_path, reach=mostly_missing, days=20, per_day=40)
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
    code, out = run_judge(tmp_path, reach=one_value, days=10, per_day=1)
    assert code == 0
    rows = read_rows(out)
    assert len(rows) == 576
    empty = [r for r in rows if int(r["n1"]) == 0]
    assert empty, "空の群が 1 つも無いので、この試験は空の群を測れていない"
    assert {r["判定"] for r in empty} == {"不明(n < 30)"}


def test_mde_takes_alpha_directly_and_uses_the_sample_p_and_s():
    """**決定 4 + 15''**: z は定数 1 本。p・s は渡した標本の行、n は走行後の件数。"""
    import numpy as np
    a = np.array([1.0] * 30 + [0.0] * 70)      # p1 = 0.30
    b = np.array([1.0] * 20 + [0.0] * 80)      # p2 = 0.20
    got = judge.mde("prop", a, b, 1000, 1000)
    want = judge.MDE_Z * (0.3 * 0.7 / 1000 + 0.2 * 0.8 / 1000) ** 0.5
    assert abs(got - want) < 1e-12
    # 使う α は ALPHA = 0.05/576 の 1 つだけ(倍率でも別の α でも読み替えない)
    assert abs(judge.MDE_Z - (judge.Z_ALPHA + judge.Z_POWER)) < 1e-15
    assert abs(judge.ALPHA - 0.05 / 576) < 1e-18
    # n は走行後の件数なので、n を増やせば MDE は小さくなる(p・s は変えない)
    assert judge.mde("prop", a, b, 4000, 4000) < got


# ==========================================================================
# 2. ブートストラップ(日クラスタ・種の固定)
# ==========================================================================
def test_bootstrap_is_reproducible_with_the_same_seed(tmp_path):
    """同じ入力なら同じ表が出る(種が固定されていることの確認)。

    **走行前の再監査(6 回目)の指摘 4 で書き替えた**: 前版はここで種を 2 に差し替えて
    「引き方が変わる」ことを測っていたが、**種の差し替えはいま「[止め]」になる**
    (決定 4'''')。**種を実際に使っていることは、引く側(numpy)で測る。**
    """
    code1, out1 = run_judge(tmp_path / "a")
    code2, out2 = run_judge(tmp_path / "b")
    assert code1 == 0 and code2 == 0
    h1 = hashlib.md5((out1 / "judgment_576.csv").read_bytes()).hexdigest()
    h2 = hashlib.md5((out2 / "judgment_576.csv").read_bytes()).hexdigest()
    assert h1 == h2
    # 種を実際に使っている(別の種なら別の引き方になる)
    import numpy as np
    a = np.random.default_rng(judge.SEED).integers(0, 60, size=(judge.REPS, 60))
    b = np.random.default_rng(judge.SEED).integers(0, 60, size=(judge.REPS, 60))
    c = np.random.default_rng(judge.SEED + 1).integers(0, 60, size=(judge.REPS, 60))
    assert (a == b).all() and not (a == c).all()


def test_bootstrap_clusters_by_day_not_by_row(tmp_path):
    """同じ行の集まりでも、値が**日でまとまっている**方が |t| は小さくなる。

    行ごとに引いていたら 2 つの走行の |t| はほぼ同じになる。日で引いているので、
    まとまっている方は標準誤差が大きくなり、|t| がはっきり小さくなる。
    """
    def clustered(kind, d, i, h):          # 日ごとに 0 か 1(日でまとまっている)
        if kind == "liq":
            return 1 if d < 24 else 0      # 40 日中 24 日 = 0.6
        if kind == "control_matched":
            return 1 if d < 20 else 0      # 40 日中 20 日 = 0.5
        return 0

    def spread(kind, d, i, h):             # 同じ割合を全部の日に散らす
        if kind == "liq":
            return 1 if i < 24 else 0      # 40 行中 24 行 = 0.6
        if kind == "control_matched":
            return 1 if i < 20 else 0      # 40 行中 20 行 = 0.5
        return 0

    _, out_c = run_judge(tmp_path / "c", reach=clustered)
    _, out_s = run_judge(tmp_path / "s", reach=spread)

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
    code, out = run_judge(tmp_path)
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
    code, out = run_judge(tmp_path)
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

    code, out = run_judge(tmp_path, w24_reach=w24_reach)
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
    write_prereg(root)                 # 承認の欄は埋めておく(止めるのは関門だけ)
    out = tmp_path / "out"
    with pytest.raises(SystemExit) as e:
        run_judge(tmp_path, root=root, out=out)
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
        run_judge(tmp_path, root=root, out=out)
    assert e.value.code == 1
    assert not out.exists()


# ==========================================================================
# 6. 判定語を書かない / MD5SUMS
# ==========================================================================
def test_no_verdict_words_anywhere_in_the_output(tmp_path):
    code, out = run_judge(tmp_path)
    assert code == 0
    for p in sorted(out.iterdir()):
        text = p.read_text(encoding="utf-8")
        for w in judge.FORBIDDEN:
            assert w not in text, f"{p.name} に判定語「{w}」がある"


def test_md5sums_uses_relative_paths_without_dot_slash(tmp_path):
    code, out = run_judge(tmp_path)
    assert code == 0
    lines = (out / "MD5SUMS").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 6
    for ln in lines:
        digest, name = ln.split("  ", 1)
        assert not name.startswith("./") and "/" not in name
        assert hashlib.md5((out / name).read_bytes()).hexdigest() == digest


def test_summary_records_the_frozen_settings(tmp_path):
    code, out = run_judge(tmp_path)
    assert code == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert s["seed"] == 1 and s["reps"] == 2000
    assert s["検定の数"] == 576 and s["群の数"] == 48
    assert s["バー"]["|t|"] == judge.BAR_T and s["バー"]["最低イベント数"] == 30
    # 決定 12': バー・CI・MDE の z は 1 本
    assert s["バー"]["|t|"] == s["バー"]["z_{1-α/2}"] == s["CI水準"]["z_{1-α/2}"]
    assert s["バー"]["|t|の丸め表示"] == "3.925"
    assert abs(s["CI水準"]["alpha"] - 0.05 / 576) < 1e-15
    assert s["CI水準"]["クラスタ"] == "UTC 日"
    assert "正規近似" in s["CI水準"]["方法"]           # 決定 1
    assert s["分岐"] == [judge.UNKNOWN_N, judge.UNKNOWN_N2, judge.UNKNOWN_T,
                         "差あり(+)", "差あり(−)",
                         judge.UNKNOWN_MDE, "検出されず(MDE = X 単位)"]
    # 決定 2'': 有限な複製の本数の最小を summary に出す(閾値は置かない = A-12)
    assert s["有限な複製の本数"]["指定した反復回数"] == 2000
    assert (s["有限な複製の本数"]["最小(検定したセルだけ)"] is not None
            and s["有限な複製の本数"]["最小(検定したセルだけ)"] >= 2)
    assert s["有限な複製の本数"]["最大(検定したセルだけ)"] <= 2000
    # 決定 10'': 使った台帳の根を残す
    assert s["監査の台帳の根(--root)"].endswith("root")
    # 決定 3'': 固定の一覧を summary にも残す
    assert s["対照(ii)の軸の作り方の固定(事前登録 §4)"] == judge.AXIS_KIND_FIXED
    # 決定 13'': 走行ごとの #14 の結果
    for nm in ("gap60_w8", "gap60_w24"):
        assert s["走行"][nm]["サニティ14の結果"]["通過"] is True
        assert s["走行"][nm]["サニティ14の結果"]["同じ相手を指す重複の件数"] == 0
    # 決定 11': 観測のみの表の行数を summary に出す
    assert s["観測のみの表の行数"]["observation_only.csv"] == 43 * 48 + 12 * 12
    assert len(s["群ごと"]) == 48
    assert s["走行"]["gap60_w8"]["window_hours"] == 8
    assert s["走行"]["gap60_w24"]["window_hours"] == 24
    # 決定 7: 全体分布の水準を根拠にした文を書いていない
    assert any("水準を根拠にした文" in n for n in s["注記"])


def test_stdout_does_not_state_the_level_of_the_overall_group(tmp_path, capsys):
    """**決定 7**: 「全体」群の水準は表の列にだけ出し、標準出力には書かない。"""
    code, out = run_judge(tmp_path)
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
    code, out = run_judge(tmp_path)
    assert code == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    g = {x["群"]: x for x in s["群ごと"]}
    for name in ("C_SELL", "B1_Q1", "B2_Q1", "E_W8h_Q1"):
        assert g[name]["対照は1対1の束から受け継いだか"] is True
        assert g[name]["対照(ii)の軸の作り方"] == judge.AX_INHERIT
        assert g[name]["n_control_uniform"] == 0
        assert g[name]["n_control_matched"] > 0
    # 対照行にも値がある軸(bin_pct / doi_pre_1h)は受け継がない
    for name in ("A1_W8h_Q1", "D_Q1"):
        assert g[name]["対照は1対1の束から受け継いだか"] is False
        assert g[name]["対照(ii)の軸の作り方"] == judge.AX_OWN
        assert g[name]["n_control_uniform"] > 0
    rows = read_rows(out)
    assert all(not r["差(i)"] for r in rows if r["群"] == "C_SELL")
    assert any(r["差(i)"] for r in rows if r["群"] == "D_Q1")


def test_only_fourteen_groups_inherit_and_twentyfour_take_the_partner_sign(tmp_path):
    """**決定 1'**: 受け継ぐのは 14 群だけ。A2〜A5 の 24 群は対照自身の値を作る。

    前版は「対照行に値があるのは `bin_pct` と `doi_pre_1h` だけ」として 38 群を
    受け継ぎにしていた。**符号なしの大きさは対照行にもある**(指摘 1)。
    """
    code, out = run_judge(tmp_path)
    assert code == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    kinds = s["対照(ii)の軸の作り方"]
    inherit = set(kinds["inherit(相手の実群の群を受け継ぐ)"])
    signed = set(kinds["partner_sign(符号なしの大きさ × 相手の側の符号)"])
    own = set(kinds["own(対照行自身の値)"])
    # 受け継ぐ 14 群 = E の 6 + B1 3 + B2 3 + C 2
    assert len(inherit) == 14 == s["受け継いだ群の数"]
    assert inherit == (
        {f"E_{w}_Q{q}" for w in ("W8h", "W24h") for q in (1, 2, 3)}
        | {f"B1_Q{q}" for q in (1, 2, 3)} | {f"B2_Q{q}" for q in (1, 2, 3)}
        | {"C_SELL", "C_BUY"}
    )
    # 相手の符号を当てる 24 群 = A2〜A5 の 4 軸 × (3 + 3)
    assert len(signed) == 24 == s["相手の符号を当てた群の数"]
    assert signed == {f"A{a}_{w}_Q{q}"
                      for a in (2, 3, 4, 5) for w in ("W8h", "W24h") for q in (1, 2, 3)}
    # 自前の値で切る 10 群 = A1 の 6 + D の 3 + 全体 1
    assert len(own) == 10 and "全体" in own
    assert len(inherit) + len(signed) + len(own) == 48
    # 決定 11': 受け継いだ群は一覧と行数で summary に残す
    assert {x["群"] for x in s["受け継いだ群"]} == inherit
    assert all(x["n_control_matched"] > 0 for x in s["受け継いだ群"])
    # 24 群では対照 (ii) に行が入り、対照 (i) は空(1 対 1 の相手が無いため)
    g = {x["群"]: x for x in s["群ごと"]}
    assert g["A2_W8h_Q1"]["n_control_matched"] > 0
    assert g["A2_W8h_Q1"]["n_control_uniform"] == 0


def test_the_partner_sign_axis_is_the_controls_own_value(tmp_path):
    """**決定 1'**: 対照自身の符号なしの大きさに、相手の側の符号を当てた値である。"""
    r8 = make_run(tmp_path / "r8", days=3, per_day=8, reach=reach_four_branches)
    run = judge.Run(judge.RUN_W8, r8)
    got = run.matched_partner_sign_axis("dist_node_bp_liqdir")
    for i, (row, p) in enumerate(zip(run.by_kind["control_matched"],
                                     run.pair_of_matched)):
        want = round(float(row["dist_node_bp"]) * judge.LIQ_SIGN[p["side"]], 4)
        assert got[i] == want
        # 相手の束の値そのものではない(= 受け継ぎではない)ことを 1 件で示す
        if float(row["dist_node_bp"]) != float(p["dist_node_bp"]):
            assert got[i] != float(p["dist_node_bp_liqdir"])


# ==========================================================================
# 1 対 1 の対応(matched_liq_id・サニティ #14・mixed の相手)
# ==========================================================================
def test_the_pairing_comes_from_the_matched_liq_id_column(tmp_path):
    """**決定 6'**: 連番の算術ではなく `matched_liq_id` 列で相手を引く。"""
    r8 = make_run(tmp_path / "r8", days=2, per_day=5, reach=reach_four_branches)
    run = judge.Run(judge.RUN_W8, r8)
    assert len(run.pair_of_matched) == len(run.by_kind["control_matched"])
    assert all(p is not None for p in run.pair_of_matched)
    for row, p in zip(run.by_kind["control_matched"], run.pair_of_matched):
        assert p["cascade_id"] == row["matched_liq_id"]
        assert p["day"] == row["day"]
    assert judge.check_pairing(run) == []
    # 算術の復元を残していない
    text = (ROOT / "scripts" / "o3c_reaction_judge.py").read_text(encoding="utf-8")
    assert "_cascade_index" not in text


def test_a_broken_pairing_stops_before_any_table_is_written(tmp_path):
    """**サニティ #14**: 相手が引けない / 別の日 / 許容を超える なら「[止め]」で終わる。"""
    import csv as _csv
    r8 = make_run(tmp_path / "run_w8", days=60, per_day=40, reach=reach_four_branches)
    r24 = make_run(tmp_path / "run_w24", days=60, per_day=40, reach=reach_four_branches,
                   window_hours=24)
    p = r8 / "table.csv"
    rows = list(_csv.DictReader(p.open(encoding="utf-8", newline="")))
    for r in rows:
        if r["kind"] == "control_matched":
            r["matched_liq_id"] = "存在しない_id"      # 相手が引けない形にする
            break
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    out = tmp_path / "out"
    code = judge.main([
        "--run-w8", str(r8), "--run-w24", str(r24),
        "--sample-w8", str(as_sample(r8, tmp_path / "s8")),
        "--sample-w24", str(as_sample(r24, tmp_path / "s24", window_hours=24)),
        "--out-dir", str(out), "--root", str(open_gate(tmp_path / "root")),
    ] + sens_required_args(tmp_path))
    assert code == 1
    assert (out / judge.STOPPED_NAME).exists(), "止めた記録が書かれていない"
    assert not (out / "judgment_576.csv").exists(), "サニティ #14 が破れているのに表が書かれている"


def test_matched_controls_of_mixed_bundles_are_dropped_from_every_group(tmp_path):
    """**決定 8'**: 相手が mixed 束の合わせた対照は全群から落とし、件数を summary に出す。"""
    code, out = run_judge(tmp_path, mixed_per_day=1, days=40, per_day=20)
    assert code == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert s["走行"]["gap60_w8"]["相手がmixed束で落とした合わせた対照"] == 40
    assert s["走行"]["gap60_w24"]["相手がmixed束で落とした合わせた対照"] == 40
    # 「全体」群の対照の件数は、落とした 40 件を引いた数になっている
    g = {x["群"]: x for x in s["群ごと"]}
    n_mat_rows = s["走行"]["gap60_w8"]["行数"]["control_matched"]
    assert g["全体"]["n_control_matched"] == n_mat_rows - 40
    # side の群でも落ちている(mixed の相手には side が無いので元から入らない)
    assert g["C_SELL"]["n_control_matched"] + g["C_BUY"]["n_control_matched"] \
        == n_mat_rows - 40


# ==========================================================================
# 感度の観測のみの表(決定 19')/ W = 24h の切り直し(決定 20')
# ==========================================================================
def test_sens_writes_one_observation_only_table_per_run(tmp_path):
    """**決定 19'**: `--sens NAME=DIR` ごとに observation_only_<NAME>.csv を出す。"""
    code, out = run_judge(tmp_path, days=20, per_day=10,
                          sens=["gap30_w8", "gap180_w8"])
    assert code == 0
    names = {p.name for p in out.iterdir()}
    assert {"observation_only_gap30_w8.csv", "observation_only_gap180_w8.csv"} <= names
    rows = read_rows(out, "observation_only_gap30_w8.csv")
    # 30 群 × (判定 12 系統 + 観測 43 系統)
    assert len(rows) == 30 * (12 + 43)
    assert list(rows[0].keys()) == judge.SENS_HEADER     # t と 判定 の列は無い
    # 決定 7'''': 感度の表の MDE の列見出しは族の α の名前を名乗らない
    assert judge.SENS_MDE_COL in rows[0] and judge.MDE_COL not in rows[0]
    assert "t" not in rows[0] and "判定" not in rows[0]
    assert {r["走行"] for r in rows} == {"gap30_w8"}
    # 対を成す標本が無いので MDE は空(判定にも F1 にも入れない)
    assert all(r[judge.SENS_MDE_COL] == "" for r in rows)
    # 判定の表は 576 行のまま(感度は 1 行も入っていない)
    assert len(read_rows(out)) == 576
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert s["観測のみの表の行数"]["observation_only_gap30_w8.csv"] == 30 * 55
    assert set(s["感度(観測のみ)"]) == {"gap30_w8", "gap180_w8"}
    # MD5SUMS にも入る
    md5 = (out / "MD5SUMS").read_text(encoding="utf-8")
    assert "observation_only_gap30_w8.csv" in md5


def test_sens_with_a_sample_dir_fills_the_mde_column(tmp_path):
    """**決定 8''**: `--sens NAME=DIR:SAMPLE_DIR` なら MDE の列が出る。

    標本を渡さない感度は MDE 列が空のままで、理由が summary に書かれる。
    """
    r8 = make_run(tmp_path / "run_w8", days=20, per_day=10, reach=reach_four_branches)
    r24 = make_run(tmp_path / "run_w24", days=20, per_day=10, reach=reach_four_branches,
                   window_hours=24)
    s30 = make_run(tmp_path / "sens30", days=20, per_day=10, reach=reach_four_branches,
                   gap_sec=30)
    smp30 = as_sample(
        make_run(tmp_path / "smp30_src", days=6, per_day=10, reach=reach_four_branches,
                 gap_sec=30),
        tmp_path / "smp30", gap_sec=30)
    s180 = make_run(tmp_path / "sens180", days=20, per_day=10, reach=reach_four_branches,
                    window_hours=24, gap_sec=30)
    out = tmp_path / "out"
    code = judge.main([
        "--run-w8", str(r8), "--run-w24", str(r24),
        "--sample-w8", str(as_sample(r8, tmp_path / "s8")),
        "--sample-w24", str(as_sample(r24, tmp_path / "s24", window_hours=24)),
        "--out-dir", str(out), "--root", str(open_gate(tmp_path / "root")),
        "--sens", f"gap30_w8={s30}:{smp30}",      # 標本つき
        "--sens", f"gap30_w24={s180}",            # 標本なし
    ] + sens_required_args(tmp_path, ("gap30_w8", "gap30_w24")))
    assert code == 0
    with_smp = read_rows(out, "observation_only_gap30_w8.csv")
    without = read_rows(out, "observation_only_gap30_w24.csv")
    assert any(r[judge.SENS_MDE_COL] for r in with_smp), "標本を渡した感度で MDE が空のまま"
    assert all(r[judge.SENS_MDE_COL] == "" for r in without)
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert s["感度(観測のみ)"]["gap30_w8"]["MDE 列"] == "出す"
    assert s["感度(観測のみ)"]["gap30_w8"]["標本(MDE の p・s)"] == str(smp30)
    assert s["感度(観測のみ)"]["gap30_w24"]["MDE 列"] == "空"
    assert s["感度(観測のみ)"]["gap30_w24"]["MDE 列が空の理由"]
    # 感度は判定に 1 行も入らない
    assert len(read_rows(out)) == 576


def test_effective_reps_are_reported_per_cell(tmp_path):
    """**決定 2''**: SE の推定に使えた有限な複製の本数を列に出す。"""
    code, out = run_judge(tmp_path, days=20, per_day=10)
    assert code == 0
    rows = read_rows(out)
    assert "有限な複製の本数" in rows[0]
    vals = [int(r["有限な複製の本数"]) for r in rows if r["有限な複製の本数"] != ""]
    assert vals and max(vals) <= judge.REPS
    # 反復を指定どおり使えたセルがあること(全部が落ちているわけではない)
    assert any(v == judge.REPS for v in vals)
    # 観測のみの表には出さない(ブートストラップを掛けていないため)
    assert "有限な複製の本数" not in judge.OBS_HEADER


def test_a_cell_without_a_finite_t_is_unknown_not_undetected(tmp_path):
    """**決定 1''**: `t` が非有限のセルは「不明(t 未算出)」で、「検出されず」にしない。

    実群と対照の値を全部同じにすると、日を引き直しても差が動かず SE = 0 になる
    (`bootstrap_diff` は `se > 0` でなければ `t = nan` を返す)。
    """
    def constant(kind, d, i, h):
        return 1

    code, out = run_judge(tmp_path, reach=constant, days=20, per_day=10)
    assert code == 0
    rows = read_rows(out)
    flat = [r for r in rows if r["判定"] == judge.UNKNOWN_T]
    assert flat, "t が非有限のセルが 1 つも作れていないので、この試験は何も測れていない"
    assert all(r["検出力"] == "t 未算出" for r in flat)
    assert all(not r["t"] for r in flat)          # t の欄は空
    assert all("検出されず" not in r["判定"] for r in flat)


def test_n2_under_30_is_unknown_too(tmp_path):
    """**決定 20''**: 対照 (ii) の n2 にも 30 を当てる。"""
    def few_controls(kind, d, i, h):
        if kind == "control_matched" and i >= 1:
            return ""            # 対照側だけ欠測にする(n2 を小さくする)
        return i % 2

    code, out = run_judge(tmp_path, reach=few_controls, days=20, per_day=40)
    assert code == 0
    rows = {(r["観測量"], r["群"]): r for r in read_rows(out)}
    v = rows[("reach_back_vwap_5m", "全体")]
    assert int(v["n1"]) >= 30 and int(v["n2"]) == 20
    assert v["判定"] == judge.UNKNOWN_N2 and v["検出力"] == "n2 < 30"


def test_the_axis_kinds_are_checked_against_the_frozen_map(tmp_path):
    """**決定 3''**: 測った作り方が事前登録の固定と違えば「[止め]」で終わる。

    対照行に `implied_leverage`(固定では inherit)の値を入れると own と測れるので、
    固定と食い違う。**測った側に合わせ直さず、1 ファイルも書かずに止まる。**
    """
    import csv as _csv
    r8 = make_run(tmp_path / "run_w8", days=20, per_day=10, reach=reach_four_branches)
    r24 = make_run(tmp_path / "run_w24", days=20, per_day=10, reach=reach_four_branches,
                   window_hours=24)
    p = r8 / "table.csv"
    rows = list(_csv.DictReader(p.open(encoding="utf-8", newline="")))
    for r in rows:
        if r["kind"] == "control_matched":
            r["implied_leverage"] = "3.0"
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    out = tmp_path / "out"
    code = judge.main([
        "--run-w8", str(r8), "--run-w24", str(r24),
        "--sample-w8", str(as_sample(r8, tmp_path / "s8")),
        "--sample-w24", str(as_sample(r24, tmp_path / "s24", window_hours=24)),
        "--out-dir", str(out), "--root", str(open_gate(tmp_path / "root")),
    ] + sens_required_args(tmp_path))
    assert code == 1
    assert not (out / "judgment_576.csv").exists(), "固定と食い違っているのに表が書かれている"
    # 素の走行では食い違いが 0 件であること
    assert judge.check_axis_kinds(judge.Run(judge.RUN_W8, r24)) == []


def test_the_root_cannot_be_swapped_for_a_real_backtest_out_dir(tmp_path):
    """**決定 10''**: 本番の出力先に試験用の台帳は使えない。"""
    repo_out = ROOT / "backtest_data" / "o3c_reaction_20260918_judge_試験用"
    bad = judge.check_root_for_out_dir(repo_out, tmp_path)
    assert bad and "backtest_data" in bad[0]
    # リポジトリ直下の root なら通る
    assert judge.check_root_for_out_dir(repo_out, ROOT) == []
    # 出力先がリポジトリの外なら、どの root でも当たらない(試験はここを通る)
    assert judge.check_root_for_out_dir(tmp_path / "out", tmp_path) == []
    # 実際に main を通しても止まり、ディレクトリは作られない
    r8 = make_run(tmp_path / "run_w8", days=3, per_day=4, reach=reach_four_branches)
    code = judge.main([
        "--run-w8", str(r8), "--run-w24", str(r8),
        "--sample-w8", str(r8), "--sample-w24", str(r8),
        "--out-dir", str(repo_out), "--root", str(tmp_path),
    ] + sens_required_args(tmp_path))
    assert code == 1
    assert not repo_out.exists(), "止めたのに本番側にディレクトリができている"


def test_forbidden_words_stop_before_any_file_is_written(tmp_path, monkeypatch):
    """**決定 11''**: 判定語の走査は表を書く前。見つかれば 1 ファイルも書かない。

    走査の対象が実際に行の中身であることを示すため、禁じた語の一覧を
    出力に必ず現れる語(群の名前)に差し替えて測る。
    """
    monkeypatch.setattr(judge, "FORBIDDEN", ("C_SELL",))
    out = tmp_path / "out"
    code, _ = run_judge(tmp_path, days=10, per_day=6, out=out)
    assert code == 1
    assert not out.exists(), "判定語が混ざっているのに出力ディレクトリができている"


def test_the_pairing_must_be_one_to_one(tmp_path):
    """**決定 12''**: 同じ相手を 2 つの対照が指していたら「[止め]」。"""
    import csv as _csv
    r8 = make_run(tmp_path / "run_w8", days=20, per_day=10, reach=reach_four_branches)
    r24 = make_run(tmp_path / "run_w24", days=20, per_day=10, reach=reach_four_branches,
                   window_hours=24)
    p = r8 / "table.csv"
    rows = list(_csv.DictReader(p.open(encoding="utf-8", newline="")))
    mat = [r for r in rows if r["kind"] == "control_matched"]
    mat[1]["matched_liq_id"] = mat[0]["matched_liq_id"]      # 同じ相手を 2 つが指す
    mat[1]["day"] = mat[0]["day"]
    mat[1]["bin_pct"] = mat[0]["bin_pct"]
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    run = judge.Run(judge.RUN_W8, r8)
    bad = judge.check_pairing(run)
    assert any("重複" in b for b in bad), bad
    assert any("引けた相手の件数" in b for b in bad), bad
    out = tmp_path / "out"
    code = judge.main([
        "--run-w8", str(r8), "--run-w24", str(r24),
        "--sample-w8", str(as_sample(r8, tmp_path / "s8")),
        "--sample-w24", str(as_sample(r24, tmp_path / "s24", window_hours=24)),
        "--out-dir", str(out), "--root", str(open_gate(tmp_path / "root")),
    ] + sens_required_args(tmp_path))
    assert code == 1
    assert not (out / "judgment_576.csv").exists()


def test_both_tables_carry_the_control_axis_kind_column(tmp_path):
    """**決定 22''**: 行単位で読む人が 14 群と 34 群を取り違えないようにする。"""
    code, out = run_judge(tmp_path, days=20, per_day=10, sens=["gap30_w8"])
    assert code == 0
    for name in ("judgment_576.csv", "observation_only.csv",
                 "observation_only_gap30_w8.csv"):
        rows = read_rows(out, name)
        assert "対照(ii)の軸の作り方" in rows[0], name
        assert {r["対照(ii)の軸の作り方"] for r in rows} <= {
            judge.AX_OWN, judge.AX_PARTNER_SIGN, judge.AX_INHERIT}
    rows = {(r["観測量"], r["群"]): r for r in read_rows(out)}
    assert rows[("reach_back_vwap_5m", "C_SELL")]["対照(ii)の軸の作り方"] == judge.AX_INHERIT
    assert rows[("reach_back_vwap_5m", "D_Q1")]["対照(ii)の軸の作り方"] == judge.AX_OWN
    assert (rows[("reach_back_vwap_5m", "A2_W8h_Q1")]["対照(ii)の軸の作り方"]
            == judge.AX_PARTNER_SIGN)


def test_the_w24_flat_groups_recut_their_own_cuts(tmp_path):
    """**決定 20'**: W = 24h 側の 12 群は W = 24h の実群で切り直す。"""
    r8 = make_run(tmp_path / "r8", days=6, per_day=12, reach=reach_four_branches)
    r24 = make_run(tmp_path / "r24", days=6, per_day=12, reach=reach_four_branches,
                   window_hours=24)
    # W = 24h 側の doi_pre_1h をずらす(切り値が違うことが見えるようにする)
    import csv as _csv
    p = r24 / "table.csv"
    rows = list(_csv.DictReader(p.open(encoding="utf-8", newline="")))
    for r in rows:
        r["doi_pre_1h"] = str(float(r["doi_pre_1h"]) * 3.0 + 500.0)
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    run8, run24 = judge.Run(judge.RUN_W8, r8), judge.Run(judge.RUN_W24, r24)
    g8 = {g.name: g for g in judge.build_groups(run8, run24)}
    g24 = {g.name: g for g in judge.build_flat_groups_w24(run24)}
    assert g8["D_Q1"].cuts != g24["D_Q1"].cuts
    assert g24["D_Q1"].cuts == judge.tertile_cuts(run24.values("liq", "doi_pre_1h"))
    assert g8["D_Q1"].cuts == judge.tertile_cuts(run8.values("liq", "doi_pre_1h"))


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
    # **決定 8'(走行前の再監査(3 回目)の指摘 8)で D1 が 54 -> 53 になった。**
    # 標本 6 日には相手が mixed 束の合わせた対照が 1 件あり、それが D1 に入っていた。
    # `table.csv` の行としては 54 / 69 / 88 + NA 2 = 213 のままである(下の 2 行で測る)。
    assert mat == [53, 69, 88]
    assert run.n_dropped_mixed_partner == 1
    assert sum(mat) + run.n_dropped_mixed_partner + 2 == 213   # NA 2 = doi_pre_1h が空
    assert abs(run.w_sell() - 117 / 224) < 1e-12   # §6.1 の参考値 0.5223
    assert judge.check_pairing(run) == []          # サニティ #14 が標本でも通る
    assert run.pairing_worst_bin_pct_gap <= judge.MATCH_TOL_PCT + 1e-9


# ==========================================================================
# 走行前の再監査(5 回目)で足したもの
# ==========================================================================
def test_reps_and_seed_are_constants_and_not_flags(tmp_path):
    """**決定 1'''(5 回目の指摘 1)**: 反復回数と種は定数で、引数では変えられない。

    **開封の後に `--reps` を変えて読みを引き直せる経路を閉じる**(A-6)。
    """
    assert judge.REPS == 2000 and judge.SEED == 1
    text = (ROOT / "scripts" / "o3c_reaction_judge.py").read_text(encoding="utf-8")
    assert 'add_argument("--reps"' not in text and 'add_argument("--seed"' not in text
    # 引数として渡すと argparse が拒否する(終了コード 2)
    r8 = make_run(tmp_path / "run_w8", days=3, per_day=4, reach=reach_four_branches)
    base = ["--run-w8", str(r8), "--run-w24", str(r8),
            "--sample-w8", str(r8), "--sample-w24", str(r8),
            "--out-dir", str(tmp_path / "out"), "--root", str(tmp_path)]
    for flag, val in (("--reps", "10"), ("--seed", "2")):
        with pytest.raises(SystemExit) as e:
            judge.main(base + [flag, val])
        assert e.value.code == 2, flag
    # summary にも「定数」と残る
    code, out = run_judge(tmp_path / "ok", days=10, per_day=6)
    assert code == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert "定数" in s["seed と reps の出所"]


def test_sanity_14_is_applied_to_the_sample_runs_too(tmp_path):
    """**決定 2'''(5 回目の指摘 2)**: サニティ #14 は標本の走行にも掛かる。

    **標本側だけ**を壊す(判定の走行は無傷)。**それでも 1 枚も書かずに止まる。**
    壊れたのが標本なら MDE の `p`・`s` の母集団が黙って変わるためである。
    """
    import csv as _csv
    r8 = make_run(tmp_path / "run_w8", days=20, per_day=10, reach=reach_four_branches)
    r24 = make_run(tmp_path / "run_w24", days=20, per_day=10, reach=reach_four_branches,
                   window_hours=24)
    s8 = as_sample(r8, tmp_path / "s8")
    s24 = as_sample(r24, tmp_path / "s24", window_hours=24)
    p = s8 / "table.csv"                      # 標本の側だけ壊す
    rows = list(_csv.DictReader(p.open(encoding="utf-8", newline="")))
    mat = [r for r in rows if r["kind"] == "control_matched"]
    mat[1]["matched_liq_id"] = mat[0]["matched_liq_id"]
    mat[1]["day"], mat[1]["bin_pct"] = mat[0]["day"], mat[0]["bin_pct"]
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    # 判定の走行の側は無傷である(= 止まる理由が標本であることを示す)
    assert judge.check_pairing(judge.Run(judge.RUN_W8, r8)) == []
    out = tmp_path / "out"
    code = judge.main([
        "--run-w8", str(r8), "--run-w24", str(r24),
        "--sample-w8", str(s8), "--sample-w24", str(s24),
        "--out-dir", str(out), "--root", str(open_gate(tmp_path / "root")),
    ] + sens_required_args(tmp_path))
    assert code == 1
    assert not (out / "judgment_576.csv").exists(), "標本の 1 対 1 が崩れているのに表が書かれている"


def test_the_run_dirs_must_match_their_names(tmp_path):
    """**決定 12'''(5 回目の指摘 12)**: `summary.json` の `params` を名前と突き合わせる。

    **前版は渡されたディレクトリを無条件に `gap60_w8` / `gap60_w24` と名付けていた。**
    **迂回する旗は作らない**(試験用に `summary.json` を差し替えた一時ディレクトリで測る)。
    """
    r8 = make_run(tmp_path / "run_w8", days=10, per_day=6, reach=reach_four_branches)
    r24 = make_run(tmp_path / "run_w24", days=10, per_day=6, reach=reach_four_branches,
                   window_hours=24)
    s8 = as_sample(r8, tmp_path / "s8")
    s24 = as_sample(r24, tmp_path / "s24", window_hours=24)
    root = open_gate(tmp_path / "root")

    def run(**kw):
        args = {"run_w8": r8, "run_w24": r24, "sample_w8": s8, "sample_w24": s24}
        args.update(kw)
        out = tmp_path / f"out_{len(list(tmp_path.iterdir()))}"
        code = judge.main([
            "--run-w8", str(args["run_w8"]), "--run-w24", str(args["run_w24"]),
            "--sample-w8", str(args["sample_w8"]),
            "--sample-w24", str(args["sample_w24"]),
            "--out-dir", str(out), "--root", str(root)]
            + sens_required_args(tmp_path, args.get("have", ()))
            + list(args.get("extra", [])))
        return code, out

    # (1) W を取り違えて渡す(24h の走行を --run-w8 に)
    code, out = run(run_w8=r24)
    assert code == 1 and not (out / "judgment_576.csv").exists()
    # (2) 標本(mode sample)を判定の走行として渡す
    code, out = run(run_w8=s8)
    assert code == 1 and not (out / "judgment_576.csv").exists()
    # (3) 判定の走行(mode full・456 日)を標本として渡す
    code, out = run(sample_w8=r8)
    assert code == 1 and not (out / "judgment_576.csv").exists()
    # (4) gap が名前と違う感度 = **その感度の表だけ書かれない**(決定 2'''''。7 回目の指摘 2)。
    #     **判定の表は書く**(感度の行は 576 にも α にも F1 の読みにも 1 行も入らないため)。
    bad = make_run(tmp_path / "sens_bad", days=10, per_day=6,
                   reach=reach_four_branches, gap_sec=60)
    code, out = run(have=("gap30_w8",), extra=["--sens", f"gap30_w8={bad}"])
    assert code == 0 and (out / "judgment_576.csv").exists()
    assert not (out / "observation_only_gap30_w8.csv").exists()
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert "gap30_w8" in s["感度の走行の検査(決定 2''''')"]["表を書かなかった感度"]
    # (5) 名前が gap<秒>_w<時間> の形でない感度 = 4 本の要求に足りないので止まる
    ok = make_run(tmp_path / "sens_ok", days=10, per_day=6,
                  reach=reach_four_branches, gap_sec=30)
    code, out = run(extra=["--sens", f"別の名前={ok}"])
    assert code == 1 and not (out / "judgment_576.csv").exists()
    # (6) 名前どおりならそのまま通る
    code, out = run(have=("gap30_w8",), extra=["--sens", f"gap30_w8={ok}"])
    assert code == 0 and (out / "observation_only_gap30_w8.csv").exists()
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert "判定の側が食い違えば" in s["走行の params の検査"]
    # この回は感度 gap30_w8 が名前どおりなので、落ちたのは中身を作っていない 3 本だけ
    assert "gap30_w8" not in s["感度の走行の検査(決定 2''''')"]["表を書かなかった感度"]
    assert s["標本の走行(サニティ #14 と params の検査を掛けた)"][
        "gap60_w8(標本)"]["params"]["mode"] == "sample"
    # 迂回する旗を作っていない
    text = (ROOT / "scripts" / "o3c_reaction_judge.py").read_text(encoding="utf-8")
    assert "allow-sample-as-run" not in text and "--skip-params" not in text


def test_low_reps_cells_are_listed_in_the_summary(tmp_path):
    """**決定 16'''(5 回目の指摘 16)**: 本数が指定に満たないセルを一覧で出す。

    **閾値は置かない**(A-12)。**本数と `1/√(2·n)` を出すだけである。**
    """
    code, out = run_judge(tmp_path, days=20, per_day=10)
    assert code == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    lst = s["有限な複製の本数"]["指定した反復回数に満たないセルの一覧(検定したセルだけ)"]
    assert s["有限な複製の本数"][
        "指定した反復回数に満たないセルの数(検定したセルだけ)"] == len(lst)
    rows = {(r["観測量"], r["群"], r["h"]): r for r in read_rows(out)}
    # **決定 12''''(6 回目の指摘 12)**: 群が空 / n < 30 のセルは一覧に入れない
    untested = sum(1 for r in read_rows(out)
                   if r["判定"] in (judge.UNKNOWN_N, judge.UNKNOWN_N2))
    assert s["有限な複製の本数"]["群が空 / n < 30 で検定していないセル数"] == untested
    for c in lst:
        assert c["有限な複製の本数"] < judge.REPS
        assert c["n1"] >= judge.MIN_N and c["n2"] >= judge.MIN_N
        assert c["1/√(2·n)"] is not None
        assert int(rows[(c["観測量"], c["群"], str(c["h"]))]["有限な複製の本数"]) \
            == c["有限な複製の本数"]
        if c["有限な複製の本数"] > 0:
            assert abs(c["1/√(2·n)"]
                       - (2 * c["有限な複製の本数"]) ** -0.5) < 1e-6


def test_the_empty_mde_reason_does_not_talk_about_the_inventory(tmp_path):
    """**決定 3'''(5 回目の指摘 3)**: 「在庫に無い」と書かない(在庫を見ていないため)。"""
    code, out = run_judge(tmp_path, days=20, per_day=10, sens=["gap30_w8"])
    assert code == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    why = s["感度(観測のみ)"]["gap30_w8"]["MDE 列が空の理由"]
    assert ":SAMPLE_DIR" in why and "在庫の有無はこの道具では見ていない" in why
    assert "在庫に無い" not in why
    # 渡した標本の一覧が残る(MDE の p・s の出所のすべて)
    lst = s["渡した標本ディレクトリの一覧"]
    assert set(lst["判定の走行"]) == {judge.RUN_W8, judge.RUN_W24}
    assert lst["感度の走行"] == {}


# ==========================================================================
# 12. 走行前の再監査(6 回目)で足した機械
# ==========================================================================
def test_the_frozen_run_settings_are_checked(tmp_path):
    """**決定 1''''(6 回目の指摘 1)**: `mmr` / `seed` / `bin_pct` / `match_order`。

    **前版は `--mmr` を付け忘れた走行でも 48 群・576 行を通り、
    軸 E の 72 行が黙って「不明(n < 30)」になった**(監査の実測)。
    **通る側と止まる側の両方を測る。**
    """
    # 通る側(既定は mmr 0.004 / seed 1 / bin_pct 0.1 / match_order table)
    code, out = run_judge(tmp_path / "ok", days=10, per_day=6)
    assert code == 0 and (out / "judgment_576.csv").exists()

    # 止まる側(4 つとも 1 つずつ崩す)
    for i, bad in enumerate(({"mmr": None}, {"mmr": 0.005}, {"seed": 2},
                             {"bin_pct": 0.2}, {"match_order": "reversed"})):
        code, out = run_judge(tmp_path / f"ng{i}", days=10, per_day=6,
                              run_params=bad)
        assert code == 1, bad
        assert not (out / "judgment_576.csv").exists(), bad
        # **決定 2'''''**: 判定の側が破れた回は stopped.txt に破れた検査が残る。
        assert (out / judge.STOPPED_NAME).exists(), bad


def test_the_frozen_run_settings_are_checked_on_the_sensitivity_runs_too(tmp_path):
    """**決定 1''''**: 感度 4 本にも同じ 4 つを当てる。

    **決定 2'''''(7 回目の指摘 2)で止まり方が変わった**: 感度で破れたときは
    **その感度の表だけ書かず、判定の表は書く。**破れた理由は `summary.json` に残る。
    """
    r8 = make_run(tmp_path / "run_w8", days=10, per_day=6, reach=reach_four_branches)
    r24 = make_run(tmp_path / "run_w24", days=10, per_day=6,
                   reach=reach_four_branches, window_hours=24)
    bad = make_run(tmp_path / "sens_bad", days=10, per_day=6,
                   reach=reach_four_branches, gap_sec=30,
                   params_override={"mmr": None})
    out = tmp_path / "out"
    code = judge.main([
        "--run-w8", str(r8), "--run-w24", str(r24),
        "--sample-w8", str(as_sample(r8, tmp_path / "s8")),
        "--sample-w24", str(as_sample(r24, tmp_path / "s24", window_hours=24)),
        "--out-dir", str(out), "--root", str(open_gate(tmp_path / "root")),
        "--sens", f"gap30_w8={bad}"] + sens_required_args(tmp_path, ("gap30_w8",)))
    assert code == 0 and (out / "judgment_576.csv").exists()
    assert not (out / "observation_only_gap30_w8.csv").exists()
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    dropped = s["感度の走行の検査(決定 2''''')"]["表を書かなかった感度"]["gap30_w8"]
    assert any("mmr" in d["理由"] for d in dropped), dropped


def test_the_approval_comes_from_the_prereg_field(tmp_path):
    """**決定 2''''(6 回目の指摘 2)**: `--approval` の番号は事前登録 §14.4 の欄から読む。

    **迂回する旗は無い**ので、`--root` を一時ディレクトリにして
    **事前登録の行を差し替えた写し**を置いて測る(リードの決定の逐語のとおり)。
    """
    # (1) 欄が「(まだ無い)」なら止まる
    root = open_gate(tmp_path / "root_empty")
    write_prereg(root, "(まだ無い。オーナーの応答を待っている。)")
    code, out = run_judge(tmp_path / "a", days=10, per_day=6, root=root)
    assert code == 1 and not out.exists()

    # (2) 欄の L 番号と走行の params.approval が違えば止まる
    root2 = open_gate(tmp_path / "root_other")
    write_prereg(root2, "L-201")
    code, out = run_judge(tmp_path / "b", days=10, per_day=6, root=root2)
    assert code == 1 and not (out / "judgment_576.csv").exists()

    # (3) 一致すれば通り、summary に出所が残る
    code, out = run_judge(tmp_path / "c", days=10, per_day=6)
    assert code == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert s["承認の L 番号(決定 2'''')"]["値"] == APPROVAL
    assert judge.PREREG_REL in s["承認の L 番号(決定 2'''')"]["出所"]

    # (4) 事前登録そのものが無ければ止まる
    root3 = tmp_path / "root_none"
    (root3 / "docs" / "AUDITOR").mkdir(parents=True)
    (root3 / "docs" / "AUDITOR" / "ACTION_LOG.md").write_text(
        (open_gate(tmp_path / "root_src") / "docs" / "AUDITOR" / "ACTION_LOG.md"
         ).read_text(encoding="utf-8"), encoding="utf-8")
    code, out = run_judge(tmp_path / "d", days=10, per_day=6, root=root3)
    assert code == 1 and not out.exists()

    # (5) 迂回する旗を作っていない(承認の番号を引数で渡す口は無い)
    text = (ROOT / "scripts" / "o3c_reaction_judge.py").read_text(encoding="utf-8")
    assert 'add_argument("--approval"' not in text
    assert "--skip-approval" not in text and "--no-approval" not in text


def test_reps_and_seed_are_checked_against_the_literals_at_run_time(tmp_path):
    """**決定 4''''(6 回目の指摘 4)**: モジュール属性の差し替えを実行時に止める。

    **引数を消しただけでは閉じていなかった**(6 回目の監査の実測:
    `judge.REPS = 50` を代入して `main()` を呼ぶと表が全部書かれた)。
    """
    for bad in ({"REPS": 50}, {"SEED": 2}):
        with swapped(**bad):
            code, out = run_judge(tmp_path / f"ng{list(bad)[0]}", days=10, per_day=6)
        assert code == 1, bad
        assert not out.exists(), bad
    # 突き合わせの相手はリテラルである(定数と同じ値を 2 か所に持っている)
    assert judge.REPS_FROZEN_LITERAL == 2000 and judge.SEED_FROZEN_LITERAL == 1
    assert judge.REPS == 2000 and judge.SEED == 1


def test_the_mde_carries_its_unit(tmp_path):
    """**決定 5''''(6 回目の指摘 5)**: 「検出されず」の MDE に単位を付ける。"""
    # 固定表に穴が無い(系統は全部単位を持つ)
    for col, _k, _h in judge.judge_systems() + judge.observation_systems():
        assert judge.mde_unit(col), col
    assert judge.mde_unit("reach_back_vwap_60m") == judge.UNIT_RATIO
    assert judge.mde_unit("bp_5m_reactdir") == judge.UNIT_BP
    assert judge.mde_unit("reach_back_node_sec") == judge.UNIT_SEC
    assert judge.mde_unit("doi_pre_1h") == judge.UNIT_QTY
    # 純関数として: 単位が判定語に入る
    v, _ = judge.decide(100, 100, 1.0, 0.01, 0.05, judge.UNIT_RATIO)
    assert v == "検出されず(MDE = 0.050000 割合)"
    # 表の側: 判定の 576 行の「検出されず」はすべて「割合」で終わる
    code, out = run_judge(tmp_path)
    assert code == 0
    got = [r["判定"] for r in read_rows(out) if r["判定"].startswith("検出されず")]
    assert got and all(r.endswith(" 割合)") for r in got), got[:3]


def test_axis_kinds_are_checked_on_the_sample_runs_too(tmp_path):
    """**決定 8''''(6 回目の指摘 8)**: 軸の作り方の検査を標本の走行にも掛ける。

    **標本の側だけを壊し、判定の走行が無傷でも止まることを測る。**
    """
    r8 = make_run(tmp_path / "run_w8", days=10, per_day=6, reach=reach_four_branches)
    r24 = make_run(tmp_path / "run_w24", days=10, per_day=6,
                   reach=reach_four_branches, window_hours=24)
    s8 = as_sample(r8, tmp_path / "s8")
    s24 = as_sample(r24, tmp_path / "s24", window_hours=24)
    # 標本の対照行に `implied_leverage` を入れる(固定は inherit なので食い違う)
    rows = list(csv.DictReader((s8 / "table.csv").open(encoding="utf-8", newline="")))
    for r in rows:
        if r["kind"] != "liq":
            r["implied_leverage"] = "3.0"
    with (s8 / "table.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    out = tmp_path / "out"
    code = judge.main([
        "--run-w8", str(r8), "--run-w24", str(r24),
        "--sample-w8", str(s8), "--sample-w24", str(s24),
        "--out-dir", str(out), "--root", str(open_gate(tmp_path / "root"))]
        + sens_required_args(tmp_path))
    assert code == 1
    assert not (out / "judgment_576.csv").exists(), "標本側の軸の作り方が固定と違うのに表が書かれている"


def test_the_sample_dirs_must_match_their_window_and_gap(tmp_path):
    """**決定 9''''(6 回目の指摘 9)**: 標本側にも `window_hours` と `gap_ms` を当てる。

    **前版は `mode` と日数の 2 つしか見ておらず、W を取り違えても止まらなかった。**
    """
    r8 = make_run(tmp_path / "run_w8", days=10, per_day=6, reach=reach_four_branches)
    r24 = make_run(tmp_path / "run_w24", days=10, per_day=6,
                   reach=reach_four_branches, window_hours=24)
    s8 = as_sample(r8, tmp_path / "s8")
    s24 = as_sample(r24, tmp_path / "s24", window_hours=24)
    root = open_gate(tmp_path / "root")

    def run(sample_w8, sample_w24, tag):
        out = tmp_path / f"out_{tag}"
        return judge.main([
            "--run-w8", str(r8), "--run-w24", str(r24),
            "--sample-w8", str(sample_w8), "--sample-w24", str(sample_w24),
            "--out-dir", str(out), "--root", str(root)]
            + sens_required_args(tmp_path)), out

    # (1) W = 24h の標本を --sample-w8 に渡す(前版では止まらなかった取り違え)
    #     **決定 2''''' で、判定の側が破れた回は stopped.txt だけが書かれる**(表は 1 枚も無い)。
    code, out = run(s24, s24, "swap")
    assert code == 1 and not (out / "judgment_576.csv").exists()
    assert (out / judge.STOPPED_NAME).exists()
    # (2) gap が違う標本
    s30 = as_sample(r8, tmp_path / "s30", gap_sec=30)
    code, out = run(s30, s24, "gap")
    assert code == 1 and not (out / "judgment_576.csv").exists()
    # (3) 正しく渡せば通る
    code, out = run(s8, s24, "ok")
    assert code == 0 and (out / "judgment_576.csv").exists()


def test_f1_must_have_twelve_cells_or_nothing_is_written(tmp_path):
    """**決定 13''''(6 回目の指摘 13)**: 12 セルでなければ 1 ファイルも書かない。

    **前版は「読めない(12 セルのはずが N セル)」を返すだけで、
    そのまま全部の表が書かれ、終了コードは 0 だった。**
    """
    with swapped(F1_GROUP="この群は 48 群に無い"):
        code, out = run_judge(tmp_path, days=10, per_day=6)
    assert code == 1
    assert not out.exists(), "F1 の 12 セルが揃っていないのに表が書かれている"


# ==========================================================================
# 走行前の再監査(7 回目)の処置
# ==========================================================================
def test_all_four_sensitivity_runs_must_be_passed(tmp_path):
    """**決定 2'''''(7 回目の指摘 2)**: `--sens` は §14.2 の 4 本とも渡す。

    **感度の検査が破れても判定の表を書く形にしたので、「渡さなければ検査もされない」
    という抜け道が空く。**先に塞ぐ(**1 本でも欠ければ表を 1 枚も書かない**)。
    """
    r8 = make_run(tmp_path / "run_w8", days=10, per_day=6, reach=reach_four_branches)
    r24 = make_run(tmp_path / "run_w24", days=10, per_day=6,
                   reach=reach_four_branches, window_hours=24)
    s8 = as_sample(r8, tmp_path / "s8")
    s24 = as_sample(r24, tmp_path / "s24", window_hours=24)
    root = open_gate(tmp_path / "root")

    def run(sens_args, tag):
        out = tmp_path / f"out_{tag}"
        return judge.main([
            "--run-w8", str(r8), "--run-w24", str(r24),
            "--sample-w8", str(s8), "--sample-w24", str(s24),
            "--out-dir", str(out), "--root", str(root)] + sens_args), out

    # (1) 1 本も渡さない
    code, out = run([], "none")
    assert code == 1 and not out.exists()
    # (2) 3 本しか渡さない
    three = sens_required_args(tmp_path, ("gap180_w24",))
    code, out = run(three, "three")
    assert code == 1 and not out.exists()
    # (3) 4 本渡せば通る(中身が無い感度はその表だけ書かれない)
    code, out = run(sens_required_args(tmp_path), "four")
    assert code == 0 and (out / "judgment_576.csv").exists()
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    rec = s["感度の走行の検査(決定 2''''')"]
    assert rec["渡すべき感度"] == list(judge.SENS_REQUIRED)
    assert set(rec["表を書かなかった感度"]) == set(judge.SENS_REQUIRED)
    # 迂回する旗を作っていない
    text = (ROOT / "scripts" / "o3c_reaction_judge.py").read_text(encoding="utf-8")
    assert "--no-sens" not in text and "--skip-sens" not in text


def test_a_broken_sensitivity_run_does_not_stop_the_judgment_tables(tmp_path):
    """**決定 2'''''**: 感度 1 本が破れても 576 行は書かれる(その感度の表だけ書かない)。

    **前版は感度 1 本の食い違いで「表を 1 枚も書かずに終わる」形だったので、
    456 日を 6 本開けたうえで 1 行も出ない帰結になりえた**(7 回目の指摘 2)。
    """
    bad = make_run(tmp_path / "sens_bad", days=10, per_day=6,
                   reach=reach_four_branches, gap_sec=30,
                   params_override={"seed": 2})     # 凍結した種と違う
    code, out = run_judge(tmp_path, days=10, per_day=6,
                          extra=["--sens", f"gap30_w8={bad}"])
    assert code == 0
    assert len(read_rows(out)) == 576
    assert not (out / "observation_only_gap30_w8.csv").exists()
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    dropped = s["感度の走行の検査(決定 2''''')"]["表を書かなかった感度"]["gap30_w8"]
    assert any("seed" in d["理由"] for d in dropped), dropped


def test_stopped_txt_records_which_check_broke(tmp_path):
    """**決定 2'''''**: 判定の側が破れたら `stopped.txt` に破れた検査と走行を書く。

    **表は 1 枚も書かない。**§10.3 の「なぜ」を書くときの材料をここに残す。
    **決定 12(8 回目の指摘 12)で、書くのは「検査の名前・走行の名前・件数」だけになった**
    (**理由の文言も、鍵の名前も、値も書かない**。理由の全文は標準出力に出る)。
    """
    out = tmp_path / "out"
    code, out = run_judge(tmp_path, days=10, per_day=6, out=out,
                          run_params={"mmr": None})
    assert code == 1
    assert not (out / "judgment_576.csv").exists()
    text = (out / judge.STOPPED_NAME).read_text(encoding="utf-8")
    assert "params の検査" in text            # 検査の名前
    assert "gap60_w8" in text                 # 走行の名前
    assert "再走行は新しい開封" in text
    # **決定 12**: 理由の文言(鍵の名前・値)は 1 つも書かない
    assert "mmr" not in text and "0.004" not in text
    # 判定語は 1 つも書かない
    for w in judge.FORBIDDEN:
        assert w not in text, w


def test_stopped_txt_writes_no_values_only_names_and_counts(tmp_path):
    """**決定 12(8 回目の指摘 12)**: `stopped.txt` に値を 1 つも書かない。

    **`check_pairing` の理由文は `bin_pct` の差の最大値(§4 の分割軸 B の値)と
    `cascade_id` の例を含みうる。**§14.4.1 の汚染の線
    (「§4.3 の観測量も §4 の分割軸の値も含まれない」)に揃える。
    """
    # 1 対 1 が崩れた走行を作る(同じ相手を 2 つの対照が指す = `cascade_id` の例が出る)。
    r8 = make_run(tmp_path / "run_w8", days=10, per_day=6, reach=reach_four_branches)
    rows = list(csv.DictReader((r8 / "table.csv").open(encoding="utf-8", newline="")))
    ids = [r["matched_liq_id"] for r in rows if r["kind"] == "control_matched"]
    first = ids[0]
    for r in rows:
        if r["kind"] == "control_matched":
            r["matched_liq_id"] = first          # 全部を同じ相手に向ける
            r["bin_pct"] = "99"                  # 差が ±5.0 を超える
    with (r8 / "table.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    r24 = make_run(tmp_path / "run_w24", days=10, per_day=6,
                   reach=reach_four_branches, window_hours=24)
    s8 = as_sample(r8, tmp_path / "s8")
    s24 = as_sample(r24, tmp_path / "s24", window_hours=24)
    root = open_gate(tmp_path / "root")
    out = tmp_path / "out"
    code = judge.main([
        "--run-w8", str(r8), "--run-w24", str(r24),
        "--sample-w8", str(s8), "--sample-w24", str(s24),
        "--out-dir", str(out), "--root", str(root)]
        + sens_required_args(tmp_path))
    assert code == 1
    text = (out / judge.STOPPED_NAME).read_text(encoding="utf-8")
    assert "サニティ #14" in text and "gap60_w8" in text
    # 値は 1 つも出ない: `bin_pct` の差の最大も、`cascade_id` の例も
    assert "bin_pct" not in text
    assert first not in text and "binance_cm_real" not in text
    assert "最大" not in text
    # 件数(「N 件」)だけは写る
    assert "件" in text
    assert not (out / "judgment_576.csv").exists()


def test_the_audit_gate_comes_before_stopped_txt(tmp_path):
    """**決定 11(8 回目の指摘 11)**: 台帳が閉じていれば `stopped.txt` も書かない。

    **前版は `write_stopped` が `pass_audit_gate` より前にあったので、判定側が破れた回は
    台帳が閉じていても 1 ファイル書かれた。**「1 ファイルも書かない」に揃える。
    """
    root = tmp_path / "root"                 # 台帳そのものが無い = 関門は閉じている
    root.mkdir()
    write_prereg(root)
    out = tmp_path / "out"
    with pytest.raises(SystemExit) as e:
        run_judge(tmp_path, days=10, per_day=6, root=root, out=out,
                  run_params={"mmr": None})   # 判定側も破れている
    assert e.value.code == 1
    assert not out.exists(), "関門が閉じているのに stopped.txt が書かれている"
    # 実装でも関門が `write_stopped` より前にある
    text = (ROOT / "scripts" / "o3c_reaction_judge.py").read_text(encoding="utf-8")
    assert (text.index("pass_audit_gate(Path(a.root).resolve())")
            < text.index("write_stopped(Path(a.out_dir)"))


def test_the_sensitivity_runs_also_match_the_approval_number(tmp_path):
    """**決定 11'''''(7 回目の指摘 11)**: 感度 4 本も同じ 456 日を開けるので、
    `params.approval` を事前登録 §14.4 の欄と突き合わせる。

    **決定 14(8 回目の指摘 14)**: **その食い違いは判定側の破れと同じ扱いになった。**
    **表を 1 枚も書かず `stopped.txt` を書いて終わる**(リードの決定の逐語:
    「**承認外の番号で 456 日を開けた走行が 1 本でもあれば、1 周目はそこで止めて
    オーナーに報告する**」)。
    """
    other = make_run(tmp_path / "sens_other", days=10, per_day=6,
                     reach=reach_four_branches, gap_sec=30,
                     params_override={"approval": "L-999"})
    out = tmp_path / "out"
    code, out = run_judge(tmp_path, days=10, per_day=6, out=out,
                          extra=["--sens", f"gap30_w8={other}"])
    assert code == 1
    assert not (out / "judgment_576.csv").exists()
    assert not list(out.glob("observation_only*.csv"))
    text = (out / judge.STOPPED_NAME).read_text(encoding="utf-8")
    assert "承認の番号(決定 14)" in text and "gap30_w8" in text
    # **決定 12**: 番号そのもの(値)は書かない
    assert "L-999" not in text and "L-200" not in text


def test_the_judgment_runs_approval_is_named_separately_in_stopped_txt(tmp_path):
    """**決定 14(9 回目の指摘 14)**: 判定 2 本の承認の食い違いも、
    `stopped.txt` に **「承認の番号(決定 14)」**の名前で出る。

    **前版は `check_run_params` の中だったので、`params の検査(決定 12''')` の名前で
    出ていた。**`stopped.txt` は理由を書かない(決定 12)ので、
    **「承認の番号が破れた」ことを `stopped.txt` だけでは見分けられなかった。**
    """
    out = tmp_path / "out"
    code, out = run_judge(tmp_path, days=10, per_day=6, out=out,
                          run_params={"approval": "L-999"})
    assert code == 1
    assert not (out / "judgment_576.csv").exists()
    text = (out / judge.STOPPED_NAME).read_text(encoding="utf-8")
    assert "承認の番号(決定 14)" in text
    assert judge.RUN_W8 in text and judge.RUN_W24 in text
    # **params の検査とは別の名前で出る**(混ざらない)
    assert "params の検査" not in text
    # **決定 12**: 番号そのもの(値)は書かない
    assert "L-999" not in text and "L-200" not in text


def test_a_sensitivity_run_with_the_right_approval_still_passes(tmp_path):
    """**決定 14 の通る側**: 承認の番号が合っていれば、感度の他の食い違いは
    従来どおり「その走行の表だけ書かない」で済む(判定の 576 行は書く)。"""
    ok = make_run(tmp_path / "sens_ok", days=10, per_day=6,
                  reach=reach_four_branches, gap_sec=30,
                  params_override={"seed": 2})      # 承認は合っている / 種が違う
    code, out = run_judge(tmp_path, days=10, per_day=6,
                          extra=["--sens", f"gap30_w8={ok}"])
    assert code == 0
    assert len(read_rows(out)) == 576
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert s["承認の L 番号(決定 2'''')"]["突き合わせ先"] == \
        "判定 2 本 + 感度 4 本の params.approval"
    assert "感度 4 本" in s["走行の params の検査"]


def test_the_frozen_tool_commit_is_recorded_and_matched(tmp_path):
    """**決定 16(8 回目の指摘 16)+ 決定 3・15(9 回目の指摘 3・15)**:
    読みの道具の版を `summary.json` に残し、事前登録 §14.4 の
    「凍結した道具のコミット」欄と突き合わせる。

    **本版で「欄が「(まだ無い)」なら記録だけして進む」をやめた**
    (9 回目の指摘 3: **欄を空のままにすれば版の検査が 1 つも掛からなかった**)。
    """
    mine = judge.tool_commit()
    assert mine == TOOL_COMMIT
    # (1) 欄が一致 -> 通り、突き合わせの中身が summary に残る
    code, out = run_judge(tmp_path, days=10, per_day=6)
    assert code == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert s["tool_commit"] == mine
    blk = s["凍結した道具のコミット(決定 16 + 決定 3・15)"]
    assert blk["この道具の版(git rev-parse HEAD)"] == mine
    assert blk["事前登録 §14.4 の欄"] == TOOL_COMMIT
    assert blk["この道具の作業ツリー(git status --porcelain)"] == "clean"
    assert set(blk["走行ごとの版"]) >= {judge.RUN_W8, judge.RUN_W24}
    assert all(v == TOOL_COMMIT for v in blk["走行ごとの版"].values())
    assert all(v == "clean" for v in blk["走行ごとの作業ツリー"].values())
    # (2) 短縮形(先頭 7 桁)でも通る
    root4 = open_gate(tmp_path / "root4")
    write_prereg(root4, commit=TOOL_COMMIT[:7])
    code, _ = run_judge(tmp_path, days=10, per_day=6, root=root4,
                        out=tmp_path / "out4")
    assert code == 0
    # (3) 欄が別のコミット -> 「[止め]」で 1 ファイルも書かない
    root3 = open_gate(tmp_path / "root3")
    write_prereg(root3, commit="0" * 40)
    out3 = tmp_path / "out3"
    code, _ = run_judge(tmp_path, days=10, per_day=6, root=root3, out=out3)
    assert code == 1
    assert not out3.exists()
    # (4) 欄が「(まだ無い)」= 空 -> 「[止め]」(本版で変えた点)
    root5 = open_gate(tmp_path / "root5")
    write_prereg(root5, commit=None)
    out5 = tmp_path / "out5"
    code, _ = run_judge(tmp_path, days=10, per_day=6, root=root5, out=out5)
    assert code == 1
    assert not out5.exists()
    # 迂回する旗は作っていない
    text = (ROOT / "scripts" / "o3c_reaction_judge.py").read_text(encoding="utf-8")
    assert "--tool-commit" not in text and "--skip-commit" not in text
    for flag in ("--allow-dirty", "--skip-git", "--no-worktree-check"):
        assert flag not in text, flag


def test_the_tool_version_gate_checks_the_worktree_and_the_six_runs(tmp_path,
                                                                    monkeypatch):
    """**決定 3・15(9 回目の指摘 3・15)**: 版の担保を 1 本にした関門。

    **(i) 自分の作業ツリー / (ii) 6 本の版と §14.4 の欄 / (iii) 6 本の汚れ**
    の 3 つを、**通る側と止まる側の両方**で測る。
    **この試験だけは上の `_stub_tool_version` を上書きする**(`monkeypatch` は後勝ち)。
    """
    # 通る側(3 つとも満たす)
    code, out = run_judge(tmp_path, days=10, per_day=6)
    assert code == 0 and (out / "summary.json").exists()

    # (i) 読みの道具の作業ツリーが汚れている -> 1 ファイルも書かない
    monkeypatch.setattr(judge, "git_status",
                        lambda *a, **k: ("dirty", ["scripts/o3c_reaction_judge.py"]))
    out_i = tmp_path / "out_i"
    code, _ = run_judge(tmp_path, days=10, per_day=6, root=open_gate(tmp_path / "root_i"),
                        out=out_i)
    assert code == 1 and not out_i.exists()
    monkeypatch.setattr(judge, "git_status", lambda *a, **k: ("clean", []))

    # (ii) 走行の版が読みの道具と違う -> 止まる
    out_ii = tmp_path / "out_ii"
    code, _ = run_judge(tmp_path / "ii", days=10, per_day=6,
                        root=open_gate(tmp_path / "root_ii"), out=out_ii,
                        run_params={"tool_commit": "b" * 40})
    assert code == 1 and not out_ii.exists()

    # (iii) 走行のときに作業ツリーが汚れていた -> 止まる
    out_iii = tmp_path / "out_iii"
    code, _ = run_judge(tmp_path / "iii", days=10, per_day=6,
                        root=open_gate(tmp_path / "root_iii"), out=out_iii,
                        run_params={"tool_dirty": "dirty"})
    assert code == 1 and not out_iii.exists()

    # 走行に `tool_commit` の鍵が無い(この機械より前に走った出力)-> 止まる
    out_iv = tmp_path / "out_iv"
    code, _ = run_judge(tmp_path / "iv", days=10, per_day=6,
                        root=open_gate(tmp_path / "root_iv"), out=out_iv,
                        run_params={"tool_commit": None})
    assert code == 1 and not out_iv.exists()

    # 射程: 読めない感度の走行は版の検査の対象に入らない(上の通る側がその経路である)
    assert "読めない感度の走行はこの検査より前に落ちている" in (
        ROOT / "scripts" / "o3c_reaction_judge.py").read_text(encoding="utf-8")


def test_the_f1_reading_records_the_d1_cut(tmp_path):
    """**決定 2(9 回目の指摘 2)**: D1 の上側の切り値を `f1_reading.txt` と
    `summary.json` に必ず残し、**切り値が 0 以上なら射程を書く。**

    **判定は D1(最も負の 3 分位)のままで、走行の後に「負の群」へ読み替えない。**
    """
    code, out = run_judge(tmp_path, days=10, per_day=6)
    assert code == 0
    txt = (out / "f1_reading.txt").read_text(encoding="utf-8")
    assert "D1 の上側の切り値(doi_pre_1h)" in txt
    assert "射程:" in txt
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    blk = s["F1 の D1 の上側の切り値(決定 2)"]
    assert blk["群"] == judge.F1_GROUP and blk["軸の列"] == "doi_pre_1h"
    cut = blk["上側の切り値"]
    if cut is not None and cut >= 0:
        assert "D1 は負の群と一致しない" in blk["射程"]
        assert "D1 は負の群と一致しない" in txt
    # 切り値の作り方そのもの(0 以上・負・出ない、の 3 通り)
    class _G:
        def __init__(self, name, cuts):
            self.name, self.cuts = name, cuts
    v, note = judge.f1_cut_note([_G(judge.F1_GROUP, (3.5, 9.0))])
    assert v == 3.5 and "D1 は負の群と一致しない" in note
    v, note = judge.f1_cut_note([_G(judge.F1_GROUP, (-2.0, 9.0))])
    assert v == -2.0 and "負" in note
    v, note = judge.f1_cut_note([_G(judge.F1_GROUP, (float("nan"), float("nan")))])
    assert v is None and "切り値が出ない" in note
    v, note = judge.f1_cut_note([])
    assert v is None and "切り値が出ない" in note


def test_the_observation_only_table_does_not_carry_the_family_alpha_in_its_mde_column(tmp_path):
    """**決定 6'''''(7 回目の指摘 6)**: `observation_only.csv` の MDE の列見出しも
    「MDE(参考。族の α に入らない)」である。

    **この表の 2,208 行も 576 にも α にも F1 の読みにも 1 行も入らない**(§10.2)。
    **前版は感度の表だけ見出しを替えていた。**
    """
    code, out = run_judge(tmp_path, days=10, per_day=6)
    assert code == 0
    head = read_rows(out, "observation_only.csv")[0]
    assert judge.REF_MDE_COL in head
    assert judge.MDE_COL not in head
    # 判定の表は族の α の名前のままである
    assert judge.MDE_COL in read_rows(out)[0]
    assert judge.REF_MDE_COL not in read_rows(out)[0]
    assert judge.MDE_COL in read_rows(out, "f1_12cells.csv")[0]


def test_the_min_and_max_reps_come_from_tested_cells_only(tmp_path):
    """**決定 7'''''(7 回目の指摘 7)**: 「最小」「最大」も検定したセルだけから取る。

    **前版は `judge_rows` 全部から取っていたので、群が空で本数 0 のセルが混ざった。**
    """
    code, out = run_judge(tmp_path, days=20, per_day=10, n_buy=20)   # C_BUY が n < 30
    assert code == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    blk = s["有限な複製の本数"]
    assert blk["群が空 / n < 30 で検定していないセル数"] > 0, "検定していないセルが無い"
    assert blk["最小(検定したセルだけ)"] >= 2
    rows = read_rows(out)
    untested = {judge.UNKNOWN_N, judge.UNKNOWN_N2}
    tested = [int(r["有限な複製の本数"]) for r in rows
              if r["有限な複製の本数"] != "" and r["判定"] not in untested]
    assert blk["最小(検定したセルだけ)"] == min(tested)
    assert blk["最大(検定したセルだけ)"] == max(tested)
    # 標準出力の文言も同じ欄を指している
    text = (ROOT / "scripts" / "o3c_reaction_judge.py").read_text(encoding="utf-8")
    assert "最小(検定したセルだけ)" in text and '"最小"]' not in text
