"""道の戦略の土台(L-766・L-767・L-754・L-745・L-746)。カードの戦略はこれを継いで書く。

オーナーの逐語:
- L-766「**・シグナルの発生・消失の時間**」「**・建玉価格の平均化や決済の計算に使った生の約定履歴(時間、価格、数量、ドル円変換に使ったusd/jpyの値、など)**」
- L-767「**a 残す b残す c １つ目**」(a = 注文の表を残す、b = 注文ごとに量の計算に使った値を残す、
  c = 消失 = 合図の条件が成り立たなくなった時刻。`docs/DISCUSSIONS/2026-10-06_held_batches/RECORD_FORM_L766.md` §6)
- L-754「**私がしてほしいの決まりを足すんじゃなくて、この計算が確実にできるツールを作ることと、そのツールが必ず使われる仕組みです。**」
- L-745「**20万×○%÷段数÷その時の価格=1段の単位やろ**」/ L-746「**70% 段数は戦略毎に変える(基本は1で計算) 0.001以下は切り捨て**」
- L-763・L-764: USDJPY は取引開始時点での最新の値

継ぐ側(カードの戦略)が書くのは `step(event, ctx)` だけ。その中で使うのは次の 4 つ:
- `signal_start(番号, 種類, 向き, 値)`: 合図の発生。時刻は土台が `ctx.now_ns` で押す(戦略に時刻を渡させない)。
  同じ番号の二度の発生は止める。番号に「無し」は使えない。値は戦略が宣言する、発生の時点で見た値(JSON にできる値)。
- `signal_end(番号, 理由)`: 合図の消失 = 合図の条件が成り立たなくなった時刻(L-767 c。注文や建玉とは無関係)。
  発生していない番号・二度目の消失は止める。理由「データの終わり」は土台が使う(データの終わりまで消えなかった合図)。
- `place(売買, 種類, 値段, 段数, 合図の番号)`: 注文。戦略は量を渡さない。土台が `sizing.size_detail`(= `size_per_level`)
  で 1 段の量を決め、量の計算に使った値(証拠金・比率・段数・その時の値段・USDJPY の値と相場の時刻・切り捨て前の量・
  切り捨て後の量)を記録して `ctx.place_order` に渡す。合図の番号は土台の記録(注文の表の signal_id)に残す
  (`OrderRequest.extra` には入れない: 取引所の模型が知らない extra の鍵の注文を拒むため。下の place の注を参照)。
  合図に依らない注文は番号に `NO_SIGNAL`(「無し」)を明示する。発生していない合図の番号の注文は止める。
  量が 0 になったら注文を出さず、注文の表に状態「量が 0 で出さない」の行だけを残す。
  種類は "market"(値段は None。その時の値段 = 直近の足の終値 / 直近の約定の値段 / 直近の板の仲値)と
  "limit"(値段 = 指値。量の計算もその値段)。
- `close(合図の番号 or 「無し」, 種類, 値段)`: 決済の普通の注文(4 周目 (2) B)。量 = |送る時点の建玉 + 出ている決済の注文の
  まだ約定していない量|、売買は建玉の逆。成行も指値も出せ、cancel で取り消して置き直せる(マチルダの利確の線が足ごとに
  動くため)。置き直すのは取り消しの答えが届いてから(届く前は前の注文の残りが「出ている決済の量」に入り、量が 0 になる)。
- `flatten(合図の番号 or 「無し」, "market", None)`: 成行で全部を決済する意図(2 周目 (d)・3 周目 問 5・4 周目 (2))。
  土台が出していて閉じていない注文(close の注文も)を全部取り消し、その取り消しの答えが全部届いてから、
  |建玉 + 出ている決済の量| を成行で出し、その後に届いた約定の知らせのぶんも、建玉が 0 で注文が残らなくなるまで出し続ける。
  指値は止める(指値の決済は close)。決済の成行が拒否された(または約定せずに閉じた)ら出し直さずに止める
  (黙って出し直すより、止まって理由が出る方が測りを誤らない。1 分足の走らせでは門が成行を次の足まで預かるので、
  約定せずに閉じる形は起こせなかった。板の足の成行の残り(market_remainder)などで起これば走らせ全体が止まる)。
  呼んだときに注文を出さなければ flatten_call の行(「量が 0 で出さない」、呼んだ時刻と合図の番号)を 1 つ残す。
  決済の途中(`is_flattening()`)は place・close・flatten を止め、決済の成行は cancel できない(戦略が「出ている注文を
  全部取り消す」と書くと、決済の成行に当たったところで止まる。決済の途中かは is_flattening で読める)。
  close と flatten の注文は reduce_only で出す(5 周目 (2-1)。取引所の模型が建玉を超える分を切り、切った分は注文の表の
  約定した量と状態・閉じ方(reduce_only・reduce_only_size_cut_filled)に出る)。
- `cancel(注文の番号)`: 取り消しを出す(出した時刻を記録して `ctx.cancel_order` に渡す)。

注文の一生は、土台が戦略に届く注文の知らせ(`bot.bt.core.events` の `OrderAckEvent`・`OrderRejectEvent`・
`OrderFillEvent`・`OrderCanceledEvent`・`OrderStateUnknownEvent`)から記録する。core は変えない。知らせの時刻は 2 つ残す:
戦略に届いた時刻(`ctx.now_ns` = 知らせの `received_time_ns`)と、取引所での時刻(知らせの `exchange_time_ns`)。
届いた順は、土台に届いた出来事の通し番号(注文を受けた時の `placed_seq`、閉じた知らせの `closed_seq`、約定の知らせの
`notice_seq`)で残す。
- 受け付けられた時刻: `OrderAckEvent` が届いた時刻(門が預かる成行は門の受け付けで、取引所の受け付けではない)
- 取り消した時刻: `OrderCanceledEvent` で `answers == "cancel"`(こちらの取り消しへの答え)が届いた時刻
- 拒否された時刻: `OrderRejectEvent`(新規の注文の拒否)と、中身が拒否の `OrderCanceledEvent`(`answers` が "venue" か
  "new" で、理由が `rejected_by_venue`・`refused_by_account` で始まるか `post_only_would_take`)が届いた時刻
  (2 周目 (b)・リードの直し・3 周目 問 4 (4))
- 期限が切れた時刻: 取引所が自分で閉じた時刻(`OrderCanceledEvent` で `answers == "venue"`、中身が拒否でないもの)。
  取引所の模型(`bot.bt.fill.venue`)には期限つきの注文(GTD)が無いので、入るのは期限切れ・成行の残り・reduce_only など
  (理由は close_reason)。`answers == "new"` で中身が拒否でないもの(IOC の残りなど)は、閉じた時刻・閉じ方
  (`close_kind`)・理由(`close_reason`)の生の列にだけ残す
- 取り消しの拒否・状態不明: `OrderRejectEvent`(request_kind = cancel)・`OrderStateUnknownEvent` が最初に届いた時刻
  (3 周目 問 4 (3))
- 最後の状態・約定した量: 知らせのたびに読む戦略の側の注文の見え方(`ctx.order(番号)`)の状態と、`OrderFillEvent` の量の和

止める(例外 `RoadStrategyError`、走らせが止まる)もの: 上の各操作の誤り、土台を通さずに出した注文の知らせ
(戦略が `ctx.place_order` を直に呼んだ。量を渡さない決まりを道具で守らせる)、土台を通さずに出した取り消しの答え
(戦略が `ctx.cancel_order` を直に呼んだ。3 周目 問 1 (5))。口座が出した強制の注文(番号が `forced-` で始まる)の知らせは、
出所「口座の強制」の行として残す。
限界: 戦略は同じ Python の中で動くので、戦略が土台の内部の記録(合図の時刻など)を書き換えるのは塞ぎ切れない
(SCHEMA.json の limits)。

記録は `road_record()` で取り出す(道の走らせ `bot.bt.pipeline` が走らせの後に読み、`bot.bt.road.tables` が表に書く)。
ここで出す文は全部日本語(O-1)。
"""
from __future__ import annotations

import bisect
import json
import math
from abc import abstractmethod
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence

from bot.bt.core import (
    BarEvent,
    BookSnapshotEvent,
    Event,
    OrderAckEvent,
    OrderCanceledEvent,
    OrderFillEvent,
    OrderRejectEvent,
    OrderRequest,
    OrderStateUnknownEvent,
    StrategyContext,
    TradeEvent,
)
from bot.bt.core.api import FORCED_ID_PREFIX
from bot.bt.core.strategy import Strategy

from .sizing import MARGIN_JPY, QUOTE_CCYS, USE_RATIO, SizingError, size_detail

NO_SIGNAL = "無し"
ZERO_QTY_STATE = "量が 0 で出さない"
DATA_END = "データの終わり"
ORDER_TYPES = ("market", "limit")
SIDES = ("buy", "sell")
ORIGIN_ROAD = "土台"
ORIGIN_FORCED = "口座の強制"
FX_PAIR = "USDJPY"
ORDER_ID_PREFIX = "road-"
# 道の走らせの門が、預かった注文の拒否を取り消しにして返すときの理由の頭(pipeline.py: 取引所の拒否・口座の確かめでの拒否)
VENUE_REJECT_PREFIXES = ("rejected_by_venue", "refused_by_account")
# answers = new(新規の注文への答えの一部)で届く取り消しのうち、中身が拒否のもの(bot.bt.fill.venue の
# _activation_refusal: post_only が成り立たないとき、取引所の決まりが "cancel" なら取り消しで返す)。3 周目 問 4 (4)
NEW_REJECT_REASONS = ("post_only_would_take",)
OPEN_STATE_VALUES = ("PENDING_NEW", "OPEN", "PENDING_CANCEL", "STATE_UNKNOWN")  # core の OPEN_STATES の値
EXIT_FLATTEN = "flatten"  # flatten が出した決済の成行
EXIT_FLATTEN_CALL = "flatten_call"  # flatten を呼んだときに注文を出さなかった記録の行(4 周目 (2) D)
EXIT_CLOSE = "close"  # close が出した決済の注文
EXIT_KINDS = (EXIT_FLATTEN, EXIT_FLATTEN_CALL, EXIT_CLOSE)
QTY_FROM_SIZING = "量の計算"
QTY_FROM_POSITION = "建玉"


class RoadStrategyError(RuntimeError):
    """道の戦略の土台が止める誤り(文は日本語)。走らせはここで止まる。"""


def _fail(msg: str) -> None:
    raise RoadStrategyError(msg)


def _sid(sid: Any, what: str) -> str:
    """合図の番号を文字列に(整数か空でない文字列)。"""
    if isinstance(sid, bool) or not isinstance(sid, (int, str)):
        _fail(f"{what}: 合図の番号は整数か空でない文字列で渡す(受け取ったのは {type(sid).__name__})")
    text = str(sid)
    if not text or text != text.strip() or "\n" in text:
        _fail(f"{what}: 合図の番号 {sid!r} は空でなく、前後に空白や改行を含まない")
    return text


def _text(v: Any, what: str) -> str:
    if type(v) is not str or not v:
        _fail(f"{what} は空でない文字列で渡す(受け取ったのは {v!r})")
    return v


def _dec_text(d: Decimal) -> str:
    """建玉(Decimal)を 10 進の文字列に(帳簿のツールの dec_str と同じ書き方: 0 は "0"、末尾の 0 を落とす)。"""
    if d == 0:
        return "0"
    t = format(d, "f")
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return t


def is_reject_reason(answers: str, reason: str) -> bool:
    """取り消しの知らせ(answers・reason)が、中身は拒否か(拒否された時刻の列に入れるか)。"""
    if answers not in ("new", "venue"):
        return False
    return reason.startswith(VENUE_REJECT_PREFIXES) or reason in NEW_REJECT_REASONS


def _num_text(x: Any) -> str:
    """数を表に書く文字列に(浮動小数は最短の 10 進 = repr、整数はそのまま)。"""
    if isinstance(x, bool):
        raise TypeError("真偽値は数として書かない")
    if isinstance(x, float):
        return repr(x)
    return str(x)


class RoadStrategy(Strategy):
    """道の戦略の土台。継ぐ側は `step(event, ctx)` を書く。

    quote_ccy: 銘柄の値段の通貨("JPY" / "USD" / "USDT")。道の書き出しが銘柄の宣言と突き合わせる。
    fx: ドル建てのとき、量の計算に使う USDJPY の相場の列({t_ns, pair, rate} の辞書の列)。
        その時刻(`ctx.now_ns`)以前の最後の相場だけを使う(先の相場は読まない)。
    fx_source: その相場の出所(ファイルの名前など。fx の表の source の列に残す)。
    """

    def __init__(self, *, quote_ccy: str, fx: Optional[Sequence[Mapping]] = None, fx_source: str = "") -> None:
        if quote_ccy not in QUOTE_CCYS:
            _fail(f"quote_ccy は {QUOTE_CCYS} のどれか: {quote_ccy!r}")
        self.quote_ccy = quote_ccy
        self.exit_reasons: dict = {}  # 道の走らせ(pipeline)が求める口。全部の注文に理由を書く(pipeline の trades は道では使わない)
        self._fx_rows: list = []
        pts = []
        for k, p in enumerate(fx or ()):
            if not isinstance(p, Mapping) or set(p) != {"t_ns", "pair", "rate"}:
                _fail(f"fx の {k} 行目は {{t_ns, pair, rate}} の辞書で渡す")
            t, pair, rate = p["t_ns"], p["pair"], p["rate"]
            if type(t) is not int or type(pair) is not str or len(pair) != 6 or not pair.isupper() \
                    or isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(float(rate)) \
                    or float(rate) <= 0:
                _fail(f"fx の {k} 行目が読めない(t_ns は ns の整数・pair は 6 文字の大文字・rate は 0 より大きい有限の数): "
                      f"{dict(p)!r}")
            self._fx_rows.append({"t_ns": t, "pair": pair, "rate": float(rate)})
            if pair == FX_PAIR:
                pts.append((t, k, float(rate)))
        pts.sort()  # 同じ時刻の相場が 2 つあれば、後に渡した方(FxRates.rate と同じ)
        self._fx_times = [q[0] for q in pts]
        self._fx_rates = [q[2] for q in pts]
        if fx_source is not None and type(fx_source) is not str:
            _fail("fx_source は文字列で渡す")
        self._fx_source = fx_source or ""
        if quote_ccy != "JPY" and not self._fx_times:
            _fail(f"{quote_ccy} 建ての戦略には量の計算に使う USDJPY の相場(fx)が要る(1 とみなさない。L-756)")
        self._signals: dict = {}  # 番号 -> 行(発生の順)
        self._orders: dict = {}  # 注文の番号 -> 行(受けた順)
        self._filled: dict = {}  # 注文の番号 -> 約定した量の和(Decimal)
        self._pos = Decimal(0)  # 届いた約定の知らせから持つ建玉(買いが +)
        self._seq = 0  # 土台に届いた出来事の通し番号(1 から。届いた順)
        self._notices: dict = {}  # 注文の番号 -> [(届いた時刻, 通し番号, 量の文字列), ...](約定の知らせ)
        self._flat: Optional[dict] = None  # 決済の意図(flatten の後、建玉 0 で注文が残らなくなるまで)
        self._cancel_pending: dict = {}  # 注文の番号 -> 取り消しの答えを待っているか(戦略の側の注文の見え方)
        self._n = 0
        self._ctx: Optional[StrategyContext] = None
        self._px: Optional[float] = None
        self._px_source = ""

    # ---- 継ぐ側が書く ---------------------------------------------------------------
    @abstractmethod
    def step(self, event: Event, ctx: StrategyContext) -> None:
        """届いた出来事 1 つごとに呼ばれる(注文の知らせも。土台が記録した後)。"""

    # ---- core から呼ばれる ------------------------------------------------------------
    def on_event(self, event: Event, ctx: StrategyContext) -> None:
        self._ctx = ctx
        self._seq += 1
        try:
            self._observe(event, ctx)
            self.step(event, ctx)
        finally:
            self._ctx = None

    def _observe(self, event: Event, ctx: StrategyContext) -> None:
        if isinstance(event, BarEvent):
            self._px, self._px_source = float(event.close), "直近の足の終値"
            return
        if isinstance(event, TradeEvent):
            self._px, self._px_source = float(event.price), "直近の約定の値段"
            return
        if isinstance(event, BookSnapshotEvent):
            if event.bids and event.asks:
                self._px = (float(event.bids[0][0]) + float(event.asks[0][0])) / 2
                self._px_source = "直近の板の仲値"
            return
        if not isinstance(event, (OrderAckEvent, OrderRejectEvent, OrderFillEvent, OrderCanceledEvent,
                                  OrderStateUnknownEvent)):
            return
        coid = event.client_order_id
        row = self._orders.get(coid)
        if row is None:
            if not coid.startswith(FORCED_ID_PREFIX):
                _fail(f"土台を通さずに出した注文 {coid!r} の知らせが届いた(注文は place で出す。戦略は量を渡さない)")
            row = self._new_row(coid, ORIGIN_FORCED, NO_SIGNAL)
            row.update(state="", sent_t_ns="")
        now = int(ctx.now_ns)
        venue_t = int(event.exchange_time_ns)
        answers_cancel = (isinstance(event, OrderCanceledEvent) and event.answers == "cancel") or (
            isinstance(event, (OrderRejectEvent, OrderStateUnknownEvent)) and event.request_kind == "cancel")
        if answers_cancel and row["origin"] == ORIGIN_ROAD and row["cancel_sent_t_ns"] == "":
            _fail(f"土台を通さずに出した取り消し(注文 {coid!r})の答えが届いた(取り消しは cancel で出す。3 周目 問 1 (5))")
        if isinstance(event, OrderAckEvent):
            if row["acked_t_ns"] == "":
                row["acked_t_ns"], row["acked_venue_t_ns"] = now, venue_t
        elif isinstance(event, OrderFillEvent):
            self._filled[coid] = self._filled.get(coid, Decimal(0)) + Decimal(repr(float(event.size)))
            row["filled_qty"] = str(self._filled[coid])
            fq = Decimal(repr(float(event.size)))
            self._pos += fq if (event.side or row["side"]) == "buy" else -fq
            self._notices.setdefault(coid, []).append((now, self._seq, repr(float(event.size))))
        elif isinstance(event, OrderCanceledEvent):
            if event.answers == "cancel":
                row["canceled_t_ns"] = now
            elif is_reject_reason(event.answers, event.reason):
                row["rejected_t_ns"] = now  # 中身は拒否(門が預かった注文を取引所・口座の確かめが拒んだ、post_only など)
            elif event.answers == "venue":
                row["venue_closed_t_ns"] = now  # 取引所が自分で閉じた(期限切れ・成行の残り・reduce_only など)
            self._close(row, now, venue_t, event.answers, event.reason)
        elif isinstance(event, OrderRejectEvent):
            if event.request_kind == "new":
                row["rejected_t_ns"] = now
                self._close(row, now, venue_t, "reject", event.reason)
            elif row["cancel_rejected_t_ns"] == "":
                row["cancel_rejected_t_ns"] = now  # 取り消しの拒否
        elif isinstance(event, OrderStateUnknownEvent):
            if row["state_unknown_t_ns"] == "":
                row["state_unknown_t_ns"] = now  # 状態不明(新規・取り消しへの曖昧な答え)
        view = ctx.order(coid)
        if view is not None:
            row["state"] = view.state.value
            self._cancel_pending[coid] = bool(view.cancel_pending)
        if row["exit_kind"] == EXIT_FLATTEN and row["closed_t_ns"] != "" and self._filled.get(coid, Decimal(0)) == 0:
            # 4 周目 (2) A: 決済の成行が拒否された(または約定せずに閉じた)ら出し直さずに止める(出し直すと同じ時刻に
            # 拒否が返り続け、走らせが終わらない)
            what = "拒否された" if row["rejected_t_ns"] != "" else "約定せずに閉じた"
            _fail(f"決済の注文 {coid!r} が{what}(閉じ方 {row['close_kind']}・理由 {row['close_reason']!r})。"
                  f"flatten は出し直さずに止める")
        if self._flat is not None:
            self._flatten_step(now)

    def _close(self, row: dict, now: int, venue_t: int, kind: str, reason: str) -> None:
        if row["closed_t_ns"] == "":
            row.update(closed_t_ns=now, closed_venue_t_ns=venue_t, close_kind=kind, close_reason=reason,
                       closed_seq=self._seq)

    def _new_row(self, coid: str, origin: str, signal: str) -> dict:
        row = {"order_id": coid, "origin": origin, "signal_id": signal, "side": "", "order_type": "", "limit_px": "",
               "qty": "", "placed_t_ns": "", "sent_t_ns": "", "acked_t_ns": "", "acked_venue_t_ns": "",
               "cancel_sent_t_ns": "", "canceled_t_ns": "", "venue_closed_t_ns": "", "rejected_t_ns": "",
               "cancel_rejected_t_ns": "", "state_unknown_t_ns": "", "closed_t_ns": "", "closed_seq": "",
               "closed_venue_t_ns": "", "close_kind": "", "close_reason": "", "state": "", "filled_qty": "0",
               "margin_jpy": "", "use_ratio": "", "levels": "", "size_px": "", "size_px_source": "", "quote_ccy": "",
               "usdjpy": "", "usdjpy_t_ns": "", "qty_raw": "", "qty_source": "", "position_at_send": "",
               "exit_pending_at_send": "", "placed_seq": "", "exit_kind": "", "reduce_only": ""}
        self._orders[coid] = row
        return row

    def _now(self, what: str) -> int:
        if self._ctx is None:
            _fail(f"{what} は step の中(出来事が届いている間)だけ呼べる")
        return int(self._ctx.now_ns)

    # ---- 継ぐ側が呼ぶ ---------------------------------------------------------------
    def signal_start(self, sid: Any, kind: str, direction: str, value: Any) -> str:
        now = self._now("signal_start")
        text = _sid(sid, "signal_start")
        if text == NO_SIGNAL:
            _fail(f"signal_start: 番号「{NO_SIGNAL}」は合図に依らない注文の印なので合図の番号に使えない")
        if text in self._signals:
            _fail(f"signal_start: 合図 {text} は既に発生している(同じ番号の二度の発生)")
        _text(kind, "signal_start の種類")
        _text(direction, "signal_start の向き")
        try:
            value_json = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError):
            _fail(f"signal_start: 合図 {text} の値は JSON にできる有限の値で渡す(受け取ったのは {type(value).__name__})")
        self._signals[text] = {"signal_id": text, "kind": kind, "direction": direction, "value_json": value_json,
                               "start_t_ns": now, "end_t_ns": "", "end_reason": ""}
        return text

    def signal_end(self, sid: Any, reason: str) -> None:
        now = self._now("signal_end")
        text = _sid(sid, "signal_end")
        row = self._signals.get(text)
        if row is None:
            _fail(f"signal_end: 合図 {text} は発生していない(発生していない番号の消失)")
        if row["end_t_ns"] != "":
            _fail(f"signal_end: 合図 {text} は既に消失している(二度目の消失)")
        _text(reason, "signal_end の理由")
        if reason == DATA_END:
            _fail(f"signal_end: 理由「{DATA_END}」は土台が使う(データの終わりまで消えなかった合図)")
        row["end_t_ns"], row["end_reason"] = now, reason

    def is_signal_on(self, sid: Any) -> bool:
        """合図が発生していて、まだ消失していないか。"""
        row = self._signals.get(_sid(sid, "is_signal_on"))
        return row is not None and row["end_t_ns"] == ""

    def _usdjpy(self, now: int) -> tuple[float, int]:
        i = bisect.bisect_right(self._fx_times, now) - 1
        if i < 0:
            _fail(f"時刻 {now} 以前の USDJPY の相場が無い(量の計算に使う。1 とみなさない。L-756)")
        return self._fx_rates[i], self._fx_times[i]

    def place(self, side: str, order_type: str, price: Optional[float], levels: int, signal: Any) -> str:
        """注文を出す。返すのは注文の番号(量が 0 で出さなかった行の番号も返す。状態は `order_state` で読める)。"""
        now = self._now("place")
        if self._flat is not None:
            _fail("place: 決済の途中(flatten の後、建玉が 0 で注文が残らなくなるまで)は注文を出せない(is_flattening で読める)")
        if side not in SIDES:
            _fail(f"place: 売買は {SIDES} のどれか: {side!r}")
        if order_type not in ORDER_TYPES:
            _fail(f"place: 種類は {ORDER_TYPES} のどれか: {order_type!r}")
        if order_type == "limit":
            if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(float(price)) \
                    or float(price) <= 0:
                _fail(f"place: 指値の注文の値段は 0 より大きい有限の数: {price!r}")
            price = float(price)
            size_px, size_src = price, "指値"
        else:
            if price is not None:
                _fail(f"place: 成行の注文に値段を渡さない(量の計算はその時の値段): {price!r}")
            if self._px is None:
                _fail("place: 成行の量の計算に使う値段がまだ無い(足・約定・板がまだ届いていない)")
            size_px, size_src = self._px, self._px_source
        if type(levels) is not int or levels < 1:
            _fail(f"place: 段数は 1 以上の整数: {levels!r}")
        sig = NO_SIGNAL if signal == NO_SIGNAL else _sid(signal, "place")
        if sig != NO_SIGNAL and sig not in self._signals:
            _fail(f"place: 合図 {sig} は発生していない(発生していない合図の番号の注文。合図に依らない注文は"
                  f"「{NO_SIGNAL}」を明示する)")
        rate = rate_t = None
        if self.quote_ccy != "JPY":
            rate, rate_t = self._usdjpy(now)
        try:
            raw, qty = size_detail(margin_jpy=MARGIN_JPY, use_ratio=USE_RATIO, levels=levels, price=size_px,
                                   quote_ccy=self.quote_ccy, usdjpy_at_entry=rate)
        except SizingError as exc:
            raise RoadStrategyError(f"place: 量の計算ができない: {exc}") from None
        coid = self._new_id()
        row = self._new_row(coid, ORIGIN_ROAD, sig)
        row.update(side=side, order_type=order_type, limit_px="" if price is None else _num_text(price),
                   qty=_num_text(qty), placed_t_ns=now, margin_jpy=_num_text(MARGIN_JPY),
                   use_ratio=_num_text(USE_RATIO), levels=levels, size_px=_num_text(size_px),
                   size_px_source=size_src, quote_ccy=self.quote_ccy,
                   usdjpy="" if rate is None else _num_text(rate), usdjpy_t_ns="" if rate_t is None else rate_t,
                   qty_raw=str(raw), qty_source=QTY_FROM_SIZING, position_at_send=_dec_text(self._pos),
                   placed_seq=self._seq)
        if qty == 0:
            row["state"] = ZERO_QTY_STATE
            return coid
        return self._send(row, coid, side, order_type, qty, price, sig, now)

    def flatten(self, signal: Any, order_type: str = "market", price: Optional[float] = None) -> str:
        """成行で全部を決済する口(2 周目 (d)・3 周目 問 5・4 周目 (2) A〜D)。決済の意図として受ける:
        1. 土台が出していてまだ閉じていない注文(close の注文も)を全部取り消し、
        2. その取り消しの答え(取り消した / 約定した / 取り消しの拒否)が全部届くのを待ってから、
        3. |知っている建玉(土台が約定の知らせから持つ建玉) + 出ている決済の注文のまだ約定していない量| を成行で出し、
        4. その後に届いた約定の知らせのぶんも、建玉が 0 で注文が残らなくなるまで出し続ける。
        種類は成行だけ(指値で決済するときは close を使う。4 周目 (2) B)。決済の成行が拒否された(または約定せずに
        閉じた)ら、出し直さずに `RoadStrategyError` で止める(4 周目 (2) A)。
        呼んだときに注文を出さなければ(建玉 0、または取り消しの答え待ち)、注文の表に flatten_call の行を 1 つ残す
        (状態「量が 0 で出さない」、呼んだ時刻と合図の番号。4 周目 (2) D)。決済の途中は place・close・flatten を止める。
        返すのは、呼んだときに出した注文か残した行の注文の番号。"""
        now = self._now("flatten")
        if self._flat is not None:
            _fail("flatten: 既に決済の途中(建玉が 0 で注文が残らなくなるまで、is_flattening で読める)")
        if order_type != "market" or price is not None:
            _fail(f"flatten: 成行だけ(種類 market・値段 None)。指値で決済するときは close を使う: {order_type!r}・{price!r}")
        sig = self._exit_signal(signal, "flatten")
        waiting = []
        for coid, row in list(self._orders.items()):
            if row["origin"] == ORIGIN_ROAD and self._is_open(row):
                if row["cancel_sent_t_ns"] == "" or not self._cancel_pending.get(coid, False):
                    self.cancel(coid)
                waiting.append(coid)
        self._flat = {"signal": sig, "waiting": waiting}
        sent = self._flatten_step(now)
        if sent is not None:
            return sent
        pos, pending = self._pos, self._pending_exit()
        coid = self._new_id()
        row = self._new_row(coid, ORIGIN_ROAD, sig)
        row.update(order_type="market", qty=_num_text(0.0), placed_t_ns=now, quote_ccy=self.quote_ccy,
                   qty_source=QTY_FROM_POSITION, position_at_send=_dec_text(pos),
                   exit_pending_at_send=_dec_text(pending), placed_seq=self._seq, state=ZERO_QTY_STATE,
                   exit_kind=EXIT_FLATTEN_CALL)
        return coid

    def close(self, signal: Any, order_type: str, price: Optional[float]) -> str:
        """決済の普通の注文(4 周目 (2) B)。量 = |送る時点の建玉 + 出ている決済の注文のまだ約定していない量|、売買は建玉の逆。
        建玉が 0、またはその和が 0 か建玉と逆の向きなら、出さずに「量が 0 で出さない」の行を残す。成行も指値も出せ、
        cancel で取り消して置き直せる(マチルダの利確の線が足ごとに動くため。MATILDA_ROAD_FRAMING.md §5)。
        取り消してすぐ置き直すと、取り消しの答えが届くまでは前の注文の残りが「出ている決済の量」に入るので量が 0 になる。
        置き直すのは取り消しの答えが届いてから。決済の途中(flatten の後)は止める。返すのは注文の番号。"""
        now = self._now("close")
        if self._flat is not None:
            _fail("close: 決済の途中(flatten の後、建玉が 0 で注文が残らなくなるまで)は注文を出せない")
        if order_type not in ORDER_TYPES:
            _fail(f"close: 種類は {ORDER_TYPES} のどれか: {order_type!r}")
        if order_type == "limit":
            if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(float(price)) \
                    or float(price) <= 0:
                _fail(f"close: 指値の注文の値段は 0 より大きい有限の数: {price!r}")
            price = float(price)
        elif price is not None:
            _fail(f"close: 成行の注文に値段を渡さない: {price!r}")
        sig = self._exit_signal(signal, "close")
        pos, pending = self._pos, self._pending_exit()
        net = pos + pending
        coid = self._new_id()
        row = self._new_row(coid, ORIGIN_ROAD, sig)
        row.update(order_type=order_type, limit_px="" if price is None else _num_text(price), placed_t_ns=now,
                   quote_ccy=self.quote_ccy, qty_source=QTY_FROM_POSITION, position_at_send=_dec_text(pos),
                   exit_pending_at_send=_dec_text(pending), placed_seq=self._seq, exit_kind=EXIT_CLOSE)
        if pos == 0 or net == 0 or (net > 0) != (pos > 0):
            row.update(qty=_num_text(0.0), state=ZERO_QTY_STATE)
            return coid
        side = "sell" if net > 0 else "buy"
        qty = float(abs(net))
        row.update(side=side, qty=_num_text(qty))
        return self._send(row, coid, side, order_type, qty, price, sig, now, reduce_only=True)

    def _exit_signal(self, signal: Any, what: str) -> str:
        sig = NO_SIGNAL if signal == NO_SIGNAL else _sid(signal, what)
        if sig != NO_SIGNAL and sig not in self._signals:
            _fail(f"{what}: 合図 {sig} は発生していない(発生していない合図の番号の注文。合図に依らない注文は"
                  f"「{NO_SIGNAL}」を明示する)")
        return sig

    def is_flattening(self) -> bool:
        """決済の途中か(flatten の後、建玉が 0 で注文が残らなくなるまで)。"""
        return self._flat is not None

    @staticmethod
    def _is_open(row: dict) -> bool:
        return row["sent_t_ns"] != "" and row["state"] in OPEN_STATE_VALUES

    def _open_rows(self) -> list:
        return [r for r in self._orders.values() if r["origin"] == ORIGIN_ROAD and self._is_open(r)]

    def _pending_exit(self) -> Decimal:
        """出ていてまだ閉じていない決済の注文(flatten・close)の、まだ約定していない量の和(買いが +)。"""
        out = Decimal(0)
        for coid, r in self._orders.items():
            if r["qty_source"] == QTY_FROM_POSITION and self._is_open(r):
                rest = Decimal(r["qty"]) - self._filled.get(coid, Decimal(0))
                out += rest if r["side"] == "buy" else -rest
        return out

    def _flatten_step(self, now: int) -> Optional[str]:
        """決済の意図の 1 歩: 取り消しの答えが全部届いていれば、足りない決済の量を成行で出す。
        建玉 0 で注文が残らなければ意図を終える。"""
        f = self._flat
        assert f is not None
        if any(self._cancel_pending.get(c, False) for c in f["waiting"]):
            return None  # 取り消しの答え待ち(4 周目 (2) C)
        pending = self._pending_exit()
        net = self._pos + pending
        sent = None
        if net != 0:
            side = "sell" if net > 0 else "buy"
            qty = float(abs(net))
            coid = self._new_id()
            row = self._new_row(coid, ORIGIN_ROAD, f["signal"])
            row.update(side=side, order_type="market", qty=_num_text(qty), placed_t_ns=now, quote_ccy=self.quote_ccy,
                       qty_source=QTY_FROM_POSITION, position_at_send=_dec_text(self._pos),
                       exit_pending_at_send=_dec_text(pending), placed_seq=self._seq, exit_kind=EXIT_FLATTEN)
            sent = self._send(row, coid, side, "market", qty, None, f["signal"], now, reduce_only=True)
        if self._pos == 0 and not self._open_rows():
            self._flat = None
        return sent

    def _new_id(self) -> str:
        coid = f"{ORDER_ID_PREFIX}{self._n}"
        self._n += 1
        return coid

    def _send(self, row: dict, coid: str, side: str, order_type: str, qty: float, price: Optional[float], sig: str,
              now: int, reduce_only: bool = False) -> str:
        # 合図の番号は OrderRequest.extra に入れない: 取引所の模型(bot.bt.fill.venue)は知らない extra の鍵の注文を
        # 拒む(rejected_by_venue: unknown_extra:['road_signal'])。注文と合図のつなぎは土台の記録(注文の表の
        # signal_id)が持つ(委任文 DELEGATION_record_form.md 2 周目 (a): このまま、取引所の模型は変えない)。
        # 決済の注文(close・flatten)は reduce_only で出す(5 周目 (2-1)): 送った後に建玉が減っても、取引所の模型が
        # 建玉を超える分を切る(bot.bt.fill.venue の _fill)ので、決済が逆向きの建玉を作らない(「段」に数えられない)
        req = OrderRequest(side=side, order_type=order_type, size=qty, price=price, client_order_id=coid,
                           reduce_only=reduce_only)
        row["reduce_only"] = "true" if reduce_only else "false"
        self.exit_reasons[coid] = f"道: 合図 {sig}"
        assert self._ctx is not None
        self._ctx.place_order(req)
        row["sent_t_ns"] = now
        view = self._ctx.order(coid)
        row["state"] = view.state.value if view is not None else ""
        return coid

    def position(self) -> str:
        """土台が約定の知らせから持つ建玉(10 進の文字列。買いが +)。"""
        return _dec_text(self._pos)

    def cancel(self, order_id: str) -> None:
        now = self._now("cancel")
        row = self._orders.get(order_id)
        if row is None or row["sent_t_ns"] == "":
            _fail(f"cancel: 注文 {order_id!r} は出していない")
        if row["exit_kind"] == EXIT_FLATTEN:
            _fail(f"cancel: 決済の成行 {order_id!r} は取り消せない(flatten は全部閉じるまで続く)")
        if row["cancel_sent_t_ns"] == "":
            row["cancel_sent_t_ns"] = now
        assert self._ctx is not None
        self._ctx.cancel_order(order_id)
        self._cancel_pending[order_id] = True

    def order_state(self, order_id: str) -> str:
        """土台が記録した注文の最後の状態(量が 0 で出さなかった行は「量が 0 で出さない」)。"""
        row = self._orders.get(order_id)
        if row is None:
            _fail(f"order_state: 注文 {order_id!r} は無い")
        return row["state"]

    # ---- 道の走らせが読む -------------------------------------------------------------
    def road_record(self) -> dict:
        """記録の写し: {quote_ccy, fx, fx_source, signals, orders}。データの終わりまで消えなかった合図は、
        消失の時刻を空・理由を「データの終わり」にする。"""
        signals = []
        for row in self._signals.values():
            r = dict(row)
            if r["end_t_ns"] == "":
                r["end_reason"] = DATA_END
            signals.append(r)
        return {"quote_ccy": self.quote_ccy, "fx": [dict(p) for p in self._fx_rows], "fx_source": self._fx_source,
                "signals": signals, "orders": [dict(r) for r in self._orders.values()],
                "fill_notices": {k: list(v) for k, v in self._notices.items()}}
