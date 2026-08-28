"""JPX (Osaka Exchange) execution layer: kabuステーションAPI client + ON1 executor.

Deliberately shares NO order code with bot/exchange/ — different venue, different
API, different failure modes (docs/ON1_LIVE_PLAN.md "実装アーキテクチャ").  Only
the design principles cross over: the SAFE/AMBIGUOUS/REJECTED taxonomy,
STATE_UNKNOWN with no auto-retry, a file-persisted kill switch, and the
env + config double gate.
"""
