"""カード 9 の走らせ直し(2026-10-06): 状態機械の入りと出を最良気配で付け、レグごとの経路を出す。

委任文: `docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_rerun_impl.md`(担当 C)。
出所: `docs/ANALYSIS/2026-10-05_card9_liquidation_cascade.md` D10 の次の手 2「入りと出を『逆張り・
順張りがその時点で成行で叩く側の約定』にし、レグごとの入りの時刻と経路(MFE・MAE)を保存する」。
付け方はリードの決め(2026-10-06、批評家 1 回目 `docs/AUDITOR/VERDICTS/2026-10-06_c9_rerun_critic1.md`
の [止める] を受けた直し): 主 = COIN-M BTCUSD_PERP の最良気配(Binance 公開アーカイブ `bookTicker`)。
直前の同じ側の約定 (b) と、以後で最初の同じ側の約定 (a) は並べる列として残す。
走らせる口: `scripts/c9_run_a.py --fill-side quote --leg-path --quotes-dir <気配の置き場>`。
気配の取得: `scripts/c9_fetch_bookticker.py`。試験: `tests/research/test_liq_cascade_fill.py`。

**状態機械の本体(`scripts/o3c_signal_policy.py: simulate_cascade / simulate_baseline`)と束の流し方
(`liq_cascade_v2.simulate_bundle`)は写さず、そのまま呼ぶ。** 変えるのは渡す `price_fn` だけ。

## 約定の値段(`--fill-side`)

- `any`(既定、元の走らせ): 目標の時刻以後の最初の約定。どちらの側の約定でもよい
  (`liq_cascade_v2.make_price_fn`)。
- `quote`(主): 目標の時刻以前(ちょうどを含む)で最新の最良気配。成行の買いは `best_ask_price`、
  売りは `best_bid_price`。気配の時刻は `transaction_time`(ミリ秒。aggTrades の `transact_time` と
  同じ種類の時刻)。気配の古さ(目標の時刻 − 気配の時刻)が 300 秒を越える、または目標の時刻の
  UTC の日の気配のファイルが無い(取れなかった・取らない日)なら値の欠け。前の日の最後の気配は、
  目標の日のファイルがあって、その日の中に目標以前の気配が無いときだけ使う(取得の台本が前の日も
  取れたときだけ書く)。前の日の気配で欠けた日を埋めない。
- 並べる列 `*_taker_prev`(案 (b)): 注文の向きで成行が叩く側の約定のうち、目標の時刻以前で最後の
  約定(前 300 秒以内)。
- 並べる列 `*_taker_wait`(案 (a)): 同じ側の約定のうち、目標の時刻以後で最初の約定(300 秒以内)。
  待った間の値動きが入る。
- (b)・(a) は、目標の時刻の UTC の日の約定のファイルが無ければ値の欠け(批評家 1 回目の問 2:
  欠けた日の直後に前の日の古い約定を値にしない)。叩く側: 買いは `is_buyer_maker` が偽の約定、
  売りは真の約定(`o3c_oi_distance.load_agg_trades_with_maker` の docstring)。

本体の `price_fn(t_ms)` は時刻しか受け取らないので、注文の向きは本体自身の出力から決める:
1 回目は `any` で流し、戻り値の `path` のうち値段を引いた行(行動が `ACTIONS_NEEDING_PRICE`。
連鎖の終わりの強制決済の行「終わり / 決済」も入る)の順に、注文の向き =
符号(新しい建玉の向き − 前の建玉の向き)(順張り = 清算の向き、逆張り = その逆、建玉なし = 0)を
並べる。2 回目以後(気配・(b)・(a))はその順に向きを取り出す `price_fn` で流し、呼び出しの回数と
行動の並びが 1 回目と同じかを毎回確かめる(違えば止める。利確を渡さない今の本体では値段で行動は
変わらないが、本体が変わったときの止めとして置く。試験は偽物の本体で止まることを確かめる)。
ドテンは 1 回の注文(同じ向き)で、決済とその逆の建てを同じ値段で行う(本体と同じ)。

## レグの経路(`--leg-path`)

レグ(建玉 1 つ)ごとに、入りと出の目標の時刻(= プリントの時刻 + 遅れ。連鎖の終わりの出は
最後のプリント + g + 遅れ)・値段を付けた気配(約定)の時刻・値段・遅れ(その時刻 − 目標の時刻)・
注文の向きと、経路の最大順行(`mfe_bp` ≥ 0)・最大逆行(`mae_bp` ≤ 0)を、入りの値段 p0 から
建玉の向きの bp で出す(起点 0 を含める。`liq_cascade_v2.reactions_from_anchor` と同じ流儀)。
- `quote`: p0 = 気配で付けた入りの値段。経路 = 両側の約定すべてのうち、時刻が
  (入りの目標の時刻, 出の目標の時刻] のもの。`mfe_after_s`・`mae_after_s` は入りの目標の時刻からの秒。
  `in_quote_age_ms`・`out_quote_age_ms` = 目標の時刻 − 気配の時刻(≥ 0)。
- `any`(`--leg-path` だけを付けたとき): p0 = 入りの約定。経路は添字で (入りの約定, 出の約定]。
値の欠け(`missing`)のある連鎖は、レグと値段の呼び出しの対応が崩れうるので経路の列を NaN にする。

`quote` のときは 1 回目(`any`)の結果を `res_any` として返す(元の走らせの再現の検めに、
`c9_run_a.py` が元と同じ列の行を別の置き場 `chunks/*_any/` に書く)。
"""
from __future__ import annotations

import csv
import gzip
import json
import math
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from bot.research import liq_cascade_v2 as v2

NAN = float("nan")
FILL_ANY, FILL_QUOTE = "any", "quote"
FILL_SIDES = (FILL_ANY, FILL_QUOTE)
#: 並べる列の叩く側の約定の引き方: (b) = 以前で最後、(a) = 以後で最初
HOW_PREV, HOW_WAIT = "prev", "wait"
QUOTE_STALENESS_MS = v2.STALENESS_MS   # 300 秒(元の穴の防御と同じ秒数。リードの決め)

#: レグの経路の列(`--leg-path`)。順はこのまま CSV に出る。
LEG_PATH_COLS: tuple[str, ...] = (
    "fill_side", "order_in", "in_target_ms", "in_fill_ms", "in_px", "in_lag_ms",
    "in_quote_age_ms", "order_out", "out_target_ms", "out_fill_ms", "out_px", "out_lag_ms",
    "out_quote_age_ms", "path_ok", "path_n", "mfe_bp", "mae_bp", "mfe_after_s", "mae_after_s")


def day_of(t_ms: int) -> str:
    return v2.day_of_ms(int(t_ms))


# --------------------------------------------------------------------------- #
# 値段の引き方
# --------------------------------------------------------------------------- #
class TakerBook:
    """約定を「成行の買いが付いた約定(`maker` が偽)」と「成行の売りが付いた約定(真)」に分けた添字。

    `present_days` を渡すと、目標の時刻の UTC の日がそこに無いときは値の欠けにする(欠けた日)。"""

    def __init__(self, tr: v2.Trades, present_days: Iterable[str] | None = None):
        self.tr = tr
        self.present = None if present_days is None else set(present_days)
        m = np.asarray(tr.maker, dtype=bool)
        self._idx = {+1: np.flatnonzero(~m), -1: np.flatnonzero(m)}
        self._times = {k: tr.times[v] for k, v in self._idx.items()}

    def _pick(self, finder, order_sign: int, t_ms: int, tol: int):
        if self.present is not None and day_of(t_ms) not in self.present:
            return -1, False
        times = self._times[order_sign]
        j, ok = finder(times, np.array([int(t_ms)]), tol)
        if not bool(ok[0]):
            return -1, False
        return int(self._idx[order_sign][j[0]]), True

    def at_or_before(self, order_sign: int, t_ms: int, tol: int = v2.STALENESS_MS):
        """(b): `t_ms` 以前(ちょうどを含む)で最も新しい、`order_sign` の成行が付いた約定。"""
        return self._pick(v2.idx_at_or_before, order_sign, t_ms, tol)

    def at_or_after(self, order_sign: int, t_ms: int, tol: int = v2.STALENESS_MS):
        """(a): `t_ms` 以後で最も古い、`order_sign` の成行が付いた約定。"""
        return self._pick(v2.idx_at_or_after, order_sign, t_ms, tol)


class QuoteBook:
    """目標の時刻ごとの最良気配(取得の台本 `scripts/c9_fetch_bookticker.py` の出力)を引く。

    `rows` = {目標の時刻: (気配の時刻 or None, 買い気配, 売り気配)}。`ok_days` = 気配のファイルを
    取れた UTC の日。目標の日が `ok_days` に無ければ値の欠け。取れた日なのに目標が表に無ければ止める
    (目標の組が走らせと合っていない)。"""

    def __init__(self, rows: dict, ok_days: Iterable[str], tol: int = QUOTE_STALENESS_MS):
        self.rows = rows
        self.ok_days = set(ok_days)
        self.tol = int(tol)

    @classmethod
    def load(cls, quotes_dir: Path, days: Iterable[str]) -> "QuoteBook":
        quotes_dir = Path(quotes_dir)
        ok_days = set()
        p = quotes_dir / "fetch_log.jsonl"
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    if r.get("status") == "ok":
                        ok_days.add(r["day"])
        rows: dict = {}
        for d in days:
            if d not in ok_days:
                continue
            f = quotes_dir / "days" / f"{d}.csv.gz"
            if not f.exists():
                raise RuntimeError(f"[止め] 取れたと記録された日の気配の表が無い: {f}")
            with gzip.open(f, "rt", encoding="utf-8", newline="") as fh:
                for r in csv.DictReader(fh):
                    q = r["q_ms"]
                    rows[int(r["target_ms"])] = (
                        None if q == "" else int(q),
                        float(r["bid"]) if r["bid"] != "" else NAN,
                        float(r["ask"]) if r["ask"] != "" else NAN)
        return cls(rows, ok_days)

    def lookup(self, order_sign: int, t_ms: int):
        """(値段, 気配の時刻) または (NaN, None)。"""
        t_ms = int(t_ms)
        if day_of(t_ms) not in self.ok_days:
            return NAN, None
        if t_ms not in self.rows:
            raise RuntimeError(f"[止め] 気配の表に無い目標の時刻 {t_ms}(目標の組が走らせと違う)")
        q, bid, ask = self.rows[t_ms]
        if q is None or q > t_ms or t_ms - q > self.tol:
            return NAN, None
        px = ask if order_sign > 0 else bid
        if not (px == px and px > 0):
            return NAN, None
        return float(px), int(q)


def _logged_any_fn(tr: v2.Trades, log: list) -> Callable:
    """`v2.make_price_fn(tr)` と同じ値を返し、呼ばれた順に (目標, 添字, 値段, 時刻) を残す。"""
    def fn(t_ms: int):
        i, ok = v2.idx_at_or_after(tr.times, np.array([int(t_ms)]))
        if not bool(ok[0]):
            log.append({"target": int(t_ms), "idx": -1, "px": NAN, "t": None})
            return NAN, None
        k = int(i[0])
        px, t = float(tr.prices[k]), int(tr.times[k])
        log.append({"target": int(t_ms), "idx": k, "px": px, "t": t})
        return px, t
    return fn


def _queued_fn(signs: list[int], log: list, picker: Callable) -> Callable:
    """呼ばれた順に `signs` から注文の向きを取り出し、`picker(向き, 目標)` → (値段, 時刻, 添字)。"""
    state = {"k": 0}

    def fn(t_ms: int):
        k = state["k"]
        if k >= len(signs):
            raise RuntimeError("[止め] 値段の呼び出しが 1 回目より多い(注文の向きの並びが尽きた)")
        s = int(signs[k])
        state["k"] = k + 1
        px, t, idx = picker(s, int(t_ms))
        log.append({"target": int(t_ms), "idx": idx, "px": px, "t": t, "sign": s})
        return (px, t) if t is not None else (NAN, None)
    fn.state = state  # type: ignore[attr-defined]
    return fn


def _trade_picker(book: TakerBook, how: str) -> Callable:
    tr = book.tr
    pick = book.at_or_before if how == HOW_PREV else book.at_or_after

    def p(s, t):
        i, ok = pick(s, t)
        if not ok:
            return NAN, None, -1
        return float(tr.prices[i]), int(tr.times[i]), i
    return p


def _quote_picker(qb: QuoteBook) -> Callable:
    def p(s, t):
        px, q = qb.lookup(s, t)
        return px, q, -1
    return p


# --------------------------------------------------------------------------- #
# 注文の向き(本体の出力から)
# --------------------------------------------------------------------------- #
def _pos_dir(pos: str, side_sign: float) -> float:
    pol = v2.policy_module()
    return {pol.POS_NONE: 0.0, pol.POS_WITH: float(side_sign),
            pol.POS_AGAINST: -float(side_sign)}[pos]


def order_signs_from_path(path: list, side_sign: float) -> list[tuple[int, str]]:
    """状態機械の `path` から、値段を引いた順に (注文の向き +1 買い / −1 売り, 種類) を返す。
    種類 = "open"(新規)/ "close"(決済・連鎖の終わり)/ "flip"(ドテン)。"""
    pol = v2.policy_module()
    out = []
    prev = 0.0
    for row in path:
        new = _pos_dir(row["建玉"], side_sign)
        act = row["行動"]
        if act in pol.ACTIONS_NEEDING_PRICE:
            d = new - prev
            if d == 0:
                raise RuntimeError(f"[止め] 値段を引く行動で建玉の向きが変わらない: {act}")
            kind = ("open" if act in (pol.ACT_NEW_WITH, pol.ACT_NEW_AGAINST)
                    else "flip" if act in (pol.ACT_FLIP_AGAINST, pol.ACT_FLIP_WITH) else "close")
            out.append((1 if d > 0 else -1, kind))
        prev = new
    return out


def baseline_order_signs(direction: str, side_sign: float) -> list[tuple[int, str]]:
    """基準の方策(最初に入り終わりまで): 入り = 建玉の向き、出 = その逆。"""
    pol = v2.policy_module()
    d = float(side_sign) if direction == pol.POS_WITH else -float(side_sign)
    s = 1 if d > 0 else -1
    return [(s, "open"), (-s, "close")]


# --------------------------------------------------------------------------- #
# 経路
# --------------------------------------------------------------------------- #
def _nan_path() -> dict:
    return {"path_ok": 0, "path_n": 0, "mfe_bp": NAN, "mae_bp": NAN,
            "mfe_after_s": NAN, "mae_after_s": NAN}


def path_stats(tr: v2.Trades, p0: float, t0: int, a: int, b: int, direction: float) -> dict:
    """約定の添字 [a, b] の、p0 からの最大順行・最大逆行(建玉の向きの bp、起点 0 を含める)。
    秒は時刻 t0 から。b < a − 1(範囲が逆)・p0 が読めないなら NaN。"""
    if not (p0 == p0 and p0 > 0) or b < a - 1:
        return _nan_path()
    seg = float(direction) * (tr.prices[a:b + 1] - p0) / p0 * 1e4
    seg0 = np.concatenate(([0.0], seg))
    tt = np.concatenate(([int(t0)], tr.times[a:b + 1]))
    ia, ib = int(np.argmax(seg0)), int(np.argmin(seg0))
    return {"path_ok": 1, "path_n": int(seg.size), "mfe_bp": float(seg0[ia]),
            "mae_bp": float(seg0[ib]), "mfe_after_s": (int(tt[ia]) - int(t0)) / 1000.0,
            "mae_after_s": (int(tt[ib]) - int(t0)) / 1000.0}


def path_by_index(tr: v2.Trades, i_in: int, i_out: int, direction: float) -> dict:
    """`any`: 入りの約定(添字 i_in)の値段から、(i_in, i_out] の約定。"""
    if i_in < 0 or i_out < 0 or i_out < i_in:
        return _nan_path()
    return path_stats(tr, float(tr.prices[i_in]), int(tr.times[i_in]), i_in + 1, i_out,
                      direction)


def path_by_target(tr: v2.Trades, p0: float, in_target_ms: int, out_target_ms: int,
                   direction: float) -> dict:
    """`quote`: 時刻が (入りの目標, 出の目標] の約定。秒は入りの目標の時刻から。"""
    if int(out_target_ms) < int(in_target_ms):
        return _nan_path()
    a = int(np.searchsorted(tr.times, int(in_target_ms), side="right"))
    b = int(np.searchsorted(tr.times, int(out_target_ms), side="right")) - 1
    return path_stats(tr, p0, int(in_target_ms), a, b, direction)


def _leg_rows(tr: v2.Trades, legs: list, calls: list, signs: list, fill_side: str,
              missing: bool) -> list[dict]:
    """レグ(`legs`)と値段の呼び出し(`calls`、`signs` と同じ並び)を開き・閉じの順で対応させる。"""
    nan_row = {c: NAN for c in LEG_PATH_COLS} | {"fill_side": fill_side, "path_ok": 0,
                                                 "path_n": 0}
    if missing:
        return [dict(nan_row) for _ in legs]
    opens = [k for k, (_s, kind) in enumerate(signs) if kind in ("open", "flip")]
    closes = [k for k, (_s, kind) in enumerate(signs) if kind in ("close", "flip")]
    if len(legs) != len(closes) or len(opens) < len(closes):
        raise RuntimeError(f"[止め] レグ {len(legs)} と値段の呼び出し(開き {len(opens)}・"
                           f"閉じ {len(closes)})が対応しない")
    rows = []
    for n, lg in enumerate(legs):
        ci, co = calls[opens[n]], calls[closes[n]]
        for key, c in (("入りの約定時刻_ms", ci), ("出の約定時刻_ms", co)):
            if key in lg and lg[key] is not None and int(lg[key]) != int(c["t"]):
                raise RuntimeError(f"[止め] レグの{key}と値段の呼び出しが合わない")
        s_in = signs[opens[n]][0]
        if fill_side == FILL_QUOTE:
            st = path_by_target(tr, float(ci["px"]), ci["target"], co["target"], float(s_in))
            ages = {"in_quote_age_ms": int(ci["target"]) - int(ci["t"]),
                    "out_quote_age_ms": int(co["target"]) - int(co["t"])}
        else:
            st = path_by_index(tr, ci["idx"], co["idx"], float(s_in))
            ages = {"in_quote_age_ms": NAN, "out_quote_age_ms": NAN}
        row = {"fill_side": fill_side, "order_in": s_in, "in_target_ms": ci["target"],
               "in_fill_ms": ci["t"], "in_px": ci["px"],
               "in_lag_ms": int(ci["t"]) - int(ci["target"]),
               "in_quote_age_ms": ages["in_quote_age_ms"],
               "order_out": signs[closes[n]][0], "out_target_ms": co["target"],
               "out_fill_ms": co["t"], "out_px": co["px"],
               "out_lag_ms": int(co["t"]) - int(co["target"]),
               "out_quote_age_ms": ages["out_quote_age_ms"]} | st
        rows.append({c: row[c] for c in LEG_PATH_COLS})
    return rows


# --------------------------------------------------------------------------- #
# 束 1 本を流す
# --------------------------------------------------------------------------- #
def _run_queued(pr, bundle, judgments, policy_type, delay_s, signs, res1, picker, baseline):
    log: list = []
    fn = _queued_fn([s for s, _k in signs], log, picker)
    res = v2.simulate_bundle(pr, bundle, judgments, policy_type, delay_s, fn, baseline=baseline)
    if fn.state["k"] != len(signs):
        raise RuntimeError("[止め] 値段の呼び出しが 1 回目より少ない")
    if [r["行動"] for r in res["path"]] != [r["行動"] for r in res1["path"]]:
        raise RuntimeError("[止め] 行動の並びが 1 回目と違う")
    return res, log


def _leg_pnls(res_other: dict, res_main: dict, baseline) -> list:
    """`res_other` のレグ損益を、主のレグの並びに合わせて返す(数が違えば NaN)。"""
    if baseline is not None:
        if res_main["missing"]:
            return []
        return [NAN if res_other["missing"] else res_other["pnl_bp"]]
    n = len(res_main.get("legs", []))
    lo = res_other.get("legs", [])
    if len(lo) == n:
        return [x["レグ損益_bp"] for x in lo]
    return [NAN] * n


def simulate(pr: v2.Prints, bundle: dict, judgments, policy_type: str, delay_s: float,
             tr: v2.Trades, fill_side: str = FILL_ANY, leg_path: bool = False,
             baseline: str | None = None, book: TakerBook | None = None,
             quotes: QuoteBook | None = None) -> dict:
    """`v2.simulate_bundle` を約定の値段の付け方つきで流す。戻り値は `v2.simulate_bundle` と同じ形に、
    - `leg_rows`: レグごとの経路の列(`leg_path` のとき。基準の方策は欠けなければ 1 行)
    - `res_any`: 1 回目(`any`)の結果(`quote` のとき)
    - `pnl_bp_anyside` / `pnl_bp_taker_prev` / `pnl_bp_taker_wait` と `missing_*`・`leg_pnl_*`
      (`quote` のとき。並べる列)
    を足したもの。`quote` の `pnl_bp` は気配。基準の方策の `legs` は呼ぶ側が作る。"""
    if fill_side not in FILL_SIDES:
        raise ValueError(fill_side)
    side_sign = v2.REACT_SIGN[bundle["side"]]
    log1: list = []
    res1 = v2.simulate_bundle(pr, bundle, judgments, policy_type, delay_s,
                              _logged_any_fn(tr, log1), baseline=baseline)
    signs = (baseline_order_signs(baseline, side_sign) if baseline is not None
             else order_signs_from_path(res1["path"], side_sign))
    if len(signs) != len(log1):
        raise RuntimeError(f"[止め] 値段の呼び出し {len(log1)} 回と注文の向き {len(signs)} 個が違う")
    if fill_side == FILL_ANY:
        res, calls = res1, log1
    else:
        if quotes is None:
            raise ValueError("quote には QuoteBook が要る")
        book = book if book is not None else TakerBook(tr)
        res, calls = _run_queued(pr, bundle, judgments, policy_type, delay_s, signs, res1,
                                 _quote_picker(quotes), baseline)
        res_b, _ = _run_queued(pr, bundle, judgments, policy_type, delay_s, signs, res1,
                               _trade_picker(book, HOW_PREV), baseline)
        res_a, _ = _run_queued(pr, bundle, judgments, policy_type, delay_s, signs, res1,
                               _trade_picker(book, HOW_WAIT), baseline)
        res["res_any"] = res1
        for key, r in (("anyside", res1), ("taker_prev", res_b), ("taker_wait", res_a)):
            res[f"pnl_bp_{key}"] = r["pnl_bp"]
            res[f"missing_{key}"] = bool(r["missing"])
            res[f"leg_pnl_{key}"] = _leg_pnls(r, res, baseline)
    if leg_path:
        if baseline is not None:
            legs = [] if res["missing"] else [{"入りの約定時刻_ms": calls[0]["t"],
                                               "出の約定時刻_ms": calls[1]["t"]}]
        else:
            legs = res["legs"]
        res["leg_rows"] = _leg_rows(tr, legs, calls, signs, fill_side, bool(res["missing"]))
    return res


EXTRA_KEYS = ("anyside", "taker_prev", "taker_wait")


def cascade_extra(res: dict, fill_side: str) -> dict:
    """連鎖の行に足す列(既定の走らせでは呼ばない)。"""
    out = {"fill_side": fill_side}
    if fill_side == FILL_QUOTE:
        for k in EXTRA_KEYS:
            out[f"pnl_bp_{k}"] = res[f"pnl_bp_{k}"]
            out[f"missing_{k}"] = int(bool(res[f"missing_{k}"]))
    return out


def _num(v) -> float:
    return NAN if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def leg_extra(res: dict, n: int, fill_side: str, leg_path: bool) -> dict:
    """レグの行(`n` 番目)に足す列(既定の走らせでは呼ばない)。"""
    out: dict = {"fill_side": fill_side}
    if leg_path:
        out |= res["leg_rows"][n]
    if fill_side == FILL_QUOTE:
        for k in EXTRA_KEYS:
            lst = res[f"leg_pnl_{k}"]
            out[f"pnl_bp_{k}"] = _num(lst[n]) if n < len(lst) else NAN
    return out


def targets_for_prints(pr: v2.Prints, gaps=v2.GAPS_S, delays=v2.DELAYS_S) -> np.ndarray:
    """状態機械が値段を引きうる目標の時刻の組(重複なし、昇順)。
    = 各プリントの時刻 + 遅れ ∪ 各束の最後のプリント + g + 遅れ(`simulate_cascade` /
    `simulate_baseline` が `price_fn` に渡す時刻のすべて)。気配の取得の台本と試験が使う。"""
    out = [pr.ts + int(round(d * 1000)) for d in delays]
    for g in gaps:
        ends = np.array([b["end_ms"] for b in v2.same_side_bundles(pr, g)["bundles"]],
                        dtype=np.int64)
        for d in delays:
            out.append(ends + int(g) * 1000 + int(round(d * 1000)))
    return np.unique(np.concatenate(out)) if out else np.zeros(0, np.int64)
