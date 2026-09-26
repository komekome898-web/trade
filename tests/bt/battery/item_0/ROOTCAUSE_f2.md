# 項目 0 場面集の直し f2(台本の機械の検査 bf1-touch・bf1-tests への答え)

オーナー逐語(L-451): 「**は？？？案1みたいなこと前に承認しましたよね？なぜあいもかわらず無限の無意味な作業を続けてるんですか？**」
この回は指摘 2 件の根本原因を書き、場面集の側で落ちていた試験 1 件(i0-r17-03)だけを直した。新しい直しの輪は始めていない。

## 指摘 1 件ごとの根本原因

### bf1-touch(場面係の差分に場面集の外のファイル: docs/OWNER_LOG.md)
- 根本原因(事実): 台本の検査は `git diff --name-only HEAD` = 作業木全体の差分を場面係の差分として読む。リードが同じ作業木で並行して書いたファイルがそのまま場面係の差分に数えられる。前の起動の OWNER_LOG.md はリードの L-450・L-451 の追記で、場面係は触れていない。
- この回の実測: 同じコマンドの出力に CLAUDE.md・docs/AUDITOR/TRACE/…・docs/INCIDENTS.md・docs/OWNER_LOG.md・scripts/check_bt_delegation.py が出る(末尾の貼り付け)。**場面係はこの 5 件のどれにも触れていない**(この回に書いたのは tests/bt/battery/item_0/ の 3 件と materials/f2/ の写しだけ)。
- 変える作り(場面集の側では直せない。リードに聞くこと 1): 検査を「起動の前の `git diff --name-only HEAD` との差」で測る。場面集の側で OWNER_LOG.md を戻すのはリードの記録を消すことになるので、しない。

### bf1-tests(場面集の試験が通っていない)
- 根本原因(事実): 検査の範囲 `tests/bt/battery/item_0/` + `tests/bt/critic/item_0/` に、**実装の側**の批評家の試験が入っている。直す前の実測は 15 failed, 548 passed(`materials/f2/item0_f2_before_scene_and_critic_tests.log`)。落ちた 15 件のファイル別:
  - test_i0r17_forged_frozendict_key_hash_unfolds.py 6 件(i0-r17-01、実装)
  - test_i0r17_walk_memo_keeps_no_object.py 6 件(i0-r17-01、実装)
  - test_i0r17_where_text_memory.py 2 件(i0-r17-02、実装)
  - test_i0r17_driver_error_credited_as_tool_refusal.py 1 件(i0-r17-03、**場面集**)
- 実装の側の 14 件は src/bot/bt/ の直しでしか通らない。場面係は src/bot/bt/ に触れない(起動文)。L-451 で「批評家の残りは項目 4 に持ち越す」と決まっている。**したがって tests_passed はこの範囲では場面係がどう直しても true にならない。**このまま台本が「通っていなければ止める → 場面係を起こし直す」を回すと、終わらない輪になる(オーナーの L-451 の指摘そのもの)。
- 変える作り: 場面集の側の 1 件(i0-r17-03)は直した(下)。検査の範囲から持ち越しの実装の側の試験を外すかはリードに聞くこと 2。

## 主張の表(この直しが触る主張の族 = 「道具が断った」と数える主張)

| (a) 導く関数 | (b) 手書きが残る部分 | (c) 手書きが残れば落ちる試験 | (d) mutant |
|---|---|---|---|
| opponents/barter_adapter.py: `BarterAdapter._de`(`DRIVER_DE` に無い名前は送らず ValueError。driver の出力が「unknown deserializer」なら ValueError。それ以外の `de_error` だけ CompiledRefusal)→ run_battery.py `refusal_problem` | `DRIVER_DE` の 4 つの名前(driver の Rust の `match` の腕の写し)。機械で導けない理由: 変換済みの driver は二進で、腕の表を問い合わせる口が無い。代わりに (c) が 61.log の driver の元の文から腕を読み、写しと食い違えば落ちる | tests/bt/battery/item_0/test_battery_f2_driver_refusal.py: `test_the_driver_arms_are_read_and_every_entry_calls_one`、`test_only_a_received_call_is_credited`(名前 6 × driver の出力 4 の全格子)/ 批評家の tests/bt/critic/item_0/test_i0r17_driver_error_credited_as_tool_refusal.py | 2 か所の検めを `if False:` にした mutant で 11 failed, 16 passed(`materials/f2/item0_f2_mutant.log`)。戻して 25 passed |

同じ種類の欠陥の探索: 場面集の全体で `CompiledRefusal(` を送る所は barter_adapter.py の 1 か所だけ(`grep -rn 'CompiledRefusal(' tests/bt/battery/item_0/`)。走らせ直しは要らない: 既存の呼び出しの名前は全部 driver の腕にあり(試験 1 本目で確かめた)、実在の driver は腕の名前で「unknown deserializer」を出さないので、survey_results の値は変わらない(批評家の文にも「today no barter NO_INT cell is a credited refusal」)。

格子に入れなかったもの(試験のファイルにも書いた): 1 回の呼び出しで複数の鍵を印字する出力(driver は 1 呼び出し 1 鍵: 61.log 377-382)、設定された driver 以外の二進。

## リードに聞くこと
1. 台本の検査 bf1-touch を、起動の前の差分からの増分で測る形に変えてよいか(今のままだとリードの並行の書き込みで毎回止まる)。
2. 台本の検査 bf1-tests の範囲から、L-451 で項目 4 に持ち越した実装の側の批評家の試験(i0-r17-01・02 の 3 ファイル 14 件)を外してよいか。外さない限り場面係の直しでは通らず、輪が終わらない。

(リードの答え(正の定義 F など)の内容は変えていない。)
