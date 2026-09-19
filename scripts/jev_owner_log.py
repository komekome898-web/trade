#!/usr/bin/env python3
"""オーナーの発言と事故の記述に狭い問いを当てる(`docs/JEV.md` §8 の U13 と U16)。

**この道具は何も判定しない。**出すのは確率と**候補**だけである(オーナー逐語 L-218:
「**判断はLLMと私の役割である**」)。記録に書き込むのはリードであって、この道具ではない。

  classify   U13 オーナー発言の種別と紐付け
    発言の本文と、状態板 `docs/OWNER_STATUS.md` から code が切り出した「待ち項目」を
    state にして、種別(`kind`)・どの待ち項目への答えか(`answers_pending`)・
    新しい規則を含むか(`contains_new_rule`)・その回のうちに記録が要るか
    (`requires_record_now`)を 1 要求で聞く。

  calibrate  U13 の校正
    `docs/OWNER_LOG.md` の表の 逐語 の列から `kind` を当て、**種別の列に既に付いている値**
    との一致件数と不一致の一覧を出す(**解釈は書かない**)。

  incident   U16 事故の同型判定
    新しい事故の記述を、`docs/INCIDENTS.md` の I-001〜I-012 の要旨と突き合わせ、
    どれと同型か(`same_type_as`)と型の名前(`type_label`)を聞く。
    確信が `KIND_CONFIDENT` 未満のときは**番号を出さない**。

規則(`docs/JEV.md` §4):
- 切り出しも合成も **code**(決定論的)。数える・比べる・日付は code。
- state は code が組む(判定される側が書かない)。断片は日本語のまま、問いは英語・肯定形。
- 送信前に `redact_json` + `assert_clean`(`jev_check.clean_state` を再利用)。
- 版は既定 `jev-1.13.0` 固定(`jev_check.DEFAULT_MODEL`)。応答の `model` を記録する。
- しきい値はこのファイルの先頭に定数として 1 箇所だけ置く。**結果を見てから動かさない。**

使い方:
  python3 scripts/jev_owner_log.py classify --text <発言のファイル> \
      [--pending-from docs/OWNER_STATUS.md] [--out DIR] [--dry-run] [--summary] [--model ID]
  python3 scripts/jev_owner_log.py calibrate [--log docs/OWNER_LOG.md] \
      [--out DIR] [--dry-run] [--summary] [--model ID]
  python3 scripts/jev_owner_log.py incident --text <事故の記述のファイル> \
      [--incidents docs/INCIDENTS.md] [--out DIR] [--dry-run] [--summary] [--model ID]
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
# 伏せ字の最終検査・未到達の 1 行・しきい値・版は `jev_check` の部品をそのまま使う
from scripts.jev_check import (  # noqa: E402
    ATTENTION,
    DEFAULT_MODEL,
    PRESENCE,
    clean_state,
    summary_line as check_summary_line,
)
# OWNER_LOG の表の読み方(4 列目 = 逐語、`L-\d{3}` の行だけ)は `jev_trace_export` を再利用する
from scripts.jev_trace_export import (  # noqa: E402
    CITED_MAX_CHARS,
    OWNER_LOG,
    load_owner_log,
)

# ---------------------------------------------------------------------------
# 定数(しきい値はこの 1 箇所だけ。`ATTENTION` / `PRESENCE` / `DEFAULT_MODEL` は import)
# ---------------------------------------------------------------------------
KIND_CONFIDENT = 0.60          # choice の確信度がこれ未満なら名前・番号を出さない
DEFAULT_OUT_DIR = REPO / "data" / "jev" / "owner_log"
DEFAULT_STATUS = REPO / "docs" / "OWNER_STATUS.md"
DEFAULT_INCIDENTS = REPO / "docs" / "INCIDENTS.md"

UTTERANCE_MAX_CHARS = 4_000    # 発言の本文の上限(仕様)
PENDING_MAX_ITEMS = 10         # 待ち項目の上限(仕様)
PENDING_MAX_CHARS = 200        # 待ち項目 1 件の上限(仕様)
INCIDENT_SUMMARY_MAX_CHARS = 300  # 事故の要旨 1 件の上限(仕様)
NONE_OPTION = "none"
QUOTE_MAX_CHARS = CITED_MAX_CHARS  # 逐語の切り方は `jev_trace_export` に合わせる(300 字)

# `ATTENTION` の使い道: `requires_record_now` は I-001(記録しなかった)の型なので、
# 低い方のバー(0.35)でも「記録の要確認」の印を出す。高い方(PRESENCE = 0.50)は
# 「そう述べている」側の存在の判定に使う(`jev_check` と同じ役割・同じ値)。

# ---------------------------------------------------------------------------
# 種別の選択肢(`docs/OWNER_LOG.md` の種別の列の語をそのまま使う)。
# 説明はすべて **OWNER_LOG から取った実例** 1 件ずつ(断片は日本語のまま)。
# ---------------------------------------------------------------------------
KIND_OPTIONS: dict[str, str] = {
    "指示": (
        "The owner tells the lead to do a specific piece of work now. "
        "Example from the owner log (L-059): 「年ごとのデータも表にして見せてください」."
    ),
    "決定": (
        "The owner settles a choice, or fixes a rule or a number that holds from now on. "
        "Example from the owner log (L-002): 「fableは70%、全モデル70%まで許容します」."
    ),
    "質問": (
        "The owner asks something and waits for an answer, without saying what to do. "
        "Example from the owner log (L-106): 「Obsidian の使い方→私は未使用なのでむしろ私が"
        "聞きたい」."
    ),
    "報告": (
        "The owner states what the owner did, or the state of something on the owner's side. "
        "Example from the owner log (L-008): 「restart_all.bat → share_logs.bat を 1 回実行"
        "しました」."
    ),
    "指摘": (
        "The owner points at something wrong in the lead's work or behaviour. "
        "Example from the owner log (L-141): 「こうやって私が提案しないと調査範囲を広げないのは"
        "おかしくないですか？」."
    ),
    "その他": (
        "None of the five above fits the utterance. "
        "Example from the owner log (L-122): 「やってるやろいい加減にしろや」, which the log "
        "records under a label (叱責) that is not one of the five."
    ),
}

# ---------------------------------------------------------------------------
# 事故の型の選択肢(仕様の 7 つ)。説明の実例は `docs/INCIDENTS.md` から取る。
# ---------------------------------------------------------------------------
TYPE_LABELS: dict[str, str] = {
    "記録の欠落": (
        "Something that happened was never written down where it had to be written, so it "
        "was lost and later work was built on the gap. Example (I-001): the owner reported "
        "the progress of opening a brokerage account and the lead never recorded it."
    ),
    "設定・順序の誤り": (
        "A configuration value, a file, or the order of the steps was wrong, so a mechanism "
        "silently stopped working. Example (I-010): one key outside the schema in "
        "`settings.json` made the whole `hooks` field be read as absent for three days. "
        "Example (I-012): the hooks were deleted before the settings were rewritten."
    ),
    "断定・検証不足": (
        "Something was stated as established without being measured or checked, or a "
        "measurement was run without checking that it implemented what was written. "
        "Example (I-005): the preparatory measurement did not implement the exit rule the "
        "pre-registration defined, and its numbers were used to overturn a decision."
    ),
    "用語のすり替え": (
        "A symbol, a term or a source label was used with a different meaning than before, "
        "or was moved rather than corrected. Example (I-004): the symbol `sd` was used for "
        "three different quantities and the old definitions were not deleted."
    ),
    "打ち切りの欠如": (
        "A loop of work kept going with no rule that ends it, and time was lost. "
        "Example (I-011): the review loop reached ten rounds and cost ten hours before the "
        "owner stopped it."
    ),
    "範囲の逸脱": (
        "Work went outside the scope it was given, or a duty inside that scope was pushed "
        "onto someone else. Example (I-006): the lead left its own monitoring of the data "
        "route unchecked and kept asking the owner for judgement and work."
    ),
    "その他": (
        "None of the six above fits the description."
    ),
}

# ---------------------------------------------------------------------------
# 待ち項目の切り出し(決定論的。規則は報告に書く)
# ---------------------------------------------------------------------------
# 状態板の文に現れる「待っている」の印。実物 `docs/OWNER_STATUS.md` を読んで選んだ語。
_PENDING_MARK_RE = re.compile(
    r"オーナーに求めていること|オーナーに要ること|オーナーの指示待ち|指示待ち|"
    r"オーナーの判断を待っている|判断を待っている|決めてもらう|承認待ち|回答待ち|"
    r"上申中|待っている|待ち"
)
# 印の直後にこれが来たら「待っているものは無い」と書いた行なので取らない
_PENDING_NONE_RE = re.compile(r"無し|なし|ありません|無い|0 件|ゼロ")
_PENDING_NONE_WINDOW = 20      # 印の直後の何文字まで見るか
# 状態板は古い版を消さずに `<br>(前)**進行中の合意(L-xxx)**…` と残す。**その断片は取らない**
# (取ると 1 行の中の履歴だけで上限 10 件が埋まり、表の「次の一手」に届かない。実測で確認)
_PENDING_STALE_RE = re.compile(r"^[\s>*]*[((]前[))]")
_NEXT_MOVE_COL_RE = re.compile(r"次の一手")
_TABLE_SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|$")
_EMPTY_CELL_RE = re.compile(r"^[\s\-—–ー*]*$")
# 「次の一手」のセルが「無し」「なし」で始まるなら待ち項目ではない(実物にある形)
_CELL_NONE_RE = re.compile(r"^[\s*]*(無し|なし|ありません|無い)")
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_BOLD_RE = re.compile(r"\*\*")


def _plain(text: str) -> str:
    """表示・選択肢の説明に使う 1 行。強調記号を外し、改行と連続空白を畳む。"""
    return " ".join(_BOLD_RE.sub("", text).split())


def extract_pending_items(text: str) -> list[dict]:
    """状態板の文から「オーナーが待っている項目」を切り出す。

    規則(実物 `docs/OWNER_STATUS.md` を読んで決めた。**この規則は報告に書く**):

    1. **表**: 見出し行(次の行が `|---|`)に「次の一手」を含む列があれば、以降の行の
       その列を見る。空・`—`・`-` だけのセル、および「無し」「なし」で始まるセルは
       取らない。本文 = `1 列目: その列`。
    2. **表以外の行**: `<br>` で切った断片ごとに、印(オーナーに求めていること /
       オーナーに要ること / 指示待ち / 判断を待っている / 承認待ち / 回答待ち / 上申中 /
       待っている / 待ち / 決めてもらう)を含むものを 1 件とする。
    3. 印の直後 20 字以内に「無し・なし・ありません・無い・0 件・ゼロ」があれば取らない
       (「いまオーナーに求めていること: 無し」の行を待ち項目にしないため)。
    3b. `(前)` で始まる断片は取らない。状態板は古い版を消さずに `<br>(前)…` と残すので、
       取ると 1 行の中の履歴だけで上限 10 件が埋まり、表の「次の一手」に届かない(実測)。
    4. 本文が同じものは 1 件にまとめ、各 200 字に切り、**先頭から 10 件**まで。
    5. id は出た順に `W1`, `W2`, …(choice の選択肢は一意でなければ鍵で読めない)。
    """
    items: list[dict] = []
    seen: set[str] = set()
    lines = text.splitlines()
    col: int | None = None

    def add(body: str, lineno: int, source: str) -> None:
        body = _plain(body)[:PENDING_MAX_CHARS]
        if not body or body in seen:
            return
        seen.add(body)
        items.append({"id": f"W{len(items) + 1}", "lineno": lineno,
                      "source": source, "text": body})

    for i, raw in enumerate(lines, start=1):
        line = raw.strip()
        if line.startswith("|"):
            if _TABLE_SEPARATOR_RE.match(line):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            nxt = lines[i].strip() if i < len(lines) else ""
            if _TABLE_SEPARATOR_RE.match(nxt):
                hit = [j for j, c in enumerate(cells) if _NEXT_MOVE_COL_RE.search(c)]
                col = hit[0] if hit else None
                continue
            if col is None or col >= len(cells):
                continue
            cell = cells[col]
            if _EMPTY_CELL_RE.match(cell) or _CELL_NONE_RE.match(cell):
                continue
            add(f"{cells[0]}: {cell}", i, "表(次の一手)")
        else:
            col = None
            if line:
                for seg in _BR_RE.split(line):
                    seg = seg.strip()
                    if not seg or _PENDING_STALE_RE.match(seg):
                        continue
                    m = _PENDING_MARK_RE.search(seg)
                    if not m:
                        continue
                    after = seg[m.end():m.end() + _PENDING_NONE_WINDOW]
                    if _PENDING_NONE_RE.search(after):
                        continue
                    add(seg, i, "文")
        if len(items) >= PENDING_MAX_ITEMS:
            break
    return items[:PENDING_MAX_ITEMS]


# ---------------------------------------------------------------------------
# OWNER_LOG の読み(表の読み方は `jev_trace_export.load_owner_log` を再利用)
# ---------------------------------------------------------------------------
_OWNER_ROW_RE = re.compile(r"^\|\s*(L-\d{3})\s*\|")
# 「指示(順次着手)+ 質問(…)」→ 「指示」。括弧・`+`・読点の前で切る(仕様)
_KIND_SPLIT_RE = re.compile(r"[((+＋、,/／]")


def normalize_kind(cell: str) -> str:
    """種別の列の値を選択肢の語に揃える。**括弧付きは括弧の前の語だけ**(仕様)。

    `**決定(改良案の選択)**` → `決定`、`指示 + **測定の実行と報告**` → `指示`。
    """
    return _KIND_SPLIT_RE.split(_plain(cell))[0].strip()


def load_owner_rows(path: Path = OWNER_LOG) -> list[dict]:
    """`docs/OWNER_LOG.md` の表から [{id, date, kind_raw, kind, quote}] を作る。

    逐語は `jev_trace_export.load_owner_log`(4 列目・`CITED_MAX_CHARS` 字で切る)を
    そのまま使う。この関数が足すのは **3 列目の種別** だけである。
    """
    quotes = load_owner_log(path)
    rows: list[dict] = []
    seen: set[str] = set()
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _OWNER_ROW_RE.match(line.lstrip())
        if not m:
            continue
        key = m.group(1)
        if key in seen or key not in quotes:
            continue
        cells = line.split("|")
        if len(cells) < 5:
            continue
        seen.add(key)
        rows.append({
            "id": key,
            "date": cells[2].strip(),
            "kind_raw": _plain(cells[3]),
            "kind": normalize_kind(cells[3]),
            "quote": quotes[key],
        })
    return rows


def kind_distribution(rows: list[dict]) -> dict[str, int]:
    """揃えたあとの種別の分布(件数は code が数える)。"""
    out: dict[str, int] = {}
    for r in rows:
        out[r["kind"]] = out.get(r["kind"], 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


# ---------------------------------------------------------------------------
# INCIDENTS の読み
# ---------------------------------------------------------------------------
_INCIDENT_ROW_RE = re.compile(r"^\|\s*(I-\d{3})\s*\|")


def load_incidents(path: Path = DEFAULT_INCIDENTS) -> tuple[dict[str, str], list[str]]:
    """`docs/INCIDENTS.md` の表から ({I-001: 要旨}, 要旨が取れなかった id の一覧)。

    表の形は `| I-001 | 日付 | 事象 | 原因 | 再発防止 |`。**3 列目(事象)** の先頭
    300 字を要旨とする。同じ id が 2 回出たら**先に出た方**を採る(取り下げた旧 I-008 の
    節は見出しであって表の行ではないので、現行の行だけが読まれる)。
    """
    found: dict[str, str] = {}
    missing: list[str] = []
    if not path.is_file():
        return found, missing
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _INCIDENT_ROW_RE.match(line.lstrip())
        if not m:
            continue
        key = m.group(1)
        if key in found or key in missing:
            continue
        cells = line.split("|")
        body = _plain(cells[3]) if len(cells) > 3 else ""
        if body:
            found[key] = body[:INCIDENT_SUMMARY_MAX_CHARS]
        else:
            missing.append(key)
    return dict(sorted(found.items())), sorted(missing)


# ---------------------------------------------------------------------------
# 問い(1 判断 1 問・肯定形・criteria は具体例つき・英語)
# ---------------------------------------------------------------------------
def questions_for_utterance(pending: list[dict]) -> dict:
    """U13。`kind` / `answers_pending` / `contains_new_rule` / `requires_record_now`。"""
    pending_criteria = {p["id"]: p["text"] for p in pending}
    pending_criteria[NONE_OPTION] = (
        "The utterance does not answer any of the listed items, or there are no items."
    )
    return {
        "kind": {
            "type": "choice",
            "instructions": (
                "`utterance` is one message written by the owner of the project to the lead. "
                "Pick the option that describes what the owner is doing in it."
            ),
            "criteria": dict(KIND_OPTIONS),
        },
        "answers_pending": {
            "type": "choice",
            "instructions": (
                "Each option below is an item the project is waiting on the owner for, taken "
                "from the status board. Pick the item that `utterance` gives the answer to."
            ),
            "criteria": pending_criteria,
        },
        "contains_new_rule": {
            "type": "noul",
            "instructions": (
                "The utterance states a rule or prohibition the lead must follow from now on, "
                "as opposed to a one-time instruction."
            ),
            "criteria": {
                "true": (
                    "A standing rule is stated. Example: 「日本人に読めない英語の出力して"
                    "なんの意味があるの？2度と出すな」, or 「サーバー借りるのは収益算段が"
                    "立ってからやって何回言ったらわかんねん」."
                ),
                "false": (
                    "Only this one piece of work is asked for. Example: 「年ごとのデータも"
                    "表にして見せてください」, or 「進めてください」."
                ),
            },
        },
        "requires_record_now": {
            "type": "noul",
            "instructions": (
                "The utterance conveys a state, decision or completion that must be written "
                "to the owner log in this turn."
            ),
            "criteria": {
                "true": (
                    "A state, a decision or a completion is conveyed. Example: 「現物口座開設"
                    "は済んでいて、今は先物口座開設のための約定のための入金待ち」, or "
                    "「fableは70%、全モデル70%まで許容します」."
                ),
                "false": (
                    "Nothing about the owner's state or the owner's choice is conveyed. "
                    "Example: 「Obsidian の使い方→私は未使用なのでむしろ私が聞きたい」."
                ),
            },
        },
    }


def questions_for_incident(summaries: dict[str, str]) -> dict:
    """U16。`same_type_as` / `type_label`。"""
    criteria = dict(summaries)
    criteria[NONE_OPTION] = (
        "The description does not match any of the listed past incidents, or it matches none "
        "of them closely enough to name one."
    )
    return {
        "same_type_as": {
            "type": "choice",
            "instructions": (
                "Each option below is a past incident in this project. Pick the incident "
                "whose failure has the same shape as the one in `incident_description`: the "
                "same thing went wrong for the same kind of reason, even if the subject "
                "matter is different."
            ),
            "criteria": criteria,
        },
        "type_label": {
            "type": "choice",
            "instructions": (
                "Pick the option that names the shape of the failure in "
                "`incident_description`."
            ),
            "criteria": dict(TYPE_LABELS),
        },
    }


# ---------------------------------------------------------------------------
# 送信(`jev_audit_eval` と同じ形)
# ---------------------------------------------------------------------------
def _send(client, state: dict, questions: dict) -> tuple[dict | None, str | None]:
    """(応答, 未到達の理由)。伏せ字に掛かったら送らない。"""
    try:
        cleaned = clean_state(state)
    except RedactionError as e:
        return None, f"伏せ字の最終検査に掛かったので送っていない: {e}"
    try:
        return client.evaluate(state=cleaned, questions=questions), None
    except JevError as e:
        return None, str(e)


def _client_or_none(args) -> tuple[object | None, str | None]:
    if args.dry_run:
        return None, None
    try:
        return JevClient(model=args.model), None
    except JevError as e:
        return None, str(e)


def _write_jsonl(out_dir: Path, name: str, records: list[dict], summary: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.write(json.dumps(summary, ensure_ascii=False) + "\n")
    return path


def _choice(ans: dict, qid: str) -> tuple[str | None, float | None, str]:
    """(選んだ値, 確信度, 出してよい値)。確信度が `KIND_CONFIDENT` 未満なら `none`。"""
    block = ans.get(qid) or {}
    choice = block.get("choice")
    conf = block.get("confidence")
    conf_f = None if conf is None else round(float(conf), 4)
    reported = NONE_OPTION
    if choice not in (None, NONE_OPTION) and conf_f is not None and conf_f >= KIND_CONFIDENT:
        reported = choice
    return choice, conf_f, reported


def _noul(ans: dict, qid: str) -> float | None:
    block = ans.get(qid) or {}
    v = block.get("noul")
    return None if v is None else round(float(v), 4)


# ---------------------------------------------------------------------------
# U13: classify
# ---------------------------------------------------------------------------
def summary_line_classify(summary: dict) -> str:
    if summary.get("unreachable"):
        return check_summary_line(summary)
    tail = "(--dry-run: 1 件も送っていない)" if summary.get("dry_run") else ""
    kind = summary.get("kind_reported") or "候補なし"
    pend = summary.get("answers_pending_reported") or NONE_OPTION
    marks = []
    if summary.get("new_rule_flag"):
        marks.append("新しい規則の要確認")
    if summary.get("record_attention"):
        marks.append("その回の記録の要確認")
    mark_s = "、".join(marks) or "印なし"
    return (f"種別の候補: {kind}、答える待ち項目: {pend}"
            f"(待ち項目 {summary['n_pending']} 件)、{mark_s}{tail}")


def cmd_classify(args) -> int:
    text_path = Path(args.text)
    if not text_path.is_file():
        print(f"[jev_owner_log] ファイルが無い: {text_path}", file=sys.stderr)
        return 1
    utterance = text_path.read_text(encoding="utf-8", errors="replace").strip()
    truncated = len(utterance) > UTTERANCE_MAX_CHARS
    utterance = utterance[:UTTERANCE_MAX_CHARS]

    status_path = Path(args.pending_from)
    pending: list[dict] = []
    status_missing = not status_path.is_file()
    if not status_missing:
        pending = extract_pending_items(
            status_path.read_text(encoding="utf-8", errors="replace"))

    client, unreachable = _client_or_none(args)
    rec = {
        "kind": "utterance",
        "text_file": text_path.name,
        "utterance_chars": len(utterance),
        "utterance_truncated": truncated,
        "utterance_head": _plain(utterance)[:80],
        "n_pending": len(pending),
        "kind_choice": None,
        "kind_confidence": None,
        "kind_reported": None,
        "answers_pending_choice": None,
        "answers_pending_confidence": None,
        "answers_pending_reported": None,
        "contains_new_rule": None,
        "new_rule_flag": None,
        "requires_record_now": None,
        "record_now_flag": None,
        "record_attention": None,
        "sent": False,
    }
    if client is not None:
        state = {
            "utterance": utterance,
            "pending_items": [{"id": p["id"], "text": p["text"]} for p in pending],
            "pending_item_count": len(pending),
        }
        resp, err = _send(client, state, questions_for_utterance(pending))
        if resp is None:
            unreachable = err
            print(f"[jev_owner_log] 送信に失敗: {err}", file=sys.stderr)
        else:
            ans = resp.get("answers") or {}
            k_choice, k_conf, k_rep = _choice(ans, "kind")
            rec["kind_choice"] = k_choice
            rec["kind_confidence"] = k_conf
            rec["kind_reported"] = k_rep
            p_choice, p_conf, p_rep = _choice(ans, "answers_pending")
            rec["answers_pending_choice"] = p_choice
            rec["answers_pending_confidence"] = p_conf
            rec["answers_pending_reported"] = p_rep
            nr = _noul(ans, "contains_new_rule")
            rec["contains_new_rule"] = nr
            rec["new_rule_flag"] = None if nr is None else bool(nr >= PRESENCE)
            rn = _noul(ans, "requires_record_now")
            rec["requires_record_now"] = rn
            rec["record_now_flag"] = None if rn is None else bool(rn >= PRESENCE)
            rec["record_attention"] = None if rn is None else bool(rn >= ATTENTION)
            rec["model"] = resp.get("model")
            rec["sent"] = True
            unreachable = None

    if args.dry_run:
        unreachable = None
    records = [rec] + [dict(p, kind="pending") for p in pending]
    summary = {
        "kind": "_summary",
        "command": "classify",
        "text_file": text_path.name,
        "pending_from": str(status_path),
        "status_missing": status_missing,
        "utterance_truncated": truncated,
        "n_pending": len(pending),
        "kind_reported": rec["kind_reported"],
        "answers_pending_reported": rec["answers_pending_reported"],
        "new_rule_flag": rec["new_rule_flag"],
        "record_attention": rec["record_attention"],
        "n_requests": int(bool(rec["sent"])),
        "dry_run": bool(args.dry_run),
        "unreachable": unreachable,
        "model": args.model,
        "thresholds": {"presence": PRESENCE, "attention": ATTENTION,
                       "kind_confident": KIND_CONFIDENT},
    }
    out_path = _write_jsonl(Path(args.out), f"classify__{text_path.stem}", records, summary)
    if not args.summary:
        _print_classify(rec, pending, summary, out_path)
    print(summary_line_classify(summary))
    return 0


def _print_classify(rec: dict, pending: list[dict], summary: dict, out_path: Path) -> None:
    print(f"発言: {summary['text_file']}  {rec['utterance_chars']} 字"
          + (f"({UTTERANCE_MAX_CHARS:,} 字で切った)" if rec["utterance_truncated"] else "")
          + ("  (--dry-run: 1 件も送っていない)" if summary["dry_run"] else ""))
    print(f"待ち項目の出所: {summary['pending_from']}"
          + ("(ファイルが無い)" if summary["status_missing"] else "")
          + f"  {len(pending)} 件(切り出しの規則: 表の「次の一手」の列 + 文の印。"
            f"各 {PENDING_MAX_CHARS} 字・最大 {PENDING_MAX_ITEMS} 件)")
    for p in pending:
        print(f"  {p['id']:>3}  行 {p['lineno']:>3}  {p['source']}  {p['text'][:70]}")
    print("")
    print("【候補】種別も紐付けも **候補** であり、**記録に書き込むのはリード**"
          "(Jev は判定しない)")
    conf = rec["kind_confidence"]
    print(f"  種別:           {rec['kind_choice'] or '-'}"
          f"(確信 {'-' if conf is None else format(conf, '.2f')})"
          f" → 出す値 {rec['kind_reported'] or '-'}")
    pconf = rec["answers_pending_confidence"]
    print(f"  答える待ち項目: {rec['answers_pending_choice'] or '-'}"
          f"(確信 {'-' if pconf is None else format(pconf, '.2f')})"
          f" → 出す値 {rec['answers_pending_reported'] or '-'}")
    nr = rec["contains_new_rule"]
    print(f"  新しい規則:     {'-' if nr is None else format(nr, '.3f')}"
          f"  印 {'要確認' if rec['new_rule_flag'] else ''}")
    rn = rec["requires_record_now"]
    print(f"  その回の記録:   {'-' if rn is None else format(rn, '.3f')}"
          f"  印 {'要確認' if rec['record_attention'] else ''}")
    print(f"(しきい値 presence={PRESENCE} / attention={ATTENTION} / "
          f"kind_confident={KIND_CONFIDENT}。**印であって判断ではない**)")
    print(f"書き出し: {out_path}")


# ---------------------------------------------------------------------------
# U13 の校正: calibrate
# ---------------------------------------------------------------------------
def summary_line_calibrate(summary: dict) -> str:
    if summary.get("unreachable"):
        return check_summary_line(summary)
    if summary.get("dry_run"):
        return (f"OWNER_LOG {summary['n_rows']} 行(逐語が読めた行)、"
                f"種別 {summary['n_kinds']} 種、選択肢に無い種別 "
                f"{summary['n_outside_options']} 件(--dry-run: 1 件も送っていない)")
    return (f"OWNER_LOG {summary['n_rows']} 行: 一致 {summary['n_same']} 件 / "
            f"不一致 {summary['n_diff']} 件 / 突き合わせ不可 {summary['n_unmatched']} 件"
            f"(うち選択肢に無い種別 {summary['n_outside_options']} 件)")


def cmd_calibrate(args) -> int:
    log_path = Path(args.log)
    if not log_path.is_file():
        print(f"[jev_owner_log] ファイルが無い: {log_path}", file=sys.stderr)
        return 1
    rows = load_owner_rows(log_path)
    dist = kind_distribution(rows)
    n_outside = sum(v for k, v in dist.items() if k not in KIND_OPTIONS)

    client, unreachable = _client_or_none(args)
    records: list[dict] = []
    n_requests = n_same = n_diff = n_unmatched = 0

    for row in rows:
        rec = {
            "kind": "row",
            "id": row["id"],
            "date": row["date"],
            "kind_raw": row["kind_raw"],
            "kind_normalized": row["kind"],
            "kind_in_options": row["kind"] in KIND_OPTIONS,
            "quote_head": row["quote"][:80],
            "kind_choice": None,
            "kind_confidence": None,
            "state": "突き合わせ不可",
            "sent": False,
        }
        if client is None:
            records.append(rec)
            n_unmatched += 1
            continue
        state = {"utterance": row["quote"], "pending_items": [], "pending_item_count": 0}
        resp, err = _send(client, state, questions_for_utterance([]))
        if resp is None:
            unreachable = err
            print(f"[jev_owner_log] 送信に失敗({row['id']}): {err}", file=sys.stderr)
            records.append(rec)
            n_unmatched += 1
            continue
        n_requests += 1
        ans = resp.get("answers") or {}
        choice, conf, _rep = _choice(ans, "kind")
        rec["kind_choice"] = choice
        rec["kind_confidence"] = conf
        rec["model"] = resp.get("model")
        rec["sent"] = True
        if choice is None:
            n_unmatched += 1
        elif choice == row["kind"]:
            rec["state"] = "一致"
            n_same += 1
        else:
            rec["state"] = "不一致"
            n_diff += 1
        records.append(rec)

    if args.dry_run or not rows or n_requests > 0:
        unreachable = None
    summary = {
        "kind": "_summary",
        "command": "calibrate",
        "log": str(log_path),
        "n_rows": len(rows),
        "n_kinds": len(dist),
        "kind_distribution": dist,
        "n_outside_options": n_outside,
        "n_requests": n_requests,
        "n_same": n_same,
        "n_diff": n_diff,
        "n_unmatched": n_unmatched,
        "dry_run": bool(args.dry_run),
        "unreachable": unreachable,
        "model": args.model,
        "thresholds": {"kind_confident": KIND_CONFIDENT},
    }
    out_path = _write_jsonl(Path(args.out), "calibrate", records, summary)
    if not args.summary:
        _print_calibrate(records, summary, out_path)
    print(summary_line_calibrate(summary))
    return 0


def _print_calibrate(records: list[dict], summary: dict, out_path: Path) -> None:
    print(f"OWNER_LOG: {summary['log']}  逐語が読めた行 {summary['n_rows']} 件"
          + ("  (--dry-run: 1 件も送っていない)" if summary["dry_run"] else ""))
    print(f"種別の分布(括弧の前の語だけに揃えたあと。{summary['n_kinds']} 種、"
          f"選択肢に無いもの {summary['n_outside_options']} 件):")
    for k, v in summary["kind_distribution"].items():
        mark = "" if k in KIND_OPTIONS else "  ※選択肢に無い"
        print(f"  {v:>4}  {k}{mark}")
    if summary["dry_run"]:
        print(f"書き出し: {out_path}")
        return
    print("")
    print(f"一致 {summary['n_same']} 件 / 不一致 {summary['n_diff']} 件 / "
          f"突き合わせ不可 {summary['n_unmatched']} 件(**中身の解釈は書かない**)")
    print("不一致の一覧:")
    print(f"{'ID':>7}{'台帳の種別':>12}{'模型':>8}{'確信':>7}  逐語の先頭")
    for rec in records:
        if rec["kind"] != "row" or rec["state"] != "不一致":
            continue
        conf = rec["kind_confidence"]
        print(f"{rec['id']:>7}{rec['kind_normalized']:>12}"
              f"{str(rec['kind_choice'] or '-'):>8}"
              f"{('-' if conf is None else format(conf, '.2f')):>7}  {rec['quote_head'][:46]}")
    print(f"書き出し: {out_path}")


# ---------------------------------------------------------------------------
# U16: incident
# ---------------------------------------------------------------------------
def summary_line_incident(summary: dict) -> str:
    if summary.get("unreachable"):
        return check_summary_line(summary)
    tail = "(--dry-run: 1 件も送っていない)" if summary.get("dry_run") else ""
    same = summary.get("same_type_as_reported") or NONE_OPTION
    label = summary.get("type_label") or "-"
    return (f"同型の候補: {same}、型の候補: {label}"
            f"(過去の事故 {summary['n_incidents']} 件、要旨が抜けた "
            f"{summary['n_missing']} 件){tail}")


def cmd_incident(args) -> int:
    text_path = Path(args.text)
    if not text_path.is_file():
        print(f"[jev_owner_log] ファイルが無い: {text_path}", file=sys.stderr)
        return 1
    description = text_path.read_text(encoding="utf-8", errors="replace").strip()
    truncated = len(description) > UTTERANCE_MAX_CHARS
    description = description[:UTTERANCE_MAX_CHARS]

    incidents_path = Path(args.incidents)
    summaries, missing = load_incidents(incidents_path)
    if not summaries:
        print(f"[jev_owner_log] 過去の事故を 1 件も読めなかった: {incidents_path}",
              file=sys.stderr)
        return 1

    client, unreachable = _client_or_none(args)
    rec = {
        "kind": "incident",
        "text_file": text_path.name,
        "description_chars": len(description),
        "description_truncated": truncated,
        "description_head": _plain(description)[:80],
        "n_incidents": len(summaries),
        "same_type_as_choice": None,
        "same_type_as_confidence": None,
        "same_type_as_reported": None,
        "type_label": None,
        "type_label_confidence": None,
        "sent": False,
    }
    if client is not None:
        state = {
            "incident_description": description,
            "past_incident_count": len(summaries),
        }
        resp, err = _send(client, state, questions_for_incident(summaries))
        if resp is None:
            unreachable = err
            print(f"[jev_owner_log] 送信に失敗: {err}", file=sys.stderr)
        else:
            ans = resp.get("answers") or {}
            c, conf, rep = _choice(ans, "same_type_as")
            rec["same_type_as_choice"] = c
            rec["same_type_as_confidence"] = conf
            rec["same_type_as_reported"] = rep
            lbl = ans.get("type_label") or {}
            rec["type_label"] = lbl.get("choice")
            lconf = lbl.get("confidence")
            rec["type_label_confidence"] = None if lconf is None else round(float(lconf), 4)
            rec["model"] = resp.get("model")
            rec["sent"] = True
            unreachable = None

    if args.dry_run:
        unreachable = None
    records = [rec] + [{"kind": "past_incident", "id": k, "summary": v}
                       for k, v in summaries.items()]
    summary = {
        "kind": "_summary",
        "command": "incident",
        "text_file": text_path.name,
        "incidents": str(incidents_path),
        "n_incidents": len(summaries),
        "n_missing": len(missing),
        "missing_ids": missing,
        "description_truncated": truncated,
        "same_type_as_reported": rec["same_type_as_reported"],
        "type_label": rec["type_label"],
        "n_requests": int(bool(rec["sent"])),
        "dry_run": bool(args.dry_run),
        "unreachable": unreachable,
        "model": args.model,
        "thresholds": {"kind_confident": KIND_CONFIDENT},
    }
    out_path = _write_jsonl(Path(args.out), f"incident__{text_path.stem}", records, summary)
    if not args.summary:
        _print_incident(rec, summaries, summary, out_path)
    print(summary_line_incident(summary))
    return 0


def _print_incident(rec: dict, summaries: dict[str, str], summary: dict,
                    out_path: Path) -> None:
    print(f"事故の記述: {summary['text_file']}  {rec['description_chars']} 字"
          + (f"({UTTERANCE_MAX_CHARS:,} 字で切った)" if rec["description_truncated"] else "")
          + ("  (--dry-run: 1 件も送っていない)" if summary["dry_run"] else ""))
    print(f"過去の事故: {summary['incidents']}  {len(summaries)} 件"
          f"(要旨 = 表の「事象」の列の先頭 {INCIDENT_SUMMARY_MAX_CHARS} 字)、"
          + (f"要旨が抜けた {summary['n_missing']} 件: "
             f"{', '.join(summary['missing_ids'])}" if summary["missing_ids"]
             else "要旨が抜けた 0 件"))
    for k, v in summaries.items():
        print(f"  {k}  {v[:70]}")
    print("")
    print("【候補】同型の番号も型の名前も **候補** であり、**記録に書き込むのはリード**"
          "(Jev は判定しない)")
    conf = rec["same_type_as_confidence"]
    print(f"  同型:  {rec['same_type_as_choice'] or '-'}"
          f"(確信 {'-' if conf is None else format(conf, '.2f')})"
          f" → 出す値 {rec['same_type_as_reported'] or '-'}"
          f"(確信 {KIND_CONFIDENT} 未満なら番号を出さない)")
    lconf = rec["type_label_confidence"]
    print(f"  型:    {rec['type_label'] or '-'}"
          f"(確信 {'-' if lconf is None else format(lconf, '.2f')})")
    print(f"書き出し: {out_path}")


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="オーナーの発言と事故の記述に狭い問いを当てる"
                    "(U13 種別と紐付け / U16 同型判定)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("classify", help="U13 オーナー発言の種別と紐付け")
    p1.add_argument("--text", required=True, help="発言の本文のファイル")
    p1.add_argument("--pending-from", default=str(DEFAULT_STATUS),
                    help="待ち項目を切り出す状態板")
    p1.set_defaults(func=cmd_classify)

    p2 = sub.add_parser("calibrate", help="U13 の校正(OWNER_LOG の種別の列と突き合わせる)")
    p2.add_argument("--log", default=str(OWNER_LOG))
    p2.set_defaults(func=cmd_calibrate)

    p3 = sub.add_parser("incident", help="U16 事故の同型判定")
    p3.add_argument("--text", required=True, help="事故の記述のファイル")
    p3.add_argument("--incidents", default=str(DEFAULT_INCIDENTS))
    p3.set_defaults(func=cmd_incident)

    for p in (p1, p2, p3):
        p.add_argument("--out", default=str(DEFAULT_OUT_DIR))
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--summary", action="store_true", help="末尾の 1 行だけを出す")
        p.add_argument("--model", default=DEFAULT_MODEL)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
