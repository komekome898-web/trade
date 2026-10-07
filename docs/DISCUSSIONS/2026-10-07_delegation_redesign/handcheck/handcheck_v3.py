"""使い捨ての手の検め(3.1 版目)。v2 の穴(引用を OWNER_LOG の行全体と比べ、読みの列に当たっても通した)を直した。
引用は 1 列目がちょうどその番号の行の 4 列目だけと比べる。パスは「/ を含む ASCII の語」+ :行。封印・根の外・ふつうのファイルを触る前に見る。"""
import hashlib, os, re, sys
from pathlib import Path

root = Path(".")
p = sys.argv[1]
b = Path(p).read_bytes(); t = b.decode("utf-8"); L = t.split("\n")


def secs(t):
    out = {}; cur = None
    for l in t.split("\n"):
        if l.startswith("## "): cur = l[3:].strip(); out[cur] = []
        elif cur is not None: out[cur].append(l)
    return out


def cells(line):
    out = []; cur = ""; inb = False
    for ch in line.strip().strip("|"):
        if ch == "`": inb = not inb
        if ch == "|" and not inb: out.append(cur.strip()); cur = ""
        else: cur += ch
    out.append(cur.strip()); return out


S = secs(t)
print("1 種類:", [i + 1 for i, l in enumerate(L[:5]) if l.startswith("種類: ")])
need = ["着手前の表", "目的(オーナーの逐語)", "読んだ事実", "決めてよいこと・決めてはいけないこと", "変えないもの", "決まった制約",
        "終わる条件と上限", "報告", "壊す場面", "受け入れ", "変異の表"]
print("2 欠けた見出し:", [n for n in need if n not in S])
NUM = r"L-(?:\d{3}[a-z]?|D\d{2})"
rows = {}
for l in Path("docs/OWNER_LOG.md").read_text(encoding="utf-8").split("\n"):
    if not l.startswith("|"): continue
    c = cells(l)
    if len(c) >= 4 and re.fullmatch(NUM, c[0]): rows.setdefault(c[0], []).append(c[3])
n = lambda x: re.sub(r"\s+", " ", x)
Q = r"「\*\*((?:(?!\*\*).)+?)\*\*」"
bad = []; cnt = 0; nonum = []; cur = None
for l in L:
    if l.startswith("## "): cur = l[3:].strip()
    l2 = re.sub(r"`[^`]*`", "", l)  # バッククォートの中は見ない
    for m in re.finditer(r"((?:" + Q + r"\s*)+)", l2):
        qs = re.findall(Q, m.group(1))
        mb = re.search("(" + NUM + r")\s*$", l2[:m.start()]); ma = re.match(r"\s*(" + NUM + ")", l2[m.end():])
        num = mb.group(1) if mb else (ma.group(1) if ma else None)
        if not num:
            if cur == "目的(オーナーの逐語)": nonum.append(qs[0][:20])
            continue
        for q in qs:
            cnt += 1
            if not any(n(q) in n(r) for r in rows.get(num, [])): bad.append((num, q[:30]))
print("3 番号付き引用:", cnt, "不一致:", bad, "目的の番号無し:", nonum)
SEAL = ("docs/research/window1/", "backtest_data/phase2_sealed/")
tb = [cells(l) for l in S["読んだ事実"] if l.startswith("|") and not l.startswith("|---")][1:]
for c in tb:
    v = c[2]; ok = False; ng = []
    for pm in re.finditer(r"(?<![\w./-])([\x21-\x7e]*/[\x21-\x7e]*?):(\d+)(?:-(\d+))?", v):
        path = pm.group(1).strip("`"); last = int(pm.group(3) or pm.group(2))
        q = os.path.normpath(os.path.join(str(root.resolve()), path)); rel = os.path.relpath(q, str(root.resolve()))
        if rel.startswith(".."): ng.append(("根の外", path)); continue
        if any((rel.lower() + "/").startswith(s) or rel.lower().startswith(s) for s in SEAL): ng.append(("封印", path)); continue
        if not os.path.isfile(q): ng.append(("ふつうのファイルでない", path)); continue
        nl = len(Path(q).read_text(encoding="utf-8", errors="replace").splitlines())
        print("   ", path, last, "<=", nl, last <= nl); ok = last <= nl
        if not ok: ng.append(("行の数", path))
    if re.search(r"`[^`]+`.*→\s*\S", v): ok = True
    if re.match(r"この委任には無い[(（].+[)）]", v): ok = True
    if ng or not ok: print("4 NG:", c[0], v[:60], ng)
print("4 1列目:", sorted(set(c[0] for c in tb)))
tb = [cells(l) for l in S["決めてよいこと・決めてはいけないこと"] if l.startswith("|") and not l.startswith("|---")][1:]
req = ["出力の置き場", "分母・数え方", "比べの方法", "確かめ方", "依存", "絞り方・選び方", "単位・通貨のそろえ方"]
print("5 欠け:", [r for r in req if r not in [c[0] for c in tb if c[1]]])
sc = [l[2:].split(":")[0] for l in Path(".claude/skills/delegated-study/BREAK_SCENES.md").read_text(encoding="utf-8").split("\n") if l.startswith("- ")]
tb = [cells(l) for l in S["壊す場面"] if l.startswith("|") and not l.startswith("|---")][1:]
U = re.findall(r"^- (U\d+):", "\n".join(S["受け入れ"]), re.M)
print("6 場面一致:", [c[0] for c in tb] == sc, "U 定義", len(U), "重なり", len(U) - len(set(U)))
for c in tb:
    refs = re.findall(r"(?<![\w])(U\d+)(?!\d)", c[1])
    if not ((refs and all(r in U for r in refs)) or re.search(r"無い[(（].+[)）]", c[1])): print("6 NG:", c)
print("7 H:", re.findall(r"^- (H\d+):", "\n".join(S["変えないもの"]), re.M))
fx = Path(".claude/skills/delegated-study/FIXED_CONSTRAINTS.md").read_text(encoding="utf-8")
norm = lambda ls: [x.rstrip() for x in "\n".join(ls).split("\n") if x.strip()]
print("8 制約一致:", norm(S["決まった制約"]) == norm(secs(fx)["決まった制約"]))
print("9:", all(w in "\n".join(S["終わる条件と上限"]) for w in ("終わる条件", "上限")))
out, skip = [], False
for line in t.splitlines(keepends=True):
    if line.startswith("## "): skip = line.rstrip() in ("## 途中の決め", "## オーナーの承認", "## 事前の批評の後の変更")
    if not skip: out.append(line)
h = hashlib.sha256("".join(out).encode()).hexdigest()
print("事前の批評の sha256:", h)
seen = re.search(r"^見た版の sha256: ([0-9a-f]{64})", t, re.M)
stem = Path(p).with_suffix(""); recs = sorted(Path(p).parent.glob(stem.name + "_premortem*.md"), key=lambda x: int(re.search(r"(\d+)\.md$", x.name).group(1)))
for r in recs:
    rt = r.read_text(encoding="utf-8"); first = rt.split("\n", 1)[0]
    items = re.split(r"(?m)^- \[(?:直す|聞く)\]", rt)[1:]
    resp = [re.search(r"(?m)^\s*応答: (直した|直さない|オーナーに聞く|次の版で直す)[(（].+[)）]\s*$", it.split("\n## ")[0]) for it in items]
    print("10", r.name, "1 行目:", first[:30], "指摘", len(items), "応答の欠け", sum(x is None for x in resp),
          "直した", sum(1 for x in resp if x and x.group(1) == "直した"))
if recs:
    last = recs[-1].read_text(encoding="utf-8").split("\n", 1)[0].split(": ")[-1]
    print("10 最後の回:", recs[-1].name, "sha 一致:", last == (seen.group(1) if seen else h))
