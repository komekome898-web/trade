"""`scripts/jev_reply.py` の抽出・経路一覧の読み込み・合成の境界・`--last-assistant` を検査する。

この道具は何も止めない。出すのは確率と要確認の印だけである(オーナー逐語 L-218)。

ネットワークには一切触れない(Jev へ送る経路は `--dry-run` でしか通さない)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import scripts.jev_reply as R  # noqa: E402


# ---------------------------------------------------------------------------
# 合成した返答
# ---------------------------------------------------------------------------
PLAIN_NEGATIVE = """清算の履歴はどこにも無い。Binance Vision の該当ファイルが 404 だった。
"""

POLITE_NEGATIVE = "群 D は未実施です。この環境に ANTHROPIC_API_KEY がありません。測るなら鍵を置いてください。\n"

WITH_CHECKS = """この環境のディスクに当該ファイルは無い。

確かめたこと:

```
ls data/liquidations -> 0 件
git log --all --diff-filter=D -- data/liquidations -> 0 件
```

オーナー PC は未確認である。
"""

MAPPING_MD = """# 着手前の対応表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 1・2・3 を全部作る | 「1〜3全てやる」 |
| ついでにコミットして押し出す | **(該当語なし)** |
| テストを足す |  |
"""


def test_routes_yaml_loads_three_classes():
    classes = R.load_routes()
    assert set(classes) == {"data_or_file", "run_model_or_service", "capability"}
    for spec in classes.values():
        assert spec["routes"], "経路が空の種類がある"
        for route in spec["routes"]:
            assert route["id"] and route["name"] and route["words"]


def test_routes_available_hides_the_code_only_words():
    avail = R.routes_available(R.load_routes())
    for spec in avail.values():
        for route in spec["routes"]:
            assert set(route) == {"id", "name"}, "`words` は code のものなので送らない"


def test_extract_negative_claim_plain_form():
    pairs = R.extract_route_pairs(PLAIN_NEGATIVE, R.load_routes())
    assert len(pairs) == 1
    assert pairs[0]["kind"] == "route_coverage"
    assert "無い" in pairs[0]["claim"]


def test_extract_negative_claim_polite_form():
    """敬体の否定(`jev_check` の語では当たらない)も拾う。"""
    pairs = R.extract_route_pairs(POLITE_NEGATIVE, R.load_routes())
    claims = [p["claim"] for p in pairs]
    assert any("ありません" in c for c in claims), claims


def test_negative_claims_does_not_leak_the_swapped_pattern():
    """語の差し替えは呼び出しの中だけで、`jev_check` 側の語を書き換えたままにしない。"""
    import scripts.jev_check as J
    before = J.NEGATIVE_RE
    R.negative_claims(POLITE_NEGATIVE)
    assert J.NEGATIVE_RE is before


def test_checks_and_routes_checked():
    checks = R.extract_checks(WITH_CHECKS)
    assert any("ls " in c or "git log" in c for c in checks)
    checked = R.routes_checked(R.load_routes(), checks)
    assert "git_history" in checked
    assert "local_disk" in checked


def test_state_for_route_pair_carries_all_classes():
    pairs = R.extract_route_pairs(WITH_CHECKS, R.load_routes())
    state = pairs[0]["state"]
    assert set(state) == {"claim", "checks_in_reply", "routes_available", "routes_checked"}
    assert set(state["routes_available"]) == {
        "data_or_file", "run_model_or_service", "capability"}


def test_mapping_table_empty_right_is_flagged_by_code_only():
    pairs = R.extract_mapping_pairs(MAPPING_MD)
    kinds = [p["kind"] for p in pairs]
    assert kinds.count("mapping_empty_right") == 2, pairs
    assert kinds.count("mapping_row") == 1, pairs
    row = next(p for p in pairs if p["kind"] == "mapping_row")
    assert row["state"]["owner_quote"].strip("「」") == "1〜3全てやる"
    assert row["state"]["planned_action"] == "1・2・3 を全部作る"
    for p in pairs:
        if p["kind"] == "mapping_empty_right":
            assert p["state"] is None, "空の行は Jev へ送らない"


def test_mapping_table_ignores_other_tables():
    other = "| 名前 | 値 |\n|---|---|\n| a | 1 |\n"
    assert R.extract_mapping_pairs(other) == []


# ---------------------------------------------------------------------------
# 合成(境界)
# ---------------------------------------------------------------------------
def _answers(presence: float, covered: float, pushes: float = 0.0) -> dict:
    return {
        "is_unavailability_claim": {"noul": presence},
        "all_routes_covered": {"noul": covered},
        "pushes_to_owner": {"noul": pushes},
        "claim_class": {"probabilities": {"data_or_file": 0.7, "capability": 0.3},
                        "confidence": 0.7},
    }


def test_combine_route_needs_both_presence_and_violation():
    # presence がちょうど PRESENCE、反する側がちょうど ATTENTION → 印
    on = R.combine_route(_answers(R.PRESENCE, 1.0 - R.ATTENTION))
    assert on["flag"] is True
    assert on["reason"] is None
    # presence が足りない → 印は付けず、理由を残す(対は捨てない)
    off = R.combine_route(_answers(R.PRESENCE - 0.01, 0.0))
    assert off["flag"] is False
    assert off["reason"] == "not_unavailability_claim"
    # 反する側がしきい値の 1 つ下 → 印なし
    near = R.combine_route(_answers(0.9, 1.0 - R.ATTENTION + 0.01))
    assert near["flag"] is False


def test_combine_route_pushes_to_owner_is_a_separate_flag():
    rec = R.combine_route(_answers(0.1, 1.0, pushes=R.PRESENCE))
    assert rec["flag"] is False
    assert rec["pushes_to_owner_flag"] is True
    assert R.combine_route(_answers(0.1, 1.0, pushes=R.PRESENCE - 0.01))[
        "pushes_to_owner_flag"] is False


def test_combine_mapping_flags_exceeds_at_threshold():
    probs = {"within": 0.6, "exceeds": R.ATTENTION, "unrelated": 0.05}
    assert R.combine_mapping({"relation": {"probabilities": probs}})["flag"] is True
    probs2 = dict(probs, exceeds=R.ATTENTION - 0.01)
    assert R.combine_mapping({"relation": {"probabilities": probs2}})["flag"] is False


# ---------------------------------------------------------------------------
# 入力
# ---------------------------------------------------------------------------
def _record(tmp_path: Path) -> Path:
    rows = [
        {"message": {"role": "user", "content": "最初の指示"}},
        {"message": {"role": "assistant",
                     "content": [{"type": "text", "text": "古い返答"}]}},
        {"message": {"role": "user", "content": [{"type": "tool_result", "content": "結果"}]}},
        {"message": {"role": "assistant",
                     "content": [{"type": "text", "text": "最後の返答。鍵がありません。"},
                                 {"type": "tool_use", "name": "Bash",
                                  "input": {"command": "ls"}}]}},
    ]
    path = tmp_path / "rec.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                    encoding="utf-8")
    return path


def test_last_assistant_text_takes_the_last_one(tmp_path):
    text = R.last_assistant_text(_record(tmp_path))
    assert text == "最後の返答。鍵がありません。"


def test_cli_last_assistant_dry_run(tmp_path, capsys):
    out = tmp_path / "out"
    code = R.main(["--last-assistant", "--record", str(_record(tmp_path)),
                   "--out", str(out), "--dry-run"])
    assert code == 0
    printed = capsys.readouterr().out
    assert "--dry-run" in printed
    files = list(out.glob("*.jsonl"))
    assert len(files) == 1
    lines = [json.loads(x) for x in files[0].read_text(encoding="utf-8").splitlines()]
    assert lines[-1]["kind"] == "_summary"
    assert lines[-1]["dry_run"] is True
    assert lines[-1]["n_requests"] == 0


def test_cli_text_dry_run_sends_nothing(tmp_path, capsys):
    src = tmp_path / "reply.txt"
    src.write_text(MAPPING_MD + "\n" + POLITE_NEGATIVE, encoding="utf-8")
    out = tmp_path / "out"
    assert R.main(["--text", str(src), "--out", str(out), "--dry-run", "--summary"]) == 0
    printed = capsys.readouterr().out.strip().splitlines()
    assert printed[-1].startswith("印 ")
    recs = [json.loads(x) for x in
            list(out.glob("*.jsonl"))[0].read_text(encoding="utf-8").splitlines()]
    # 右が空の行は --dry-run でも code だけで印が付く
    assert any(r.get("reason") == "empty_right" and r["flag"] for r in recs)
    assert all(r.get("sent") is False for r in recs if r["kind"] != "_summary")
