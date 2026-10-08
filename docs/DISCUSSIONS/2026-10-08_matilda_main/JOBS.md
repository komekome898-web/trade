# マチルダの本測定(段 1)— ジョブ

- 出所(オーナーの逐語): L-888「**測定は別セッションで族毎に並行で走らせてください。**」・L-889「**2 よい 3 よい**」(2 = 走らせの台本の引数の上書き口、3 = 出力を git に入れる)・L-890「**段数の基準は5 エントリーセッティング4 イグジットセッティング3 これを踏まえて族を切り方を変えてください**」。計画は `docs/DISCUSSIONS/2026-10-08_matilda_main/PLAN.md`。
- 本数: 15 族・32 本。この文書は `scripts/simple/main_jobs.py` が作った(手で直さない)。
- 上限: 各本 1 回。失敗した本は打ち直さない。

## 打つもの(どの族も同じ。<族> の節の本を上から順に)

1. `pip install -e ".[dev]" -q` と `PYTHONPATH=src python -m pytest tests/simple`(落ちたら止まる)
2. 本ごとに(1 本 約 10 分なので Bash の道具の run_in_background で。ログは /tmp/<本の名前>.log):

       PYTHONPATH=src python3 scripts/simple/run_one.py backtest_runs_shared/matilda_main/<本の名前> --params '<引数の JSON>'

3. 本ごとに `report.json` の `params` が下の表の JSON を基準に上書きしたものと同じかを出す(python で `BASE_PARAMS` の写しに JSON を update して == で比べる)。
4. 本ごとに置き場のファイルの大きさを出す(`ls -la`)。1 ファイルが 50 MB を超えたら git に入れず、止めて報告する。

## 決まり

- `backtest_data/phase2_sealed/` と `docs/RESEARCH/WINDOW1/` は読まない(ls・grep・find を含む)。台本は 2023-12-17T15:00Z より後を読まない(台本の門)。
- 各コマンドは 1 回だけ。失敗したら打ち直さず、コマンド・戻り値・ログの末尾 50 行を報告する。
- 終わったら、自分の族の本の置き場だけを `git add` し、英語の短い文でコミットして、指定の枝に押し出す。押し出しの関門で止まったら、関門の出力を報告して止まる(関門・フックを変えない、--no-verify を使わない)。
- 台本・試験・文書を直さない。読みや判断を書かない。

## 報告(日本語)

- 着手前の表(CLAUDE.md §0.1)と完了見込み時間(内訳)
- 本ごとに: コマンド・戻り値・所要時間・ログの末尾 5 行・3 の比べの結果・4 の大きさ
- コミットの番号

## 族 base(1 本。枝 `claude/matilda-main-base`)

| 本の名前 | 引数の JSON(原典の値に上書きする鍵だけ。本測定の基準 levels 5・entry 4・exit 3 を含む) |
|---|---|
| base | `{"levels": 5, "entry_setting": 4, "exit_setting": 3}` |

## 族 levels(3 本。枝 `claude/matilda-main-levels`)

| 本の名前 | 引数の JSON(原典の値に上書きする鍵だけ。本測定の基準 levels 5・entry 4・exit 3 を含む) |
|---|---|
| levels_1 | `{"levels": 1, "entry_setting": 4, "exit_setting": 3}` |
| levels_3 | `{"levels": 3, "entry_setting": 4, "exit_setting": 3}` |
| levels_7 | `{"levels": 7, "entry_setting": 4, "exit_setting": 3}` |

## 族 foot(1 本。枝 `claude/matilda-main-foot`)

| 本の名前 | 引数の JSON(原典の値に上書きする鍵だけ。本測定の基準 levels 5・entry 4・exit 3 を含む) |
|---|---|
| foot_5 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "foot": 5, "alert_count": 100.0}` |

## 族 count(2 本。枝 `claude/matilda-main-count`)

| 本の名前 | 引数の JSON(原典の値に上書きする鍵だけ。本測定の基準 levels 5・entry 4・exit 3 を含む) |
|---|---|
| count_20 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "vola_count": 20, "range_count": 20, "alert_count": 10.0}` |
| count_80 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "vola_count": 80, "range_count": 80, "alert_count": 40.0}` |

## 族 alert(2 本。枝 `claude/matilda-main-alert`)

| 本の名前 | 引数の JSON(原典の値に上書きする鍵だけ。本測定の基準 levels 5・entry 4・exit 3 を含む) |
|---|---|
| alert_x1 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "alert_count": 40}` |
| alert_x2 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "alert_count": 80}` |

## 族 entry_exit(2 本。枝 `claude/matilda-main-entry_exit`)

| 本の名前 | 引数の JSON(原典の値に上書きする鍵だけ。本測定の基準 levels 5・entry 4・exit 3 を含む) |
|---|---|
| entry_exit_3_2 | `{"levels": 5, "entry_setting": 3, "exit_setting": 2}` |
| entry_exit_2_1 | `{"levels": 5, "entry_setting": 2, "exit_setting": 1}` |

## 族 step(2 本。枝 `claude/matilda-main-step`)

| 本の名前 | 引数の JSON(原典の値に上書きする鍵だけ。本測定の基準 levels 5・entry 4・exit 3 を含む) |
|---|---|
| step_2 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "step_setting": 2}` |
| step_4 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "step_setting": 4}` |

## 族 break_dist(2 本。枝 `claude/matilda-main-break_dist`)

| 本の名前 | 引数の JSON(原典の値に上書きする鍵だけ。本測定の基準 levels 5・entry 4・exit 3 を含む) |
|---|---|
| break_dist_0.25 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "break_dist": 0.25}` |
| break_dist_1 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "break_dist": 1}` |

## 族 break_len_mult(1 本。枝 `claude/matilda-main-break_len_mult`)

| 本の名前 | 引数の JSON(原典の値に上書きする鍵だけ。本測定の基準 levels 5・entry 4・exit 3 を含む) |
|---|---|
| break_len_mult_4 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "break_len_mult": 4}` |

## 族 beard(1 本。枝 `claude/matilda-main-beard`)

| 本の名前 | 引数の JSON(原典の値に上書きする鍵だけ。本測定の基準 levels 5・entry 4・exit 3 を含む) |
|---|---|
| beard_off | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "beard_ignore": null}` |

## 族 break_delay(4 本。枝 `claude/matilda-main-break_delay`)

| 本の名前 | 引数の JSON(原典の値に上書きする鍵だけ。本測定の基準 levels 5・entry 4・exit 3 を含む) |
|---|---|
| break_delay_2 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "break_delay": 2}` |
| break_delay_3 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "break_delay": 3}` |
| break_delay_4 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "break_delay": 4}` |
| break_delay_8 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "break_delay": 8}` |

## 族 break_off(1 本。枝 `claude/matilda-main-break_off`)

| 本の名前 | 引数の JSON(原典の値に上書きする鍵だけ。本測定の基準 levels 5・entry 4・exit 3 を含む) |
|---|---|
| break_off | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "break_delay": 0}` |

## 族 range_lo(4 本。枝 `claude/matilda-main-range_lo`)

| 本の名前 | 引数の JSON(原典の値に上書きする鍵だけ。本測定の基準 levels 5・entry 4・exit 3 を含む) |
|---|---|
| range_lo_none | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "range_setting": null}` |
| range_lo_p10 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "range_setting": 0.001857}` |
| range_lo_p25 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "range_setting": 0.00301}` |
| range_lo_p50 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "range_setting": 0.005133}` |

## 族 range_hi(3 本。枝 `claude/matilda-main-range_hi`)

| 本の名前 | 引数の JSON(原典の値に上書きする鍵だけ。本測定の基準 levels 5・entry 4・exit 3 を含む) |
|---|---|
| range_hi_p75 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "over_range_setting": 0.008844}` |
| range_hi_p90 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "over_range_setting": 0.014995}` |
| range_hi_none | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "over_range_setting": null}` |

## 族 vola_gate(3 本。枝 `claude/matilda-main-vola_gate`)

| 本の名前 | 引数の JSON(原典の値に上書きする鍵だけ。本測定の基準 levels 5・entry 4・exit 3 を含む) |
|---|---|
| vola_gate_p10 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "vola_setting": 0.00017}` |
| vola_gate_p25 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "vola_setting": 0.000276}` |
| vola_gate_p50 | `{"levels": 5, "entry_setting": 4, "exit_setting": 3, "vola_setting": 0.000465}` |

