"""Jev の後半 5,000 件: リードが呼び出しの記録(data/jev/continue/、リポジトリ外)と行データから的中率・較正を独立に計算する(2026-09-20)。
確率そのものはこのログに書かない(帯ごとの件数と実際の割合だけ)。"""
import json, math, numpy as np, pandas as pd
rows = [json.loads(l) for l in open("data/jev/continue/prints_answers.jsonl")]
print("呼び出しの記録:", len(rows), "キー:", sorted(rows[0].keys())[:12])
def prob(r):
    if "prob" in r: return r["prob"]
    a = r.get("answers") or r.get("answer") or {}
    if isinstance(a, dict):
        c = a.get("continue", a); 
        if isinstance(c, dict): return c.get("noul")
    return r.get("noul", r.get("prob", r.get("p")))
pid = [r.get("print_id") for r in rows]; pr = np.array([prob(r) for r in rows], dtype=float)
df = pd.DataFrame({"print_id": pid, "p": pr}).dropna()
print("確率が取れた件数:", len(df), " 重複 print_id:", int(df.print_id.duplicated().sum()))
r = pd.read_csv("backtest_data/o3c_signal_continue_20260920/rows_continue.csv.gz"); p = r[r.kind == "print"]
m = df.merge(p[["print_id", "half", "label_30", "label_60", "label_120", "mat1_same_side_count_60s_and_elapsed", "side"]], on="print_id", how="left")
print("後半の件数:", int((m.half == "後半").sum()), " 前半:", int((m.half == "前半").sum()))
base = m.label_60.mean(); print(f"5,000 件の基準率(続く割合, 60 秒) = {base:.4f}")
for th in (0.5, 0.6, 0.7):
    say = m.p.to_numpy() >= th; lab = m.label_60.to_numpy() == 1
    hit = float((say == lab).mean()); prec = float(lab[say].mean()) if say.sum() else float("nan"); rec = float(say[lab].mean())
    print(f"閾値 {th}: 続くと言った {int(say.sum())} 件 的中 {hit:.4f} 適合 {prec:.4f} 再現 {rec:.4f}")
print("較正(帯 = [k/10, (k+1)/10)): 件数 / 実際の続く割合 / 2SE / 基準率と区別できるか")
bands = np.minimum((m.p.to_numpy() * 10).astype(int), 9); lab = m.label_60.to_numpy()
for k in range(10):
    msk = bands == k; n = int(msk.sum())
    if n == 0: print(f"帯 {k}: n=0 → わからない"); continue
    q = lab[msk].mean(); se = math.sqrt(q * (1 - q) / n) if 0 < q < 1 else 0.0
    verdict = "わからない" if abs(q - base) <= 2 * se else ("続く" if q > base else "止まる")
    print(f"帯 {k}: n={n:<5} 実際={q:.4f} 2SE={2*se:.4f} → {verdict}")
print("規則(材料 1 ≥ 1)との一致率(閾値 0.5):", round(float(((m.p >= 0.5) == (m.mat1_same_side_count_60s_and_elapsed >= 1)).mean()), 4))
