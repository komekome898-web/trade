#!/usr/bin/env python3
"""データの導線の門 G1〜G4(オーナーの指示 2026-10-11、L-984・L-986)。

オーナーの逐語:
- L-984「**いつになったらPCの共有データ取り込むねんなんのために収集してんねんいつになったら欠落の補充すんねん
  いつになったらDATA.MDを最新の状態に更新してデータ探すときに見るねん**」
- L-986「**なんでフックの変更が消えてんねん データ絡みの導線も確実に通るように作り替えな意味ないやろ**」

経緯: 「データは最重要」(L-026・L-039・L-103・L-740)のたびに、リードは仕組み(記録器・登録簿・取り込みの台帳)を
作ったが回さなかった。表示だけのフック(UserPromptSubmit の「共有が途絶えている」)は 10 回以上読み流された。
だから門は全部「止める」(表示だけにしない)。

門:
- G1 取り込み: 既定ブランチ(PC の共有が毎朝届く)に、作業ブランチへ合流していないコミットがある間、
  データ・研究の置き場に触る道具を止める。取り込みの道具(git・照合・取り込みの台帳・品質の検査)は通す。
- G2 登録簿: git に載っているデータの置き場(`backtest_data/` の直下、`paper_logs/` の流れ)が
  `docs/DATA.md` §10 の表に無い / 表の「最新の日付」が実物より古い / 「説明の節」にその名前が無いとき、
  研究の道具と返答の終わり(Stop)を止める。
- G3 見る: その会話で `docs/DATA.md` を Read する前に、データの置き場を探す・読む道具を止める。
- G4 欠け: 取り元が消す期間(`config/constants.yaml: data_retention`)の中にある欠けが、
  取り直されていない、かつ `docs/DATA.md` §8.1 に処置の行が無いとき、返答の終わり(Stop)を止める。

限界(全部書く):
- Stop を止めるのは 1 回の返答の終わりにつき 1 回(`stop_hook_active` が真なら通す)。止め続けると、
  オーナーに見せて返事を待つべき場面(合流の前の照合の表など)で返答を終えられなくなるため。
  返答の終わりに必ず残りの一覧を突き付ける形で、終わらせない形ではない。
- G1・G3 の Bash の判定はコマンドの文字だけを見る。別のファイルの台本の中で置き場を読めば通る。
- G4 が見るのは、取り直しの手立てを持つ流れ(bitFlyer の約定、OKX の建玉 5 分・1 時間、OKX のロング・ショート比 1 時間)だけ。
  取り元が履歴を持たない流れ(清算・Hyperliquid・OKX の上位トレーダー・Deribit など、記録を始めた日からしか無いもの)の
  欠けは取り直せないので、G4 では見ない(`docs/DATA.md` §8 に書く)。
- G2 は置き場の名前と日付だけを見る。説明の中身が正しいかは見ない。
- 効いているかは、止まるはずの操作をして確かめるしかない(CLAUDE.md §3)。

Usage:
    python3 scripts/data_gates.py status          # 4 つの門の状態
    python3 scripts/data_gates.py fetch           # 既定ブランチを取ってくる(UserPromptSubmit・SessionStart)
    python3 scripts/data_gates.py registry-table  # §10 の表の行の下書き(置き場・最新の日付)を出す
    (pretool / posttool / stop は フックが標準入力の JSON で呼ぶ)
"""
from __future__ import annotations

import gzip
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SHARE_BRANCH = "claude/bitflyer-trading-bot-hhxxaf"
SHARE_REF = f"origin/{SHARE_BRANCH}"
DATA_MD = "docs/DATA.md"
STATE_DIR = ".claude/state"

DATA_ROOTS = ("backtest_data", "paper_logs", "data")
RESEARCH_PREFIXES = ("scripts/analysis/", "docs/RESEARCH/", "docs/ANALYSIS/")
SEALED_PREFIXES = ("backtest_data/phase2_sealed",)

# G1 の間も通す Bash(取り込みの道具)。コマンドの区切りごとに、置き場に触る区切りはこのどれかで始まること。
G1_ALLOWED = (
    re.compile(r"^git\s"),
    re.compile(r"^(python3?|PYTHONPATH=\S+\s+python3?)\s+scripts/(intake_ledger|data_quality|share_reconcile|data_gates|fetch_[\w]+|retention_snapshot)\.py\b"),
)
# G3 で探す・読むとみなさない git の操作(書く・送る側)。
G3_GIT_EXEMPT = re.compile(r"^git\s+(commit|add|push|fetch|merge|pull|rm|mv|restore)\b")
# G2 の間も通す研究の置き場の道具(コミットの関門は研究ではない)。
G2_ALLOWED_BASH = (re.compile(r"^(sh\s+)?scripts/analysis/commit_gate\.sh\b"),)

DATE8 = re.compile(r"(?<!\d)(20\d{6})(?!\d)")


# ---------------------------------------------------------------- 共通

def root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(env) if env else Path(__file__).resolve().parent.parent


def git(args: list[str], cwd: Path, timeout: int = 20) -> tuple[int, str]:
    try:
        p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def rel(p: str, base: Path) -> str:
    p = os.path.normpath(p or "")
    b = str(base)
    if p == b:
        return ""
    if p.startswith(b + os.sep):
        p = p[len(b) + 1:]
    if p.startswith("./"):
        p = p[2:]
    return p.replace(os.sep, "/")


def under(path: str, prefixes) -> bool:
    return any(path == x.rstrip("/") or path.startswith(x.rstrip("/") + "/") for x in prefixes)


def segments(cmd: str) -> list[str]:
    out = []
    for s in re.split(r"&&|\|\||[;|\n]", cmd or ""):
        s = s.strip()
        # 先頭の cd / 環境変数の代入 / サブシェルの括弧は外す
        s = re.sub(r"^\(+", "", s).strip()
        if s.startswith("cd "):
            continue
        if s:
            out.append(s)
    return out


ROOT_TOKEN = re.compile(r"(?:^|[\s'\"=(:,])(?:\./|/home/user/trade/|\$ROOT/|\$CLAUDE_PROJECT_DIR/)?(backtest_data|paper_logs)(?:/|\b)|(?:^|[\s'\"=(:,])(?:\./|/home/user/trade/)?data/")
RESEARCH_TOKEN = re.compile(r"(scripts/analysis/|docs/RESEARCH/|docs/ANALYSIS/)")


def touches_data(text: str) -> bool:
    return bool(ROOT_TOKEN.search(text or ""))


def path_is_data(p: str) -> bool:
    return under(p, DATA_ROOTS) or bool(re.search(r"(^|/|\*\*/)(backtest_data|paper_logs)(/|$)", p or ""))


def touches_research(text: str) -> bool:
    return bool(RESEARCH_TOKEN.search(text or ""))


def tool_paths(tool: str, ti: dict, base: Path) -> list[str]:
    """Read/Glob/Grep/Edit/Write/NotebookEdit が触る道(相対)。"""
    out = []
    for k in ("file_path", "path", "notebook_path"):
        if ti.get(k):
            out.append(rel(ti[k], base))
    if tool in ("Glob", "Grep"):
        pat = ti.get("pattern") or ""
        if tool == "Glob":
            base_dir = rel(ti.get("path") or str(base), base)
            out.append((base_dir + "/" + pat).lstrip("/") if base_dir else pat)
        if ti.get("glob"):
            out.append(ti["glob"])
    return out


# ---------------------------------------------------------------- G1

def g1_pending(base: Path) -> tuple[int | None, str]:
    """既定ブランチにあって作業ブランチに無いコミットの数(参照が無ければ None)と最新の日付。"""
    rc, _ = git(["rev-parse", "--verify", "-q", SHARE_REF], base, 10)
    if rc != 0:
        return None, ""
    rc, out = git(["rev-list", "--count", f"HEAD..{SHARE_REF}"], base, 10)
    if rc != 0:
        return None, ""
    n = int(out.strip() or 0)
    last = ""
    if n:
        _, last = git(["log", "-1", "--format=%ci", SHARE_REF], base, 10)
    return n, last.strip()


def g1_bash_ok(cmd: str) -> bool:
    for s in segments(cmd):
        if (touches_data(s) or touches_research(s)) and not any(p.search(s) for p in G1_ALLOWED):
            return False
    return True


# ---------------------------------------------------------------- G2

def family_of(path: str) -> str | None:
    """git に載ったファイルの道 → 置き場の名前(日付を外す)。データでないものは None。"""
    parts = path.split("/")
    if under(path, SEALED_PREFIXES):
        return None
    if parts[0] == "backtest_data" and len(parts) >= 2:
        name = parts[1]
        if name in ("MD5SUMS", "README.md", ".gitattributes"):
            return None
        name = re.sub(r"\.(csv|csv\.gz|json|jsonl|jsonl\.gz|parquet|txt|zip)$", "", name)
        name = re.sub(r"_20\d{6}(?=_|$)", "", name)
        return name
    if parts[0] == "paper_logs" and len(parts) >= 3:
        return "paper_logs/" + parts[1]
    if parts[0] == "paper_logs" and len(parts) == 2:
        n = parts[1]
        if n == "INTAKE.jsonl" or not re.search(r"\.(csv|csv\.gz|jsonl|jsonl\.gz)$", n):
            return None
        n = re.sub(r"\.(csv|csv\.gz|jsonl|jsonl\.gz)$", "", n)
        return "paper_logs/" + re.sub(r"_20\d{6}(?=_|$)", "", n)
    return None


def families(paths: list[str]) -> dict[str, str]:
    """置き場 → 最新の日付(YYYY-MM-DD、日付が無ければ "")。"""
    out: dict[str, str] = {}
    for p in paths:
        f = family_of(p)
        if f is None:
            continue
        ds = DATE8.findall(p)
        d = max(ds) if ds else ""
        d = f"{d[:4]}-{d[4:6]}-{d[6:]}" if d else ""
        if f not in out or d > out[f]:
            out[f] = d
    return out


def parse_index(md: str) -> dict[str, tuple[str, str]]:
    """§10 の表: 置き場 → (最新の日付, 説明の節)。"""
    m = re.search(r"^## 10\. .*?$(.*?)(?=^## |\Z)", md, re.M | re.S)
    out = {}
    if not m:
        return out
    for line in m.group(1).splitlines():
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and not set(cells[0]) <= set("-: ") and cells[0] != "置き場":
            out[cells[0]] = (cells[1], cells[2])
    return out


def section_text(md: str, sec: str) -> str:
    n = re.sub(r"[^\d.]", "", sec).rstrip(".")
    if not n:
        return ""
    m = re.search(rf"^##+ {re.escape(n)}[.\s].*?$(.*?)(?=^## |\Z)", md, re.M | re.S)
    return m.group(0) if m else ""


def registry_problems(fams: dict[str, str], md: str) -> list[str]:
    idx = parse_index(md)
    probs = []
    if not idx:
        probs.append("docs/DATA.md に §10(置き場の一覧)の表が無い")
    for f, d in sorted(fams.items()):
        if f not in idx:
            probs.append(f"{f}: §10 の表に行が無い(実物の最新 {d or '日付なし'})")
            continue
        got, sec = idx[f]
        if d and (not re.match(r"\d{4}-\d{2}-\d{2}$", got) or got < d):
            probs.append(f"{f}: §10 の最新の日付 {got or '空'} が実物 {d} より古い")
        name = f.split("/", 1)[1] if f.startswith("paper_logs/") else f
        if name not in section_text(md, sec):
            probs.append(f"{f}: 説明の節 {sec or '空'} にこの名前が無い")
    return probs


def tracked_paths(base: Path) -> list[str]:
    _, out = git(["ls-files", "backtest_data", "paper_logs"], base, 30)
    return [p for p in out.splitlines() if p]


# ---------------------------------------------------------------- G3

def marker(base: Path, sid: str) -> Path:
    safe = re.sub(r"[^\w.-]", "_", sid or "nosession")
    return base / STATE_DIR / f"data_md_read_{safe}"


# ---------------------------------------------------------------- G4

def parse_gap_ledger(md: str) -> set[tuple[str, str]]:
    """§8.1 の表: (流れ, 日 or 欠けの始まり) の組。"""
    m = re.search(r"^### 8\.1 .*?$(.*?)(?=^##+ |\Z)", md, re.M | re.S)
    out = set()
    if not m:
        return out
    for line in m.group(1).splitlines():
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and not set(cells[0]) <= set("-: ") and cells[0] != "流れ":
            out.add((cells[0], cells[1]))
    return out


def bitflyer_day_complete(first_ts: str, last_ts: str, day: date) -> bool:
    """丸 1 日の取り直しか。端の 10 分: 取り直した約定の記録で、日次メンテ以外の空白は最大 4 分(docs/DATA.md §1 の行、
    2026-09-18〜21 の 151,079 件)なので、端が 10 分より空いていれば取っていない側と読む。"""
    try:
        f = datetime.fromisoformat(first_ts[:19])
        l = datetime.fromisoformat(last_ts[:19])
    except ValueError:
        return False
    d0 = datetime(day.year, day.month, day.day)
    return f <= d0 + timedelta(minutes=10) and l >= d0 + timedelta(hours=23, minutes=50)


def gz_first_last(p: Path) -> tuple[str, str]:
    first = last = ""
    with gzip.open(p, "rt", encoding="utf-8", errors="replace") as fh:
        next(fh, None)
        for line in fh:
            if not first:
                first = line.split(",", 1)[0]
            last = line
    return first, last.split(",", 1)[0] if last else ""


def bitflyer_missing(base: Path, today: date, ledger: set) -> list[str]:
    days = {}
    for p in base.glob("backtest_data/bitflyer_executions_backfill_*/executions_*.csv.gz"):
        m = DATE8.search(p.name)
        if not m:
            continue
        d = datetime.strptime(m.group(1), "%Y%m%d").date()
        if d in days and days[d]:
            continue
        try:
            f, l = gz_first_last(p)
            days[d] = bitflyer_day_complete(f, l, d)
        except Exception:  # noqa: BLE001
            days[d] = False
    out = []
    for k in range(30, 0, -1):  # 31 日の保持のうち、今日(未完)を除く 30 日。古い方(先に消える)から
        d = today - timedelta(days=k)
        if days.get(d):
            continue
        if ("bitflyer_executions", d.isoformat()) in ledger:
            continue
        out.append(f"bitFlyer 約定 {d.isoformat()}(残り {31 - k} 日で取り元から消える)")
    return out


COVERAGE = (
    # (流れ, 置き場の glob, ファイル名, 刻み[分], 保持の短い側[日]) 保持は config/constants.yaml: data_retention
    ("okx_open_interest_5m", "backtest_data/auto_okx_open_interest_5m_*", "okx_btc_oi_5m.csv", 5, 2),
    ("okx_open_interest_1h", "backtest_data/auto_okx_open_interest_1h_*", "okx_btc_oi_1h.csv", 60, 30),
    ("okx_long_short_ratio_1h", "backtest_data/auto_okx_long_short_ratio_*", "okx_btc_lsratio_1h.csv", 60, 60),
)


def coverage_gaps(ts: list[datetime], step_min: int, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    """[start, end] の刻みの格子のうち、行の無い区間(連続した刻み)を (最初, 最後) で返す。"""
    step = timedelta(minutes=step_min)
    epoch = datetime(2000, 1, 1)
    k = -(-(start - epoch) // step)  # start 以上で最初の格子
    cur = epoch + k * step
    have = {t for t in ts if start - step <= t <= end + step}
    out = []
    gap_start = None
    while cur <= end:
        if cur in have:
            if gap_start is not None:
                out.append((gap_start, cur - step))
                gap_start = None
        elif gap_start is None:
            gap_start = cur
        cur += step
    if gap_start is not None:
        out.append((gap_start, cur - step))
    return out


def okx_missing(base: Path, now: datetime, ledger: set) -> list[str]:
    out = []
    for name, pat, fname, step, keep_days in COVERAGE:
        ts = []
        for p in base.glob(f"{pat}/{fname}"):
            with open(p, encoding="utf-8") as fh:
                next(fh, None)
                for line in fh:
                    try:
                        ts.append(datetime.fromisoformat(line.split(",", 1)[0]).astimezone(timezone.utc).replace(tzinfo=None))
                    except ValueError:
                        continue
        # 保持の中で、まだ取り元にある範囲だけ。終わりは 1 日前(PC の取得は 1 日 1 回)
        start = now - timedelta(days=keep_days) + timedelta(hours=1)
        end = now - timedelta(days=1)
        for a, b in coverage_gaps(ts, step, start, end):
            key = a.strftime("%Y-%m-%dT%H:%M")
            if (name, key) in ledger:
                continue
            out.append(f"{name} {key}〜{b.strftime('%Y-%m-%dT%H:%M')} UTC(保持 {keep_days} 日)")
    return out


def g4_problems(base: Path, now: datetime | None = None) -> list[str]:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    md = (base / DATA_MD).read_text(encoding="utf-8") if (base / DATA_MD).exists() else ""
    ledger = parse_gap_ledger(md)
    return bitflyer_missing(base, now.date(), ledger) + okx_missing(base, now, ledger)


# ---------------------------------------------------------------- 判定(フックの入口)

def pretool_decision(tool: str, ti: dict, *, base: Path, pending: int | None, data_md_read: bool,
                     registry_ok: bool) -> str | None:
    """止めるなら理由の文、通すなら None。"""
    if tool == "Bash":
        cmd = ti.get("command") or ""
        data = any(touches_data(s) for s in segments(cmd))
        research = any(touches_research(s) and not any(p.search(s) for p in G2_ALLOWED_BASH) for s in segments(cmd))
        paths: list[str] = []
    else:
        paths = tool_paths(tool, ti, base)
        data = any(path_is_data(p) for p in paths)
        research = any(under(p, RESEARCH_PREFIXES) for p in paths)
        cmd = ""
    if not (data or research):
        return None
    # G1
    if pending is None or pending > 0:
        if tool == "Bash" and g1_bash_ok(cmd):
            pass
        else:
            what = "参照が無い(先に git fetch origin " + SHARE_BRANCH + ")" if pending is None else f"{pending} 本"
            return (f"[門 G1 取り込み] 既定ブランチ {SHARE_BRANCH} に、作業ブランチへ合流していない PC の共有がある({what})。"
                    "照合して取り込むまで、データ・研究の置き場に触る道具を止める。"
                    "通るのは git・scripts/share_reconcile.py・intake_ledger.py・data_quality.py・data_gates.py・fetch_*.py・retention_snapshot.py だけ。"
                    "次に打つ: python3 scripts/share_reconcile.py(照合の表をオーナーに見せてから git merge)")
    # G3
    if data and not data_md_read:
        if not (tool == "Bash" and all(G3_GIT_EXEMPT.search(s) or not touches_data(s) for s in segments(cmd))):
            return ("[門 G3 見る] この会話でまだ docs/DATA.md を読んでいない。データを探す・読む前に、"
                    "docs/DATA.md(データの登録簿)の該当の節を Read で読む(L-984「データ探すときに見るねん」)。")
    # G2
    if research and not registry_ok:
        return ("[門 G2 登録簿] docs/DATA.md が git に載ったデータの置き場と合っていない。登録簿を最新にするまで研究の道具を止める。"
                "次に打つ: python3 scripts/data_gates.py status(足りない行の一覧)")
    return None


def _read_stdin() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        return {}


def cmd_pretool() -> int:
    base = root()
    d = _read_stdin()
    tool = d.get("tool_name") or ""
    ti = d.get("tool_input") or {}
    if tool not in ("Bash", "Read", "Glob", "Grep", "Edit", "Write", "MultiEdit", "NotebookEdit"):
        return 0
    paths = tool_paths(tool, ti, base)
    cmd = ti.get("command") or "" if tool == "Bash" else ""
    probe_research = touches_research(cmd) or any(under(p, RESEARCH_PREFIXES) for p in paths)
    probe_data = touches_data(cmd) or any(path_is_data(p) for p in paths)
    if not probe_research and not probe_data:
        return 0
    pending, _ = g1_pending(base)
    md_read = marker(base, d.get("session_id") or "").exists()
    reg_ok = True
    if probe_research:
        md = (base / DATA_MD).read_text(encoding="utf-8") if (base / DATA_MD).exists() else ""
        reg_ok = not registry_problems(families(tracked_paths(base)), md)
    msg = pretool_decision(tool, ti, base=base, pending=pending, data_md_read=md_read, registry_ok=reg_ok)
    if msg:
        print(msg, file=sys.stderr)
        return 2
    return 0


def cmd_posttool() -> int:
    base = root()
    d = _read_stdin()
    if (d.get("tool_name") or "") != "Read":
        return 0
    if rel((d.get("tool_input") or {}).get("file_path") or "", base) == DATA_MD:
        m = marker(base, d.get("session_id") or "")
        m.parent.mkdir(parents=True, exist_ok=True)
        m.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    return 0


def all_problems(base: Path) -> dict[str, list[str]]:
    pending, last = g1_pending(base)
    g1 = []
    if pending is None:
        g1.append(f"既定ブランチ {SHARE_BRANCH} の参照が無い(git fetch origin {SHARE_BRANCH})")
    elif pending:
        g1.append(f"既定ブランチに未取り込みの共有 {pending} 本(最新 {last})")
    md = (base / DATA_MD).read_text(encoding="utf-8") if (base / DATA_MD).exists() else ""
    g2 = registry_problems(families(tracked_paths(base)), md)
    g4 = g4_problems(base)
    return {"G1 取り込み": g1, "G2 登録簿": g2, "G4 欠け": g4}


def cmd_stop() -> int:
    base = root()
    d = _read_stdin()
    if d.get("stop_hook_active"):
        return 0
    probs = all_problems(base)
    if not any(probs.values()):
        return 0
    lines = ["[門 データの導線] 返答を終える前に、次が残っている(L-984・L-986)。片付けるか、"
             "オーナーの返事待ちならその旨を返答に書いてから終える。"]
    for k, v in probs.items():
        if v:
            lines.append(f"{k}: {len(v)} 件")
            lines += [f"  - {x}" for x in v[:15]]
            if len(v) > 15:
                lines.append(f"  - ほか {len(v) - 15} 件(python3 scripts/data_gates.py status)")
    print("\n".join(lines), file=sys.stderr)
    return 2


def cmd_fetch() -> int:
    git(["fetch", "-q", "origin", SHARE_BRANCH], root(), 25)
    return 0


def cmd_status() -> int:
    base = root()
    probs = all_problems(base)
    for k, v in probs.items():
        print(f"{k}: {'通る' if not v else f'止まる({len(v)} 件)'}")
        for x in v:
            print(f"  - {x}")
    print("G3 見る: 会話ごと(docs/DATA.md を Read すると印が付く)")
    return 0


def cmd_registry_table() -> int:
    base = root()
    for f, d in sorted(families(tracked_paths(base)).items()):
        print(f"| {f} | {d or '—'} | |")
    return 0


def digest_line(base: Path) -> str:
    pending, last = g1_pending(base)
    if pending is None:
        return f"!!! 門 G1: 既定ブランチ {SHARE_BRANCH} の参照が取れない(git fetch が失敗)。データの道具は止まる"
    if pending:
        return f"!!! 門 G1: PC の共有 {pending} 本が未取り込み(既定ブランチの最新 {last})。取り込むまでデータ・研究の道具は止まる"
    _, last = git(["log", "-1", "--format=%ci", SHARE_REF], base, 10)
    return f"PC の共有: 既定ブランチの最新 {last.strip()} まで取り込み済み"


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "status"
    if cmd == "pretool":
        return cmd_pretool()
    if cmd == "posttool":
        return cmd_posttool()
    if cmd == "stop":
        return cmd_stop()
    if cmd == "fetch":
        return cmd_fetch()
    if cmd == "digest-line":
        cmd_fetch()
        print(digest_line(root()))
        return 0
    if cmd == "registry-table":
        return cmd_registry_table()
    return cmd_status()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
