"""原典の設定値とモードを抜き出し、仕様の表に 1 つも欠けていないかを確かめる(1 本道の工程 0 の S3)。

オーナーの逐語:
- L-776「**全ての変数は固定値でなく調整可能な値で、それはバックテストで探る族の種類と同義です。modeの切り替えとかもあったと思う。**」
- L-776「**間違った前提で組んだ確かめが通ってしまったら、後続が全て間違いになり結局全捨てになります。私はもうやり直さなくてよい信頼性のある仕組みを求めていると言ったはずです。**」
- L-778「**お願いします**」(工程 0 を 1 本道に足す)

抜き出すもの: 原典の設定の区切り(既定は「各自の設定値ココカラ」から「ここから下は触らない方がいい」まで。`--block-start` /
`--block-end` で変えられる。区切りが見つからなければ止まる)の中の、モジュールの頂の代入の名前全部。値が `dict(...)` か
`{...}` なら、鍵も `名前.鍵` として抜き出す。

仕様の側: 仕様の文書の中に、次の形の囲みを 1 つ置く(原典ごとに `params <原典のファイル名>`):

    ```params matilda_v52.py
    foot: 族
    settings_inner.entry_setting: 族
    apikey: 除外 API の鍵(売買に効かない)
    ```

検査(`check`)が失敗にするもの: 抜き出した名前で囲みに無いもの / 囲みにあって原典に無い名前 / 「族」でも「除外 <理由>」でもない行 /
理由の無い「除外」/ 同じ名前の 2 度書き / 原典の囲みが無い。終了コード 0 = 合格、1 = 失敗、2 = 入力の誤り。
ここで出す文は全部日本語(O-1)。
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from dataclasses import dataclass

DEFAULT_START = r"各自の設定値ココカラ"
DEFAULT_END = r"ここから下は触らない方がいい"
FAMILY = "族"
EXCLUDED = "除外"


class SourceParamsError(Exception):
    """入力の誤り(原典・仕様が読めない、区切りが無い)。文は日本語。"""


@dataclass(frozen=True)
class Param:
    name: str
    line: int
    source: str  # 値の式の原文


def _block_lines(text: str, start: str, end: str, path: str) -> tuple[int, int]:
    lines = text.split("\n")
    s = next((i for i, x in enumerate(lines, 1) if re.search(start, x)), None)
    if s is None:
        raise SourceParamsError(f"{path}: 設定の区切りの始まり(/{start}/)が見つからない")
    e = next((i for i, x in enumerate(lines, 1) if i > s and re.search(end, x)), None)
    if e is None:
        raise SourceParamsError(f"{path}: 設定の区切りの終わり(/{end}/)が {s} 行より後に見つからない")
    return s, e


def _dict_keys(node: ast.AST) -> list[str] | None:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict" and not node.args:
        return [k.arg for k in node.keywords if k.arg is not None]
    if isinstance(node, ast.Dict):
        keys = []
        for k in node.keys:
            if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
                return None
            keys.append(k.value)
        return keys
    return None


def extract(path: str, start: str = DEFAULT_START, end: str = DEFAULT_END) -> list[Param]:
    """原典の設定の区切りの中の、頂の代入の名前(と dict の鍵)を行の順に返す。"""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        raise SourceParamsError(f"{path}: 読めない({exc.strerror})") from None
    s, e = _block_lines(text, start, end, path)
    try:
        tree = ast.parse(text, filename=path)
    except SyntaxError as exc:
        raise SourceParamsError(f"{path}: Python として読めない({exc.lineno} 行)") from None
    out: list[Param] = []
    for node in tree.body:
        if not (s < node.lineno < e):
            continue
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        src = ast.get_source_segment(text, value) or ""
        for t in targets:
            names = [t.id] if isinstance(t, ast.Name) else [x.id for x in getattr(t, "elts", []) if isinstance(x, ast.Name)]
            for n in names:
                out.append(Param(n, node.lineno, src))
                for k in _dict_keys(value) or []:
                    out.append(Param(f"{n}.{k}", node.lineno, src))
    return out


_FENCE = re.compile(r"^```params[ \t]+(\S+)[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)


def read_spec(spec_path: str) -> dict[str, list[tuple[int, str, str]]]:
    """仕様の文書の params の囲みを読む。{原典のファイル名: [(文書の行, 名前, 印の原文)]}"""
    try:
        with open(spec_path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        raise SourceParamsError(f"{spec_path}: 読めない({exc.strerror})") from None
    out: dict[str, list[tuple[int, str, str]]] = {}
    for m in _FENCE.finditer(text):
        base_line = text.count("\n", 0, m.start(2)) + 1
        rows = out.setdefault(m.group(1), [])
        for i, raw in enumerate(m.group(2).split("\n")):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            name, sep, mark = line.partition(":")
            mark = mark.split("#", 1)[0]  # 行の後ろの注釈(extract の出力の「# 行 = 値」)は印に含めない
            rows.append((base_line + i, name.strip(), mark.strip() if sep else ""))
    return out


def check(sources: list[str], spec_path: str, start: str = DEFAULT_START, end: str = DEFAULT_END) -> list[str]:
    """失敗の行(日本語)を返す。空なら合格。"""
    spec = read_spec(spec_path)
    failures: list[str] = []
    for src in sources:
        base = os.path.basename(src)
        params = extract(src, start, end)
        want = {p.name: p for p in params}
        rows = spec.get(base)
        if rows is None:
            failures.append(f"{spec_path}: 原典 {base} の params の囲みが無い(抜き出した {len(want)} 個が全部どこにも無い)")
            continue
        seen: dict[str, int] = {}
        for ln, name, mark in rows:
            if name in seen:
                failures.append(f"{spec_path} {ln} 行: {base} の {name} を 2 度書いている(前は {seen[name]} 行)")
                continue
            seen[name] = ln
            if name not in want:
                failures.append(f"{spec_path} {ln} 行: {name} は {base} の設定の区切りに無い名前")
            if mark == FAMILY:
                continue
            if mark.startswith(EXCLUDED):
                if not mark[len(EXCLUDED):].strip():
                    failures.append(f"{spec_path} {ln} 行: {base} の {name} の「除外」に理由が無い")
                continue
            failures.append(f"{spec_path} {ln} 行: {base} の {name} の印 '{mark}' は「族」でも「除外 <理由>」でもない")
        for p in params:
            if p.name not in seen:
                failures.append(f"{base} {p.line} 行の {p.name}(= {p.source})が仕様の表に無い")
    return failures


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="原典の設定値とモードを抜き出し、仕様の表と突き合わせる(工程 0 の S3)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("extract", "check"):
        p = sub.add_parser(name)
        p.add_argument("--src", action="append", required=True, help="原典のファイル(何度でも)")
        p.add_argument("--block-start", default=DEFAULT_START)
        p.add_argument("--block-end", default=DEFAULT_END)
        if name == "check":
            p.add_argument("--spec", required=True, help="params の囲みを持つ仕様の文書")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "extract":
            for src in a.src:
                print(f"```params {os.path.basename(src)}")
                for p in extract(src, a.block_start, a.block_end):
                    print(f"{p.name}:   # {p.line} 行 = {p.source}")
                print("```")
            return 0
        failures = check(a.src, a.spec, a.block_start, a.block_end)
    except SourceParamsError as exc:
        print(f"入力の誤り: {exc}", file=sys.stderr)
        return 2
    if failures:
        print(f"検査 失敗: {len(failures)} 行")
        for f in failures:
            print(f"  {f}")
        return 1
    print("検査 合格: 原典の設定値とモードは全部、仕様の表にある")
    return 0


if __name__ == "__main__":
    sys.exit(main())
