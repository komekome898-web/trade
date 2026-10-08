"""マチルダの本測定(段 1)の 33 本の引数と、族ごとのジョブの文書を作る(PLAN.md §1.2・§2、L-888・L-889)。

使い方: python3 scripts/simple/main_jobs.py > docs/DISCUSSIONS/2026-10-08_matilda_main/JOBS.md
本の引数は基準(BASE_PARAMS)に上書きする鍵だけを書く。値の出所は PLAN.md §1.2 の表と §1.4(門は分布の点)。
"""
from __future__ import annotations

import json

# alert_count = (vola_count = range_count) × foot の分 × 倍(基準は × 0.5。FAMILIES_TO_MEASURE.md の注・L-787)
FAMILIES = {
    "base": [("base", {})],
    "levels": [(f"levels_{v}", {"levels": v}) for v in (1, 3, 5)],
    "foot": [("foot_5", {"foot": 5, "alert_count": 40 * 5 * 0.5})],
    "count": [(f"count_{v}", {"vola_count": v, "range_count": v, "alert_count": v * 1 * 0.5}) for v in (20, 80)],
    "alert": [(f"alert_x{m}", {"alert_count": 40 * 1 * m}) for m in (1, 2)],
    "entry_exit": [(f"entry_exit_{e}_{x}", {"entry_setting": e, "exit_setting": x}) for e, x in ((3, 2), (4, 3), (2, 1))],
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


def main():
    n = sum(len(v) for v in FAMILIES.values())
    print("# マチルダの本測定(段 1)— ジョブ\n")
    print("- 出所(オーナーの逐語): L-888「**測定は別セッションで族毎に並行で走らせてください。**」・L-889「**2 よい 3 よい**」"
          "(2 = 走らせの台本の引数の上書き口、3 = 出力を git に入れる)。計画は `docs/DISCUSSIONS/2026-10-08_matilda_main/PLAN.md`。")
    print(f"- 本数: {len(FAMILIES)} 族・{n} 本。この文書は `scripts/simple/main_jobs.py` が作った(手で直さない)。")
    print("- 上限: 各本 1 回。失敗した本は打ち直さない。\n")
    print("## 打つもの(どの族も同じ。<族> の節の本を上から順に)\n")
    print("1. `pip install -e \".[dev]\" -q` と `PYTHONPATH=src python -m pytest tests/simple`(落ちたら止まる)")
    print("2. 本ごとに(1 本 約 10 分なので Bash の道具の run_in_background で。ログは /tmp/<本の名前>.log):\n")
    print(f"       PYTHONPATH=src python3 scripts/simple/run_one.py {OUT}/<本の名前> --params '<引数の JSON>'\n")
    print("3. 本ごとに `report.json` の `params` が下の表の JSON を基準に上書きしたものと同じかを出す"
          "(python で `BASE_PARAMS` に JSON を update して == で比べる)。")
    print("4. 本ごとに置き場のファイルの大きさを出す(`ls -la`)。1 ファイルが 50 MB を超えたら git に入れず、止めて報告する。\n")
    print("## 決まり\n")
    print("- `backtest_data/phase2_sealed/` と `docs/RESEARCH/WINDOW1/` は読まない(ls・grep・find を含む)。台本は 2023-12-17T15:00Z より後を読まない(台本の門)。")
    print("- 各コマンドは 1 回だけ。失敗したら打ち直さず、コマンド・戻り値・ログの末尾 50 行を報告する。")
    print("- 終わったら、自分の族の本の置き場だけを `git add` し、英語の短い文でコミットして、指定の枝に押し出す。"
          "押し出しの関門で止まったら、関門の出力を報告して止まる(関門・フックを変えない、--no-verify を使わない)。")
    print("- 台本・試験・文書を直さない。読みや判断を書かない。\n")
    print("## 報告(日本語)\n")
    print("- 着手前の表(CLAUDE.md §0.1)と完了見込み時間(内訳)")
    print("- 本ごとに: コマンド・戻り値・所要時間・ログの末尾 5 行・3 の比べの結果・4 の大きさ")
    print("- コミットの番号\n")
    for fam, runs in FAMILIES.items():
        print(f"## 族 {fam}({len(runs)} 本。枝 `claude/matilda-main-{fam}`)\n")
        print("| 本の名前 | 引数の JSON(基準に上書きする鍵だけ) |")
        print("|---|---|")
        for name, over in runs:
            print(f"| {name} | `{json.dumps(over)}` |")
        print()


if __name__ == "__main__":
    main()
