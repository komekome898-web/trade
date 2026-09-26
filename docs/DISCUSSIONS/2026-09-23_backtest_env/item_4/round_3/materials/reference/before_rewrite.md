# 参照実装の役: 直す前に落ちる記録(2026-09-26)

打ったこと(1 回の Bash): 新しい `bar_sim.py` を scratchpad に退避 → HEAD の旧 `src/bot/bt/reference/bar_sim.py`(`git show HEAD:src/bot/bt/reference/bar_sim.py`)を同じ場所に置く → 新しい試験 2 本を回す → 新しい版を戻し、`cmp` で戻ったことを確かめた。旧の版の中身は読んでいない(置き換えて試験を回しただけ)。

```
PYTHONPATH=src python -m pytest -p no:cacheprovider -o tmp_path_retention_policy=none --basetemp=<scratchpad>/bt/ref/before_basetemp tests/bt/item_4/reference/test_i4ref_rules_scenes.py tests/bt/item_4/reference/test_i4ref_rules_properties.py
```

末尾の行(逐語):

```
=========================== short test summary info ============================
ERROR tests/bt/item_4/reference/test_i4ref_rules_scenes.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.16s
```

読み: 旧の版は入口の形が違い(規則の文の選択肢 = 発注額・費用 4 つ・持ち越し・構造的な逆指値・率の逆指値と利確・maker の利確を 1 つの options で受ける形が無い)、新しい試験は集めの段で落ちる。旧の版の SPEC.md §4(書き直す前)は、I4-11 構造的な逆指値・I4-15 持ち越し・I4-16 の一部・I4-17・I4-18 を「作っていない」と書いていた(事実: 書き直す前の SPEC.md §4 の表)。
