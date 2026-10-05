#!/bin/sh
# β: 分析の文書を書く瞬間に、骨組みが無ければ止める — PreToolUse(Write / Edit / MultiEdit / Bash)
#
# オーナーの指示 2026-10-05、L-694「**案1+α+βを実施してください。フックもスキルの変更も許可します。**」。
# 経緯(L-683〜L-693): 分析のスキルを読み込んでいても手順を当てずに分析した(10-05 の夜、9 枚中 6 枚で前提 P が無い)。
# 規則に書くだけでは直らない(CLAUDE.md・スキルの一覧の 1 行が常に入っていても守らなかった)ので、書く瞬間に止める。
#
# 何を見るか: `docs/ANALYSIS/` の `.md`(`README.md` を除く)への書き込みの、書いた後の中身に、
#   スキル(`.claude/skills/analysis-lens/SKILL.md`)第 2 部の手順ごとの節 `<!-- step:X -->` 〜 `<!-- /step:X -->` が
#   スキルの順で全部あり、その間の引用がスキルの本文の今の写しと一字違わず同じこと。
#   骨組みは `scripts/analysis/diag_skeleton.py` が作る(写しの抜き出し方はこのフックと同じ)。
#   Bash で `docs/ANALYSIS/` に書き込む操作(リダイレクト・tee・cp・mv・sed -i・python/perl の本文の書き込み)は止める
#   (中身を検められないので、Write / Edit で書かせる)。
#
# **限界(全部書く)**:
#   - 形を見るだけ。「当てたこと」の欄に書いた読みが正しいか、手順どおりに当てたかは見ない(L-688)。
#   - `docs/ANALYSIS/` の外に分析を書けば通る。別のファイルの台本から書き込んでも、コマンドの文字に現れないので通る(L-691)。
#   - 手順を上から順に埋めたか(前の節が「(未記入)」のまま次を書いたか)は見ない(L-694 の承認の範囲は「骨組みが無ければ止める」)。
#   - スキルの呼び出しそのものは見ない。
#   - 走っているかは、止まるはずの操作をして確かめるしかない(CLAUDE.md §3)。
set -u
INPUT="$(cat 2>/dev/null || true)"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

MSG="$(printf '%s' "$INPUT" | GATE_ROOT="$ROOT" python3 -c '
import json, os, re, sys
root = os.path.normpath(os.environ.get("GATE_ROOT", "."))
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
tn = d.get("tool_name") or ""
ti = d.get("tool_input") or {}

def rel(p):
    p = os.path.normpath(p or "")
    if p.startswith(root + os.sep):
        p = p[len(root) + 1:]
    return p.replace(os.sep, "/")

def is_doc(p):
    q = rel(p)
    return q.startswith("docs/ANALYSIS/") and q.endswith(".md") and q != "docs/ANALYSIS/README.md"

def steps():
    with open(os.path.join(root, ".claude", "skills", "analysis-lens", "SKILL.md"), encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    s = next(i for i, l in enumerate(lines) if l.startswith("## P "))
    e = next(i for i, l in enumerate(lines) if l.startswith("## 道具"))
    out, cur = [], None
    for l in lines[s:e]:
        if l.startswith("## "):
            if cur:
                out.append(cur)
            cur = [l[3:].split()[0], []]
        elif cur:
            cur[1].append(l)
    if cur:
        out.append(cur)
    for c in out:
        b = c[1]
        while b and not b[0].strip():
            b.pop(0)
        while b and not b[-1].strip():
            b.pop()
    return out

def check(text):
    try:
        st = steps()
    except Exception as ex:
        return ["スキルの本文から手順を読めない(%s)" % ex]
    probs, pos = [], -1
    for name, body in st:
        want = "\n".join([("> " + l) if l.strip() else ">" for l in body])
        m = re.search(r"<!-- step:%s -->\n(.*?)\n<!-- /step:%s -->" % (re.escape(name), re.escape(name)), text, re.S)
        if not m:
            probs.append("手順 %s の節(<!-- step:%s --> 〜 <!-- /step:%s -->)が無い" % (name, name, name))
            continue
        if m.group(1) != want:
            probs.append("手順 %s の写しがスキルの本文と違う" % name)
        if m.start() < pos:
            probs.append("手順 %s の節の順がスキルと違う" % name)
        pos = max(pos, m.start())
    return probs

def deny(path, probs):
    print("[関門 β] 分析の文書への書き込みを止めた: %s" % path)
    print("理由:")
    for p in probs:
        print("- " + p)
    print("直し方: 分析の文書は `python3 scripts/analysis/diag_skeleton.py --unit <単位>` で作った骨組みに Write / Edit で書く。"
          "手順の節と、スキルの本文の写し(<!-- step:X --> 〜 <!-- /step:X -->)は消さない・書き換えない。"
          "スキルを改訂した後なら `python3 scripts/analysis/diag_skeleton.py --refresh <ファイル>` で写しを入れ替える。")
    print("(L-694。オーナーの指示で入れたフック `.claude/hooks/analysis_skeleton_gate.sh`。)")
    sys.exit(0)

if tn == "Write":
    fp = ti.get("file_path") or ""
    if is_doc(fp):
        pr = check(ti.get("content") or "")
        if pr:
            deny(rel(fp), pr)
    sys.exit(0)

if tn in ("Edit", "MultiEdit"):
    fp = ti.get("file_path") or ""
    if not is_doc(fp):
        sys.exit(0)
    try:
        with open(fp if os.path.isabs(fp) else os.path.join(root, fp), encoding="utf-8") as fh:
            text = fh.read()
    except Exception:
        sys.exit(0)
    edits = ti.get("edits") if tn == "MultiEdit" else [ti]
    for e in edits or []:
        old, new = e.get("old_string") or "", e.get("new_string") or ""
        if not old:
            continue
        text = text.replace(old, new) if e.get("replace_all") else text.replace(old, new, 1)
    pr = check(text)
    if pr:
        deny(rel(fp), pr)
    sys.exit(0)

if tn == "Bash":
    cmd = ti.get("command") or ""
    if "docs/ANALYSIS" not in cmd:
        sys.exit(0)
    targets = []
    for m in re.finditer(r"(?:^|[^0-9<>&])>{1,2}\|?(?!&)\s*([^\s;|&]+)", cmd):
        targets.append(m.group(1))
    for seg in re.split(r";|\|\||&&|\|", cmd):
        toks = seg.strip().split()
        if not toks:
            continue
        i = 0
        if toks[0] in ("sudo", "env", "nice", "nohup", "setsid", "time", "timeout") and len(toks) > 1:
            i = 1
            if toks[0] == "timeout" and len(toks) > 2 and re.match(r"^\d", toks[1]):
                i = 2
        head = toks[i:i + 2]
        w = False
        if head and head[0] in ("tee", "cp", "mv", "truncate", "ln", "patch", "install", "dd"):
            w = True
        if head and head[0] == "sed" and any(t.startswith("-i") for t in toks[i + 1:]):
            w = True
        if len(head) > 1 and head[0] == "git" and head[1] in ("mv", "checkout", "restore"):
            w = True
        if w:
            targets.extend(toks[i + 1:])
    m = re.search(r"\b(python[0-9.]*|perl)\b", cmd)
    if m:
        seg = cmd[m.start():]
        if re.search(r"write_text\(|open\([^)]*[\"\x27][wa]|shutil\.(copy|move)", seg):
            targets.append(seg)
    if any("docs/ANALYSIS" in t for t in targets):
        print("[関門 β] Bash で分析の文書(docs/ANALYSIS/)に書き込もうとしたので止めた。")
        print("理由: Bash の書き込みは、書いた後の中身(手順の節とスキルの本文の写し)を検められない。")
        print("直し方: 骨組みは `python3 scripts/analysis/diag_skeleton.py --unit <単位>` で作り、中身は Write / Edit で書く。")
        print("(L-694。オーナーの指示で入れたフック `.claude/hooks/analysis_skeleton_gate.sh`。)")
    sys.exit(0)
sys.exit(0)
' 2>/dev/null)"
[ -n "$MSG" ] || exit 0
printf '%s\n' "$MSG" >&2
exit 2
