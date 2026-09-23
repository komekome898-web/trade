import json

from bot.bt.core import CORE_CONTRACT, STRATEGY_API, EventType


def test_contract_is_json_serialisable_and_consistent_with_code():
    text = json.dumps(CORE_CONTRACT, sort_keys=True)
    assert json.loads(text) == json.loads(json.dumps(CORE_CONTRACT))
    assert CORE_CONTRACT["event_types"] == [t.value for t in EventType]
    assert CORE_CONTRACT["strategy_api"] == list(STRATEGY_API)
    assert CORE_CONTRACT["time"]["unit"] == "ns" and CORE_CONTRACT["time"]["timezone"] == "UTC"
    assert CORE_CONTRACT["resend_on_state_unknown"] is False
