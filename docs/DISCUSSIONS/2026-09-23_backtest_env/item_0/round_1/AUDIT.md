# 監査役の出力と作業者の問い(項目 0 第 1 周、Workflow の記録から逐語で書き出し)

## 監査役(場面集と最初の表)の出力

(この周には無い)

## 監査役(最初の表)の出力

### 監査役(表):0(agent afdb2a29d40fd07b7)

- [止める] docs/DATA/delegations/20260923_backtest_env_prompt.md §2/§3 は項目0の1周目に必要な盲検の露出を「審査員6体(2組×3体。1周目は試金石の3体を足す)」=9件と明記し、各件で「左右は審査員ごとに入れ替える」としている。しかし実際に配布された6表は round_1/make_tables.py の pairs 辞書(current_1/2, survey_1/2, mutant_1/2)どおり、比較の種類(当方の現状/調査結果側/試金石=mutant)ごとに『A→B』『B→A』の2通りしか作られていない(docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_1/item0_r1_materials_tables_mapping.log で確認)。3体の審査員に2通りの表しか無いという設計は、3人目にどちらかの表を再利用する前提を明示していない。この『2通りで3体をまかなう』割り当ては委任文のどこにも書かれておらず、資料係の記録にも説明が無い。9件必要なところ6件(各種2件ずつ)しか用意されていないことは、審査員への割り当てが決まっているのか、それとも不足なのか、をどう確認したか(P3・P5)。
- [聞く] make_tables.py が出力する table_id→ファイル名の対応(current_1=表_ebp3vp.md 等。A/B のどちらが新実装かも table_id で決まる)は、資料係の記録に『$B/item0_r1_materials_tables_mapping.log にだけ残した』とあるとおり、リポジトリ外の一時スクラッチパッド(/tmp/claude-0/.../17c10364.../scratchpad/bt/item_0/)にしか存在しない。このディレクトリが消えると、6枚のうちどれがどの比較(当方の現状/調査結果側/試金石)かを二度と機械的に確認できなくなる。盲検対象(A/Bの正体)を明かさない形の対応表(例えば table_id とファイル名だけ、比較対象名は含めない)を docs/DISCUSSIONS 配下に残す判断はしたか、それとも一時ファイルへの依存のままでよいか(P8)。
- [直す] docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_1/ には、今回の6表(表_ebp3vp/wlkjip/k5k5vm/9cvgdi/urwv3s/64cb9h.md)とは別に、コミット baf30f1 で追加された古い6表(表_3kkbjf/ip7vpv/jtlqu3/nl7plt/s1fkj3/vriymj.md、'v1-event_driven-cap' 等の旧場面名・28場面)が同じディレクトリに残っている。委任文は『項目0のやり直し…規則に合わないものは流用しない』としており、この6枚は場面集の規則(32場面・P0-1〜P0-7形式)に合っていない旧版である。資料係の記録(commands/adapters_changed)はこの6枚の存在に一切触れていない。ディレクトリを `表_*.md` で機械的に数えると12枚になり、今回の6枚と旧6枚を区別する手段が場面係・審査員側に無いように見えるが、削除・隔離するかどうかは確認したか(P5・CLAUDE.md『項目0のやり直し』)。
- [聞く] 表_k5k5vm.md と表_9cvgdi.md(survey_1 / survey_2、A=新実装・B=調査結果側の順を入れ替えた対)は MD5 が完全一致するバイト同一のファイルである。これは新実装と調査結果側の『最も良い結果』が32場面全てで完全に同じ(正しさ・再現とも)ためで、make_tables.py のバグではない。ただしこの場合、survey 組の3体の審査員には(左右をどう入れ替えても)常に見分けのつかない同一内容の表しか渡せない。委任文の『圧倒の判定=両方の組で3体中2体以上が新実装を選ぶ』という判定は、区別できない材料からの選択を前提にしてよいか、この組についてはこの縮退(材料の無差別性)を報告に明記する判断はしたか(P9)。
- [直す] 資料係の記録(commands のコマンド10)は『finmarketpy を足しても場面ごとの最も良い結果は1件も変わらない、食い違い0件』という結論を、make_tables.py の load/best を使った即興の Python 実行として説明するのみで、他の全ステップ(コマンド1〜9、12)と違い、出力を保存した実測ログのファイル名が示されていない。この確認だけ再現可能な形跡(スクリプト・保存出力)が無いのはなぜか、残す判断はしたか(CLAUDE.md §0.2 O-3 系: 機構・データの挙動主張には実行コマンドと出力を示す)。
- [聞く] 表_k5k5vm.md / 表_9cvgdi.md の『注記』は道具名を伏せる一方、導入を試みて止まった正確な開始・停止時刻(2026-09-23T17:42:44Z/17:43:20Z)を書いている。この時刻は同じリポジトリ内の runs/not_run_finmarketpy_reinstall.log(道具名 finmarketpy を明記)の時刻と完全一致し、同じ round_1 ディレクトリを見られる者なら突き合わせて対象を特定できる。審査員は場面集と比較の表だけを読む設計のため実害は無いと思われるが、注記に一次資料級の具体的時刻を残すことは、道具名を伏せる目的(場面集の規則)との整合をどう判断したか確認したか(P1 に近い『範囲と方法の記述』の要求)。

## 監査役(作業者の報告)の出力

(この周には無い)

## 作業者の「リードに聞くこと」

### 作る:0#1(agent a85da652e00ac1055)

- 同時刻に入力の心拍(時計)と戦略のタイマーが並ぶとき、入力の心拍を先にした(ORIGIN_SOURCE=0 < ORIGIN_ENGINE=1)。REQUIREMENTS.md の P0-5 で調査結果の側に挙がっている候補 44 の契約「データ → 派生 → 信号 → 注文 → 約定」に合わせ、入力から来たものを核が作ったものより先に置く、と読んだ。この向きは委任文の逐語には無い。逆にするなら定数 2 つを入れ替えるだけで、規則の形(入力の中身だけで決まる)は変わらない。
- event.seq の意味を「待ち行列の番号」から「戦略が受け取った回数」に変えた。src/bot/bt/ の外で bot.bt を読む所は無い【事実: grep -rn "bot\.bt\b\|bot/bt\|from bot.bt\|import bot.bt" --include=*.py src scripts tests の当たりは src/bot/bt/ と tests/bt/ だけ】。CORE_VERSION は core-3 から core-4 に上げた。
- 資料係の新実装の adapter(tests/bt/battery/item_0/adapters/new_impl.py)はまだ無い。adapters/ にあるのは __init__.py・common.py・current_impl.py・protocol.py だけ。mutant.py --check も new_impl.py が無いと回らない。場面を公開の口だけで通す書き方は tests/bt/item_0/test_bt0_scene_set.py にある(口座・約定の模型・遅延・費用を公開の口の形で書いている)。adapter は資料係の持ち物なので、作業者は作っていない。
- 批評家の試験 test_liquidation_has_no_account_hook.py::...test_engine_notifies_the_account_of_a_liquidation_event は、試験自身の誤りで落ちる(規則 8 により変えていない)。誤りは 2 つある。(a) 69 行の side="long" は清算の注文の向き(buy/sell)ではないので、EventValidationError になる。(b) 43〜53 行の _RecordingAccount に apply_liquidation・on_market_event・check_order が無く、構築時に TypeError で拒まれる。2 つを直した写しでは apply_liquidation が 1 回呼ばれる【事実: /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/item0_r1_worker_liq_check.py と .log】。リードの処置 11 のとおり、次の周の批評家に確かめてもらう。
- REPORT.md を置く場所(round_1/)には、この周の前(14:32)に作られた 表_*.md が 6 枚ある。作業者が作ったものではないので、触っていない。
