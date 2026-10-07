import re,sys,os,hashlib
p=sys.argv[1]; b=open(p,'rb').read(); t=b.decode()
L=t.split("\n")
def secs(t):
    out={};cur=None
    for l in t.split("\n"):
        if l.startswith("## "): cur=l[3:].strip(); out[cur]=[]
        elif cur is not None: out[cur].append(l)
    return out
S=secs(t)
print("1 種類:", [i+1 for i,l in enumerate(L[:5]) if l.strip() in ("種類: 作る","種類: 読む","種類: 批評")])
need=["着手前の表","目的(オーナーの逐語)","読んだ事実","決めてよいこと・決めてはいけないこと","変えないもの","決まった制約","終わる条件と上限","報告","壊す場面","受け入れ","変異の表"]
print("2 欠けた見出し:", [n for n in need if n not in S])
def cells(line):
    out=[];cur="";inb=False
    for ch in line.strip().strip("|"):
        if ch=="`": inb=not inb
        if ch=="|" and not inb: out.append(cur.strip()); cur=""
        else: cur+=ch
    out.append(cur.strip()); return out
log=open("docs/OWNER_LOG.md",encoding="utf-8").read().split("\n")
rows={}
for l in log:
    m=re.match(r"\|\s*(L-(?:\d{3}[a-z]?|D\d{2}))\s*\|",l)
    if m: rows.setdefault(m.group(1),[]).append(l)
n=lambda x: re.sub(r"\s+"," ",x)
NUM=r"L-(?:\d{3}[a-z]?|D\d{2})"
bad=[];cnt=0
for l in L:
    for m in re.finditer(r"「\*\*((?:(?!\*\*).)+?)\*\*」",l):
        before=l[:m.start()]; after=l[m.end():]
        mb=re.search(r"("+NUM+r")\s*$",before)
        ma=re.match(r"(?:[\s、/]|「\*\*(?:(?!\*\*).)+?\*\*」)*("+NUM+")",after)
        num=mb.group(1) if mb else (ma.group(1) if ma else None)
        if not num: continue
        cnt+=1
        if not any(n(m.group(1)) in n(r) for r in rows.get(num,[])): bad.append((num,m.group(1)[:30]))
print("3 番号付き引用:",cnt,"不一致:",bad)
# 4
tb=[cells(l) for l in S["読んだ事実"] if l.startswith("|") and not l.startswith("|---")][1:]
for c in tb:
    ok=False; v=c[2]
    for pm in re.finditer(r"([\w./-]+):(\d+)(?:-(\d+))?",v):
        path,a,bb=pm.group(1),pm.group(2),pm.group(3)
        if os.path.isfile(path):
            nl=sum(1 for _ in open(path,encoding="utf-8",errors="replace")); ok= int(bb or a)<=nl
            print("  ",path,bb or a,"<=",nl,ok)
    if re.search(r"`[^`]+`.*→\s*\S",v): ok=True
    if re.match(r"この委任には無い[(（].+[)）]",v): ok=True
    if not ok: print("4 NG:",c[0],v[:60])
print("4 1列目:",sorted(set(c[0] for c in tb)))
tb=[cells(l) for l in S["決めてよいこと・決めてはいけないこと"] if l.startswith("|") and not l.startswith("|---")][1:]
req=["出力の置き場","分母・数え方","比べの方法","確かめ方","依存","絞り方・選び方","単位・通貨のそろえ方"]
print("5 欠け:",[r for r in req if r not in [c[0] for c in tb if c[1]]])
sc=[l[2:].split(":")[0] for l in open(".claude/skills/delegated-study/BREAK_SCENES.md",encoding="utf-8").read().split("\n") if l.startswith("- ")]
tb=[cells(l) for l in S["壊す場面"] if l.startswith("|") and not l.startswith("|---")][1:]
U=re.findall(r"^- (U\d+):","\n".join(S["受け入れ"]),re.M)
print("6 場面一致:",[c[0] for c in tb]==sc, "U定義",len(U),"重なり",len(U)-len(set(U)))
for c in tb:
    refs=re.findall(r"(?<!\d)(U\d+)(?!\d)",c[1])
    ok=(refs and all(r in U for r in refs)) or re.match(r"この委任には無い[(（].+[)）]",c[1])
    if not ok: print("6 NG:",c)
H=re.findall(r"^- (H\d+):","\n".join(S["変えないもの"]),re.M); print("7 H:",H)
fx=open(".claude/skills/delegated-study/FIXED_CONSTRAINTS.md",encoding="utf-8").read()
norm=lambda ls: [x.rstrip() for x in "\n".join(ls).strip("\n").split("\n")]
print("8 制約一致:", norm(S["決まった制約"])==norm(secs(fx)["決まった制約"]))
print("9:", all(w in "\n".join(S["終わる条件と上限"]) for w in ("終わる条件","上限")))
body=re.sub(r"(?ms)^## 途中の決め\n.*?(?=^## |\Z)","",t)
print("body_sha256:",hashlib.sha256(body.encode()).hexdigest())
