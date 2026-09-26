import json

from bot.bt.core import CORE_CONTRACT, STRATEGY_API, EventType


def test_contract_is_json_serialisable_and_consistent_with_code():
    text = json.dumps(CORE_CONTRACT, sort_keys=True)
    assert json.loads(text) == json.loads(json.dumps(CORE_CONTRACT))
    assert CORE_CONTRACT["event_types"] == [t.value for t in EventType]
    assert CORE_CONTRACT["strategy_api"] == list(STRATEGY_API)
    assert CORE_CONTRACT["time"]["unit"] == "ns" and CORE_CONTRACT["time"]["timezone"] == "UTC"
    assert CORE_CONTRACT["resend_on_state_unknown"] is False


def test_contract_states_the_scope_of_the_visibility_guarantee():
    # i0-r2-10: the guarantee covers the context and what is reachable from
    # it by attribute access, not interpreter introspection
    vis = CORE_CONTRACT["visibility"]
    assert "attribute" in vis["scope"] and "introspection" in vis["scope"]
    assert "HistoryTruncatedError" in vis["history_limit"]
