#!/bin/sh
# ③(a) 構造的に不可能にする — PreToolUse(Write / Edit / NotebookEdit / Bash)
#
# オーナー承認 2026-09-14、L-169「**A-16 ①③④⑤ のフック配線(4 件) →yes**」。
#
# **なぜ「規則に書く」ではなく「拒否する」か。**
#   Reason の分類(`docs/DISCUSSIONS/2026-09-14_instruction_adherence/03_人的要因と安全科学.md` §5):
#   逸脱を**自分で書いてから進んだ**ものは error ではなく **violation** である。
#   violation は情報不足で起きていないので、**規則の追記・強調・再掲では原理的に直らない。**
#   効くのは (a) 逸脱しなくても仕事が終わる経路、(b) 構造的に不可能にすること、の 2 つだけ。
#
# **限界を先に書く(§5.0 と同じ形)**:
#   - **解除ファイルはリードが作れる。**構造的な不可能性ではない。作った回数は OWNER_LOG に書く。
#   - このフック自体、`~/.claude.json` の `hasTrustDialogAccepted` が false なら走らない
#     (2026-09-14 の段 0)。**走っているかは、止まるはずの操作をして確かめるしかない。**
#
# **Bash の照合(2026-10-01、L-488 7(a) で直した)**: 前版は「保護パスの語がコマンドのどこかにあり、
# 同じコマンドに書き込みの語(python3・>>・sed -i …)があれば拒否」で、保護パスを**読むだけ**の操作
# (`wc -l`、`git blame`)と別のファイルへの追記が同居しただけで止まった(2026-10-01 の監査中に 3 回)。
# 今版は**書き込みの対象**が保護パスのときだけ拒む: リダイレクトの先、tee / sed -i / cp / mv / rm /
# truncate / ln / chmod / patch / git rm / git mv の引数、python / perl の本文に書き込みの呼び出し
# (open(…'w'/'a')、write_text、unlink、remove、rmtree)があってその本文に保護パスがある場合。
set -u
INPUT="$(cat 2>/dev/null || true)"

FP="$(printf '%s' "$INPUT" | python3 -c '
import json,sys,re
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
ti=d.get("tool_input") or {}
PATS=("PROJECT_GOAL.md","OWNER_MODEL_SOURCE.md","OWNER_INTENT",".claude/hooks/",".claude/settings.json",".claude/agents/","githooks/")
if d.get("tool_name")=="Bash":
    cmd=ti.get("command") or ""
    targets=[]
    # 1. リダイレクトの先(2>/dev/null の "2>" と ">&" は除く)
    for m in re.finditer(r"(?:^|[^0-9<>&])>{1,2}\|?(?!&)\s*([^\s;|&]+)", cmd):
        targets.append(m.group(1))
    # 2. 書き込みの命令の引数(次の ; | && || まで)
    segs=re.split(r";|\|\||&&|\|", cmd)
    for seg in segs:
        toks=seg.strip().split()
        if not toks: continue
        i=0
        if toks[0] in ("sudo","env","nice","nohup","setsid","time","timeout") and len(toks)>1:
            i=1
            if toks[0]=="timeout" and len(toks)>2 and re.match(r"^\d",toks[1]): i=2
        head=toks[i:i+2]
        is_write=False
        if head and head[0] in ("tee","cp","mv","rm","truncate","ln","chmod","patch","rmdir","shred","install"): is_write=True
        if head and head[0]=="sed" and any(t.startswith("-i") for t in toks[i+1:]): is_write=True
        if len(head)>1 and head[0]=="git" and head[1] in ("rm","mv","checkout","restore"): is_write=True
        if is_write:
            targets.extend(toks[i+1:])
    # 3. python / perl の本文(その語から後ろ)に書き込みの呼び出しがあるとき、その本文に保護パスがあれば対象とみなす
    m=re.search(r"\b(python[0-9.]*|perl)\b", cmd)
    if m:
        seg=cmd[m.start():]
        if re.search(r"write_text\(|open\([^)]*[\"\x27][wa]|\.unlink\(|os\.remove\(|rmtree\(|shutil\.(copy|move)", seg):
            targets.append(seg)
    for pat in PATS:
        if any(pat in t for t in targets):
            print("bash:"+pat); sys.exit(0)
    print(""); sys.exit(0)
print(ti.get("file_path","") or "")
' 2>/dev/null)"
[ -n "$FP" ] || exit 0

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$ROOT" ] || ROOT="$(pwd)"
# **末尾一致で判定する。**絶対パスで来ても相対パスで来ても、$CLAUDE_PROJECT_DIR が
# 何であっても同じ結果になる。
REL="$FP"

deny() {
  cat >&2 <<EOF
[関門] この場所への書き込みを拒否した: $REL

理由: $1

解除: $2 が存在するときだけ通る。**この解除ファイルはオーナーの指示があるときだけ作る**(作った回数を OWNER_LOG に書く)。
EOF
  exit 2
}

case "$REL" in
  */docs/PROJECT_GOAL.md|docs/PROJECT_GOAL.md|*/OWNER_MODEL_SOURCE.md|OWNER_MODEL_SOURCE.md|*OWNER_INTENT*|bash:PROJECT_GOAL.md|bash:OWNER_MODEL_SOURCE.md|bash:OWNER_INTENT)
    if [ -f "$ROOT/.claude/state/owner_unlock_intent" ]; then
      # **無言で通さない。**通したこと自体を記録に出す。
      echo "[関門] 解除ファイル owner_unlock_intent があるので通した: $REL" >&2
      exit 0
    fi
    deny "**オーナーの逐語とゴールは、リードが書き換えるものではない。**" \
      ".claude/state/owner_unlock_intent" ;;
  */.claude/hooks/*|.claude/hooks/*|*/.claude/settings.json|.claude/settings.json|*/.claude/agents/*|.claude/agents/*|bash:.claude/*|bash:githooks/)
    if [ -f "$ROOT/.claude/state/owner_unlock_hooks" ]; then
      echo "[関門] 解除ファイル owner_unlock_hooks があるので通した: $REL" >&2
      exit 0
    fi
    deny "**A-16 / A-15 の機械化。**オーナー逐語(L-156): 「**なんでフックを自分で書き換える前提で話してる？私が指示した時以外変えないものでないとフックの意味をなさない**」" \
      ".claude/state/owner_unlock_hooks" ;;
esac

exit 0
