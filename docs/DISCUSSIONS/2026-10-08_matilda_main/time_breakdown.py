import json, re, collections
from datetime import datetime
p="/root/.claude/projects/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02.jsonl"
ev=[]
for line in open(p,encoding="utf-8"):
    try: d=json.loads(line)
    except: continue
    ts=d.get("timestamp")
    if not ts or ts<"2026-10-08T23:38:58" or ts>"2026-10-09T01:20:35": continue
    m=d.get("message",{})
    c=m.get("content") if isinstance(m,dict) else None
    role=m.get("role") if isinstance(m,dict) else None
    desc=""
    if isinstance(c,list):
        for b in c:
            if not isinstance(b,dict): continue
            if b.get("type")=="tool_use": desc+=" TOOL:"+b["name"]+" "+json.dumps(b.get("input",{}),ensure_ascii=False)[:400]
            if b.get("type")=="server_tool_use": desc+=" TOOL:advisor"
            if b.get("type")=="text" and role=="assistant": desc+=" TEXT:"+b["text"][:60]
            if b.get("type")=="tool_result": desc+=" RESULT"
    elif isinstance(c,str): desc=" USER:"+c[:60]
    ev.append((datetime.fromisoformat(ts.replace("Z","+00:00")),role,desc))
ev.sort(key=lambda x:x[0])
# 役の無い行(フックの出力・添付など)は区間の切れ目にしない
ev=[e for e in ev if e[1] in ("assistant","user")]
def cat(s):
    if "TOOL:advisor" in s: return "相方(advisor)"
    if "owner-auditor" in s: return "関門② 監査役"
    if re.search(r"simple_trades|diag_tables\.py|diag_paths\.py",s): return "表の作り直し(取引の行・読み口)"
    if re.search(r"_extra|compare_family|scenes\.py|market_side|width_vola|market_delay|foot_check|half_diff|levels_extra",s): return "追加の数え(台本を書く・走らせる)"
    if re.search(r"ledger_rows|FINDINGS_LEDGER|edit_ledger|check_findings",s): return "台帳"
    if re.search(r"partner_brief|partner/|brief\.py|_reply\.md",s): return "相方の渡し書き・記録"
    if re.search(r"VERDICTS|gate2",s): return "関門② の記録・直し"
    if re.search(r"git (commit|push|add|status|reset)|commit_",s): return "コミット・押し出し"
    if re.search(r"SESSIONS|receive_main|get_session|list_events|send_later|Monitor|sleep",s): return "受け取り・見回り"
    if re.search(r"OWNER_LOG|OWNER_STATUS",s): return "状態板・記録"
    if re.search(r"ANALYSIS|diag_skeleton|count_tables|check_partner|check_placeholders",s): return "分析の文書を書く"
    if "TEXT:" in s and "TOOL:" not in s: return "報告の文"
    if "TOOL:Read" in s or "TOOL:Grep" in s: return "読む(その他)"
    return "その他"
tot=collections.Counter(); n=collections.Counter()
for i,(t,role,s) in enumerate(ev[:-1]):
    if role!="assistant": continue
    # time attributable: from previous event end to this assistant event (model gen) + until next user/result
    j=i+1
    while j<len(ev) and ev[j][1]=="assistant": j+=1
    nxt=ev[j][0] if j<len(ev) else t
    prev=ev[i-1][0] if i>0 else t
    dt=(t-prev).total_seconds()  # generation time for this message
    k=cat(s); tot[k]+=dt; n[k]+=1
    # tool runtime: from this to next non-assistant
    if "TOOL:" in s:
        tot[k]+= max(0,(nxt-t).total_seconds()) if j==i+1 else 0
all_=sum(tot.values())
for k,v in tot.most_common(): print(f"{k}\t{v/60:.1f} 分\t{100*v/all_:.0f}%\t呼び {n[k]}")
print("計", round(all_/60,1), "分;", "窓", round((ev[-1][0]-ev[0][0]).total_seconds()/60,1),"分")
print("---- 区間で数える(前の結果から次の結果まで = 考える + 打つ + 走る)")
tot=collections.Counter(); n=collections.Counter(); spans=[]
last=ev[0][0]; buf=""
for t,role,s in ev:
    if role=="assistant":
        buf+=s; continue
    if buf:
        k=cat(buf); dt=(t-last).total_seconds(); tot[k]+=dt; n[k]+=1; spans.append((dt,k,buf[:150]))
    last=t; buf=""
all_=sum(tot.values())
for k,v in tot.most_common(): print(f"{k}\t{v/60:.1f} 分\t{100*v/all_:.0f}%\t区間 {n[k]}")
print("計", round(all_/60,1))
for dt,k,b in sorted(spans,reverse=True)[:15]: print(round(dt), k, b[:140])
print("---- 窓ごと")
wins=[("base","2026-10-08T23:38:58","2026-10-09T00:23:16"),("levels","2026-10-09T00:23:16","2026-10-09T00:58:49"),("foot","2026-10-09T00:58:49","2026-10-09T01:20:35")]
last=ev[0][0]; buf=""; per=collections.defaultdict(collections.Counter)
for t,role,s in ev:
    if role=="assistant": buf+=s; continue
    if buf:
        for w,a,b in wins:
            if a<=last.isoformat().replace("+00:00","Z")[:19]<b[:19]: per[w][cat(buf)]+=(t-last).total_seconds()
    last=t; buf=""
for w in per:
    tt=sum(per[w].values()); print(w, round(tt/60,1),"分:", "、".join(f"{k} {v/60:.1f}" for k,v in per[w].most_common()))
for t,role,s in ev:
    if "diag_skeleton.py --unit matilda_main_foot" in s or "diag_skeleton.py --unit matilda_main_levels" in s: print(t, s[:100])
print("---- 置き場の名前で族に割り当て(区間の中の道具の引数に出た名前。複数なら『混ざり』)")
last=ev[0][0]; buf=""; per=collections.Counter(); unk=[]
for t,role,s in ev:
    if role=="assistant": buf+=s; continue
    if buf:
        hit={u for u,pat in (("base",r"main_base|/base/|matilda_main_trades/base|_base\.|base_gate"),("levels",r"levels"),("foot",r"foot"),("count",r"count_|/count")) if re.search(pat,buf)}
        k=("混ざり" if len(hit)>1 else hit.pop()) if hit else "名前なし"
        per[k]+=(t-last).total_seconds()
    last=t; buf=""
for k,v in per.most_common(): print(f"{k}\t{v/60:.1f} 分")
print("---- 記録の行の間が 60 秒を超える所(数えに入らない時間の候補)")
miss=0
for i in range(1,len(ev)):
    g=(ev[i][0]-ev[i-1][0]).total_seconds()
    if g>60 and ev[i][1]!="user" or (g>60 and ev[i-1][1]=="user" and ev[i][1]=="user"):
        print(ev[i-1][0].strftime("%H:%M:%S"), "→", ev[i][0].strftime("%H:%M:%S"), round(g), ev[i-1][1], ev[i-1][2][:50].replace("\n"," "), "|", ev[i][1], ev[i][2][:50].replace("\n"," "))
