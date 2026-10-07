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
    - 約定の時刻 t を含む 1 分足(始まり s ≤ t < s + 60 秒)があるか(無ければ失敗)
    - 当たる足が 2 本以上なら失敗(足が重なっている)
    - 当たる足の始まりが分の区切り(60 秒の倍数の ns)にそろうか(そろわなければ失敗)
    - 約定の値段がその足の安値以上・高値以下か(外なら失敗)
    足は引数で受ける: 1 本 = {"t_ns": 足の始まり(ns), "high": 数, "low": 数}(ほかの鍵は見ない)。

置き場の形(この段で決めたもの。道につなぐ段で変えるときは `write_store` / `read_store` の 2 つだけを直す):
- `road_fills.json`: {"fills": [約定の行 ...], "fx": [{"t_ns", "pair", "rate"} ...]}  約定の行は `ledger` の入力の形
- `road_summary.json`: 帳簿のツールのまとめ(`ledger.SUMMARY_KEYS`: fill_count・closed_trades・pnl_jpy・open_trades・
  trades。trades の行は `ledger.TRADE_KEYS`)

表の形の置き場(道の走らせの `road/`。RECORD_FORM_L766.md §2・§4、委任文 DELEGATION_record_form.md 4.)には
`check_tables` が次を当てる。失敗した行は {"check": "i"〜"v", "row": どの表のどの行か, "reason": 日本語}。
(i)  表と列が SCHEMA どおりそろっているか: SCHEMA.json がこのコードの SCHEMA と同じ、表のファイルが全部あり、
     列の名前がその表の SCHEMA の列と同じ順で同じ(欠けたら失敗)。
(ii) 生の表 `fills`・`fx` から帳簿のツールで `ledger_fills`・`trades`・`summary` を作り直し(`tables.derive`。書き出しと
     同じ関数)、行の数・1 欄でも違えば失敗(使った USDJPY の値と相場の時刻の欄も含む)。summary の (銘柄, 側) の組
     (groups)は、置き場が走らせの置き場の road/ なら走らせの記録(../record.json)の銘柄 × 側と同じであること。
(iii) つなぎ: どの約定にも注文があり、約定の合図の番号 = その注文の合図の番号。どの注文にも存在する合図か「無し」が
     ある。合図のある注文は合図の発生の後に出ている(土台が受けた時刻 ≥ 発生の時刻)。どの合図も発生 ≤ 消失、
     消失の時刻が空なら理由は「データの終わり」。番号は (銘柄, 側) の中で一意。
(iv) 足の検査: 約定は (b) と同じ(その分の 1 分足・分の区切り・安値以上高値以下)。合図の発生・消失の時刻は、
     分の区切り(60 秒の倍数の ns)で、その時刻に閉じた 1 分足(始まり = 時刻 − 60 秒)があること
     (道は 1 分足で回し、戦略は足が閉じた時刻に足を見て合図を出す)。
     **足の遅れ(feed の遅延)が 0 でない走らせでは、合図の時刻が足の閉じた時刻より遅れて分の区切りから外れるので、
     この検査に必ず落ちる**(2 周目 (e): 今のまま。`tests/road/test_road_record.py` の場面で確かめている)。
(v)  注文の量: 出所が土台の注文のうち、量の出所が「量の計算」(place)の行は、記録した量の計算の値(証拠金・比率・
     段数・その時の値段・値段の通貨・USDJPY)から `size_per_level` で計算し直した量 = 注文の量(切り捨て前の量も同じ)。
     「建玉」(flatten)の行は、注文を受けた時刻以前の約定(この注文より前に出した注文の約定)までで帳簿のツールが出す
     建玉の絶対値 = 注文の量、送る時点の建玉の列 = その建玉、売買は建玉の逆、量の計算の列は空(2 周目 (d))。
     約定の知らせが戦略に届く前に決済を出す走らせ(知らせの遅れがある)では、土台の建玉と帳簿の建玉がずれてこの検査に落ちる。量が 0 の行は状態「量が 0 で出さない」で
     出していない(出した時刻が空)、量が 0 でない行は状態がそれでない。

ここで出す文は全部日本語(O-1)。下の層の例外の英語の文は出さない。
"""
from __future__ import annotations

import bisect
import json
import math
import os
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from .ledger import SUMMARY_KEYS, TRADE_KEYS, LedgerError, book
from .sizing import SizingError, size_detail
from .strategy import DATA_END, NO_SIGNAL, ORIGIN_FORCED, ORIGIN_ROAD, ZERO_QTY_STATE
from .strategy import QTY_FROM_POSITION, QTY_FROM_SIZING
from .tables import (CSV_TABLES, RANGES, ROAD_DIR, SCHEMA, SCHEMA_FILE, SUMMARY_TABLE, TableError, columns, derive,
                     groups_of, is_table_store, read_csv, read_json)

FILLS_FILE = "road_fills.json"
SUMMARY_FILE = "road_summary.json"
MINUTE_NS = 60_000_000_000


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


def check_bars(fills: Sequence[Mapping], bars: Sequence[Mapping]) -> list:
    """(b) 約定ごとに、その分の 1 分足・足の始まりの分の区切り・値段が安値以上高値以下かを見る。"""
    out = []
    rows = []
    for j, b in enumerate(bars):
        try:
            s, hi, lo = b["t_ns"], b["high"], b["low"]
        except (KeyError, TypeError):
            out.append({"check": "b", "row": f"足 {j}", "reason": "足に t_ns / high / low が無い"})
            continue
        if type(s) is not int:
            out.append({"check": "b", "row": f"足 {j}", "reason": f"足の t_ns が ns の整数でない: {s!r}"})
            continue
        bad = [n for n, v in (("high", hi), ("low", lo)) if not _finite_number(v)]
        if bad:
            out.append({"check": "b", "row": f"足 {j}", "reason": f"足の {'・'.join(bad)} が有限の数でない"})
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
        # 始まり s が t - 60 秒 < s <= t の足が、t を含む足
        lo_i = bisect.bisect_right(starts, t - MINUTE_NS)
        hi_i = bisect.bisect_right(starts, t)
        hits = rows[lo_i:hi_i]
        if not hits:
            out.append({"check": "b", "row": i, "reason": f"約定の時刻 {t} を含む 1 分足が無い"})
            continue
        if len(hits) > 1:
            out.append({"check": "b", "row": i,
                        "reason": f"約定の時刻 {t} を含む足が {len(hits)} 本ある(始まり {[h[0] for h in hits]})"})
            continue
        s, j, hi, lo = hits[0]
        if s % MINUTE_NS != 0:
            out.append({"check": "b", "row": i,
                        "reason": f"約定の時刻 {t} が属する足(足 {j})の始まり {s} が分の区切りから "
                                  f"{s % MINUTE_NS} ns ずれている"})
            continue
        if not (lo <= float(px) <= hi):
            out.append({"check": "b", "row": i,
                        "reason": f"約定の値段 {px} がその分の足(足 {j})の安値 {lo}〜高値 {hi} の外"})
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


def _run_groups(store_dir: str) -> list | None:
    """置き場が道の走らせの置き場の road/ なら、走らせの記録(../record.json)の銘柄 × 側。読めなければ None。"""
    d = os.path.normpath(store_dir)
    if os.path.basename(d) != ROAD_DIR:
        return None
    path = os.path.join(os.path.dirname(d), "record.json")
    if not os.path.isfile(path):
        return None
    try:
        rec = read_json(path, "走らせの記録")
        names = [i["name"] for i in rec["config"]["instruments"]]
    except (TableError, KeyError, TypeError):
        return None
    return sorted((n, r) for n in names for r in RANGES)


def _check_derived(t: dict, out: list, store_dir: str = "") -> None:
    """(ii) 生の表から作り直して突き合わせる。(銘柄, 側) の組は、走らせの記録があればその銘柄 × 側、
    無ければ summary の groups と生の表に出てくる組を合わせたもの(summary の groups は走らせの記録と突き合わせる)。"""
    w = t[SUMMARY_TABLE]
    wg = w.get("groups") if isinstance(w, dict) else None
    written_groups = set()
    if isinstance(wg, list) and all(isinstance(g, list) and len(g) == 2 and all(type(x) is str for x in g) for g in wg):
        written_groups = {tuple(g) for g in wg}
    else:
        _fail(out, "ii", SUMMARY_TABLE, "summary の groups が [銘柄, 側] の列でない")
    run = _run_groups(store_dir)
    groups = set(groups_of(t["signals"], t["orders"], t["fills"]))
    if run is not None:
        if sorted(written_groups) != run:
            _fail(out, "ii", SUMMARY_TABLE, f"summary の groups {sorted(written_groups)} が走らせの記録(record.json)の"
                                            f"銘柄 × 側 {run} と違う")
        groups |= set(run)
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


def _int_or_none(v: str) -> int | None:
    try:
        return int(v) if v != "" and v.strip() == v else None
    except ValueError:
        return None


def _check_links(t: dict, out: list) -> None:
    """(iii) 合図 → 注文 → 約定のつなぎ、合図の発生 ≤ 消失。"""
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


def _check_bars_tables(t: dict, bars: Sequence[Mapping], out: list) -> None:
    """(iv) 約定は check_bars、合図の発生・消失の時刻は分の区切りとその時刻に閉じた足。"""
    fl = []
    for k, f in enumerate(t["fills"]):
        try:
            fl.append({"t_ns": int(f["t_ns"]), "px": float(f["px"])})
        except ValueError:
            fl.append({"t_ns": f["t_ns"], "px": f["px"]})
    for r in check_bars(fl, bars):
        if isinstance(r["row"], int):
            r = dict(r, row=_label("fills", r["row"], t["fills"][r["row"]], "約定"))
        _fail(out, "iv", r["row"], r["reason"])
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
            if v % MINUTE_NS != 0:
                _fail(out, "iv", lab, f"{what}の時刻 {v} が分の区切りから {v % MINUTE_NS} ns ずれている")
                continue
            if v - MINUTE_NS not in starts:
                _fail(out, "iv", lab, f"{what}の時刻 {v} に閉じた 1 分足(始まり {v - MINUTE_NS})が無い")


def _num(v: str):
    """記録した量の計算の値を数に(整数の書き方なら整数、ほかは浮動小数)。"""
    if v.strip() != v or not v:
        raise ValueError(v)
    try:
        return int(v)
    except ValueError:
        return float(v)


SIZING_COLS = ("margin_jpy", "use_ratio", "levels", "size_px", "size_px_source", "usdjpy", "usdjpy_t_ns", "qty_raw")


def _position_before(t: dict, o: Mapping, k: int, order_pos: dict) -> str:
    """注文 o(orders の k 行目)を送る時刻以前の約定までで、帳簿のツールが出す建玉(10 進の文字列)。
    使う約定: 同じ (銘柄, 側) の、時刻 ≤ 注文を受けた時刻で、注文の表でこの注文より前の行の注文の約定(この注文自身と、
    後に出した注文の約定は入れない。道の約定の時刻は値を決めた観測の時刻で、注文を受けた時刻と同じことがあるため)。"""
    placed = int(o["placed_t_ns"])
    inp = []
    for f in t["fills"]:
        if (f["instrument"], f["range"]) != (o["instrument"], o["range"]):
            continue
        j = order_pos.get((f["instrument"], f["range"], f["order_id"]))
        if j is None or j >= k or int(f["t_ns"]) > placed:
            continue
        inp.append({"t_ns": int(f["t_ns"]), "side": f["side"], "qty": float(f["qty"]), "px": float(f["px"]),
                    "ccy": f["ccy"]})
    if not inp:
        return "0"
    fx = [{"t_ns": int(p["t_ns"]), "pair": p["pair"], "rate": float(p["rate"])} for p in t["fx"]
          if (p["instrument"], p["range"]) == (o["instrument"], o["range"])]
    return book(inp, fx or None).fills[-1]["position_after"]


def _check_sizes(t: dict, out: list) -> None:
    """(v) 注文の量: 量の出所が「量の計算」の行は、記録した量の計算の値から計算し直した量。「建玉」の行は、送る時刻
    以前の約定までで帳簿のツールが出す建玉の絶対値(売買は建玉の逆、量の計算の列は空)。"""
    order_pos = {(o["instrument"], o["range"], o["order_id"]): k for k, o in enumerate(t["orders"])}
    for k, o in enumerate(t["orders"]):
        lab = _label("orders", k, o, "注文")
        if o["origin"] == ORIGIN_FORCED:
            continue
        if o["origin"] != ORIGIN_ROAD:
            _fail(out, "v", lab, f"出所 {o['origin']!r} が「{ORIGIN_ROAD}」でも「{ORIGIN_FORCED}」でもない")
            continue
        if o["qty_source"] == QTY_FROM_POSITION:
            filled = [c for c in SIZING_COLS if o[c] != ""]
            if filled:
                _fail(out, "v", lab, f"量の出所が「建玉」の行に量の計算の列 {filled} が書かれている")
            try:
                pos = _position_before(t, o, k, order_pos)
            except (ValueError, KeyError, LedgerError) as exc:
                _fail(out, "v", lab, f"送る時刻以前の約定から建玉を計算できない: {exc}")
                continue
            want = repr(abs(float(pos)))
            if o["qty"] != want:
                _fail(out, "v", lab, f"注文の量 {o['qty']!r} が、送る時刻以前の約定までの建玉 {pos} の絶対値 {want!r} と違う")
            if o["position_at_send"] != pos:
                _fail(out, "v", lab, f"送る時点の建玉 {o['position_at_send']!r} が帳簿のツールの建玉 {pos!r} と違う")
            if pos != "0" and o["side"] != ("sell" if not pos.startswith("-") else "buy"):
                _fail(out, "v", lab, f"決済の売買 {o['side']!r} が建玉 {pos} の逆でない")
            zero = pos == "0"
        elif o["qty_source"] == QTY_FROM_SIZING:
            try:
                usd = None if o["usdjpy"] == "" else _num(o["usdjpy"])
                raw, qty = size_detail(margin_jpy=_num(o["margin_jpy"]), use_ratio=_num(o["use_ratio"]),
                                       levels=int(o["levels"]), price=_num(o["size_px"]), quote_ccy=o["quote_ccy"],
                                       usdjpy_at_entry=usd)
            except (ValueError, SizingError) as exc:
                _fail(out, "v", lab, f"記録した量の計算の値から量を計算し直せない: {exc}")
                continue
            if o["qty"] != repr(qty):
                _fail(out, "v", lab, f"注文の量 {o['qty']!r} が、記録した量の計算の値から計算し直した量 {repr(qty)!r} と違う")
            if o["qty_raw"] != str(raw):
                _fail(out, "v", lab, f"切り捨て前の量 {o['qty_raw']!r} が計算し直した値 {str(raw)!r} と違う")
            zero = qty == 0
        else:
            _fail(out, "v", lab, f"量の出所 {o['qty_source']!r} が「{QTY_FROM_SIZING}」でも「{QTY_FROM_POSITION}」でもない")
            continue
        if zero:
            if o["state"] != ZERO_QTY_STATE or o["sent_t_ns"] != "":
                _fail(out, "v", lab, f"量が 0 の行は状態「{ZERO_QTY_STATE}」で出していない(出した時刻が空)はず: "
                                     f"状態 {o['state']!r}・出した時刻 {o['sent_t_ns']!r}")
        elif o["state"] == ZERO_QTY_STATE or o["sent_t_ns"] == "":
            _fail(out, "v", lab, f"量が 0 でない行が出されていない: 状態 {o['state']!r}・出した時刻 {o['sent_t_ns']!r}")


def check_tables(store_dir: str, bars: Sequence[Mapping]) -> CheckResult:
    """表の形の置き場 1 つに (i)〜(v) を当てる(モジュールの説明を参照)。"""
    out: list = []
    try:
        t = _read_all(store_dir, out)
        if t is None:
            return CheckResult(out)  # 表がそろわなければ、ほかの検査はしない((i) の失敗だけを出す)
        _check_derived(t, out, store_dir)
        _check_links(t, out)
        _check_bars_tables(t, bars, out)
        _check_sizes(t, out)
    except Exception as exc:  # 想定外の壊れ方。英語の文を出さずに失敗として止める(O-1)
        _fail(out, "i", store_dir, f"検査の途中で想定していない壊れ方に当たった(例外の種類 {type(exc).__name__})")
    return CheckResult(out)
