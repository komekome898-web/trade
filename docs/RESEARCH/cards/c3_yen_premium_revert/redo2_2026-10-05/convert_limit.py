"""カード 3 の指値の模型(measure_limit/<窓>/daily.csv、列 day_jst・pnl_bp・n_minutes・…・worse_vs_better_bp)を、
diag_tables.py が読む形(daily.csv の列 day・pnl_bp・n)に写す。値は変えない(列の名前を替えるだけ)。
- 悪い側 = pnl_bp(README「損益の悪い方を本値にした」)
- 良い側 = pnl_bp + worse_vs_better_bp(README「悪い方と良い方の差 = Σ(良い方 − 悪い方の分の損益)」の日ごとの値)
出力: このフォルダの limit_conv/<窓>_bad/daily.csv・<窓>_good/daily.csv
    python3 docs/RESEARCH/cards/c3_yen_premium_revert/redo2_2026-10-05/convert_limit.py
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "measure_limit")

for w in ("1h", "1d", "1w"):
    rows = list(csv.DictReader(open(os.path.join(SRC, w, "daily.csv"))))
    for side in ("bad", "good"):
        d = os.path.join(HERE, "limit_conv", f"{w}_{side}")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "daily.csv"), "w") as fh:
            fh.write("day,pnl_bp,n\n")
            for r in rows:
                v = float(r["pnl_bp"]) + (float(r["worse_vs_better_bp"]) if side == "good" else 0.0)
                fh.write(f"{r['day_jst']},{v!r},{r['n_minutes']}\n")
    print(w, len(rows))
