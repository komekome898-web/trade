import json, sys
sys.path.insert(0, 'scripts')
from jev.client import JevClient
c = JevClient(model='jev-1.13.0')
purpose = "清算の監視による値段の上がりすぎ下がりすぎやトレンド転換を捉えることができるか確認 (owner's stated purpose, verbatim Japanese: 'confirm whether monitoring liquidations can capture price overshoot/undershoot and trend reversals')"
q_quantity = "reach_back rate: whether, within h minutes after a liquidation cascade, the trade price returned to the volume-weighted average price of the preceding W hours (a binary reached / not reached per cascade, averaged over cascades)"
q_control = "matched control: for each cascade, a random time on the same day with no liquidation, matched 1:1 on the thinness of the price bin (bin_pct); the control's distance from its own W-hour VWAP is not matched"
alt_quantity = "signed price change: the price move within h minutes after the cascade, signed so that negative means the price moved against the cascade direction (reversal) and positive means it continued in the cascade direction, in basis points"
conclusion_v1 = "The mechanism hypothesis 'fuel exhaustion -> price returns' is refuted: the cascades' reach-back rate to the pre-cascade VWAP within 240 minutes (0.471) is lower than the matched control's (0.537), significant. Reading: a few minutes of bounce exist, but seen over 4 hours the price is less likely to return to its pre-cascade level; the direction is opposite to what the hypothesis assumed."
S = {"owner_purpose": purpose, "judgment_quantity": q_quantity, "control_group": q_control,
     "alternative_quantity_available_in_the_same_output": alt_quantity, "report_conclusion": conclusion_v1,
     "fact_about_groups": "cascades start on average farther from the W-hour VWAP than the control times do (the cascade itself moves price away from the VWAP)"}
def noul(instr, yes, no): return {"type": "noul", "instructions": instr, "criteria": {"true": yes, "false": no}}
Q = {
 "quantity_measures_purpose": noul("Does `judgment_quantity` directly measure what `owner_purpose` asks, namely whether price overshoots and then reverses (or continues) after a liquidation? Answer yes only if the quantity's value directly expresses reversal versus continuation, not a proxy such as reaching a fixed reference level.", "the quantity directly expresses reversal/continuation after the cascade", "it measures something else or only a proxy"),
 "quantity_confounded_by_start": noul("Given `judgment_quantity`, `control_group` and `fact_about_groups`: is the value of `judgment_quantity` strongly determined by how far the price starts from the reference level (the W-hour VWAP), a property that the control matching does not equalize between cascades and controls?", "the start distance largely determines the quantity and is not matched", "the quantity does not depend on start distance, or the matching equalizes it"),
 "alternative_is_more_direct": noul("Is `alternative_quantity_available_in_the_same_output` a more direct measure of `owner_purpose` than `judgment_quantity`?", "the alternative expresses reversal versus continuation more directly", "it does not"),
 "conclusion_answers_purpose": noul("Does `report_conclusion` answer the question in `owner_purpose` (whether liquidation monitoring captures overshoot and reversal)?", "the conclusion states, from the measurement, whether overshoot/reversal is captured", "it answers a different question (e.g. whether price returns to a reference level) or does not answer"),
 "conclusion_direction_supported": noul("Does the measurement described in `judgment_quantity` and `control_group` support the conclusion's claim that 'the direction is opposite to what the hypothesis assumed' (i.e. that price does not reverse after cascades)? Consider `fact_about_groups`.", "a lower reach-back rate than the control establishes that price does not reverse", "a lower reach-back rate can arise from a farther starting point and does not by itself establish absence of reversal"),
 "other_cause_named": noul("Does `report_conclusion` name any cause other than the mechanism (such as a difference in starting distance between the groups) that could produce the observed difference?", "at least one alternative cause is named", "none is named"),
}
r = c.evaluate(S, Q)
print(json.dumps(r, ensure_ascii=False)[:2500])
