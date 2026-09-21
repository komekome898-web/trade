#!/usr/bin/env python3
"""関門の実測。**オーナーと監査役が何度でも再現できるようにリポジトリに置く。**

使い方: python3 scripts/verify_gates.py

**通る側と止まる側の両方を測る**(「拒否される側しか測っていない」と 2026-09-13 の 3 本目の
監査に指摘されたため)。

2026-09-19、L-202 で関門を縮めた(経緯は `docs/AUDITOR/ACTION_LOG.md` 063。削除の 1 手が済む前は「残したフック 6 本だけ」と pre-push の試験が食い違っていた = 実物が縮んでいないことを示す)。残したのは
  - 指紋の照合 `_verify_manifest.sh`(Write / Edit / Agent と、git 側の `githooks/pre-push`)
  - ③(a) 保護パスへの書き込み拒否 `deny_protected_paths.sh`
  - ③(b) 選択待ちの全面停止 `owner_options_gate.sh`
  - TRACE の記録 `trace_snapshot.sh`(監査役の定義 §0.5 の入力。止めない)
  - `settings.json` の健全性(スキーマ外の鍵が無い / 参照するフックが実在する)
  - 台帳 `HOOK_MANIFEST.sha256` の健全性(載っているファイルが実在する = I-012 の型)
撤去するもの(押し出しの行動監査・返答の関門・MCP の既定拒否・④⑤・全称語の検査)の試験は消した。

**この道具の限界(2026-09-14 に実測)**: 関門の**部品**を直接叩くので、
「ハーネスがその関門を呼んでいるか」は見ていない。それは止まるはずの操作をして止まるかで
しか確かめられない(`docs/DISCUSSIONS/2026-09-14_instruction_adherence/STAGE0_hook_probe.md`)。
"""
import json, os, shutil, subprocess, tempfile

ROOT = os.environ.get("CLAUDE_PROJECT_DIR", "/home/user/trade")
HOOKS = os.path.join(ROOT, ".claude", "hooks")
VM = os.path.join(HOOKS, "_verify_manifest.sh")
PRE = os.path.join(ROOT, "githooks", "pre-push")
MANIFEST = os.path.join(ROOT, "docs", "AUDITOR", "HOOK_MANIFEST.sha256")
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")

FAIL = 0


def show(label, got, want):
    global FAIL
    ok = got == want
    if not ok:
        FAIL += 1
    print(f"  [{got}] 期待 {want} {'一致' if ok else '**食い違い**'}  {label}")


def run(args, stdin="", root=None, cwd=None):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=root or ROOT)
    p = subprocess.run(args, input=stdin, capture_output=True, text=True, env=env, cwd=cwd or ROOT)
    return p.returncode


def hook(name, payload, root=None):
    return run(["sh", os.path.join(HOOKS, name)], json.dumps(payload), root)


def _pre(tool, fp=None, cmd=None):
    ti = {}
    if fp:
        ti["file_path"] = fp
    if cmd:
        ti["command"] = cmd
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": ti}


# ---------------------------------------------------------------------------
print("== 指紋の照合(_verify_manifest.sh を直接叩く) ==")
show("台帳と一致していれば通る", run(["sh", VM]), 0)
show("--allow-regen(復旧路)は通る", run(["sh", VM, "--allow-regen"]), 0)
bak = VM + ".bak"
shutil.copy(VM, bak)
open(VM, "a").write("\n#x\n")
show("フックを 1 バイト改変すると止まる", run(["sh", VM]), 2)
shutil.move(bak, VM)
show("復元後は通る", run(["sh", VM]), 0)

# 台帳に載ったファイルが消えた状態(I-012 の型)。実物は触らず、一時の root で測る。
tmp_root = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp_root, ".claude", "hooks"))
os.makedirs(os.path.join(tmp_root, "docs", "AUDITOR"))
shutil.copy(VM, os.path.join(tmp_root, ".claude", "hooks", "_verify_manifest.sh"))
import hashlib
_vm_sha = hashlib.sha256(open(VM, "rb").read()).hexdigest()
open(os.path.join(tmp_root, "docs", "AUDITOR", "HOOK_MANIFEST.sha256"), "w").write(
    f"{_vm_sha}  .claude/hooks/_verify_manifest.sh\n")
show("一時の root: 台帳と一致していれば通る", run(["sh", VM], root=tmp_root), 0)
open(os.path.join(tmp_root, "docs", "AUDITOR", "HOOK_MANIFEST.sha256"), "a").write(
    f"{'0' * 64}  .claude/hooks/deleted_hook.sh\n")
show("一時の root: 台帳に載ったファイルが消えていると止まる(I-012 の型)", run(["sh", VM], root=tmp_root), 2)
shutil.rmtree(tmp_root, ignore_errors=True)

# ---------------------------------------------------------------------------
print("\n== git 側の関門(githooks/pre-push を直接叩く) ==")
HEAD = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
BASE = subprocess.run(["git", "rev-parse", "HEAD~1"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
_stdin = f"refs/heads/x {HEAD} refs/heads/x {BASE}\n"
show("台帳と一致していれば押し出しは通る",
     run(["sh", PRE, "origin", "https://example.invalid/r.git"], _stdin), 0)
shutil.copy(VM, bak)
open(VM, "a").write("\n#x\n")
show("フックが改変されていれば押し出しは止まる",
     run(["sh", PRE, "origin", "https://example.invalid/r.git"], _stdin), 1)
shutil.move(bak, VM)
show("復元後は通る", run(["sh", PRE, "origin", "https://example.invalid/r.git"], _stdin), 0)

# ---------------------------------------------------------------------------
print("\n== ③(a) 保護パスへの書き込み拒否 ==")
hk = tempfile.mkdtemp()
os.makedirs(os.path.join(hk, ".claude", "state"), exist_ok=True)
show("オーナーの逐語への Edit は止まる",
     hook("deny_protected_paths.sh", _pre("Edit", ROOT + "/docs/PROJECT_GOAL.md"), hk), 2)
show("フックへの Edit は止まる",
     hook("deny_protected_paths.sh", _pre("Edit", ROOT + "/.claude/hooks/x.sh"), hk), 2)
show("settings.json への Write は止まる",
     hook("deny_protected_paths.sh", _pre("Write", ROOT + "/.claude/settings.json"), hk), 2)
show("普通の文書への Edit は通る",
     hook("deny_protected_paths.sh", _pre("Edit", ROOT + "/docs/OWNER_LOG.md"), hk), 0)
open(os.path.join(hk, ".claude", "state", "owner_unlock_intent"), "w").close()
show("解除ファイルがあれば通る(穴であることを測る)",
     hook("deny_protected_paths.sh", _pre("Edit", ROOT + "/docs/PROJECT_GOAL.md"), hk), 0)
os.remove(os.path.join(hk, ".claude", "state", "owner_unlock_intent"))

# ---------------------------------------------------------------------------
print("\n== ③(b) 選択待ちの全面停止 / ゴール未読の書き込み ==")
hk2 = tempfile.mkdtemp()
os.makedirs(os.path.join(hk2, ".claude", "state"), exist_ok=True)
show("ゴール未読で書き始めようとすると止まる",
     hook("owner_options_gate.sh", _pre("Write", ROOT + "/src/x.py"), hk2), 2)
show("記録(ACTION_LOG)は例外で通る",
     hook("owner_options_gate.sh", _pre("Edit", ROOT + "/docs/AUDITOR/ACTION_LOG.md"), hk2), 0)
hook("owner_options_gate.sh", _pre("Read", ROOT + "/docs/PROJECT_GOAL.md"), hk2)
show("ゴールを開いた後は通る",
     hook("owner_options_gate.sh", _pre("Write", ROOT + "/src/x.py"), hk2), 0)
open(os.path.join(hk2, ".claude", "state", "awaiting_owner_choice"), "w").write("試験")
show("選択待ちなら Bash も止まる(案 A = 全面停止)",
     hook("owner_options_gate.sh", _pre("Bash", cmd="ls"), hk2), 2)
hook("owner_options_gate.sh", {"hook_event_name": "UserPromptSubmit"}, hk2)
show("オーナーの発言で待ちが解ける",
     hook("owner_options_gate.sh", _pre("Bash", cmd="ls"), hk2), 0)

# ---------------------------------------------------------------------------
print("\n== settings.json の健全性 ==")


def _settings_clean(path):
    """(a) 上位に `_` 始まり / 非 ASCII の鍵が無い、(b) hooks の組と各項目に決まった鍵以外が無い、
    (c) 上位鍵が `docs/AUDITOR/claude-code-settings.schema.json` の `properties` に含まれる。
    I-010(2026-09-16): 辞書型の未知キー 1 つで CLI が `hooks` を丸ごと無視した。
    公開スキーマは未知キーを許すが CLI 内部の検証は厳しかった(実測)ので、厳しい側に合わせる。"""
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception:
        return 1
    bad = 0
    try:
        props = set(json.load(open(os.path.join(ROOT, "docs", "AUDITOR",
                    "claude-code-settings.schema.json"), encoding="utf-8")).get("properties", {}))
    except Exception:
        props = None
    for k in d:
        if k.startswith("_") or not k.isascii():
            bad = 1
        if props is not None and k not in props:
            bad = 1
    for _ev, arr in (d.get("hooks") or {}).items():
        for g in arr:
            if set(g) - {"matcher", "hooks"}:
                bad = 1
            for h in g.get("hooks", []):
                if set(h) - {"type", "command", "timeout"}:
                    bad = 1
    return bad


def _referenced_hooks(path):
    d = json.load(open(path, encoding="utf-8"))
    out = []
    for _ev, arr in (d.get("hooks") or {}).items():
        for g in arr:
            for h in g.get("hooks", []):
                cmd = h.get("command", "")
                if "/.claude/hooks/" in cmd:
                    out.append(cmd.split("/.claude/hooks/", 1)[1].split()[0].strip('"'))
    return out


def _all_exist(names):
    return all(os.path.isfile(os.path.join(HOOKS, n)) for n in names)


show("スキーマ外の鍵が無い(通る側)", _settings_clean(SETTINGS), 0)
_tmp_s = os.path.join(tempfile.mkdtemp(), "settings.json")
json.dump({"hooks": {}, "_退避": {"hooks": {}}}, open(_tmp_s, "w"))
show("辞書型の未知キーがあれば落ちる(止まる側 = I-010 の型)", _settings_clean(_tmp_s), 1)
json.dump({"hooks": {}, "backup": {"hooks": {}}}, open(_tmp_s, "w"))
show("ASCII 名の別名の辞書があっても落ちる(止まる側)", _settings_clean(_tmp_s), 1)
_refs = _referenced_hooks(SETTINGS)
show(f"参照するフック {len(_refs)} 件が全部実在する(通る側)", _all_exist(_refs), True)
show("消したフックを参照していれば落ちる(止まる側 = I-012 の型)",
     _all_exist(_refs + ["deleted_hook.sh"]), False)
show("残したフック 6 本 + jev_notice.sh(L-218、表示だけ)だけを参照している",
     sorted(set(_refs)),
     sorted(["_verify_manifest.sh", "deny_protected_paths.sh", "jev_notice.sh", "owner_options_gate.sh",
             "owner_turn_digest.sh", "session_start_digest.sh", "trace_snapshot.sh"]))

# ---------------------------------------------------------------------------
print("\n== 台帳 HOOK_MANIFEST.sha256 の健全性 ==")
_rows = [l.split() for l in open(MANIFEST, encoding="utf-8") if l.strip()]
show("台帳に載ったファイルが全部実在する(通る側 = I-012 の型を実物で)",
     all(os.path.isfile(os.path.join(ROOT, f)) for _h, f in _rows), True)
show("台帳に載ったファイルの指紋が全部一致する",
     all(hashlib.sha256(open(os.path.join(ROOT, f), "rb").read()).hexdigest() == h for h, f in _rows), True)
show("フックのディレクトリにあるファイルが全部台帳に載っている",
     sorted(os.listdir(HOOKS)), sorted(f.split("/")[-1] for _h, f in _rows if f.startswith(".claude/hooks/")))

for _t in (hk, hk2):
    shutil.rmtree(_t, ignore_errors=True)

print(f"\n食い違い: {FAIL} 件")
raise SystemExit(1 if FAIL else 0)
