#!/usr/bin/env python3
"""区分 1 の数え直し。報告書 `docs/DATA/SCAN_2026-09-21_tools.md` だけを入力にして、
6 要素の印・3 段の残り・機関で数えた値・段の表との突き合わせを機械で出す。

使い方: python3 scripts/recount_scan_cat1.py [報告.md]

置いた理由(2026-09-23、区分 1 の 29 回目のリードの検収 §3(5)):
22 回目の数え直しに使った道具が scratchpad に置かれたまま残らず、**同じ規則で数え直せなくなった。**
29 回目は粗い道具で数えて節の値と 6 要素中 5 つで食い違い、どちらが正かを決められなかった。
規則を口伝えにしないため(CLAUDE.md §0.2 O-6)、規則そのものをここに固定する。

**数える規則(ここが唯一の在処)**:
1. 一次は **候補の一覧の記載**である(22 回目の知見 13 の逐語「候補の一覧の記載が一次で、集計は従とする」)。
   `### 候補の一覧` の見出しから次の `### ` までを候補の一覧とみなす。
2. 候補の行は `^\\s*(\\d+)\\.\\s` で始まる行と、それに続く字下げした行である。
   **候補の番号は、行の中に `(<数> 番` があればそれを採る。**無ければ行頭の数字を採る。
   (一覧の番号は回によって「候補の番号」と「その回の並び順」の 2 通りが使われている。
   119 番の記載は先頭が並び順の `15.` で、番号は名前の後ろに `(119 番、` の形で在る。)
3. 印は 6 要素の語の出現ごとに判定する。語の直後から**同じ文の終わりまで**を見て、
   途中に挟まる語の並び(`と`・読点・符号・他の 6 要素の語)を飛ばした先が
   打ち消しの語(付けない / 付けていない / 付けなかった / 付けず / 入れない / 外す / 外した /
   決めていない / 決まらなかった / 未確認)で始まればその出現は打ち消し、そうでなければ肯定。
   並びを飛ばすのは「A と B と C は付けない」の形が 1 つの打ち消しで複数の語に掛かるためで、
   直後の何字かだけを見る粗い当て方だと、隣の文の打ち消しを拾って肯定を打ち消してしまう。
   **同じ候補について、その語に触れた最後の記載を採る。**同じ記載の中では最後の出現を採る。
4. 到達は同じ規則で「一次資料に未到達」「未到達」を打ち消し、「一次資料に到達」「到達済み」を肯定とする。
   **どちらも書かれていない候補は「到達の記載なし」に入れ、残りには数えない。**
5. 3 段(一次資料に未到達 / 到達済みだが印が無い / 個別の要素が未決)は、
   報告の **最後の「尽きた」に数えないもの の見出し** の下の列挙を読み、その文言で振り分ける。
   見出しに限るのは、本文がこの小節を参照するだけの行を拾わないためである。
   これは報告自身の台帳を数え直すものであって、台帳の中身が正しいかは見ていない。
6. 機関で数えた値は、番号で数えた値に束ねの規則を当てたものである。
   束ねるのは 22 番と 52 番(同じ機関の別の起動口)、13 番と 123 番(本家と分岐)。

**この道具が見ていないもの(射程)**: 印の中身が原典と合っているか / 段の当てはめが正しいか /
候補の一覧に書き落とされた印。**書いてあるものを数えるだけである。**
"""
import re
import sys
import pathlib

ELEMS = ["区分1-足", "区分1-ティック", "区分1-板の待ち行列",
         "区分1-イベント駆動", "区分1-ベクトル化", "区分1-市場影響と約定の模型"]
NEG = re.compile(r"付けない|付けていない|付けなかった|付けず|入れない|外す|外した|"
                 r"決めていない|決まらなかった|当たらない|該当しない|未確認")
NEG_WIN = 24
CHAIN = re.compile(r"^(?:[\s`*]|と|、|・|および|区分1-[^\s`*、。]+)*")
BUNDLE = [(22, 52), (13, 123)]


def candidate_entries(lines):
    """候補の一覧の中の「候補の行 + 字下げの続き」を、報告の順に返す。"""
    out = []
    i, n = 0, len(lines)
    inside = False
    while i < n:
        ln = lines[i]
        if re.match(r"^### +候補の一覧", ln):
            inside, i = True, i + 1
            continue
        if inside and re.match(r"^### ", ln):
            inside = False
        if inside and re.match(r"^\s*\d+\.\s", ln):
            body = [ln]
            j = i + 1
            while j < n and lines[j].startswith("   ") and lines[j].strip():
                body.append(lines[j])
                j += 1
            head = ln
            lead = re.split(r"[—–]", head)[0]
            m = re.search(r"(\d+)\s*番", lead)
            num = int(m.group(1)) if m else int(re.match(r"^\s*(\d+)\.", head).group(1))
            out.append((i + 1, num, " ".join(x.strip() for x in body)))
            i = j
            continue
        i += 1
    return out


def verdict(body, word):
    """その記載の中で、その語が最後に出たところの肯定 / 打ち消しを返す。無ければ None。"""
    last = None
    for m in re.finditer(re.escape(word), body):
        tail = body[m.end():]
        cut = tail.find("。")
        if cut >= 0:
            tail = tail[:cut]
        rest = tail[CHAIN.match(tail).end():]
        last = not NEG.search(rest[:NEG_WIN])
    return last


def marks(entries):
    """候補ごとの 6 要素の印と、到達の状態を決める。"""
    mk = {}
    reach = {}
    for _, num, body in entries:
        for e in ELEMS:
            v = verdict(body, e)
            if v is not None:
                mk.setdefault(num, {})[e] = v
        for word, val in (("一次資料に未到達", False), ("未到達", False),
                          ("一次資料に到達", True), ("到達済み", True)):
            if word in body:
                reach[num] = val
    return mk, reach


def stage_rows(lines):
    """最後の「段の表」の候補の番号を返す。見出しの 2 列目が「段(機構)」の表を採る。"""
    rows, cur = [], None
    for ln in lines:
        s = ln.strip()
        if not s.startswith("|"):
            cur = None
            continue
        c = [x.strip() for x in s.strip("|").split("|")]
        if len(c) >= 3 and c[0] == "候補" and c[1].startswith("段"):
            cur = []
            rows.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r"^\*{0,2}(\d+)\*{0,2}\s", c[0])
        if m:
            cur.append(int(m.group(1)))
    return rows[-1] if rows else []


def leftovers(lines):
    """最後の「尽きた」に数えないもの の列挙を、文言で 3 段に振り分ける。"""
    idx = [i for i, ln in enumerate(lines)
           if re.match(r"^#{1,4} ", ln) and "「尽きた」に数えないもの" in ln]
    if not idx:
        return {}
    start = idx[-1]
    buf = []
    for ln in lines[start + 1:]:
        if re.match(r"^#{1,4} ", ln):
            break
        if re.match(r"^\s*[-*]\s", ln):
            buf.append(ln.strip())
    out = {"一次資料に未到達": [], "到達済みだが印が無い": [],
           "個別の要素が未決": [], "その他": []}
    for b in buf:
        m = re.search(r"(\d+)\s*番", b) or re.search(r"候補\s*(\d+)", b)
        # 番号が読めないときも、印や符号をそのまま出さない。報告に貼ったときに
        # 太字や符号の対応が崩れるため(2026-09-23 の受け入れ検査 --all で当てた)。
        tag = (m.group(1) + " 番") if m else re.sub(r"[`*\-]", "", b)[:20]
        if "未到達" in b:
            out["一次資料に未到達"].append(tag)
        elif "未決" in b:
            out["個別の要素が未決"].append(tag)
        elif "印が無い" in b:
            out["到達済みだが印が無い"].append(tag)
        else:
            out["その他"].append(tag)
    return out


def why(lines, num):
    """1 つの候補について、印を決めた記載を報告の行番号つきで出す(食い違いを追うため)。"""
    for no, cand, body in candidate_entries(lines):
        if cand != num:
            continue
        hits = [(e, verdict(body, e)) for e in ELEMS if verdict(body, e) is not None]
        if hits:
            print("報告 %d 行 : %s" % (no, " ".join(
                "%s=%s" % (e, "肯定" if v else "打ち消し") for e, v in hits)))
            print("    %s" % body[:200])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    p = pathlib.Path(args[0] if args else "docs/DATA/SCAN_2026-09-21_tools.md")
    lines = p.read_text().splitlines()
    for a in sys.argv[1:]:
        if a.startswith("--why="):
            why(lines, int(a.split("=")[1]))
            return 0
    entries = candidate_entries(lines)
    mk, reach = marks(entries)

    print("入力 = %s" % p)
    print("候補の一覧の記載 = %d 件" % len(entries))
    print("印に触れた候補 = %d 件" % len(mk))
    print("")

    print("== 3 段の数え直し")
    lo = leftovers(lines)
    for k in ["一次資料に未到達", "到達済みだが印が無い", "個別の要素が未決"]:
        v = lo.get(k, [])
        print("%s = %d 件 : %s" % (k, len(v), " ".join(v) if v else "なし"))
    if lo.get("その他"):
        print("上の 3 段に入らない別立て = %d 件 : %s"
              % (len(lo["その他"]), " ".join(lo["その他"])))
    print("")

    print("== 6 要素ごとの 総数 と 残り")
    union = set()
    for e in ELEMS:
        have = sorted(c for c, d in mk.items() if d.get(e))
        union |= set(have)
        rest = [c for c in have if reach.get(c) is False]
        print("%s : 総数 %d 件 : 残り %d 件 : %s"
              % (e, len(have), len(rest), " ".join(str(c) for c in have)))
    print("6 要素のどれかに印がある候補 = %d 件" % len(union))
    norec = sorted(c for c in union if c not in reach)
    print("そのうち到達の記載が無い候補 = %d 件 : %s"
          % (len(norec), " ".join(str(c) for c in norec) if norec else "なし"))
    print("")

    print("== 機関で数えた値")
    print("番号で数えた値 = %d 件" % len(union))
    cur = set(union)
    for a, b in BUNDLE:
        if a in cur and b in cur:
            cur.discard(a)
        print("%d 番と %d 番を束ねた値 = %d 件" % (a, b, len(cur)))
    print("")

    print("== 段の表と印の集合の突き合わせ")
    st = stage_rows(lines)
    imp = {c for c, d in mk.items() if d.get("区分1-市場影響と約定の模型")}
    print("段の表の行 = %d 件" % len(st))
    print("区分1-市場影響と約定の模型 の印 = %d 件" % len(imp))
    only_stage = sorted(set(st) - imp)
    only_mark = sorted(imp - set(st))
    print("段の表にあって印が無い = %d 件 : %s"
          % (len(only_stage), " ".join(str(c) for c in only_stage) if only_stage else "なし"))
    print("印があって段の表に無い = %d 件 : %s"
          % (len(only_mark), " ".join(str(c) for c in only_mark) if only_mark else "なし"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
