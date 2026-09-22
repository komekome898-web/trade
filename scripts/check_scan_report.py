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
    """K1 太字(2 回目の監査 13・14 回目)。奇数個 / 入れ子の 2 つの形。"""
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
    """K2 括弧の対応(15 回目)。全角を半角に直してから数える(混在は誤検出の元)。"""
    out = []
    for i, ln in paragraphs(lines):
        s = ln.translate(Z2H)
        for o, c, name in [("(", ")", "丸括弧"), ("[", "]", "大括弧"), ("「", "」", "鉤括弧")]:
            if s.count(o) != s.count(c):
                out.append((i, "%s の数が合わない (%d 対 %d)" % (name, s.count(o), s.count(c))))
    return out

def check_sections(text, section_head=None):
    """K3 委任文 §11 が要求する節の存在(8 回目 = 2 回目の節に知見・出典が丸ごと無かった)。

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
    """K4 本文の数値が生ログに在るか(10・11・12 回目 = 所要時間・依存数の食い違い)。"""
    out = []
    pat = re.compile(r"(\d+(?:\.\d+)?)\s*(秒|個|パッケージ)")
    for i, ln in enumerate(lines, 1):
        if not re.search(r"install|導入|依存", ln) or "ハーネス" in ln:
            continue
        for num, unit in pat.findall(ln):
            if not num_in_log(num, log):
                out.append((i, "生ログに無い数値: %s %s" % (num, unit)))
    return out

def check_conflicting_values(lines):
    """K6 同じ道具・同じ単位に別の値(12 回目 = Qlib 185/130、11 回目 = Jesse 60/19.49)。"""
    tools = ["hftbacktest", "NautilusTrader", "vectorbt", "freqtrade", "Backtesting.py",
             "zipline", "QSTrader", "Lean", "PyAlgoTrade", "Qlib", "VnPy", "Jesse", "ccxt"]
    seen = collections.defaultdict(set)
    pat = re.compile(r"(\d+(?:\.\d+)?)\s*(秒|個|パッケージ)")
    for i, ln in enumerate(lines, 1):
        hit = [t for t in tools if t.lower() in ln.lower()]
        if len(hit) > 2:
            continue
        for t in hit:
            if True:
                for num, unit in pat.findall(ln):
                    seen[(t, unit)].add((num, i))
    out = []
    for (t, unit), vals in sorted(seen.items()):
        nums = {v[0] for v in vals}
        if len(nums) > 1:
            out.append((min(v[1] for v in vals), "%s の %s に別の値: %s" % (t, unit, sorted(nums))))
    return out

def check_contradiction(lines):
    """K7 同じ道具で「未実施/未確認」と「実測/実施」が同居(2〜4 回目。同じ型が 4 回続いた)。"""
    tools = ["hftbacktest", "NautilusTrader", "zipline", "QSTrader", "PyAlgoTrade",
             "Qlib", "VnPy", "Jesse", "Backtesting.py", "Lean"]
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
         "4軸1_道具", "4軸2_情報", "4軸3_視点", "4軸4_向上"]
MARKS = ["一次資料", "実測", "推定", "仮定", "未確認"]

def read_table(lines):
    """委任文 §4.0 の「道具 | 項目 | 値 | 印 | 根拠」の行を集める。"""
    rows = []
    for i, ln in enumerate(lines, 1):
        c = [x.strip() for x in ln.strip().strip("|").split("|")] if ln.strip().startswith("|") else []
        if len(c) == 5 and c[1] in ITEMS:
            rows.append((i, c))
    return rows

def check_table_complete(lines):
    """K8 深掘りした道具が 37 項目すべての行を持つか(監査 1 回目 = 危険検査の 3 項目が全候補で欠落)。"""
    rows = read_table(lines)
    if not rows:
        return [(0, "§4.0 の機械可読の表が 1 行も無い(2026-09-22 版の委任文では必須)")]
    have = {}
    for i, c in rows:
        have.setdefault(c[0], set()).add(c[1])
    out = []
    for tool, got in sorted(have.items()):
        miss = [x for x in ITEMS if x not in got]
        if miss:
            out.append((rows[0][0], "%s: 表に無い項目 %d 件 (%s%s)"
                        % (tool, len(miss), "、".join(miss[:4]), " ほか" if len(miss) > 4 else "")))
    return out

def check_table_marks(lines):
    """K9 印が 5 語のどれかで、根拠が空でないか(監査 1・10 回目 = 印の誤用)。"""
    out = []
    for i, c in read_table(lines):
        if c[3] not in MARKS:
            out.append((i, "印が語彙にない: %r (%s / %s)" % (c[3], c[0], c[1])))
        if not c[4]:
            out.append((i, "根拠が空: %s / %s" % (c[0], c[1])))
    return out

def check_prose_vs_table(lines):
    """K10 文章の数値が表にあるか(監査 10〜12 回目 = 表に無い数字を文章で作る)。"""
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

def main():
    if len(sys.argv) < 3:
        print(__doc__); return 2
    rep = pathlib.Path(sys.argv[1]); text = rep.read_text(); lines = text.splitlines()
    log = "".join(pathlib.Path(p).read_text(errors="replace") for p in sys.argv[2:])
    checks = [("K1 太字", check_bold(lines)), ("K2 括弧", check_brackets(lines)),
              ("K3 必須の節", check_sections(text, "## 区分 1(2 回目")),
              ("K4 生ログに無い数値", check_numbers_in_log(lines, log)),
              ("K6 同じ道具に別の値", check_conflicting_values(lines)),
              ("K7 未実施と実測の同居", check_contradiction(lines)),
              ("K8 表の項目の欠落", check_table_complete(lines)),
              ("K9 表の印と根拠", check_table_marks(lines)),
              ("K10 表に無い数値", check_prose_vs_table(lines))]
    bad = 0
    for name, hits in checks:
        print("%-22s %d 件" % (name, len(hits)))
        for i, msg in hits:
            print("    %s:%d  %s" % (rep, i, msg))
        bad += len(hits)
    print("---- 合計 %d 件" % bad)
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
