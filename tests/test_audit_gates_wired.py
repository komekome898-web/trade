"""研究の関門が**呼ばれていること**を測る試験(2026-09-13、10 本目の監査、L-164)。

**なぜ指紋の台帳ではなくテストなのか。**
10 本目の監査の指摘: 共有部品 `scripts/_research_audit_gate.py` は指紋の台帳に載ったが、
**それを呼んでいる側**(`src/bot/research/sealed.py` / `scripts/phase2/p2_02_final.py` /
`scripts/judge_gates.py`)は載っていないので、呼び出しを消しても検知されない。指摘は正しい。

ただし、この 3 本は**研究のたびに手を入れる現役のコード**である。台帳に載せると
「オーナーの指示があったときだけ変更する」の対象になり、**普通の研究作業が止まる**。
(この非対称をどう扱うかはオーナーに出してある。台帳の範囲はオーナーが決めること。)

そこで、消したら**落ちる**ものを置く。指紋は「改変が差分に残る」ことしか保証しないが、
この試験は**関門が実際に呼ばれているか**を毎回の `pytest` で測る。
消せば赤くなり、赤いまま押し出せば行動の関門が止める。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))


def _audit_record(root: Path, unit: str, stage: str) -> None:
    log = root / "docs" / "AUDITOR" / "ACTION_LOG.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"> 指摘の本文 {i} 行目。これは監査役が書いた文である。" for i in range(1, 10))
    log.write_text(f"## 試験\n\n監査対象: {unit}/{stage}\n**監査役**: `owner-model-auditor`\n\n"
                   f"{body}\n\n判定: 通す\n", encoding="utf-8")


# --- 共有部品そのもの --------------------------------------------------------

def test_gate_refuses_when_no_record(tmp_path):
    from _research_audit_gate import find_audit
    ok, why = find_audit("U1", "結果", tmp_path)
    assert not ok and "読めない" in why


def test_gate_passes_with_a_record(tmp_path):
    from _research_audit_gate import find_audit
    _audit_record(tmp_path, "U1", "結果")
    ok, why = find_audit("U1", "結果", tmp_path)
    assert ok, why


def test_gate_refuses_when_the_last_verdict_is_stop(tmp_path):
    """判定は**行頭の「判定:」のうち最後のもの**だけを見る(引用を鍵にしない)。"""
    from _research_audit_gate import find_audit
    _audit_record(tmp_path, "U1", "結果")
    log = tmp_path / "docs" / "AUDITOR" / "ACTION_LOG.md"
    log.write_text(log.read_text(encoding="utf-8") + "\n判定: 止める\n", encoding="utf-8")
    ok, why = find_audit("U1", "結果", tmp_path)
    assert not ok and "止める" in why


def test_gate_refuses_a_thin_record(tmp_path):
    """見出しだけの空の追記では通さない。"""
    from _research_audit_gate import find_audit
    log = tmp_path / "docs" / "AUDITOR" / "ACTION_LOG.md"
    log.parent.mkdir(parents=True)
    log.write_text("## x\n\n監査対象: U1/結果\n`owner-model-auditor`\n\n判定: 通す\n",
                   encoding="utf-8")
    ok, why = find_audit("U1", "結果", tmp_path)
    assert not ok and "本文" in why


# --- 呼び出し口が生きているか(消したらここが落ちる)-------------------------

def test_load_sealed_calls_the_gate():
    """`bot.research.sealed.load_sealed` が 4 つ目の門を持っていること。"""
    import inspect
    from bot.research import sealed
    src = inspect.getsource(sealed.load_sealed)
    assert "_research_audit_gate" in src, "load_sealed から監査の門が消えている"
    assert "封印の開封" in src


def test_p2_02_check_guards_calls_the_gate():
    """`load_sealed` の二重実装にも同じ門があること(片方だけ塞がない)。"""
    text = (ROOT / "scripts" / "phase2" / "p2_02_final.py").read_text(encoding="utf-8")
    assert "_research_audit_gate" in text, "check_guards から監査の門が消えている"
    assert "封印の開封" in text


def test_judge_gates_requires_a_unit():
    """`judge_gates.py` に**関門を通らない経路が無い**こと。

    10 本目の監査の指摘: `--no-audit-gate` を消しても、`--unit` を省けば
    関門は呼ばれず結果が出ていた。旗の名前が消えただけで挙動は同じだった。
    """
    text = (ROOT / "scripts" / "judge_gates.py").read_text(encoding="utf-8")
    assert "--no-audit-gate" not in text.replace("`--no-audit-gate`", ""), \
        "関門を外す旗が復活している"
    assert 'ap.add_argument("--unit", required=True' in text, \
        "--unit が必須でないと、省くだけで関門を通らずに結果が出る"
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "judge_gates.py")],
                         capture_output=True, text=True, cwd=str(ROOT))
    assert out.returncode != 0
    assert "--unit" in out.stderr


def test_o3c_reaction_judge_calls_the_gate():
    """段 A の読みのスクリプトが関門を呼んでいること(走行前の再監査(4 回目)の指摘 9)。

    **呼び出しを消すとここが赤くなる。**前版はこの道具が試験に無く、
    `require_audit("o3c_reaction_20260918", "結果")` を消してもテストが通っていた
    (`CLAUDE.md` §5.0 の「関門が呼ばれていることを毎回の pytest で測る」が
    この道具に掛かっていなかった)。

    **`scripts/_research_audit_gate.py` の `WIRED` の一覧への追記は、
    このファイルが指紋の台帳(`docs/AUDITOR/HOOK_MANIFEST.sha256`)に載っているため
    行えていない**(処置書 `2026-09-18_reaction_prereg_r4.md` の 9 に経緯を書いた)。
    **一覧に無いことをここで測ると、追記されるまで赤いままになるので測らない。**
    """
    text = (ROOT / "scripts" / "o3c_reaction_judge.py").read_text(encoding="utf-8")
    assert "_research_audit_gate" in text, "読みのスクリプトから監査の門が消えている"
    assert 'require_audit(UNIT, "結果"' in text, "require_audit の呼び出しが消えている"
    assert 'UNIT = "o3c_reaction_20260918"' in text, "単位名が変わっている"
    # 関門を外す旗を作っていないこと
    assert "--no-gate" not in text and "--no-audit-gate" not in text
    # 表を書く前に呼んでいること(最初の write_csv より前)
    assert (text.index("pass_audit_gate(Path(a.root)")
            < text.index('write_csv(out / "judgment_576.csv"'))


def test_o3c_reaction_judge_gate_actually_stops_the_write(tmp_path):
    """**呼ばれていることを、止まるはずの操作で測る**(`CLAUDE.md` §3 の「実測」の形)。

    台帳が無い根を渡すと、終了コード 1 で**出力ディレクトリが 1 つもできない**。

    **走行前の再監査(5 回目)の指摘 12 で、走行の `params` の検査が関門より前に入った。**
    そこで**判定の走行の形に `summary.json` を差し替えた一時ディレクトリ**を渡し、
    **止めるのが関門であること**を測る(迂回する旗は作っていない)。
    """
    import importlib.util
    import json as _json

    spec = importlib.util.spec_from_file_location(
        "o3c_reaction_judge_wired", ROOT / "scripts" / "o3c_reaction_judge.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    smp = ROOT / "backtest_data" / "o3c_reaction_20260918_sample"
    if not (smp / "gap60_w8" / "table.csv").exists():
        pytest.skip("標本 6 日の出力が無い")

    approval = "L-200"

    def place(src: Path, dst: Path, *, mode: str, n_days: int, window_hours: float):
        dst.mkdir(parents=True, exist_ok=True)
        for n in ("table.csv", "table_mixed.csv"):
            if (src / n).exists():
                (dst / n).write_bytes((src / n).read_bytes())
        # **走行前の再監査(6 回目)の指摘 1・2**: 凍結した入力 4 つと承認の L 番号も
        # `params` の検査に入ったので、**関門より前で止まらないように**そろえて置く。
        params = {"mode": mode, "days": [f"day{i:04d}" for i in range(n_days)],
                  "window_hours": float(window_hours), "gap_ms": 60000,
                  "bin_pct": mod.BIN_PCT_FIXED, "seed": mod.RUN_SEED_FIXED,
                  "mmr": mod.MMR_FIXED, "match_order": mod.MATCH_ORDER_FIXED}
        if mode == "full":
            params["approval"] = approval
        (dst / "summary.json").write_text(_json.dumps({"params": params}),
                                          encoding="utf-8")
        return dst

    # **指摘 2**: 承認の L 番号は事前登録 §14.4 の欄から読む。
    # **台帳(ACTION_LOG)だけが無い根**を作り、止めるのが関門であることを測る。
    empty_root = tmp_path / "empty_root"
    prereg = empty_root / mod.PREREG_REL
    prereg.parent.mkdir(parents=True, exist_ok=True)
    prereg.write_text(f"   **応答の L 番号**: **{approval}**\n", encoding="utf-8")

    r8 = place(smp / "gap60_w8", tmp_path / "run_w8",
               mode="full", n_days=mod.JUDGMENT_N_DAYS, window_hours=8)
    r24 = place(smp / "gap60_w24", tmp_path / "run_w24",
                mode="full", n_days=mod.JUDGMENT_N_DAYS, window_hours=24)
    s8 = place(smp / "gap60_w8", tmp_path / "sample_w8",
               mode="sample", n_days=mod.SAMPLE_N_DAYS, window_hours=8)
    s24 = place(smp / "gap60_w24", tmp_path / "sample_w24",
                mode="sample", n_days=mod.SAMPLE_N_DAYS, window_hours=24)
    out = tmp_path / "out"
    # **決定 2'''''(7 回目の指摘 2)**: `--sens` は §14.2 の 4 本を必ず渡す
    # (渡さないと関門の前で止まるので、**止めたのが関門であること**が測れない)。
    # 中身の無い感度は「その表だけ書かない」経路に落ちるだけで、判定の側は止めない。
    sens = []
    for nm in mod.SENS_REQUIRED:
        sens += ["--sens", f"{nm}={tmp_path / 'sens_missing' / nm}"]
    # **決定 4''''(6 回目の指摘 4)**: `REPS` は差し替えない(差し替えると関門の前で止まる)。
    with pytest.raises(SystemExit) as e:
        mod.main(["--run-w8", str(r8), "--run-w24", str(r24),
                  "--sample-w8", str(s8), "--sample-w24", str(s24),
                  "--out-dir", str(out), "--root", str(empty_root)] + sens)
    assert e.value.code == 1
    assert not out.exists(), "関門が閉じているのに出力ディレクトリができている"


@pytest.mark.parametrize("unit,stage", [("U1", "封印の開封"), ("U1", "結果")])
def test_require_audit_exits_with_2(tmp_path, unit, stage):
    from _research_audit_gate import require_audit
    with pytest.raises(SystemExit) as e:
        require_audit(unit, stage, tmp_path)
    assert e.value.code == 2


def test_gate_ignores_the_key_quoted_in_prose(tmp_path):
    """**鍵は行頭に固定されていること(14 本目の監査の一括点検)。**

    台帳は監査役の指摘を逐語で載せるので、鍵の文字列が地の文の引用として現れる
    (実例: ACTION_LOG 561 行目)。`find_audit` は「最後に現れた鍵」を節の先頭にするので、
    行頭固定でないと**後から書いた引用が本物の記録を上書きする**。
    """
    from _research_audit_gate import find_audit
    _audit_record(tmp_path, "U1", "結果")            # 本物(判定: 通す)
    log = tmp_path / "docs" / "AUDITOR" / "ACTION_LOG.md"
    log.write_text(log.read_text(encoding="utf-8")
                   + "\n## 別の節\n\n> 監査役は「監査対象: U1/結果」の節を作れと書いた。\n"
                     "\n判定: 止める\n", encoding="utf-8")
    ok, why = find_audit("U1", "結果", tmp_path)
    assert ok, f"地の文の引用が本物の記録を上書きしている: {why}"
