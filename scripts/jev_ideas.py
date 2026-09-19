#!/usr/bin/env python3
"""戦略案の在庫から「空白の地図」を作る道具(`docs/JEV.md` §8 の U1)。

出所: `docs/JEV.md` §8 の U1(**戦略案の在庫の「空白の地図」**)。
`.claude/skills/delegated-study/SKILL.md` §5.5-3 の「状態変数の系統」がここで見える。

**この道具は何も止めないし、何かを良しともしない**(オーナー逐語 L-218:
「**そもそも止めるとjev出させようとするのは間違った運用で、判断はLLMと私の役割である**」)。
出すのは案ごとの分類と確率、code が数えた件数表、そして「不確か」の印だけである。
**順位・重み・優先度は作らない。**

**CLAUDE.md §5.1(全捨て)・§0.2 A-5 を機械で守る**:
- state に入れてよいのは `docs/STRATEGY_IDEAS.md` の**案の本文そのもの**(箇条書き 1 項目)と、
  `docs/DATA.md` 由来の在庫名だけ。過去の検証結果・判定・数値は一切入れない。
- 案の本文は**元の文書の逐語の部分文字列**であることを送信前に検査する(`_assert_verbatim`)。
- 出力に「効く / 効かない / 有望 / 優先」の語を置かない。地図は**記述**であって順位ではない。

使い方:
  python3 scripts/jev_ideas.py map [--ideas docs/STRATEGY_IDEAS.md] [--dry-run] [--summary]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.jev.client import JevClient, JevError  # noqa: E402
from scripts.jev.redact import RedactionError  # noqa: E402
# しきい値・伏せ字の作法・末尾 1 行は `jev_check` から import して使う(複製しない)。
from scripts.jev_check import (  # noqa: E402
    ATTENTION,
    PRESENCE,
    DEFAULT_MODEL,
    clean_state,
    flag_counts,
    summary_line,
)
# 在庫名の集め方は `jev_survey` のものを再利用する(複製しない)。
from scripts.jev_survey import inventory_names  # noqa: E402

# ---------------------------------------------------------------------------
# 定数(しきい値はこの 1 箇所。ATTENTION / PRESENCE は import したまま書き直さない)
# ---------------------------------------------------------------------------
DEFAULT_IDEAS = REPO / "docs" / "STRATEGY_IDEAS.md"
DEFAULT_OUT_DIR = REPO / "data" / "jev" / "ideas"
MAX_IDEA_CHARS = 1_500          # state に入れる案の本文の上限(仕様)
UNCERTAIN_CONFIDENCE = 0.60     # 選択の確信がこれ未満なら「不確か」と書く(料理本 E.16)

# この体制の市場の呼び名(state に入れる。順序は `CLAUDE.md` §5.3 の記載順)
MARKETS = ["暗号資産", "FX", "株"]

# 集計の軸(表の行と列。**順位ではない**)
FAMILIES = ["price_derived", "volume_or_flow", "positioning_or_liquidation",
            "orderbook", "external_or_calendar", "composite", "unclear"]
MARKET_OPTIONS = ["crypto", "fx", "stock", "any", "unclear"]
HORIZONS = ["intraday_minutes", "hours", "days_or_longer", "unclear"]
WEIGHT_LEVELS = 3  # 0 / 1 / 2 の 3 段

# 案 1 件 = 箇条書き 1 項目。`- **<ID> <名前>**: <本文>`
_BULLET_RE = re.compile(r"^-\s+\*\*(?P<head>.+?)\*\*\s*[:：]\s*(?P<rest>.*)$")
# ID は 1 個だけ。`#70` か `O-3` / `O-3b` の形。ID の直後に別の ID や区切り記号が
# 続く見出し(例: `O-3 / O-6 の到達点…`)は「案 1 件」ではないので案として扱わない。
_IDEA_HEAD_RE = re.compile(r"^(?P<id>#\d+|[A-Za-z]{1,4}-\d+[a-z]?)\s+(?P<name>[^/、,・\s].*)$")
_CONT_RE = re.compile(r"^\s{2,}\S")


def _clip(text: str) -> tuple[str, bool]:
    text = text.strip()
    if len(text) <= MAX_IDEA_CHARS:
        return text, False
    return text[:MAX_IDEA_CHARS], True


# ---------------------------------------------------------------------------
# 抽出(決定論的。state は code が組む = `docs/JEV.md` §4-2)
# ---------------------------------------------------------------------------
def scan_bullets(text: str) -> tuple[list[dict], list[dict]]:
    """(案, 案として扱わなかった箇条書き)。どちらも行番号つきで返す。

    本文 = 箇条書きの行の `:` の後ろ + 直後の字下げされた継続行(空行で切れる)。
    """
    lines = text.splitlines()
    ideas: list[dict] = []
    skipped: list[dict] = []
    i = 0
    while i < len(lines):
        m = _BULLET_RE.match(lines[i])
        if not m:
            i += 1
            continue
        anchor = i + 1
        body = [m.group("rest")]
        j = i + 1
        while j < len(lines) and _CONT_RE.match(lines[j]):
            body.append(lines[j].strip())
            j += 1
        head = m.group("head").strip()
        hm = _IDEA_HEAD_RE.match(head)
        raw = " ".join(part for part in body if part).strip()
        if hm and raw:
            idea_text, truncated = _clip(raw)
            ideas.append({
                "anchor": anchor,
                "idea_id": hm.group("id"),
                "idea_name": hm.group("name").strip(),
                "idea_text": idea_text,
                "parts": [p for p in body if p],
                "chars": len(raw),
                "truncated": truncated,
            })
        else:
            skipped.append({
                "anchor": anchor,
                "head": head,
                "reason": "見出しが「ID 1 個 + 名前」の形ではない" if not hm else "本文が空",
            })
        i = j
    return ideas, skipped


def extract_ideas(text: str) -> list[dict]:
    return scan_bullets(text)[0]


def _assert_verbatim(idea: dict, source: str) -> None:
    """案の本文が元の文書の逐語であることを確かめる(A-5 の機械的な担保)。

    継続行は連結するので、(a) 連結前の各行が元の文書にそのまま現れること、
    (b) state に入れる本文が連結の先頭からの切り出しであること、の 2 つで代える。
    """
    joined = " ".join(idea["parts"]).strip()
    if not joined.startswith(idea["idea_text"]):
        raise ValueError(f"案 {idea['idea_id']} の本文が元の連結の先頭からの切り出しではない")
    for part in idea["parts"]:
        if part and part not in source:
            raise ValueError(
                f"案 {idea['idea_id']} の本文に元の文書に無い行がある: {part[:40]}")


def state_for(idea: dict, names: list[str]) -> dict:
    return {
        "idea_id": idea["idea_id"],
        "idea_name": idea["idea_name"],
        "idea_text": idea["idea_text"],
        "inventory_names": names,
        "markets": list(MARKETS),
    }


# ---------------------------------------------------------------------------
# 問い(1 判断 1 問・肯定形・criteria は具体例つき・英語。断片は日本語のまま)
# ---------------------------------------------------------------------------
def questions_map() -> dict:
    """1 案 1 要求。6 問をまとめて出す(投機的な fan-out、`docs/JEV.md` §4-3)。"""
    return {
        "state_variable_family": {
            "type": "choice",
            "instructions": (
                "Which family does the main state variable of `idea_text` belong to? "
                "The state variable is what the idea reads to decide when to act."
            ),
            "criteria": {
                "price_derived": (
                    "It reads only the price series itself or something computed from it: "
                    "moving averages, range width, candle bodies and wicks, returns, "
                    "realised volatility, a gap between two prices. Example: "
                    "\"直近40分のレンジ中心からの乖離で建てる\"."
                ),
                "volume_or_flow": (
                    "It reads traded quantity or the direction of executed trades: volume "
                    "spikes, taker buy/sell imbalance, the tape. Example: "
                    "\"出来高の急増の後に価格が続くか\"."
                ),
                "positioning_or_liquidation": (
                    "It reads how market participants are positioned, or forced exits: open "
                    "interest, long/short ratio, funding rate, liquidation or stop-out prints. "
                    "Example: \"建玉の急増が翌日の値動きを予告するか\"."
                ),
                "orderbook": (
                    "It reads resting limit orders: depth on each side, the imbalance between "
                    "bid and ask size, queue position, quotes being picked off. Example: "
                    "\"厚い板の数円手前に指値を置く\"."
                ),
                "external_or_calendar": (
                    "It reads something outside this market's own tape: another venue's price, "
                    "a clock or session boundary, an index rebalance date, on-chain flows, "
                    "news or social attention. Example: \"仲値決定前の値動きに追随する\"."
                ),
                "composite": (
                    "It combines variables from two or more of the families above, and no "
                    "single one is the main one. Example: \"価格・出来高・建玉を合わせて嵐を予告する\"."
                ),
                "unclear": (
                    "The text does not say what is read. Example: a one-line entry that names "
                    "only an outcome, with no variable named."
                ),
            },
        },
        "market": {
            "type": "choice",
            "instructions": "Which market does `idea_text` act in?",
            "criteria": {
                "crypto": (
                    "A crypto asset or a crypto venue is named or clearly implied: BTC, "
                    "bitFlyer, Binance, a perpetual future, funding rate, on-chain data."
                ),
                "fx": (
                    "A currency pair or an FX-specific event is named: USD/JPY, the Tokyo "
                    "fixing (仲値), an FX broker."
                ),
                "stock": (
                    "An equity, an equity index or an equity venue is named: Nikkei 225, "
                    "TOPIX, J-REIT, JPX, a listed share, an index rebalance."
                ),
                "any": (
                    "The mechanism is stated in terms that hold in any of the three markets, "
                    "with no venue or instrument named. Example: \"移動平均クロスがコストを上回るか\"."
                ),
                "unclear": "The text does not give enough to place it in any of the above.",
            },
        },
        "data_in_inventory": {
            "type": "noul",
            "instructions": (
                "The data this idea needs appears, by name, in `inventory_names`."
            ),
            "criteria": {
                "true": (
                    "Every input the idea reads is named in the list, possibly under different "
                    "wording for the same thing. Example: the idea reads 1-minute candles of "
                    "FX_BTC_JPY and the list contains \"FX_BTC_JPY 1分足チャート(lightchart)\"."
                ),
                "false": (
                    "At least one input is not in the list. Example: the idea reads liquidation "
                    "prints or social-media attention and no entry names such a series."
                ),
            },
        },
        "needs_execution_model": {
            "type": "noul",
            "instructions": (
                "The edge of `idea_text` depends on execution details - whether a maker order "
                "fills, where it sits in the queue, latency - rather than on a signal alone."
            ),
            "criteria": {
                "true": (
                    "The idea is about resting quotes, market making, rebates, picking off "
                    "quotes, or the fill of a limit order. Example: \"両側に気配を出し続けて "
                    "スプレッドを取る\" - whether it works is decided by which side fills."
                ),
                "false": (
                    "The idea states a directional prediction and could be measured by taking "
                    "the prevailing price. Example: \"建玉の急増の翌日に同方向へ動くか\"."
                ),
            },
        },
        "implementation_weight": {
            "type": "score",
            "instructions": (
                "How much new machinery must be built before `idea_text` can be measured at all?"
            ),
            "criteria": [
                (
                    "Nothing new is needed. The series the idea reads is named in "
                    "`inventory_names`, and a replay over a stored price or trade series answers "
                    "the question. Example: a moving-average rule on 1-minute candles already "
                    "on disk."
                ),
                (
                    "New data must be collected or reshaped first. The series exists somewhere "
                    "but is not in `inventory_names`, or the stored files must be rebuilt into "
                    "another shape before the question can be asked. Example: open-interest "
                    "history that must be snapshotted daily for weeks, or an order book that "
                    "must be reconstructed from raw messages."
                ),
                (
                    "A new execution path or a new market connection must be built first. The "
                    "question cannot be answered without placing orders, without a venue this "
                    "system does not connect to, or without a fill model that does not exist. "
                    "Example: measuring slippage by sending live minimum-size orders, or "
                    "quoting on a venue that has not been connected."
                ),
            ],
        },
        "horizon": {
            "type": "choice",
            "instructions": "How long does `idea_text` hold a position once it is opened?",
            "criteria": {
                "intraday_minutes": (
                    "Seconds to tens of minutes, closed the same session. Example: "
                    "\"秒スケールの小さな変動を常時回転する\", \"30分保有\"."
                ),
                "hours": (
                    "Hours, within a day or across one session boundary. Example: \"週明けの "
                    "ギャップが最初の1時間で縮むか\", an overnight session held to the next open."
                ),
                "days_or_longer": (
                    "One day or more. Example: \"翌日以降の価格の方向を予測する\", a daily "
                    "on-chain series used to hold for days."
                ),
                "unclear": "The text does not say how long the position is held.",
            },
        },
    }


# ---------------------------------------------------------------------------
# 合成(印と分類。**印であって判断ではない**。順位も重みも作らない)
# ---------------------------------------------------------------------------
def _probs(answers: dict, qid: str) -> dict:
    return (answers.get(qid) or {}).get("probabilities") or {}


def _argmax(probs: dict) -> str | None:
    return max(probs, key=probs.get) if probs else None


def _conf(answers: dict, qid: str) -> float | None:
    c = (answers.get(qid) or {}).get("confidence")
    return None if c is None else float(c)


def _weight_level(answers: dict) -> int | None:
    probs = _probs(answers, "implementation_weight")
    top = _argmax(probs)
    if top is None:
        return None
    try:
        return int(str(top))
    except ValueError:
        return None


def combine_map(answers: dict) -> dict:
    family = _argmax(_probs(answers, "state_variable_family"))
    market = _argmax(_probs(answers, "market"))
    horizon = _argmax(_probs(answers, "horizon"))
    conf = {qid: _conf(answers, qid) for qid in ("state_variable_family", "market",
                                                 "horizon", "implementation_weight")}
    uncertain = sorted(q for q, c in conf.items()
                       if c is not None and c < UNCERTAIN_CONFIDENCE)
    in_inv = (answers.get("data_in_inventory") or {}).get("noul")
    needs_exec = (answers.get("needs_execution_model") or {}).get("noul")
    score = (answers.get("implementation_weight") or {}).get("score")
    return {
        "family": family,
        "family_probabilities": _probs(answers, "state_variable_family"),
        "family_confidence": conf["state_variable_family"],
        "market": market,
        "market_probabilities": _probs(answers, "market"),
        "market_confidence": conf["market"],
        "data_in_inventory_probability": None if in_inv is None else round(float(in_inv), 4),
        "data_in_inventory": None if in_inv is None else bool(float(in_inv) >= PRESENCE),
        "needs_execution_model_probability": (
            None if needs_exec is None else round(float(needs_exec), 4)),
        "needs_execution_model": (
            None if needs_exec is None else bool(float(needs_exec) >= PRESENCE)),
        "implementation_weight_score": None if score is None else round(float(score), 4),
        "implementation_weight_level": _weight_level(answers),
        "implementation_weight_confidence": conf["implementation_weight"],
        "horizon": horizon,
        "horizon_probabilities": _probs(answers, "horizon"),
        "horizon_confidence": conf["horizon"],
        "uncertain": uncertain,
        "flag": bool(uncertain),
        "reason": None if uncertain else "confidence_at_or_above_uncertain",
    }


# ---------------------------------------------------------------------------
# 集計(**code が数える**。`docs/JEV.md` §4-4)
# ---------------------------------------------------------------------------
def aggregate(records: list[dict]) -> dict:
    grid = {f: {m: 0 for m in MARKET_OPTIONS} for f in FAMILIES}
    unplaced = 0
    data_yes = data_no = data_unknown = 0
    weights = {i: 0 for i in range(WEIGHT_LEVELS)}
    weight_unknown = 0
    horizons = {h: 0 for h in HORIZONS}
    horizon_unknown = 0
    exec_yes = exec_no = exec_unknown = 0
    for rec in records:
        f, m = rec.get("family"), rec.get("market")
        if f in grid and m in grid[f]:
            grid[f][m] += 1
        else:
            unplaced += 1
        d = rec.get("data_in_inventory")
        data_yes += d is True
        data_no += d is False
        data_unknown += d is None
        e = rec.get("needs_execution_model")
        exec_yes += e is True
        exec_no += e is False
        exec_unknown += e is None
        w = rec.get("implementation_weight_level")
        if w in weights:
            weights[w] += 1
        else:
            weight_unknown += 1
        h = rec.get("horizon")
        if h in horizons:
            horizons[h] += 1
        else:
            horizon_unknown += 1
    empty_cells = [(f, m) for f in FAMILIES for m in MARKET_OPTIONS if grid[f][m] == 0]
    return {
        "family_market": grid,
        "empty_cells": [list(c) for c in empty_cells],
        "n_empty_cells": len(empty_cells),
        "n_cells": len(FAMILIES) * len(MARKET_OPTIONS),
        "unplaced": unplaced,
        "data_in_inventory": {"あり": data_yes, "無し": data_no, "未分類": data_unknown},
        "needs_execution_model": {"要": exec_yes, "不要": exec_no, "未分類": exec_unknown},
        "implementation_weight": {str(k): v for k, v in weights.items()} | {
            "未分類": weight_unknown},
        "horizon": dict(horizons) | {"未分類": horizon_unknown},
    }


# ---------------------------------------------------------------------------
# 本体
# ---------------------------------------------------------------------------
def _send(client, state: dict, questions: dict) -> tuple[dict | None, str | None]:
    try:
        cleaned = clean_state(state)
    except RedactionError as e:
        return None, f"redaction:{e}"
    try:
        return client.evaluate(state=cleaned, questions=questions), None
    except JevError as e:
        return None, str(e)


def _write(out_dir: Path, stem: str, records: list[dict], summary: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}.jsonl"
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.write(json.dumps(summary, ensure_ascii=False) + "\n")
    return out_path


def _print_dry_run(ideas: list[dict], skipped: list[dict]) -> None:
    print(f"{'行':>5}  {'ID':<6}{'字数':>6}  名前")
    for idea in ideas:
        mark = "(切った)" if idea["truncated"] else ""
        print(f"{idea['anchor']:>5}  {idea['idea_id']:<6}{idea['chars']:>6}{mark}  "
              f"{idea['idea_name'][:52]}")
    if skipped:
        print("案として扱わなかった箇条書き:")
        for s in skipped:
            print(f"{s['anchor']:>5}  {s['reason']}: {s['head'][:56]}")


def _print_table(records: list[dict]) -> None:
    print(f"{'行':>5}  {'ID':<6}{'族':<28}{'市場':<9}{'在庫':>6} {'執行':>6} "
          f"{'重さ':>4}  {'期間':<18}印")
    for rec in records:
        def yn(v):
            return "-" if v is None else ("あり" if v else "無し")
        w = rec.get("implementation_weight_level")
        print(f"{rec['anchor']:>5}  {rec['idea_id']:<6}"
              f"{str(rec.get('family') or '-'):<28}{str(rec.get('market') or '-'):<9}"
              f"{yn(rec.get('data_in_inventory')):>6} "
              f"{('-' if rec.get('needs_execution_model') is None else ('要' if rec['needs_execution_model'] else '不要')):>6} "
              f"{('-' if w is None else str(w)):>4}  {str(rec.get('horizon') or '-'):<18}"
              f"{'不確か(' + '・'.join(rec.get('uncertain') or []) + ')' if rec.get('flag') else ''}")


def _print_aggregate(agg: dict) -> None:
    print("\n族 × 市場 の件数(0 のセルは空白。**順位ではない**)")
    print(f"{'族':<28}" + "".join(f"{m:>12}" for m in MARKET_OPTIONS) + f"{'計':>8}")
    for f in FAMILIES:
        row = agg["family_market"][f]
        print(f"{f:<28}" + "".join(f"{(row[m] or 0):>12}" for m in MARKET_OPTIONS)
              + f"{sum(row.values()):>8}")
    print(f"0 件のセル: {agg['n_empty_cells']} / {agg['n_cells']}"
          + (f"  分類できなかった案: {agg['unplaced']} 件" if agg["unplaced"] else ""))
    print("必要データが在庫に: " + " / ".join(f"{k} {v} 件"
                                       for k, v in agg["data_in_inventory"].items()))
    print("執行の細部に依る: " + " / ".join(f"{k} {v} 件"
                                     for k, v in agg["needs_execution_model"].items()))
    print("実装の重さ(0=在庫と既存機構で測れる / 1=データの収集か整形 / 2=新しい執行か市場): "
          + " / ".join(f"{k} {v} 件" for k, v in agg["implementation_weight"].items()))
    print("保有期間: " + " / ".join(f"{k} {v} 件" for k, v in agg["horizon"].items()))


def cmd_map(args) -> int:
    ideas_path = Path(args.ideas)
    if not ideas_path.is_file():
        print(f"[jev_ideas] 案の一覧が無い: {ideas_path}", file=sys.stderr)
        return 1
    text = ideas_path.read_text(encoding="utf-8", errors="replace")
    ideas, skipped = scan_bullets(text)
    names = inventory_names()

    client, unreachable = None, None
    if not args.dry_run:
        try:
            client = JevClient(model=args.model)
        except JevError as e:
            unreachable = str(e)

    records: list[dict] = []
    n_requests = 0
    for idea in ideas:
        rec = {"file": ideas_path.name, "kind": "idea", "anchor": idea["anchor"],
               "idea_id": idea["idea_id"], "idea_name": idea["idea_name"],
               "idea_chars": idea["chars"], "truncated": idea["truncated"],
               "flag": False, "reason": None, "sent": False}
        if args.dry_run or client is None:
            records.append(rec)
            continue
        state = state_for(idea, names)
        try:
            _assert_verbatim(idea, text)
        except ValueError as e:
            print(f"[jev_ideas] 逐語の検査に掛かったので送信しない: {e}", file=sys.stderr)
            return 2
        resp, err = _send(client, state, questions_map())
        if resp is None:
            if err and err.startswith("redaction:"):
                print(f"[jev_ideas] 伏せ字の最終検査に掛かったので送信しない: {err}",
                      file=sys.stderr)
                return 2
            unreachable = err
            print(f"[jev_ideas] 送信に失敗({idea['idea_id']} @ {idea['anchor']}): {err}",
                  file=sys.stderr)
            records.append(rec)
            continue
        n_requests += 1
        rec.update(combine_map(resp.get("answers") or {}))
        rec["sent"] = True
        rec["model"] = resp.get("model")
        records.append(rec)

    if args.dry_run or not ideas or n_requests > 0:
        unreachable = None
    agg = aggregate(records)
    n_flag, by_kind = flag_counts(records)
    summary = {"file": ideas_path.name, "kind": "_summary", "mode": "map",
               "n_ideas": len(ideas), "n_skipped_bullets": len(skipped),
               "skipped_bullets": skipped,
               "n_sent": sum(1 for r in records if r["sent"]),
               "n_requests": n_requests, "n_flag": n_flag, "flag_by_kind": by_kind,
               "inventory_names": len(names), "markets": list(MARKETS),
               "aggregate": agg,
               "dry_run": bool(args.dry_run), "unreachable": unreachable,
               "threshold": {"attention": ATTENTION, "presence": PRESENCE,
                             "uncertain_confidence": UNCERTAIN_CONFIDENCE}}
    out_path = _write(Path(args.out), ideas_path.stem + "_map", records, summary)

    if not args.summary:
        print(f"案の一覧: {ideas_path.name}  案の数: {len(ideas)}  在庫名: {len(names)} 件  "
              f"送った要求の数: {n_requests}"
              + ("  (--dry-run: 1 件も送っていない)" if args.dry_run else ""))
        if args.dry_run or n_requests == 0:
            _print_dry_run(ideas, skipped)
        else:
            _print_table(records)
            if skipped:
                print("案として扱わなかった箇条書き: "
                      + " / ".join(f"{s['anchor']} 行({s['reason']})" for s in skipped))
        _print_aggregate(agg)
        print(f"(「不確か」= 選択の確信 < {UNCERTAIN_CONFIDENCE}。"
              "**印であって判断ではない**。順位・重みは作らない)")
        print(f"書いた先: {out_path}")
    print(summary_line(summary)
          + f" / 案 {len(ideas)} 件、族 × 市場で 0 件のセル {agg['n_empty_cells']} 個")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="戦略案の在庫から族 × 市場 × データ要件の地図を作る(順位は作らない)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("map")
    p.add_argument("--ideas", default=str(DEFAULT_IDEAS))
    p.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--summary", action="store_true")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.set_defaults(func=cmd_map)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
