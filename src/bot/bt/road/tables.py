"""道の記録の表(RECORD_FORM_L766.md §2、L-766・L-767)。書き出しと読み込みと、生の表から作る表の作り方。

オーナーの逐語:
- L-766「**・再利用、分解が可能な形 ・建玉価格の平均化や決済の計算に使った生の約定履歴(時間、価格、数量、ドル円変換に使ったusd/jpyの値、など) ・シグナルの発生・消失の時間**」
- L-767「**a 残す b残す c １つ目**」
- L-754「**私がしてほしいの決まりを足すんじゃなくて、この計算が確実にできるツールを作ることと、そのツールが必ず使われる仕組みです。**」

1 回の走らせ = 1 つの置き場(道の走らせの置き場 `<runs_dir>/<run_id>/` の下の `road/`)。表は gzip した CSV
(1 行 = 1 件、全部の欄は文字列。空の欄は「無い」)。`summary` は JSON。列・単位・生か作ったものかは `SCHEMA.json`
(= このモジュールの `SCHEMA`)。どの表にも銘柄(`instrument`)と約定の範囲の側(`range`: 悲観側 pessimistic・
楽観側 optimistic)の列があり、帳簿は (銘柄, 側) ごとに計算する。

- 生の表: `signals`(戦略が宣言し土台が時刻を押す)・`orders`(土台の記録)・`fills`(道の約定 = pipeline の約定)・
  `fx`(戦略に渡した USDJPY の系列)
- 作った表: `ledger_fills`・`trades`・`summary`。`derive(fills, fx, groups)` 1 つで、生の表の文字列の行から作る。
  書き出しも検査(`check.check_tables`)も同じ `derive` を使うので、突き合わせは文字列の比較になる。
  pipeline の `trades`(FIFO の `round_trips`)は使わない。

(銘柄, 側) の組は、道の走らせの宣言の銘柄 × 側(書き出しの口が渡す)と生の表に出てくる組を合わせたもの(名前の順)。
`summary` の `groups` に残し、何もしなかった (銘柄, 側) も `summary` に 0 の行を出す(2 周目 (f))。

ここで出す文は全部日本語(O-1)。
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import os
from typing import Any, Iterable, Mapping, Optional, Sequence

from .ledger import LedgerError, book
from .strategy import NO_SIGNAL

ROAD_DIR = "road"
SCHEMA_FILE = "SCHEMA.json"
SCHEMA_VERSION = "road-record-4"  # 4: expired_t_ns → venue_closed_t_ns、exit_kind、flatten_pending_at_send → exit_pending_at_send(4 周目)
# 3  # 3: 取り消しの拒否・状態不明・届いた順の列、約定の知らせの時刻、限界の文(3 周目)
# 2  # 2: 拒否の時刻・量の出所・送る時点の建玉の列、summary の groups(2 周目)
SUMMARY_TABLE = "summary"
RANGES = ("optimistic", "pessimistic")  # 約定の範囲の側(bot.bt.pipeline.SIDES と同じ。pipeline をここから読まない)
RAW = "生"
MADE = "作ったもの(帳簿のツール)"

_IR = [("instrument", "-", "銘柄の名前(道の走らせの宣言)"),
       ("range", "-", "約定の範囲の側: pessimistic(悲観側)/ optimistic(楽観側)")]

SCHEMA: dict = {
    "version": SCHEMA_VERSION,
    "form": "表は gzip した CSV(UTF-8、1 行目が列の名前、全部の欄は文字列、空の欄は「無い」)。summary は JSON。"
            "時刻は UTC の ns の整数。数は 10 進の文字列(浮動小数は最短の 10 進)",
    "keys": "走らせ → 合図の番号 → 注文の番号 → 約定の番号 → 取引の番号。番号は (instrument, range) の中で一意",
    "read_from": "道の走らせの読み口は road/ のこの表だけ。同じ走らせの置き場の pipeline の trades.json と metrics.json の"
                 "取引の数は、建ての分と決済の約定の組ごとに 1 取引と数える FIFO の数え方で、道の数え方(建玉 0 → 0 で 1 取引。"
                 "L-749・L-750)ではない",
    "limits": [
        "戦略は同じ Python の中で動くので、戦略が土台の内部の記録(合図の発生・消失の時刻など)を書き換えるのは機械で"
        "塞ぎ切れない。外から照らせる記録(pipeline の約定・注文、足、fx、repro.json の指紋)との突き合わせで落とせない"
        "書き換え(合図の時刻を足の閉じた別の時刻に動かす、合図の種類・向き・値・消失の理由を変える)は検査を通る",
        "量の計算の値段は、出所が「直近の足の終値」なら足の終値と、「指値」なら指値と突き合わせる。「直近の約定の値段」"
        "「直近の板の仲値」は突き合わせる記録が検査に渡らないので突き合わせない",
        "合図の時刻の足の検査(分の区切り・その時刻に閉じた 1 分足)は、足で動き足の遅れ(feed の遅延)が 0 の走らせを"
        "前提にする。足の遅れが 0 でない走らせは必ず落ちる",
        "検査は置き場が道の走らせの置き場の road/ であることを求める(../repro.json・record.json・fills.json・"
        "orders.json)。repro.json も書き換えられるので、最後の錨は押し出しの関門(L-755、次の段)",
        "受け付けられた時刻: 道の走らせの門(pipeline の ArrivalGate)が預かる成行は、門がその場で受け付けを返す"
        "(取引所の受け付けではない)",
        "期限が切れた時刻: 取引所の模型に期限つきの注文(GTD)が無いので、ここに入るのは取引所が自分で閉じたもの"
        "(期限切れ・成行の残り・reduce_only など。理由は close_reason)",
        "書き出しの後の書き換えは repro.json の指紋で落ちる。repro.json の指紋も合わせて書き換えた場合に検査を通る欄"
        "(4 周目に、表の全部の行の全部の欄を 1 欄ずつ書き換えて確かめた。tests/road/test_road_record.py の "
        "test_r4_sweep_every_row_forged): "
        "signals の kind・direction・end_reason、消えた合図の end_t_ns、注文の無い合図の signal_id・start_t_ns / "
        "orders の acked_t_ns、取り消しの答えの無い注文の cancel_sent_t_ns、cancel_rejected_t_ns・state_unknown_t_ns、"
        "表の順を崩さない範囲の placed_seq、約定の無い注文の closed_seq、close_reason / "
        "fills の notice_t_ns・notice_seq(知らせの順を崩さない範囲) / "
        "fx の source、どの計算にも使われていない fx の行の t_ns・rate",
    ],
    "tables": {
        "signals": {
            "file": "signals.csv.gz", "kind": RAW, "row": "合図 1 つ",
            "columns": _IR + [
                ("signal_id", "-", "合図の番号(戦略が付ける)"),
                ("kind", "-", "合図の種類(戦略が宣言)"),
                ("direction", "-", "合図の向き(戦略が宣言)"),
                ("value_json", "JSON", "発生の時点で戦略が見た値(戦略が宣言したもの)"),
                ("start_t_ns", "ns", "発生の時刻(土台が ctx.now_ns で押す)"),
                ("end_t_ns", "ns", "消失の時刻 = 合図の条件が成り立たなくなった時刻(L-767 c)。データの終わりまで消えなければ空"),
                ("end_reason", "-", "消失の理由(戦略が宣言)。データの終わりまで消えなければ「データの終わり」"),
            ]},
        "orders": {
            "file": "orders.csv.gz", "kind": RAW, "row": "注文 1 つ(量が 0 で出さなかった段も 1 行)",
            "columns": _IR + [
                ("order_id", "-", "注文の番号(土台が付ける client_order_id)"),
                ("origin", "-", "出所: 土台(戦略が place で出した)/ 口座の強制"),
                ("signal_id", "-", "合図の番号、または「無し」(合図に依らない注文)"),
                ("side", "-", "buy / sell"),
                ("order_type", "-", "market / limit"),
                ("limit_px", "値段の通貨", "指値の値段(成行は空)"),
                ("qty", "BTC", "注文の量(量の出所が「量の計算」なら切り捨て後の量、「建玉」なら |送る時点の建玉 + 出ている決済の量|)"),
                ("placed_t_ns", "ns", "土台が place / close / flatten を受けた時刻(flatten の続きは、その知らせが届いた時刻)"),
                ("placed_seq", "-", "そのとき土台に届いていた出来事の通し番号(届いた順。約定の notice_seq と比べる)"),
                ("sent_t_ns", "ns", "出した時刻(ctx.place_order に渡した時刻。出さなかった行は空)"),
                ("acked_t_ns", "ns", "受け付けられた時刻(OrderAckEvent が戦略に届いた時刻。門が預かる成行は門の受け付けで、"
                                     "取引所の受け付けではない)"),
                ("acked_venue_t_ns", "ns", "受け付けの取引所での時刻(OrderAckEvent の exchange_time_ns)"),
                ("cancel_sent_t_ns", "ns", "取り消しを出した時刻(土台の cancel)"),
                ("canceled_t_ns", "ns", "取り消した時刻(OrderCanceledEvent で answers = cancel が届いた時刻)"),
                ("venue_closed_t_ns", "ns", "取引所が自分で閉じた時刻(成行の残り・reduce_only・oco など。理由は close_reason)。"
                                            "OrderCanceledEvent で answers = venue、中身が拒否でないものが届いた時刻。"
                                            "期限切れはここに入る(今の取引所の模型には期限つきの注文が無い)。"
                                            "列の名前は 3 周目までの expired_t_ns から変えた(一度出した語の意味を広げて使い回さない。O-7)"),
                ("rejected_t_ns", "ns", "拒否された時刻: OrderRejectEvent(新規)、または中身が拒否の OrderCanceledEvent"
                                        "(answers = venue / new で、理由が rejected_by_venue・refused_by_account で始まるか "
                                        "post_only_would_take)が届いた時刻"),
                ("cancel_rejected_t_ns", "ns", "取り消しが拒否された時刻(OrderRejectEvent で request_kind = cancel、最初の 1 つ)"),
                ("state_unknown_t_ns", "ns", "状態不明の答えが届いた時刻(OrderStateUnknownEvent、新規・取り消しのどちらも。最初の 1 つ)"),
                ("closed_t_ns", "ns", "閉じた知らせ(取り消し・期限切れ・新規への答えの一部としての取り消し・拒否)が届いた時刻"),
                ("closed_venue_t_ns", "ns", "その取引所での時刻"),
                ("closed_seq", "-", "閉じた知らせが届いたときの出来事の通し番号"),
                ("close_kind", "-", "閉じ方の生の値: cancel / venue / new(OrderCanceledEvent の answers)/ reject"),
                ("close_reason", "-", "閉じた理由の生の値(知らせの reason)"),
                ("state", "-", "最後の状態(戦略の側の注文の見え方の状態)、または「量が 0 で出さない」"),
                ("filled_qty", "BTC", "約定した量(届いた OrderFillEvent の量の和)"),
                ("margin_jpy", "円", "量の計算に使った証拠金(L-743・L-744: 毎回 20 万円)"),
                ("use_ratio", "割合", "量の計算に使った比率(L-746: 70%)"),
                ("levels", "段", "段数(戦略が渡す)"),
                ("size_px", "値段の通貨", "量の計算に使ったその時の値段(指値 = 指値の値段、成行 = 直近の値段)"),
                ("size_px_source", "-", "その時の値段の出所: 指値 / 直近の足の終値 / 直近の約定の値段 / 直近の板の仲値"),
                ("quote_ccy", "-", "値段の通貨 JPY / USD / USDT"),
                ("usdjpy", "円/ドル", "量の計算に使った USDJPY(ドル建てのとき。出した時刻以前の最後の相場)"),
                ("usdjpy_t_ns", "ns", "その相場の時刻"),
                ("qty_raw", "BTC", "切り捨て前の量(Decimal、28 桁)"),
                ("qty_source", "-", "量の出所: 量の計算(place。margin_jpy〜qty_raw の列で計算)/ 建玉(close・flatten。量の計算の列は空)"),
                ("position_at_send", "BTC", "注文を受けた時点の建玉(土台が約定の知らせから持つ建玉、買いが +)"),
                ("exit_pending_at_send", "BTC", "決済の行(量の出所が建玉): 送る時点で出ていた決済の注文(close・flatten)のまだ約定していない量"
                                                "(買いが +)。量 = |position_at_send + これ|"),
                ("exit_kind", "-", "決済の種類: close(close が出した注文)/ flatten(flatten が出した成行)/ flatten_call(flatten を"
                                   "呼んだときに注文を出さなかった記録の行)/ 空(place の注文)"),
            ]},
        "fills": {
            "file": "fills.csv.gz", "kind": RAW, "row": "約定 1 つ(道の約定 = pipeline の約定)",
            "columns": _IR + [
                ("fill_id", "-", "約定の番号((instrument, range) の中の順番。0 から)"),
                ("order_id", "-", "注文の番号"),
                ("signal_id", "-", "合図の番号(注文の合図の番号を写したもの)"),
                ("t_ns", "ns", "約定の時刻(pipeline の t_ns: 値を決めた観測の時刻)"),
                ("venue_t_ns", "ns", "取引所での約定の時刻"),
                ("side", "-", "buy / sell"),
                ("qty", "BTC", "量"),
                ("px", "値段の通貨", "値段"),
                ("ccy", "-", "値段の通貨"),
                ("fee", "口座の通貨", "手数料(帳簿の損益には入れない。L-741)"),
                ("liquidity", "-", "maker(指値)/ taker(成行)"),
                ("notice_t_ns", "ns", "この約定の知らせが戦略(土台)に届いた時刻(データの終わりまで届かなければ空)"),
                ("notice_seq", "-", "そのときの出来事の通し番号(届いた順。注文の placed_seq と比べる)"),
            ]},
        "fx": {
            "file": "fx.csv.gz", "kind": RAW, "row": "USDJPY の相場 1 点(戦略に渡した系列。円建ては行が無い)",
            "columns": _IR + [
                ("t_ns", "ns", "相場の時刻"),
                ("pair", "-", "通貨の組(USDJPY = 1 ドルの円)"),
                ("rate", "円/ドル", "相場"),
                ("source", "-", "出所(戦略の宣言の fx_source)"),
            ]},
        "ledger_fills": {
            "file": "ledger_fills.csv.gz", "kind": MADE, "row": "約定 1 つ(fills と fx から帳簿のツールで作る)",
            "columns": _IR + [
                ("fill_id", "-", "約定の番号(fills と同じ)"),
                ("t_ns", "ns", "約定の時刻"),
                ("side", "-", "buy / sell"),
                ("qty", "BTC", "量"),
                ("px", "値段の通貨", "値段"),
                ("ccy", "-", "値段の通貨"),
                ("position_after", "BTC", "その後の建玉(買いが +)"),
                ("avg_px_after", "値段の通貨", "その後の平均の建値(建玉 0 なら空)"),
                ("pnl_quote", "値段の通貨", "今回の確定損益(換算の前)"),
                ("usdjpy", "円/ドル", "今回の損益を円にするのに使った USDJPY = 属する取引の開始の相場(円建ては 1)"),
                ("usdjpy_t_ns", "ns", "その相場の時刻(円建ては空)"),
                ("pnl_jpy", "円", "今回の確定損益(円)"),
                ("pnl_jpy_cum", "円", "累計の確定損益(円)"),
                ("trade_id", "-", "属する取引の番号(ドテンなら閉じた側)"),
                ("opens_trade_id", "-", "この約定で始まった取引の番号(無ければ空)"),
            ]},
        "trades": {
            "file": "trades.csv.gz", "kind": MADE, "row": "取引 1 つ(建玉 0 → 0。L-749・L-750)",
            "columns": _IR + [
                ("trade_id", "-", "取引の番号((instrument, range) の中の順番。0 から)"),
                ("signal_id", "-", "最初の約定の合図の番号"),
                ("first_fill_id", "-", "最初の約定の番号"),
                ("fill_count", "件", "この取引の約定の数"),
                ("first_t_ns", "ns", "最初の約定の時刻"),
                ("last_t_ns", "ns", "最後の約定の時刻"),
                ("direction", "-", "long / short"),
                ("levels", "段", "段の数(建てる向きの約定の数)"),
                ("max_position", "BTC", "最大の建玉"),
                ("hold_ns", "ns", "保有時間(最初の約定から建玉 0 まで。途中は空。L-755)"),
                ("pnl_jpy", "円", "損益(円。途中はそこまでの確定分)"),
                ("usdjpy", "円/ドル", "損益を円にするのに使った USDJPY = 取引の開始の時刻以前の最後の相場(円建ては 1。L-763・L-764)"),
                ("usdjpy_t_ns", "ns", "その相場の時刻(円建ては空)"),
                ("status", "-", "closed(閉じた)/ open(途中)"),
                ("position", "BTC", "データの終わりの建玉(途中の取引だけ)"),
                ("avg_px", "値段の通貨", "データの終わりの平均の建値(途中の取引だけ)"),
            ]},
        SUMMARY_TABLE: {
            "file": "summary.json", "kind": MADE,
            "row": "(instrument, range) 1 つ(JSON の rows の 1 要素。合図・注文・約定の無い組も 0 の行。"
                   "groups は走らせの (instrument, range) の一覧 = 道の走らせの宣言の銘柄 × 側、生)",
            "columns": _IR + [
                ("fill_count", "件", "約定の数"),
                ("closed_trades", "件", "閉じた取引の数"),
                ("pnl_jpy", "円", "閉じた取引の損益の合計"),
                ("open_trades", "件", "途中の取引の数"),
            ]},
    },
}
# JSON にしたときの形(列は [名前, 単位, 意味] の列)にそろえておく
SCHEMA = json.loads(json.dumps(SCHEMA, ensure_ascii=False))
TABLES = tuple(SCHEMA["tables"])
CSV_TABLES = tuple(t for t in TABLES if t != SUMMARY_TABLE)


def columns(table: str) -> list:
    return [c[0] for c in SCHEMA["tables"][table]["columns"]]


class TableError(ValueError):
    """道の記録の表が作れない・読めない(文は日本語)。"""


def text(v: Any) -> str:
    """欄の値を文字列に。None は空、整数はそのまま、浮動小数は最短の 10 進(repr)、文字列はそのまま。"""
    if v is None:
        return ""
    if isinstance(v, bool):
        raise TableError(f"真偽値は欄に書かない: {v!r}")
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, (int, str)):
        return str(v)
    return str(v)


def _canon(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1, allow_nan=False)


# --------------------------------------------------------------------------- 生の表を作る(道の走らせの後)
def raw_tables(runs: Iterable[tuple]) -> dict:
    """runs: (銘柄, 側, 銘柄の値段の通貨, pipeline の約定の行の列, 土台の記録 `RoadStrategy.road_record()`) の列。
    返すのは生の表 {signals, orders, fills, fx}(各々 文字列の行の列)。"""
    out: dict = {t: [] for t in ("signals", "orders", "fills", "fx")}
    for inst, rng, quote_ccy, fills, rec in runs:
        if rec is None:
            raise TableError(f"銘柄 {inst}・側 {rng} に道の戦略の土台の記録が無い(道の戦略は bot.bt.road.RoadStrategy を継ぐ)")
        if rec["quote_ccy"] != quote_ccy:
            raise TableError(f"銘柄 {inst}・側 {rng}: 戦略の値段の通貨 {rec['quote_ccy']} が銘柄の宣言の値段の通貨 "
                             f"{quote_ccy} と違う")
        ir = {"instrument": inst, "range": rng}
        for s in rec["signals"]:
            out["signals"].append({**ir, **{k: text(s[k]) for k in columns("signals")[2:]}})
        sig_of = {}
        for o in rec["orders"]:
            out["orders"].append({**ir, **{k: text(o[k]) for k in columns("orders")[2:]}})
            sig_of[o["order_id"]] = o["signal_id"]
        seen: dict = {}
        for k, f in enumerate(fills):
            oid = f["order_id"]
            if oid not in sig_of:
                raise TableError(f"銘柄 {inst}・側 {rng}: 約定 {k} の注文 {oid!r} が土台の記録に無い")
            if f.get("range", rng) != rng or f.get("instrument", inst) != inst:
                raise TableError(f"銘柄 {inst}・側 {rng}: 約定 {k} の銘柄・側が違う")
            got = seen.get(oid, 0)
            seen[oid] = got + 1
            ns = rec.get("fill_notices", {}).get(oid, [])
            nt, nq = (ns[got][0], ns[got][1]) if got < len(ns) else ("", "")
            out["fills"].append({**ir, "fill_id": str(k), "order_id": oid, "signal_id": sig_of[oid],
                                 "notice_t_ns": text(nt), "notice_seq": text(nq),
                                 "t_ns": text(f["t_ns"]), "venue_t_ns": text(f["venue_t_ns"]), "side": f["side"],
                                 "qty": text(float(f["qty"])), "px": text(float(f["px"])), "ccy": quote_ccy,
                                 "fee": text(float(f["fee"])), "liquidity": text(f["liquidity"])})
        for p in rec["fx"]:
            out["fx"].append({**ir, "t_ns": text(p["t_ns"]), "pair": p["pair"], "rate": text(float(p["rate"])),
                              "source": rec.get("fx_source", "")})
    return out


def groups_of(signals: Sequence[Mapping], orders: Sequence[Mapping], fills: Sequence[Mapping]) -> list:
    """(銘柄, 側) の組。生の表に出てくる組を名前の順で。"""
    return sorted({(r.get("instrument", ""), r.get("range", "")) for rows in (signals, orders, fills) for r in rows})


# --------------------------------------------------------------------------- 作った表(帳簿のツール)
def _int(v: str, what: str) -> int:
    try:
        if v.strip() != v or not v:
            raise ValueError
        return int(v)
    except (ValueError, AttributeError):
        raise TableError(f"{what} が整数として読めない: {v!r}") from None


def _float(v: str, what: str) -> float:
    try:
        if v.strip() != v or not v:
            raise ValueError
        return float(v)
    except (ValueError, AttributeError):
        raise TableError(f"{what} が数として読めない: {v!r}") from None


def derive(fills: Sequence[Mapping], fx: Sequence[Mapping], groups: Sequence[tuple]) -> tuple[list, list, dict]:
    """groups: 走らせの (銘柄, 側) の一覧(合図・注文・約定の無い組も summary に 0 の行を出す。2 周目 (f))。"""
    groups = sorted({tuple(g) for g in groups})
    """生の表 `fills`・`fx`(文字列の行)から、(銘柄, 側) ごとに帳簿のツール(`ledger.book`)で
    `ledger_fills`・`trades`・`summary` を作る。読めない欄・帳簿のツールが止まる列は `TableError`。"""
    lf_rows, tr_rows, sm_rows = [], [], []
    for inst, rng in groups:
        mine = [r for r in fills if r.get("instrument") == inst and r.get("range") == rng]
        rates = [r for r in fx if r.get("instrument") == inst and r.get("range") == rng]
        where = f"銘柄 {inst}・側 {rng}"
        inp = []
        for k, r in enumerate(mine):
            if r.get("fill_id") != str(k):
                raise TableError(f"{where}: fills の約定の番号 {r.get('fill_id')!r} が順番 {k} と違う")
            inp.append({"t_ns": _int(r.get("t_ns", ""), f"{where} 約定 {k} の t_ns"), "side": r.get("side"),
                        "qty": _float(r.get("qty", ""), f"{where} 約定 {k} の qty"),
                        "px": _float(r.get("px", ""), f"{where} 約定 {k} の px"), "ccy": r.get("ccy")})
        pts = [{"t_ns": _int(p.get("t_ns", ""), f"{where} 為替の t_ns"), "pair": p.get("pair"),
                "rate": _float(p.get("rate", ""), f"{where} 為替の rate")} for p in rates]
        try:
            led = book(inp, pts or None)
        except LedgerError as exc:
            raise TableError(f"{where}: 帳簿のツールで計算できない: {exc}") from None
        ir = {"instrument": inst, "range": rng}
        for k, f in enumerate(led.fills):
            src = mine[k]
            lf_rows.append({**ir, "fill_id": src["fill_id"], "t_ns": text(f["t_ns"]), "side": f["side"],
                            "qty": src["qty"], "px": src["px"], "ccy": f["ccy"],
                            "position_after": text(f["position_after"]), "avg_px_after": text(f["avg_px_after"]),
                            "pnl_quote": text(f["pnl_quote"]), "usdjpy": text(f["usdjpy"]),
                            "usdjpy_t_ns": text(f["usdjpy_t_ns"]), "pnl_jpy": text(f["pnl_jpy"]),
                            "pnl_jpy_cum": text(f["pnl_jpy_cum"]), "trade_id": text(f["trade"]),
                            "opens_trade_id": text(f["opens_trade"])})
        for j, tr in enumerate(led.trades):
            first = mine[tr["fills"][0]]
            tr_rows.append({**ir, "trade_id": str(j), "signal_id": first["signal_id"], "first_fill_id": first["fill_id"],
                            "fill_count": str(len(tr["fills"])), "first_t_ns": text(tr["first_t_ns"]),
                            "last_t_ns": text(tr["last_t_ns"]), "direction": tr["direction"],
                            "levels": text(tr["levels"]), "max_position": text(tr["max_position"]),
                            "hold_ns": text(tr["hold_ns"]), "pnl_jpy": text(tr["pnl_jpy"]),
                            "usdjpy": text(tr["usdjpy"]), "usdjpy_t_ns": text(tr["usdjpy_t_ns"]),
                            "status": tr["status"], "position": text(tr.get("position")),
                            "avg_px": text(tr.get("avg_px"))})
        s = led.summary
        sm_rows.append({**ir, "fill_count": s["fill_count"], "closed_trades": s["closed_trades"],
                        "pnl_jpy": s["pnl_jpy"], "open_trades": s["open_trades"]})
    return lf_rows, tr_rows, {"version": SCHEMA_VERSION, "groups": [list(g) for g in groups], "rows": sm_rows}


# --------------------------------------------------------------------------- 書く・読む
def _write_csv(path: str, table: str, rows: Sequence[Mapping]) -> None:
    cols = columns(table)
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(cols)
    for r in rows:
        if set(r) != set(cols):
            raise TableError(f"{table} の行の列 {sorted(r)} が SCHEMA の列と違う(作りの誤り)")
        w.writerow([r[c] for c in cols])
    # 2 回の実行で同じバイトになるよう、gzip の時刻を 0・名前を空にする(pipeline の再現の突き合わせ)
    with open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            gz.write(buf.getvalue().encode("utf-8"))


def write_tables(store_dir: str, raw: Mapping[str, list], groups: Optional[Sequence[tuple]] = None) -> dict:
    """生の表を書き、生の表から作った表(derive)と SCHEMA.json も書く。書いた表を全部返す。
    groups: 走らせの (銘柄, 側) の一覧。生の表に出てくる組は必ず足す。"""
    groups = sorted(set(map(tuple, groups or ())) | set(groups_of(raw["signals"], raw["orders"], raw["fills"])))
    lf, tr, sm = derive(raw["fills"], raw["fx"], groups)
    tables = {"signals": raw["signals"], "orders": raw["orders"], "fills": raw["fills"], "fx": raw["fx"],
              "ledger_fills": lf, "trades": tr, SUMMARY_TABLE: sm}
    os.makedirs(store_dir, exist_ok=True)
    for t in CSV_TABLES:
        _write_csv(os.path.join(store_dir, SCHEMA["tables"][t]["file"]), t, tables[t])
    with open(os.path.join(store_dir, SCHEMA["tables"][SUMMARY_TABLE]["file"]), "w", encoding="utf-8",
              newline="\n") as fh:
        fh.write(_canon(sm) + "\n")
    with open(os.path.join(store_dir, SCHEMA_FILE), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_canon(SCHEMA) + "\n")
    return tables


def write_road_store(store_dir: str, runs: Iterable[tuple]) -> dict:
    """道の走らせの後に呼ぶ口(`bot.bt.pipeline.execute_once`)。runs は `raw_tables` と同じ。"""
    runs = list(runs)
    return write_tables(store_dir, raw_tables(runs), [(r[0], r[1]) for r in runs])


def read_csv(path: str, table: str) -> tuple[list, list]:
    """(列の名前の列, 行の列(列の名前 -> 文字列))。読めなければ `TableError`。"""
    try:
        with gzip.open(path, "rb") as gz:
            body = gz.read().decode("utf-8")
    except FileNotFoundError:
        raise TableError(f"表 {table} のファイルが無い: {path}") from None
    except (OSError, EOFError, gzip.BadGzipFile):
        raise TableError(f"表 {table} のファイルが gzip として読めない: {path}") from None
    except UnicodeDecodeError:
        raise TableError(f"表 {table} のファイルが UTF-8 の文字として読めない: {path}") from None
    try:
        rows = list(csv.reader(io.StringIO(body, newline="")))
    except csv.Error:
        raise TableError(f"表 {table} のファイルが CSV として読めない: {path}") from None
    if not rows:
        raise TableError(f"表 {table} のファイルに列の名前の行が無い: {path}")
    head = rows[0]
    out = []
    for k, r in enumerate(rows[1:]):
        if len(r) != len(head):
            raise TableError(f"表 {table} の {k} 行目の欄の数 {len(r)} が列の数 {len(head)} と違う")
        out.append(dict(zip(head, r)))
    return head, out


def read_json(path: str, what: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise TableError(f"{what}のファイルが無い: {path}") from None
    except json.JSONDecodeError as exc:
        raise TableError(f"{what}のファイルが JSON として読めない: {path}(行 {exc.lineno} 列 {exc.colno})") from None
    except UnicodeDecodeError:
        raise TableError(f"{what}のファイルが UTF-8 の文字として読めない: {path}") from None
    except OSError as exc:
        raise TableError(f"{what}のファイルを開けない: {path}(OS の誤りの番号 {exc.errno})") from None


def is_table_store(store_dir: str) -> bool:
    """表の形の置き場か(SCHEMA.json か表のファイルのどれかがある)。"""
    names = [SCHEMA_FILE] + [SCHEMA["tables"][t]["file"] for t in TABLES]
    return any(os.path.exists(os.path.join(store_dir, n)) for n in names)


__all__ = ["CSV_TABLES", "NO_SIGNAL", "ROAD_DIR", "SCHEMA", "SCHEMA_FILE", "SUMMARY_TABLE", "TABLES", "TableError",
           "columns", "derive", "groups_of", "is_table_store", "raw_tables", "read_csv", "read_json", "text",
           "write_road_store", "write_tables"]
