"""使い捨て(4 版目)。1 周目の道具が見ない新しい決まりだけを見る: 目的の引用の区切り・空の節・同じ見出し・終わる条件と上限の行・
バッククォートの中の パス:行 の実在。"""
import re, sys, os
from pathlib import Path
t = Path(sys.argv[1]).read_text(encoding="utf-8")
def cells(line):
    out=[];cur="";inb=False
    for ch in line.strip().strip("|"):
        if ch=="`": inb=not inb
        if ch=="|" and not inb: out.append(cur.strip()); cur=""
        else: cur+=ch
    out.append(cur.strip()); return out
rows={}
for l in Path("docs/OWNER_LOG.md").read_text(encoding="utf-8").split("\n"):
    if l.startswith("| L-"):
        c=cells(l)
        if len(c)>=4 and re.fullmatch(r"L-\d{3}[a-z]?|L-D\d{2}",c[0]): rows.setdefault(c[0],[]).append(c[3])
norm=lambda s: re.sub(r"\s+"," ",re.sub(r"<br\s*/?>"," ",s,flags=re.I))
B=set(" 。！？!?•→")
def bounded(q,num):
    q=norm(q)
    for col in rows.get(num,[]):
        v=norm(col)
        for m in re.finditer(re.escape(q),v):
            s,e=m.start(),m.end()
            # 欄の端 = 「** の内側の端
            okS = s==0 or v[s-1] in B or v[max(0,s-3):s].endswith("「**")
            okE = q[-1] in "。！？!?" or e==len(v) or v[e] in B or v[e:e+3]=="**」"
            if okS and okE: return True
    return False
need=["着手前の表","目的(オーナーの逐語)","読んだ事実","決めてよいこと・決めてはいけないこと","変えないもの","決まった制約","終わる条件と上限","報告","壊す場面","受け入れ","変異の表"]
heads=[l[3:].rstrip() for l in t.split("\n") if l.startswith("## ")]
print("同じ見出し:", [h for h in need if heads.count(h)>1])
secs={}; cur=None
for l in t.split("\n"):
    if l.startswith("## "): cur=l[3:].rstrip(); secs[cur]=[]
    elif cur: secs[cur].append(l)
print("空の節:", [h for h in need if not "".join(secs.get(h,[])).strip()])
pur="\n".join(secs["目的(オーナーの逐語)"])
qs=[(m.group(1),m.group(2)) for m in re.finditer(r"(L-\d{3})「\*\*(.+?)\*\*」",pur)]
print("目的の番号付き引用:", len(qs), "区切りの外:", [(n,q[:20]) for n,q in qs if not bounded(q,n)])
eu="\n".join(secs["終わる条件と上限"])
print("終わる条件・上限の行:", bool(re.search(r"^- 終わる条件:\s*\S",eu,re.M)), bool(re.search(r"^- 上限:\s*\S",eu,re.M)))
facts="\n".join(secs["読んだ事実"])
for m in re.finditer(r"`([^`\s]*/[^`\s]*):(\d+)(?:-(\d+))?`",facts):
    p_,last=m.group(1),int(m.group(3) or m.group(2))
    ok=os.path.isfile(p_) and last<=len(Path(p_).read_text(encoding="utf-8",errors="replace").splitlines())
    if not ok: print("パス:行 NG", p_, last)
print("バッククォートの中の パス:行:", len(re.findall(r"`([^`\s]*/[^`\s]*):(\d+)(?:-(\d+))?`",facts)))
