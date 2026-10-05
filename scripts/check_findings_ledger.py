"""知見台帳(`docs/RESEARCH/FINDINGS_LEDGER.md`)の機械の検査。

合意 L-603〜L-607(`docs/OWNER_STATUS.md` の進行中の合意「知見の溜め方」)を、
文章の決まりで終わらせず(A-17)、行ごとに機械で止める。

止めるもの:
- 観察の行(`### K-nnn`)に決まった欄が無い・空
- 確かさが 監査済 / 未監査 / 推定 のどれでもない。監査済なのに監査の記録が無い
- 測った日が全捨て(L-019、2026-09-08)より前
- 観察・渡す先・次の問い が「知見なし」「言えない」「なし」だけ(L-604「**「知見なし」と書くだけで監査を通り…**」)
- どこかに「知見なし」「棄却済み」がある(CLAUDE.md §5「既に棄却済み」と書かない)
- 否定を含む行の射程に期間(西暦の年)が無い(射程の外へ使わせないため)
- 出所のファイルがリポジトリに無い
- 状態が「確かめた / 覆った」なのに、指す K 番号が台帳に無い
- カードの節(`### カード: …`)で、閉じたのに改良の周が 0、または次に打てる手が空
- カードの物差しの欄が、台帳に無い K 番号を指す
- 欄「なぜの仮説」「予言」「確かめのデータ」(L-702 で足した)が無い・空。確かめのデータが
  「見つけたのと同じ…」「別: …」のどちらでもない。初期値は欄を足す前(測った日 2026-10-05 以前)の行だけ
- 状態が「確かめた」なのに、確かめのデータが「別: …」(見つけるのに使っていないデータ)でない(L-702)

`--report <報告.md>` を付けると、測定の報告に「## 知見台帳に足した行」の節があり、
そこに書かれた K 番号がすべて台帳にあり、「次の手」が書かれているかも見る。

使い方:
    python3 scripts/check_findings_ledger.py [--ledger PATH] [--report PATH ...]
終了コード 0 = 問題なし、1 = 問題あり(1 行に 1 件出す)。
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = REPO / "docs" / "RESEARCH" / "FINDINGS_LEDGER.md"

# 全捨て(L-019)の日。これより前の測定は台帳に入れない。
ZENSUTE = date(2026, 9, 8)

OBS_FIELDS = (
    "観察", "対象", "出所", "測った日", "射程", "大きさ", "確かさ", "監査",
    "否定を含む", "渡す先", "次の問い", "なぜの仮説", "予言", "確かめのデータ", "状態",
)
# L-702(2026-10-05)で足した欄。足す前の行には初期値を入れ、なぜと予言のスキルが候補を受け取ったときに 1 行ずつ埋める。
WHY_FIELDS = ("なぜの仮説", "予言", "確かめのデータ")
INITIAL = "初期値(L-702 で欄を足した。1 行ずつは未確認)"
INITIAL_UNTIL = date(2026, 10, 5)
DATA_SAME, DATA_OTHER = "見つけたのと同じ", "別:"
CARD_FIELDS = (
    "状態", "場面ごとの効き", "なぜ", "安定", "重なり", "経費と約定",
    "bitFlyer で効くか", "改良の周", "次に打てる手",
)
CARD_AXES = ("場面ごとの効き", "なぜ", "安定", "重なり", "経費と約定", "bitFlyer で効くか")

CERTAINTY = {"監査済", "未監査", "推定"}
TARGET = {"場面", "仕組み"}
YESNO = {"はい", "いいえ"}
CARD_STATE = {"測定中", "休止", "閉じた"}
EMPTY_VALUES = {"", "なし", "無し", "知見なし", "言えない", "不明", "-", "—", "未記入"}
FORBIDDEN_ANYWHERE = ("知見なし", "棄却済み")

OBS_HEAD = re.compile(r"^### (K-\d{3,})\s*(.*)$")
CARD_HEAD = re.compile(r"^### カード: (.+)$")
FIELD = re.compile(r"^- ([^:：]+)[:：]\s*(.*)$")
KREF = re.compile(r"K-\d{3,}")
BACKTICK = re.compile(r"`([^`]+)`")


def _parse(text: str):
    """台帳を観察の行とカードの節に分ける。欄は `- 名前: 値` の 1 行。"""
    obs: dict[str, dict] = {}
    cards: dict[str, dict] = {}
    errors: list[str] = []
    cur: dict | None = None
    in_example = False
    for ln, line in enumerate(text.splitlines(), 1):
        if line.startswith("```"):
            in_example = not in_example  # 書式の見本の囲みは数えない
            continue
        if in_example:
            continue
        if line.startswith("## ") or line.startswith("# "):
            cur = None
            continue
        m = OBS_HEAD.match(line)
        if m:
            kid = m.group(1)
            if kid in obs:
                errors.append(f"{ln}: {kid} が 2 回ある")
            cur = obs[kid] = {"_line": ln, "_kind": "obs"}
            continue
        m = CARD_HEAD.match(line)
        if m:
            name = m.group(1).strip()
            if name in cards:
                errors.append(f"{ln}: カード「{name}」の節が 2 回ある")
            cur = cards[name] = {"_line": ln, "_kind": "card"}
            continue
        if line.startswith("### "):
            cur = None
            continue
        if cur is not None:
            f = FIELD.match(line)
            if f:
                cur[f.group(1).strip()] = f.group(2).strip()
    return obs, cards, errors


def _year_in(text: str) -> bool:
    return re.search(r"(19|20)\d\d", text) is not None


def check_ledger_text(text: str, repo: Path = REPO) -> list[str]:
    obs, cards, errors = _parse(text)
    for kid, row in obs.items():
        at = f"{row['_line']}: {kid}"
        for name in OBS_FIELDS:
            if name not in row:
                errors.append(f"{at}: 欄「{name}」が無い")
        for name in ("観察", "渡す先", "次の問い", "射程", "大きさ", "出所") + WHY_FIELDS:
            if name in row and row[name] in EMPTY_VALUES:
                errors.append(f"{at}: 欄「{name}」が「{row[name]}」だけ(出口にしない。L-604)")
        for name, val in row.items():
            if name.startswith("_"):
                continue
            for bad in FORBIDDEN_ANYWHERE:
                if bad in val:
                    errors.append(f"{at}: 欄「{name}」に「{bad}」がある")
        if row.get("確かさ") is not None and row["確かさ"] not in CERTAINTY:
            errors.append(f"{at}: 確かさ「{row['確かさ']}」は 監査済 / 未監査 / 推定 のどれでもない")
        if row.get("確かさ") == "監査済" and row.get("監査", "") in EMPTY_VALUES:
            errors.append(f"{at}: 監査済なのに監査の記録が無い")
        if row.get("対象") is not None and row["対象"] not in TARGET:
            errors.append(f"{at}: 対象「{row['対象']}」は 場面 / 仕組み のどちらでもない")
        if row.get("否定を含む") is not None and row["否定を含む"] not in YESNO:
            errors.append(f"{at}: 否定を含む「{row['否定を含む']}」は はい / いいえ のどちらでもない")
        if row.get("否定を含む") == "はい" and not _year_in(row.get("射程", "")):
            errors.append(f"{at}: 否定を含むのに射程に期間(年)が無い(射程の外へ使わない)")
        d = row.get("測った日", "")
        try:
            measured = date.fromisoformat(d)
        except ValueError:
            if "測った日" in row:
                errors.append(f"{at}: 測った日「{d}」が YYYY-MM-DD でない")
        else:
            if measured < ZENSUTE:
                errors.append(f"{at}: 測った日 {d} は全捨て(L-019、{ZENSUTE})より前")
        src = BACKTICK.findall(row.get("出所", ""))
        if "出所" in row and not src:
            errors.append(f"{at}: 出所にファイルのパス(`…`)が無い")
        for p in src:
            if not (repo / p.split("#")[0].split(":")[0]).exists():
                errors.append(f"{at}: 出所のファイル `{p}` がリポジトリに無い")
        try:
            old_row = date.fromisoformat(row.get("測った日", "")) <= INITIAL_UNTIL
        except ValueError:
            old_row = False
        for name in WHY_FIELDS:
            if row.get(name) == INITIAL and not old_row:
                errors.append(f"{at}: 欄「{name}」の初期値は、欄を足す前(測った日 {INITIAL_UNTIL} 以前)の行だけ。中身を書く")
        data = row.get("確かめのデータ", "")
        if data and data != INITIAL and not (data.startswith(DATA_SAME) or data.startswith(DATA_OTHER)):
            errors.append(f"{at}: 確かめのデータ「{data[:20]}…」は「{DATA_SAME}…」「{DATA_OTHER} …」のどちらでもない")
        st = row.get("状態", "")
        if st.startswith("確かめた") and not data.startswith(DATA_OTHER):
            errors.append(f"{at}: 状態が確かめたなのに、確かめのデータが「{DATA_OTHER} …」(見つけるのに使っていないデータ)でない(L-702)")
        if st:
            if st == "開いている":
                pass
            elif st.startswith("確かめた") or st.startswith("覆った"):
                refs = KREF.findall(st)
                if not refs:
                    errors.append(f"{at}: 状態「{st}」が K 番号を指していない")
                for r in refs:
                    if r not in obs:
                        errors.append(f"{at}: 状態が指す {r} が台帳に無い")
            else:
                errors.append(f"{at}: 状態「{st}」は 開いている / 確かめた(K-…) / 覆った(K-…) のどれでもない")
    for name, card in cards.items():
        at = f"{card['_line']}: カード「{name}」"
        for f in CARD_FIELDS:
            if f not in card:
                errors.append(f"{at}: 欄「{f}」が無い")
        st = card.get("状態")
        if st is not None and st not in CARD_STATE:
            errors.append(f"{at}: 状態「{st}」は 測定中 / 休止 / 閉じた のどれでもない")
        m = re.match(r"\s*(\d+)", card.get("改良の周", ""))
        cycles = int(m.group(1)) if m else None
        if "改良の周" in card and cycles is None:
            errors.append(f"{at}: 改良の周が数で始まっていない")
        if card.get("次に打てる手", "") in EMPTY_VALUES and "次に打てる手" in card:
            errors.append(f"{at}: 次に打てる手が空(閉じたカードにも書く)")
        if st == "閉じた" and (cycles is None or cycles < 1):
            errors.append(f"{at}: 閉じたのに「なぜ」から出た改良の周が 0(閉じるのは重くする)")
        for axis in CARD_AXES:
            for r in KREF.findall(card.get(axis, "")):
                if r not in obs:
                    errors.append(f"{at}: 欄「{axis}」が指す {r} が台帳に無い")
    return errors


def check_report_text(report: str, ledger_text: str) -> list[str]:
    obs, _, _ = _parse(ledger_text)
    m = re.search(r"^## 知見台帳に足した行\s*$(.*?)(?=^## |\Z)", report, re.S | re.M)
    if not m:
        return ["報告に「## 知見台帳に足した行」の節が無い(測定の出口は次の手。L-603)"]
    body = m.group(1)
    errs = []
    refs = KREF.findall(body)
    if not refs:
        errs.append("「## 知見台帳に足した行」に K 番号が無い")
    for r in refs:
        if r not in obs:
            errs.append(f"報告が挙げる {r} が台帳に無い")
    if "次の手" not in body:
        errs.append("「## 知見台帳に足した行」に「次の手」が無い")
    return errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    ap.add_argument("--report", type=Path, action="append", default=[])
    a = ap.parse_args(argv)
    text = a.ledger.read_text(encoding="utf-8")
    errs = check_ledger_text(text)
    for r in a.report:
        errs += [f"{r}: {e}" for e in check_report_text(r.read_text(encoding="utf-8"), text)]
    for e in errs:
        print(e)
    obs, cards, _ = _parse(text)
    print(f"観察の行 {len(obs)}・カードの節 {len(cards)}・問題 {len(errs)}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
