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
   **「- **68 番 `quanttrader`**」の形の中黒の箇条も候補の行として採る**(2026-09-23、31 回目)。
   21 回目の節は粒度が決まった 2 件(61 番・68 番)をこの形で書いており、番号つきの行だけを見る
   作りでは 68 番の `区分1-足` と `区分1-ティック` を数え落としていた(節の 35 件に対し 34 件)。
3. 印は 6 要素の語の出現ごとに判定する。**同じ文の中で、その語より前に自分以外の候補の
   「<数> 番」が出ていたら、その出現は数えない**(2026-09-23、31 回目)。22 番 `Lean CLI` の記載は
   「**なお 52 番 `QuantConnect` が同じ機関の別の入口として `区分1-足` と `区分1-イベント駆動` を持つ。**」
   であり、この 2 つは 52 番の印である。22 番自身は同じ記載で「**6 要素はこの回に決まらなかった。**」と
   書かれていて、報告の台帳でも「到達済みだが 6 要素の印が無い」2 件の片方である。
   語の直後から**同じ文の終わりまで**を見て、
   途中に挟まる語の並び(`と`・読点・符号・他の 6 要素の語)を飛ばした先が
   打ち消しの語(付けない / 付けていない / 付けなかった / 付けず / 入れない / 外す / 外した /
   決めていない / 決めない / 決めなかった / 決まらなかった / 可能性 / 当たらない / 該当しない /
   未確認)で始まればその出現は打ち消し、そうでなければ肯定。**「決めない」と「可能性」は
   2026-09-23(31 回目)に足した。**46 番の記載「名前から `区分1-ティック` の可能性があるが、
   販売の場に到達していないので決めない。」が肯定として数えられ、節に無い印が 1 件立っていた。
   並びを飛ばすのは「A と B と C は付けない」の形が 1 つの打ち消しで複数の語に掛かるためで、
   直後の何字かだけを見る粗い当て方だと、隣の文の打ち消しを拾って肯定を打ち消してしまう。
   **同じ候補について、その語に触れた最後の記載を採る。**同じ記載の中では最後の出現を採る。
4. 到達は、22 回目の節が引いた定義の逐語で決める(報告書の `#### 6 要素ごとの 総数 と 残り(数え方を変えた)`)。
   > **総数** = その印を持つ候補の数 / **残り** = そのうち**一次資料に到達していない**ものの数
   > (状態が「未着手」または「判別に一次資料が要る」のまま)。**「浅い」以上は到達済みであり、残りではない。**
   したがって到達していない側の語は「未着手」「判別に一次資料が要る」「一次資料に未到達」の 3 つ、
   到達した側の語は「一次資料に到達」「到達済み」「到達の記録」「[深掘り]」「浅い」の 5 つである。
   記載の中で**最後に出た語**を採り、直後が「を外す」「ではない」「ではなく」ならその語を打ち消す
   (95 番の記載「`判別に一次資料が要る` を外す。」がこの形)。
   **裸の「未到達」は採らない。**この報告では 11 番 `OctoBot` の「最小実行(成行と指値の 1 往復)は未到達」の
   ように、一次資料ではなく最小実行について使われているためである。
   **どちらも書かれていない候補は「到達の記載なし」に入れ、残りには数えない。**
   (2026-09-23、31 回目に直した。それまでは 4 つの語句の字面だけを見ており、印を持つ 81 件のうち
   53 件が「到達の記載なし」に落ちていた。落ちた中には 23 回目に一次資料から印を当てた候補 1〜23 が
   まるごと入っており、報告自身の台帳の「一次資料に未到達 = 0 件」とも噛み合っていなかった。)
5. 3 段(一次資料に未到達 / 到達済みだが印が無い / 個別の要素が未決)は、
   報告の **最後の「尽きた」に数えないもの の見出し** の下の列挙を読み、その文言で振り分ける。
   見出しに限るのは、本文がこの小節を参照するだけの行を拾わないためである。
   これは報告自身の台帳を数え直すものであって、台帳の中身が正しいかは見ていない。
6. 機関で数えた値は、番号で数えた値に束ねの規則を当てたものである。
   束ねるのは 22 番と 52 番(同じ機関の別の起動口)、13 番と 123 番(本家と分岐)。

**この道具が見ていないもの(射程)**: 印の中身が原典と合っているか / 段の当てはめが正しいか /
候補の一覧に書き落とされた印。**書いてあるものを数えるだけである。**
現に、候補 18 `zipline-reloaded` の `区分1-イベント駆動` は 24 回目の表にだけ在って候補の一覧に無いので、
この道具では拾えない(候補 6 `Ziplime` は 31 回目に一覧へ足した)。
"""
import re
import sys
import pathlib

ELEMS = ["区分1-足", "区分1-ティック", "区分1-板の待ち行列",
         "区分1-イベント駆動", "区分1-ベクトル化", "区分1-市場影響と約定の模型"]
NEG = re.compile(r"付けない|付けていない|付けなかった|付けず|入れない|外す|外した|"
                 r"決めていない|決めない|決めなかった|決まらなかった|可能性|"
                 r"当たらない|該当しない|未確認")
NEG_WIN = 24
CHAIN = re.compile(r"^(?:[\s`*]|と|、|・|および|区分1-[^\s`*、。]+)*")
BUNDLE = [(22, 52), (13, 123)]
# 中黒の箇条で書かれた候補の行(21 回目の「粒度が決まった 2 件」がこの形)。
BULLET = re.compile(r"^\s*[-*]\s+\*{0,2}`?(\d+)\s*番")
# 記載の中に出る「<数> 番」。自分以外の番号なら、その文の印は自分のものではない。
OTHER = re.compile(r"(\d+)\s*番")
# 到達の状態を表す語(規則 4)。True = 到達済みの側、False = まだ到達していない側。
REACH_WORDS = [("一次資料に未到達", False), ("未着手", False),
               ("判別に一次資料が要る", False), ("一次資料に到達", True),
               ("到達済み", True), ("到達の記録", True),
               ("[深掘り]", True), ("浅い", True)]
# 「`判別に一次資料が要る` を外す。」の形だけを打ち消しにする。
STATE_NEG = re.compile(r"^(?:[\s`*」』]|を)*(?:外す|外した|ではない|ではなく)")


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
        num = None
        if inside and re.match(r"^\s*\d+\.\s", ln):
            lead = re.split(r"[—–]", ln)[0]
            m = re.search(r"(\d+)\s*番", lead)
            num = int(m.group(1)) if m else int(re.match(r"^\s*(\d+)\.", ln).group(1))
        elif inside and BULLET.match(ln):
            num = int(BULLET.match(ln).group(1))
        if num is not None:
            body = [ln]
            j = i + 1
            while j < n and lines[j].startswith("   ") and lines[j].strip():
                body.append(lines[j])
                j += 1
            out.append((i + 1, num, " ".join(x.strip() for x in body)))
            i = j
            continue
        i += 1
    return out


def _other_candidate(body, start, own):
    """その語より前、同じ文の中に自分以外の候補の「<数> 番」が出ていれば True。"""
    if own is None:
        return False
    head = body[:start]
    head = head[head.rfind("。") + 1:]
    return any(int(x) != own for x in OTHER.findall(head))


def verdict(body, word, own=None):
    """その記載の中で、その語が最後に出たところの肯定 / 打ち消しを返す。無ければ None。"""
    last = None
    for m in re.finditer(re.escape(word), body):
        if _other_candidate(body, m.start(), own):
            continue
        tail = body[m.end():]
        cut = tail.find("。")
        if cut >= 0:
            tail = tail[:cut]
        rest = tail[CHAIN.match(tail).end():]
        last = not NEG.search(rest[:NEG_WIN])
    return last


def reach_of(body, own=None):
    """その記載から到達の状態を返す(規則 4)。書かれていなければ None。"""
    hits = []
    for word, side in REACH_WORDS:
        for m in re.finditer(re.escape(word), body):
            if any(m.start() >= s and m.end() <= e for s, e, _ in hits):
                continue
            if _other_candidate(body, m.start(), own):
                continue
            neg = bool(STATE_NEG.match(body[m.end():]))
            hits.append((m.start(), m.end(), (not side) if neg else side))
    if not hits:
        return None
    hits.sort()
    return hits[-1][2]


def marks(entries):
    """候補ごとの 6 要素の印と、到達の状態を決める。"""
    mk = {}
    reach = {}
    for _, num, body in entries:
        for e in ELEMS:
            v = verdict(body, e, num)
            if v is not None:
                mk.setdefault(num, {})[e] = v
        r = reach_of(body, num)
        if r is not None:
            reach[num] = r
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
        hits = [(e, verdict(body, e, cand)) for e in ELEMS
                if verdict(body, e, cand) is not None]
        if hits or reach_of(body, cand) is not None:
            print("報告 %d 行 : 到達=%s : %s" % (no, reach_of(body, cand), " ".join(
                "%s=%s" % (e, "肯定" if v else "打ち消し") for e, v in hits)))
            print("    %s" % body[:200])


def master_entries(lines):
    """今の番号体系の候補の記載だけ。1・2 回目の節(独自の番号)と「**限界:**」の注記を除く。"""
    heads = [i for i, l in enumerate(lines) if re.match(r"^## 区分\s*1", l)]
    third = next((i for i in heads if re.search(r"3 回目", lines[i])), 0)
    return [e for e in candidate_entries(lines)
            if e[0] > third and not re.match(r"^\s*\d+\.\s*\*\*限界", e[2])]


def pending_classification(lines):
    """最後の記載が `判別に一次資料が要る` のまま(外したとは書いていない)候補の番号。"""
    last = {}
    for ln, num, body in master_entries(lines):
        last[num] = body
    return sorted(n for n, b in last.items()
                  if "判別に一次資料が要る" in b
                  and not re.search(r"判別に一次資料が要る`?\s*を外|を外した", b))


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
    # 上の 3 段は報告書の文章(「尽きた」に数えないもの)から読んでいる = 報告の申告を数えているだけ。
    # 6 要素の印がまだ付いていない候補は「残り」の集合にそもそも入らないので、
    # **まだどの要素かを決めていない候補が、完了の数から見えなくなる**。2026-09-23、
    # 台帳を作ったリードが 8 件(45・50・94・110・111・112・117・118)をこれで見落としていたのを見つけた。
    # よって、候補ごとの**最後の記載**から機械で数える行を足す。1・2 回目の節(独自の番号体系)と
    # 「**限界:**」の注記は候補ではないので読まない。
    pend = pending_classification(lines)
    print("最後の記載が「判別に一次資料が要る」のまま(機械) = %d 件 : %s"
          % (len(pend), " ".join("%d 番" % n for n in pend) if pend else "なし"))
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
