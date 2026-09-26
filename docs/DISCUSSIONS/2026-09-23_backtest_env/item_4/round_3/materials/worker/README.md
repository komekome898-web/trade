# 作業者(仕上げ 第 1 段)の直す前・後の記録

- `before_barmodel.txt`: 足の模型を直す前に、先に書いた格子 2 本(`test_i4_r3_time_exit_at_open_grid.py` 96 升・`test_i4_r3_maker_two_values_grid.py` 24 升)と批評家の試験 `test_i4r2_time_exit_at_the_open.py` を回した出力。33 件落ちる(時間切れの格子 23・maker の格子 8・批評家 2)。
- `after_barmodel_before_pipeline_run.txt`: 足の模型を直したあと、統合の口(`pipeline.py`)を直す前に `tests/bt/item_4 tests/bt/compat tests/bt/critic/item_4` を回した出力(`test_i4_engine_vs_independent_bar_sim.py` は参照実装の役が `bar_sim.py` を書き直し中で import が落ちるので外した)。批評家の i4-r2-03 の 6 件・i4-r2-05 の 3 件が落ちている = 統合の口の直す前の記録。
- **順序の開示**: 統合の口の格子 3 本(`test_i4_r3_origin_by_rows_grid.py`・`test_i4_r3_prereg_file_grid.py`・`test_i4_pipeline.py` の差し込み口の試験)は、統合の口を書き換えた**あと**に書いた(提出前の吟味 (6) の「先に書く」を守れていない)。直す前に落ちる記録は、上の批評家の試験 9 件の失敗だけである。新しい格子は宣言の形(fill・latency・costs・account)が変わったので、旧の統合の口に当てると型の誤り(引数が無い)で落ちるだけで、規則の検査にならない。
