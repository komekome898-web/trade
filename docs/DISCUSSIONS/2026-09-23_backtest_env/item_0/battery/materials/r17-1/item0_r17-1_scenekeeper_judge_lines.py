"""Round r17-1: the scene keeper's judgments for the marked lines without one (each line read in the listing printed
by line_marks.py before writing; the category is chosen by the file)."""
import sys
sys.path.insert(0, "/home/user/trade/tests/bt/battery/item_0")
import line_marks as M
R17 = "(第 r17-1 回)"
BY_FILE = {
    "ROOTCAUSE_r17-1.md": ("規則・読み", "根本原因・主張の表・読みと判断・結果の記録(場面の中身は scenes.py と runner の出力を名指す)" + R17),
    "run_battery.py": ("規則・読み", "runner の docstring(採点の規則の文。場面の中身ではない)" + R17),
    "test_battery_r17_refusal.py": ("コード", "場面 id を照合元から場面を引く鍵・格子の場面の一覧として使う試験のコード" + R17),
}
lines = M.all_lines()
j = M.judgments()
add = []
for f, i, t, m in lines:
    if m and M.key(f, t) not in j:
        if f not in BY_FILE:
            raise SystemExit(f"no category for {f}:{i}: {t[:120]}")
        cat, note = BY_FILE[f]
        add.append(f"{M.key(f, t)}\t{f}:{i}\t{cat}\t{note}")
print("add", len(add))
if "--write" in sys.argv:
    rows = M.JUDGMENTS.read_text(encoding="utf-8").rstrip("\n").split("\n")
    M.JUDGMENTS.write_text("\n".join(rows + add) + "\n", encoding="utf-8")
    print("written")
