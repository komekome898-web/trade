"""Generic verdict/trap scorer for known-answer packets whose sealed file has a `claims` list
with `id` and `claim_correct`. True claims are correct if the verdict is 再現 or 数値差異(結論維持);
false claims are correct if the verdict is 結論変更. Usage: score_claims.py <answers.json> <report.md>..."""
import re, json, sys
ans = json.load(open(sys.argv[1]))
traps_gen3 = {'survivorship': r'除外|survivor|forced.{0,40}(drop|exclud|除)|生存',
         'naive_fill_wrong': r'naive|印字.{0,20}約定|fill.on.print|queue.ahead|キュー先行',
         'crossed_rows': r'crossed|交差|ask\s*<=?\s*bid|逆転',
         'adverse_selection_nonzero': r'(adverse|逆選択).{0,80}(t\s*=?\s*[3-9]|significant|有意)'}
traps = {'unclosed/survivorship': r'除外|survivor|unclosed|never clos|手仕舞えな|決済されな|dropped',
         'mid_reference': r'mid.{0,40}(reference|基準|at fill|at quote|直前|stale)|基準.{0,20}mid',
         'crossed_rows': r'crossed|交差|ask\s*<\s*bid|逆転',
         'off_grid/tiny_depth': r'grid|グリッド|tick.{0,30}(lie|not on|0 of)|median 0\.001|displayed.{0,40}0\.00'}
for path in sys.argv[2:]:
    txt = open(path).read()
    secs = re.split(r'^## +', txt, flags=re.M)
    got = {}
    for s in secs:
        m = re.match(r'(QA3?-M?\d)', s)
        if not m: continue
        v = re.findall(r'Verdict\s*[:：]\s*\**\s*([^\n*]+)', s)
        got[m.group(1)] = v[-1].strip() if v else None
    ok = 0; rows = []
    for c in ans['claims']:
        if c.get('scored', True) is False:
            continue
        v = got.get(c['id']) or ''
        correct = (('再現' in v) or ('維持' in v)) if c['claim_correct'] else ('結論変更' in v)
        ok += correct; rows.append((c['id'], c['claim_correct'], v, correct))
    print(path)
    for r in rows: print('  ', *r)
    tset = traps_gen3 if any(c['id'].startswith('QA3') for c in ans['claims']) else traps
    hits = {k: bool(re.search(p, txt, flags=re.I|re.S)) for k, p in tset.items()}
    print('   verdicts %d/%d  traps %s' % (ok, len(rows), hits))
