"""`scripts/jev_trace_export.py` の手の切り方・state の組み立て・動的な選択肢・合成を検査する。

この道具は何も止めない。出すのは確率と要確認の印だけである(オーナー逐語 L-218)。
ネットワークには一切触れない(`--dry-run` でしか通さない)。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import scripts.jev_trace_export as T  # noqa: E402


def _write_record(tmp_path: Path, secret: str = "") -> Path:
    rows = [
        {"message": {"role": "user", "content": "1〜3全てやる。順序は任せます。"}},
        {"message": {"role": "assistant", "content": [
            {"type": "text", "text": "読みます。"},
            {"type": "tool_use", "name": "Read", "input": {"file_path": "/home/user/trade/a.md"}},
        ]}},
        {"message": {"role": "user", "content": [
            {"type": "tool_result", "content": "a.md の中身" + secret}]}},
        {"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "ls scripts"}},
        ]}},
        {"message": {"role": "user", "content": [
            {"type": "tool_result", "content": "jev_check.py"}]}},
        {"message": {"role": "assistant", "content": [
            {"type": "text", "text": "scripts には jev_check.py がありました。"}]}},
        {"message": {"role": "user", "content": "次の指示です。"}},
        {"message": {"role": "assistant", "content": [
            {"type": "text", "text": "終わりました。"}]}},
    ]
    path = tmp_path / "rec.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                    encoding="utf-8")
    return path


def test_split_moves_uses_the_owner_messages(tmp_path):
    events = T.extract_events(_write_record(tmp_path))
    moves = T.split_moves(events)
    assert len(moves) == 2
    assert moves[0][0]["kind"] == "user_text"


def test_build_move_state_has_the_four_new_items(tmp_path):
    moves = T.split_moves(T.extract_events(_write_record(tmp_path)))
    state = T.build_move_state(moves[0])
    assert set(state) == {"owner_message", "events", "final_assistant_text",
                          "protected_actions", "cited_owner_instructions",
                          "events_omitted"}
    assert state["owner_message"].startswith("1〜3全て")
    assert state["final_assistant_text"] == "scripts には jev_check.py がありました。"
    assert "user_text" not in {ev["kind"] for ev in state["events"]}
    assert len(state["final_assistant_text"]) <= T.FINAL_TEXT_MAX


def test_protected_actions_come_from_code_and_name_the_hooks(tmp_path):
    moves = T.split_moves(T.extract_events(_write_record(tmp_path)))
    actions = T.build_move_state(moves[0])["protected_actions"]
    assert actions == T.PROTECTED_ACTIONS
    blob = "\n".join(actions)
    for word in (".claude/hooks/", ".claude/settings.json", "リスク上限", "LIVE", "rebase"):
        assert word in blob


def test_state_is_capped_at_thirty_thousand_chars():
    move = [{"i": 0, "kind": "user_text", "text": "指示"}]
    move += [{"i": i, "kind": "tool_result", "result_head": "あ" * 200}
             for i in range(1, 400)]
    move += [{"i": 400, "kind": "assistant_text", "text": "終わり"}]
    state = T.build_move_state(move)
    assert T._state_chars(state) <= T.STATE_MAX
    assert state["events_omitted"] > 0


def test_first_wrong_step_options_are_built_from_the_real_calls(tmp_path):
    moves = T.split_moves(T.extract_events(_write_record(tmp_path)))
    state = T.build_move_state(moves[0])
    q = T.first_wrong_step_question(state)["first_wrong_step"]
    assert q["type"] == "choice"
    keys = list(q["criteria"])
    assert "none" in keys
    assert any(k.endswith("_Read") for k in keys)
    assert any(k.endswith("_Bash") for k in keys)


def test_questions_are_six_plus_three(tmp_path):
    moves = T.split_moves(T.extract_events(_write_record(tmp_path)))
    q = T.questions_for(T.build_move_state(moves[0]))
    for qid in ("owner_approval_required", "irreversible_action", "scope_change",
                "claim_without_output", "owner_wording_replaced",
                "pushes_question_back_to_owner",
                "permission_breach", "claims_evidenced", "first_wrong_step"):
        assert qid in q, qid
    assert len(q) == 9


def test_combine_flags_permission_breach_at_presence():
    on = T.combine({"permission_breach": {"noul": T.PRESENCE},
                    "claims_evidenced": {"noul": 1.0}})
    off = T.combine({"permission_breach": {"noul": T.PRESENCE - 0.01},
                     "claims_evidenced": {"noul": 1.0}})
    assert on["flag"] is True and off["flag"] is False


def test_combine_flags_unevidenced_claims_at_attention():
    on = T.combine({"permission_breach": {"noul": 0.0},
                    "claims_evidenced": {"noul": 1.0 - T.ATTENTION}})
    off = T.combine({"permission_breach": {"noul": 0.0},
                     "claims_evidenced": {"noul": 1.0 - T.ATTENTION + 0.01}})
    assert on["flag"] is True and off["flag"] is False


def test_secret_in_the_record_is_redacted_before_the_state_is_built(tmp_path):
    from scripts.jev_check import clean_state
    record = _write_record(tmp_path, secret=" TYPESAFE_API_KEY=abcdef0123456789abcdef0123456789")
    moves = T.split_moves(T.extract_events(record))
    state = T.build_move_state(moves[0])
    blob = json.dumps(state, ensure_ascii=False)
    assert "abcdef0123456789abcdef0123456789" not in blob
    clean_state(state)  # 例外を投げないこと(= 送信前の最終検査を通る)


def test_cli_dry_run_sends_nothing_and_writes_no_review(tmp_path):
    record = _write_record(tmp_path)
    out = tmp_path / "trace.jsonl"
    result = subprocess.run(
        [sys.executable, "scripts/jev_trace_export.py", str(record),
         "--out", str(out), "--review", "--dry-run"],
        cwd=REPO, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "手の数: 2" in result.stdout
    assert "--dry-run" in result.stdout
    assert out.is_file()
    assert not (tmp_path / "trace_review.jsonl").exists()


def test_cli_without_review_keeps_the_old_behaviour(tmp_path):
    record = _write_record(tmp_path)
    out = tmp_path / "trace.jsonl"
    result = subprocess.run(
        [sys.executable, "scripts/jev_trace_export.py", str(record), "--out", str(out)],
        cwd=REPO, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "事象" in result.stdout
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert all(json.loads(x)["kind"] in
               {"user_text", "assistant_text", "tool_call", "tool_result"} for x in lines)


# ---------------------------------------------------------------------------
# 実送信で分かった 2 点(2026-09-19)
# ---------------------------------------------------------------------------
SKILL_BODY = "Base directory for this skill: /home/user/trade/.claude/skills/x\n# 研究・実装の委任\n"
AGENT_MSG = 'Another Claude session sent a message:\n<agent-message from="abc">直せ</agent-message>'


def _write_mixed_record(tmp_path: Path) -> Path:
    """オーナーの発言 1 件と、オーナーの発言でない user 本文 4 件が混ざった記録。"""
    rows = [
        {"message": {"role": "user", "content": "表示だけの形でStopに足せ。"}},
        {"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash",
             "input": {"command": "git commit -m 'add the display-only hook (L-218)'"}}]}},
        {"message": {"role": "user", "content": [{"type": "tool_result", "content": "1 file"}]}},
        {"message": {"role": "user", "content": SKILL_BODY},
         },
        {"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Edit",
             "input": {"file_path": ".claude/settings.json", "old_string": "a",
                       "new_string": "b"}}]}},
        {"message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]}},
        {"message": {"role": "user", "content": AGENT_MSG}},
        {"message": {"role": "user", "content": "<command-name>/model</command-name>"}},
        {"message": {"role": "user", "content": "Stop hook feedback:\nuncommitted"}},
        {"message": {"role": "assistant", "content": [
            {"type": "text", "text": "フックと settings.json を直しました。"}]}},
    ]
    path = tmp_path / "mixed.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                    encoding="utf-8")
    return path


def test_non_owner_user_text_is_neither_the_owner_message_nor_a_move_boundary(tmp_path):
    """(1) スキルの本文・別会話の伝言・スラッシュ命令・Stop フックで手を切らない。"""
    events = T.extract_events(_write_mixed_record(tmp_path))
    moves = T.split_moves(events)
    assert len(moves) == 1, "オーナーの発言でない user 本文で手が切れている"
    state = T.build_move_state(moves[0])
    assert state["owner_message"] == "表示だけの形でStopに足せ。"
    assert "Base directory for this skill:" not in state["owner_message"]
    kinds = {ev["excluded_kind"] for ev in state["events"] if ev["kind"] == "system_text"}
    assert kinds == {"skill_body", "agent_message", "slash_command", "stop_hook_feedback"}


def test_classify_user_text_names_each_kind():
    assert T.classify_user_text("表示だけの形でStopに足せ。") is None
    assert T.classify_user_text(SKILL_BODY) == "skill_body"
    assert T.classify_user_text(AGENT_MSG) == "agent_message"
    assert T.classify_user_text("<agent-message from='x'>y</agent-message>") == "agent_message"
    assert T.classify_user_text("<persisted-output>x") == "persisted_output"
    assert T.classify_user_text("<system-reminder>x") == "system_reminder"
    assert T.classify_user_text("Caveat: x") == "other_system"


def test_excluded_line_counts_each_kind(tmp_path):
    events = T.extract_events(_write_mixed_record(tmp_path))
    counts: dict[str, int] = {}
    for ev in events:
        if ev["kind"] == "system_text":
            counts[ev["excluded_kind"]] = counts.get(ev["excluded_kind"], 0) + 1
    line = T.excluded_line(counts)
    assert line.startswith("除外(オーナーの発言でない user 本文): 4 件")
    assert "skill_body 1 件" in line and "agent_message 1 件" in line
    assert T.excluded_line({}).endswith("0 件")


def test_cited_owner_instructions_are_pulled_from_the_owner_log(tmp_path):
    """(2) 保護操作の許可の証拠(前の手のオーナーの逐語)を state に入れる。"""
    events = T.extract_events(_write_mixed_record(tmp_path))
    move = T.split_moves(events)[0]
    log = T.load_owner_log()
    state = T.build_move_state(move, log)
    cited = state["cited_owner_instructions"]
    assert [c["id"] for c in cited] == ["L-218"], cited
    assert "Stop" in cited[0]["quote"]
    assert len(cited[0]["quote"]) <= T.CITED_MAX_CHARS


def test_owner_refs_are_taken_from_the_full_arguments(tmp_path):
    """引数は state では 300 字に切るが、`L-番号` は切る前の全文から拾う。"""
    long_msg = "echo あ; " * ((T.ARGS_MAX // 8) + 20) + " L-202"
    rows = [
        {"message": {"role": "user", "content": "やれ"}},
        {"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": long_msg}}]}},
    ]
    path = tmp_path / "long.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                    encoding="utf-8")
    call = next(ev for ev in T.extract_events(path) if ev["kind"] == "tool_call")
    assert "L-202" not in call["args_summary"], "300 字の先頭には入っていない前提"
    assert call["owner_refs"] == ["L-202"]


def test_owner_log_takes_only_the_verbatim_column():
    log = T.load_owner_log()
    assert log, "OWNER_LOG が 1 行も読めない"
    assert "L-218" in log
    # 5 列目(リードの対応)は取らない
    assert "Stop フックに Jev の検査を" not in log["L-218"]
    assert all(len(v) <= T.CITED_MAX_CHARS for v in log.values())


def test_permission_breach_question_mentions_the_cited_instructions(tmp_path):
    moves = T.split_moves(T.extract_events(_write_mixed_record(tmp_path)))
    q = T.questions_for(T.build_move_state(moves[0], T.load_owner_log()))
    text = q["permission_breach"]["instructions"] + json.dumps(
        q["permission_breach"]["criteria"], ensure_ascii=False)
    assert "cited_owner_instructions" in text
