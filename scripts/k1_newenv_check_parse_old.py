"""Independent re-read of RESULT.md tables 2.1-2.4 (audit k1a-aud-01).
Different method from scripts/k1_newenv_diff.py: parse_old — whole file, sections found by
heading text, header row read for column order, no line-range slice, no shared code.
Compares every value with old_values.json and prints counts."""
import json, re
T = open("docs/PHASE2/K1/RESULT.md", encoding="utf-8").read().split("\n")
SEC = {"## 2.1 ": "both", "## 2.2 ": "strong", "## 2.3 ": "weak", "## 2.4 ": "n24"}
tabs, cur = {}, None
for ln in T:
    if ln.startswith("## "):
        cur = next((v for k, v in SEC.items() if ln.startswith(k)), None)
        continue
    if cur and ln.startswith("| "):
        tabs.setdefault(cur, []).append([c.strip() for c in ln.strip()[1:-1].split("|")])
old = json.load(open("docs/PHASE2/K1/NEWENV_A/old_values.json"))
bad, n_mean, n_star, n_24 = [], 0, 0, 0
for key, rows in tabs.items():
    head = rows[0]
    feet = [int(h.replace(" 分", "")) for h in head[1:]]
    body = rows[1:]  # the "|---|" separator does not start with "| " so it is not collected
    print(key, "rows", len(body), "cols", feet)
    for r in body:
        g = r[0].replace("`", "").replace("(当時の規則)", "").replace("*", "").strip()
        for f, v in zip(feet, r[1:]):
            if key == "n24":
                n, h = [int(x.strip().replace(",", "")) for x in v.split("/")]
                o = old["n_hold"].get(f"{f}|{g}|both")
                n_24 += 1
                if o != {"n": n, "hold_median": h}: bad.append((key, f, g, v, o))
            else:
                star = v.endswith("\\*") or v.endswith("\\***")
                num = float(v.replace("**", "").replace("\\*", "").replace("−", "-"))
                o = old["means"].get(f"{f}|{g}|{key}")
                n_mean += 1; n_star += star
                if o is None or abs(o["mean_bp"] - num) > 1e-9 or o["star"] != star: bad.append((key, f, g, v, o))
print("means read", n_mean, "of which star", n_star, "| 2.4 cells read", n_24)
print("old_values.json sizes: means", len(old["means"]), "stars", sum(v["star"] for v in old["means"].values()), "n_hold", len(old["n_hold"]))
print("mismatches", len(bad)); [print(b) for b in bad[:20]]
