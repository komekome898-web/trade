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
- G5 記録の停止: 共有に毎日届く流れ(`paper_logs/<流れ>/<種類>_<日付>.*`)のうち、最新の日が、共有全体の最新の日より
  2 日以上遅れているもの(記録が止まった・共有から漏れた)があり、`docs/DATA.md` §8.1 に「停止」の行が無いとき、
  返答の終わり(Stop)を止める(L-987 で足した。10-05 で止まった venues を、G1〜G4 では見つけられなかった)。
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


HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")


def strip_heredocs(cmd: str) -> str:
    """ヒアドキュメントの本文(コマンドではなく文字)を外す。本文を読む側(python など)は、その行で別に判定される。"""
    out, term = [], None
    for line in (cmd or "").split("\n"):
        if term is not None:
            if line.strip() == term:
                term = None
            continue
        out.append(line)
        m = HEREDOC.search(line)
        if m:
            term = m.group(2)
    return "\n".join(out)


def segments(cmd: str) -> list[str]:
    """引用の外の ; && || | 改行で区切る(引用の中の | などでは区切らない)。"""
    text = strip_heredocs(cmd)
    out, cur, q, i = [], [], None, 0
    while i < len(text):
        c = text[i]
        if q:
            cur.append(c)
            if c == q:
                q = None
            elif c == "\\" and q == '"' and i + 1 < len(text):
                cur.append(text[i + 1])
                i += 1
        elif c in "'\"":
            q = c
            cur.append(c)
        elif c in ";|\n" or (c == "&" and text[i:i + 2] == "&&"):
            out.append("".join(cur))
            cur = []
            if text[i:i + 2] in ("&&", "||"):
                i += 1
        else:
            cur.append(c)
        i += 1
    out.append("".join(cur))
    res = []
    for s in out:
        s = re.sub(r"^\(+", "", s.strip()).strip()
        if s.startswith("cd ") or not s:
            continue
        res.append(s)
    return res


def unquoted(seg: str) -> str:
    """単引用の中身を外し、二重引用は中身の $ と ` だけ残す(ワイルドカードの判定用)。"""
    s = re.sub(r"'[^']*'", "''", seg)
    return re.sub(r'"([^"\\]|\\.)*"', lambda m: '"' + "".join(re.findall(r"\$\(|\$\{?[A-Za-z_]|`", m.group(0))) + '"', s)


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
    # 共有(既定ブランチ)に届いていて、まだ合流していない置き場も「持っている」に数える
    # (合流の承認を待つ間に、合流しないと消えない欠けで返答の終わりの門が詰まらないように。L-990)
    _, share_list = git(["ls-tree", "-r", "--name-only", SHARE_REF, "--", "backtest_data"], base, 30)
    share_paths = share_list.splitlines()
    for name, pat, fname, step, keep_days in COVERAGE:
        ts = []
        texts = []
        local = {str(p.relative_to(base)) for p in base.glob(f"{pat}/{fname}")}
        for rp in sorted(local):
            texts.append((base / rp).read_text(encoding="utf-8"))
        prefix = pat.replace("*", "")
        for sp in share_paths:
            if sp.startswith(prefix) and sp.endswith("/" + fname) and sp not in local:
                rc, txt = git(["show", f"{SHARE_REF}:{sp}"], base, 30)
                if rc == 0:
                    texts.append(txt)
        for txt in texts:
            for line in txt.splitlines()[1:]:
                try:
                    ts.append(datetime.fromisoformat(line.split(",", 1)[0]).astimezone(timezone.utc).replace(tzinfo=None))
                except ValueError:
                    continue
        # 保持の中で、まだ取り元にある範囲。次の取得で埋まる見込みの新しい側の空白は数えず、
        # 取り元から消えるまで 1 日を切った空白(始まりが「今 − (保持 − 1 日)」より古い)だけを数える
        start = now - timedelta(days=keep_days) + timedelta(hours=1)
        end = now - timedelta(minutes=2 * step)
        at_risk = now - timedelta(days=keep_days - 1)
        for a, b in coverage_gaps(ts, step, start, end):
            if a >= at_risk:
                continue
            key = a.strftime("%Y-%m-%dT%H:%M")
            if (name, key) in ledger:
                continue
            out.append(f"{name} {key}〜{b.strftime('%Y-%m-%dT%H:%M')} UTC(保持 {keep_days} 日)")
    return out


KIND = re.compile(r"^paper_logs/([^/]+)/(.+?)_?(20\d{6})[^/]*$")


def stream_lags(paths: list[str], ledger: set) -> list[str]:
    """共有の流れ(流れ/種類)ごとの最新の日が、全体の最新の日より 2 日以上遅れているもの。"""
    latest: dict[str, str] = {}
    for p in paths:
        m = KIND.match(p)
        if not m:
            continue
        k = f"{m.group(1)}/{m.group(2)}"
        if m.group(3) > latest.get(k, ""):
            latest[k] = m.group(3)
    if not latest:
        return []
    top = max(latest.values())
    topd = datetime.strptime(top, "%Y%m%d").date()
    out = []
    for k, d in sorted(latest.items()):
        lag = (topd - datetime.strptime(d, "%Y%m%d").date()).days
        if lag >= 2 and (k, "停止") not in ledger:
            out.append(f"paper_logs/{k}: 最新 {d[:4]}-{d[4:6]}-{d[6:]}(共有全体の最新 {top[:4]}-{top[4:6]}-{top[6:]} より {lag} 日遅れ)")
    return out


def g5_problems(base: Path) -> list[str]:
    md = (base / DATA_MD).read_text(encoding="utf-8") if (base / DATA_MD).exists() else ""
    ref = SHARE_REF if git(["rev-parse", "--verify", "-q", SHARE_REF], base, 10)[0] == 0 else "HEAD"
    _, out = git(["ls-tree", "-r", "--name-only", ref, "--", "paper_logs"], base, 30)
    return stream_lags(out.splitlines(), parse_gap_ledger(md))


def g4_problems(base: Path, now: datetime | None = None) -> list[str]:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    md = (base / DATA_MD).read_text(encoding="utf-8") if (base / DATA_MD).exists() else ""
    ledger = parse_gap_ledger(md)
    return bitflyer_missing(base, now.date(), ledger) + okx_missing(base, now, ledger)


# ---------------------------------------------------------------- 判定(フックの入口)

OPAQUE = (
    # 中で何を読むかがコマンドの文字に出ない操作(台本の実行・ワイルドカード・再帰の走査・置き換え)
    re.compile(r"^(\S+=\S*\s+)*(python3?|sh|bash|zsh|node|perl|ruby|Rscript|uv|pipx?|make|exec|xargs|env|timeout|nohup|source|\.)\b"),
    re.compile(r"^(\S+=\S*\s+)*\./"),
    re.compile(r"[*?\[]"),
    re.compile(r"^(find|du|tree|rg|ag|rsync|tar|zip|unzip|7z)\b"),
    re.compile(r"^(grep|egrep|zgrep)\b.*\s-[a-zA-Z]*[rR]"),
    re.compile(r"^ls\b.*\s-[a-zA-Z]*R"),
    re.compile(r"\$\(|`|\$\{?[A-Za-z_]"),
)
# 道具の前に付けてよい前置き(時間の上限・切り離し・PYTHONPATH)。前置きを付けただけで直しの道具が止まらないように
RUN_PREFIX = r"^(?:timeout\s+\d+[smh]?\s+)?(?:nohup\s+)?(?:PYTHONPATH=\S+\s+)?"
ALWAYS_OK = (
    # 門が閉じていても通す: 取り込み・補充・登録簿の道具、コミット、フックの台帳、門そのものの試験
    re.compile(r"^git\s"),
    re.compile(RUN_PREFIX + r"python3?\s+scripts/(intake_ledger|data_quality|share_reconcile|data_gates|fetch_[\w]+|retention_snapshot)\.py\b"),
    # 直しの道具の置き場(L-990「データ不備→直そうとするがそれすらも止められて…何もできなくなったらアホすぎる」)。
    # データを取り直す・直す台本はここに置けば、どの門が閉じていても走らせられる。中身は git の差分に残る。
    re.compile(RUN_PREFIX + r"python3?\s+scripts/data_repair/[\w]+\.py\b"),
    # 置き場の整理(消す・移す・写す・作る・一覧)は直す操作なので止めない。中身を読む操作(cat・zcat・head など)は止める
    re.compile(r"^(rm|mv|cp|mkdir|touch|ls|stat|wc\s+-c|md5sum|sha256sum)\b"),
    re.compile(r"^(sh\s+)?scripts/analysis/commit_gate\.sh\b"),
    re.compile(r"^(sh\s+)?scripts/regen_hook_manifest\.sh\b"),
    re.compile(r"^(PYTHONPATH=\S+\s+)?python3?\s+-m\s+pytest\s+tests/test_data_gates\.py\b"),
)
G3_OK = (
    # 登録簿を読む前でも通すもの: 書く・送る側の git と、門の状態を見るだけの道具
    re.compile(r"^git\s+(commit|add|push|fetch|merge|pull|rm|mv|restore|status|log)\b"),
    re.compile(r"^(PYTHONPATH=\S+\s+)?python3?\s+scripts/data_gates\.py\b"),
    re.compile(r"^(sh\s+)?scripts/(analysis/commit_gate|regen_hook_manifest)\.sh\b"),
    re.compile(r"^(PYTHONPATH=\S+\s+)?python3?\s+-m\s+pytest\s+tests/test_data_gates\.py\b"),
)


def opaque(seg: str) -> bool:
    return any(p.search(unquoted(seg)) for p in OPAQUE)


def G1_MSG(pending):
    what = "参照が無い(先に git fetch origin " + SHARE_BRANCH + ")" if pending is None else f"{pending} 本"
    return (f"[門 G1 取り込み] 既定ブランチ {SHARE_BRANCH} に、作業ブランチへ合流していない PC の共有がある({what})。"
            "取り込むまで、データ・研究の置き場に触る操作と、中で何を読むか見えない操作(台本の実行・ワイルドカード・再帰の走査)を止める。"
            "通るのは git・scripts の取り込み・補充・登録簿の道具・コミットの関門だけ。"
            "次に打つ: python3 scripts/share_reconcile.py → 照合の表を記録してから git merge")


G3_MSG = ("[門 G3 見る] この会話でまだ docs/DATA.md を読んでいない。データを探す・読む前と、中で何を読むか見えない操作"
          "(台本の実行・ワイルドカード・再帰の走査)の前に、docs/DATA.md(データの登録簿)を Read で読む"
          "(L-984「データ探すときに見るねん」)。")
G2_MSG = ("[門 G2 登録簿] docs/DATA.md が git に載ったデータの置き場と合っていない。登録簿を最新にするまで、研究の置き場に触る操作と"
          "中で何を読むか見えない操作を止める。次に打つ: python3 scripts/data_gates.py status(足りない行の一覧)")


def pretool_decision(tool: str, ti: dict, *, base: Path, pending: int | None, data_md_read: bool,
                     registry_ok: bool) -> str | None:
    """止めるなら理由の文、通すなら None。"""
    g1 = pending is None or pending > 0
    g3 = not data_md_read
    g2 = not registry_ok
    if not (g1 or g2 or g3):
        return None
    if tool == "Bash":
        for s in segments(ti.get("command") or ""):
            unseen = opaque(s)
            data = touches_data(s) or unseen
            research = touches_research(s) or unseen
            if g3 and data and not any(p.search(s) for p in G3_OK):
                return G3_MSG
            if any(p.search(s) for p in ALWAYS_OK):
                continue
            if g1 and (data or research):
                return G1_MSG(pending)
            if g2 and research:
                return G2_MSG
        return None
    paths = tool_paths(tool, ti, base)
    whole = False
    if tool == "Grep" and not ti.get("path"):
        whole = True  # 置き場を指定しない検索はリポジトリ全体(データの置き場を含む)
    if tool == "Glob" and not ti.get("path") and re.match(r"^\*", ti.get("pattern") or ""):
        whole = True
    if tool in ("Grep", "Glob") and ti.get("path") and rel(ti["path"], base) in ("", "."):
        whole = True
    data = whole or any(path_is_data(p) for p in paths)
    research = whole or any(under(p, RESEARCH_PREFIXES) for p in paths)
    if g3 and data:
        return G3_MSG
    if g1 and (data or research):
        return G1_MSG(pending)
    if g2 and research:
        return G2_MSG
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
    pending, _ = g1_pending(base)
    md_read = marker(base, d.get("session_id") or "").exists()
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
    return {"G1 取り込み": g1, "G2 登録簿": g2, "G4 欠け": g4, "G5 記録の停止": g5_problems(base)}


WAIT_DAYS = 3  # オーナー・PC の作業待ちの例外が効く日数(L-990 で承認)


def parse_waits(md: str) -> dict[str, date]:
    """§8.1 の「オーナー待ち」の行: 流れ → 依頼した日。"""
    m = re.search(r"^### 8\.1 .*?$(.*?)(?=^##+ |\Z)", md, re.M | re.S)
    out: dict[str, date] = {}
    if not m:
        return out
    for line in m.group(1).splitlines():
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[2].startswith("オーナー待ち"):
            try:
                out[cells[0]] = date.fromisoformat(cells[1][:10])
            except ValueError:
                continue
    return out


def apply_waits(probs: dict[str, list[str]], waits: dict[str, date], today: date) -> dict[str, list[str]]:
    """オーナー・PC の作業を待つもの(G1 の合流・G5 の記録の再開)だけ、依頼から WAIT_DAYS 日まで外す。
    登録簿(G2)と欠け(G4)は自分で片付けられるので外さない。"""
    live = {k for k, d in waits.items() if 0 <= (today - d).days <= WAIT_DAYS}
    out = dict(probs)
    if "共有の合流" in live:
        out["G1 取り込み"] = []
    out["G5 記録の停止"] = [x for x in probs.get("G5 記録の停止", [])
                          if x.split(":", 1)[0].replace("paper_logs/", "") not in live]
    return out


def cmd_stop() -> int:
    # 返答の終わり: 残りがあれば必ず止める(2 回目も止める。L-988「穴あるけどほっときますなんか通じるわけないやろ」)。
    # 例外はオーナー・PC の作業待ちを §8.1 に依頼日つきで書いたものだけ(L-990)。
    base = root()
    _read_stdin()
    md = (base / DATA_MD).read_text(encoding="utf-8") if (base / DATA_MD).exists() else ""
    probs = apply_waits(all_problems(base), parse_waits(md), datetime.now(timezone.utc).date())
    if not any(probs.values()):
        return 0
    lines = ["[門 データの導線] 返答を終える前に、次が残っている(L-984・L-986・L-988)。片付けてから終える。"
             "オーナー・PC の作業を待つもの(合流の承認・PC 側の記録の再開)だけは、docs/DATA.md §8.1 に"
             f"「| <流れ> | <依頼した日> | オーナー待ち: <依頼の中身> |」を書けば {WAIT_DAYS} 日まで通る。"
             "直しの台本は scripts/data_repair/ に置けば、門が閉じていても走らせられる。"]
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
    err = base / ERROR_LOG
    if err.exists() and datetime.now().timestamp() - err.stat().st_mtime < 86400:
        last_err = err.read_text(encoding="utf-8").strip().splitlines()[-1][:200]
        return f"!!! 門の台本が 24 時間以内に落ちた(落ちた間は止めずに通した): {last_err}"
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


ERROR_LOG = ".claude/state/data_gates_error.log"


def safe_main(argv: list[str]) -> int:
    """門の台本そのものが落ちたときは止めない(門の不具合でリードが何もできなくなるのを防ぐ。L-990)。
    落ちたことは記録し、オーナーの発言ごとの状態の行に出す(digest-line)。"""
    try:
        return main(argv)
    except Exception as exc:  # noqa: BLE001
        try:
            p = root() / ERROR_LOG
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as fh:
                fh.write(f"{datetime.now(timezone.utc).isoformat()} {argv[1:]} {type(exc).__name__}: {exc}\n")
        except Exception:  # noqa: BLE001
            pass
        print(f"[門 データの導線] 門の台本が落ちたので通した({type(exc).__name__}: {exc})。"
              "scripts/data_gates.py を直すこと", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(safe_main(sys.argv))
