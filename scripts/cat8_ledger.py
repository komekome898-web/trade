#!/usr/bin/env python3
"""道具サーベイ区分 8 の台帳 `docs/DATA/tools_catalog_cat8.tsv` を扱う道具。打つのはリードだけ。

使い方:
  python3 scripts/cat8_ledger.py add --name <名前> --route <発見の経路> --source <URL> [--cat1 <番号>] [--round <回>]
  python3 scripts/cat8_ledger.py sync <報告.md> --round <回> [--new <名前> ...]
  python3 scripts/cat8_ledger.py set <8-NNN> <列>=<値> [...]
  python3 scripts/cat8_ledger.py recount
  python3 scripts/cat8_ledger.py check [<報告.md>] [<生ログ.log> ...]
  python3 scripts/cat8_ledger.py check-elements <報告.md> --round <回>   (読むだけ。調査班も打つ)

規則の在処は設計票 `docs/DATA/surveys/CAT8_DESIGN.md`(§2 状態の語 / §3 要素の印 / §4.1 段 / §5 台帳の列と番号 /
§6 この道具の役目)。**数は報告の文章から数えない**(台帳から数える)。

番号(設計票 §5):
- 番号は `8-001` の形で、この道具だけが振る。調査班は報告で既存の候補を `(8-NNN)`、新しい候補を `(新)` と書く。
- 重複を拒む: 名前の正規形(NFKC・小文字・空白と - _ . を除く。**書かれたとおりの全体**を使い、`所有者/` を
  切らない)か、URL の正規形のどちらか一方でも既存の行と当たれば、足さずに止まる。**止まるだけで、まとめない。**
  名前だけが当たった別の道具は、リードが両方の出典を開いて別物と確かめたうえで `sync --new <名前>` で足す。
"""
import argparse, csv, pathlib, re, sys, unicodedata

REPO = pathlib.Path(__file__).resolve().parent.parent
LEDGER = REPO / "docs/DATA/tools_catalog_cat8.tsv"

ELEMS = ["E1a", "E1b", "E2", "E3a", "E3b", "E4", "E5", "E6"]
STAGES = ["段_" + e for e in ELEMS]
COLS = (["番号", "名前", "初出の回", "発見の経路", "発見の出典", "区分1の番号", "状態"] + ELEMS + STAGES
        + ["他の区分へ", "安全側の所見", "最後の記載の回", "最後の記載の行"])
STATES = ["未着手", "判別に一次資料が要る", "浅い", "深掘り", "危険で導入停止", "登録が要る", "区分8の要素なし"]
REMAINING = ["未着手", "判別に一次資料が要る", "浅い"]
ELEM_VALUES = ["印", "なし", "未判別"]
STAGE_VALUES = ["1", "2", "3", "4", "5", "未判別", "-"]
ROUTES = ["検索", "X", "GitHub・PyPI・公式", "一覧の辿り", "区分1から"]
LOG_HEAD = re.compile(r"^--- \S+ method=\S+ target=\S+ rc=\S+ time_s=\S+ note=")


def norm_name(n):
    return re.sub(r"[\s\-_.]", "", unicodedata.normalize("NFKC", n).lower())


def norm_url(u):
    u = unicodedata.normalize("NFKC", u.strip()).lower()
    u = re.sub(r"[#?].*$", "", u)
    u = re.sub(r"^[a-z]+://", "", u)
    u = re.sub(r"^www\.", "", u).rstrip("/")
    m = re.match(r"^(?:github\.com|ungh\.cc/repos|raw\.githubusercontent\.com)/([^/]+)/([^/]+)", u)
    if m:
        return "github:%s/%s" % (m.group(1), re.sub(r"\.git$", "", m.group(2)))
    m = re.match(r"^pypi\.org/(?:project|simple)/([^/]+)", u)
    if m:
        return "pypi:" + re.sub(r"[-_.]+", "-", m.group(1))
    m = re.match(r"^(?:x\.com|twitter\.com|fxtwitter\.com|api\.fxtwitter\.com)/[^/]+/status/(\d+)", u)
    if m:
        return "x:" + m.group(1)
    return u


def load():
    if not LEDGER.exists():
        return []
    with LEDGER.open(newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    return rows


def save(rows):
    with LEDGER.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})


def find_dup(rows, name, url):
    nn, nu = norm_name(name), (norm_url(url) if url else "")
    hits = []
    for r in rows:
        why = []
        if norm_name(r["名前"]) == nn:
            why.append("名前")
        if nu and r["発見の出典"] and norm_url(r["発見の出典"]) == nu:
            why.append("URL")
        if why:
            hits.append((r["番号"], r["名前"], "・".join(why)))
    return hits


def new_row(rows, name, route, source, cat1="", rnd=""):
    n = max([int(r["番号"].split("-")[1]) for r in rows] or [0]) + 1
    r = {c: "" for c in COLS}
    r.update({"番号": "8-%03d" % n, "名前": name, "初出の回": rnd, "発見の経路": route, "発見の出典": source,
              "区分1の番号": cat1, "状態": "未着手"})
    for e in ELEMS:
        r[e] = "未判別"
    for s in STAGES:
        r[s] = "未判別"
    return r


def cmd_add(a):
    rows = load()
    if a.route not in ROUTES:
        sys.exit("発見の経路は %s のどれか: %s" % (" / ".join(ROUTES), a.route))
    hits = find_dup(rows, a.name, a.source)
    if hits:
        for h in hits:
            print("重複の疑い(%s が当たった): %s %s" % (h[2], h[0], h[1]))
        sys.exit("足さずに止まった(設計票 §5)。別物と確かめたら sync --new で足す")
    r = new_row(rows, a.name, a.route, a.source, a.cat1 or "", a.round or "")
    rows.append(r)
    save(rows)
    print("足した: %s %s" % (r["番号"], r["名前"]))


def section(text, rnd):
    """報告から `## 区分8 — <回> 回目` の節を切り出す(次の `## 区分` まで)。行番号(1 始まり)も返す。"""
    lines = text.splitlines()
    st = None
    for i, ln in enumerate(lines):
        if re.match(r"^## 区分8 — %s 回目" % re.escape(str(rnd)), ln):
            st = i
        elif st is not None and re.match(r"^## 区分", ln):
            return st, i, lines
    return st, len(lines), lines


NEW_RE = re.compile(r"^\s*(?:\d+\.|[-*])\s*(?:\[深掘り\]\s*)?`([^`\n]+)`\s*\(新\)(.*)$")
URL_RE = re.compile(r"https?://[^\s)>|`]+")


def cmd_sync(a):
    rows = load()
    text = pathlib.Path(a.report).read_text()
    st, en, lines = section(text, a.round)
    if st is None:
        sys.exit("報告に `## 区分8 — %s 回目` の節が無い" % a.round)
    forced = set(a.new or [])
    stopped = 0
    for i in range(st, en):
        m = NEW_RE.match(lines[i])
        if not m:
            continue
        name, rest = m.group(1), m.group(2)
        um = URL_RE.search(rest)
        url = um.group(0) if um else ""
        if not url:
            print("行 %d: `新` の行に URL が無い: %s" % (i + 1, name))
            stopped += 1
            continue
        hits = find_dup(rows, name, url)
        if hits and name not in forced:
            for h in hits:
                print("行 %d: 重複の疑い(%s が当たった): `%s` と %s %s" % (i + 1, h[2], name, h[0], h[1]))
            stopped += 1
            continue
        route = "X" if norm_url(url).startswith("x:") else (
            "GitHub・PyPI・公式" if re.match(r"^(github|pypi):", norm_url(url)) else "検索")
        r = new_row(rows, name, route, url, "", str(a.round))
        r["最後の記載の回"], r["最後の記載の行"] = str(a.round), str(i + 1)
        rows.append(r)
        print("足した: %s `%s` (行 %d、経路 %s は URL から推した。直すなら set)" % (r["番号"], name, i + 1, route))
    save(rows)
    if stopped:
        sys.exit("止まった行 %d 件(足していない)" % stopped)


def cmd_set(a):
    rows = load()
    tgt = [r for r in rows if r["番号"] == a.num]
    if not tgt:
        sys.exit("台帳に無い番号: " + a.num)
    for kv in a.pairs:
        k, _, v = kv.partition("=")
        if k not in COLS or k == "番号":
            sys.exit("台帳の列ではない: " + k)
        tgt[0][k] = v
    save(rows)
    errs = check_rows([tgt[0]])
    for e in errs:
        print("注意: " + e)
    print("書いた: %s" % a.num)


def check_rows(rows):
    errs = []
    for r in rows:
        n = r["番号"]
        if r["状態"] not in STATES:
            errs.append("%s: 状態の語が語彙に無い: %s" % (n, r["状態"]))
        if r["発見の経路"] not in ROUTES:
            errs.append("%s: 発見の経路が語彙に無い: %s" % (n, r["発見の経路"]))
        for e, s in zip(ELEMS, STAGES):
            if r[e] not in ELEM_VALUES:
                errs.append("%s: %s の値が語彙に無い: %s" % (n, e, r[e]))
            if r[s] not in STAGE_VALUES:
                errs.append("%s: %s の値が語彙に無い: %s" % (n, s, r[s]))
            if r[e] == "印" and r[s] in ("-", ""):
                errs.append("%s: %s が印なのに段が無い" % (n, e))
            if r[e] == "なし" and r[s] != "-":
                errs.append("%s: %s がなしなのに段が %s" % (n, e, r[s]))
            if r[e] == "未判別" and r[s] != "未判別":
                errs.append("%s: %s が未判別なのに段が %s" % (n, e, r[s]))
        if r["状態"] == "深掘り" and any(r[e] == "未判別" for e in ELEMS):
            errs.append("%s: 深掘りなのに未判別の要素がある(設計票 §2)" % n)
        if r["状態"] == "区分8の要素なし" and any(r[e] != "なし" for e in ELEMS):
            errs.append("%s: 区分8の要素なしなのに なし でない要素がある(設計票 §3)" % n)
    seen = {}
    for r in rows:
        k = norm_name(r["名前"])
        if k in seen:
            errs.append("%s と %s: 名前の正規形が同じ(%s)" % (seen[k], r["番号"], k))
        seen[k] = r["番号"]
    return errs


def cmd_check(a):
    rows = load()
    errs = check_rows(rows)
    nums = {r["番号"] for r in rows}
    if a.report:
        text = pathlib.Path(a.report).read_text()
        lines = text.splitlines()
        cited = set(re.findall(r"\((8-\d{3})\)", text))
        for c in sorted(cited - nums):
            errs.append("報告に台帳に無い番号がある: " + c)
        appeared = set(cited)
        for i, ln in enumerate(lines, 1):
            m = NEW_RE.match(ln)
            if not m:
                continue
            hits = find_dup(rows, m.group(1), "")
            if not hits:
                errs.append("報告の `新` で台帳に入っていない: 行 %d `%s`(sync を打つ)" % (i, m.group(1)))
            appeared.update(h[0] for h in hits)
        for n in sorted(nums - appeared):
            errs.append("台帳の行が報告に 1 度も出ない: " + n)
        for r in rows:
            ln = r["最後の記載の行"]
            if ln and not (ln.isdigit() and 1 <= int(ln) <= len(lines)):
                errs.append("%s: 最後の記載の行 %s が報告に無い" % (r["番号"], ln))
    for lg in a.logs:
        for i, ln in enumerate(pathlib.Path(lg).read_text(errors="replace").splitlines(), 1):
            if ln.startswith("---") and not LOG_HEAD.match(ln):
                errs.append("%s:%d: 生ログの見出しの形が違う: %s" % (lg, i, ln[:80]))
    for e in errs:
        print(e)
    print("---- 合計 %d 件" % len(errs))
    sys.exit(1 if errs else 0)


EVIDENCE_KINDS = ["一次資料", "実測", "推定", "仮定", "未確認"]


def cells(ln):
    return [c.strip() for c in re.split(r"(?<!\\)\|", ln.strip().strip("|"))]


def cmd_check_elements(a):
    """報告の `### 要素と段` の表(道具 | 要素 | 値 | 段 | 根拠の種類 | 根拠)を検査する。読むだけ。
    受け入れ検査 check_scan_report.py はこの 6 列の表を読まない(監査 8 回目の指摘 3)ので、ここで見る。"""
    text = pathlib.Path(a.report).read_text()
    st, en, lines = section(text, a.round)
    if st is None:
        sys.exit("報告に `## 区分8 — %s 回目` の節が無い" % a.round)
    errs, names, table, in_tab, in_list = [], [], {}, False, False
    cand_re = re.compile(r"^\s*(?:\d+\.|[-*])\s*(?:\[深掘り\]\s*)?`([^`\n]+)`\s*\((8-\d{3}|新)\)")
    for i in range(st, en):
        ln = lines[i]
        if re.match(r"^#{2,4} ", ln):
            in_list = bool(re.match(r"^#{2,4} *候補の一覧", ln))
            in_tab = bool(re.match(r"^#{2,4} *要素と段", ln))
            continue
        if in_list:
            m = cand_re.match(ln)
            if m:
                names.append(m.group(1))
                if not re.search(r"状態:\s*(%s)" % "|".join(map(re.escape, STATES)), ln):
                    errs.append("行 %d: 候補の一覧の行に設計票 §2 の状態が無い: `%s`" % (i + 1, m.group(1)))
            elif re.match(r"^\s*(?:\d+\.|[-*])\s*(?:\[深掘り\]\s*)?`", ln):
                errs.append("行 %d: 候補の一覧の行に (8-NNN) か (新) が無い: %s" % (i + 1, ln.strip()[:60]))
        if in_tab and ln.strip().startswith("|"):
            c = cells(ln)
            if len(c) != 6 or c[0] in ("道具", "") or set(c[0]) <= set("-: "):
                continue
            tool, el, val, stg, kind, ev = c
            tool = tool.strip("`")
            table.setdefault(tool, {})
            if el in table[tool]:
                errs.append("行 %d: %s の %s が 2 行ある" % (i + 1, tool, el))
            table[tool][el] = (i + 1, val, stg)
            if el not in ELEMS:
                errs.append("行 %d: 要素の語が 8 列に無い: %s" % (i + 1, el))
            if val not in ELEM_VALUES:
                errs.append("行 %d: 値が 印/なし/未判別 でない: %s" % (i + 1, val))
            want = {"印": [v for v in STAGE_VALUES if v != "-"], "なし": ["-"], "未判別": ["未判別"]}.get(val, [])
            if want and stg not in want:
                errs.append("行 %d: %s %s は値 %s なので段は %s のどれか(書かれた段: %s)" % (
                    i + 1, tool, el, val, "/".join(want), stg))
            if kind not in EVIDENCE_KINDS:
                errs.append("行 %d: 根拠の種類が委任文 §4.1 の 5 語でない: %s" % (i + 1, kind))
            if not ev:
                errs.append("行 %d: 根拠が空: %s %s" % (i + 1, tool, el))
    for n in names:
        got = table.get(n, {})
        miss = [e for e in ELEMS if e not in got]
        if miss:
            errs.append("候補 `%s` の「要素と段」の行が欠けている: %s" % (n, " ".join(miss)))
    for t in table:
        if t not in names:
            errs.append("「要素と段」の表の道具が候補の一覧に無い(名前が 1 文字違う?): `%s`" % t)
    print("読んだもの: 候補の一覧 %d 行 / 要素と段の表 %d 行(道具 %d)" % (
        len(names), sum(len(v) for v in table.values()), len(table)))
    for e in errs:
        print(e)
    print("---- 合計 %d 件" % len(errs))
    sys.exit(1 if errs else 0)


def cmd_recount(a):
    rows = load()
    print("== 台帳の全行(母集合) = %d 行" % len(rows))
    print("== 状態ごと")
    for s in STATES:
        ns = [r["番号"] for r in rows if r["状態"] == s]
        print("%s = %d : %s" % (s, len(ns), " ".join(ns)))
    rem = [r["番号"] for r in rows if r["状態"] in REMAINING]
    print("== 残り(未着手・判別に一次資料が要る・浅い) = %d : %s" % (len(rem), " ".join(rem)))
    print("== 要素ごと(印 / なし / 未判別)と、印の段の分布")
    for e, s in zip(ELEMS, STAGES):
        cnt = {v: [r["番号"] for r in rows if r[e] == v] for v in ELEM_VALUES}
        dist = {v: sum(1 for r in rows if r[e] == "印" and r[s] == v) for v in STAGE_VALUES if v != "-"}
        print("%s: 印 %d / なし %d / 未判別 %d | 段 %s | 印の番号: %s" % (
            e, len(cnt["印"]), len(cnt["なし"]), len(cnt["未判別"]),
            " ".join("%s=%d" % kv for kv in dist.items()), " ".join(cnt["印"])))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("add"); p.add_argument("--name", required=True); p.add_argument("--route", required=True)
    p.add_argument("--source", required=True); p.add_argument("--cat1"); p.add_argument("--round")
    p = sp.add_parser("sync"); p.add_argument("report"); p.add_argument("--round", required=True)
    p.add_argument("--new", action="append")
    p = sp.add_parser("set"); p.add_argument("num"); p.add_argument("pairs", nargs="+")
    sp.add_parser("recount")
    p = sp.add_parser("check"); p.add_argument("report", nargs="?"); p.add_argument("logs", nargs="*")
    p = sp.add_parser("check-elements"); p.add_argument("report"); p.add_argument("--round", required=True)
    a = ap.parse_args()
    {"add": cmd_add, "sync": cmd_sync, "set": cmd_set, "recount": cmd_recount, "check": cmd_check,
     "check-elements": cmd_check_elements}[a.cmd](a)


if __name__ == "__main__":
    main()
