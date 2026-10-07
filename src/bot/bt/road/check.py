"""検査のツールの本体(L-754・L-755)。CLI は `scripts/road/check_outputs.py`。

オーナーの逐語:
- L-754「**私がしてほしいの決まりを足すんじゃなくて、この計算が確実にできるツールを作ることと、そのツールが必ず使われる仕組みです。**」
- L-755「**1.yes 2.消す**」(検査を押し出しの関門と分析のフックにつなぐ。つなぐのは次の段で、この段では作らない)

検査が見るのは「道の外で作った数か」と「約定が足の上にあるか」だけ。帳簿のツールそのものの正しさは
`tests/road/` の場面の試験で確かめる。

(a) まとめの計算し直し: 置き場の約定の列(`road_fills.json`)から帳簿のツール(`ledger.book`)でまとめを計算し直し、
    置き場に書かれたまとめ(`road_summary.json`)と鍵・値が 1 つでも違えば失敗。まとめには約定の数と取引ごとの表
    (最初の約定の時刻・最後の約定の時刻・段の数・最大の建玉・保有時間・損益・状態)も入っているので、取引の行ごと・
    欄ごとに突き合わせる(約定を 1 つ消すと、約定の数と、その約定が属する取引の行が変わる)。
    値は型も含めて == で比べる(損益・建玉は帳簿のツールが出す 10 進の文字列。数で書かれていたら違うとみなす)。
(b) 足の検査: 約定ごとに、
    - 約定の時刻 t を含む足(始まり s ≤ t < s + 足の長さ)があるか(無ければ失敗)
    - 当たる足が 2 本以上なら失敗(足が重なっている)
    - 当たる足の始まりが足の長さの区切り(足の長さの倍数の ns)にそろうか(そろわなければ失敗)
    - 約定の値段がその足の安値以上・高値以下か(外なら失敗)
    足は引数で受ける: 1 本 = {"t_ns": 足の始まり(ns), "high": 数, "low": 数}(ほかの鍵は見ない)。足の長さは決め打ちしない:
    この置き場には走らせの記録が無いので、足のファイルの隣り合う始まりの間隔で一番多いものから読む(始まりの違う足が
    2 本以上要る。無ければ失敗)。

置き場の形(この段で決めたもの。道につなぐ段で変えるときは `write_store` / `read_store` の 2 つだけを直す):
- `road_fills.json`: {"fills": [約定の行 ...], "fx": [{"t_ns", "pair", "rate"} ...]}  約定の行は `ledger` の入力の形
- `road_summary.json`: 帳簿のツールのまとめ(`ledger.SUMMARY_KEYS`: fill_count・closed_trades・pnl_jpy・open_trades・
  trades。trades の行は `ledger.TRADE_KEYS`)

表の形の置き場(道の走らせの `road/`。RECORD_FORM_L766.md §2・§4、委任文 DELEGATION_record_form.md 4.・3 周目)には
`check_tables` が次を当てる。失敗した行は {"check": "i"〜"vi", "row": どの表のどの行か, "reason": 日本語}。
(i)  表と列が SCHEMA どおりそろっているか: SCHEMA.json がこのコードの SCHEMA と同じ、表のファイルが全部あり、
     列の名前がその表の SCHEMA の列と同じ順で同じ(欠けたら失敗)。
(ii) 生の表 `fills`・`fx` から帳簿のツールで `ledger_fills`・`trades`・`summary` を作り直し(`tables.derive`。書き出しと
     同じ関数)、行の数・1 欄でも違えば失敗(使った USDJPY の値と相場の時刻の欄も含む)。summary の (銘柄, 側) の組
     (groups)は、走らせの記録(../record.json)の銘柄 × 側と同じであること。
(iii) 値の形とつなぎと順:
     - 売買・種類・状態・閉じ方・量の出所・決済の種類・値段の通貨・出所・約定の liquidity が決まった値の中か、
       reduce_only が決済の注文(close・flatten)で true・place の注文で false・出していない行で空か、value_json が JSON として読めるか、
       時刻・通し番号が整数か、fx の通貨の組が 6 文字の大文字か、fx の行の (銘柄, 側) が走らせの組の中か(黙って捨てない)
     - 時刻の順: 土台が受けた = 出した ≤ 受け付けられた ≤ 閉じた、出した ≤ 取り消しを出した ≤ 取り消した、
       取引所での時刻 ≤ 戦略に届いた時刻、取り消した・期限が切れた・拒否された時刻 = 閉じた時刻(閉じ方と合う)
     - 届いた順: 注文を受けた時の通し番号は表の順に減らない、約定の知らせの通し番号は一意でその注文を受けた後、
       知らせの通し番号の順に届いた時刻が減らない
     - つなぎ: どの約定にも注文があり、約定の合図の番号 = その注文の合図の番号。どの注文にも存在する合図か「無し」が
       ある。合図のある注文は合図の発生の後に出ている。どの合図も発生 ≤ 消失、消失の時刻が空なら理由は「データの終わり」
(iv) 足の検査: 足の長さ L は走らせの記録(record.json の data の、足で値段を付ける銘柄の price のデータの
     generator.params.step_ns か spec.bar.interval_s)から読む(そういう銘柄が無い・記録が読めないときは (b) と同じく
     足のファイルから。銘柄で L が違えば失敗)。約定は (b) と同じ(その時刻の足・L の区切り・安値以上高値以下)。ただし、
     足で値段を付ける銘柄の maker の約定(足で約定させた指値。t_ns = 取引所での時刻 = 約定させた足が閉じた時刻)は、
     t_ns で閉じた足 [t − L, t) と比べる(5 周目 (2-5))。成行(門が預かって次の足の始値で付けた約定。t_ns = 足の始まり)
     は今のまま。合図の発生・消失の時刻は、L の区切りで、その時刻に閉じた足(始まり = 時刻 − L)があること
     (戦略は足が閉じた時刻に足を見て合図を出す)。足は「足の JSON の n 本目」(1 から)と始まり・閉じた時刻(UTC)で書く。
     **足の遅れ(feed の遅延)が 0 でない走らせでは、合図の時刻が足の閉じた時刻より遅れて区切りから外れるので、
     この検査に必ず落ちる**(2 周目 (e): 今のまま。`tests/road/test_road_record.py` の場面で確かめている)。
(v)  注文の量と量の計算の値:
     - 量の出所が「量の計算」(place)の行: 証拠金 = 200,000 円・比率 = 0.7(検査の側の定数。L-743・L-746)、記録した
       量の計算の値から `size_per_level` で計算し直した量 = 注文の量(切り捨て前の量も)、量の計算の値段 = 指値なら指値の
       値段・直近の足の終値なら土台が受けた時刻以前に閉じた最後の足の終値(足の JSON に close が要る)、
       ドル建ての USDJPY = fx の土台が受けた時刻以前の最後の相場(時刻も)、円建ては USDJPY が空、
       受けた時点の建玉 = それまでに知らせの届いた約定の帳簿のツールの建玉
     - 量の出所が「建玉」(close・flatten)の行: 量の計算の列は空、送る時点の建玉 = 注文を受けた時の通し番号までに
       知らせの届いた約定で帳簿のツールが出す建玉、出ていた決済の量 = それより前の決済の行(close・flatten)で閉じておらず
       まだ約定していない量(同じ通し番号までの知らせで)。決済の種類(exit_kind)ごとに:
       flatten = |建玉 + 出ていた決済の量|(0 でない)、close = 同じ(ただし建玉 0、または和が 0 か建玉と逆の向きなら 0)、
       flatten_call(呼んだ記録の行)= 0。売買はその逆(3 周目 問 5・4 周目 (2))
     - 量が 0 の行は状態「量が 0 で出さない」で出していない(出した時刻が空)、量が 0 でない行は状態がそれでない
     - 注文ごとに、知らせの届いた約定の量の和 = 約定した量、全部の約定の量の和 ≤ 注文の量
(vi) 走らせの記録との突き合わせ: 置き場は道の走らせの置き場の road/ であること(../repro.json・record.json・
     fills.json・orders.json が読める)。road/ のファイルの指紋が repro.json の指紋と同じ(書き出しの後の書き換えは
     ここで落ちる)。record.json の指紋も repro.json の指紋と同じ((vii) が読む約定の決まり・刻み・足の長さの書き換えは
     ここで落ちる)。fills の各行 = pipeline の fills.json の行(注文の番号・時刻・取引所での時刻・売買・量・値段・
     手数料・liquidity)、出した注文の量・売買・種類 = pipeline の orders.json(実際に送った量)。
(vii) 約定の決まりと指値の値段(SCHEMA の fill_rules。L-769・L-770・L-783):
     - どの走らせでも: 送った指値の値段 sent_limit_px = 計算した値段 limit_px を record.json の銘柄の刻みに切り捨てた値
       (L-783)。約定の行の印(fill_rule・fill_exit_rule)がその側の宣言(bar_rule・attached_exit)と同じ(印があるのに
       宣言に bar_rule が無ければ失敗。黙って飛ばさない)、印のある約定の liquidity = maker(L-783)
     - どちらかの側が bar_rule を選んでいれば: 両側で同じ bar_rule、楽観側 = same_bar・悲観側 = next_bar(pipeline の
       確かめを記録から掛け直す)。bar_rule の側の注文は、取引所が受け付けた時刻 = 置いた時刻(注文の遅れ 0)
     その側が bar_rule を選んだ走らせの、足で値段を付ける銘柄の指値ごとに(値段は送った値段 = 切り捨てた値段)、
     - 約定の印 fill_rule = その側の bar_rule、fill_case = 下の当たり方(range / open / entry_bar)
     - 約定させた足(t_ns に閉じた足)で、指値が 安値 ≤ 指値 ≤ 高値 なら値段 = 指値、約定する向きに範囲の外(買いの指値 >
       高値、売りの指値 < 安値)なら値段 = その足の始値(足の JSON に open が要る。無ければ失敗)、約定しない向きに範囲の外
       なら失敗
     - 注文の最初の約定の足が、当て始める足(取引所が受け付けた時刻 acked_venue_t_ns 以後に始まる足。建てと一緒に出した
       決済は、建ての最初の約定の時刻と自分の受け付けの時刻の遅い方 以後に始まる足)より前でなく、それより前の当てる足で
       この決まりなら約定していたはずの足が無いこと(楽観側の決済は、建てが約定した足の範囲に決済の値段が入っていたら
       その足で約定しているはず)。約定していない注文は、有効だった足(当て始める足から、取り消しの時刻に閉じた足まで・
       取引所が自分で閉じた時刻より前に閉じた足まで・閉じていなければ足の JSON の終わりまで。同じ時刻では足が取引所に
       届いてから注文・取り消しが届く)の範囲に値段が入る足、または約定する向きに外の足があれば失敗
     - 決済が建てと同じ足で約定した行(with_entry の約定の t_ns = 建ての最初の約定の t_ns)は、楽観側(attached_exit =
       same_bar)にしか無く、値段 = 決済の指値で、その足の範囲の内であること
     (iii) では、建てと一緒に出した決済の行(exit_kind = with_entry)の attached_to が、同じ (銘柄, 側) の、同じ時に受けた
     (placed_seq・placed_t_ns が同じ)逆の売買の place の指値の行を指すこと、ほかの行の attached_to が空であることも見る。
     (v) では、with_entry の行の量 = 建ての注文の量(建てが量 0 なら 0 で出していない)、出ていた決済の量の数え方
     (with_entry の決済は、建ての約定の知らせの和(決済の量まで)からこの決済の約定の知らせの和を引いた量)も見る。
限界(SCHEMA.json の limits にも書く): 戦略が土台の合図の記録を書き換えるのは落とせない。repro.json の指紋も
合わせて書き換えた場合に通る欄がある(SCHEMA の limits に列挙)。

ここで出す文は全部日本語(O-1)。下の層の例外の英語の文は出さない。
"""
from __future__ import annotations

import bisect
import hashlib
import json
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import ROUND_FLOOR, Decimal
from typing import Mapping, Sequence

from .ledger import SUMMARY_KEYS, TRADE_KEYS, LedgerError, book
from .sizing import SizingError, size_detail
from .strategy import DATA_END, NO_SIGNAL, ORIGIN_FORCED, ORIGIN_ROAD, ZERO_QTY_STATE
from .sizing import QUOTE_CCYS
from .strategy import (EXIT_CLOSE, EXIT_FLATTEN, EXIT_FLATTEN_CALL, EXIT_KINDS, EXIT_WITH_ENTRY, OPEN_STATE_VALUES,
                       QTY_FROM_POSITION, QTY_FROM_SIZING, _dec_text)
from .tables import (CSV_TABLES, RANGES, ROAD_DIR, SCHEMA, SCHEMA_FILE, SUMMARY_TABLE, TableError, columns, derive,
                     groups_of, is_table_store, read_csv, read_json, text)

FILLS_FILE = "road_fills.json"
SUMMARY_FILE = "road_summary.json"
_NS = 1_000_000_000


def _iso(ns: int) -> str:
    """ns の時刻を UTC の文字列に(秒の端数があれば ns まで)。"""
    sec, frac = divmod(int(ns), _NS)
    out = datetime.fromtimestamp(sec, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return out + (f".{frac:09d}" if frac else "") + "Z"


def _bar_name(j: int, start: int, bar_ns: int | None) -> str:
    """オーナーに見える足の書き方: 足の JSON の 1 本目から数えた「n 本目」と始まり・閉じた時刻(O-7)。"""
    if bar_ns is None:
        return f"足の JSON の {j + 1} 本目(始まり {_iso(start)})"
    return f"足の JSON の {j + 1} 本目(始まり {_iso(start)}・閉じた時刻 {_iso(start + bar_ns)})"


def _grid_word(bar_ns: int) -> str:
    return "分の区切り" if bar_ns == 60 * _NS else f"足の長さ {bar_ns} ns の区切り"


def bar_ns_from_bars(bars: Sequence[Mapping]) -> int | None:
    """足のファイル(足の JSON)から読む足の長さ: 隣り合う足の始まりの間隔(ns)のうち一番多いもの(同じ数なら短い方)。
    始まりの違う足が 2 本以上無ければ None。走らせの記録の無い置き場(作る順 1 の road_fills.json)と、走らせの記録が
    読めないときに使う(ずれた足・重なった足・抜けた足が混じっても、そろった足が多ければその長さになる)。"""
    starts = sorted({b["t_ns"] for b in bars if isinstance(b, Mapping) and type(b.get("t_ns")) is int})
    count: dict = {}
    for a, b in zip(starts, starts[1:]):
        count[b - a] = count.get(b - a, 0) + 1
    return min(count, key=lambda g: (-count[g], g)) if count else None


@dataclass
class CheckResult:
    failures: list = field(default_factory=list)  # 失敗した行: {"check": "a"|"b", "row": ..., "reason": 日本語}

    @property
    def ok(self) -> bool:
        return not self.failures


def _dump(path: str, obj: object) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1, allow_nan=False) + "\n")


def write_store(run_dir: str, fills: Sequence[Mapping], fx: Sequence[Mapping] = ()) -> dict:
    """約定の列と、帳簿のツールで計算したまとめを置き場に書く。書いたまとめを返す。"""
    fills = [dict(f) for f in fills]
    fx = [dict(p) for p in fx]
    summary = book(fills, fx or None).summary
    os.makedirs(run_dir, exist_ok=True)
    _dump(os.path.join(run_dir, FILLS_FILE), {"fills": fills, "fx": fx})
    _dump(os.path.join(run_dir, SUMMARY_FILE), summary)
    return summary


class StoreError(ValueError):
    """置き場が読めない(文は日本語)。"""


def load_json(path: str, what: str) -> object:
    """JSON のファイルを読む。読めなければ日本語の文の `StoreError`。"""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise StoreError(f"{what}のファイルが無い: {path}") from None
    except json.JSONDecodeError as exc:
        raise StoreError(f"{what}のファイルが JSON として読めない: {path}(行 {exc.lineno} 列 {exc.colno})") from None
    except UnicodeDecodeError:
        raise StoreError(f"{what}のファイルが UTF-8 の文字として読めない: {path}") from None
    except OSError as exc:
        raise StoreError(f"{what}のファイルを開けない: {path}(OS の誤りの番号 {exc.errno})") from None


def read_store(run_dir: str) -> tuple[list, list, object]:
    """(約定の列, 為替の列, 書かれたまとめ)。ファイルが無い・読めないときは `StoreError`。"""
    body = load_json(os.path.join(run_dir, FILLS_FILE), "約定の列")
    summary = load_json(os.path.join(run_dir, SUMMARY_FILE), "まとめ")
    if not isinstance(body, dict) or not isinstance(body.get("fills"), list):
        raise StoreError(f"{FILLS_FILE} に fills の列が無い")
    fx = body.get("fx", [])
    if not isinstance(fx, list):
        raise StoreError(f"{FILLS_FILE} の fx が列でない")
    return body["fills"], fx, summary


def _same(a: object, b: object) -> bool:
    return type(a) is type(b) and a == b


def check_summary(fills: Sequence[Mapping], fx: Sequence[Mapping], written: object) -> list:
    """(a) まとめ(約定の数・取引ごとの表を含む)を計算し直して書かれたまとめと突き合わせる。"""
    try:
        again = book(fills, list(fx) or None).summary
    except LedgerError as exc:  # 帳簿のツールが止まった約定の列は、それ自体が失敗
        return [{"check": "a", "row": "約定の列", "reason": f"帳簿のツールで計算し直せない: {exc}"}]
    except Exception as exc:  # 想定外(作りの誤り)。下の層の英語の文は出さない
        return [{"check": "a", "row": "約定の列",
                 "reason": f"帳簿のツールが想定外の形で止まった(例外の種類 {type(exc).__name__})"}]
    if not isinstance(written, dict):
        return [{"check": "a", "row": "まとめ", "reason": f"書かれたまとめが辞書でない({type(written).__name__})"}]
    if set(again) != set(SUMMARY_KEYS):
        return [{"check": "a", "row": "まとめ", "reason": "帳簿のツールのまとめの鍵が SUMMARY_KEYS と違う(作りの誤り)"}]
    out = []
    for k in sorted(set(again) | set(written)):
        if k not in written:
            out.append({"check": "a", "row": k, "reason": f"書かれたまとめに {k} が無い(計算し直すと {again[k]!r})"})
        elif k not in again:
            out.append({"check": "a", "row": k, "reason": f"書かれたまとめに帳簿のツールが出さない鍵 {k} がある"})
        elif k == "trades":
            out.extend(_check_trades(written[k], again[k]))
        elif not _same(written[k], again[k]):
            out.append({"check": "a", "row": k,
                        "reason": f"書かれた値 {written[k]!r} と計算し直した値 {again[k]!r} が違う"})
    return out


def _check_trades(written: object, again: list) -> list:
    """まとめの取引ごとの表を、行ごと・欄ごとに突き合わせる。"""
    if not isinstance(written, list):
        return [{"check": "a", "row": "trades", "reason": f"書かれた取引ごとの表が列でない({type(written).__name__})"}]
    out = []
    if len(written) != len(again):
        out.append({"check": "a", "row": "trades",
                    "reason": f"書かれた取引の数 {len(written)} と計算し直した取引の数 {len(again)} が違う"})
    for j in range(max(len(written), len(again))):
        if j >= len(written):
            out.append({"check": "a", "row": f"trades[{j}]", "reason": f"書かれた表にこの取引が無い(計算し直すと {again[j]!r})"})
            continue
        if j >= len(again):
            out.append({"check": "a", "row": f"trades[{j}]", "reason": f"計算し直すと無い取引が書かれている: {written[j]!r}"})
            continue
        w, a = written[j], again[j]
        if not isinstance(w, dict):
            out.append({"check": "a", "row": f"trades[{j}]", "reason": f"書かれた取引の行が辞書でない({type(w).__name__})"})
            continue
        for k in TRADE_KEYS:
            if k not in w:
                out.append({"check": "a", "row": f"trades[{j}].{k}",
                            "reason": f"書かれた取引の行に {k} が無い(計算し直すと {a[k]!r})"})
            elif not _same(w[k], a[k]):
                out.append({"check": "a", "row": f"trades[{j}].{k}",
                            "reason": f"書かれた値 {w[k]!r} と計算し直した値 {a[k]!r} が違う"})
        for k in sorted(set(w) - set(TRADE_KEYS)):
            out.append({"check": "a", "row": f"trades[{j}].{k}",
                        "reason": f"書かれた取引の行に帳簿のツールが出さない鍵 {k} がある"})
    return out


def check_bars(fills: Sequence[Mapping], bars: Sequence[Mapping], bar_ns: int | None = None) -> list:
    """(b) 約定ごとに、その時刻を含む足・足の始まりが足の長さの区切りか・値段が安値以上高値以下かを見る。
    bar_ns: 足の長さ(ns)。None なら足のファイルから読む(`bar_ns_from_bars`。読めなければ失敗)。"""
    out = []
    if bar_ns is None:
        bar_ns = bar_ns_from_bars(bars)
        if bar_ns is None and fills:
            return [{"check": "b", "row": "足", "reason": "足の長さが決まらない(走らせの記録が無く、足のファイルに始まりの違う足が "
                                                       "2 本以上無い)。足の長さを決め打ちしない"}]
    rows = []
    for j, b in enumerate(bars):
        try:
            s, hi, lo = b["t_ns"], b["high"], b["low"]
        except (KeyError, TypeError):
            out.append({"check": "b", "row": f"足の JSON の {j + 1} 本目", "reason": "足に t_ns / high / low が無い"})
            continue
        if type(s) is not int:
            out.append({"check": "b", "row": f"足の JSON の {j + 1} 本目", "reason": f"足の t_ns が ns の整数でない: {s!r}"})
            continue
        bad = [n for n, v in (("high", hi), ("low", lo)) if not _finite_number(v)]
        if bad:
            out.append({"check": "b", "row": f"足の JSON の {j + 1} 本目", "reason": f"足の {'・'.join(bad)} が有限の数でない"})
            continue
        rows.append((s, j, float(hi), float(lo)))
    rows.sort()
    starts = [r[0] for r in rows]
    for i, f in enumerate(fills):
        if not isinstance(f, Mapping):
            out.append({"check": "b", "row": i, "reason": f"約定の行が辞書の形でない: {type(f).__name__}"})
            continue
        t, px = f.get("t_ns"), f.get("px")
        if type(t) is not int or not _finite_number(px):
            out.append({"check": "b", "row": i, "reason": f"約定の t_ns / px が読めない: {t!r} / {px!r}"})
            continue
        # 始まり s が t - 足の長さ < s <= t の足が、t を含む足
        lo_i = bisect.bisect_right(starts, t - bar_ns)
        hi_i = bisect.bisect_right(starts, t)
        hits = rows[lo_i:hi_i]
        if not hits:
            out.append({"check": "b", "row": i, "reason": f"約定の時刻 {t}({_iso(t)})を含む足(長さ {bar_ns} ns)が無い"})
            continue
        if len(hits) > 1:
            out.append({"check": "b", "row": i,
                        "reason": f"約定の時刻 {t} を含む足が {len(hits)} 本ある(始まり {[h[0] for h in hits]})"})
            continue
        s, j, hi, lo = hits[0]
        if s % bar_ns != 0:
            out.append({"check": "b", "row": i,
                        "reason": f"約定の時刻 {t} が属する足({_bar_name(j, s, bar_ns)})の始まり {s} が{_grid_word(bar_ns)}"
                                  f"から {s % bar_ns} ns ずれている"})
            continue
        if not (lo <= float(px) <= hi):
            out.append({"check": "b", "row": i,
                        "reason": f"約定の値段 {px} がその時刻の足({_bar_name(j, s, bar_ns)})の安値 {lo}〜高値 {hi} の外"})
    return out


def _finite_number(v) -> bool:
    """真偽値でない有限の数か(とても大きい整数で float に直せないものも有限でないとみなす)。"""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    try:
        return math.isfinite(float(v))
    except OverflowError:
        return False


def check_outputs(run_dir: str, bars: Sequence[Mapping]) -> CheckResult:
    """置き場 1 つを検査する。表の形の置き場(SCHEMA.json か表のファイルがある。道の走らせの `road/`)は
    `check_tables` の (i)〜(v)、それ以外(作る順 1 の road_fills.json / road_summary.json)は (a) と (b)。
    置き場が読めなければ失敗。"""
    if is_table_store(run_dir):
        return check_tables(run_dir, bars)
    try:
        fills, fx, written = read_store(run_dir)
    except StoreError as exc:
        return CheckResult([{"check": "a", "row": run_dir, "reason": f"置き場が読めない: {exc}"}])
    return CheckResult(check_summary(fills, fx, written) + check_bars(fills, bars))


# --------------------------------------------------------------------------- 表の形の置き場(道の走らせの road/)
def _fail(out: list, check: str, row: object, reason: str) -> None:
    out.append({"check": check, "row": row, "reason": reason})


def _read_all(store_dir: str, out: list) -> dict | None:
    """(i) SCHEMA.json と表を読む。読めない・列が違うものは失敗に足す。全部の表が読めたときだけ表を返す。"""
    try:
        written = read_json(os.path.join(store_dir, SCHEMA_FILE), "SCHEMA ")
    except TableError as exc:
        _fail(out, "i", SCHEMA_FILE, str(exc))
        written = None
    if written is not None and written != SCHEMA:
        _fail(out, "i", SCHEMA_FILE, "SCHEMA.json がこのコードの SCHEMA(bot.bt.road.tables.SCHEMA)と違う")
    tables: dict = {}
    for t in CSV_TABLES:
        path = os.path.join(store_dir, SCHEMA["tables"][t]["file"])
        try:
            head, rows = read_csv(path, t)
        except TableError as exc:
            _fail(out, "i", t, str(exc))
            continue
        want = columns(t)
        if head != want:
            missing = [c for c in want if c not in head]
            extra = [c for c in head if c not in want]
            detail = []
            if missing:
                detail.append(f"欠けた列 {missing}")
            if extra:
                detail.append(f"SCHEMA に無い列 {extra}")
            if not detail:
                detail.append("列の順が違う")
            _fail(out, "i", t, f"表 {t} の列が SCHEMA と違う: {'・'.join(detail)}")
            continue
        tables[t] = rows
    try:
        sm = read_json(os.path.join(store_dir, SCHEMA["tables"][SUMMARY_TABLE]["file"]), "まとめ(summary)")
    except TableError as exc:
        _fail(out, "i", SUMMARY_TABLE, str(exc))
        sm = None
    if sm is not None:
        rows = sm.get("rows") if isinstance(sm, dict) else None
        if not isinstance(sm, dict) or set(sm) != {"version", "groups", "rows"}:
            _fail(out, "i", SUMMARY_TABLE, "summary の鍵が version・groups・rows でない")
        if not isinstance(rows, list) or any(not isinstance(r, dict) or set(r) != set(columns(SUMMARY_TABLE))
                                             for r in rows):
            _fail(out, "i", SUMMARY_TABLE, f"summary の rows の各行の鍵が SCHEMA の列 {columns(SUMMARY_TABLE)} と違う")
        tables[SUMMARY_TABLE] = sm
    if len(tables) != len(SCHEMA["tables"]):
        return None
    return tables


_ID_COL = {"signals": ("signal_id", "合図"), "orders": ("order_id", "注文"), "fills": ("fill_id", "約定"),
           "ledger_fills": ("fill_id", "約定"), "trades": ("trade_id", "取引")}


def _label(table: str, k: int, r: Mapping, key: str = "") -> str:
    col, word = _ID_COL[table]
    return f"{table} の {k} 行目(銘柄 {r.get('instrument')}・側 {r.get('range')}・{word} {r.get(col)})"


def _compare_rows(out: list, table: str, written: list, again: list, key: str) -> None:
    if len(written) != len(again):
        _fail(out, "ii", table, f"表 {table} の行の数 {len(written)} が作り直した行の数 {len(again)} と違う")
    for k in range(min(len(written), len(again))):
        w, a = written[k], again[k]
        for c in columns(table):
            if w.get(c) != a.get(c):
                _fail(out, "ii", _label(table, k, w, key),
                      f"{c} の書かれた値 {w.get(c)!r} と生の表から作り直した値 {a.get(c)!r} が違う")


def _read_run(store_dir: str, out: list) -> dict | None:
    """(vi) 置き場が道の走らせの置き場の road/ であることを求め、走らせの置き場の記録を読む:
    repro.json(road/ のファイルの指紋を突き合わせる)・record.json(銘柄)・fills.json・orders.json(pipeline の書き出し)。
    読めたら {groups, pfills, porders} を返す。"""
    d = os.path.normpath(store_dir)
    if os.path.basename(d) != ROAD_DIR:
        _fail(out, "vi", store_dir, f"置き場が道の走らせの置き場の {ROAD_DIR}/ でない(走らせの記録 repro.json・record.json・"
                                    f"fills.json・orders.json と突き合わせられない)")
        return None
    parent = os.path.dirname(d)
    got = {}
    for name, what in (("repro.json", "走らせの再現の記録"), ("record.json", "走らせの記録"),
                       ("fills.json", "pipeline の約定の書き出し"), ("orders.json", "pipeline の注文の書き出し")):
        try:
            got[name] = read_json(os.path.join(parent, name), what)
        except TableError as exc:
            _fail(out, "vi", name, str(exc))
    if len(got) != 4:
        return None
    try:
        sha = got["repro.json"]["sha256"]
        want = {k[len(ROAD_DIR) + 1:]: v for k, v in sha.items() if k.startswith(ROAD_DIR + "/")}
        names = [n for n in sorted(os.listdir(d)) if os.path.isfile(os.path.join(d, n))]
        for n in sorted(set(want) | set(names)):
            if n not in names:
                _fail(out, "vi", f"{ROAD_DIR}/{n}", "repro.json に指紋があるファイルが置き場に無い")
                continue
            if n not in want:
                _fail(out, "vi", f"{ROAD_DIR}/{n}", "repro.json に指紋が無いファイルが置き場にある")
                continue
            with open(os.path.join(d, n), "rb") as fh:
                h = hashlib.sha256(fh.read()).hexdigest()
            if h != want[n]:
                _fail(out, "vi", f"{ROAD_DIR}/{n}", "ファイルの指紋が repro.json の指紋と違う(書き出しの後に書き換えた)")
        # 走らせの記録 record.json(約定の決まり・銘柄の刻み・足の長さを (vii) などがここから読む)の指紋も突き合わせる
        if "record.json" not in sha:
            _fail(out, "vi", "record.json", "repro.json に record.json の指紋が無い")
        else:
            with open(os.path.join(parent, "record.json"), "rb") as fh:
                if hashlib.sha256(fh.read()).hexdigest() != sha["record.json"]:
                    _fail(out, "vi", "record.json", "record.json の指紋が repro.json の指紋と違う(書き出しの後に書き換えた)")
        rec = got["record.json"]
        names_i = [i["name"] for i in rec["config"]["instruments"]]
        # 足で値段を付ける銘柄(price のデータが 1 分足などの bar): 足で約定させた指値の約定の比べ方に使う((iv))
        kinds = {}
        for dd in rec["data"]:
            k = (dd.get("generator") or {}).get("params", {}).get("kind") if dd.get("generator") else \
                (dd.get("spec") or {}).get("kind")
            kinds[dd["dataset"]] = k
        bar_priced = {i["name"] for i in rec["config"]["instruments"] if kinds.get(i["price"]) == "bar"}
        # 足の長さ(ns): 足で値段を付ける銘柄の price のデータの宣言から(generator.params.step_ns か spec.bar.interval_s)
        lens = {}
        for dd in rec["data"]:
            if dd.get("generator"):
                lens[dd["dataset"]] = dd["generator"].get("params", {}).get("step_ns")
            elif isinstance((dd.get("spec") or {}).get("bar"), dict):
                iv = dd["spec"]["bar"].get("interval_s")
                lens[dd["dataset"]] = iv * _NS if type(iv) is int else None
        bar_lens = {i["name"]: lens.get(i["price"]) for i in rec["config"]["instruments"] if i["name"] in bar_priced}
        # 銘柄の刻み(道の土台が指値の値段を切り捨てる刻み。L-783、(vii))
        ticks = {i["name"]: float(i["product"]["tick"]) for i in rec["config"]["instruments"]}
        pf = got["fills.json"]["data"]
        po = got["orders.json"]["data"]
        if not isinstance(pf, list) or not isinstance(po, list):
            raise TypeError
        fill = rec["config"]["fill"]  # 走らせの約定の決まり(側ごと。(vii))
        if not isinstance(fill, dict) or any(not isinstance(fill.get(r), dict) for r in RANGES):
            raise TypeError
    except (KeyError, TypeError, AttributeError):
        _fail(out, "vi", parent, "走らせの記録(repro.json・record.json・fills.json・orders.json)の形が読めない")
        return None
    return {"groups": sorted((n, r) for n in names_i for r in RANGES), "pfills": pf, "porders": po,
            "bar_priced": bar_priced, "fill": {r: dict(fill[r]) for r in RANGES}, "bar_lens": bar_lens, "ticks": ticks}


def _bar_len(run: dict | None, bars: Sequence[Mapping], out: list) -> int | None:
    """検査に使う足の長さ(ns)。走らせの記録があれば、足で値段を付ける銘柄の price のデータの宣言から読む(銘柄で違えば
    1 つの足の JSON で検査できないので失敗)。そういう銘柄が無い・記録が読めないときは足のファイルから読む。決まらなければ失敗して None。"""
    if run is not None and run["bar_lens"]:
        vals = set(run["bar_lens"].values())
        if len(vals) == 1:
            v = vals.pop()
            if type(v) is int and v > 0:
                return v
            _fail(out, "iv", "record.json", f"足の長さが走らせの記録から読めない({v!r})")
            return None
        _fail(out, "iv", "record.json", f"足で値段を付ける銘柄の足の長さが銘柄で違う({run['bar_lens']})。1 つの足の JSON で"
                                        f"検査できない")
        return None
    v = bar_ns_from_bars(bars)
    if v is None:
        _fail(out, "iv", "足", "足の長さが決まらない(走らせの記録から読めず、足のファイルに始まりの違う足が 2 本以上無い)。"
                               "足の長さを決め打ちしない")
    return v


def _check_derived(t: dict, out: list, run: dict | None) -> None:
    """(ii) 生の表から作り直して突き合わせる。(銘柄, 側) の組は、走らせの記録があればその銘柄 × 側、
    無ければ summary の groups と生の表に出てくる組を合わせたもの。"""
    w = t[SUMMARY_TABLE]
    wg = w.get("groups") if isinstance(w, dict) else None
    written_groups = set()
    if isinstance(wg, list) and all(isinstance(g, list) and len(g) == 2 and all(type(x) is str for x in g) for g in wg):
        written_groups = {tuple(g) for g in wg}
    else:
        _fail(out, "ii", SUMMARY_TABLE, "summary の groups が [銘柄, 側] の列でない")
    groups = set(groups_of(t["signals"], t["orders"], t["fills"]))
    if run is not None:
        if sorted(written_groups) != run["groups"]:
            _fail(out, "ii", SUMMARY_TABLE, f"summary の groups {sorted(written_groups)} が走らせの記録(record.json)の"
                                            f"銘柄 × 側 {run['groups']} と違う")
        groups |= set(run["groups"])
    else:
        groups |= written_groups
    try:
        lf, tr, sm = derive(t["fills"], t["fx"], groups)
    except TableError as exc:
        _fail(out, "ii", "fills・fx", f"生の表から作り直せない: {exc}")
        return
    except Exception as exc:  # 想定外(作りの誤り)。下の層の英語の文は出さない
        _fail(out, "ii", "fills・fx", f"作り直しが想定外の形で止まった(例外の種類 {type(exc).__name__})")
        return
    _compare_rows(out, "ledger_fills", t["ledger_fills"], lf, "約定")
    _compare_rows(out, "trades", t["trades"], tr, "取引")
    if not isinstance(w, dict) or w.get("version") != sm["version"] or not isinstance(w.get("rows"), list):
        _fail(out, "ii", SUMMARY_TABLE, "summary の形(version・rows)が作り直したものと違う")
        return
    if w.get("groups") != sm["groups"]:
        _fail(out, "ii", SUMMARY_TABLE, f"summary の groups {w.get('groups')!r} が作り直した組 {sm['groups']!r} と違う")
    if len(w["rows"]) != len(sm["rows"]):
        _fail(out, "ii", SUMMARY_TABLE, f"summary の行の数 {len(w['rows'])} が作り直した行の数 {len(sm['rows'])} と違う")
    for k in range(min(len(w["rows"]), len(sm["rows"]))):
        wr, ar = w["rows"][k], sm["rows"][k]
        for c in columns(SUMMARY_TABLE):
            if not isinstance(wr, dict) or not _same(wr.get(c), ar.get(c)):
                got = wr.get(c) if isinstance(wr, dict) else wr
                _fail(out, "ii", f"summary の {k} 行目(銘柄 {ar['instrument']}・側 {ar['range']})",
                      f"{c} の書かれた値 {got!r} と生の表から作り直した値 {ar.get(c)!r} が違う")


ORDER_STATES = OPEN_STATE_VALUES + ("FILLED", "CANCELED", "REJECTED")
CLOSE_KINDS = ("", "cancel", "new", "venue", "reject")
_ORDER_TIME_COLS = ("placed_t_ns", "sent_t_ns", "acked_t_ns", "acked_venue_t_ns", "cancel_sent_t_ns", "canceled_t_ns",
                    "venue_closed_t_ns", "rejected_t_ns", "cancel_rejected_t_ns", "state_unknown_t_ns", "closed_t_ns",
                    "closed_venue_t_ns", "placed_seq", "closed_seq", "usdjpy_t_ns")


def _check_forms(t: dict, out: list) -> None:
    """(iii) 値の形(決まった値の中か・JSON として読めるか・整数か)と時刻の順。"""
    for k, s in enumerate(t["signals"]):
        lab = _label("signals", k, s)
        for c in ("kind", "direction"):
            if s[c] == "":
                _fail(out, "iii", lab, f"{c} が空")
        try:
            json.loads(s["value_json"])
        except (ValueError, TypeError):
            _fail(out, "iii", lab, f"value_json {s['value_json']!r} が JSON として読めない")
    for k, o in enumerate(t["orders"]):
        lab = _label("orders", k, o)
        forced = o["origin"] == ORIGIN_FORCED
        if o["origin"] not in (ORIGIN_ROAD, ORIGIN_FORCED):
            _fail(out, "iii", lab, f"出所 {o['origin']!r} が「{ORIGIN_ROAD}」でも「{ORIGIN_FORCED}」でもない")
        zero = o["state"] == ZERO_QTY_STATE
        ok_side = ("buy", "sell") + (("",) if forced or (zero and o["qty_source"] == QTY_FROM_POSITION) else ())
        if o["side"] not in ok_side:
            _fail(out, "iii", lab, f"売買 {o['side']!r} が {ok_side} のどれでもない")
        ok_type = ("market", "limit") + (("",) if forced else ())
        if o["order_type"] not in ok_type:
            _fail(out, "iii", lab, f"種類 {o['order_type']!r} が {ok_type} のどれでもない")
        ok_state = ORDER_STATES + ((ZERO_QTY_STATE,) if not forced else ("",))
        if o["state"] not in ok_state:
            _fail(out, "iii", lab, f"状態 {o['state']!r} が決まった値(core の注文の状態か「{ZERO_QTY_STATE}」)でない")
        if o["close_kind"] not in CLOSE_KINDS:
            _fail(out, "iii", lab, f"閉じ方 {o['close_kind']!r} が {CLOSE_KINDS} のどれでもない")
        if not forced and o["qty_source"] not in (QTY_FROM_SIZING, QTY_FROM_POSITION):
            _fail(out, "iii", lab, f"量の出所 {o['qty_source']!r} が「{QTY_FROM_SIZING}」でも「{QTY_FROM_POSITION}」でもない")
        if not forced:
            want_kinds = ("",) if o["qty_source"] == QTY_FROM_SIZING else EXIT_KINDS
            if o["exit_kind"] not in want_kinds:
                _fail(out, "iii", lab, f"決済の種類 {o['exit_kind']!r} が量の出所 {o['qty_source']!r} の行の {want_kinds} のどれでもない")
            if o["quote_ccy"] not in QUOTE_CCYS:
                _fail(out, "iii", lab, f"値段の通貨 {o['quote_ccy']!r} が {QUOTE_CCYS} のどれでもない")
            if o["exit_kind"] in (EXIT_FLATTEN, EXIT_FLATTEN_CALL) and o["order_type"] != "market":
                _fail(out, "iii", lab, "flatten の行が成行でない(flatten は成行だけ)")
        elif o["exit_kind"] != "":
            _fail(out, "iii", lab, "口座の強制の注文に決済の種類が書かれている")
        if not forced:
            want_ro = "" if o["sent_t_ns"] == "" else ("true" if o["qty_source"] == QTY_FROM_POSITION else "false")
            if o["reduce_only"] != want_ro:
                _fail(out, "iii", lab, f"reduce_only {o['reduce_only']!r} が {want_ro!r} でない(決済の注文は reduce_only で出す)")
        if o["order_type"] == "market" and o["limit_px"] != "":
            _fail(out, "iii", lab, f"成行の注文に指値の値段 {o['limit_px']!r} がある")
        if o["order_type"] == "limit" and o["limit_px"] == "":
            _fail(out, "iii", lab, "指値の注文に指値の値段が無い")
        if (o["sent_limit_px"] != "") != (o["order_type"] == "limit" and o["sent_t_ns"] != ""):
            _fail(out, "iii", lab, f"送った指値の値段 sent_limit_px {o['sent_limit_px']!r} は、出した指値の行だけに書く")
        elif o["sent_limit_px"] != "" and not _finite_number(_num_or_none(o["sent_limit_px"])):
            _fail(out, "iii", lab, f"sent_limit_px {o['sent_limit_px']!r} が数でない")
        tv = {}
        if forced:
            continue  # 口座の強制の注文は知らせから作った行(出した時刻が無い)
        for c in _ORDER_TIME_COLS:
            if o[c] == "":
                continue
            v = _int_or_none(o[c])
            if v is None:
                _fail(out, "iii", lab, f"{c} {o[c]!r} が整数でない")
            else:
                tv[c] = v
        # 時刻の順: 土台が受けた = 出した ≤ 受け付けられた ≤ 閉じた、出した ≤ 取り消しを出した ≤ 取り消した
        if "sent_t_ns" in tv and tv.get("placed_t_ns") != tv["sent_t_ns"]:
            _fail(out, "iii", lab, f"出した時刻 {tv['sent_t_ns']} が土台が受けた時刻 {tv.get('placed_t_ns')} と違う(同じ時に出す)")
        sent = tv.get("sent_t_ns")
        for c in ("acked_t_ns", "cancel_sent_t_ns", "closed_t_ns", "cancel_rejected_t_ns", "state_unknown_t_ns"):
            if c in tv and (sent is None or tv[c] < sent):
                _fail(out, "iii", lab, f"{c} {tv[c]} が出した時刻 {sent} より前(または出していない)")
        if "acked_t_ns" in tv and "closed_t_ns" in tv and tv["closed_t_ns"] < tv["acked_t_ns"]:
            _fail(out, "iii", lab, f"閉じた時刻 {tv['closed_t_ns']} が受け付けられた時刻 {tv['acked_t_ns']} より前")
        for c, kinds in (("canceled_t_ns", ("cancel",)), ("venue_closed_t_ns", ("venue",)),
                         ("rejected_t_ns", ("reject", "venue", "new"))):
            if c in tv and (tv[c] != tv.get("closed_t_ns") or o["close_kind"] not in kinds):
                _fail(out, "iii", lab, f"{c} {tv[c]} が閉じた時刻 {tv.get('closed_t_ns')}・閉じ方 {o['close_kind']!r} と合わない")
        if "canceled_t_ns" in tv and tv.get("cancel_sent_t_ns", tv["canceled_t_ns"] + 1) > tv["canceled_t_ns"]:
            _fail(out, "iii", lab, "取り消した時刻の前に取り消しを出した時刻が無い")
        if not (("closed_t_ns" in tv) == ("closed_seq" in tv) == ("closed_venue_t_ns" in tv) == (o["close_kind"] != "")
                == (o["close_reason"] != "")):
            _fail(out, "iii", lab, "閉じた時刻・取引所での時刻・閉じた知らせの番号・閉じ方・理由のそろい方が合わない")
        for c, v in (("acked_venue_t_ns", "acked_t_ns"), ("closed_venue_t_ns", "closed_t_ns")):
            if (c in tv) != (v in tv) or (c in tv and tv[c] > tv[v]):
                _fail(out, "iii", lab, f"取引所での時刻 {c} {tv.get(c)} が戦略に届いた時刻 {v} {tv.get(v)} の後(または片方だけ)")
        if "closed_seq" in tv and tv["closed_seq"] < tv.get("placed_seq", 0):
            _fail(out, "iii", lab, f"閉じた知らせの番号 {tv['closed_seq']} が受けた時の番号 {tv.get('placed_seq')} より前")
        if o["qty_source"] == QTY_FROM_SIZING and o["exit_pending_at_send"] != "":
            _fail(out, "iii", lab, "量の計算の行に、出ていた決済の量が書かれている")
    _check_attached_forms(t, out)
    # 届いた順: 土台が受けた時の番号は表の順に減らない。約定の知らせの番号は (銘柄, 側) の中で一意で、その注文を
    # 受けた時の番号より後、知らせの番号の順に届いた時刻が減らない
    last: dict = {}
    placed_of = {}
    for k, o in enumerate(t["orders"]):
        if o["origin"] != ORIGIN_ROAD:
            continue
        g, v = (o["instrument"], o["range"]), _int_or_none(o["placed_seq"])
        placed_of[g + (o["order_id"],)] = v
        if v is None:
            _fail(out, "iii", _label("orders", k, o), f"受けた時の番号 {o['placed_seq']!r} が整数でない")
        elif v < last.get(g, 0):
            _fail(out, "iii", _label("orders", k, o), f"受けた時の番号 {v} が前の行の {last[g]} より小さい(表は受けた順)")
        else:
            last[g] = v
    notices: dict = {}
    for k, f in enumerate(t["fills"]):
        ns, nt = _int_or_none(f["notice_seq"]), _int_or_none(f["notice_t_ns"])
        if ns is None or nt is None:
            continue
        g = (f["instrument"], f["range"])
        lab = _label("fills", k, f)
        pv = placed_of.get(g + (f["order_id"],))
        if pv is not None and ns <= pv:
            _fail(out, "iii", lab, f"約定の知らせの番号 {ns} が注文を受けた時の番号 {pv} より後でない")
        if ns in notices.setdefault(g, {}):
            _fail(out, "iii", lab, f"約定の知らせの番号 {ns} が同じ銘柄・側の中で二度ある")
        notices[g][ns] = (nt, lab)
    for g, d in notices.items():
        prev = None
        for ns in sorted(d):
            nt, lab = d[ns]
            if prev is not None and nt < prev:
                _fail(out, "iii", lab, f"知らせの番号 {ns} の届いた時刻 {nt} が、前の番号の届いた時刻 {prev} より前")
            prev = nt if prev is None else max(prev, nt)
    for k, f in enumerate(t["fills"]):
        lab = _label("fills", k, f)
        if f["side"] not in ("buy", "sell"):
            _fail(out, "iii", lab, f"売買 {f['side']!r} が buy / sell でない")
        if f["liquidity"] not in ("maker", "taker"):
            _fail(out, "iii", lab, f"liquidity {f['liquidity']!r} が maker / taker でない")
        fr, fe, fc = f["fill_rule"], f["fill_exit_rule"], f["fill_case"]
        if fr == "":
            if fe != "" or fc != "":
                _fail(out, "iii", lab, f"約定の印 fill_rule が空なのに fill_exit_rule {fe!r}・fill_case {fc!r} が書かれている")
        elif fr not in CHECK_BAR_RULES:
            _fail(out, "iii", lab, f"約定の印 fill_rule {fr!r} が {CHECK_BAR_RULES} のどれでもない(tier の決まりなら空)")
        else:
            if fe not in tuple(CHECK_EXIT_BY_RANGE.values()):
                _fail(out, "iii", lab, f"約定の印 fill_exit_rule {fe!r} が {tuple(CHECK_EXIT_BY_RANGE.values())} のどれでもない")
            if fc not in CHECK_FILL_CASES or (fc == "entry_bar" and fe != "same_bar"):
                _fail(out, "iii", lab, f"約定の印 fill_case {fc!r} が {CHECK_FILL_CASES} のどれでもない(entry_bar は same_bar だけ)")
        vt, nt = _int_or_none(f["venue_t_ns"]), _int_or_none(f["notice_t_ns"])
        if (f["notice_t_ns"] == "") != (f["notice_seq"] == "") or (f["notice_seq"] and _int_or_none(f["notice_seq"]) is None):
            _fail(out, "iii", lab, "知らせの時刻と通し番号のそろい方が合わない")
        if nt is not None and vt is not None and nt < vt:
            _fail(out, "iii", lab, f"知らせが届いた時刻 {nt} が取引所での約定の時刻 {vt} より前")
    for k, p in enumerate(t["fx"]):
        if len(p["pair"]) != 6 or not p["pair"].isupper() or not p["pair"].isalpha():
            _fail(out, "iii", f"fx の {k} 行目", f"通貨の組 {p['pair']!r} が 6 文字の大文字でない")


def _check_attached_forms(t: dict, out: list) -> None:
    """(iii) 建てと一緒に出した決済の行(exit_kind = with_entry)の attached_to が、同じ (銘柄, 側) の、同じ時に受けた
    (placed_seq・placed_t_ns が同じ)逆の売買の place の指値の行を指すこと。ほかの行の attached_to は空。"""
    by_id = {(o["instrument"], o["range"], o["order_id"]): o for o in t["orders"]}
    for k, o in enumerate(t["orders"]):
        lab = _label("orders", k, o)
        att = o.get("attached_to", "")
        if o["exit_kind"] != EXIT_WITH_ENTRY:
            if att != "":
                _fail(out, "iii", lab, f"建てと一緒に出した決済の行(exit_kind = {EXIT_WITH_ENTRY})でないのに attached_to "
                                       f"{att!r} が書かれている")
            continue
        if o["order_type"] != "limit":
            _fail(out, "iii", lab, "建てと一緒に出した決済の行が指値でない")
        p = by_id.get((o["instrument"], o["range"], att))
        if p is None or p["origin"] != ORIGIN_ROAD:
            _fail(out, "iii", lab, f"attached_to {att!r} の建ての注文が同じ銘柄・側の注文の表に無い")
            continue
        if p["qty_source"] != QTY_FROM_SIZING or p["order_type"] != "limit" or p["exit_kind"] != "":
            _fail(out, "iii", lab, f"attached_to {att!r} の注文が place の指値(建て)でない")
        if p["placed_seq"] != o["placed_seq"] or p["placed_t_ns"] != o["placed_t_ns"]:
            _fail(out, "iii", lab, f"建てと決済を受けた時(番号 {p['placed_seq']}・{o['placed_seq']}、時刻 "
                                   f"{p['placed_t_ns']}・{o['placed_t_ns']})が同じでない(一緒に出したもの)")
        if p["signal_id"] != o["signal_id"]:
            _fail(out, "iii", lab, f"決済の合図の番号 {o['signal_id']!r} が建ての合図の番号 {p['signal_id']!r} と違う")
        if p["side"] in ("buy", "sell") and o["side"] != ("sell" if p["side"] == "buy" else "buy"):
            _fail(out, "iii", lab, f"決済の売買 {o['side']!r} が建ての売買 {p['side']!r} の逆でない")


def _num_or_none(v: str) -> float | None:
    try:
        return float(v) if v.strip() == v else None
    except ValueError:
        return None


def _int_or_none(v: str) -> int | None:
    try:
        return int(v) if v != "" and v.strip() == v else None
    except ValueError:
        return None


def _check_links(t: dict, out: list, groups: list | None) -> None:
    """(iii) 合図 → 注文 → 約定のつなぎ、合図の発生 ≤ 消失、fx の組が走らせの組の中か。"""
    if groups is not None:
        for k, p in enumerate(t["fx"]):
            if (p["instrument"], p["range"]) not in set(groups):
                _fail(out, "iii", f"fx の {k} 行目", f"銘柄 {p['instrument']}・側 {p['range']} が走らせの組 {groups} に無い"
                                                    f"(黙って捨てない)")
    sigs: dict = {}
    for k, s in enumerate(t["signals"]):
        key = (s["instrument"], s["range"], s["signal_id"])
        lab = _label("signals", k, s, "合図")
        if key in sigs:
            _fail(out, "iii", lab, "合図の番号が同じ銘柄・側の中で二度ある")
            continue
        if s["signal_id"] == NO_SIGNAL:
            _fail(out, "iii", lab, f"合図の番号に「{NO_SIGNAL}」が使われている")
        start = _int_or_none(s["start_t_ns"])
        if start is None:
            _fail(out, "iii", lab, f"発生の時刻 {s['start_t_ns']!r} が整数でない")
        if s["end_t_ns"] == "":
            if s["end_reason"] != DATA_END:
                _fail(out, "iii", lab, f"消失の時刻が空なのに理由が「{DATA_END}」でない: {s['end_reason']!r}")
        else:
            end = _int_or_none(s["end_t_ns"])
            if end is None:
                _fail(out, "iii", lab, f"消失の時刻 {s['end_t_ns']!r} が整数でない")
            elif start is not None and start > end:
                _fail(out, "iii", lab, f"発生の時刻 {start} が消失の時刻 {end} より後")
            if s["end_reason"] in ("", DATA_END):
                _fail(out, "iii", lab, f"消失した合図の理由が {s['end_reason']!r}")
        sigs[key] = start
    orders: dict = {}
    for k, o in enumerate(t["orders"]):
        key = (o["instrument"], o["range"], o["order_id"])
        lab = _label("orders", k, o, "注文")
        if key in orders:
            _fail(out, "iii", lab, "注文の番号が同じ銘柄・側の中で二度ある")
            continue
        orders[key] = o
        sid = o["signal_id"]
        if sid == NO_SIGNAL:
            continue
        skey = (o["instrument"], o["range"], sid)
        if skey not in sigs:
            _fail(out, "iii", lab, f"合図の番号 {sid!r} の合図が signals に無い(存在する合図か「{NO_SIGNAL}」が要る)")
            continue
        placed, start = _int_or_none(o["placed_t_ns"]), sigs[skey]
        if placed is None:
            _fail(out, "iii", lab, f"土台が受けた時刻 {o['placed_t_ns']!r} が整数でない")
        elif start is not None and placed < start:
            _fail(out, "iii", lab, f"注文を受けた時刻 {placed} が合図 {sid} の発生の時刻 {start} より前")
    for k, f in enumerate(t["fills"]):
        lab = _label("fills", k, f, "約定")
        o = orders.get((f["instrument"], f["range"], f["order_id"]))
        if o is None:
            _fail(out, "iii", lab, f"約定の注文 {f['order_id']!r} が orders に無い")
            continue
        if f["signal_id"] != o["signal_id"]:
            _fail(out, "iii", lab, f"約定の合図の番号 {f['signal_id']!r} が注文の合図の番号 {o['signal_id']!r} と違う")
        if f["signal_id"] != NO_SIGNAL and (f["instrument"], f["range"], f["signal_id"]) not in sigs:
            _fail(out, "iii", lab, f"約定の合図の番号 {f['signal_id']!r} の合図が signals に無い")


def _check_bars_tables(t: dict, bars: Sequence[Mapping], out: list, bar_priced: set | None, L: int) -> None:
    """(iv) 約定は check_bars(足で値段を付ける銘柄の maker の約定は、t_ns で閉じた足と比べる)、合図の発生・消失の時刻は
    足の長さの区切りとその時刻に閉じた足。L: 足の長さ(ns、走らせの記録から)。"""
    fl, idx, at_close = [], [], []
    for k, f in enumerate(t["fills"]):
        if bar_priced and f["instrument"] in bar_priced and f["liquidity"] == "maker":
            at_close.append(k)  # 足で約定させた指値: t_ns = 取引所での時刻 = 約定させた足が閉じた時刻(5 周目 (2-5))
            continue
        try:
            fl.append({"t_ns": int(f["t_ns"]), "px": float(f["px"])})
        except ValueError:
            fl.append({"t_ns": f["t_ns"], "px": f["px"]})
        idx.append(k)
    for r in check_bars(fl, bars, L):
        if isinstance(r["row"], int):
            k = idx[r["row"]]
            r = dict(r, row=_label("fills", k, t["fills"][k], "約定"))
        _fail(out, "iv", r["row"], r["reason"])
    by_start = {}
    for j, b in enumerate(bars):
        if isinstance(b, Mapping) and type(b.get("t_ns")) is int and _finite_number(b.get("high")) \
                and _finite_number(b.get("low")):
            by_start.setdefault(b["t_ns"], []).append((j, float(b["high"]), float(b["low"])))
    for k in at_close:
        f = t["fills"][k]
        lab = _label("fills", k, f, "約定")
        v = _int_or_none(f["t_ns"])
        try:
            px = float(f["px"])
        except ValueError:
            _fail(out, "iv", lab, f"約定の値段 {f['px']!r} が数でない")
            continue
        if v is None:
            _fail(out, "iv", lab, f"約定の時刻 {f['t_ns']!r} が整数でない")
            continue
        if v % L != 0:
            _fail(out, "iv", lab, f"足で約定させた指値の約定の時刻 {v} が{_grid_word(L)}(足が閉じた時刻)から {v % L} ns ずれている")
            continue
        hits = by_start.get(v - L, [])
        if len(hits) != 1:
            _fail(out, "iv", lab, f"足で約定させた指値の約定の時刻 {v}({_iso(v)})に閉じた足(始まり {_iso(v - L)})が "
                                  f"{len(hits)} 本(1 本でない)")
            continue
        j, hi, lo = hits[0]
        if not (lo <= px <= hi):
            _fail(out, "iv", lab, f"足で約定させた指値の約定の値段 {f['px']} が、約定させた足({_bar_name(j, v - L, L)})の"
                                  f"安値 {lo}〜高値 {hi} の外")
    starts = set()
    for b in bars:
        if isinstance(b, Mapping) and type(b.get("t_ns")) is int:
            starts.add(b["t_ns"])
    for k, s in enumerate(t["signals"]):
        lab = _label("signals", k, s, "合図")
        for col, what in (("start_t_ns", "発生"), ("end_t_ns", "消失")):
            if s[col] == "":
                continue
            v = _int_or_none(s[col])
            if v is None:
                _fail(out, "iv", lab, f"{what}の時刻 {s[col]!r} が整数でない")
                continue
            if v % L != 0:
                _fail(out, "iv", lab, f"{what}の時刻 {v} が{_grid_word(L)}から {v % L} ns ずれている")
                continue
            if v - L not in starts:
                _fail(out, "iv", lab, f"{what}の時刻 {v}({_iso(v)})に閉じた足(始まり {_iso(v - L)})が無い")


def _num(v: str):
    """記録した量の計算の値を数に(整数の書き方なら整数、ほかは浮動小数)。"""
    if v.strip() != v or not v:
        raise ValueError(v)
    try:
        return int(v)
    except ValueError:
        return float(v)


SIZING_COLS = ("margin_jpy", "use_ratio", "levels", "size_px", "size_px_source", "usdjpy", "usdjpy_t_ns", "qty_raw")
# 量の計算の定数は検査の側に書く(sizing・strategy の定数を読まない: 走らせの中で書き換えられても縛れるように)。
# L-743「**俺は20万って言ってたのに**」・L-746「**70%**」
CHECK_MARGIN_JPY = "200000"
CHECK_USE_RATIO = "0.7"


def _dsum(vals) -> Decimal:
    out = Decimal(0)
    for v in vals:
        out += Decimal(v)
    return out


def _flatten_expect(t: dict, o: Mapping, k: int) -> tuple[str, Decimal]:
    """決済の行 o(orders の k 行目)の (送る時点の建玉, 出ていた決済の注文のまだ約定していない量)。
    建玉: 同じ (銘柄, 側) の約定のうち、知らせが届いた通し番号 ≤ この注文の placed_seq のもので、帳簿のツールが出す建玉。
    出ていた決済の量: この行より前の決済の行で、閉じた知らせがこの通し番号までに届いておらず、まだ約定していない量
    (届いた知らせの約定を引く。買いが +)。"""
    seq = int(o["placed_seq"])
    g = (o["instrument"], o["range"])
    inp, by_order = [], {}
    for f in t["fills"]:
        if (f["instrument"], f["range"]) != g or f["notice_seq"] == "" or int(f["notice_seq"]) > seq:
            continue
        inp.append({"t_ns": int(f["t_ns"]), "side": f["side"], "qty": float(f["qty"]), "px": float(f["px"]),
                    "ccy": f["ccy"]})
        by_order.setdefault(f["order_id"], []).append(f["qty"])
    if inp:
        fx = [{"t_ns": int(p["t_ns"]), "pair": p["pair"], "rate": float(p["rate"])} for p in t["fx"]
              if (p["instrument"], p["range"]) == g]
        pos = book(inp, fx or None).fills[-1]["position_after"]
    else:
        pos = "0"
    pending = Decimal(0)
    for j, r in enumerate(t["orders"]):
        if j >= k or (r["instrument"], r["range"]) != g or r["qty_source"] != QTY_FROM_POSITION or r["sent_t_ns"] == "":
            continue
        if r["closed_seq"] != "" and int(r["closed_seq"]) <= seq:
            continue
        cap = Decimal(r["qty"])
        if r["exit_kind"] == EXIT_WITH_ENTRY:  # 建てと一緒に出した決済: 建ての約定の知らせの和(決済の量まで)が有効
            cap = min(cap, _dsum(by_order.get(r["attached_to"], [])))
        rest = cap - _dsum(by_order.get(r["order_id"], []))
        pending += rest if r["side"] == "buy" else -rest
    return pos, pending


def _check_sizes(t: dict, bars: Sequence[Mapping], out: list, L: int | None) -> None:
    """(v) 注文の量と、量の計算の値を外の記録と突き合わせる(モジュールの説明を参照)。L: 足の長さ(ns)。"""
    closes = {}
    for b in bars:
        if L is not None and isinstance(b, Mapping) and type(b.get("t_ns")) is int:
            closes[b["t_ns"] + L] = b.get("close")  # 足が閉じた時刻 -> 終値
    close_times = sorted(closes)
    fx_by = {}
    for p in t["fx"]:
        if p["pair"] == "USDJPY":
            v = _int_or_none(p["t_ns"])
            if v is not None:
                fx_by.setdefault((p["instrument"], p["range"]), []).append((v, p["rate"]))
    for v in fx_by.values():
        v.sort(key=lambda x: x[0])  # 同じ時刻は後の行(FxRates と同じ: 安定な並べ替えで後のものを最後に)
    fills_by = {}
    for f in t["fills"]:
        fills_by.setdefault((f["instrument"], f["range"], f["order_id"]), []).append(f)
    for k, o in enumerate(t["orders"]):
        lab = _label("orders", k, o)
        if o["origin"] != ORIGIN_ROAD:
            continue
        mine = fills_by.get((o["instrument"], o["range"], o["order_id"]), [])
        try:
            if o["qty_source"] == QTY_FROM_POSITION:
                filled = [c for c in SIZING_COLS if o[c] != ""]
                if filled:
                    _fail(out, "v", lab, f"量の出所が「建玉」の行に量の計算の列 {filled} が書かれている")
                pos, pending = _flatten_expect(t, o, k)
                net = Decimal(pos) + pending
                kind = o["exit_kind"]
                if kind == EXIT_WITH_ENTRY:
                    # 量 = 建ての注文の量。建てを出さなかった(量 0)なら決済も出さない(下の量が 0 の行の検査)
                    _check_with_entry_size(t, o, lab, pos, pending, out)
                    p = _entry_of(t, o)
                    raise _Next(p is not None and p["state"] == ZERO_QTY_STATE)
                if kind == EXIT_FLATTEN_CALL:
                    want_net = Decimal(0)  # 呼んだ記録の行: 注文は出していない(量 0)
                elif kind == EXIT_CLOSE and (Decimal(pos) == 0 or net == 0 or (net > 0) != (Decimal(pos) > 0)):
                    want_net = Decimal(0)  # close: 建玉 0、または出ている決済で足りている
                else:
                    want_net = net
                want = repr(float(abs(want_net)))
                if o["qty"] != want:
                    _fail(out, "v", lab, f"注文の量 {o['qty']!r} が、送る時点までに知らせの届いた約定の建玉 {pos} と出ていた"
                                         f"決済の量 {_dec_text(pending)} から決まる量 {want!r}(決済の種類 {kind})と違う")
                if kind == EXIT_FLATTEN and net == 0:
                    _fail(out, "v", lab, "flatten の成行なのに、送る時点の建玉と出ていた決済の量の和が 0")
                if o["position_at_send"] != pos:
                    _fail(out, "v", lab, f"送る時点の建玉 {o['position_at_send']!r} が帳簿のツールの建玉 {pos!r} と違う")
                if o["exit_pending_at_send"] != _dec_text(pending):
                    _fail(out, "v", lab, f"出ていた決済の量 {o['exit_pending_at_send']!r} が計算し直した "
                                         f"{_dec_text(pending)!r} と違う")
                if want_net != 0 and o["side"] != ("sell" if want_net > 0 else "buy"):
                    _fail(out, "v", lab, f"決済の売買 {o['side']!r} が建玉 {pos} の逆でない")
                zero = want_net == 0
            elif o["qty_source"] == QTY_FROM_SIZING:
                if o["margin_jpy"] != CHECK_MARGIN_JPY or o["use_ratio"] != CHECK_USE_RATIO:
                    _fail(out, "v", lab, f"証拠金 {o['margin_jpy']!r}・比率 {o['use_ratio']!r} が {CHECK_MARGIN_JPY} 円・"
                                         f"{CHECK_USE_RATIO} でない(L-743・L-746)")
                usd = None if o["usdjpy"] == "" else _num(o["usdjpy"])
                raw, qty = size_detail(margin_jpy=_num(o["margin_jpy"]), use_ratio=_num(o["use_ratio"]),
                                       levels=int(o["levels"]), price=_num(o["size_px"]), quote_ccy=o["quote_ccy"],
                                       usdjpy_at_entry=usd)
                if o["qty"] != repr(qty):
                    _fail(out, "v", lab, f"注文の量 {o['qty']!r} が、記録した量の計算の値から計算し直した量 {repr(qty)!r} と違う")
                if o["qty_raw"] != str(raw):
                    _fail(out, "v", lab, f"切り捨て前の量 {o['qty_raw']!r} が計算し直した値 {str(raw)!r} と違う")
                _check_size_px(o, lab, close_times, closes, out)
                pos, _ = _flatten_expect(t, o, k)
                if o["position_at_send"] != pos:
                    _fail(out, "v", lab, f"受けた時点の建玉 {o['position_at_send']!r} が、それまでに知らせの届いた約定の"
                                         f"帳簿のツールの建玉 {pos!r} と違う")
                _check_usdjpy(o, lab, fx_by.get((o["instrument"], o["range"]), []), out)
                zero = qty == 0
            else:
                continue  # (iii) が落とす
        except _Next as nx:
            zero = nx.zero
        except (ValueError, KeyError, SizingError, LedgerError, ArithmeticError) as exc:
            _fail(out, "v", lab, f"量を計算し直せない: {exc}")
            continue
        if zero:
            if o["state"] != ZERO_QTY_STATE or o["sent_t_ns"] != "":
                _fail(out, "v", lab, f"量が 0 の行は状態「{ZERO_QTY_STATE}」で出していない(出した時刻が空)はず: "
                                     f"状態 {o['state']!r}・出した時刻 {o['sent_t_ns']!r}")
        elif o["state"] == ZERO_QTY_STATE or o["sent_t_ns"] == "":
            _fail(out, "v", lab, f"量が 0 でない行が出されていない: 状態 {o['state']!r}・出した時刻 {o['sent_t_ns']!r}")
        # 約定の和: 知らせの届いた約定の和 = 約定した量、全部の約定の和 ≤ 注文の量
        try:
            seen = _dsum(f["qty"] for f in mine if f["notice_seq"] != "")
            total = _dsum(f["qty"] for f in mine)
            if seen != Decimal(o["filled_qty"]):
                _fail(out, "v", lab, f"約定した量 {o['filled_qty']!r} が、知らせの届いた約定の和 {_dec_text(seen)} と違う")
            if o["qty"] != "" and total > Decimal(o["qty"]):
                _fail(out, "v", lab, f"約定の和 {_dec_text(total)} が注文の量 {o['qty']} を超える")
        except ArithmeticError:
            _fail(out, "v", lab, "約定した量・約定の量が数として読めない")


class _Next(Exception):
    """(v) の with_entry の行: 量の検査を終えて、量が 0 の行の検査へ進む。"""

    def __init__(self, zero: bool) -> None:
        super().__init__()
        self.zero = zero


def _entry_of(t: dict, o: Mapping) -> Mapping | None:
    for p in t["orders"]:
        if (p["instrument"], p["range"], p["order_id"]) == (o["instrument"], o["range"], o["attached_to"]):
            return p
    return None


def _check_with_entry_size(t: dict, o: Mapping, lab: str, pos: str, pending: Decimal, out: list) -> None:
    """(v) 建てと一緒に出した決済の行: 量 = 建ての注文の量、量の計算の列は空、送る時点の建玉・出ていた決済の量は
    知らせの届いた約定から計算し直した値。"""
    filled = [c for c in SIZING_COLS if o[c] != ""]
    if filled:
        _fail(out, "v", lab, f"量の出所が「建玉」の行に量の計算の列 {filled} が書かれている")
    p = _entry_of(t, o)
    if p is None:
        return  # (iii) が落とす
    if o["qty"] != p["qty"]:
        _fail(out, "v", lab, f"建てと一緒に出した決済の量 {o['qty']!r} が建ての注文の量 {p['qty']!r} と違う")
    if o["position_at_send"] != pos:
        _fail(out, "v", lab, f"送る時点の建玉 {o['position_at_send']!r} が帳簿のツールの建玉 {pos!r} と違う")
    if o["exit_pending_at_send"] != _dec_text(pending):
        _fail(out, "v", lab, f"出ていた決済の量 {o['exit_pending_at_send']!r} が計算し直した {_dec_text(pending)!r} と違う")


def _check_size_px(o: Mapping, lab: str, close_times: list, closes: dict, out: list) -> None:
    """量の計算の値段を、指値なら指値の値段と、直近の足の終値なら土台が受けた時刻以前に閉じた最後の足の終値と比べる。"""
    src = o["size_px_source"]
    if src == "指値":
        if o["order_type"] != "limit" or o["limit_px"] != o["size_px"]:
            _fail(out, "v", lab, f"量の計算の値段 {o['size_px']!r}(出所 指値)が指値の値段 {o['limit_px']!r} と違う")
    elif src == "直近の足の終値":
        if o["order_type"] != "market":
            _fail(out, "v", lab, "出所が直近の足の終値なのに成行でない")
        placed = int(o["placed_t_ns"])
        i = bisect.bisect_right(close_times, placed) - 1
        if i < 0:
            _fail(out, "v", lab, f"土台が受けた時刻 {placed}({_iso(placed)})以前に閉じた足が無い")
            return
        c = closes[close_times[i]]
        if not _finite_number(c):
            _fail(out, "v", lab, "足に終値(close)が無いので、量の計算の値段を突き合わせられない")
        elif float(o["size_px"]) != float(c):
            _fail(out, "v", lab, f"量の計算の値段 {o['size_px']!r} が、土台が受けた時刻以前に閉じた最後の足"
                                 f"(閉じた時刻 {_iso(close_times[i])})の終値 {c!r} と違う")
    elif src not in ("直近の約定の値段", "直近の板の仲値"):
        _fail(out, "v", lab, f"量の計算の値段の出所 {src!r} が決まった値でない")


def _check_usdjpy(o: Mapping, lab: str, rates: list, out: list) -> None:
    """注文の USDJPY を、fx の表の土台が受けた時刻以前の最後の相場と比べる(円建ては空)。"""
    if o["quote_ccy"] == "JPY":
        if o["usdjpy"] != "" or o["usdjpy_t_ns"] != "":
            _fail(out, "v", lab, "円建ての注文に USDJPY が書かれている")
        return
    placed = int(o["placed_t_ns"])
    last = None
    for tt, r in rates:
        if tt <= placed:
            last = (tt, r)
    if last is None:
        _fail(out, "v", lab, f"fx に土台が受けた時刻 {placed} 以前の USDJPY が無い")
    elif o["usdjpy_t_ns"] != str(last[0]) or float(o["usdjpy"] or "nan") != float(last[1]):
        _fail(out, "v", lab, f"注文の USDJPY {o['usdjpy']!r}(時刻 {o['usdjpy_t_ns']!r})が、fx の土台が受けた時刻以前の"
                             f"最後の相場 {last[1]!r}(時刻 {last[0]})と違う")


_PFILL_COLS = ("order_id", "t_ns", "venue_t_ns", "side", "qty", "px", "fee", "liquidity")


def _check_pipeline(t: dict, run: dict, out: list) -> None:
    """(vi) 道の約定・注文を、同じ走らせの置き場の pipeline の書き出し(fills.json・orders.json)と突き合わせる。"""
    def ptext(c, v):
        return text(float(v)) if c in ("qty", "px", "fee") else text(v)
    groups = sorted({(r["instrument"], r["range"]) for r in t["fills"]} |
                    {(r.get("instrument"), r.get("range")) for r in run["pfills"] if isinstance(r, dict)})
    for g in groups:
        mine = [f for f in t["fills"] if (f["instrument"], f["range"]) == g]
        theirs = [f for f in run["pfills"] if isinstance(f, dict) and (f.get("instrument"), f.get("range")) == g]
        if len(mine) != len(theirs):
            _fail(out, "vi", f"fills(銘柄 {g[0]}・側 {g[1]})",
                  f"約定の数 {len(mine)} が pipeline の fills.json の約定の数 {len(theirs)} と違う")
        for k in range(min(len(mine), len(theirs))):
            for c in _PFILL_COLS:
                try:
                    want = ptext(c, theirs[k][c])
                except (KeyError, TypeError, ValueError):
                    want = None
                if mine[k][c] != want:
                    _fail(out, "vi", _label("fills", t["fills"].index(mine[k]), mine[k]),
                          f"{c} {mine[k][c]!r} が pipeline の fills.json の {want!r} と違う")
    sent = {(o["instrument"], o["range"], o["order_id"]): o for o in t["orders"] if o["sent_t_ns"] != ""}
    seen = set()
    for p in run["porders"]:
        if not isinstance(p, dict):
            continue
        key = (p.get("instrument"), p.get("range"), p.get("id"))
        seen.add(key)
        o = sent.get(key)
        if o is None:
            _fail(out, "vi", f"orders.json の注文 {key[2]!r}(銘柄 {key[0]}・側 {key[1]})", "道の注文の表に出した行が無い")
            continue
        lab = _label("orders", t["orders"].index(o), o)
        try:
            pq, ps, pt = repr(float(p["qty"])), p["side"], p["type"]
        except (KeyError, TypeError, ValueError):
            _fail(out, "vi", lab, "pipeline の orders.json の行が読めない")
            continue
        if o["qty"] != pq:
            _fail(out, "vi", lab, f"注文の量 {o['qty']!r} が pipeline の orders.json の量 {pq!r}(実際に送った量)と違う")
        if o["side"] != ps or o["order_type"] != pt:
            _fail(out, "vi", lab, f"売買・種類 {o['side']!r}・{o['order_type']!r} が orders.json の {ps!r}・{pt!r} と違う")
    for key, o in sent.items():
        if key not in seen and o["origin"] == ORIGIN_ROAD:
            _fail(out, "vi", _label("orders", t["orders"].index(o), o), "出した注文が pipeline の orders.json に無い")


# 約定の決まり(L-769・L-770)の検査の側の定数(取引所の模型・pipeline の定数を読まない: 走らせの中で書き換えられても縛れるように)
CHECK_BAR_RULES = ("range_open",)
# L-769「**指値決済の良い側はその足内で指値があれば通り、悪い側は次の足内から**」(良い側 = 楽観側はリードの対応)
CHECK_EXIT_BY_RANGE = {"optimistic": "same_bar", "pessimistic": "next_bar"}
CHECK_FILL_CASES = ("range", "open", "entry_bar")


def _floor_px(limit_px: str, tick: float) -> str:
    """送るはずの指値の値段を、戦略が計算した値段 limit_px と走らせが宣言した銘柄の刻み tick から検査の側で計算し直す:
    刻みに切り捨てた値段(L-783「間違えそうやから小数点以下は切り捨ててください」。買いも売りも切り捨て。最短の 10 進の
    文字列で計算する)。"""
    d, tk = Decimal(repr(float(limit_px))), Decimal(repr(float(tick)))
    return repr(float((d / tk).to_integral_value(rounding=ROUND_FLOOR) * tk))


def _bar_hits(lim: float, side: str, hi: float, lo: float) -> str:
    """bar_rule range_open で、指値 lim がその足でどう当たるか: "range"(範囲の内、指値の値段)/ "open"(約定する向きに外、
    始値)/ ""(約定しない)。"""
    if lo <= lim <= hi:
        return "range"
    if (lim > hi) if side == "buy" else (lim < lo):
        return "open"
    return ""


def _check_fill_rule(t: dict, bars: Sequence[Mapping], out: list, run: dict, L: int | None) -> None:
    """(vii) 約定の決まりと指値の値段(SCHEMA の fill_rules。モジュールの説明を参照)。"""
    fill = run["fill"]
    br = {r: fill[r].get("bar_rule") for r in RANGES}
    ae = {r: fill[r].get("attached_exit") for r in RANGES}
    # 両側の組み合わせを掛け直す(pipeline の確かめと同じものを、記録から)
    if any(v is not None for v in br.values()):
        if br["optimistic"] != br["pessimistic"]:
            _fail(out, "vii", "record.json", f"両側の bar_rule が違う(楽観側 {br['optimistic']!r}・悲観側 {br['pessimistic']!r})。"
                                             f"建ての当て方は両側で同じ")
        for r in RANGES:
            if br[r] is not None and br[r] not in CHECK_BAR_RULES:
                _fail(out, "vii", "record.json", f"{r} の bar_rule {br[r]!r} がこの検査の知る決まり {CHECK_BAR_RULES} でない")
            if ae[r] != CHECK_EXIT_BY_RANGE[r]:
                _fail(out, "vii", "record.json", f"{r} の attached_exit が {ae[r]!r}。楽観側 = same_bar・悲観側 = next_bar "
                                                 f"(L-769「指値決済の良い側はその足内で指値があれば通り、悪い側は次の足内から」)")
    # 指値の値段: 送った値段(sent_limit_px)= 計算した値段(limit_px)を宣言の刻みに切り捨てた値段(L-783。どの側も)
    for k, o in enumerate(t["orders"]):
        if o["origin"] != ORIGIN_ROAD or o["sent_limit_px"] == "":
            continue
        lab = _label("orders", k, o)
        tick = run["ticks"].get(o["instrument"])
        try:
            want = _floor_px(o["limit_px"], tick)  # type: ignore[arg-type]
        except (ValueError, TypeError, ArithmeticError):
            _fail(out, "vii", lab, f"指値の値段 {o['limit_px']!r} を銘柄の刻み {tick!r} に切り捨てられない")
            continue
        if o["sent_limit_px"] != want:
            _fail(out, "vii", lab, f"送った指値の値段 {o['sent_limit_px']!r} が、計算した値段 {o['limit_px']!r} を刻み {tick!r} に"
                                   f"切り捨てた値 {want!r} と違う(L-783)")
    # 約定の行の印と、その側の宣言(印があるのに宣言に bar_rule が無いものも落とす)・liquidity
    for k, f in enumerate(t["fills"]):
        if f["fill_rule"] == "":
            continue
        lab = _label("fills", k, f, "約定")
        spec = fill.get(f["range"], {})
        if (spec.get("bar_rule"), spec.get("attached_exit")) != (f["fill_rule"], f["fill_exit_rule"]):
            _fail(out, "vii", lab, f"約定の印(fill_rule {f['fill_rule']!r}・fill_exit_rule {f['fill_exit_rule']!r})が、この側 "
                                   f"{f['range']} の走らせの宣言(bar_rule {spec.get('bar_rule')!r}・attached_exit "
                                   f"{spec.get('attached_exit')!r})と違う")
        if f["liquidity"] != "maker":
            _fail(out, "vii", lab, f"bar_rule の約定の liquidity {f['liquidity']!r} が maker でない(範囲の内 = 待っていた指値。始値の"
                                   f"約定も maker: オーナーの決定 L-783)")
    rules = {r: fill[r] for r in RANGES if br[r] is not None}
    if not rules:
        return
    # 注文の遅れ: bar_rule の側では、取引所が受け付けた時刻 = 土台が置いた時刻(足が閉じた時刻)
    for k, o in enumerate(t["orders"]):
        if o["origin"] == ORIGIN_ROAD and o["range"] in rules and o["acked_venue_t_ns"] != "" \
                and o["acked_venue_t_ns"] != o["placed_t_ns"]:
            _fail(out, "vii", _label("orders", k, o), f"取引所が受け付けた時刻 {o['acked_venue_t_ns']} が置いた時刻 "
                                                      f"{o['placed_t_ns']} と違う(bar_rule は足が閉じた時刻に置いた指値を次の"
                                                      f"足から当てる決まりで、注文の遅れを前提にしない)")
    if L is None:
        return  # 足の長さが決まらない((iv) で失敗にした)
    by_start: dict = {}
    for j, b in enumerate(bars):
        if isinstance(b, Mapping) and type(b.get("t_ns")) is int and _finite_number(b.get("high")) \
                and _finite_number(b.get("low")):
            op = float(b["open"]) if _finite_number(b.get("open")) else None
            by_start.setdefault(b["t_ns"], []).append((j, float(b["high"]), float(b["low"]), op))
    starts = sorted(by_start)
    fills_of: dict = {}
    for k, f in enumerate(t["fills"]):
        fills_of.setdefault((f["instrument"], f["range"], f["order_id"]), []).append((k, f))
    for k_o, o in enumerate(t["orders"]):
        inst, rng, oid = o["instrument"], o["range"], o["order_id"]
        spec = rules.get(rng)
        if spec is None or inst not in run["bar_priced"] or o["origin"] != ORIGIN_ROAD or o["order_type"] != "limit" \
                or o["acked_venue_t_ns"] == "":
            continue
        olab = _label("orders", k_o, o)
        try:
            lim = float(_floor_px(o["limit_px"], run["ticks"].get(inst)))  # type: ignore[arg-type]
        except (ValueError, TypeError, ArithmeticError):
            continue  # 上で落とした
        acked = _int_or_none(o["acked_venue_t_ns"])
        if acked is None:
            continue  # (iii) で落とした
        side = o["side"]  # 範囲の内・外の判定と約定の値段は送った値段(刻みに切り捨てた値段)で
        fl = fills_of.get((inst, rng, oid), [])
        with_entry = o["exit_kind"] == EXIT_WITH_ENTRY
        parent_t = None
        if with_entry:
            pf = fills_of.get((inst, rng, o["attached_to"]), [])
            if not pf:
                if fl:
                    _fail(out, "vii", _label("fills", fl[0][0], fl[0][1], "約定"),
                          f"建てと一緒に出した決済 {oid} が約定しているのに、建て {o['attached_to']} の約定が無い")
                continue  # 建てが約定していない決済には有効だった足が無い
            parent_t = _int_or_none(pf[0][1]["t_ns"])
            if parent_t is None:
                continue  # (iii) が落とす
        same_bar = with_entry and spec.get("attached_exit") == "same_bar" and parent_t >= acked  # type: ignore[operator]
        for n, (k, f) in enumerate(fl):
            lab = _label("fills", k, f, "約定")
            v, px = int(f["t_ns"]), float(f["px"])
            if f["fill_rule"] != spec.get("bar_rule"):
                _fail(out, "vii", lab, f"bar_rule の側の指値の約定なのに、約定の印 fill_rule が {f['fill_rule']!r}"
                                       f"(この側の決まり {spec.get('bar_rule')!r} で当てた印でない)")
            hits = by_start.get(v - L, [])
            if len(hits) != 1:
                continue  # (iv) が落とす
            j, hi, lo, op = hits[0]
            name = _bar_name(j, v - L, L)
            if with_entry and v == parent_t:
                want_case = "entry_bar"
                if spec.get("attached_exit") != "same_bar":
                    _fail(out, "vii", lab, f"決済が建てと同じ足({name})で約定している。建てと同じ足の決済の約定は楽観側"
                                           f"(attached_exit = same_bar)にしか無い(この側 {rng} は {spec.get('attached_exit')!r})")
                elif not (lo <= lim <= hi) or px != lim:
                    _fail(out, "vii", lab, f"建てと同じ足の決済の約定は、決済の値段 {lim!r} がその足({name})の安値 {lo}〜"
                                           f"高値 {hi} の内で値段 = 決済の値段のときだけ(約定の値段 {px!r})")
            else:
                how = _bar_hits(lim, side, hi, lo)
                want_case = how
                if how == "":
                    _fail(out, "vii", lab, f"指値 {lim!r}({side})が約定させた足({name})の安値 {lo}〜高値 {hi} の約定しない"
                                           f"向きの外なのに約定している")
                elif how == "range" and px != lim:
                    _fail(out, "vii", lab, f"指値 {lim!r} が約定させた足({name})の範囲の内なのに、約定の値段 {px!r} が指値の"
                                           f"値段でない")
                elif how == "open":
                    if op is None:
                        _fail(out, "vii", lab, f"指値 {lim!r} が約定させた足({name})の範囲の約定する向きの外で、始値で約定する"
                                               f"はずだが、足に始値(open)が無いので確かめられない")
                    elif px != op:
                        _fail(out, "vii", lab, f"指値 {lim!r} が約定させた足({name})の範囲の約定する向きの外なのに、約定の"
                                               f"値段 {px!r} がその足の始値 {op!r} でない")
            if want_case and f["fill_case"] != want_case:
                _fail(out, "vii", lab, f"約定の印 fill_case {f['fill_case']!r} が、決まりから決まる当たり方 {want_case!r} と違う")
        # 有効だった足で約定していたはずの足が無いか(約定した注文は最初の約定の足より前、約定していない注文は閉じるか
        # データの終わりまで)
        begin = acked if parent_t is None else max(acked, parent_t)
        c = None
        if fl:
            v = int(fl[0][1]["t_ns"])
            if with_entry and v == parent_t:
                continue  # 建てと同じ足(上で見た)
            if v - L < begin:
                _fail(out, "vii", _label("fills", fl[0][0], fl[0][1], "約定"),
                      f"約定させた足(始まり {_iso(v - L)})が、当て始める足(始まり {_iso(begin)} 以後)より前")
                continue
            upto, what = v - L, "約定させた足より前の"
        else:
            c = _int_or_none(o["closed_venue_t_ns"])
            # 同じ時刻では足が取引所に届いてから注文・取り消しが届く(core の順): 取り消しの時刻に閉じた足は有効だった。
            # 取引所が自分で閉じたもの(reduce_only など)は、閉じた時刻に閉じた足を当てた結果なので含めない
            if c is None:
                upto = None
            elif o["close_kind"] == "cancel":
                upto = c - L + 1
            else:
                upto = c - L
            what = "有効だった"
        # 建ての足で取引所が自分で閉じた決済(有効になったところで self_trade で閉じたなど)は、その足を当てた結果なので見ない
        if same_bar and not (not fl and c is not None and o["close_kind"] != "cancel" and c <= parent_t):  # type: ignore[operator]
            same = by_start.get(parent_t - L, [])  # type: ignore[operator]
            if len(same) == 1 and same[0][2] <= lim <= same[0][1]:
                _fail(out, "vii", olab, f"楽観側の決済の値段 {lim!r} が建てが約定した足({_bar_name(same[0][0], parent_t - L, L)})"  # type: ignore[operator]
                                        f"の範囲の内なのに、その足で約定していない")
                continue
        hi_i = len(starts) if upto is None else bisect.bisect_left(starts, upto)
        for s0 in starts[bisect.bisect_left(starts, begin):hi_i]:
            b = by_start[s0]
            if len(b) == 1 and _bar_hits(lim, side, b[0][1], b[0][2]):
                _fail(out, "vii", olab, f"指値 {lim!r}({side})は、{what}足({_bar_name(b[0][0], s0, L)})で約定していたはず"
                                        f"なのに、その足で約定していない")
                break


def check_tables(store_dir: str, bars: Sequence[Mapping]) -> CheckResult:
    """表の形の置き場 1 つに (i)〜(vii) を当てる(モジュールの説明を参照)。"""
    out: list = []
    try:
        run = _read_run(store_dir, out)
        t = _read_all(store_dir, out)
        if t is None:
            return CheckResult(out)  # 表がそろわなければ、ほかの検査はしない
        _check_forms(t, out)
        _check_derived(t, out, run)
        _check_links(t, out, None if run is None else run["groups"])
        # 足の長さは走らせの記録から(読めなければ足のファイルから)。表に何も無ければ足は見ないので求めない
        L = _bar_len(run, bars, out) if (t["signals"] or t["orders"] or t["fills"]) else None
        if L is not None:
            _check_bars_tables(t, bars, out, None if run is None else run["bar_priced"], L)
        _check_sizes(t, bars, out, L)
        if run is not None:
            _check_pipeline(t, run, out)
            _check_fill_rule(t, bars, out, run, L)
    except Exception as exc:  # 想定外の壊れ方。英語の文を出さずに失敗として止める(O-1)
        _fail(out, "i", store_dir, f"検査の途中で想定していない壊れ方に当たった(例外の種類 {type(exc).__name__})")
    return CheckResult(out)
