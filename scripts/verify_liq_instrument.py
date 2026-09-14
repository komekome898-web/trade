#!/usr/bin/env python3
"""O-3c 測定器(`src/bot/research/liq_response.py`)の合成データ検証。

**目的**(委任元の指示、逐語): 「O-3c の測定器が、仕込んだ効果を仕込んだ大きさで
取り出せるかを、合成データで確かめる」。2026-09-13 に実データで開封したあと
欠陥が次々出て 1 日分の研究を破棄した反省から、実データに触る前にこれを測る。

**測定器そのもの(`build_cascades` / `compute_reactions` / `attach_internal_direction` /
`compute_reversal`)は一切書き換えない。** インポートしてそのまま呼ぶだけ。

使い方:
    PYTHONPATH=src python3 scripts/verify_liq_instrument.py

終了コード: 0 = 合格(素の合成データで 4 条件すべて通過し、かつ変異試験の全件
すべてで壊れたことを検出できた)。1 = 不合格(いずれか)。
"""
from __future__ import annotations

import random
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bot.research.liq_response import (  # noqa: E402
    Cascade,
    LiquidationEvent,
    PriceSeries,
    ReversalExclusionImbalance,
    ReversalReport,
    attach_internal_direction,
    build_cascades,
    compute_reactions,
    compute_reversal,
)

# --------------------------------------------------------------------------- #
# 自分で決めた値(すべてここに集める。理由はそれぞれの行に書く)
# --------------------------------------------------------------------------- #

SEED = 20260913  # 再現用の乱数の種。日付をそのまま使っただけ(意味は無い)。
N_REAL = 300      # 実カスケードの件数。SEM を noise_std/sqrt(N) 程度まで小さくしたい
                  # (下の NOISE_STD_BP=4.0 なら SEM ≈ 4/sqrt(300) ≈ 0.23bp)ので N=300 とした。
N_CONTROL = 300   # 対照窓(清算無し)の件数。実カスケードと同数(指示どおり)。
HORIZON_MIN = 15  # 反転を測る水平線。DEFAULT_HORIZONS_MIN=(1,5,15,60) のうち中庸を選んだ
                  # (1 分は短すぎてスプレッド・ノイズに埋もれやすく、60 分は他要因が混ざりやすい)。
GAP_MS = 60_000   # build_cascades の既定値をそのまま使う(測定器を変えないのと同じ理由で、
                  # 呼び出し側の既定も変えない)。
R_BP = 20.0       # 仕込む「反転」の大きさ(bp)。ノイズ(NOISE_STD_BP=4.0)に対して
                  # 十分大きく、かつ非現実的に大きすぎない値として選んだ。
I_BP_RANGE = (15.0, 60.0)  # カスケード内部の値動きの大きさ(bp)の一様分布範囲。
                            # 内部の符号がノイズで反転しない(下限 15bp >> noise std 4bp)ように
                            # 下限を noise std の 3 倍以上に取った。
NOISE_STD_BP = 4.0  # 価格に乗せるガウスノイズの標準偏差(bp)。内部の動き・反転の各区間に
                    # 独立に加える。適当に選んだ「小さくない現実的なノイズ」の値。
CASCADE_DURATION_RANGE_MS = (5_000, 45_000)  # カスケードの継続時間(5〜45 秒)。
                                              # GAP_MS=60_000 未満に収まるようにした
                                              # (カスケード内の全イベントが 1 つに束ねられる)。
N_EVENTS_RANGE = (2, 8)  # 1 カスケードあたりのイベント件数。
SLOT_MS = 2 * 3_600_000  # 各カスケード/対照窓に割り当てる時間帯の幅(2 時間)。
                          # HORIZON_MIN(最大 60 分想定)+ カスケード長 + 余白が
                          # 十分収まり、他のカスケードと絶対に重ならない値。
BASE_TS_MS = 1_700_000_000_000  # 適当な基準時刻(2023-11 ごろ)。値そのものに意味は無い。

TOLERANCE_BP = 3.0  # 条件1(効果の大きさ)の許容誤差。理由:
                     # 上の設計では score の分散は主に反転区間のノイズ(std=NOISE_STD_BP)だけで
                     # 決まり、N=300 なら SEM ≈ 0.23bp。3bp は SEM の約13倍で、健全な合成データは
                     # 確実に通す一方、条件1の変異試験(効果を半分=R/2=10bpにする→誤差10bp)は
                     # 確実に落とす、という分離を狙って選んだ。
SIGN_MATCH_THRESHOLD = 0.95  # 条件4(符号)。内部方向の符号がノイズで反転する確率は
                              # I_BP_RANGE の下限15bpに対しnoise std4bpなので極めて低いが、
                              # 完全な100%を要求すると稀な反転で誤って不合格になるため
                              # 0.95 を閾値にした。
ZERO_CI_Z = 1.96  # 95% 信頼区間の z 値(正規近似)。


# --------------------------------------------------------------------------- #
# 合成データの生成
# --------------------------------------------------------------------------- #

@dataclass
class SyntheticBundle:
    events: list[LiquidationEvent]
    control_cascades: list[Cascade]
    prices: PriceSeries
    n_real: int
    n_control: int


def build_synthetic(seed: int, r_bp: float, n_real: int = N_REAL, n_control: int = N_CONTROL,
                     horizon_min: int = HORIZON_MIN) -> SyntheticBundle:
    """合成データを 1 セット作る。`r_bp` が仕込む反転の大きさ(0 なら零効果テスト用)。"""
    rng = random.Random(seed)
    roles = ["real"] * n_real + ["control"] * n_control
    rng.shuffle(roles)

    events: list[LiquidationEvent] = []
    control_cascades: list[Cascade] = []
    price_points: list[tuple[int, float]] = []

    P0 = 5_000_000.0  # 基準価格(BTC/JPY 想定のスケール。値そのものに意味は無い)。

    for slot_idx, role in enumerate(roles):
        slot_start = BASE_TS_MS + slot_idx * SLOT_MS
        start_ms = slot_start + 5 * 60_000  # スロット先頭から 5 分の余白
        duration_ms = rng.randint(*CASCADE_DURATION_RANGE_MS)
        end_ms = start_ms + duration_ms
        future_ms = end_ms + horizon_min * 60_000
        assert future_ms < slot_start + SLOT_MS, "SLOT_MS が足りない(設計ミス)"

        noise1 = rng.gauss(0.0, NOISE_STD_BP)
        noise2 = rng.gauss(0.0, NOISE_STD_BP)

        if role == "real":
            side = rng.choice(["long", "short"])
            s = -1.0 if side == "long" else 1.0  # ロング強制決済 → 価格下方向
            i_bp = rng.uniform(*I_BP_RANGE)
            internal_move_bp = s * i_bp + noise1
            reversal_move_bp = -s * r_bp + noise2

            p_start = P0
            p_end = p_start * (1 + internal_move_bp / 10_000.0)
            p_future = p_end * (1 + reversal_move_bp / 10_000.0)

            n_events = rng.randint(*N_EVENTS_RANGE)
            ts_list = sorted(rng.sample(range(start_ms + 1, end_ms), n_events - 2)) \
                if n_events > 2 else []
            ts_all = [start_ms] + ts_list + [end_ms]
            for j, ts in enumerate(ts_all):
                frac = (ts - start_ms) / duration_ms if duration_ms else 0.0
                price = p_start + (p_end - p_start) * frac
                events.append(LiquidationEvent(
                    exchange="synthetic", ts_ms=ts, side=side,
                    qty=rng.uniform(0.1, 2.0), price=price,
                ))
        else:
            p_start = P0
            p_end = p_start * (1 + noise1 / 10_000.0)
            p_future = p_end * (1 + noise2 / 10_000.0)
            control_cascades.append(Cascade(
                cascade_id=f"synthetic_no_liq_{slot_idx:06d}", exchange="synthetic",
                kind="no_liquidation", start_ms=start_ms, end_ms=end_ms,
                n_events=0, total_size=0.0, direction="none",
                first_price=None, last_price=None,
            ))

        price_points.append((start_ms, p_start))
        price_points.append((end_ms, p_end))
        price_points.append((future_ms, p_future))

    prices = PriceSeries.from_trades(price_points)
    return SyntheticBundle(events=events, control_cascades=control_cascades, prices=prices,
                            n_real=n_real, n_control=n_control)


# --------------------------------------------------------------------------- #
# パイプライン(測定器の 4 本をそのまま順に呼ぶ)
# --------------------------------------------------------------------------- #

def run_pipeline(bundle: SyntheticBundle, horizon_min: int = HORIZON_MIN,
                  gap_ms: int = GAP_MS, compute_reactions_fn=compute_reactions
                  ) -> tuple[ReversalReport, dict[str, list[dict]], list[Cascade]]:
    """`build_cascades → compute_reactions_fn → attach_internal_direction → compute_reversal`。

    `compute_reactions_fn` だけ差し替え可能にしてある(変異試験で「測定器を包んで壊した版」を
    通すため。測定器の関数自体は変えない — 呼び出し側で結果を後加工するラッパーを渡すだけ)。
    """
    real_cascades = build_cascades(bundle.events, "synthetic", gap_ms=gap_ms)
    all_cascades = list(real_cascades) + list(bundle.control_cascades)

    rows = compute_reactions_fn(all_cascades, bundle.prices, horizons_min=(horizon_min,))
    rows = attach_internal_direction(rows, bundle.prices)

    real_rows = [r for r in rows if r["kind"] == "real"]
    control_rows = [r for r in rows if r["kind"] == "no_liquidation"]

    bp_key = f"bp_{horizon_min}m"
    report = compute_reversal({"real": real_rows, "control": control_rows}, bp_key)
    return report, {"real": real_rows, "control": control_rows}, real_cascades


# --------------------------------------------------------------------------- #
# 変異(測定器を壊した版。測定器自身のファイルは一切触らない)
# --------------------------------------------------------------------------- #

def mutate_drop_some(cascades, prices, horizons_min, drop_every: int = 5):
    """(a) カスケードの一部を黙って落とす(5 件に 1 件、行ごと消す)。"""
    rows = compute_reactions(cascades, prices, horizons_min=horizons_min)
    return [r for i, r in enumerate(rows) if i % drop_every != 0]


def mutate_flip_sign(cascades, prices, horizons_min):
    """(b) 反応 bp の符号を反転させる。"""
    rows = compute_reactions(cascades, prices, horizons_min=horizons_min)
    for r in rows:
        for h in horizons_min:
            col = f"bp_{h}m"
            v = r.get(col)
            if v is not None and v == v:
                r[col] = -v
    return rows


def mutate_wrong_horizon(cascades, prices, horizons_min, offset_min: int = 10):
    """(e) **測定器に別の地平線を読ませる**(2026-09-14 追加)。

    なぜ要るか: 合成データは反転を「地平線の位置ちょうどに置いた 1 段の階段」として
    仕込むので、**仕込み量はどの地平線でも同じ**である(実測: h=1/15/60 のいずれでも
    先頭スロットの反転は +18.6000bp で一致)。だから「4 本とも同じ平均が出た」ことは
    測定器が地平線を正しく読んだ証拠にならない。**その疑いをここで潰す。**

    期待する挙動: 頼んだ地平線がデータの階段とずれると、階段の手前を読むので反応は 0、
    階段より後ろだと価格点が無いので nan になり、どちらも条件 1(効果の大きさ)で落ちる。
    (実測、データ=15 分: 5 分で読むと 0.0000 / 25 分で読むと nan・n_used=0)

    **短い地平線では手前にずらせない**(h=1 のとき `max(1, 1-10)` が 1 に潰れ、
    「間違った地平線」が正しい地平線と一致して変異が空振りする。2026-09-14 に実測で発覚。
    最初の版はこれで h=1 だけ「検出できなかった」と出していた)。なので
    **10 分以下では行き過ぎ側にずらす。**
    """
    rows = compute_reactions(cascades, prices, horizons_min=horizons_min)
    wrong = [h - offset_min if h > offset_min else h + offset_min for h in horizons_min]
    bad = compute_reactions(cascades, prices, horizons_min=tuple(wrong))
    by_id = {r["cascade_id"]: r for r in bad}
    for r in rows:
        src = by_id.get(r["cascade_id"])
        for h, w in zip(horizons_min, wrong):
            r[f"bp_{h}m"] = None if src is None else src.get(f"bp_{w}m")
    return rows


def mutate_halve_effect(cascades, prices, horizons_min):
    """(c) 反応 bp を半分にする(効果を薄める)。"""
    rows = compute_reactions(cascades, prices, horizons_min=horizons_min)
    for r in rows:
        for h in horizons_min:
            col = f"bp_{h}m"
            v = r.get(col)
            if v is not None and v == v:
                r[col] = v * 0.5
    return rows


# --------------------------------------------------------------------------- #
# 4 条件の判定
# --------------------------------------------------------------------------- #

@dataclass
class ConditionResult:
    name: str
    passed: bool
    detail: str


def check_conditions(report: ReversalReport, rows: dict[str, list[dict]],
                      n_real_in: int, n_control_in: int, r_bp: float,
                      tolerance_bp: float = TOLERANCE_BP) -> list[ConditionResult]:
    results: list[ConditionResult] = []

    real_group = report.groups["real"]
    control_group = report.groups["control"]

    # 条件1: 効果の大きさ
    mean_score = real_group.mean
    diff = abs(mean_score - r_bp) if mean_score == mean_score else float("nan")
    ok1 = diff == diff and diff <= tolerance_bp
    results.append(ConditionResult(
        "1_効果の大きさ", ok1,
        f"仕込んだ R={r_bp:.2f}bp / 測定平均={mean_score:.4f}bp / |差|={diff:.4f}bp"
        f"(許容={tolerance_bp}bp)",
    ))

    # 条件2: 零効果(この関数は呼び出し側が r_bp=0 のシナリオを渡してくる前提)
    n = real_group.n_used
    if n >= 2:
        sem = statistics.stdev(real_group.scores) / (n ** 0.5)
        ci_low, ci_high = mean_score - ZERO_CI_Z * sem, mean_score + ZERO_CI_Z * sem
        ok2 = ci_low <= 0.0 <= ci_high
        results.append(ConditionResult(
            "2_零効果", ok2,
            f"平均={mean_score:.4f}bp, SEM={sem:.4f}bp, 95%CI=[{ci_low:.4f}, {ci_high:.4f}]"
            f"(0 を含むか: {ok2})",
        ))
    else:
        results.append(ConditionResult("2_零効果", False, f"n_used={n} で CI が計算できない"))

    # 条件3: 事象の数(投入 N == 最終指標まで運んだ行数)
    real_n_rows_ok = real_group.n_rows == n_real_in
    control_n_rows_ok = control_group.n_rows == n_control_in
    excl_rates = report.exclusion_rates
    ok3 = real_n_rows_ok and control_n_rows_ok
    results.append(ConditionResult(
        "3_事象の数", ok3,
        f"real: 投入{n_real_in} / report.n_rows={real_group.n_rows} / n_used={real_group.n_used} "
        f"/ exclusion_rate={excl_rates['real']:.4f} | "
        f"control: 投入{n_control_in} / report.n_rows={control_group.n_rows} "
        f"/ n_used={control_group.n_used} / exclusion_rate={excl_rates['control']:.4f}",
    ))

    # 条件4: 符号(仕込んだ反転の向き == 測定器が報告する向き)
    real_rows = rows["real"]
    bp_key = report.bp_key
    n_checked = 0
    n_match = 0
    for r in real_rows:
        internal = r.get("internal_bp")
        bp = r.get(bp_key)
        if internal is None or bp is None or internal != internal or bp != bp:
            continue
        sign_internal = 1.0 if internal > 0 else (-1.0 if internal < 0 else 0.0)
        score = -sign_internal * bp
        n_checked += 1
        # **仕込んだ効果の向きと一致するか**を見る。
        # **2026-09-14 の欠陥**: 旧版は `if r_bp > 0: (score>0 を数える) else: n_match += 1` で、
        # **`else` が r_bp<0(継続側)も飲み込んでいた**。継続側を初めて回した瞬間、
        # 符号一致率が構造的に 1.0000 になり、**変異 b(符号反転)が検出できなくなっていた**
        # (実測: 継続側 h=1/5/15/60 のすべてで `[検出できなかった(重大な発見)] b_符号を反転`)。
        # しかも表示の「[r_bp=0 のため参考値]」は `r_bp == 0` のときしか付かないので、
        # **継続側では普通の `[OK] 符号一致率=1.0000` に見えていた。**
        # これは 09-13 に焼かれた型(壊れても止まらず、もっともらしい数値を返す)そのもの。
        # 監査役の [直す]「継続側を一度も測っていない」を実行して初めて出た。
        if r_bp > 0:
            if score > 0:
                n_match += 1
        elif r_bp < 0:
            if score < 0:
                n_match += 1
        else:
            # r_bp == 0 は「向きが無い」ので符号一致に意味が無い。参考値として 1.0 にする
            # (下の表示で [r_bp=0 のため参考値] と明示し、合否は条件 2 が担う)。
            n_match += 1
    frac_match = n_match / n_checked if n_checked else float("nan")
    ok4 = (frac_match == frac_match) and frac_match >= SIGN_MATCH_THRESHOLD
    results.append(ConditionResult(
        "4_符号", ok4,
        f"符号一致率={frac_match:.4f}(n={n_checked}, 閾値={SIGN_MATCH_THRESHOLD})"
        + (" [r_bp=0 のため参考値]" if r_bp == 0 else ""),
    ))

    return results


def print_condition_table(title: str, results: list[ConditionResult]) -> bool:
    print(f"\n--- {title} ---")
    all_ok = True
    for r in results:
        mark = "OK" if r.passed else "NG"
        all_ok = all_ok and r.passed
        print(f"[{mark}] {r.name}: {r.detail}")
    return all_ok


# --------------------------------------------------------------------------- #
# メイン
# --------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------
# 変異d: タイ(internal_bp == 0)— **2026-09-13 に実際に起きた欠陥の型**
# ---------------------------------------------------------------------------
# 初版のこの検証は内部の値動きを 15〜60bp の連続値で作っていたため、
# **タイが一度も起きなかった**(実測: 全群 n_tie=0)。
# ところが 09-13 の実在の欠陥は、まさに `internal_bp == 0` の行を NaN として
# 黙って落とし、**実カスケードの約 8 割を捨てていた**ことだった
# (`liq_response.py` 365 行目のコメントが残している)。
# **一度も通っていない経路を「合格」と呼ぶことはできない。**
#
# タイの作り方: 価格を粗い刻みに丸める。刻みが内部の動きより粗ければ、
# 窓の始めと終わりが同じ刻みに乗り、内部の値動きが 0 になる。
# 実データでこれが起きたのと同じ理屈(価格は刻みを持つ)。
def quantize_prices(prices: PriceSeries, tick: float) -> PriceSeries:
    """価格を `tick` の格子に丸めた新しい系列を返す(元は壊さない)。"""
    return PriceSeries(ts_ms=list(prices.ts_ms),
                       price=[round(p / tick) * tick for p in prices.price])


def run_tie_scenario(horizon: int = HORIZON_MIN, r_bp: float = R_BP) -> dict:
    """タイを起こし、測定器が (1) どう扱うか (2) 群間差で止まるかを測る。"""
    out = {}
    bundle = build_synthetic(SEED, r_bp=r_bp, horizon_min=horizon)
    real_cascades = build_cascades(bundle.events, "synthetic", gap_ms=GAP_MS)
    all_casc = list(real_cascades) + list(bundle.control_cascades)

    tick = 5_000_000.0 * 40 / 10_000.0   # 基準価格の 40bp 相当の刻み
    coarse = quantize_prices(bundle.prices, tick)

    # **粗い価格は compute_reactions にも渡す。**粗い方の内部方向は
    # 「at_or_before(start_ms)(渡した系列)」→「anchor_price(compute_reactions が入れた値)」
    # で計算されるので、片方だけ粗くしてもタイにならない(最初そう書いて n_tie=0 になった)。
    # 実データでこれが起きたのは「1 分バーの終値」を両方に使っていたときである。
    base_rows = compute_reactions(all_casc, coarse, (horizon,))
    rows = attach_internal_direction([dict(r) for r in base_rows], coarse)
    real_rows = [r for r in rows if r["kind"] == "real"]
    ctrl_rows = [r for r in rows if r["kind"] == "no_liquidation"]

    for policy in ("keep", "refine", "drop"):
        try:
            rep = compute_reversal({"real": real_rows, "control": ctrl_rows},
                                   f"bp_{horizon}m", tie_policy=policy, strict=False)
            out[policy] = {r["group"]: dict(n_rows=r["n_rows"], n_used=r["n_used"],
                                            n_tie=r["n_tie"],
                                            n_tie_resolved=r["n_tie_resolved"],
                                            excl=round(r["exclusion_rate"], 4),
                                            mean=None if r["mean"] is None else round(r["mean"], 3))
                           for r in rep.summary_rows()}
        except Exception as exc:
            out[policy] = {"例外": f"{type(exc).__name__}: {exc}"}

    # 群間の除外率が非対称なとき、strict=True が止めるか
    fine_rows = compute_reactions(all_casc, bundle.prices, (horizon,))
    ctrl_fine = attach_internal_direction(
        [dict(r) for r in fine_rows if r["kind"] == "no_liquidation"], bundle.prices)
    try:
        compute_reversal({"real": real_rows, "control": ctrl_fine},
                         f"bp_{horizon}m", tie_policy="drop", strict=True)
        out["strict_非対称"] = "**止まらなかった(素通り)**"
    except ReversalExclusionImbalance as exc:
        out["strict_非対称"] = f"止まった: {type(exc).__name__}"
    except Exception as exc:
        out["strict_非対称"] = f"別の例外: {type(exc).__name__}: {exc}"
    return out


def main() -> int:
    # **ホライズンを指定できるようにする(2026-09-13、測定後監査の指摘)。**
    # 旧版は 15 分に固定。09-13 の実欠陥は「1 分バーの終値」が原因でタイが起きたので、
    # **短いホライズンほどタイが起きやすいはず**。射程に書くより測る方が安い。
    # **グローバルを書き換えない(2026-09-14、測定後監査 2 回目の指摘の診断結果)。**
    # 初版は `global horizon` で書き換えたが、`build_synthetic` と `run_pipeline` の
    # **既定引数は定義時に 15 で束縛済み**なので変わらなかった。結果、データは +15 分に
    # 仕込まれたまま条件だけが `bp_60m` を探し、**全行 NaN → 全除外**になった。
    # 60 分の「不合格」は測定器ではなく**この旗のバグ**だった(実測で確認)。
    # → ホライズンは引数で明示的に通す。
    import argparse as _ap
    _a = _ap.ArgumentParser()
    _a.add_argument("--horizon", type=int, default=HORIZON_MIN,
                    help="反応を測る水平線(分)。既定 15")
    # **継続(トレンド化)側も測れるようにする(2026-09-14、測定後監査 3 回目の指摘)。**
    # オーナーの原文は「トレンド転換が起きるか**またはそれがトレンドになるのか**」の両方を
    # 観測対象にしている(`OWNER_INTENT_2026-09-12.md` §1.1)。合成データは
    # `reversal_move_bp = -s * r_bp` なので、**r_bp を負にすると継続側**を仕込める。
    _a.add_argument("--r-bp", type=float, default=R_BP, dest="r_bp",
                    help="仕込む効果の大きさ(bp)。負にすると継続(トレンド化)側。既定 20.0")
    _args = _a.parse_args()
    horizon, r_bp = _args.horizon, _args.r_bp
    print("=" * 78)
    print("O-3c 測定器(liq_response.py)の合成データ検証")
    print("=" * 78)

    # --- 素の合成データ(R=r_bp)で 4 条件を測る ---
    print(f"\n[設定] SEED={SEED} N_REAL={N_REAL} N_CONTROL={N_CONTROL} "
          f"horizon={horizon} R_BP={r_bp} I_BP_RANGE={I_BP_RANGE} "
          f"NOISE_STD_BP={NOISE_STD_BP} GAP_MS={GAP_MS}")

    bundle_main = build_synthetic(SEED, r_bp=r_bp, horizon_min=horizon)
    report_main, rows_main, real_cascades_main = run_pipeline(bundle_main, horizon_min=horizon)
    print(f"\n[素の合成データ] 投入イベント数={len(bundle_main.events)} "
          f"build_cascades が作った実カスケード数={len(real_cascades_main)} "
          f"(投入 N_REAL={N_REAL} と一致するはず)")
    for row in report_main.summary_rows():
        print(f"  group={row['group']}: n_rows={row['n_rows']} n_used={row['n_used']} "
              f"n_tie={row['n_tie']} n_excluded_tie={row['n_excluded_tie']} "
              f"n_excluded_missing={row['n_excluded_missing']} "
              f"exclusion_rate={row['exclusion_rate']:.4f} mean={row['mean']:.4f}")

    results_main = check_conditions(report_main, rows_main, N_REAL, N_CONTROL, r_bp)
    main_ok = print_condition_table("素の合成データ(R={:.1f}bp)の4条件".format(r_bp), results_main)

    # --- 零効果(R=0)シナリオ ---
    bundle_zero = build_synthetic(SEED + 1, r_bp=0.0, horizon_min=horizon)
    report_zero, rows_zero, real_cascades_zero = run_pipeline(bundle_zero, horizon_min=horizon)
    print(f"\n[零効果(R=0)] 実カスケード数={len(real_cascades_zero)}")
    for row in report_zero.summary_rows():
        print(f"  group={row['group']}: n_rows={row['n_rows']} n_used={row['n_used']} "
              f"exclusion_rate={row['exclusion_rate']:.4f} mean={row['mean']:.4f}")
    results_zero = check_conditions(report_zero, rows_zero, N_REAL, N_CONTROL, 0.0,
                                     tolerance_bp=TOLERANCE_BP)
    zero_ok = print_condition_table("零効果(R=0)シナリオの4条件(条件2が主目的)", results_zero)
    # 条件2は零効果シナリオでのみ意味を持つ(素の合成データでの条件2は「R自体が0近傍でない」ため
    # 意図的に不合格になりうる。ここで零効果シナリオの条件2だけを正式な合格判定に使う)。
    cond2_zero_ok = next(r for r in results_zero if r.name == "2_零効果").passed

    clean_pass = main_ok and cond2_zero_ok
    # 条件2は main の表では「効果があるはずなのに0を含むか」を測ってしまうため意味が無い。
    # main 側は条件1,3,4、zero 側は条件2、という組み合わせで正式判定する。
    cond134_main_ok = all(r.passed for r in results_main if r.name != "2_零効果")
    clean_pass = cond134_main_ok and cond2_zero_ok

    print(f"\n>>> 素の合成データの正式判定(条件1,3,4 @ R={r_bp}bp のシナリオ + "
          f"条件2 @ R=0 のシナリオ): {'合格' if clean_pass else '不合格'}")

    # --- 変異試験 ---
    print("\n" + "=" * 78)
    print("変異試験(測定器の関数は変えず、結果を後加工して壊す/合成データを変える)")
    print("=" * 78)

    mutation_caught = {}

    # (a) カスケードの一部を黙って落とす
    real_cascades_a = build_cascades(bundle_main.events, "synthetic", gap_ms=GAP_MS)
    all_cascades_a = list(real_cascades_a) + list(bundle_main.control_cascades)
    rows_a = mutate_drop_some(all_cascades_a, bundle_main.prices, (horizon,), drop_every=5)
    rows_a = attach_internal_direction(rows_a, bundle_main.prices)
    real_rows_a = [r for r in rows_a if r["kind"] == "real"]
    control_rows_a = [r for r in rows_a if r["kind"] == "no_liquidation"]
    print(f"\n[変異a: 5件に1件を黙って落とす] 投入 real={N_REAL} → 生き残った real 行数="
          f"{len(real_rows_a)}(期待: N と不一致になるはず)")
    try:
        report_a = compute_reversal({"real": real_rows_a, "control": control_rows_a},
                                     f"bp_{horizon}m")
        results_a = check_conditions(report_a, {"real": real_rows_a, "control": control_rows_a},
                                      N_REAL, N_CONTROL, r_bp)
        ok_a = print_condition_table("変異a の4条件", results_a)
        cond3_a = next(r for r in results_a if r.name == "3_事象の数")
        mutation_caught["a_カスケードを黙って落とす"] = not cond3_a.passed
    except Exception as e:  # noqa: BLE001
        print(f"  compute_reversal が例外を送出: {type(e).__name__}: {e}")
        mutation_caught["a_カスケードを黙って落とす"] = True  # 例外そのものが「検出できた」証拠

    # (b) 符号を反転
    rows_b = mutate_flip_sign(list(real_cascades_main) + list(bundle_main.control_cascades),
                               bundle_main.prices, (horizon,))
    rows_b = attach_internal_direction(rows_b, bundle_main.prices)
    real_rows_b = [r for r in rows_b if r["kind"] == "real"]
    control_rows_b = [r for r in rows_b if r["kind"] == "no_liquidation"]
    report_b = compute_reversal({"real": real_rows_b, "control": control_rows_b},
                                 f"bp_{horizon}m")
    results_b = check_conditions(report_b, {"real": real_rows_b, "control": control_rows_b},
                                  N_REAL, N_CONTROL, r_bp)
    print("\n[変異b: bp の符号を反転]")
    ok_b = print_condition_table("変異b の4条件", results_b)
    cond4_b = next(r for r in results_b if r.name == "4_符号")
    mutation_caught["b_符号を反転"] = not cond4_b.passed

    # (c) 効果を半分に
    rows_c = mutate_halve_effect(list(real_cascades_main) + list(bundle_main.control_cascades),
                                  bundle_main.prices, (horizon,))
    rows_c = attach_internal_direction(rows_c, bundle_main.prices)
    real_rows_c = [r for r in rows_c if r["kind"] == "real"]
    control_rows_c = [r for r in rows_c if r["kind"] == "no_liquidation"]
    report_c = compute_reversal({"real": real_rows_c, "control": control_rows_c},
                                 f"bp_{horizon}m")
    results_c = check_conditions(report_c, {"real": real_rows_c, "control": control_rows_c},
                                  N_REAL, N_CONTROL, r_bp)
    print("\n[変異c: bp を半分に薄める]")
    ok_c = print_condition_table("変異c の4条件", results_c)
    cond1_c = next(r for r in results_c if r.name == "1_効果の大きさ")
    mutation_caught["c_効果を半分に薄める"] = not cond1_c.passed

    # (e) 別の地平線を読ませる(2026-09-14 追加。下の「同じ平均が 4 本で並ぶ」への答え)
    rows_e = mutate_wrong_horizon(list(real_cascades_main) + list(bundle_main.control_cascades),
                                   bundle_main.prices, (horizon,))
    rows_e = attach_internal_direction(rows_e, bundle_main.prices)
    real_rows_e = [r for r in rows_e if r["kind"] == "real"]
    control_rows_e = [r for r in rows_e if r["kind"] == "no_liquidation"]
    report_e = compute_reversal({"real": real_rows_e, "control": control_rows_e},
                                 f"bp_{horizon}m")
    results_e = check_conditions(report_e, {"real": real_rows_e, "control": control_rows_e},
                                  N_REAL, N_CONTROL, r_bp)
    wrong_h = horizon - 10 if horizon > 10 else horizon + 10
    print(f"\n[変異e: 地平線を {horizon} 分ではなく {wrong_h} 分で読ませる]")
    ok_e = print_condition_table("変異e の4条件", results_e)
    cond1_e = next(r for r in results_e if r.name == "1_効果の大きさ")
    mutation_caught["e_地平線を読み違える"] = not cond1_e.passed

    # --- 変異d: タイ(09-13 の実在の欠陥の型)---
    print("\n" + "=" * 78)
    print("変異d: タイ(internal_bp == 0)— 09-13 に実カスケードの約 8 割を落とした型")
    print("=" * 78)
    tie_out = run_tie_scenario(horizon, r_bp)
    for policy in ("keep", "refine", "drop"):
        print(f"  tie_policy={policy}: {tie_out.get(policy)}")
    print(f"  群間の除外率が非対称 + strict=True: {tie_out.get('strict_非対称')}")
    real_keep = tie_out.get("keep", {}).get("real", {})
    tie_seen = isinstance(real_keep, dict) and real_keep.get("n_tie", 0) > 0
    stopped = "止まった" in str(tie_out.get("strict_非対称", ""))
    mutation_caught["d_タイ(09-13 の型)"] = bool(tie_seen and stopped)
    print(f"  → タイが実際に発生したか: {tie_seen} / 群間差で止まったか: {stopped}")

    # **合否は 3 方針すべてに課す(2026-09-14、測定後監査 4 回目の [止める] 2 件)。**
    #
    # 旧版は `keep` の実群平均だけを見ていた。監査役が生ログから割り算で示したとおり、
    # **それは 2 つの誤差の打ち消し合いを「合格」と読んでいた**:
    #   反転側 262×22.747÷300 = 19.866(非タイ分が +2.747bp 過大 → 38/300 の 0 埋めで薄まって相殺)
    #   継続側 262×(-17.256)÷300 = -15.070(非タイ分の偏りは +2.744bp で**同じ量**。
    #                                        こちらは薄まりが重なって外れただけ)
    # **同じ一つの現象が、片方では True、片方では False として報告されていた。**
    #
    # さらに実測すると、40bp の刻みではタイ行の反応そのものが量子化の産物になっている:
    #   反転側のタイ 38 行は `bp` が全部 0.0 / 継続側のタイ 38 行は全部 ±40.0(刻み 1 個分)。
    # だから反転側では `refine` が「38 件解決」と数えても平均は `keep` と同一(19.866)になる。
    # **どの方針が「正しい」かではなく、どの方針でも仕込み値は取り出せていない。**
    #
    # → 合否は **3 方針すべてが許容内**を要求する。**緩めたのではなく締めた。**
    #   締めた結果、反転側も不合格になる(drop=22.747 が許容 ±3 を外れる)。
    #   監査役: 「同じ測定の 3 つの方針のうち 1 つだけを出して不合格と書くのは、
    #             測っていない族を説明なしに外す形である」
    print("  → **タイの場面で仕込んだ効果が取り出せるか(3 方針すべてに課す)**")
    tie_effect_ok = True
    for policy in ("keep", "refine", "drop"):
        rr = tie_out.get(policy, {}).get("real", {})
        m = rr.get("mean") if isinstance(rr, dict) else None
        ok = m is not None and m == m and abs(m - r_bp) <= TOLERANCE_BP
        tie_effect_ok = tie_effect_ok and ok
        n_used = rr.get("n_used") if isinstance(rr, dict) else None
        n_tie = rr.get("n_tie") if isinstance(rr, dict) else None
        diff = "nan" if (m is None or m != m) else f"{abs(m - r_bp):.3f}"
        print(f"     {policy:>6}: 実群平均={m} / 仕込み R={r_bp} / |差|={diff} "
              f"(許容={TOLERANCE_BP}) / n_used={n_used} / n_tie={n_tie} → {'OK' if ok else 'NG'}")
    # 打ち消し合いを読み手が割り算しなくて済むように、その場で分解して出す。
    rr_keep = tie_out.get("keep", {}).get("real", {})
    rr_drop = tie_out.get("drop", {}).get("real", {})
    if isinstance(rr_keep, dict) and isinstance(rr_drop, dict) and rr_drop.get("n_rows"):
        md, nu, nr = rr_drop.get("mean"), rr_drop.get("n_used"), rr_drop.get("n_rows")
        if md is not None and md == md and nu:
            print(f"     [分解] 非タイ {nu} 行の平均={md} (仕込みからの偏り={md - r_bp:+.3f}bp) "
                  f"× {nu}/{nr} = {nu * md / nr:.3f} = keep の平均({rr_keep.get('mean')})")
            print("            ← **keep の値は「偏り」と「タイ行の 0 埋め」の積である。"
                  "許容内に入っても、それは打ち消し合いであって効果の回収ではない。**")
    if not tie_effect_ok:
        # **言い過ぎない(2026-09-14)。**最初にここへ「どの方針でも仕込み値に戻らない」と
        # 書いたが、継続側の `refine` は -20.137 で戻っている。**外れた方針だけを名指しする。**
        ng = [p for p in ("keep", "refine", "drop")
              if not (isinstance(tie_out.get(p, {}).get("real", {}), dict)
                      and (lambda m: m is not None and m == m and abs(m - r_bp) <= TOLERANCE_BP)(
                          tie_out.get(p, {}).get("real", {}).get("mean")))]
        print(f"     ← **外れた方針: {', '.join(ng)}。**40bp の刻みではタイ行の反応が"
              "量子化の産物(0.0 か ±刻み 1 個分)になるため、どの値が出るかは方針で変わる。"
              "**これは測定器の欠陥ではなく『この分解能では測れない』という射程の事実だが、"
              "合否に入れないと見逃すので入れる。**")

    print("\n" + "=" * 78)
    print("変異試験のまとめ(検出できたか)")
    print("=" * 78)
    all_mutations_caught = True
    for name, caught in mutation_caught.items():
        all_mutations_caught = all_mutations_caught and caught
        print(f"[{'検出できた' if caught else '検出できなかった(重大な発見)'}] {name}")

    overall_pass = clean_pass and all_mutations_caught and tie_effect_ok
    print("\n" + "=" * 78)
    print(f"最終判定: {'合格(0)' if overall_pass else '不合格(1)'}")
    print("  内訳: 素の合成データが4条件を満たすか =", clean_pass,
          " / 変異すべてを検出できたか =", all_mutations_caught)
    print("=" * 78)

    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
