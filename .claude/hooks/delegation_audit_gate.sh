#!/bin/sh
# 委任の関門 — PreToolUse(Agent / SendMessage)
#
# オーナー指示 2026-09-21、L-375「**機械直せよ**」(経緯: L-367「元々委任する前に監査入れてたんじゃない？？
# 今日お前は勝手にガンガン進めてたけど、確認しろ」)。
#
# 何を止めるか: **監査役の記録が無い委任。**
#   委任(Agent で下位モデルを起動する / SendMessage で委任先に指示を送る)は、
#   (a) 委任文が `docs/DATA/delegations/<name>.md` のファイルにあり、
#   (b) その委任文の**今の中身の指紋** `<name>.md@<sha256 の先頭 12 桁>` が `docs/AUDITOR/VERDICTS/` の
#       どれかの記録に書かれている(= その版を監査役に読ませ、問いに答えた記録がある)
#   ときだけ通す。委任文を書き換えたら指紋が変わるので、監査をやり直さない限り通らない。
#   会話のメッセージだけの委任(ファイル無し)は通らない(2026-09-21 に 4 回あった型)。
#
# 通すもの: 監査役そのもの(owner-auditor / owner-auditor-candidate / owner-model-auditor)、
#   読むだけの補助(Explore / Plan / claude-code-guide / statusline-setup)。
#
# **限界(全部書く)**: 解除ファイル `.claude/state/owner_unlock_delegation` はリードが作れる(③(a) と同じ穴)。
#   VERDICTS の記録も リードが書く。この関門が保証するのは「記録が差分に残る」ことと
#   「記録の無い委任が通らない」ことだけで、監査の中身の質は保証しない。
set -u
INPUT="$(cat 2>/dev/null || true)"
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$ROOT" ] || ROOT="$(pwd)"
if [ -f "$ROOT/.claude/state/owner_unlock_delegation" ]; then
  echo "[関門] 解除ファイル owner_unlock_delegation があるので通した(委任の関門)" >&2
  exit 0
fi
printf '%s' "$INPUT" | ROOT="$ROOT" python3 -c '
import json, sys, os, re, hashlib, glob
try: d = json.load(sys.stdin)
except Exception: sys.exit(0)
tool = d.get("tool_name", ""); ti = d.get("tool_input") or {}
root = os.environ.get("ROOT", ".")
if tool == "Agent":
    if (ti.get("subagent_type") or "") in ("owner-auditor", "owner-auditor-candidate", "owner-model-auditor",
                                           "Explore", "Plan", "claude-code-guide", "statusline-setup"):
        sys.exit(0)
    text = ti.get("prompt") or ""
elif tool == "SendMessage":
    text = ti.get("message") or ""
else:
    sys.exit(0)
def deny(msg):
    sys.stderr.write("[関門] 委任を拒否した。" + msg + "\n"
        "\n規則(KA-101、オーナー指示 L-375「機械直せよ」): 委任文は docs/DATA/delegations/ のファイルにし、"
        "設計と一緒に監査役に読ませ、その版の指紋 <name>.md@<sha256 先頭 12 桁> を docs/AUDITOR/VERDICTS/ の記録に書いてから送る。"
        "会話のメッセージだけの委任は通らない。解除は .claude/state/owner_unlock_delegation(オーナーが作る)。\n")
    sys.exit(2)
cites = re.findall(r"docs/DATA/delegations/[A-Za-z0-9_.-]+\.md", text)
if not cites:
    deny("委任文のファイル(docs/DATA/delegations/*.md)がプロンプトに引用されていない。")
ok = []
for rel in dict.fromkeys(cites):
    p = os.path.join(root, rel)
    if not os.path.isfile(p):
        deny(f"引用された委任文が存在しない: {rel}")
    sha = hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]
    marker = os.path.basename(rel) + "@" + sha
    found = False
    for v in glob.glob(os.path.join(root, "docs", "AUDITOR", "VERDICTS", "*.md")):
        try:
            if marker in open(v, encoding="utf-8", errors="replace").read():
                found = True; break
        except OSError:
            pass
    if not found:
        deny(f"この版の委任文の監査の記録が無い: 期待する印 = {marker}(docs/AUDITOR/VERDICTS/ のどれにも無い)")
    ok.append(marker)
sys.stderr.write("[関門] 委任文の監査の記録を確認して通した: " + ", ".join(ok) + "\n")
sys.exit(0)
'
