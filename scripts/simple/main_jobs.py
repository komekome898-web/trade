"""マチルダの本測定(段 1)の 33 本の引数と、族ごとのジョブの文書を作る(PLAN.md §1.2・§2、L-888・L-889)。

使い方: PYTHONPATH=src python3 scripts/simple/main_jobs.py > docs/DISCUSSIONS/2026-10-08_matilda_main/JOBS.md
本の引数は、原典の値(BASE_PARAMS)に上書きする鍵だけを書く。本測定の基準は原典の値に MAIN_BASE を上書きしたもの
(L-890「**段数の基準は5 エントリーセッティング4 イグジットセッティング3**」)。どの本の JSON にも MAIN_BASE を入れる。
値の出所は PLAN.md §1.2 の表と §1.4(門は分布の点)。

L-903(2026-10-09)で、測定のセッションの仕事に取引の行と標準の表の作成を足した(手順 5〜7)。
「**採用します。次回の測定から委任できるようにしておいてください。**」。段 1 の JOBS.md はこの前の版で作った記録なので作り直さない。
前半・後半の境 CUT は測定ごとに 1 つ(「**境の統一は必要だが**」)。基準の期間の日数の真ん中の日を、走らせる前に決める。
手順 6 の `--cut` は `diag_tables.py` の口(L-903・L-905 で足した。後半の最初の日を渡す)。
"""
from __future__ import annotations

import json

from bot.strategy.matilda_simple import BASE_PARAMS

MAIN_BASE = {"levels": 5, "entry_setting": 4, "exit_setting": 3}
# alert_count = (vola_count = range_count) × foot の分 × 倍(基準は × 0.5。FAMILIES_TO_MEASURE.md の注・L-787)
FAMILIES = {
    "base": [("base", {})],
    "levels": [(f"levels_{v}", {"levels": v}) for v in (1, 3, 7)],
    "foot": [("foot_5", {"foot": 5, "alert_count": 40 * 5 * 0.5})],
    "count": [(f"count_{v}", {"vola_count": v, "range_count": v, "alert_count": v * 1 * 0.5}) for v in (20, 80)],
    "alert": [(f"alert_x{m}", {"alert_count": 40 * 1 * m}) for m in (1, 2)],
    "entry_exit": [(f"entry_exit_{e}_{x}", {"entry_setting": e, "exit_setting": x}) for e, x in ((3, 2), (2, 1))],
    "step": [(f"step_{v}", {"step_setting": v}) for v in (2, 4)],
    "break_dist": [(f"break_dist_{v}", {"break_dist": v}) for v in (0.25, 1)],
    "break_len_mult": [("break_len_mult_4", {"break_len_mult": 4})],
    "beard": [("beard_off", {"beard_ignore": None})],
    "break_delay": [(f"break_delay_{v}", {"break_delay": v}) for v in (2, 3, 4, 8)],
    "break_off": [("break_off", {"break_delay": 0})],
    "range_lo": [("range_lo_none", {"range_setting": None})]
    + [(f"range_lo_p{q}", {"range_setting": v}) for q, v in ((10, 0.001857), (25, 0.003010), (50, 0.005133))],
    "range_hi": [(f"range_hi_p{q}", {"over_range_setting": v}) for q, v in ((75, 0.008844), (90, 0.014995))]
    + [("range_hi_none", {"over_range_setting": None})],
    "vola_gate": [(f"vola_gate_p{q}", {"vola_setting": v}) for q, v in ((10, 0.000170), (25, 0.000276), (50, 0.000465))],
}
OUT = "backtest_runs_shared/matilda_main"
TRADES = OUT + "_trades"
TABLES = "docs/RESEARCH/matilda_main"
# 基準の期間(2015-12-01〜2023-12-17 の UTC の日、2,939 日)の真ん中の日 = 後半の最初の日(diag_tables の days[len // 2] と同じ決め方)
CUT = "2019-12-09"


def alert_min(over: dict) -> float:
    """その本の alert_count(分。foot 1 の足のとき)。取引の行の late_levels と、合図の有効期間(× 2)に使う。"""
    return float({**BASE_PARAMS, **MAIN_BASE, **over}["alert_count"])


def main():
    n = sum(len(v) for v in FAMILIES.values())
    print("# マチルダの本測定(段 1)— ジョブ\n")
    print("- 出所(オーナーの逐語): L-888「**測定は別セッションで族毎に並行で走らせてください。**」・L-889「**2 よい 3 よい**」"
          "(2 = 走らせの台本の引数の上書き口、3 = 出力を git に入れる)・"
          "L-890「**段数の基準は5 エントリーセッティング4 イグジットセッティング3 これを踏まえて族を切り方を変えてください**」。計画は `docs/DISCUSSIONS/2026-10-08_matilda_main/PLAN.md`。")
    print(f"- 本数: {len(FAMILIES)} 族・{n} 本。この文書は `scripts/simple/main_jobs.py` が作った(手で直さない)。")
    print("- 上限: 各本 1 回。失敗した本は打ち直さない。\n")
    print("## 打つもの(どの族も同じ。<族> の節の本を上から順に)\n")
    print("1. `pip install -e \".[dev]\" -q` と `PYTHONPATH=src python -m pytest tests/simple`(落ちたら止まる)")
    print("2. 本ごとに(1 本 約 10 分なので Bash の道具の run_in_background で。ログは /tmp/<本の名前>.log):\n")
    print(f"       PYTHONPATH=src python3 scripts/simple/run_one.py {OUT}/<本の名前> --params '<引数の JSON>'\n")
    print("3. 本ごとに `report.json` の `params` が下の表の JSON を基準に上書きしたものと同じかを出す"
          "(python で `BASE_PARAMS` の写しに JSON を update して == で比べる)。")
    print("4. 本ごとに置き場のファイルの大きさを出す(`ls -la`)。1 ファイルが 50 MB を超えたら git に入れず、止めて報告する。")
    print("5. 本ごとに、約定の列から取引の行を作る(<alert> は下の表の列):\n")
    print(f"       PYTHONPATH=src python3 scripts/analysis/simple_trades.py --run {OUT}/<本の名前> --out {TRADES}/<本の名前> --alert-min <alert>\n")
    print("6. 本ごとに、標準の表(読み口 D0・D1・D3・D6)を作る(<valid> は下の表の列。前半・後半の境は全部の本で同じ):\n")
    print(f"       PYTHONPATH=src python3 scripts/analysis/diag_tables.py --run {TRADES}/<本の名前> --out {TABLES}/<本の名前>/diag_tables.md --valid-min <valid> --cut {CUT}\n")
    print("7. 本ごとに、取引の一生と合図の表(D4・D5)を作る(1 本 約 6 分なので run_in_background で):\n")
    print(f"       PYTHONPATH=src python3 scripts/analysis/diag_paths.py --run {TRADES}/<本の名前> --out {TABLES}/<本の名前>/diag_paths.md\n")
    print("   基準との比べ(D7)はセッションでは作らない(並行のセッションに基準の本が無い)。リードが受け取りで作る。\n")
    print("## 決まり\n")
    print("- `backtest_data/phase2_sealed/` と `docs/RESEARCH/WINDOW1/` は読まない(ls・grep・find を含む)。台本は 2023-12-17T15:00Z より後を読まない(台本の門)。")
    print("- 各コマンドは 1 回だけ。失敗したら打ち直さず、コマンド・戻り値・ログの末尾 50 行を報告する。")
    print(f"- 終わったら、自分の族の本の置き場({OUT}/<本の名前>・{TRADES}/<本の名前>・{TABLES}/<本の名前>)だけを `git add` し、英語の短い文でコミットして、指定の枝に押し出す。"
          "押し出しの関門で止まったら、関門の出力を報告して止まる(関門・フックを変えない、--no-verify を使わない)。")
    print("- 台本・試験・文書を直さない。読みや判断を書かない。\n")
    print("## 報告(日本語)\n")
    print("- 着手前の表(CLAUDE.md §0.1)と完了見込み時間(内訳)")
    print("- 本ごとに: コマンド・戻り値・所要時間・ログの末尾 5 行・3 の比べの結果・4 の大きさ・5〜7 の戻り値と出力の末尾 3 行")
    print("- コミットの番号\n")
    for fam, runs in FAMILIES.items():
        print(f"## 族 {fam}({len(runs)} 本。枝 `claude/matilda-main-{fam}`)\n")
        print("| 本の名前 | 引数の JSON(原典の値に上書きする鍵だけ。本測定の基準 levels 5・entry 4・exit 3 を含む) | alert | valid |")
        print("|---|---|---|---|")
        for name, over in runs:
            a = alert_min(over)
            print(f"| {name} | `{json.dumps({**MAIN_BASE, **over})}` | {a:g} | {2 * a:g} |")
        print()


if __name__ == "__main__":
    main()
