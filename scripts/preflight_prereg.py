"""事前登録の**出荷前検査**。実行の前に、文書の構造的な欠陥を機械で洗う。

**なぜ機械なのか**(2026-09-09、L-050): 2026-09-09 の 1 日で、オーナーの問い 9 回から
リードの誤り 8 件が出た。**同じ期間、リードの自己点検では 1 件も出ていない。**
自分の文書を自分で読むと、書いたときと同じ視点で読むので矛盾が見えない。
**視点を持たない検査に回す**のが対処である。

各検査は**実際に起きた事故から導出**した。想像上の欠陥は入れない。
検査 ID の横に、その検査が拾えたはずの事故を書く。

    PYTHONPATH=src python scripts/preflight_prereg.py docs/PHASE2/K1/PREREG.md

戻り値: 指摘が 1 件でもあれば 1。**1 件でも出たら実行しない**(層 1 の不合格条件)。

**この検査が拾えないもの**(層 2 / 層 3 が要る理由。ここを正直に書かないと、
検査を通ったことが「正しい」の代用品になる):

- 数値の**妥当性**(出所タグが付いていても、その出所が正しいとは限らない)
- 実装が事前登録の条項を**本当に**実装しているか(層 2 の読み A)
- 設定が**仮説から出たか都合から出たか**(層 2 の読み B)
- 書かれていない前提(層 3 の独立監査)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# 本文でこの語を使うなら、用語節に説明が要る(L-049: オーナーが読めない事前登録は監査できない)
JARGON = [
    "MDE",
    "帰無",
    "巡回シフト",
    "多重性",
    "アブレーション",
    "サニティ",
    "bp",
]

# 出所の 3 分類(I-004)。数値を含む主張には、このいずれかが要る
PROVENANCE = ("【一次資料", "【実測", "【仮定", "【事実")

# 未処理を示す語。事前登録が「完成」を称するなら、本文に残っていてはいけない(I-005)
UNFINISHED = ("未測定", "TODO", "追って測る", "後で決める", "要検討")


@dataclass
class Finding:
    check: str
    motive: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.check}] {self.detail}\n         ← {self.motive}"


def split_sections(text: str) -> dict[str, str]:
    """`## ` 見出しで章に割る。見出し行そのものを含めて返す。"""
    parts = re.split(r"^(## .*)$", text, flags=re.M)
    out: dict[str, str] = {}
    for i in range(1, len(parts), 2):
        out[parts[i].strip()] = parts[i] + parts[i + 1]
    return out


def find_section(sections: dict[str, str], *needles: str) -> tuple[str, str] | None:
    for head, body in sections.items():
        if all(n in head for n in needles):
            return head, body
    return None


def strip_quotes(body: str) -> str:
    """引用ブロック(`> `)を落とす。訂正枠の中では、撤回した旧値をそのまま引用してよい。"""
    return "\n".join(ln for ln in body.splitlines() if not ln.lstrip().startswith(">"))


def table_rows(body: str, after: int = 0) -> int:
    """`after` 文字目以降で最初に現れる表の**データ行数**を返す(見出しと区切りを除く)。"""
    lines = body[after:].splitlines()
    n = 0
    started = False
    for ln in lines:
        s = ln.strip()
        if s.startswith("|") and s.endswith("|"):
            if not started:
                started = True
                continue  # 見出し行
            if set(s) <= set("|-: "):
                continue  # 区切り行
            n += 1
        elif started and s == "":
            break
        elif started and not s.startswith("|"):
            break
    return n


def list_items(body: str, after: int = 0) -> int:
    """`after` 文字目以降で最初に現れる番号付きリストの項目数。"""
    n = 0
    started = False
    for ln in body[after:].splitlines():
        if re.match(r"^\s*\d+\.\s", ln):
            started = True
            n += 1
        elif started and ln.strip() == "":
            continue
        elif started:
            break
    return n


# ---------------------------------------------------------------- 検査 --------


def c1_counts_match(text: str, sections: dict[str, str]) -> list[Finding]:
    """C1 数え上げと項目数の一致。

    L-049: §7 の番号が `1, 2, 3, 3b, 3c, 4, 5` と枝番だったため、
    **著者自身が「6 種」と数え間違えた**。人は自分の書いた表を数え直さない。
    """
    out = []
    for head, body in sections.items():
        for m in re.finditer(r"\*\*?(\d+)\s*(種|個|水準|通り)\*\*?", body):
            claimed = int(m.group(1))
            actual = table_rows(body, m.end()) or list_items(body, m.end())
            if actual and actual != claimed:
                out.append(
                    Finding(
                        "C1 数え上げ",
                        "L-049: アブレーションを 6 種と書いて実際は 7 種だった",
                        f"{head.strip()} — 「{claimed} {m.group(2)}」と書いてあるが、"
                        f"直後の表/リストは **{actual} 項目**",
                    )
                )
    return out


def c2_symbol_defined_once(text: str) -> list[Finding]:
    """C2 記号の一意性。

    I-004: 同じ記号 `sd` を 3 つの別の量に使い回し、**古い定義を消さずに**
    新しい定義を足したので、同じ節に矛盾する定義が同居した。
    """
    lines = text.splitlines()
    # 表の**見出し行**(次の行が区切り `|---|`)は定義ではなく列名なので除く
    header = {
        i
        for i, ln in enumerate(lines)
        if i + 1 < len(lines) and set(lines[i + 1].strip()) <= set("|-: ") and lines[i + 1].strip().startswith("|")
    }
    defs: dict[str, list[str]] = {}
    for i, ln in enumerate(lines):
        if i in header:
            continue
        m = re.match(r"\s*[-|]\s*\*\*`([^`]+)`\*\*\s*[=|]\s*([^\n|]+)", ln)
        if m:
            defs.setdefault(m.group(1), []).append(m.group(2).strip())
    out = []
    for sym, bodies in defs.items():
        uniq = {b[:40] for b in bodies}
        if len(uniq) > 1:
            out.append(
                Finding(
                    "C2 記号の一意性",
                    "I-004: 同じ記号 sd を 3 つの量に使い回していた",
                    f"記号 `{sym}` に **{len(uniq)} 通りの定義**がある: "
                    + " / ".join(sorted(uniq)),
                )
            )
    return out


def c3_scope_leak(sections: dict[str, str]) -> list[Finding]:
    """C3 射程外の語が判定基準に混入していないか。

    L-048: §0 で「執行・経費は答えない」と自分で書きながら、§5 の判定バーを
    **2019 年の手数料**で置いていた。しかも指摘を受けた直後、
    **現代のコスト**に置き換えて同じ誤りを 1 段ずらして再発させた。
    """
    scope = find_section(sections, "この単位が答える問い")
    judge = find_section(sections, "採用基準")
    if not scope or not judge:
        return []
    # §0 の「答えない」以降に現れる語のうち、判定に混ざると危ないもの
    tail = scope[1].split("答えない")[-1] if "答えない" in scope[1] else ""
    watch = [w for w in ("経費", "手数料", "スプレッド", "逆選択", "約定率", "執行") if w in tail]
    # 判定条件の節(§5.3 相当)だけを見る。§5.1 は「入れない」と宣言する節なので除く
    body = judge[1]
    idx = body.find("候補と呼ぶ条件")
    cond = strip_quotes(body[idx:]) if idx >= 0 else ""
    out = []
    for w in watch:
        for ln in cond.splitlines():
            # 「使わない」「入れない」「削除」と一緒に出るのは宣言なので通す
            if w in ln and not any(k in ln for k in ("使わない", "入れない", "削除", "外した", "課さない")):
                out.append(
                    Finding(
                        "C3 射程の漏れ",
                        "L-048: §0 で射程外と書いた経費を §5 の判定バーにしていた",
                        f"§0 で射程外とした「{w}」が、判定条件の中に肯定形で現れる: {ln.strip()[:80]}",
                    )
                )
                break
    return out


def c4_no_unfinished(sections: dict[str, str]) -> list[Finding]:
    """C4 未処理の残留。

    I-005: `sd_trade` が 6 水準のうち 3 つで「未測定」のまま、
    **事前登録は完成と称していた**。MDE が書けない水準が残るのは規約 §4.1 違反。
    """
    out = []
    for head, body in sections.items():
        if "用語" in head:  # 用語節は事故の説明で「未測定」に言及する
            continue
        for word in UNFINISHED:
            for ln in strip_quotes(body).splitlines():
                if word in ln and not ln.lstrip().startswith("#"):
                    out.append(
                        Finding(
                            "C4 未処理の残留",
                            "I-005: 3 水準が未測定のまま『事前登録は完成』と称していた",
                            f"{head.strip()} に「{word}」が残っている: {ln.strip()[:80]}",
                        )
                    )
                    break
    return out


def c5_jargon_explained(text: str, sections: dict[str, str]) -> list[Finding]:
    """C5 専門語の説明。

    L-049: 「帰無 1,000 回・アブレーション 6 種・サニティ 5 種」が
    **オーナーに一つも通じなかった**。読み手が追えない事前登録は監査できない。
    """
    glossary = find_section(sections, "用語")
    if not glossary:
        return [
            Finding(
                "C5 用語",
                "L-049: 専門語が読み手に一つも通じなかった",
                "用語の節が無い。専門語を使うなら説明を置く",
            )
        ]
    body = glossary[1]
    return [
        Finding(
            "C5 用語",
            "L-049: 専門語が読み手に一つも通じなかった",
            f"本文で使っている「{w}」が用語節に無い",
        )
        for w in JARGON
        if w in text and w not in body
    ]


def c6_coverage(text: str, measured: Path | None) -> list[Finding]:
    """C6 測定の網羅性 + 事前登録の数値と測定出力の一致。

    I-005: 族には 6 水準あるのに準備測定は 3 水準しか埋めておらず、
    しかも埋まっていた 3 つの値も**事前登録の定義を実装していない測定**から出ていた。
    """
    if measured is None or not measured.exists():
        return [
            Finding(
                "C6 網羅性",
                "I-005: 準備測定が 3 水準しか埋まっていなかった",
                f"測定出力 {measured} が無い。事前登録の数値が再現できない",
            )
        ]
    data = json.loads(measured.read_text(encoding="utf-8"))
    feet = {k: v for k, v in data.get("feet", {}).items() if ":" not in k}
    out = []
    # 族の水準を事前登録から読む(§3 の足の行)
    m = re.search(r"\*\*足\*\*\s*`foot`\s*\|\s*([0-9 /]+)分", text)
    if m:
        declared = [x.strip() for x in m.group(1).split("/") if x.strip()]
        missing = [d for d in declared if d not in feet]
        if missing:
            out.append(
                Finding(
                    "C6 網羅性",
                    "I-005: 族の一部が未測定のまま完成と称していた",
                    f"族に宣言された水準 {declared} のうち **{missing} が測定されていない**",
                )
            )
    for foot, r in sorted(feet.items(), key=lambda kv: int(kv[0])):
        sd = r.get("sd_trade_bp")
        if sd is None:
            continue
        if f"{sd:.1f} bp" not in text:
            out.append(
                Finding(
                    "C6 数値の一致",
                    "I-005: 事前登録の数値が、測定を伴わない値だった",
                    f"{foot} 分の `sd_trade` = {sd} bp が事前登録の本文に無い"
                    "(測定と文書がずれている)",
                )
            )
    return out


def c7_provenance_on_thresholds(sections: dict[str, str]) -> list[Finding]:
    """C7 判定条件に、出所の無い裸の数値が無いか。

    I-004: 判定バー 5 bp の出所を 2 回とも誤って表示した。
    **裸の数値が判定条件に入ること自体**が、出所を問われない構造をつくる。
    """
    judge = find_section(sections, "採用基準")
    if not judge:
        return []
    body = judge[1]
    idx = body.find("候補と呼ぶ条件")
    if idx < 0:
        return []
    out = []
    for ln in strip_quotes(body[idx:]).splitlines():
        s = ln.strip()
        if not re.match(r"^\d+\.\s", s):
            continue
        # 節番号(§5.2 等)と年は除いて、裸の量を探す
        cleaned = re.sub(r"§[\d.]+|20\d\d", "", s)
        if re.search(r"\d+(\.\d+)?\s*(bp|%|ドル|円)", cleaned) and not any(
            p in s for p in PROVENANCE
        ):
            out.append(
                Finding(
                    "C7 判定条件の出所",
                    "I-004: 判定バー 5 bp の出所を 2 回とも誤表示した",
                    f"判定条件に出所タグの無い数値がある: {s[:80]}",
                )
            )
    return out


CHECKS = "C1 数え上げ / C2 記号の一意性 / C3 射程の漏れ / C4 未処理 / C5 用語 / C6 網羅性 / C7 出所"


def run(path: Path, measured: Path | None) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    sections = split_sections(text)
    return [
        *c1_counts_match(text, sections),
        *c2_symbol_defined_once(text),
        *c3_scope_leak(sections),
        *c4_no_unfinished(sections),
        *c5_jargon_explained(text, sections),
        *c6_coverage(text, measured),
        *c7_provenance_on_thresholds(sections),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("prereg", nargs="?", default=str(REPO / "docs" / "PHASE2" / "K1" / "PREREG.md"))
    ap.add_argument("--measured", default=None, help="準備測定の出力 JSON(既定は同じ階層の dispersion.json)")
    args = ap.parse_args()

    path = Path(args.prereg)
    measured = Path(args.measured) if args.measured else path.parent / "dispersion.json"

    findings = run(path, measured)
    print(f"出荷前検査: {path}")
    print(f"  検査項目: {CHECKS}")
    print(f"  測定出力: {measured}")
    print()
    if not findings:
        print("指摘 0 件。**層 1 は通過**(層 2 / 層 3 は別途)")
        return 0
    for f in findings:
        print(f"  {f}")
    print()
    print(f"**{len(findings)} 件。層 1 不合格 — 直すまで実行しない。**")
    return 1


if __name__ == "__main__":
    sys.exit(main())
