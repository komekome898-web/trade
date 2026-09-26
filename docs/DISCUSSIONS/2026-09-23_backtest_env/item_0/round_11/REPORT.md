# 作業者の報告(作る:0#11、agent aa35d795cfbccd2de。Workflow の記録の返り値から逐語で書き出し)

## 変えたファイル

- src/bot/bt/core/values.py(class_parts・type_name を type 自身の記述子で読む形に、exception_text を新設、_now の断りの文を exception_text に)
- src/bot/bt/core/engine.py(_usable の断りの文を exception_text に、_qualname を class_parts で、差し込み口の名前 _models を構築のときに 1 度だけ読む、知らない報告の型と _require_protocol の文を type_name に、説明の文を事実に合わせた)
- src/bot/bt/core/contract.py(core-13。lifecycle・scope・ownership・type_decisions・visibility.history_limit(1 件 16 バイト)の文)
- src/bot/bt/core/history.py(説明の文のみ: 核が読むのは戦略から届かない参照の列 _items・_overall_items の並びだけ)
- tests/bt/item_0/test_bt0_r11_foreign_objects.py(新規。格子 3 本と見張りの試験)
- tests/bt/item_0/test_bt0_r10_strategy_side.py(説明の 1 文のみ。核が読む物の記述を事実に合わせた)
- docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_11/ROOTCAUSE.md(新規。直す前の根本原因 §A〜§D と、直しの途中で見つけた同じ根の箇所 §E)
- (git commit はしていない。リードのチェックポイント 615be20 にこの周の作業の全部が入っていることを git show --stat で確かめた)

## 足した試験の数

291

## 試験のコマンド

PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 -p no:cacheprovider(ほかに、全試験(場面集を含む)を最後に 1 回だけ切り離して実行: PYTHONPATH=src python -m pytest -p no:cacheprovider。ログは /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/pytest_item0_r11_worker_{mid2,full}.log)

## 試験の末尾の行

項目 0・核・批評家の試験: 「1624 passed, 2 skipped in 324.96s (0:05:24)」(この周の初めは 1333 件。足した 291 件はすべて test_bt0_r11_foreign_objects.py)。全試験(場面集を含む。作業の最後に 1 回だけ): 「4597 passed, 6 skipped, 1 warning in 872.40s (0:14:32)」。第 10 周に落ちていた場面集の試験 3 件もこの実行で通った(場面係の直しのあとの作業木)。

## 要件の各行を満たした根拠(ファイル:行)

- 時刻は UTC の int64 ナノ秒: src/bot/bt/core/time.py 55(TIME_CONTRACT)・75(validate_nanos)。この周の変更なし
- 事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知): src/bot/bt/core/events.py 52(EventType)。この周の変更なし
- 戦略は「受け取れた時刻 ≤ 今」の事象しか見られない(構造で): api.py 696(visible_events)・900(_time_arg。今より後は LookAheadError)、window.py 61(POSITION_RULE)。history_limit の下の読み出しは、制限なしの答えと同じか正しく断る。確かめ直した神託の 375,671 読み出しで、誤り・断りすぎ・位置の誤りが 0 件
- 決定的な事象の順序(同時刻の並びの規則を明記): ordering.py 161(ORDERING_RULE)。この周の変更の前と後で配達の要約が同じ(cbc4e7073082 / 23b27a7a143c、<S>/item0_r11_worker_digest_compare.out)
- 戦略の API(事象ごとの呼び出し・発注・取消): api.py 928(STRATEGY_API)・871(place_order)・877(cancel_order)、engine.py 1082(on_event の呼び出し)。戦略のコードは on_event の中でしか走らない。この周に閉じた道は、戦略の例外の説明(engine.py 884 _usable → values.py 230 exception_text)。格子 test_a_failure_s_own_code_never_runs_and_every_later_call_is_refused(210 升目)で確かめる
- 他項目が差し込む口(約定模型・遅延模型・費用・口座): interfaces.py 226(SOCKETS)。この周の格子 1・3 の入口は、SOCKETS と socket_methods とプロトコルの戻りの注釈から機械で出した。差し込み口の名前は engine.py 758(_models)で構築のときに 1 度だけ読み、result() は差し込み口の class を読まない(test_a_socket_s_class_names_are_read_once_when_the_engine_is_built)
- 契約: contract.py 15(CORE_VERSION = core-13)・81(history_limit。1 件 16 バイト)・93(scope。後始末は対象外、例外の説明)・121(lifecycle。断りの文は例外の事実だけから)・144(ownership。戦略が届く物のうち読むのは箱だけ)、type_decisions(型の名前は type 自身の記述子)

## 満たせなかった行とその理由

- 満たせなかった要件の行: 無し。以下は委任文 §3「提出前の吟味」の記録。判定の語は書かず、候補ごとに何をしたかだけを書く
- (1) i0-r9-01 の直した根拠: 第 10 周で作り替えた api.py 807-848 行 __refuse_truncated・790-805 行 __empty_answer・history.py 241-260 行を、この周の初めに確かめ直した。コマンド `PYTHONPATH=src python3 <S>/item0_r9_critic_probe_history_until.py` → `until_ns=T0+3s -> [1, 2] place (0, 1, 3, 0)` / `n=1, until_ns=T0+3s -> [2] place (1, 1, 3, 0)` / `until_ns=T0 (before every event) -> [] place (0, 1, 3, 0)`。批評家の神託 `item0_r9_critic_probe_history_oracle.py 80` → `{'ok': 375671, 'wrong': 0, 'silent_short': 0, 'over_refused': 0, 'place_wrong': 0, 'over_refused_nonempty': 0, 'over_refused_empty': 0}`(<S>/item0_r11_worker_recheck_history_oracle.out)。LEAD_DESIGN §8.3 の答えのとおり、契約 visibility.history_limit(contract.py 81 行〜)に「落とした事象 1 件あたり 16 バイトで、実行の間ずっと増える」と書いた。<S> = /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt
- (1) i0-r9-02 の直した根拠: (a) `<S>/item0_r10_worker_probe_port_class_swap_tuple.py` → `port class now: Hook` だけで、OUTSIDE の記録も失敗も無い。(b) `<S>/item0_r10_worker_probe_closure_reach.py` → 全配達で `shared with the core's own state: []`・`callbacks with anything shared: 0`。批評家の元の試し 2 本は、この版では口を見つけられない(名前 eng._box で探す / tuple に入らない)ので止まる(ROOTCAUSE §0)
- (2) 同じ根の全箇所: 族を「戦略が核に渡す物」に広げ、道ごとに列べずに「外のコードが作った物で、核が後で持つ物」として探し直した。見つけて直したのは次の 5 か所(ROOTCAUSE §B-2・§E)。(i) FAILED の断りの文 engine.py _usable の str(failure)・type(failure).__name__: 戦略の例外の __str__ が on_event の外で走り、断りが RuntimeError になった。直す前の試し → `step -> builtins RuntimeError | is EngineFailedError: False` と `strategy code run: [('__str__', 'OUTSIDE on_event'), ×3]`、直した後 → 3 つとも `EngineFailedError: True` と `strategy code run: []`(<S>/item0_r11_worker_probe_failure_text.{before,after}.out)。(ii) values._now の断りの文が送り手の変換の例外の __str__ を走らせていた。(iii) result().models が差し込み口の class の名前を呼ばれるたびに普通の読みで取っていた。(iv) 知らない報告の型の文(engine.py の 2 か所)。(v) _require_protocol の文
- (3) 批評家の試験と場面集の試験: tests/bt/critic/item_0 は全部通る(1624 passed に入っている)。場面集は全試験の実行の中で 1 回走らせ、落ちた試験は無い(4597 passed)。規則 8 に当たる、批評家の試験自身の誤りで落ちる試験は無い
- (4) 非常に厳しい批評家が [止める] にしそうな候補 → したこと: (a)「戦略の物の後始末(__del__・weakref の呼び戻し)は核の手順の中でも走る」→ 解釈系が物を放すときに走るので、核には止められない。届くのは戦略が届く物だけで、核はそれを判断に使わない。契約 scope に「対象外」として書き、リードに聞く。(b)「契約は『箱だけ読む』と書くのに、drop は _items を読む」→ 契約・説明を事実に合わせた。_items が戦略から届かないことを試験 test_the_core_s_own_reference_lists_are_not_reached で確かめる。読み方はリードに聞く。(c)「変更の格子に出口の箱が入っていない」→ 箱は第 9 周の格子と第 10 周の知らせの値の格子が持つ。列に入れなかった物として試験の説明に書いた。(d)「数の変換が Exception でない BaseException を投げると、入口の誤りにならない」→ 割り込み(KeyboardInterrupt など)を模型の誤りに変えないのが lifecycle の規則。元のまま出て FAILED になり、以後は EngineFailedError になることを格子 3 で固定した。(e)「exception_text は、組み込みの型そのものでない引数を型の名前にしてしまう」→ 元の例外は __cause__ と failure にそのまま残る。(f)「型の名前の書き方が変わった」→ 知らない報告の型の文で builtins の型は 'builtins.str' から 'str' になった(試験は語 'unknown report type' で照合するので影響なし)。(g) 速さ → 同じ入力を直す前と後で 2 回ずつ実行した。配達の要約は同じ(台本の実行 cbc4e7073082、5 万約定 23b27a7a143c)。1 事象あたり、直す前 67.56・68.49 マイクロ秒、直した後 63.35・64.84 マイクロ秒(<S>/item0_r11_worker_digest_compare.out)
- (5) 場当たりの直しの確かめ: 試験だけを特別扱いする分岐・閾値や既定値のずらし・文言合わせ・機能を外すことはしていない。直しは読み方の規則 1 つ(外の物は class を通さず、type と BaseException 自身の記述子と基の型の方法で読む)を、断りの文・型の名前・差し込み口の名前の全部の読み手に当てたもの
- (6) 敵対者の試験を直す前に書いた。直す前の src(HEAD 667cd4d を git archive で取り出した物。-o pythonpath で指定)で実行 → 格子 1・3 と名前の試験は `166 failed, 117 passed`(<S>/item0_r11_worker_grid13_on_oldsrc.out、<S>/item0_r11_worker_newtests_on_oldsrc.out)。直した後は 291 件が全部通る。格子の入力は実装の場合分けから作っていない。入口は interfaces.SOCKETS と socket_methods から、数を返す口はプロトコルの戻りの注釈から、変更の方法は型とその変わらない相手の型の差(dir の差)から、機械で出した。表がその差を尽くすことも試験 test_the_mutator_tables_cover_every_method_the_types_add で確かめる。格子の大きさ: 格子 1 = 15 入口 × 14 種 = 210、格子 3 = 5 × 14 = 70、格子 2 = A 799・B 799・C 2005・D 1794 升目で、全部走らせた(LEAD_DESIGN §7.2 の 12)。変更で規則を破った升目は 0 件(直す前の src でも 0 件)。列に入れなかった物は試験のファイルの説明の「NOT in the grids」に書いた

## 外部の道具を入れたときの §4 の検査の結果

入れていない(外部の道具は導入も実行もしていない。ネットワークも使っていない)。

## リードに聞くこと

- LEAD_DESIGN §8.3「エンジンは _StrategySide の中の物を書くだけで、読むのは箱を 1 度写すときだけ」の読み方を確かめたい。事実: 核は事象を落とすとき、_StrategySide の中の HistoryLists が持つ「事象の写しへの参照の列」(_items・_overall_items)を切り出して、新しい履歴の列を作る(history.py 160-173 行 drop)。この 2 つの列は戦略から届かない(試験 test_the_core_s_own_reference_lists_are_not_reached)。核が読むのは参照の並びだけで、写しの中身は読まない。この周は「戦略が届く物のうち核が読むのは箱だけ」と契約・説明を直し、構造は変えていない。列を核の側へ移すと、核の状態が事象の写しに届いて到達性 0 が崩れる。落とすたびに写しを作り直すと、戦略が持つ事象と列の中の事象が同じ物でなくなる。この読みでよいか、決めてほしい
- 戦略の物の後始末(__del__・weakref の呼び戻し)は、解釈系が物を放すときに走る。核の手順の中でも走る(例: _drain の list.clear が、戦略が箱に書いた物の最後の参照を放すとき)。核はこれを止められない。届くのは戦略が届く物だけで、核はそこから判断しない。契約 scope に「対象外」と書いた。これで要件の外として扱ってよいか
- (独立の項目)起動文 (3) の候補 35 の権限の分類器の拒否は、場面係・監査役あての項目なので、作業者は扱っていない
- 批評家の第 9 周の試し item0_r9_critic_probe_port_class_swap.py・item0_r9_critic_probe_closure_reach.py・item0_r9_critic_recheck_r8_registry.py は、口を名前(eng._box など)で探すか、tuple に入らない。第 10 周からの版では口を見つけられずに止まる(TypeError / AttributeError)。第 11 周の批評家が直りを確かめるときは、歩いて探す形の試し(作業者の item0_r10_worker_probe_*_tuple.py と同じ形)が要る

## この周で変えた構造

(1) 核の外のコード(戦略・差し込み口・入力の流れ)が作った例外と class を核が持ち主の呼び出しの外で扱うとき、その class を通さずに事実だけから読むようにした。FAILED の断りの文は values.exception_text、型の名前は type 自身の記述子(values.class_parts / type_name)で読み、差し込み口の名前は構築のときに 1 度だけ読む。これで、戦略の例外の __str__ が on_event の外で走ることも、断りが EngineFailedError 以外の型になることもなくなった。(2) 「戦略が届く物のうち核が読むのは出口の箱だけ」を試験で固定した(LEAD_DESIGN §8.3)。gc の参照で歩いて届く全部の物(cell・既定値・array を含む)を、その型が持つ変更の方法の全部で変える格子を置き、外のコードの入口ごとに例外の作り 14 種を当てる格子も置いた。契約は core-13。
