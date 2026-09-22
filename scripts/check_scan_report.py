#!/usr/bin/env python3
"""調査報告の保存前検査。監査で実際に出た指摘の型を、1 件につき 1 つの検査にしたもの。

使い方: python3 scripts/check_scan_report.py <報告.md> <生ログ.log> [<生ログ.log> ...]
終了コード: 0 = 全検査が 0 件 / 1 = どれかが当たった(当たった行を全部出す)

各検査の見出しに、それを生んだ監査の回を書いてある。検査は足すだけで、外さない。
"""
import re, sys, pathlib, unicodedata, collections

Z2H = str.maketrans("（）［］｛｝", "()[]{}")

def bold_spans(line):
    pos = [m.start() for m in re.finditer(r"\*\*", line)]
    return pos

def paragraphs(lines):
    """空行で区切った塊に畳む。折り返した文で括弧・太字が行をまたぐため(検査の誤検出 9 件の原因)。"""
    out, buf, start = [], [], 1
    for i, ln in enumerate(lines, 1):
        if ln.strip():
            if not buf: start = i
            buf.append(ln)
        elif buf:
            out.append((start, " ".join(buf))); buf = []
    if buf: out.append((start, " ".join(buf)))
    return out

def check_bold(lines):
    """太字(2 回目の監査 13・14 回目)。奇数個 / 入れ子の 2 つの形。"""
    out = []
    for i, ln in paragraphs(lines):
        p = bold_spans(ln)
        if len(p) % 2:
            out.append((i, "太字 ** の数が奇数 (%d 個)" % len(p))); continue
        for a, b in zip(p[0::2], p[1::2]):
            body = ln[a+2:b]
            if body != body.strip():
                out.append((i, "太字の内側が空白で始まる/終わる: %r" % body[:40]))
            elif not re.search(r"[0-9A-Za-z぀-ヿ一-鿿]", body):
                out.append((i, "太字の中身が記号だけ: %r" % body[:40]))
    return out

def check_brackets(lines):
    """括弧の対応(15 回目)。全角を半角に直してから数える(混在は誤検出の元)。"""
    out = []
    for i, ln in paragraphs(lines):
        s = ln.translate(Z2H)
        for o, c, name in [("(", ")", "丸括弧"), ("[", "]", "大括弧"), ("「", "」", "鉤括弧")]:
            if s.count(o) != s.count(c):
                out.append((i, "%s の数が合わない (%d 対 %d)" % (name, s.count(o), s.count(c))))
    return out

def check_sections(text, section_head=None):
    """委任文 §11 が要求する節の存在(8 回目 = 2 回目の節に知見・出典が丸ごと無かった)。

    区分の節ごとに、その節の中だけを見る。前の版では固定の見出し文字列で分割しようとして
    一度も一致せず、文書全体を見て常に通っていた(= 落ちない検査)。区分の見出しを正規表現で
    拾う形に直した。
    """
    need = ["検索計画", "出典", "知見", "候補の一覧", "ツール1件ごとの表", "予算"]
    lines = text.splitlines()
    heads = [i for i, ln in enumerate(lines) if re.match(r"^## 区分\s*\d", ln)]
    out = []
    for k, start in enumerate(heads):
        end = heads[k + 1] if k + 1 < len(heads) else len(lines)
        body = "\n".join(lines[start:end])
        title = lines[start][:40]
        for n in need:
            if not re.search(r"^#{3,4} *" + re.escape(n), body, re.M):
                out.append((start + 1, "節『%s…』に必須の小節が無い: %s" % (title, n)))
    return out

def num_in_log(num, log):
    """生ログの数値と丸めを許して突き合わせる(60.286559606 → 60.29 は一致とみなす)。
    生ログは先頭の 0 を省く書き方(.835891471)をするので、取り出しの正規表現もそれに合わせる。"""
    if num in log:
        return True
    try:
        v = float(num)
    except ValueError:
        return False
    d = len(num.split(".")[1]) if "." in num else 0
    for m in re.finditer(r"\d*\.\d+|\d+", log):
        try:
            if round(float(m.group()), d) == v:
                return True
        except ValueError:
            pass
    return False

def check_numbers_in_log(lines, log):
    """本文の数値が生ログに在るか(10・11・12 回目 = 所要時間・依存数の食い違い)。"""
    out = []
    pat = re.compile(r"(\d+(?:\.\d+)?)\s*(秒|個|パッケージ)")
    for i, ln in enumerate(lines, 1):
        if not re.search(r"install|導入|依存", ln) or "ハーネス" in ln:
            continue
        for num, unit in pat.findall(ln):
            if not num_in_log(num, log):
                out.append((i, "生ログに無い数値: %s %s" % (num, unit)))
    return out

def tool_names(lines):
    """道具名は表の 1 列目と候補の一覧から取る(直書きしない)。
    監査の指摘 5: 区分 1 の固有名詞を直書きしていたため、他の区分では値の食い違いの検査が当たらなかった。"""
    names = {c[0] for _, c in read_table(lines)}
    for ln in lines:
        m = re.match(r"^\s*(?:\d+\.|[-*])\s*(?:\[深掘り\]\s*)?([A-Za-z][A-Za-z0-9_.+-]{2,})", ln)
        if m:
            names.add(m.group(1))
    return sorted(n for n in names if len(n) >= 3)

def check_conflicting_values(lines):
    """同じ道具・同じ単位に別の値(12 回目 = Qlib 185/130、11 回目 = Jesse 60/19.49)。"""
    tools = tool_names(lines)
    seen = collections.defaultdict(set)
    pat = re.compile(r"(\d+(?:\.\d+)?)\s*(秒|個|パッケージ)")
    # §4.0 の表の行は、単位ではなく**項目**で束ねる。単位で束ねると
    # 「install所要秒 2 秒」と「規模の見積の中の 1.3 秒」が食い違い扱いになった
    # (2026-09-22 区分 1 の 4 回目、調査班が自分で閉じずに残した 2 件目)。
    rowitem = {i: c[1] for i, c in read_table(lines)}
    for i, ln in enumerate(lines, 1):
        hit = [t for t in tools if t.lower() in ln.lower()]
        if len(hit) > 2:
            continue
        for t in hit:
            for num, unit in pat.findall(ln):
                seen[(t, rowitem.get(i, unit))].add((num, i))
    out = []
    for (t, key), vals in sorted(seen.items()):
        nums = {v[0] for v in vals}
        if len(nums) > 1:
            out.append((min(v[1] for v in vals), "%s の %s に別の値: %s" % (t, key, sorted(nums))))
    return out

def check_contradiction(lines):
    """同じ道具で「未実施/未確認」と「実測/実施」が同居(2〜4 回目。同じ型が 4 回続いた)。"""
    tools = tool_names(lines)
    neg, pos = collections.defaultdict(list), collections.defaultdict(list)
    for i, ln in enumerate(lines, 1):
        if "wheel" not in ln and "setup.py" not in ln:
            continue
        hit = [t for t in tools if t.lower() in ln.lower()]
        if len(hit) > 2:
            continue
        for t in hit:
            if True:
                (neg if re.search(r"未実施|未確認", ln) else pos)[t].append(i)
    return [(min(neg[t]), "%s: wheel/setup.py が「未実施・未確認」と「実施済み」の両方にある (行 %s / %s)"
             % (t, neg[t], pos[t])) for t in sorted(neg) if t in pos]

ITEMS = ["版", "最終更新日", "ライセンス", "言語と動作環境", "対応取引所", "星", "コミット数",
         "保守者数", "週DL数", "初回公開日", "既知の脆弱性", "料金体系", "無料枠の上限",
         "課金開始条件", "隠れた依存", "登録の要否", "到達経路", "導入可否", "install所要秒",
         "依存数", "pip check", "最小実行の可否", "最小実行の中身", "実行所要秒", "wheel展開",
         "setup.py導入時実行", "同梱バイナリ", "外部送信", "自動発注機能", "宣伝詐欺の兆候",
         "当方データ投入", "時刻の扱い", "再現性", "規模の見積",
         "配布元の一致", "難読化", "外部URL取得", "依存の一覧", "保守者名の一貫性",
         "4軸1_道具", "4軸2_情報", "4軸3_視点", "4軸4_向上"]
MARKS = ["一次資料", "実測", "推定", "仮定", "未確認"]

def norm_name(x):
    """道具名の表記ゆれを 1 箇所で吸収する。エスケープした縦棒、バッククォート、前後の空白。
    委任文の監査 4 回目の指摘 1・3・6: 表記の違いで同じ道具が別物になっていた。"""
    return x.replace("\\|", "|").strip().strip("`").strip()


def marked_names(lines):
    """候補の一覧で [深掘り] と印を付けた道具名。改行を越えない(指摘 2 の閉じ忘れ対策)。"""
    body = "\n".join(lines)
    return [norm_name(m.group(1)) for m in
            re.finditer(r"^\s*(?:\d+\.|[-*])\s*\[深掘り\]\s*`([^`\n]+)`", body, re.M)]


def read_table(lines):
    """委任文 §4.0 の「道具 | 項目 | 値 | 印 | 根拠」の行を集める。"""
    rows = []
    for i, ln in enumerate(lines, 1):
        raw = ln.strip().replace("\\|", "\x00")   # `\|` は名前の一部なので退避(指摘 1)
        c = [x.strip().replace("\x00", "|") for x in raw.strip("|").split("|")] if raw.startswith("|") else []
        if len(c) == 5 and c[1] in ITEMS:
            c[0] = norm_name(c[0])
            rows.append((i, c))
    return rows

def check_table_complete(lines):
    """深掘りした道具が語彙のすべての項目の行を持つか(監査 1 回目 = 危険検査の 3 項目が全候補で欠落)。"""
    rows = read_table(lines)
    if not rows:
        return [(0, "§4.0 の機械可読の表が 1 行も無い(2026-09-22 版の委任文では必須)")]
    # 名前は必ずバッククォートで囲ませる。区切り記号を足していく直し方は 3 回続けて
    # 偽陽性を生んだ(括弧・全角括弧・パイプが名前の一部になりうる)ので、曖昧さの元を断った。
    body = "\n".join(lines)
    marked = marked_names(lines)
    bad = [(i + 1, "候補の一覧の [深掘り] の道具名がバッククォートで囲まれていない: " + ln.strip()[:60])
           for i, ln in enumerate(lines, 1)
           if re.match(r"^\s*(?:\d+\.|[-*])\s*\[深掘り\]", ln) and not re.search(r"\[深掘り\]\s*`[^`]+`", ln)]
    have = {}
    for i, c in rows:
        have.setdefault(c[0], set()).add(c[1])
    out = list(bad)
    for m in marked:
        if m not in have:
            out.append((0, "候補の一覧で [深掘り] と印を付けた道具が表に 1 行も無い: " + m))
    for tool, got in sorted(have.items()):
        miss = [x for x in ITEMS if x not in got]
        if miss:
            out.append((rows[0][0], "%s: 表に無い項目 %d 件 (%s%s)"
                        % (tool, len(miss), "、".join(miss[:4]), " ほか" if len(miss) > 4 else "")))
    return out

def check_table_marks(lines):
    """印が 5 語のどれかで、根拠が空でないか(監査 1・10 回目 = 印の誤用)。"""
    out = []
    for i, c in read_table(lines):
        if c[3] not in MARKS:
            out.append((i, "印が語彙にない: %r (%s / %s)" % (c[3], c[0], c[1])))
        if not c[4]:
            out.append((i, "根拠が空: %s / %s" % (c[0], c[1])))
    return out

def check_prose_vs_table(lines):
    """文章の数値が表にあるか(監査 10〜12 回目 = 表に無い数字を文章で作る)。"""
    rows = read_table(lines)
    if not rows:
        return []
    vals = " ".join(c[2] for _, c in rows)
    tbl_lines = {i for i, _ in rows}
    out = []
    pat = re.compile(r"(\d+(?:\.\d+)?)\s*(秒|個|パッケージ)")
    for i, ln in enumerate(lines, 1):
        if i in tbl_lines:
            continue
        for num, unit in pat.findall(ln):
            if num not in vals:
                out.append((i, "表に無い数値を文章で書いている: %s %s" % (num, unit)))
    return out

def check_heading_counts(lines):
    """見出しやラベルの「(N 件)」と直後の列挙の数の不一致(監査 1・3・5・6・7 回目、非数値の型)。"""
    out = []
    for i, ln in enumerate(lines):
        if not (ln.startswith("#") or ln.strip().startswith("**")):
            continue
        m = re.search(r"[(（](\d+)\s*件[)）]", ln)
        if not m:
            continue
        want, n, j = int(m.group(1)), 0, i + 1
        while j < len(lines) and lines[j].strip():
            if re.match(r"^\s*(?:\d+\.|[-*])\s", lines[j]):
                n += 1
            j += 1
        if n and n != want:
            out.append((i + 1, "見出しは %d 件と書いているが、直後の列挙は %d 件" % (want, n)))
    return out


def check_measured_evidence(lines, logs):
    """実測の根拠が実在し、背景起動でないか(監査の止める 1 = 出力を読まずに実測と書いた型)。"""
    out = []
    for i, c in read_table(lines):
        if c[3] != "実測":
            continue
        m = re.match(r"([\w./-]+\.log):(\d+)", c[4])
        if not m:
            out.append((i, "実測なのに根拠が <生ログ>:<行番号> の形でない: %s / %s = %r" % (c[0], c[1], c[4])))
            continue
        name, no = m.group(1).split("/")[-1], int(m.group(2))
        if name not in logs:
            out.append((i, "根拠が指す生ログが渡されていない: " + name)); continue
        body = logs[name]
        if no < 1 or no > len(body):
            out.append((i, "根拠の行が生ログに存在しない: %s:%d (全 %d 行)" % (name, no, len(body)))); continue
        src = body[no - 1]
        if "started pid=" in src or ("rc=" not in src and "time_s=" not in src):
            out.append((i, "根拠の行が実行の結果になっていない(背景起動・未読の疑い): %s:%d %r"
                        % (name, no, src[:60])))
    return out


def check_checker_output_pasted(text, computed):
    """報告に受け入れ検査の出力の節があり、貼られた合計がいま計算した合計と一致するか。

    節の有無だけを見ていたときは、検査を 1 度も打たずに「すべて 0 件」と書いた偽の出力でも通った
    (委任文の監査 3 回目の指摘 2)。貼り付けの真正性を、こちらで数え直した値との一致で見る。
    """
    if not re.search(r"^#{2,4} *受け入れ検査の出力", text, re.M):
        return [(0, "報告に「受け入れ検査の出力」の節が無い(検査の出力全文を貼ること)")]
    m = re.findall(r"----\s*検査対象の合計\s*(\d+)\s*件", text)
    if not m:
        return [(0, "貼られた出力に「---- 検査対象の合計 N 件」の行が無い(全文をそのまま貼ること)")]
    pasted = int(m[-1])
    if pasted != computed:
        return [(0, "貼られた出力の合計 %d 件が、いま数え直した %d 件と合わない(打ち直して貼ること)"
                 % (pasted, computed))]
    return []

def check_hollow(lines):
    """深掘りと書いた道具の中身が実質空でないか(委任文の監査 4 回目の指摘 4)。

    全項目を「未確認」+ 定型文の根拠で埋めた報告が K1〜K12 を 0 件で通り抜けた。
    オーナー逐語 L-379「エラー出た瞬間弾くんやろ…全部無理で始めて諦めるような委任文にしないと
    意味ない」が防ごうとした「浅く終わらせて逃げる」が、機械では見えないまま通っていた。
    """
    rows = read_table(lines)
    if not rows:
        return []
    marked, by = set(marked_names(lines)), {}
    for i, c in rows:
        by.setdefault(c[0], []).append((i, c))
    out = []
    for tool, rs in sorted(by.items()):
        unk = [c for _, c in rs if c[3] == "未確認"]
        if tool in marked and len(unk) * 2 > len(rs):
            out.append((rs[0][0], "%s は [深掘り] と印を付けているが、表の %d/%d 行が「未確認」"
                        "(深掘りでないなら候補の一覧で「浅い」と書く)" % (tool, len(unk), len(rs))))
        srcs = [c[4] for _, c in rs if c[4]]
        for u in set(srcs):
            if srcs.count(u) > 5:
                out.append((rs[0][0], "%s の根拠が %d 行で同じ文言の複写: %r"
                            % (tool, srcs.count(u), u[:40])))
    return out


def scope(lines):
    """検査の対象にする行だけを残し、他は空行にする(行番号を保つため消さずに空にする)。

    外すもの 2 つ。どちらも 2026-09-22 の区分 1 の 3 回目で調査班が見つけて、自分で閉じずに
    リードに渡してきたもの(委任文 §12 の「誤検出は自分で閉じない」が働いた最初の例)。
      (a) 「受け入れ検査の出力」の節。検査の出力を貼ると、その中の数値が K9 に当たり、
          貼るたびに合計が増えて「貼った合計 = 数え直した合計」になる状態が存在しなくなる。
      (b) §4.0 の表を持たない区分の節。表が要るようになる前に書かれた節なので、
          表を前提にした検査(K4・K5・K9・K13)を当てても直しようがない。
    """
    heads = [i for i, ln in enumerate(lines) if re.match(r"^## 区分\s*\d", ln)] or [0]
    keep = [False] * len(lines)
    for k, st in enumerate(heads):
        en = heads[k + 1] if k + 1 < len(heads) else len(lines)
        # 「表がある」は §4.0 の表の行(2 列目が語彙の項目)が在ることで判定する。
        # 列の数だけで見ると、他の 5 列の表(X の投稿など)を持つ節まで対象に入る。
        if read_table(lines[st:en]):
            for j in range(st, en):
                keep[j] = True
    drop = False
    for i, ln in enumerate(lines):
        if re.match(r"^#{2,4} *受け入れ検査の出力", ln):
            drop = True
        elif re.match(r"^#{1,4} ", ln):
            drop = False
        if drop:
            keep[i] = False
    return [ln if keep[i] else "" for i, ln in enumerate(lines)]


def main():
    if len(sys.argv) < 3:
        print(__doc__); return 2
    rep = pathlib.Path(sys.argv[1]); text = rep.read_text(); raw_lines = text.splitlines()
    lines = raw_lines if "--all" in sys.argv else scope(raw_lines)
    logs = {pathlib.Path(q).name: pathlib.Path(q).read_text(errors="replace").splitlines()
            for q in sys.argv[2:]}
    log = "\n".join("\n".join(v) for v in logs.values())
    checks = [("K1 太字", check_bold(lines)), ("K2 括弧", check_brackets(lines)),
              ("K3 必須の節", check_sections(text)),
              ("K4 生ログに無い数値", check_numbers_in_log(lines, log)),
              ("K5 同じ道具に別の値", check_conflicting_values(lines)),
              ("K6 未実施と実測の同居", check_contradiction(lines)),
              ("K7 表の項目の欠落", check_table_complete(lines)),
              ("K8 表の印と根拠", check_table_marks(lines)),
              ("K9 表に無い数値", check_prose_vs_table(lines)),
              ("K10 見出しの件数", check_heading_counts(lines)),
              ("K11 実測の根拠", check_measured_evidence(lines, logs)),
              ("K13 中身が実質空", check_hollow(lines)),
              ]
    checks.append(("K12 検査の出力の貼付",
                   check_checker_output_pasted(text, sum(len(h) for _, h in checks))))
    bad = 0
    for name, hits in checks:
        print("%-22s %d 件" % (name, len(hits)))
        for i, msg in hits:
            print("    %s:%d  %s" % (rep, i, msg))
        bad += len(hits)
    print("---- 検査対象の合計 %d 件(K12 を除く。貼り付けはこの数で照合する)"
          % sum(len(h) for n, h in checks if not n.startswith("K12")))
    print("---- 合計 %d 件" % bad)
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
