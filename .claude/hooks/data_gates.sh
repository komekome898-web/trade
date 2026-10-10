#!/bin/sh
# データの導線の門 G1〜G5 — PreToolUse / PostToolUse(Read)/ Stop
#
# オーナーの指示 2026-10-11、L-984「**いつになったらPCの共有データ取り込むねんなんのために収集してんねん
# いつになったら欠落の補充すんねん いつになったらDATA.MDを最新の状態に更新してデータ探すときに見るねん**」・
# L-986「**データ絡みの導線も確実に通るように作り替えな意味ないやろ**」・L-988「**印を作ってよい**」
# 「**穴あるけどほっときますなんか通じるわけないやろ**」。
# 経緯: 表示だけのフック(「共有が途絶えている」)は 10 回以上読み流された。だから止める形にする。
# 判定は全部 scripts/data_gates.py(試験 tests/test_data_gates.py)。このフックは呼ぶだけ。
MODE="${1:-pretool}"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT" 2>/dev/null || exit 0
exec python3 "$ROOT/scripts/data_gates.py" "$MODE"
