# 照合(README「照合」)。gate_diag.py を 2019-01-01〜01-15 で走らせた置き場を引数に: PYTHONPATH=src python3 gate_check.py <置き場>
import sys,os,numpy as np
sys.path.insert(0,'docs/RESEARCH/cards/c4_owner_matilda_range/diag_gate')
import gate_diag as g
from gate_diag import run_b2, iso, boundaries, cardmd, pnl, C4OwnerMatildaRange
lo,hi=iso('2019-01-01T00:00:00Z'),iso('2019-01-15T00:00:00Z')
st,_=cardmd.settings(cardmd.parse(open('docs/RESEARCH/cards/c4_owner_matilda_range/CARD.md').read()))
decl=dict(st.declarations)
class Full(C4OwnerMatildaRange):
    def __init__(s): super().__init__(range_from='body'); s.tr=[]; s.tt=[]
    def _in_trend(s,*a,**k): s.tr.append(s._trend); s.tt.append(a[0]); return super()._in_trend(*a,**k)
    def _in_range(s,*a,**k): s.tr.append(0); s.tt.append(a[0]); return super()._in_range(*a,**k)
f=Full(); run_b2.run_chunks(f,lo,hi,boundaries(lo,hi,'year'),decl)
n=C4OwnerMatildaRange(range_from='body',trend_gate=False); rn,_,_=run_b2.run_chunks(n,lo,hi,boundaries(lo,hi,'year'),decl)
z=np.load(sys.argv[1]+'/probe.npz')
pn=pnl(rn)
print('exposure same', np.array_equal(pn.exposure,z['exposure']))
print('fix10 same', len(f.tr)==len(z['fix10']), np.array_equal(np.array(f.tr),z['fix10']), np.array_equal(np.array(f.tt),z['rec_t']))
print('fix10 share', (z['fix10']!=0).mean(), 'v37 share', (z['v37']!=0).mean())
