"""材料の選定: 前半の表(screen_A / screen_B)の |分かれ方−0.5| を並べ、隣り合う落差と順位確率の SE を出す。
後半には触れない(入力は前半だけで作られた 2 つの表)。境目を置く根拠の数字を出すだけで、判定はしない。"""
import math, pandas as pd
D = "backtest_data/o3c_signal_materials_20260920/"
for name, g1, g2 in (("screen_A", "単発", "多件の最初"), ("screen_B", "途中", "多件の最後")):
    t = pd.read_csv(D + name + ".csv")
    t = t.sort_values("|分かれ方-0.5|", ascending=False, na_position="last").reset_index(drop=True)
    n1, n2 = int(t[g1 + "_n"].iloc[0]), int(t[g2 + "_n"].iloc[0])
    se = math.sqrt((n1 + n2 + 1) / (12 * n1 * n2))
    print(f"== {name}: {g1} n={n1}, {g2} n={n2}, 順位確率の SE(交換可能のとき)= sqrt((n1+n2+1)/(12 n1 n2)) = {se:.4f}")
    prev = None
    for _, r in t.iterrows():
        d = r["|分かれ方-0.5|"]
        gap = "" if prev is None or pd.isna(d) else f"落差 {prev - d:.4f}"
        miss = f"欠測 {r[g1+'_欠測割合']:.2f}/{r[g2+'_欠測割合']:.2f}"
        print(f"  {str(r['候補']):>3}  |d|={d:.4f}  分かれ方={r['分かれ方の数']:.4f}  {gap:>12}  {miss}" if not pd.isna(d)
              else f"  {str(r['候補']):>3}  |d|=  (欠測 100%)")
        if not pd.isna(d): prev = d
