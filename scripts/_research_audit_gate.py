#!/usr/bin/env python3
"""研究の取り返しのつかない一手に、監査の記録を要求する関門。

**なぜコードの中にあるか(2026-09-13、L-164)**
押し出しの関門は `githooks/pre-push` に置いた。どう呼ばれても押し出すのは git だからである。
同じ理屈で、**封印を開ける・結果を読む**という取り返しのつかない行為が実際に起きるのは
このリポジトリのコードの中なので、関門もそこに置く。フックでも設定でもないので、
コマンドの書き方を変えても迂回できない。

**09-13 に何が起きたか**
判定区間を開けたあとで測定器の欠陥が次々に出て、1 日分の研究を全部捨てた。
測定器が壊れても止まらず、もっともらしい数値を返していた。
事前登録の監査は設計を見るので、**出てきた数値そのものは見ない。**
だから検査点は 2 つ要る: **開ける前**と、**結果を報告する前**。

**限界(正直に書く)**
- リードはこのファイルを書き換えられる。**防いでいるのは「改変が差分に残る」ことだけ**である。
- 呼び出していないスクリプトには効かない。組み込み先は下の `WIRED` に列挙する。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

LOG_REL = "docs/AUDITOR/ACTION_LOG.md"

# このファイルを呼んでいる場所(増やしたらここにも書く)
# **10 本目の監査の訂正**: 旧版はここに「scripts/phase2_seal.py — 封印の作成と開封」と
# 書いていたが、`phase2_seal.py` は封印の**作成**しかせず、この関門を呼んでいない(grep で 0 件)。
# 開封(held-out を読む)を行うのは `sealed.py: load_sealed` と、その写しである
# `p2_02_final.py: check_guards` の 2 本である。**記述が実装と違っていた。**
WIRED = [
    "src/bot/research/sealed.py: load_sealed        — 封印の開封(4 つ目の門)",
    "scripts/phase2/p2_02_final.py: check_guards    — 同上(load_sealed の二重実装)",
    "scripts/judge_gates.py (--unit は必須)          — 結果の読み出し(測定後・報告前)",
]
# 呼び出し口が消されていないことは `tests/test_audit_gates_wired.py` が毎回の pytest で測る
# (指紋の台帳は共有部品にしか掛かっておらず、呼び出し側の現役コードに掛けると
#  普通の研究作業が止まるため。台帳の範囲はオーナーが決めること。)

AUDITORS = ("owner-model-auditor", "owner-auditor")


def _root(root: Path | str | None = None) -> Path:
    if root is not None:
        return Path(root)
    here = Path(__file__).resolve().parent.parent
    return here


def find_audit(unit: str, stage: str, root: Path | str | None = None) -> tuple[bool, str]:
    """ACTION_LOG に `監査対象: <unit>/<stage>` の節があり、判定が「通す」かを見る。

    返り値: (通してよいか, 理由)
    判定できないときは通さない(2026-09-13 の教訓)。
    """
    log = _root(root) / LOG_REL
    try:
        lines = log.read_text(encoding="utf-8").split("\n")
    except Exception as exc:
        return False, f"{LOG_REL} が読めない({exc})。**判定できないときは通さない。**"

    key = f"監査対象: {unit}/{stage}"
    start = None
    for i, line in enumerate(lines):
        if key in line:
            start = i  # 最後に現れたものを使う
    if start is None:
        return False, f"「{key}」の節が {LOG_REL} に無い。**この一手はまだ監査を通していない。**"

    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    sec = lines[start:end]

    if not any(a in ln for ln in sec for a in AUDITORS):
        return False, "節に監査役の名前が無い。"

    body = [ln for ln in sec if len(ln.strip()) >= 10]
    if len(body) < 8:
        return False, f"指摘の本文が {len(body)} 行しかない(8 行以上が必要)。"

    # 判定は「行頭が 判定: の行」のうち**最後のもの**だけを見る。
    # 地の文の中の引用を判定として拾わないため(2026-09-13 の 2 本目の監査)。
    verdicts = [ln.strip() for ln in sec if ln.startswith("判定:")]
    if not verdicts:
        return False, "行頭の「判定:」の行が無い。"
    last = verdicts[-1]
    if not last.startswith("判定: 通す"):
        return False, f"最後の判定が [{last}]。「判定: 通す」でなければ進めない。"
    return True, "監査の記録あり。"


def require_audit(unit: str, stage: str, root: Path | str | None = None) -> None:
    """通らなければ、理由を日本語で書いて終了コード 2 で止める。"""
    ok, why = find_audit(unit, stage, root)
    if ok:
        return
    what = {
        "封印の開封": "判定区間を開ける",
        "事前登録": "事前登録を確定する",
        "結果": "測定の結果を読み出して報告する",
    }.get(stage, stage)
    sys.stderr.write(
        f"""
[研究の関門] {what}ことを拒否した。

対象: {unit} / {stage}
理由: {why}

**なぜ止めるか**: 2026-09-13、判定区間を開けたあとで測定器の欠陥が次々に出て、
1 日分の研究を全部捨てた。測定器は壊れても止まらず、もっともらしい数値を返していた。
判定区間は一度しか開けられないので、**開ける前と、結果を報告する前**に検査する。

通すには:
  1. `owner-model-auditor` を呼ぶ。渡すのは (a) この一手 (b) 応えているオーナーの逐語
     (c) **事前登録と、生の出力の両方**(結果の監査のとき)
  2. 返ってきた指摘と判定を、**逐語で**この会話に出す
  3. {LOG_REL} に次を含む節を作る:
       「監査対象: {unit}/{stage}」/ 監査役の名前 / 逐語 8 行以上 / 行頭の「判定: 通す」
  4. **「止める」が残っている間は進めない。**直すか、両論を添えてオーナーへ上申する

**この監査は「測定が事前登録どおりに動いたか」だけを見る。判定そのものをやり直すためではない。**
**監査のあとに数値や図を変えたら、変更点を記録して監査をやり直す**(検査を通すための調整を防ぐため)。
"""
    )
    raise SystemExit(2)


def cli() -> int:
    import argparse

    p = argparse.ArgumentParser(description="研究の関門の状態を確認する(組み込み先から呼ばれる)")
    p.add_argument("--unit", required=True)
    p.add_argument("--stage", required=True, choices=["事前登録", "封印の開封", "結果"])
    p.add_argument("--check-only", action="store_true", help="止めずに結果だけ表示する")
    a = p.parse_args()
    ok, why = find_audit(a.unit, a.stage)
    print(("通す" if ok else "止める") + f": {why}")
    if a.check_only:
        return 0
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(cli())
