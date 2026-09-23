#!/usr/bin/env python3
"""道具サーベイの台帳を、報告書から機械で作る(オーナー指示 L-403「調査結果を資源化し保管してください」)。

入力: docs/DATA/SCAN_2026-09-21_tools.md だけ。
出力: docs/DATA/tools_catalog.tsv(候補 1 件 = 1 行)。

手で写さない理由: 区分 1 の 32 回のあいだ、手で数えた・写した数字が何度も食い違った
(`VERDICTS/2026-09-22_tools_scan_cat1_run31.md` §2・§3)。台帳の値はすべて報告書の記載から
機械で取り、報告書の行番号を添える。読み方の規則は `scripts/recount_scan_cat1.py` と同じものを使う
(節と機械の数が 6 要素すべてで一致することを 32 回目に確かめた規則)。

使い方: python3 scripts/build_tools_catalog.py [--check]
  --check  書き出さずに、今の tools_catalog.tsv と作り直した内容が同じかだけを見る(0 = 同じ)
"""
import re, sys, pathlib, importlib.util

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORT = ROOT / "docs/DATA/SCAN_2026-09-21_tools.md"
OUT = ROOT / "docs/DATA/tools_catalog.tsv"

spec = importlib.util.spec_from_file_location("rc", ROOT / "scripts/recount_scan_cat1.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

SHORT = {"区分1-足": "足", "区分1-ティック": "ティック", "区分1-板の待ち行列": "板の待ち行列",
         "区分1-イベント駆動": "イベント駆動", "区分1-ベクトル化": "ベクトル化",
         "区分1-市場影響と約定の模型": "市場影響と約定の模型"}


def cell(x):
    return re.sub(r"\s+", " ", x.replace("\t", " ")).strip()


def plain(x):
    return cell(re.sub(r"\*\*", "", x))


def head_word(x):
    """「**在る。**…」「**該当なし。**…」「未確認(…)」の先頭の判定語だけを取る。"""
    m = re.match(r"^\**(在る|該当なし|未確認|無い|持たない|持つ)", plain(x))
    return m.group(1) if m else ""


def stage_table(lines):
    """最後の「段の表」(候補 | 段(機構) | 段(既定) | 遅延 | 取り消しの扱い)を行ごとに返す。"""
    heads = [i for i, l in enumerate(lines) if re.match(r"^\|\s*候補\s*\|\s*段", l.strip())]
    if not heads:
        return {}
    out, i = {}, heads[-1] + 2
    while i < len(lines) and lines[i].strip().startswith("|"):
        c = [x.strip() for x in lines[i].strip().strip("|").split("|")]
        m = re.match(r"^\*{0,2}(\d+)\*{0,2}\s*`?([^`|]*)`?", c[0])
        if m and len(c) >= 5:
            out[int(m.group(1))] = {"名前": m.group(2).strip(), "段(機構)": plain(c[1]),
                                    "段(既定)": plain(c[2]), "遅延": head_word(c[3]),
                                    "遅延(原文)": plain(c[3]), "取り消しの扱い": head_word(c[4]),
                                    "取り消しの扱い(原文)": plain(c[4]), "行": i + 1}
        i += 1
    return out


def safety_table(lines):
    """最後の「安全側の通算」の表(型 | 件数 | 候補 | 中身)から、候補の番号 → 型 を返す。"""
    idx = [i for i, l in enumerate(lines) if re.match(r"^#{2,4} .*安全側の通算", l)]
    out = {}
    if not idx:
        return out
    for l in lines[idx[-1]:idx[-1] + 20]:
        c = [x.strip() for x in l.strip().strip("|").split("|")] if l.strip().startswith("|") else []
        if len(c) >= 3 and re.search(r"\d", c[2]) and not c[0].startswith("-"):
            kind = plain(c[0])
            for num in re.findall(r"(?:^|・)\s*(\d+)\s", c[2]):
                out.setdefault(int(num), []).append(kind)
    return out


def name_of(body):
    m = re.search(r"`([^`]+)`", body)
    return m.group(1) if m else ""


def routes(body):
    return sorted({int(n) for n in re.findall(r"`区分(\d)\s*へ`", body)})


def build():
    lines = REPORT.read_text().split("\n")
    # 読まないもの 2 つ(2026-09-23 リードが台帳を作ったときに見つけた):
    #  - 「24. **限界: …**」のような番号付きの注記。道具の名前を符号で含むので候補に見える。
    #  - 1・2 回目の節の候補の一覧。今とは別の番号体系で、24 = Superalgos のように今の番号と衝突する
    #    (20 回目の洗い出しで今の番号へ振り直し済み・21 回目で落ちた 4 件を 121〜124 に立て直し済み)。
    entries = rc.master_entries(lines)
    mk, reach = rc.marks(entries)
    stages = stage_table(lines)
    safety = safety_table(lines)
    last, names, route = {}, {}, {}
    for ln, num, body in entries:
        last[num] = max(last.get(num, 0), ln)
        if num not in names and name_of(body):
            names[num] = name_of(body)
        route.setdefault(num, set()).update(routes(body))
    left = rc.leftovers(lines)
    left_nums = {}
    for label, tags in left.items():                 # 値は「14 番」の形の文字列
        for t in tags:
            m = re.match(r"(\d+)\s*番", t)
            if m:
                left_nums[int(m.group(1))] = label
    cols = ["番号", "名前", "到達", *SHORT.values(), "段(機構)", "段(既定)", "遅延", "取り消しの扱い",
            "他の区分へ", "安全側の所見", "尽きていない理由", "報告書の最後の記載の行", "段の表の行",
            "遅延(原文)", "取り消しの扱い(原文)"]
    rows = []
    for num in sorted(set(last) | set(stages)):
        s = stages.get(num, {})
        d = mk.get(num, {})
        r = reach.get(num)
        rows.append([str(num), cell(s.get("名前") or names.get(num, "")),
                     "到達済み" if r is True else ("未到達" if r is False else ""),
                     *[("○" if d.get(e) is True else ("×" if d.get(e) is False else "")) for e in SHORT],
                     s.get("段(機構)", ""), s.get("段(既定)", ""), s.get("遅延", ""), s.get("取り消しの扱い", ""),
                     "・".join("区分%d" % n for n in sorted(route.get(num, ()))),
                     "・".join(safety.get(num, [])), left_nums.get(num, ""),
                     str(last.get(num, "")), str(s.get("行", "")),
                     s.get("遅延(原文)", ""), s.get("取り消しの扱い(原文)", "")])
    return "\t".join(cols) + "\n" + "\n".join("\t".join(r) for r in rows) + "\n"


def main():
    text = build()
    if "--check" in sys.argv:
        same = OUT.exists() and OUT.read_text() == text
        print("同じ" if same else "違う(作り直すこと)")
        return 0 if same else 1
    OUT.write_text(text)
    print("書き出した: %s(%d 行)" % (OUT.relative_to(ROOT), text.count("\n") - 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
