"""# 10 のカード 4: 1 分足のシミュレーター(`bot.research.matilda_limit_sim.MatildaLimitSim`、c4_limit_run.py が呼ぶもの)と
同じ仕様のロジックを、約定の記録の上で回す(L-632・L-635 で決まった形)。シミュレーターは import して継承し、写さない。

1 分足のシミュレーターは、足の中の値段の動きを 2 本の道(上が先 = 始値 → 高値 → 安値、下が先 = 始値 → 安値 → 高値)で
通し、結果が違う足(決まらない足)では良い側・悪い側の仮定で道を選ぶ(モジュールの説明 3-5)。ここでは、約定の記録が
ある分(6 日の中)について、同じ状態・同じ量(足 k までで作った _q)から、約定の値段の道(行の順の値段の折り返し点。
g3_trades.DayTrades.zigzag)を、シミュレーター自身の脚の処理(`_leg`)に順に通す:
  足の頭 = 最初の約定の値段で、上りの頭 → 下りの頭(シミュレーターの _run_path と同じ)。
  続けて、折り返し点ごとに 1 本の脚(前の点 → 次の点。上りか下りかは値段の向き)。
これは _run_path の 2 本の道を、本当の道 1 本に置き換えたもの(2 本の道は「折り返しが 1 回の道」にあたる)。

2 つの使い方(mode):
  "watch"  : 1 分足の仮定(fill_side)のまま流す(出力の取引の行はシミュレーターと同じ)。決まらない足ごとに、選んだ道・
             もう一方の道・約定の道を同じ状態から通した結果を比べて 1 行にする(compare)。= 1 決定。
  "replay" : 約定のある分は約定の道だけで通す(2 本の道の代わりに同じ道を 2 回返すので、その足は決まる足になる)。
             6 日の外の分と約定の無い分はシミュレーターのまま(fill_side の仮定)。取引の行を日ごとに足して、
             1 分足の良い側・悪い側の 1 日の損益と並べる。

台本の決め(委任文・D1B_FRAMINGS に書いていない所。2026-10-06 のリードの決め 4・6 でこの形。形は M-A = c4_w6b_order.SIM_KW だけ):
  - 一致の判定 = 出来事の並び(シミュレーターの st.events。悪い側の「利確の手前で止めた」印 "stop" は除く)と、足の終わりの
    持ち高(向き・段の値段・ブレイクの状態)が全部同じ。
  - 道の損益の差 = シミュレーターの _path_value(その足で閉じた取引の損益 + 足の終わりの持ち高の含み)を、約定の道と選んだ道で
    同じ値段(その分の最後の約定の値段)で評価した差(bp)。
  - 反対の入りで閉じた後に同じ足でその向きに入るか(仕様 3-2)は、値段の順ではなく待ち行列の問題なので、replay でも
    シミュレーターの fill_side のまま(約定の記録の値段の道では決まらない)。
  - 足の高値・安値(1 分足の置き場)と約定の記録の分の最高値・最安値が違う分がある(W6b の O5)。ブレイクの判定(ev, pb)は
    シミュレーターが 1 分足の高値・安値で決める(_bar の 1.)ので、そのまま使い、食い違いの分の数を出す(除かない)。
"""
from __future__ import annotations

from bot.research.matilda_limit_sim import MatildaLimitSim

MODES = ("watch", "replay")


def _sig(st) -> tuple:
    """道の結果の印: 出来事の並び("stop" を除く)と足の終わりの持ち高。"""
    return (tuple(e for e in st.events if e[0] != "stop"), st.side, tuple(st.fills), st.brk)


def _has_tp(st) -> bool:
    return any(e[0] == "tp" for e in st.events)


class TradePathMatilda(MatildaLimitSim):
    """MatildaLimitSim に、約定の道で 1 本の足を通す口を足したもの(モジュールの説明)。

    trade_paths: 分の始まり(ns)→ 約定の値段の折り返し点の並び(空でない)。ここに無い分はシミュレーターのまま。
    mode: "watch" / "replay"。そのほかの引数は MatildaLimitSim と同じ(fill_side・SIM_KW など)。"""

    def __init__(self, *, trade_paths: dict, mode: str, **kw) -> None:
        if mode not in MODES:
            raise ValueError(f"mode は {list(MODES)} のどれか: {mode!r}")
        self._paths = trade_paths
        self._mode = mode
        self._own_log = kw.get("undecided_log") is None and mode == "watch"
        if self._own_log:
            kw["undecided_log"] = []
        super().__init__(**kw)
        self._seen: dict = {}  # 分の始まり → [(up_first, tp_stop, 状態, 足)]
        self._truth: dict = {}  # 分の始まり → 約定の道で通した状態
        self.compare: list = []  # watch: 決まらない足 1 本 = 1 行
        self.replayed_bars = 0  # replay: 約定の道で通した足の数(道を試した足だけ)
        self._log_seen = 0

    # ---------------------------------------------------------------- 約定の道
    def _true_path(self, st0, zz: list, q, ev, pb, t_start: int, t_end: int):
        st = st0.copy()
        p0 = zz[0]
        for up in (True, False):  # 足の頭(_run_path と同じ: 上りの頭 → 下りの頭)
            self._leg(st, up, p0, q, ev, pb, False, t_start, t_end)
        start = p0
        for p in zz[1:]:
            self._leg(st, p > start, p, q, ev, pb, False, t_start, t_end, start)
            start = p
        return st

    def _run_path(self, st0, up_first, bar, q, ev, pb, tp_stop):
        t_start, t_end = bar[3], bar[4]
        zz = self._paths.get(t_start)
        if not zz:
            return super()._run_path(st0, up_first, bar, q, ev, pb, tp_stop)
        if self._mode == "replay":
            if up_first:
                self.replayed_bars += 1
            return self._true_path(st0, zz, q, ev, pb, t_start, t_end)
        st = super()._run_path(st0, up_first, bar, q, ev, pb, tp_stop)
        if t_start not in self._truth:
            self._truth[t_start] = self._true_path(st0, zz, q, ev, pb, t_start, t_end)
        self._seen.setdefault(t_start, []).append((up_first, tp_stop, st, bar))
        return st

    # ---------------------------------------------------------------- 足の取り込み
    def feed(self, b) -> list:
        out = super().feed(b)
        if self._mode == "watch":
            log = self._undecided_log
            for e in log[self._log_seen:]:
                self._compare_one(e)
            if self._own_log:
                log.clear()
                self._log_seen = 0
            else:
                self._log_seen = len(log)
            self._seen.clear()
            self._truth.clear()
        return out

    def _compare_one(self, e: dict) -> None:
        s = e["start_ns"]
        if s not in self._truth:
            return  # 約定の記録の無い分(6 日の外・約定の無い分)
        tru = self._truth[s]
        seen = self._seen[s]
        main = {u: st for u, stop, st, _b in seen if not stop}
        bar = seen[0][3]
        if e["kind"] == "one_tp" and self.fill_side == "bad":
            chosen = next(st for u, stop, st, _b in seen if stop)
            other = main[True] if _has_tp(main[True]) else main[False]
        else:
            up = e["path"] in ("up", "same")
            chosen, other = main[up], main[not up]
        zz = self._paths[s]
        mark = zz[-1]
        v_true, v_ch, v_ot = (self._path_value(x, mark) for x in (tru, chosen, other))
        self.compare.append({
            "start_ns": s, "fill_side": self.fill_side, "kind": e["kind"], "path": e["path"],
            "eq_chosen": _sig(tru) == _sig(chosen), "eq_other": _sig(tru) == _sig(other),
            "tp_true": _has_tp(tru), "tp_chosen": _has_tp(chosen),
            "value_true_minus_chosen_bp": v_true - v_ch, "value_other_minus_chosen_bp": v_ot - v_ch,
            "n_turns": len(zz),
            "bar_vs_trades_hl_differ": (bar[1], bar[2]) != (max(zz), min(zz)),
            "bar_open_vs_first_trade_differ": bar[0] != zz[0]})


__all__ = ["MODES", "TradePathMatilda"]
