# バックテスト環境の仕上げ(L-464)— 記録

委任文: `docs/DATA/delegations/20260926_backtest_env_finish.md`(監査 1 回のあとの版の指紋 **20260926_backtest_env_finish.md@ec283fb43be1**。監査に出した版は 45df2e60e788)。親: `docs/DATA/delegations/20260925_backtest_env_prompt.md@388d55cdeb32`。
起動の時刻 = L-464 の時刻 11:57 UTC。上限 14:57 UTC。

## 監査役の出力(1 回目 = 最後、逐語)と処置

1. [止める] docs/DATA/delegations/20260926_backtest_env_finish.md:16 — 「**上限 = 起動から 3 時間、2026-09-26 14:57 UTC まで**」という数値の出所が本文に示されていない。docs/OWNER_LOG.md L-464 の行は起動根拠の L-464 発言時刻を「**2026-09-26 21:5x JST(12:5x UTC)**」と記録しており(L-462「21:3x JST(12:3x UTC)」→L-463「21:4x JST(12:4x UTC)」→L-464「21:5x JST(12:5x UTC)」の並びから、起動はこれ以降=12:5x UTC 以降のはず)、単純に +3h すれば 15:5x UTC 前後になるはずのところ、本文は 14:57 UTC としている。さらに同じ L-464 行のリード対応欄は「**上限3時間(起動から14:57 UTC = 翌23:57 JST)**」と書いており、21:5x JST(同日)から「翌23:57 JST」までは 3 時間ではなく約 26 時間相当になる(日をまたいだ「翌」の解釈が正しければ)。I-013 が要求する「終わる条件の上限」そのものの算出根拠・計算過程が本文にも OWNER_LOG にも示されていない。この数字はどう導出されたか、3 時間という L-464 の逐語と整合するか。(P2、I-013)
   - 処置: OWNER_LOG の L-464 の時刻が誤りだった(リードの `date -u` の実測は 11:56:59 UTC = 20:57 JST。L-462・L-463 の「12:3x・12:4x」も推定で書いた時刻で、実測ではない)。L-464 を 20:57 JST(11:57 UTC)に直し、委任文に導出(11:57 + 3 時間 = 14:57 UTC = 同日 23:57 JST)を書いた。「翌」を消した。
2. [止める] …:18-25 — 終わる条件 1 は「第 2 周の批評家の [止める] のうち次の 6 件を直し」として i4-r2-02・03・05・06・08・01 の 6 件だけを列挙するが、背景として渡された docs/AUDITOR/VERDICTS/2026-09-25_backtest_env_run12.md の「15 回目の出力」(1485 行)には批評家の [止める] が 9 件(i4-r2-01〜09)記録されている。残る i4-r2-04(検討表の誤り、target=場面集)・i4-r2-07(PineForge 未実行、target=場面集)・i4-r2-09(委任文と台本の食い違い試験、target=場面集)の 3 件には「直し方の決め」が無く、本文のどこにも触れられていない。CLAUDE.md §0.2 A-10「族を減らしたところで見つかった欠陥を放置してよい理由にはならない」「族・スコープを説明なく縮める」に照らして、この 3 件を対象外にする理由が書かれているか。書かれていないなら、これは説明のない族の縮小ではないか。(P13、A-10)
   - 処置: 9 件全部を閉じる形に直した(04 = 場面係が照合を直す / 07 = 場面係が構築し直しを試み、止めるなら実測つき / 09 = この文書に除外の文を置き、場面係が試験の正解を文書に合わせる)。
3. [止める] …:32 — 「**検討表の言い回し・調査の相手の数(PineForgeを含む)・委任文と台本の文の一致・報告の書き方は [直す] 以下にし、周を止めない。**」という一文は、直前の周(round 2)で批評家が [止める] にした i4-r2-07 と i4-r2-09 を名指しで非ブロッキングに格下げしている。これは L-464 の逐語「**精度を落とさず**」、および委任文自身の §0 対応表(6 行目)が「終わる条件を緩めない(検査を薄くしない)」を「精度を落とさず」の該当語として掲げていることと、直接に矛盾しないか。この格下げは検査を薄くすることそのものに見えるが、その理由が本文に書かれているか。(A-10、L-464)
   - 処置: 射程を「正しさ・安全・統合・場面集の規則 1〜9 の違反(比べの結果を変えるもの)」に広げ、9 件全部を [止める] の中に置いた。[直す] 以下は「報告の書き方・注記の言い回し(結果を変えないもの)」だけ。
4. [直す] …:18 と :32 — 終わる条件 1 は「批評家の試験 tests/bt/critic/item_4/ と場面集 tests/bt/battery/item_4/ が全部通る」と書く一方、i4-r2-04 の失敗試験と i4-r2-09 の失敗試験はどちらもこの 2 ディレクトリの中にある。「全部通る」を字義どおり読めば、この 2 件の直しは条件 1 に含まれてしまうが、直し方の決めが一切示されていない。「次の 6 件」という限定と「全部通る」という全称の要求が、この 2 件について食い違っている。これはどちらが優先するか。(P9)
   - 処置: 2 の処置で解消(9 件全部 + 全部通る、で一致)。
5. [直す] 全文(grep 0 件) — docs/AUDITOR/VERDICTS/2026-09-25_backtest_env_run12.md 1373-1374 行(i4-r2-09)は「直し方はリードが委任文に除外の文を足し、場面係が _inside_by_text をその文に合わせること」と明記し、run 15 終了時のリードの読み(1498 行)も「次の起動が無い限り委任文は変えない」と書いている。この仕上げの委任文はまさに「次の起動」だが、その除外の文(docs/AUDITOR/TRACE/ を場面集の差分検査から外す旨)がどこにも見当たらない。この直しは意図的に見送られたのか、書き漏らしたのか。(P8、O-3 系)
   - 処置: 書き漏らし。§3 に除外の文を足した。
6. [聞く] …:40, 42 — §3 の役の表で、作業者の持ち物には `tests/bt/item_4/`(全体)が挙げられ、参照実装の役の持ち物には `tests/bt/item_4/reference/`(その部分集合のパス)が別に挙げられている。作業者の「読んでよい物 = 全部」「してはいけないこと」欄には `tests/bt/item_4/reference/` に触れない旨の明記が無い。参照実装の役の独立性を守る配線として、作業者がこのサブパスに書き込まない保証はどこにあるか。(P9、独立の参照の設計)
   - 答え: 無かった。作業者の持ち物から `tests/bt/item_4/reference/` と `bar_sim.py`・`SPEC.md` を除き、してはいけないことに書いた。
7. [聞く] …:40 — 作業者の「してはいけないこと」欄に「核の契約を変えるなら契約の版に書く」とあるが、作業者の持ち物欄には `src/bot/bt/core/` に該当するパスが無い。「契約の版」はどのパスに書くことになっているか。
   - 答え: `src/bot/bt/core/contract.py` の CORE_VERSION と契約の文。持ち物に足した(欠陥を直すときだけ)。
8. [聞く] …:53 — 批評家についての戻し回数の上限を定めるが、終わる条件 4「監査役(通過)の [止める] 0」について、監査役が [止める] を出した場合の直し・再監査の回数上限は §4 のどこにも書かれていない。(I-013)
   - 答え: 直しと再監査を 1 回だけ、と足した。
9. [聞く] …:25 と §3 — 条件 2 は参照実装の役が bar_sim.py を書き直し、作業者の格子の試験を全ての規則に広げて全升で一致することを要求し、§3 は 3 役を同時に起こすと定める。参照実装の役の bar_sim.py が完成する前に作業者が全升比較の試験を実行・報告してしまう順序上の担保が本文に書かれているか。
   - 答え: 無かった。作業者の格子の広げは参照実装の役が返ったあとの第 2 段としてリードが起こす、と書いた。
10. [直す] …:23(i4-r2-08 の直し方の決め) — 「独立の参照の役の決めと同じ側にする(D2・D3 を消す)」という決定は、条件 2 の一般原則より前に、D2・D3 の「正しい側」を作業者・場面係が先に確定させる形になっている。参照実装の役が DEFINITIONS.md だけから独立に bar_sim.py を書く前に、その規則文(R-M・R-E)の具体的な値をこの直しの段で場面係が先に書き込むことは、条件 2 が確認しようとする「独立に導いた一致」を後付けで保証したことにならないか。
   - 処置: そのとおりなので開示に変えた(3 役を同時に起こすためにリードが値を決める。この 2 値は第 1 周の参照の役の決めと同じで、この 2 点の一致は「同じ文を 2 者が実装した一致」に留まる、と委任文に書いた)。

## 役の返り値・批評家・監査役(通過)の出力(逐語)

(起動のあとに写す)

### 場面係(第 1 段 r3-1)の返り値(逐語、12:33 UTC)

リードに報告を返しました。PineForge を除く場面集の側の直しは済み、場面集と批評家の試験は全部通っています(`245 passed`)。PineForge(候補 70)は比べられていません。

**PineForge で手順を破りました。** 取り直した版 `0d76a099` は、前に検査した `5e62602c` ではありません。私はこの新しい版に導入前の検査をせず、CMake の構築まで走らせました。次の操作をこの環境の許可の判定が止めたので、driver の翻訳と実行はしておらず、道具は 1 度も呼んでいません。容量では止めていません(空き 2,046 MB → 1,935 MB)。検討表・RUNNABILITY.tsv・survey_results の PineForge の行に「比べていない(理由)」を書きました。検査していない版の clone と構築物は `<venvs>/item_2/src/c70` に残したままです。

**直したこと:**
- **i4-r2-02**: R-O1・R-H3 を、決めのとおり「始値の時間切れが範囲の逆指値より先」に直しました。2 場面の正解は 98 から 101 になりました。
- **i4-r2-08**: 規則 R-E4(マスクが False の合図は指値を置かない)と R-M6(同じ向きの合図は指値を置き直さない)、旧エンジンの計算 L-6・L-7、場面 5 つを足しました。旧エンジンの側の答えは、旧エンジンを実際に呼んで確かめました。
- **i4-r2-04**: 照合を正規表現にし、括弧が挟まっても当たるようにしました。zvt・lumibot の I4-17 の行は「再現できない」になり、批評家の試験が通ります。
- **i4-r2-09**: `_inside_by_text` を、仕上げの委任文 §3 の除外の文に合わせました。
- 足した・直した 8 場面を全 42 対象に通し、survey_results を直しました。`check_bt_considered.py` は誤り 0 件です。

**手順の順も守れていません。** 根本原因の文書(ROOTCAUSE_r3-1.md)と格子の試験は、直しを始めたあとに書きました。直す前の試験の記録だけは、場面集を 1 行も変える前に取っています(`13 failed`)。着手時の基準は道具では取っていません。着手直後に見た作業木が空(HEAD と同じ)だったことを、あとから同じ形に書き写しました。このことは ROOTCAUSE の冒頭に書いてあります。

**リードに聞いた 4 点:**
1. 委任文に語の無い作りの変更 2 つを認めるか。時間切れの足の逆指値を別の出来事(`stop@time`)に分けるのをやめたことと、2 出力の場面を 1 つ足したことです。
2. 待っている建ての指値に、マスクが False の反対向きの合図が来たときの規則が無い。決めてもらえれば文と場面を足します。
3. PineForge を `5e62602c` で取り直して構築・実行してよいか。検査していない版を消すかどうか。
4. 記録の置き場所が起こし文と仕上げの委任文で違う。今は両方に写しています。

根本原因と提出前の吟味の全文は `tests/bt/battery/item_4/ROOTCAUSE_r3-1.md`、記録は `docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r3-1/` にあります。

**リードの答え(12:36 UTC)**: (1) stop@time を範囲の逆指値 1 つにまとめたこと・2 出力の場面 two-models を足したこと = 認める(R-H3 の決めから導いた範囲)。(2) 待っている建ての指値にマスク False の反対向きの合図が来たとき = **古い指値を残す**(R-E4 が先: マスク False の合図は何もしない。R-M3 の置き換えは有効な合図のときだけ)。文と場面を足す。参照実装の役にも同じ値を渡す。(3) PineForge: 検査していない版(0d76a099)は走らせない。前に検査した版 5e62602c を取り直し、前の検査の記録を当てて構築・実行する。**13:20 UTC までに走らなければ「比べていない(理由)」のまま進める。** 検査していない版の clone と構築物は消す。§4 の手順から外れて構築したことは記録に残す(場面係の自己申告)。(4) 置き場所は両方でよい。


### 参照実装の役(第 1 段)の返り値(逐語、12:38 UTC)

参照実装の役(仕上げの第 1 段)の報告です。12:38 UTC 時点で、期限 13:37 UTC の前に終えました。

**結論**: `src/bot/bt/reference/bar_sim.py` を、場面集の規則の文と、仕上げの委任文 §1 の i4-r2-02・i4-r2-08 の決め(作業中に届いたマスク False の補いを含む)だけから、空のファイルで書き直しました。対象の規則は R-T・R-C・R-A・R-M・R-P・R-X・R-W・R-H・R-E・R-S・R-O の全部です。試験は 1056 件すべて通り、mutant は 40 件すべて落ちました。場面集の I4-1 の 2 場面(i4-1-ref-taker・i4-1-ref-maker)も、場面集の正解と一致しています。

注意が 1 つあります。**私の作業途中のファイルが、リードのコミット c79b2e6 に入っています**(`bar_sim.py`・試験・mutant・materials など)。現時点で未コミットの私の変更は `SPEC.md` だけです。

## (a) 変えたファイル
- `src/bot/bt/reference/bar_sim.py`: 新しく書きました。入口は `run_bars(bars, signals, options)` の 1 つで、値は全部正確な分数です。float の入力は、書かれた 10 進の値として読みます。
- `src/bot/bt/reference/SPEC.md`: §1 の入口の行、§3(規則ごとの表)、§4(文が決めていない点)、§5 の冒頭の注記、§6〜§10 を書き直しました。§10 にこの周の対応表と、「この版は場面集の規則の文だけから書いた。核・新エンジン・bar_rules は開いていない」を書きました。
- `src/bot/bt/reference/__init__.py`: 説明の文の 1 行を直しました。
- 旧の足の模型(第 1 周に書かれた、選べる型を多く持つもの)の扱い:
  - 中身は読まずに `git mv` で `tests/bt/item_4/reference/ext_bar_modes.py` に移し、先頭に「規則の参照ではない」という注記を足しました。
  - 理由: 外部の道具 backtesting.py との記録の突き合わせの試験が、この模型を使っているためです(既存の試験を消さない規則)。
  - 旧の場面と性質の試験は `test_i4ref_extmodes_scenes.py`・`test_i4ref_extmodes_properties.py` に名前を変え、import の行だけを付け替えました。`ext_backtesting_compare.py` も import の 1 行だけ変えました。
- 新しい試験:
  - `tests/bt/item_4/reference/i4ref_bar_kit.py`(共通の道具と、場面集の足の組)
  - `test_i4ref_rules_scenes.py`(52 件。規則ごとの正解つきの場面で、注釈に手計算の式)
  - `test_i4ref_rules_properties.py`(289 件。96 升 × 種 3 の格子と、規則の文の式だけで見る性質 Q1〜Q11)
- `tests/bt/item_4/reference/ref_mutants.py`: この版に向けた mutant を 26 件足しました。一時フォルダは各回の私有の場所にしました。
- `docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/reference/before_rewrite.md`: 直す前に落ちる記録です(旧の版では、新しい試験が集めの段で落ちる)。
- `event_sim.py` は触っていません。

## (b) 試験のコマンドと末尾の行
- `PYTHONPATH=src python -m pytest -p no:cacheprovider -o tmp_path_retention_policy=none --basetemp=/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/finish_ref_basetemp tests/bt/item_4/reference/`
  - 末尾の行: `1056 passed in 7.46s`
- `python3 tests/bt/item_4/reference/ref_mutants.py`
  - 末尾の行: `killed 40/40`
  - 内訳: 事象の参照 8 件、移した旧の模型 6 件、この版 26 件。
  - 最初の回で生き残ったのは 2 件でした。
    - 保有を始めた足(建てた足)を窓に入れる mutant: 場面 1 つと性質 Q11(出口を飛ばさない)を足して潰しました。
    - R-T2 の分岐を消す mutant: 最後の足の合図は処理の繰り返しが終わるので約定せず、分岐を消しても結果が変わりません。この分岐をコードから外し、mutant も外しました。

## (c) 満たせなかった規則と理由
- 規則の文 R-T〜R-O の中で満たせなかったものはありません。
- 持っていないもの: 指標 M-1〜M-12、分け方 D-1・D-2、互換の計算 L-1〜L-5。起動文の規則の一覧に無いため作っていません。
- 規則の文の参照(この版)は、外部の道具と突き合わせていません。外部の道具との記録は、移した旧の模型との比較のままです。
- 入口の形を変えたので、作業者の `tests/bt/item_4/test_i4_engine_vs_independent_bar_sim.py` は第 2 段で §7 の口に合わせる必要があり、それまでは落ちるはずです。このファイルは中身を開いておらず、実行もしていません。`grep -rl` でファイル名だけを確かめました。

## (d) リードに聞くこと
1. 文が決めていない 2 点の値を決めてください。第 2 段の突き合わせでも、この値を渡します。今は必須の引数 `options["undecided"]` にしてあります。
   - U1 `wick_short_history`(値: `refuse` / `use_available` / `no_stop`): 構造的な逆指値の窓で、約定の足の前に足が N 本無いとき。
   - U2 `same_side_exit_signal`(値: `keep` / `replace`): **決済の**指値が待っている間に、同じ向きの合図が来たとき。i4-r2-08 が決めたのは建ての指値だけです。
2. 字義どおりに読んだ点(SPEC §4)を正とするか、規則の文に足すか:
   - U3: 保有を始めた足自身の終値も、構造的な逆指値の判定に入れる。
   - U4: 向きや空売り不可で止められた反対向きの合図のときは、待っている建ての指値を残す(マスク False はリードの決めのとおり)。
   - U5: 高値・安値が始値・終値を囲まない足は拒む。
   - U6: 「使わない」は `None` で表し、0 以下の率は拒む。
   - U7: 費用が負の値でも受ける。
   - U8: 寿命 0 は拒む。
3. `ext_bar_modes.py`(旧の模型)を残すか。それとも、外部の道具との突き合わせをこの版で取り直すか。取り直すには、隔離した venv でもう一度動かす必要があります。
4. 指標と分け方も参照に持たせるか。
5. 場面集が「使わない」を 0 と null のどちらで表すかが DEFINITIONS.md に書かれていません。第 2 段で作業者が写し間違えないよう、場面係に書いてもらうか。

## (e) 提出前の吟味の結果(SPEC.md §9 に表で記録)
- **独立**: 核・新エンジン・`pipeline.py`・`bar_rules.py`・作業者の試験・battery の Python・批評家の試験は開いていません。旧の `bar_sim.py` の中身も読んでいません。
  - 名前は全部この役で付けました。
  - `options` の鍵の名は、DEFINITIONS.md の場面の config の名をそのまま使いました。
  - 読んでよい 4 つの外で読んだのは、この役の持ち物(SPEC.md・`num.py`・`ref_mutants.py`・ext の比べの周り)だけです。
- **i4-r2-02**: 時間切れの足では、始値の時間切れが先です。場面は taker と maker の 2 つ、mutant もあります。
- **i4-r2-08 と、リードから届いたその補い**: マスクが False の合図は何もしません(指値を置かない・取り逃しに数えない・反対向きでも古い指値を残す)。同じ向きの合図では建ての指値を置き直しません。場面 2 つと mutant 2 つで確かめています。
- **正解の出所**: 期待値は全部、実行の前に手で計算して書きました。場面集の I4-1 の 2 場面は、場面集の正解と相対 1e-9 の幅で一致しました。
- **mutant**: 生き残りは 0 件です。
- 既存の試験は消していません。§4 の禁止(相場についての主張・モデル名・依存の追加・実データ)はどれにも当たりません。git commit / push はしていません。

## (f) 入口の形(SPEC.md §7 と同じ)
`run_bars(bars, signals, options) -> BarRun`。3 つとも位置引数で、既定値はありません。欠けや誤りは `RefusedConfig` で拒みます。

- `bars`: `(始値, 高値, 安値, 終値)` の組か、`{"open", "high", "low", "close"}` の dict の列。値は int・str・Fraction・float です。
- `signals`: `{足の番号: "BUY" | "SELL" | "CLOSE"}`、または足と同じ長さの列(`None` か `"HOLD"` は何もしない)。
- `options`: 次の鍵が全部要ります(欠けても余っても拒む)。
  - `capital`・`order_amount`・`bar_seconds`
  - `costs`(`taker_fee_pct`・`maker_fee_pct`・`slippage_pct`・`spread_pct`。単位は %)
  - `execution`(`taker` / `maker`)・`maker_timeout_bars`(`None` か 1 以上)・`allow_short`・`swap_daily_pct`
  - `stop_loss_pct`・`take_profit_pct`・`max_hold_bars`(使わないときは `None`)
  - `exit_execution`(`signal` / `maker_tp`)・`maker_tp_pct`
  - `entry_mask`(`None` か bool の列)・`entry_sides`(`both` / `long` / `short`)
  - `stop_mode`(`fixed` / `wick_invalidation`)・`stop_window_bars`
  - `undecided`(`wick_short_history`・`same_side_exit_signal`)
- 返り値 `BarRun`:
  - `fills`: 約定の列。各約定は `bar`・`side`(OPEN_LONG / OPEN_SHORT / CLOSE_LONG / CLOSE_SHORT)・`price`・`size`・`fee`・`liquidity`・`reason`。
  - `pnls`: 往復ごとの損益(R-A3)。
  - `equity`: 各足の終値の時点の資産(R-A4)。
  - `missed_fills`: 取り逃しの数(int、R-M5)。
  - ほかに `trades`・`open_trade` を持ちます。
  - `to_dict()` は分数を文字列にします。`to_floats()` は float の新エンジンと、場面集の判定の決まり(相対 1e-9)で比べるためのものです。
- 違いが出たら、参照ではなく新エンジンの欠陥として扱います。

**リードの答え(12:42 UTC)**: U1 `wick_short_history` = **use_available**(窓の足が N 本無ければ有る分で判定。規則の文に足す。refuse だとデータの頭 N 本に建てる全実行が拒まれ、no_stop は黙って逆指値を無くす)。U2 `same_side_exit_signal` = **keep**(建ての R-M6 と同じ側)。U3〜U8 = 字義どおりの読みを正とし、場面係が規則の文に足す(U3 建てた足の終値も構造的な逆指値の判定に入れる / U4 向き・空売り不可で止められた反対向きの合図では待っている建ての指値を残す / U5 高値・安値が始値・終値を囲まない足は拒む / U6 「使わない」は null、0 以下の率は拒む / U7 負の費用も受ける / U8 寿命 0 は拒む)。新エンジンが違えば新エンジンを直す(条件 2)。Q3 = ext_bar_modes.py は残す(外部の道具との取り直しはしない)。Q4 = 指標と分け方は参照に持たせない(golden で見る)。Q5 = 場面係が DEFINITIONS.md に「使わない = null」と書く。


### 場面係(第 1 段の追加 + 第 2 段)の返り値(逐語、12:48 UTC)

リードの答え (1)〜(4) と第 2 段の指示を片付け、報告を返しました。場面集と批評家の試験は全部通っています(`248 passed`)。PineForge は、検査した版を取り直したものの比べられていません。新エンジンは 4 場面で正解と食い違い、作業者が直す分として報告しました。

**第 1 段の追加:**
- 待っている建ての指値に、マスクが False の反対向きの合図が来たときは、リードの決めどおり古い指値を残すことにしました。規則の文と場面 2 つを足しました。旧エンジンがどう計算するかは、実際に呼んで確かめました。
- 検査していない版 0d76a099 の clone と構築物は消しました。前に検査した版 5e62602c は取り直しましたが、構築・実行へ進む操作をこの環境の許可の判定がまた止めました。PineForge は道具を 1 度も呼んでいません。検討表・RUNNABILITY・survey_results の全 86 行に「比べていない(理由)」を書きました。
- 検査をせずに 0d76a099 を構築して手順から外れたことは、ROOTCAUSE_r3-1.md に自己申告として残しました。

**第 2 段:**
- 参照実装が字義どおりに読んだ U1〜U8 を、規則の文に足しました。「使わない」は null で表すこと、0 以下の率や寿命 0 を拒むこと、負の手数料を受けること、などです。これを固める場面を 11 足しました。
- 参照を `bar_sim.run_bars` に切り替えました。i4-1-ref-taker・i4-1-ref-maker・i4-3-ref-signal-first の 3 場面とも、新エンジンで「正解と一致」です。
- 私が最初に書いた場面の 1 本に、高値が終値より低い不正な足がありました。新エンジンがその足を拒んだことで気づき、直しました。あわせて、場面集の全部の足を検める試験を足しました。

**新エンジンが正解と食い違う 4 場面**(新エンジンの側で直すもの):
- `i4-14-sides-opposite-keeps-limit` と `i4-14-sides-opposite-two-models`: 向きの制限で止められた SELL で、待っている買いの指値を置き換えてしまう。
- `i4-10-zero-rate-refused`: 率 0 を拒まない。
- `i4-16-zero-timeout-refused`: 寿命 0 を拒まない。

**リードに聞いたこと:**
- 参照は指標の式を持たないので、I4-1 の 2 場面では参照の側の判定から指標を外しました。指示に無い変更なので、これでよいかを聞いています。
- PineForge を進めるには、オーナーが許可の規則を足す必要があります。「比べていない」のまま進めるかを聞いています。
- 拒むべき入力の 3 場面は、旧エンジンも拒みません。場面は仕様の答えだけにし、旧と新の 2 出力は置いていないことを伝えました。

途中でリードがコミットしたため、着手時の基準と HEAD が食い違っています。差分の節の行ごとの帰属は「判定できない」になります。

主なファイル:
- /home/user/trade/tests/bt/battery/item_4/ROOTCAUSE_r3-1.md
- /home/user/trade/tests/bt/battery/item_4/i4_scenes.py
- /home/user/trade/tests/bt/battery/item_4/gen_definitions.py
- /home/user/trade/tests/bt/battery/item_4/adapters/new_impl.py

**リードの答え(12:52 UTC)**: (1) I4-1 の 2 場面で参照の側の判定から指標を外すこと(W_E_REF)= 認める(参照は規則の文の実装で、指標は golden と場面集の本体の側で見る)。(2) PineForge = 「比べていない(この環境の許可の判定が構築・実行を止めた。道具は呼んでいない)」のまま進める。取り直した 5e62602c の clone は残す。オーナーに許可の規則を足してもらうかは、完了の報告の「判断が要る項目」ではなく「測っていない範囲」に載せる(道具 1 つの有無は測定器の正しさを変えない)。(3) 拒むべき入力の 3 場面は仕様の答えだけでよい(互換の口の「旧と同じ数を出す層」は条件 3 の作業者)。
新実装の不一致 4 場面(R-E5 の 2・R-V2・R-V4)は作業者の第 2 段で直す。


### 作業者(第 1 段)の返り値(逐語、13:33 UTC)

## 項目 4 仕上げ 第 1 段(作業者)の返り値

委任文の完了の形(仕上げの委任文 §1 条件 1、逐語): 「**第 2 周の批評家の [止める] 9 件全部を閉じ(下の 6 件は直し、残る 3 件は次のとおり)、批評家の試験 `tests/bt/critic/item_4/` と場面集 `tests/bt/battery/item_4/` が全部通る**」。この段で受け持ったのは実装の側の i4-r2-02・03・05・06 と i4-r2-08 の spec の側。

実装の側の 5 件は、狙った試験が全部通るところまで来た。ただし場面集の統合の場面 5 つは落ちたままで、直せるのは場面係だけ(下の (c)-1)。核(`src/bot/bt/core/`)は変えていないので、CORE_VERSION は core-19 のまま。

### 直した中身(事実)
- **i4-r2-02**(`barmodel.py`・`bar_rules.py`):
  - spec では時間切れを始値の段で取る(R-O1 の ②)。その足では範囲の逆指値・利確は起きず、待っている合図や指値は捨てる。
  - `BarRules` に欄 `time_exit_at_open` を足した。legacy は旧の順のまま。
- **i4-r2-08**(spec の側):
  - `maker_mask_at_signal`: 止められた建ての合図は指値を置かない・取り逃しに数えない(R-E4)。マスクだけでなく、場面係が並行して足した R-E5 に合わせて向きの制限(R-E1)も同じにした。
  - `maker_same_side_keeps`: 同じ向きの合図は古い指値を残す(R-M6・R-M7)。取り消しの理由は "kept_older"。
  - `refuse_non_positive`: 場面係の R-V2・R-V4 に合わせ、0 以下の率・本数・寿命を断る。
  - どれも spec だけで、legacy は旧のまま。`bar_rules.py` も同じに直した。
- **i4-r2-05**(`pipeline.py`):
  - `prereg_sha256` を渡すと PipelineError で断る。
  - 事前登録は root の下のファイルだけを受け、sha256 をこちらで計算して記録する。空のファイルも断る。
- **i4-r2-03**(`pipeline.py`):
  - 出所は行で決める。データ層の read で読んだ行(時刻と全部の値)を、市場データのフォルダのファイルを同じ宣言でデータ層に通して読んだ行と照らす。一致した行が最も多いファイルを証拠として記録する(market_path、一致した行数 / 読んだ行数)。
  - 候補のファイルは、1 行目の列名と、最初と最後のデータ行の時刻で絞る。封印のあるファイルはデータ層の read でだけ照らす。
  - 合成は種つきの生成器 `{"name","generator":{"name":"random_walk","seed","params"}}` からだけ作れる。生成器の名前・版・種を実行記録の `generators` に残す。
  - ファイルのデータセットを "synthetic" と宣言すると断る。`market_evidence`(置き場所とバイトの一致で見ていた旧の判定)は消した。
- **i4-r2-06**(`pipeline.py`):
  - 自前の FirstObservedFill・_Latency・_Fee・NullAccount を消し、銘柄ごとに SimVenue・LatencyModel・ScheduleCostModel・MarginAccount を差した。
  - 宣言の形:
    - `fill` = 楽観と悲観の 2 つ(tier 6 の影響関数も宣言できる)
    - `latency` = 4 つの遅延をそれぞれ分布で(種つき)
    - `costs` = 率・出所・スプレッド、資金調達の規則は任意
    - `account` = 通貨・元本・レバレッジ・評価の規則・清算の規則・証拠金の見方
    - 銘柄には `product` と `rules`
  - 実行は楽観と悲観の両側を回す。実行記録の `components` に、差した模型の型・引いた遅延(回数と和)・両側の口座の最終状態が出る。`metrics["range"]` と、約定・往復・注文の各行の `range` の欄で両側が分かる。

### (a) 変えたファイル
**コード**
- `src/bot/bt/compat/barmodel.py`
- `src/bot/bt/reference/bar_rules.py`
- `src/bot/bt/pipeline.py`

**試験(新しく作ったもの)**
- `tests/bt/item_4/i4w_decl.py`
- `tests/bt/item_4/test_i4_r3_time_exit_at_open_grid.py`(96 升)
- `tests/bt/item_4/test_i4_r3_maker_two_values_grid.py`(24 升)
- `tests/bt/item_4/test_i4_r3_origin_by_rows_grid.py`(64 升)
- `tests/bt/item_4/test_i4_r3_prereg_file_grid.py`(12 升)

**試験(書き換えたもの)**
- `tests/bt/item_4/test_i4_pipeline.py`(全面)
- `tests/bt/item_4/test_i4_r2_origin_from_data_grid.py`
- `tests/bt/item_4/test_i4_real_data_smoke.py`
- `tests/bt/item_4/test_i4_r2_signal_at_open_grid.py`(R-H3 の新しい読み)
- `tests/bt/item_4/test_i4_barmodel_on_core.py`(取り消しの理由に kept_older)

**記録**
- `docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/ROOTCAUSE_worker.md`
- 同じ場所の `materials/worker/`(`before_barmodel.txt`・`after_barmodel_before_pipeline_run.txt`・`README.md`)

途中の変更の一部は、リードのコミット c62f2e8 などに既に入っている。

### (b) 試験のコマンドと末尾の行(basetemp はどれも私有、`-p no:cacheprovider -o tmp_path_retention_policy=none` 付き)

| 回したもの | 結果 | 時点 |
|---|---|---|
| `tests/bt/item_0 tests/bt/critic/item_0` | **6709 passed, 4 skipped, 3 warnings in 507.58s** | 核は変えていない |
| 足の模型の格子・批評家の時間切れ・`tests/bt/compat` | **201 passed in 139.42s** | R-E5・R-V を足す前 |
| `test_i4_real_data_smoke.py` と `test_i4_pipeline.py` | **15 passed in 422.59s** | tier 6・資金調達・比べる窓の幅を足す前 |
| 最後の範囲の実行(下) | 392 件通過、5 件失敗 | 最後のコード |

- **最後の範囲の実行の中身**: `test_i4_pipeline.py`・`test_i4_r3_prereg_file_grid.py`・`test_i4_r3_time_exit_at_open_grid.py`・`test_i4_r3_maker_two_values_grid.py`・`test_i4_r2_signal_at_open_grid.py`・`test_i4_barmodel_on_core.py`・`test_i4_battery_scenes.py`・`tests/bt/compat`・`tests/bt/critic/item_4`。
- **末尾の行について**: 私が `-q` を重ねたので、件数の行が出なかった。数えたのは進み具合の行(392 件通過・5 件失敗)で、失敗は全部 `test_i4_battery_scenes.py` の i4-5-fills・i4-5-outputs・i4-6-label・i4-6-signal-refused・i4-6-research-refused。
- **批評家の試験**: 時間切れ 2 件・出所 6 件・事前登録 3 件は、上の範囲の中で通った。`test_i4r2_considered_unread_is_not_confirmed` は場面係の持ち物。
- **出所の格子 2 本と実データの動作確認**: 最後のコードでの実行はまだ走っている。記録は `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/pytest_item4_finish_worker_origin.log`。その中の 1 件の F は、直す前の書き方での TOPIX の every_row_edited の升(値を変えた足が不正な足になって、データ層が断っていた)。書き方を直したあと、その升を含む 4 升を回し直して失敗の行は 0。

### (c) 満たせなかった条件と理由
1. **場面集の統合の場面 5 つが落ちる**(i4-5・i4-6)。場面の宣言が旧の形のまま(fill の first_observed・costs の pct・銘柄に product / rules が無い・`prereg_sha256`)で、正解も旧の「最初に観測した値」で計算されている。直せるのは場面係だけ(規則 2「場面集を変えない」)。場面係にしてもらうこと:
   - 宣言を新しい形に書き直す
   - 研究の場面は事前登録のファイルを置いて `prereg=` で渡す
   - 合成は生成器で作る
   - 正解を項目 2 の模型の規則(板を歩く / 直前の約定 ± スプレッド / 次の足の始値)で出し直す
   - adapter `_pipeline` と私の `i4w_drive.run_pipeline_scene` を新しい引数にする(後者は私の持ち物。次の段で直す)

   場面集 `tests/bt/battery/item_4` 全体の実行は、時間内に終わりの行を確かめられなかった。
2. `test_i4_engine_vs_independent_bar_sim.py` は外して回した。参照実装の役が `bar_sim.py` を書き直していて import が落ちる(第 2 段で広げる物)。
3. 提出前の吟味 (6)(規則を直す前に格子を先に書く)を、統合の口の格子 3 本で守れなかった(直したあとに書いた)。統合の口の直す前の記録は、批評家の試験 9 件の失敗だけ。`materials/worker/README.md` に書いた。

### (d) リードに聞くこと
1. **行が一致しないファイルを「実データ(出所が分からないもの)」として扱う決め**は原文に無い。理由: 合成を生成器だけに限った以上、一致しないファイルを合成にすると、全行を書き換えたファイルで §4 の規則を迂回できる。この形でよいか。
2. **指標の書き出しの見出しの数(既存の欄)を悲観側にした決め**(両側は `metrics["range"]` にある)も原文に無い。この形でよいか。
3. 統合の口で宣言できないまま残るものがある。ここまで要るか:
   - L3 の 1 注文ごとの供給
   - 故障の注入
   - FX の換算表(いまは銘柄の値の通貨 = 口座の通貨に限る)
   - スワップ・手数料表
   - 旧の滑り(slippage_pct)の欄(項目 2 の CostSchedule に無いので受けない)

### (e) 提出前の吟味の結果
- **厳しい批評家が止めそうだと挙げて、潰したもの**:
  - 統合の口が tier 6(影響関数)と資金調達を宣言できない = 部品を狭めて繋いでいる → 宣言できるようにし、試験を足した
  - 同じ種類の事象を乗せたデータセットの断りを、書き換えのときに落としていた → 戻した
  - バーの範囲の端で 1 行を数え落としていた → 比べる窓を 1 日広げた
- **試験側の誤りとして直したもの**:
  - TOPIX のファイルは行末が CRLF で、書き換えがそのあとに付いていた
  - TOPIX の出来高を書き換えると、ミニ TOPIX の実在の行と一致した(値が同じで出来高だけ違う)。規則ではこれも実データの証拠なので、書き換えを値の列に替えた
- **場当たりの直しはしていない**: 規則の側を変えて通した升は無い。落ちた升の直しは、上に挙げた試験の書き方の誤りと、場面係が同時に足した規則(R-E5・R-V2・R-V4)への合わせだけ。
- **残る目立つ点**: 実データの計画は行を照らすので遅い(実データの動作確認 1 本で約 7 分)。

**リードの答え(13:36 UTC)**: (1) 行が一致しないファイルを「出所の分からない実データ」として扱う(合成は生成器からだけ)= 認める(最も厳しい側)。(2) 指標の書き出しの見出しの数を悲観側にし、両側は range に持つ = 認める。(3) L3 の 1 注文ごとの供給・故障の注入・FX の換算表・スワップと手数料表・旧の滑りの欄は、この仕上げでは要らない = 「測っていない範囲」に載せる。
**時間の判断(リード)**: 残り 80 分。第 2 段(作業者 = 格子の広げ + 4 場面の直し + bar_rules の削除 + i4w_drive の新しい宣言 / 場面係 = 統合の場面 5 つを新しい宣言の形に)を 13:36 UTC に並列で起こした(期限 14:05)。批評家は 14:05 に起こす。**第 3 段(旧エンジンの置き換え + 全試験)は批評家と同時に起こす**(委任文 §3 の「批評家の [止める] 0 のあと」から外れる。時間の上限のため。批評家に正しさ・安全の [止める] が出れば置き換えを戻す。この逸脱は報告に書く)。


### 場面係(第 3 段)の返り値(逐語、13:51 UTC)

リードの答え (1)〜(4) と第 2 段の指示を片付け、報告を返しました。場面集と批評家の試験は全部通っています(`248 passed`)。PineForge は、検査した版を取り直したものの比べられていません。新エンジンは 4 場面で正解と食い違い、作業者が直す分として報告しました。

**第 1 段の追加:**
- 待っている建ての指値に、マスクが False の反対向きの合図が来たときは、リードの決めどおり古い指値を残すことにしました。規則の文と場面 2 つを足しました。旧エンジンがどう計算するかは、実際に呼んで確かめました。
- 検査していない版 0d76a099 の clone と構築物は消しました。前に検査した版 5e62602c は取り直しましたが、構築・実行へ進む操作をこの環境の許可の判定がまた止めました。PineForge は道具を 1 度も呼んでいません。検討表・RUNNABILITY・survey_results の全 86 行に「比べていない(理由)」を書きました。
- 検査をせずに 0d76a099 を構築して手順から外れたことは、ROOTCAUSE_r3-1.md に自己申告として残しました。

**第 2 段:**
- 参照実装が字義どおりに読んだ U1〜U8 を、規則の文に足しました。「使わない」は null で表すこと、0 以下の率や寿命 0 を拒むこと、負の手数料を受けること、などです。これを固める場面を 11 足しました。
- 参照を `bar_sim.run_bars` に切り替えました。i4-1-ref-taker・i4-1-ref-maker・i4-3-ref-signal-first の 3 場面とも、新エンジンで「正解と一致」です。
- 私が最初に書いた場面の 1 本に、高値が終値より低い不正な足がありました。新エンジンがその足を拒んだことで気づき、直しました。あわせて、場面集の全部の足を検める試験を足しました。

**新エンジンが正解と食い違う 4 場面**(新エンジンの側で直すもの):
- `i4-14-sides-opposite-keeps-limit` と `i4-14-sides-opposite-two-models`: 向きの制限で止められた SELL で、待っている買いの指値を置き換えてしまう。
- `i4-10-zero-rate-refused`: 率 0 を拒まない。
- `i4-16-zero-timeout-refused`: 寿命 0 を拒まない。

**リードに聞いたこと:**
- 参照は指標の式を持たないので、I4-1 の 2 場面では参照の側の判定から指標を外しました。指示に無い変更なので、これでよいかを聞いています。
- PineForge を進めるには、オーナーが許可の規則を足す必要があります。「比べていない」のまま進めるかを聞いています。
- 拒むべき入力の 3 場面は、旧エンジンも拒みません。場面は仕様の答えだけにし、旧と新の 2 出力は置いていないことを伝えました。

途中でリードがコミットしたため、着手時の基準と HEAD が食い違っています。差分の節の行ごとの帰属は「判定できない」になります。

主なファイル:
- /home/user/trade/tests/bt/battery/item_4/ROOTCAUSE_r3-1.md
- /home/user/trade/tests/bt/battery/item_4/i4_scenes.py
- /home/user/trade/tests/bt/battery/item_4/gen_definitions.py
- /home/user/trade/tests/bt/battery/item_4/adapters/new_impl.py

**リードの決め(13:55 UTC、統合の口の規則 I-1〜I-5。場面係が正解を手で出し直し、作業者が新エンジンを直す)**: I-1 成行の参照 = 注文の時刻以後の最初の観測(項目 0 の核と同じ) / I-2 最初の観測より前の注文は最初の観測で埋まる / I-3 板のある銘柄: 楽観 tier 3 = 板を歩く、悲観 tier 1 = 直前の約定 ± スプレッド(項目 2 の tier 1 の文) / I-4 足の成行 = 注文の時刻以後に始まる最初の足の始値 / I-5 板もスプレッドも無い銘柄は両側とも I-1 の値。場面係が見つけた新エンジンの振る舞い 5 点のうち 1・3・4・5 は欠陥(作業者に回した)。i4-6-signal-refused の対照 2 の置き換え = 認める。


### 作業者(第 2 段 + I-1〜I-5)の返り値(逐語、13:59 UTC)

第 2 段の結果を返しました。新エンジン(spec)と独立の参照 `bar_sim` は 720 場合の全升で一致しました(違い 0 件)。ただし、追加で頼まれた成行の規則 I-1〜I-5 のうち I-2 はまだ満たせていません。

**独立の参照との突き合わせ(条件 2)**
- `test_i4_engine_vs_independent_bar_sim.py` を `bar_sim.run_bars(bars, signals, options)` の口に合わせて書き直しました。足の模型の選択肢を全部、種つきの乱数で引く格子です。
- 格子が空でないことも確かめました。第 1 段で直した spec の欄を 1 つずつ旧に戻すと、24〜100 場合で差が出ます。
- 場面係が返した不一致 4 場面(R-E5・R-V2・R-V4)は、spec の直しで一致しました。

**`bar_rules.py` の削除**
- 消しました(`git rm` 済み、commit はしていません)。作業者の試験の参照は全部 `bar_sim` に替えました。
- まだ import しているのは、批評家の `test_i4r1_pending_signal_before_intrabar_exit.py` だけです。これは批評家の役が直します。

**成行の規則 I-1〜I-5**
- `pipeline.py` で `SimVenue` の前に、成行を最初の観測まで保留する層を置きました。I-1・I-3・I-4・I-5 はそれぞれ試験で通っています。
- I-2(最初の観測より前の注文)は、項目 2 の証拠金の口座が到着の時点で「値が無い」として注文を断るので満たせません。この試験は「予想どおり落ちる」印を付けて残しました。直すには、統合の口で証拠金の検査を遅らせるか、項目 2 の口座を変えるかの判断が要るので、リードに聞いています。

**試験**
- 4 フォルダ全体の実行は `29 failed, 1842 passed, 2 skipped, 10 errors` でした。これは成行の層を入れる**前**のコードでの実行で、入れたあとの全体と実データの動作確認は時間内に回せていません。
- 失敗の内訳:

| 件数 | 中身 | 原因 |
|---|---|---|
| 12 | 批評家の試験 | `bar_rules` の import |
| 6 + 2 | 旧エンジンとの比べ・互換の golden | `src/bot/backtest/engine.py` が変わっている。並行の第 3 段が変えたと推定、私は触っていない |
| 5 | 場面集の統合の場面 | 場面係の正解の出し直し待ち |
| 4 | 場面集の試験 | 未確認 |
| error 10 | 場面集の setup | 未確認 |

リードに聞いたことは 3 つです。
1. I-2 をどちらの形で直すか。
2. 板を見ない側を tier 1・2 とした分け方でよいか。
3. 旧エンジンの変更が第 3 段のものか。

変えた主なファイル:
- `src/bot/bt/pipeline.py`
- `tests/bt/item_4/test_i4_engine_vs_independent_bar_sim.py`
- `tests/bt/item_4/test_i4_pipeline.py`
- `tests/bt/item_4/i4w_drive.py`
- `docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/ROOTCAUSE_worker.md`

**リードの答え(14:01 UTC)**: (1) I-2 = **(甲)** 統合の口で account を包み、値の無い成行の証拠金の検査を最初の観測のあとに遅らせる(項目 2 の account の意味は変えない)。(2) I-3 の分け方(tier 1・2 は板を見ない、0・3〜6 は板を歩く。気配で値を決める銘柄は板で決める)= 認める。(3) golden の 2 件と旧エンジンとの比べ 6 件は第 3 段の置き換え(並行)が原因と読む(推定)。置き換えの作業者が golden の記録(engine.py の sha256)を更新し、旧の写しで比べを取り直す。
**条件 2 は満たした**(新エンジンと独立の参照 = 720 場合の全升で一致。規則の欄を 1 つずつ旧に戻すと差が出る = 格子は空でない)。


### 場面係(第 3 段の続き = 統合の口の規則 I-1〜I-5)の返り値(逐語、14:05 UTC)

項目 4 場面係、第 3 段の続き(統合の口の規則 I-1〜I-5)の報告です(委任文 docs/DATA/delegations/20260926_backtest_env_finish.md@ec283fb43be1 §1 条件 1)。5 場面の正解を規則から手で出し直しました。新実装は 5 場面とも「結果なし」で、作業者が直している途中の核がエラーを出して止まるため、正解との突き合わせはまだできていません。

(a) 変えたファイル(git diff --name-only HEAD、HEAD = 920a34b 14:00:30 UTC のリードのコミット、docs/AUDITOR/TRACE/ を除く)
- 場面係の物: tests/bt/battery/item_4/ROOTCAUSE_r3-1.md、tests/bt/battery/item_4/survey_results/ の 42 本
- 同じ差分に出るが私は書いていない物(作業者の持ち物): src/bot/bt/pipeline.py、tests/bt/item_4/test_i4_pipeline.py
- この段でほかに変えた場面係のファイル(i4_scenes.py、gen_definitions.py、DEFINITIONS.md 1026 行、test_battery_item4.py、opponents/CONSIDERED.md)は 920a34b にもう入っています。
- 未追跡の記録: docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r3-1/run_new_scenes5.sh とそのログ

(b) 試験
- 私有の basetemp で PYTHONPATH=src python -m pytest tests/bt/battery/item_4 tests/bt/critic/item_4 … の末尾の行: `12 failed, 230 passed, 7 skipped in 13.83s`(14:02 UTC)
- 場面集の側は全部通ります。落ちた 12 件はどれも批評家の test_i4r1_pending_signal_before_intrabar_exit.py で、原因は ModuleNotFoundError: bot.bt.reference.bar_rules(第 2 段で作業者が bar_rules.py を消した)。場面集の規則 8 により、批評家の試験は変えていません。
- check_bt_considered.py → OK 誤り 0 件

やったこと
- DEFINITIONS.md の「統合の場面」に I-1〜I-5 を足しました。F-1 は「I-1・I-2・I-4 と悲観の側の I-3 をまとめた形」と書き直し、目的「研究」を断る条件は「事前登録のファイル無し」に直しました。
- 正解は手で出し直しました(出力は写していません)。鍵は <側>:<銘柄> です。
  - 悲観の側と、板の無い銘柄の楽観の側は F-1 です。T0 の注文は最初の観測で埋まり、足の銘柄は 300 秒に始まる足の始値で埋まります。
  - bf の楽観の側は I-3 で板を歩きます(walk_board)。買い 1 は売りの気配 15000010〜15000030 を 0.2 ずつ、売り 1 は買いの気配 15000000〜14999955 を 0.1 ずつ。
  - bf の損益は楽観 −85、悲観 2000 です。
  - i4-6-signal-refused の対照 2 の楽観の側も、同じ注文を I-3 で板に歩かせて出しました。
- 試験 test_pipeline_book_walk_matches_the_board_file を足しました。場面が書く板のファイルを読み直し、板を歩いた答えを別に導いて正解と照らします。
- 規則 4: 5 場面を全 42 対象に通しました(13:55:05〜14:02:03 UTC、全部 rc=0)。

(c) 満たせなかった条件と理由
1. 新実装と mutant は 5 場面とも「結果なし」です。
   - エラー: `VenueProtocolError: on_order: fill model gave no Ack/Reject/StateUnknown for order 'leg2'`(src/bot/bt/core/engine.py:1282)
   - 走らせたのは作業者が直している途中の src/ です。作業者の欠陥として返します。直ったら 5 場面を通し直す必要があります(1 回 7〜12 分)。
2. 批評家の試験 12 件は、bar_rules.py の削除で落ちたままです。

(d) リードに聞くこと
1. 場面の入力を 1 つ変えました(指示の語に無い変更)。01:05 の売りの後に板の写しが無く、I-3 の「以後の最初の板の写し」が無い注文ができていたので、板の写しを 01:05:02 に 1 つ足しました(3 つ → 4 つ)。読んだ事象の数と sha256 の正解はファイルから機械で作り直しています。これでよいですか。
2. 悲観の側の「直前の約定」を「注文の時刻以後の最初の約定」(I-1)と読みました。スプレッド 0 なので F-1 と同じ値になります。これでよいですか。

(e) 提出前の吟味
- 正解は規則の文だけから導き、出力は写していません。板の歩き方は、場面のファイルを読み直す別の試験で確かめました。
- リードの答え 3 つ(対照 2 の置き換え、指標を参照の判定から外す、PineForge は比べていないのまま)は ROOTCAUSE に記録しました(全文は ROOTCAUSE_r3-1.md §6-6・§6-7)。
- ROOTCAUSE 末尾の差分の節を作り直しました。基準の head は 658582d なので、行ごとの帰属は「判定できない」になります。
- 見ていない範囲: 板の深さが足りない注文(walk_board の assert で止まる)、板と約定が同じ時刻にあるときの順(01:05:02)、スプレッドが 0 でない悲観の側。

**リードの答え(14:07 UTC)**: (d)1 板の写しを 01:05:02 に 1 つ足した(3 → 4) = 認める(I-3 が「以後の最初の板の写し」を要求する以上、入力に写しが要る。sha256 の正解はファイルから機械で作り直した、とのこと)。(d)2 悲観の側の「直前の約定」を I-1(注文の時刻以後の最初の約定)と読む = 認める(I-1 の文のとおり。スプレッド 0 で F-1 と同値)。(c)1 `VenueProtocolError: on_order: fill model gave no Ack/Reject/StateUnknown for order 'leg2'` は作業者の物として作業者に渡す。直ったら場面係が 5 場面を通し直す(1 回 7〜12 分、時間が無ければ持ち越しとして記録)。(c)2 批評家の試験 12 件(bar_rules の import)は批評家(14:03 起動)が付け替える。


### 作業者(第 2 段の続き = I-2 甲・VenueProtocolError・battery の失敗の読み)の返り値(逐語、14:16 UTC)

## 作業者 第 2 段の続き(I-2 = 甲、場面係の VenueProtocolError、battery の失敗の読み)の返り値(14:16 UTC)

委任文 §1 の i4-r2-06 の直し方の決め(逐語): 「**pipeline.py の約定・遅延・費用・口座を項目 2 の差し込み口(venue・LatencyModel・ScheduleCostModel・MarginAccount)に置き換え…**」+ リードの答え (甲)「**統合の口で account を包み、値の無い成行の証拠金の検査を最初の観測のあとに遅らせる(項目 2 の MarginAccount は変えない)**」。

結論:
- I-2(甲)は入れて、試験が通った。`test_i4_pipeline.py` の残り 1 件(遅延の試験)も直したあとに通った。
- 実データの動作確認は `2 passed` で通った。
- 場面係の VenueProtocolError は直した。
- ただし場面 i4-5-fills は、まだ楽観の bf で約定の数が合わない(下の (c)-1)。

### 直した中身(事実)
**1. I-2(甲): `pipeline.py` の `DeferredMarginAccount`**
- 項目 2 の MarginAccount を包む。MarginAccount 自身は変えていない。
- 到着の時点で値が無く、account が断った成行(no_price_for_margin_check / no_mark_for_equity)は、その場では断らず保留に記録する。
- ArrivalGate がその注文に値を付ける時点で、先に account に最初の観測を見せてから(`observe`)、証拠金の検査をやり直す(`recheck`)。そこで断られたら Canceled(`refused_by_account: <理由>`)にする。
- 同じ事象が core からもう一度 account に届いたときは、先に返した答えを返す。事象が MarginAccount に届くのは 1 回だけ。
- 試験 `test_i2_an_order_before_the_first_observation_fills_at_it` の xfail(strict) を外した。中身は次の 2 つで、どちらも通る。
  - 最初の約定より前の成行が、最初の約定で埋まる
  - 元本 1 円では、遅らせた検査が断る

**2. 場面係の `VenueProtocolError: on_order: fill model gave no Ack…`**
- 推定のとおりだった。到着前の成行に、ゲートが何も返していなかった(私の第 2 段の途中の版)。
- 今は到着の時点で Ack を返し、値を付けて venue に渡すときに venue の Ack を捨てる。
- 確かめ: 場面係の `run_battery.py --target new_impl --scenes i4-5-fills` を 1 場面分だけ通すと、エラーは出ず結果が出る(下の (b))。

**3. 約定の時刻**
- 約定の `t_ns` を「値を付けた観測の時刻」にした(足は足の始まり、I-4)。
- それまでは venue の時刻(足の終わり)で、場面の pessimistic:jpx が `t_ns` だけ 60 秒ずれていた。

**4. `i4w_drive.run_pipeline_scene`**
- 出力を `"<側>:<銘柄>"` の鍵(両側)にした。場面係の adapter と同じ形。

**5. 遅延の試験 `test_order_latency_moves_the_fill_and_a_seeded_distribution_repeats`**
- 旧の読み(遅延 0.25 秒で約定の時刻が必ず 0.25 秒動く)は I-1 と合わない。0.25 秒の遅延では、到着以後の最初の気配が同じ行になる。
- I-1 の文どおりに書き直した: 約定の時刻 ≥ 送った時刻 + 遅延。遅延 60 秒なら、遅延 0 の約定より後になる。

### (a) 変えたファイル
- `src/bot/bt/pipeline.py`(DeferredMarginAccount、ArrivalGate の Ack と観測の時刻)
- `tests/bt/item_4/test_i4_pipeline.py`(I-2 の試験、遅延の試験)
- `tests/bt/item_4/i4w_drive.py`

### (b) 試験のコマンドと末尾の行(私有の basetemp、`-p no:cacheprovider -o tmp_path_retention_policy=none`、`-q` は重ねない)

| 何を | 末尾の行 | 注 |
|---|---|---|
| `test_i4_pipeline.py` 全体 | `1 failed, 16 passed in 194.38s (0:03:14)` | 失敗 1 件は遅延の試験で、直す前の版で回した分 |
| 直したあとの遅延の試験(`test_i4_pipeline.py -k latency`) | `1 passed, 16 deselected in 134.32s (0:02:14)` | 全 17 件を直したあとの版で通しで回し直してはいない |
| `test_i4_real_data_smoke.py` | `2 passed in 412.22s (0:06:52)` | 回したのはゲート・DeferredMarginAccount・観測の時刻を入れた版 |
| 場面係の sh の 1 場面分(`run_battery.py --target new_impl --scenes i4-5-fills`) | `i4-5-fills I4-5 値 不一致 fills[optimistic:bf]: 26 件(正解 30 件)` | 出力は `…/scratchpad/bt/finish_worker3_scene/new_impl2.tsv` |

1 場面分の経過: 14:09 の版では最初の不一致が `fills[pessimistic:jpx][0]` の t_ns だった。観測の時刻を直した版では、最初の不一致は `optimistic:bf` の件数に移った。

### (c) 満たせなかった条件と理由
1. **場面 i4-5-fills の `optimistic:bf` が 26 件(正解 30 件)で合わない。**
   - 楽観の側(tier 3)は板を歩く。原因の推定は 2 つで、どちらかを場面の正解(板のファイルから出したもの)と照らしていない = 未確認。
     - 板を歩いて約定が段ごとに分かれる数え方の違い
     - 成行の残りを取り消す(market_remainder = cancel)ことで、約定しない分がある
   - 期限のため、ここで止めた。他の 4 つの統合の場面も、この版では回していない。
2. 範囲の全体は回していない(リードの指示)。

### battery の失敗 4 件と setup の error 10 件の読み(1 行ずつ)
- `test_legacy_answers_of_two_model_scenes_are_the_existing_engine`・`test_mutant_plants_one_defect_and_breaks_its_scenes`・`test_stated_rules_and_existing_engine_agree_except_the_listed_deviations` と、`test_battery_item4_claims.py` の setup の error 10 件(`test_invariants_hold_on_the_existing_engine_and_the_hand_answers`・`test_invariants_catch_each_perturbation[i4-2-grid-*]`)
  - 全部同じ原因: `ImportError: cannot import name 'evaluate_on_splits_as_old' from 'bot.bt.compat.engine'`。
  - 旧 `src/bot/backtest/walk_forward.py:18` がその名を import していた。それを書いた置き換えの作業者(第 3 段)が、その時点ではまだ compat の側に関数を足していなかった(推定。いまは `src/bot/bt/compat/engine.py:274` にある)。
  - **置き換えの物で、私の物ではない。** 今の木で `test_battery_item4_claims.py` と `test_battery_item4.py` を回し直すと `148 passed in 5.11s`。
- `test_pipeline_expected_fills_match_the_files`
  - `KeyError: 'optimistic:bf'`。場面係が場面の正解を両側の形に書き直している途中だった(**場面係の物**)。
  - 今の木では通る(上の 148 件に入っている)。

### (d) リードに聞くこと
1. i4-5-fills の `optimistic:bf` の件数の違い(26 対 30)を、次の周で私が板のファイルと照らして直すか。それとも場面係に正解の数え方(板を歩く約定の数え方と、成行の残りの扱い)を確かめてもらうか。

### (e) 提出前の吟味
- (甲) は項目 2 の MarginAccount を変えていない。検査を遅らせるのは、DEFERRABLE の 2 つの理由(値が無い)の成行だけ。それ以外の断りは到着の時点のまま効く。
- 遅らせた検査が断る側も、試験で確かめた(元本 1 円)。
- 事象を account に 2 回渡さない作り(`observe` の答えを取っておく)。清算の注文が二重に出ないため。
- 遅延の試験の直しは、I-1 の文に合わせたもの。閾値をずらして通したものではない(遅延 60 秒で、約定が遅延 0 より後になることを確かめている)。

**リードの答え(14:19 UTC)**: (d)1 = 作業者が板のファイルと照らす(場面係の正解は I-3 の文から板のファイルを読み直す別の試験 `test_pipeline_book_walk_matches_the_board_file` で確かめてある = 正解の側は 2 経路で一致している)。違いの原因が「段ごとの数え方」なら実装を場面係の数え方(規則の文)に合わせる。「成行の残りの取り消し」なら、規則の文(DEFINITIONS.md の I-3)に残りの扱いが書いてあるかを読み、書いてあれば実装を合わせ、書いてなければ直さずに「規則の文に無い(持ち越し)」と返す。期限 14:40 UTC。それまでに直らなければ持ち越しとして報告に載せる。


### 作業者(i4-5-fills の 26 対 30)の返り値(逐語、14:25 UTC)

## 作業者(i4-r2-06 の続き: i4-5-fills の optimistic:bf 26 件 対 30 件)の返り値(14:25 UTC)

規則の文(`tests/bt/battery/item_4/DEFINITIONS.md` 153-155 行、逐語): 「**I-3 板がある銘柄の成行: 楽観(tier 3)= 注文の時刻以後の最初の板の写しを、数量の分だけ段を進んで埋まる(買いは売りの気配の良い方から、売りは買いの気配の良い方から。各段の値と量で部分約定、時刻は板の写しの時刻)**」

結論: 違いの原因は、リードが挙げた 2 つ(段ごとの数え方・成行の残りの取り消し)の**どちらでもなかった**。実装が I-3 の文と違っていたので、文に合わせて直した。統合の場面 5 つは全部「正解と一致」になった。

### 原因(事実。観測の jsonl を読んだ)
- ArrivalGate は、約定で値を決める銘柄(bf)では、楽観の側でも「到着以後の最初の**約定**」で注文を venue に渡していた。
- そのため venue は、その時点で最後に見た板を歩いた(到着より前の板)。板をまだ一度も見ていなければ、直前の約定の値で 1 件にまとめて埋めた。
- 観測の例:
  - 最初の買い(00:00:00 の注文)は、00:00:00.2 の約定で 15000000 × 1.0 の 1 件になった。正解は 00:00:10 の板を 0.2 ずつ 5 段。
  - 00:05:00 の売りは、00:00:10 の古い板を歩いた。正解は 00:05:01 の板。
- I-3 の文は「注文の時刻以後の**最初の板の写し**」で、これと違う。

### 直し(`src/bot/bt/pipeline.py` の `_run_instrument` と ArrivalGate の docstring)
- 約定で値を決める銘柄に板が乗っていて、その側が板を歩く(tier が BOOKLESS_TIERS の外)なら、ゲートが待つ観測を**板の写し**(BookSnapshotEvent)にした。
- 悲観の側(tier 1、板を見せない)と板の無い銘柄は、これまでどおり約定で待つ(I-3 の悲観・I-5)。
- 段ごとの数え方と成行の残りの扱いは変えていない。

### (a) 変えたファイル
- `src/bot/bt/pipeline.py`

### (b) 試験のコマンドと末尾の行(私有の basetemp、`-p no:cacheprovider -o tmp_path_retention_policy=none`、`-q` は重ねない)
- `PYTHONPATH=src python -m pytest tests/bt/item_4/test_i4_pipeline.py --basetemp=<scratchpad>/bt/finish_worker5_pipe …` → **`17 passed in 162.60s (0:02:42)`**(直したあとの版。前回の遅延の試験の直しも含む)
- 場面係の走らせ方の 1 場面分: `PYTHONPATH=src python3 tests/bt/battery/item_4/run_battery.py --target new_impl --out <scratchpad>/bt/finish_worker3_scene/new_impl3.tsv --scenes i4-5-fills` → 出力の行 **`i4-5-fills  I4-5  値  正解と一致  8d57d621e29e  正解と一致  8d57d621e29e`**(2 回とも一致、digest も同じ)
- 同じ走らせ方で残る統合の 4 場面(`new_impl4.tsv`)も、4 場面とも 2 回とも「正解と一致」:
  - `i4-5-outputs` 能力
  - `i4-6-label` 値
  - `i4-6-signal-refused` 能力(変形を拒んだ: price_rule は時刻だけの戦略でない)
  - `i4-6-research-refused` 能力(変形を拒んだ: 事前登録のファイルが無い)
- 実データの動作確認(`test_i4_real_data_smoke.py`)は、この直しのあとには回していない。前回の `2 passed in 412.22s` は、この直しの前の版。

### (c) 満たせなかった条件と理由
- 実データの動作確認をこの版で回し直していない(時間)。この直しは、板が乗った約定の銘柄(実データでは bf)の楽観の側の約定の値と時刻を変える。動作確認の試験が検める構造(4 注文とも両側で FILLED、数量の全部)が保たれるかは未確認。

### (d) リードに聞くこと
- なし。

### (e) 提出前の吟味
- **直した根拠**: I-3 の文の「注文の時刻以後の最初の板の写し」「時刻は板の写しの時刻」。場面係の別経路の試験 `test_pipeline_book_walk_matches_the_board_file`(板のファイルを読み直して正解を出す)と同じ読みである。
- **同じ根の全箇所**: 板で値を決める側の待つ観測を決めているのは `_run_instrument` の 1 か所だけ。気配で値を決める銘柄(FX のティック)は、もともと写しそのものが観測なので変わらない。足の銘柄も変わらない(I-4)。
- **場当たりでないこと**: 場面の値に合わせて数を変えた所は無い。待つ観測の型を規則の文に合わせただけで、場面 5 つと `test_i4_pipeline.py` 17 件が通った。

**リードの読み(14:27 UTC)**: 原因はリードが挙げた 2 つのどちらでもなく、ゲートが楽観の側でも約定で待っていた(I-3 の文「最初の板の写し」と違う)。直しは規則の文に合わせたもので、統合の場面 5 つが全部「正解と一致」(2 回とも同じ digest)、test_i4_pipeline.py 17 passed。実データの動作確認はこの版で未実施 → 作業者に回させる(期限 14:42)。


### 置き換えの作業者(第 3 段 = 条件 3)の返り値(逐語、14:28 UTC)

## 作業者(第 3 段 = 条件 3「旧エンジンの置き換え」)の返り値

**結論**: 置き換えはできたが、全試験で私の置き換えが原因の失敗が 2 件出た。指示どおり `src/bot/backtest/` の 3 本を旧(写しと同じバイト)に戻した。条件 3 は未達。原因は場面集 item_0 の出所の検めで、場面係かリードが決める事柄。

**置き換えで落ちた 2 件**: `tests/bt/battery/item_0/test_battery_item0.py::test_current_impl_runs_every_scene_twice_identically`、`::test_current_impl_passes_the_provenance_check`。
- 原因: `tests/bt/battery/item_0/run_battery.py:291` の `TARGET_DISTS["current_impl"] = {"py": ["bot.backtest", "bot.strategy"]}`。
- 置き換えたあとに実際に走るコードは `bot.bt.compat` と `bot.bt.core` にあり、この一覧に入っていない。そのため 9 場面が「出所の検めで採点しない…対象の配布物に無い」と判定されて error になった。

リードの途中の commit について: e45109a には置き換えた版が入り、63e64c0 と 8f441c9 には戻した版が入っている。HEAD 8f441c9 の `src/bot/backtest/` は fa82126 と差分 0 である。

### (a) 変えたファイル
- `src/bot/bt/compat/engine.py`(旧と同じ数を出す層)
  - 足したもの: `run_backtest_as_old`・`evaluate_on_splits_as_old`・`route_of`・`_old_arithmetic`。`_old_arithmetic` は旧 `run_backtest` の複写で、変えたのは名前だけ。
  - 互換の口 `run_backtest` は中身を `_on_core` に分けただけで、振る舞いは変えていない。不正な足を拒むことも含めて、核の契約は変えていない。
  - 核を通すのは次の 4 つがすべて満たされるときだけ。どれか 1 つでも外れたら旧の算術に回す。
    - 足がすべて核に通る。
    - `costs` が CostModel そのもので、4 つの率が有限であり、taker の価格が正になる。
    - `order_notional_jpy` が有限で 0 より大きい。
    - stop・tp・maker_tp の率が None か有限。
  - 道筋は戦略を呼ぶ前に決まる。
- `src/bot/backtest/engine.py`・`metrics.py`・`walk_forward.py`: 委譲の形に一度置き換え、そのあと旧に戻した。置き換えた版は `materials/replace/replaced_version_reverted/` に残してある。
- `tests/bt/compat/test_replace_layer_grid.py`(新規、107 件): 層を旧の写しと格子で突き合わせる試験。
  - 不正な足の形 27 × 位置 4 × 選択肢(1008 セルと 28 セル)
  - 変な選択肢の値
  - CostModel の子クラス 4 種
  - `evaluate_on_splits`
  - 戦略を呼ぶ回数
  - 正しい足が必ず核の道を通ること
  - critic の小数価格のセルを写しと比べること
  - 旧の算術がテキストとして写しと同一であること
  - 格子に入れていないものの一覧はファイル冒頭に書いた。
- `docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/`:
  - `old_engine_snapshot/`: 旧の写しと SHA256SUMS。golden が記録する sha256 と一致する。
  - 直す前の記録: `before_old8_and_compat_at_HEAD_fa82126.log`
  - 置き換えたあとの各記録、戻したあとの記録
  - 変異の検証 `layer_grid_mutants.*`
  - 速度 `speed_5000_bars_old_vs_replaced.txt`

### (b) 試験のコマンドと末尾の行
共通の形: `PYTHONPATH=src python -m pytest -p no:cacheprovider -o tmp_path_retention_policy=none --basetemp=<私有>`

- **直す前**(fa82126 の複写で、旧の試験 8 本 + `tests/bt/compat/`): `148 passed in 135.21s`
- **置き換えたあと**(同じ範囲): `243 passed, 4 skipped in 475.67s`
  - 飛ばした 4 件は「生きている旧エンジン」との比較。これは写しとの比較で置き換えた。
  - 試験 8 本は変えていない。
- **置き換えたあと、旧を import する 12 本**: 1 本ずつ import して全部成功した。`after_replace_12_importers_import.txt`
- **置き換えたあとの全試験**(`--continue-on-collection-errors` つき): 11% 付近で打ち切った。
  - `2 failed, 2316 passed, 15 skipped, 3 warnings, 1 error in 1067.24s`
  - 失敗の 2 件は上の item_0 の出所の検め。
  - error の 1 件は `tests/bt/critic/item_4/test_i4r1_pending_signal_before_intrabar_exit.py` の収集エラーで、`new_impl` という名前の取り違えによる。fa82126 でも同じエラーが出るのを確かめた。
- **置き換えたあと、item_0 の場面集と critic の item_0**: `2 failed, 584 passed, 2 skipped`(同じ 2 件)
- **置き換えたあと、場面集 item_1〜4**: 80 / 16 / 69 / 172 passed。失敗は 0。
- **戻したあと**(旧の 8 本 + compat + item_0 の current_impl の 2 件): `257 passed in 545.82s`
- **戻したあとの critic item_4**: `3 failed, 80 passed`
  - 3 件は `test_i4r3_deferred_account_sees_each_event_once.py` で、第 3 周の批評家の新しい試験。核と口座の話で、旧エンジンとは関係しない。
- **戻したあとの全試験**: 実行中。14:27 UTC の時点で `[  4%]`、失敗 0。
  - ログは `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/pytest_item4_finish_replace_full_reverted.log`
  - 収集した試験は 21,002 件ある。今の混み具合では終わるまで約 2.5〜3 時間かかる見込み(推定)。「約 25 分」には収まらない。

### (c) 満たせなかった条件と理由
- **条件 3「全試験が全部通る」**: 置き換えた状態では、上の 2 件が落ちる。直す場所は `tests/bt/battery/item_0/` で、場面係の持ち物なので私は触れない。
- **全試験の完走**: 21,002 件あり、時間内に終わらない。どちらの状態の実行も途中まで。

### (d) リードに聞くこと
1. item_0 の `current_impl`(現状)は、置き換えたあと何を指すことにするか。
   - 案 A: `TARGET_DISTS["current_impl"]` に `"bot.bt"` を足す。この場合、現状 = 新エンジンの legacy になり、item_0 の表の列の意味が変わる。
   - 案 B: `current_impl` の adapter が旧の写しを読むようにする。旧エンジンの記録として残す形。
   - どちらかに決まれば、`replaced_version_reverted/*.py` を `src/bot/backtest/` に写すだけで置き換えを再適用できる。
2. 層が核の通らない入力を「旧の算術の複写」で計算していることは、L-407 の「例外は作らない」を満たすと読んでよいか。
   - 核の契約を変えずに旧と同じ数を返すには、この方法しか見つからなかった。
   - 複写は写しとテキストで一致し、正しい足では一度も使われないことを試験で確かめている。
3. 範囲を広げたことの確認。指示にあったのは不正な足だけだが、次の入力でも互換の口は旧と違う結果(拒否か別の数)を返していた。
   - CostModel の子クラス(旧は上書きした `buy_price`・`fee` を使っていた。item_0 の場面 p7 がこれを使う)
   - `order_notional_jpy` が 0 以下か NaN
   - stop の率が NaN
   - taker の価格が 0 以下になる費用
   - 同じ根なので同じ層で旧の算術に回した。これでよいか。
4. 速度: 核の道は旧より遅い。5,000 本の足で、旧の写し 0.16 秒に対し置き換えた版 2.01 秒(混んだ状態での実測)。研究のスクリプトを大きなデータで回すと時間が延びる。
5. 全試験の実行の仕方。critic item_4 の収集エラーは既存のもので、何もしないと全試験が収集の段で止まる。私は `--continue-on-collection-errors` を付けて回した。この付け方でよいか。

### (e) 提出前の吟味
1. **要件の読み直し**: 条件 3 の文と照らした結果。
   - 委譲にした・旧の名前を残した・例外を作らなかった・写しを置いた・格子の試験を足した・8 本と golden が通った・12 本が import できた、の 7 点は満たした。
   - 満たせなかったのは全試験が通ることだけで、そのため戻した。
2. **同じ根の全箇所**: 「互換の口が旧の計算した入力を拒む」という根を、選択肢の全部について probe で探した(`materials/replace` の probe の結果。拒否の種類の違いは ValueError の文で比べた)。見つかった 5 種類は全部、層で旧の数を返す。
   - 別の根も 1 つ見つけた。「旧エンジンをモジュールの場所で見分ける箇所」で、item_0 の TARGET_DISTS と、`_old_engine_present()` で飛ぶ試験がこれに当たる。飛ぶ試験は写しとの比較で置き換えた。item_0 は (d)1 に回した。
3. **批評家と場面集の試験**: compat・critic item_4・場面集 item_0〜4 を回した。落ちたものの原因は上に分けて書いた。
4. **厳しい批評家なら止めるもの**:
   - 旧の算術が層の中に残っていること → (d)2 に書いた。
   - 置き換えたあと `run_backtest.__name__` が `run_backtest_as_old` になること(署名は旧と同じ)。
   - 速度 → (d)4 に書いた。
   - 互換の口そのものは不正な足を拒んだままであること(既存の試験がそれを約束している)。
5. **場当たりの直し**: していない。試験だけを特別扱いする直しや、閾値をずらす直しは無い。
6. **敵対者の格子**:
   - 形・位置・選択肢で入力を並べ、層の分岐からは作らなかった。
   - 変異を 5 通り入れ、5 通りとも捕まえた。
   - 別に試した「ちょうど同じ値で止まる」の変異(`<=` → `<`)は値の格子では捕まらなかった。そこで写しとテキストが同一であることを確かめる試験を足して塞いだ。
   - 格子に入れていないもの: 数値でない列、列の欠け、DataFrame でない入力、並んでいない・重複した index、例外を出す戦略、40 本以外の本数。

**リードの読みと答え(14:31 UTC)**: 条件 3 は**未達**(置き換えると場面集 item_0 の出所の検め 2 件が落ちる → 指示どおり旧に戻した。HEAD の src/bot/backtest/ は fa82126 と差分 0)。(d)1 = item_0 の「現状」が置き換え後に何を指すか(案 A: 新エンジンの legacy = 表の列の意味が変わる / 案 B: 旧の写し)は**枠組みの変更(A-13)なのでオーナーに聞く**(上限の回の報告に載せる)。(d)2 = 委任文 §1 条件 3 の「旧と同じ数を出す層」の設計のとおりだが、「旧の算術の複写が層の中に残る」ことはオーナーに開示する。(d)3 = 同じ根なので認める(開示する)。(d)4 = 速度 0.16 秒 → 2.01 秒(5,000 本)はオーナーに開示。(d)5 = 収集エラーは批評家の試験(bar_rules の import)で批評家が付け替え中。`--continue-on-collection-errors` は今回はよい。全試験(21,002 件)は時間内に終わらない = 「測っていない範囲」として報告する(戻した版の全試験は背景で続行、ログの場所は上)。


### 批評家(第 3 周)の返り値(逐語、14:29 UTC。全文は round_3/CRITIC.md)

# 項目 4 第 3 周 批評家の記録(統合の周)

委任文 `docs/DATA/delegations/20260926_backtest_env_finish.md@ec283fb43be1`(親 `20260925_backtest_env_prompt.md@388d55cdeb32`)。起こされた時刻 14:03 UTC、期限 14:35 UTC。射程は委任文 §2 の逐語「[止める] にするのは **正しさ(場面集の正解・規則の文・独立の参照と食い違う)・安全(実データ・事前登録・封印の規則を迂回できる)・統合(部品が繋がっていない、試験が落ちる)・場面集の規則 1〜9 の違反(比べの結果を変えるもの)**」「報告の書き方・注記の言い回し(比べの結果を変えないもの)は **[直す] 以下**」。

## 0. 対応表(CLAUDE.md §0.1)

| やろうとすること | 委任文・起こし文の該当語(逐語) |
|---|---|
| 第 2 周の [止める] 9 件が閉じたかを VERDICTS と round_3/ の根本原因で確かめる | 「第 2 周の [止める] 9 件(委任文 §1 の i4-r2-01〜09 と「直し方の決め」)が閉じたか」 |
| barmodel.py・engine.py・pipeline.py・bar_sim.py・SPEC.md・格子・場面集を読む | 「実装: src/bot/bt/compat/barmodel.py・engine.py、src/bot/bt/pipeline.py(…)、独立の参照 …、格子 …、場面集 …」 |
| bar_rules.py を import する 12 件を bar_sim の口に付け替える | 「削除された src/bot/bt/reference/bar_rules.py を import する 12 件は、あなたが bar_sim(…)か compat の口に付け替えて直す」 |
| 落ちる試験と対照を tests/bt/critic/item_4/ に足す | 「批評家の試験は `tests/bt/critic/item_4/` に足す(落ちる試験 + 対照)」 |
| 3 役の途中の落ちは「途中(誰の物)」と書く | 「これら 3 つの途中の落ちは、その役が返る前は [止める] にせず「途中(誰の物)」と書く」 |
| 14:35 UTC で途中でも返す | 「返す期限 **14:35 UTC**(…時間が来たら途中でも返す)」 |

## 1. 整備(批評ではない): bar_rules の付け替え

`tests/bt/critic/item_4/test_i4r1_pending_signal_before_intrabar_exit.py:100` の `from bot.bt.reference.bar_rules import run_rules` を `bot.bt.reference.bar_sim.run_bars(bars, signals, options)` に付け替えた。場面集の config → 参照の options の写し(`_ref_options`: initial_equity → capital、order_notional → order_amount、bar_seconds、undecided = リードの値 U1 `use_available`・U2 `keep`)を同じファイルに置いた(作業者の `i4w_drive.reference_options` と同じ形だが、作業者のファイルは import していない)。
結果: `PYTHONPATH=src python -m pytest --basetemp=<私有> -p no:cacheprovider tests/bt/critic/item_4/test_i4r1_pending_signal_before_intrabar_exit.py` → **36 passed in 0.77s**(付け替えた 12 件を含む。独立の参照も R-T1 の答えを返す)。

## 2. 第 2 周の [止める] 9 件が閉じたか(自分で確かめた範囲)

| id | 確かめ方(読んだ所・打ったもの) | 結果 |
|---|---|---|
| i4-r2-01 | `adapters/new_impl.py:199-209` `_run_reference` が `bot.bt.reference.bar_sim.run_bars` を呼ぶ。`bar_rules.py` は作業木に無い(`ls src/bot/bt/reference/` = SPEC.md・bar_sim.py・event_sim.py・num.py)。格子 `test_i4_engine_vs_independent_bar_sim.py` は下の全体の実行に含めて回した | 閉じた(場面集の口が独立の参照を呼ぶ) |
| i4-r2-02 | 私の第 2 周の試験 `test_i4r2_time_exit_at_the_open.py` が通る(下の全体の実行)。作業者の ROOTCAUSE_worker.md §1(`time_exit_at_open`、spec のみ) | 閉じた |
| i4-r2-03 | `pipeline.py:387-425` `row_evidence`: データ層で読んだ行の (時刻, 値) を市場のフォルダのファイルの行と照らす。`:623-636` 合成は `{name, generator}` からだけ(`origin: "synthetic"` の宣言は断る)。私の第 2 周の試験 `test_i4r2_origin_survives_reencoding.py` が通る | 閉じた |
| i4-r2-04 | `test_i4r2_considered_unread_is_not_confirmed.py` が通る | 閉じた |
| i4-r2-05 | `pipeline.py:602-616`: `prereg_sha256` は断る、`prereg` は root の下のファイル、空は断る、研究はファイル必須。`test_i4r2_research_needs_a_real_preregistration.py` が通る | 閉じた |
| i4-r2-06 | `pipeline.py:117-129` の import に fill(SimVenue・FillRange)・latency(LatencyModel)・costs(ScheduleCostModel)・portfolio(MarginAccount)。`:968-984` で銘柄ごとに差す。`:516-518` `_check_fill` は両側必須、`:1039` 両側を回す。自前の 4 つの名は無い(`grep -n "FirstObservedFill\|NullAccount\|_Latency\|_Fee" pipeline.py` = 0) | 閉じた(ただし口座の差し込みに新しい欠陥 = i4-r3-01) |
| i4-r2-07 | VERDICTS の場面係の返り値: 検査した版 5e62602c を取り直したが、この環境の許可の判定が構築・実行を止めた(道具は 1 度も呼んでいない)。リードの決め(12:52)「比べていない(…)のまま進める」 | 測定では閉じていない。リードの決めで「比べていない(理由つき)」の記録に置き換え = [注記](i4-r3-03) |
| i4-r2-08 | 作業者 ROOTCAUSE_worker.md §5(`maker_mask_at_signal`・`maker_same_side_keeps`、spec のみ)、場面係が R-E4・R-M6 と場面 5 つを足した(VERDICTS 12:33) | 閉じた |
| i4-r2-09 | `test_battery_item4_diffscope.py` が通る(下の全体の実行) | 閉じた |

## 3. 指摘

### i4-r3-01 [止める] 安全・統合(target=実装)口座の差し込み口が、統合の口で遅らせた証拠金の検査の観測を MarginAccount に 2 度見せ、その観測で出た強制清算の注文を落とす
- **作業者の I-2(甲)の途中の部品**である(起こし文「作業者(I-2 = …)」)。作業者が返った時点でこの形のままなら [止める]。作業者が返る前は「途中(作業者)」の印も付ける。
- 読んだ所: `src/bot/bt/pipeline.py:816-855` `DeferredMarginAccount`。docstring は「each event reaches the MarginAccount once」と書き、`observe`(:836)が `id(event)` を憶え、`on_market_event`(:846)が同じ `id` のときだけ憶えた答えを返す。しかし核は受け手ごとに**別の写し**を渡す: `src/bot/bt/core/engine.py:1219`(約定模型 = ArrivalGate へ `copy_carrier(event)`)と `:1222`(口座へ別の `copy_carrier(event)`)。`values.py:1935-1939`「each receiver holds objects no one else holds」。よって `id` は決して一致せず、`_seen` は捨てられ `inner.on_market_event` が**もう 1 度**呼ばれる。
- 結果を変える所: `src/bot/bt/portfolio/account.py:339-354` `_maybe_liquidate` は `_forced_pending = True` を立てて強制清算の注文を**1 度だけ**返す。1 度目(`observe`、答えは核に渡らない)で立った旗のせいで、2 度目(核が受け取る方)は `[]`。**保留した成行を値付けする観測で証拠金が維持率を割ると、清算の注文が消え、その口座は以後 2 度と清算されない**(`_forced_pending` が立ったまま)。悲観側の幅・証拠金の結果(要件 I4-5・委任文 §1 i4-r2-06「証拠金が実行記録に出ること」)が誤る。
- 試験: `tests/bt/critic/item_4/test_i4r3_deferred_account_sees_each_event_once.py`(格子 = 観測 {trade・bar・book} × 渡し方 {核の写し・同じ物(対照)})→ **3 failed, 3 passed**。落ちた 3 件の文: `the MarginAccount saw the trade observation 2 times (stated: once)`(bar・book も同じ)。対照 3 件(同じ物を渡す)は通る = 試験は空でない。
- fix_files: `src/bot/bt/pipeline.py`(`DeferredMarginAccount`。`id` でなく、値の等しさ + 時刻、または「次に核から来る同じ時刻・同じ型の観測 1 件を写しと見なす」印で照らす。もしくは `observe` を消し、`recheck` で口座の `_to(t)` と mark の更新だけを別の口で行う)。核(`engine.py` の写し)は変えない(核の契約 = 受け手ごとに別の物、は正しい)。
- 打ったコマンド: `PYTHONPATH=src python -m pytest --basetemp=<私有> -p no:cacheprovider tests/bt/critic/item_4/test_i4r3_deferred_account_sees_each_event_once.py` → `3 failed, 3 passed in 0.46s`。

### i4-r3-02 途中(場面係)場面集の統合の場面 `i4-5-fills` が落ちる
- `tests/bt/item_4/test_i4_battery_scenes.py::test_scene_is_answered_right_and_the_same_twice[i4-5-fills]` → `fills[pessimistic:bf]: None 件(正解 4 件)`。起こし文「場面係(統合の場面 5 つの正解を I-1〜I-5 の規則で導き直す)」の途中の落ちなので [止める] にしない。場面係が返ったあとに残れば [止める](統合)。

### i4-r3-03 [注記] 場面集(target=場面集)PineForge は 3 周続けて 1 場面も走っていない(場面集の規則 4)
- 第 2 周の i4-r2-07 は測定では閉じていない。VERDICTS の記録: 検査した版 5e62602c を取り直したが「構築・実行へ進む操作をこの環境の許可の判定がまた止めた。PineForge は道具を 1 度も呼んでいない」。リードの決め(12:52 UTC)「比べていない(この環境の許可の判定が構築・実行を止めた。道具は呼んでいない)」のまま進め、「測っていない範囲」に載せる。
- 比べの結果は変えない(相手が 1 つ減るだけで、新エンジンの正解との一致は変わらない)ので [注記]。完了の報告の「測っていない範囲」に、規則 4 の文どおり「この周では未実行」ではなく理由(許可の判定)と、走らせるのに要るもの(オーナーの許可の規則)が書かれていることをリードが確かめること。

### i4-r3-04 [注記] 実装(target=実装)作業者の I-2 の試験は印なしで作業木にあるが、i4-r3-01 の経路を含まない
- `grep -rn "xfail" tests/bt/item_4/*.py` = 0 件(14:09 UTC)。`tests/bt/item_4/test_i4_pipeline.py:351` `test_i2_an_order_before_the_first_observation_fills_at_it` は印なし(作業者が (甲) = `DeferredMarginAccount` を置いて印を外した途中の状態と読む。推定)。この試験が見るのは「最初の観測で埋まる」と「1 JPY の口座で遅らせた検査が断る」の 2 つで、保留した成行の値付けの観測で清算が起きる経路(i4-r3-01)と、口座がその観測を 1 度だけ見ることは見ていない。比べの結果は変えないので [注記]。作業者が返るときに i4-r3-01 の試験が通ることを返り値に書くこと。

## 4. 回した試験(全部 `PYTHONPATH=src python -m pytest --basetemp=<私有の basetemp> -p no:cacheprovider <path>`、`-q` は足していない)

| 対象 | 末尾の行 | 時刻(UTC) |
|---|---|---|
| tests/bt/critic/item_4 + tests/bt/battery/item_4 + tests/bt/item_4 + tests/bt/compat(`-x`、bar_rules 付け替え前の私の 1 本を deselect) | `1 failed, 1286 passed, 7 skipped, 36 deselected in 150.67s`(落ちたのは `test_i4_battery_scenes.py::…[i4-5-fills]` = i4-r3-02 途中(場面係)。`-x` なのでそこで止まり、以後は回っていない) | 14:06 |
| 同じ 4 つを `-x` 無しで | 2 回とも 600 秒 / 560 秒の上限で止められ(exit 143)、末尾の行は取れていない(他の役の pytest が同時に 14 本走っていた: `ps aux \| grep -c "[p]ytest"` = 14) | 14:06〜14:26 |
| tests/bt/compat | `152 passed in 460.14s` | 14:24 |
| tests/bt/critic/item_4(付け替え後、私の r3 の試験を含む) | `3 failed, 80 passed in 40.37s`(落ちた 3 件は全部 i4-r3-01 の私の試験) | 14:11 |
| tests/bt/critic/item_4/test_i4r1_pending_signal_before_intrabar_exit.py(付け替えた 12 件を含む) | `36 passed in 0.77s` | 14:08 |
| tests/bt/item_4/test_i4_engine_vs_independent_bar_sim.py + test_i4_pipeline.py(格子 720 場合と統合の口。`-x` の実行で届かなかった分) | `38 passed in 140.94s` | 14:28 |

**bar_rules の付け替え**: 済み(§1)。12 件とも `bar_sim.run_bars` で通る。

**[止める] 1 件(i4-r3-01。作業者の I-2 の途中の部品なので、作業者が返る前は「途中(作業者)」の印つき)、[直す] 0 件、[注記] 2 件(i4-r3-03・04)、途中 1 件(i4-r3-02 = 場面係)。**

## 5. 時間が来て読めなかった範囲(全部書く)

- `src/bot/bt/compat/barmodel.py`(754 行)・`engine.py`(576 行)の本文は読んでいない。第 2 周の指摘 02・08 の閉じは、作業者の ROOTCAUSE_worker.md の記述と、私の第 2 周の試験と作業者の格子(720 場合)が通ることで確かめた(実装の行を目で追ってはいない)。
- `src/bot/bt/reference/SPEC.md`(228 行)と `bar_sim.py` の 249 行目以降(`run_bars` の本体)は読んでいない。独立の参照の正しさは格子の一致(38 passed)にだけ依っている。
- 場面集 `DEFINITIONS.md`・`CONSIDERED.md`・`gen_considered.py` の第 3 周の差分(I-1〜I-5 の規則の文、U1〜U8 の追記、場面 11 + 5 + 2)は読んでいない(場面係が今も書いている)。
- `tests/bt/item_4/` のうち上の 2 本と `-x` の実行が届いた分以外(`test_i4_r3_*` の格子 4 本・`test_i4_real_data_smoke.py` など)は、この周では末尾の行を取れていない。
- 置き換えの作業者の差分(`src/bot/backtest/{engine,metrics,walk_forward}.py`、`git diff --stat` = 3 files changed, 429 insertions(+), 51 deletions(-))は読んでいない。`tests/bt/compat` は 152 passed。旧エンジンとの比べの試験が `tests/bt/item_4` にある分は未確認。

**リードの処置(14:33 UTC)**: i4-r3-01 = 作業者は 14:16 に返っており、この形のままなので **[止める] 1 件**として戻す(委任文 §4「戻しを 1 回だけ」)。直し方は批評家の案のうち「id でなく値の等しさ + 時刻で照らす」ではなく、事象の同一性に依らない形(observe を消し、recheck の前に口座の時刻と mark の更新だけを別の口で行う、または核が渡す写しを口座に 1 度だけ渡して答えをそのまま核に返す)を作業者が選ぶ。批評家の試験 3 件が通ること。i4-r3-02 = 作業者の 14:25 の直しで統合の場面 5 つが「正解と一致」になった(閉じた。批評家の再検で確かめる)。i4-r3-03・04 = 報告に反映する。


### リードの実測(14:36 UTC、コンテナの再起動のあと。作業木 = 作業者の i4-r3-01 の直しの差分をコミットした ac44f7c)

```
$ PYTHONPATH=src python -m pytest -p no:cacheprovider --basetemp=<私有> tests/bt/critic/item_4/test_i4r3_deferred_account_sees_each_event_once.py
6 passed in 0.20s
$ PYTHONPATH=src python -m pytest -p no:cacheprovider -o tmp_path_retention_policy=none --basetemp=<私有> tests/bt/critic/item_4
83 passed in 29.12s
$ ... tests/bt/item_4/test_i4_pipeline.py
18 passed in 127.98s (0:02:07)
$ ... tests/bt/item_4/test_i4_battery_scenes.py -k "i4-5 or i4-6"
7 passed, 88 deselected in 101.98s (0:01:41)
```

**記録の欠落について(監査役(通過)1 回目の [止める] 1)**: 役の返り値は、リードの抜き出しの機械(返り値の text の欄を探す)が SubagentHandback の欄に入った返り値を拾えず「(取り出せず)」と書いていた(6 か所)。14:45 UTC に、リードの会話に残る 4 つ(場面係 14:05・作業者 14:16・作業者 14:25・置き換え 14:28)は逐語を写し直し、第 1 段の 2 つ(参照実装の役 12:38・作業者 13:33)は出力ファイルから取り出せたものを写した(取り出せなければその旨を書いた)。抜き出しの機械の欠陥はリードのもの。

### 監査役(通過)1 回目の出力(逐語、14:38 UTC。コンテナの再起動で 14:32 の検査は失われ、14:34 に起こし直した分)

検査の結果(下書きの `{COND1}` `{COND1_EVID}` `{COND4}` `{COND4_EVID}` `{SMOKE}` `{CRITIC_CARRY}` 6 穴は未記入の状態での検査。埋めた後の再検査が要る)。

1. [止める] docs/AUDITOR/VERDICTS/2026-09-26_backtest_env_finish.md:190,197,204,211 — 「場面係(第3段の続き)」「作業者(第2段の続き)」「作業者(i4-5-fills)」「置き換えの作業者(第3段=条件3)」の**4 つの役の返り値が全部「(取り出せず)」**で、逐語が一切残っていない。委任文 §5「監査役の出力・批評家の出力・各役の返り値は逐語で…写す」、CLAUDE.md O-4「監査役の出力をそのままここに出力すればいいだけ…後でまとめて出すから書き換えるんやろ」に反する。COND1(批評家の[止める]閉じ)・COND2(720場合一致)・COND3(置き換え・243 passed・107件・5/5捕捉等)の根拠は、逐語の代わりに**リードの要約(「リードの読み」「リードの読みと答え」)だけ**に依っている。O-3(機構・データの挙動の主張にはコマンドと出力を同じ返答に出す)も満たしていない。COND1_EVID・COND4_EVID を埋める際、この欠落自体を書かない限り根拠不明のまま通ることになる。

2. [止める] REPORT_finish_2026-09-26.md:22(i4-r2-06 の行「統合の場面5つは全部『正解と一致』(2回とも同じ digest)、test_i4_pipeline.py 17 passed」)— VERDICTS.md:297「i4-r3-02 = 作業者の14:25の直しで統合の場面5つが『正解と一致』になった(**閉じた。批評家の再検で確かめる**)」と対照すると、批評家の再検はまだ条件文で明記された未完了事項。かつ CRITIC.md §4 の実測表(38 passed 140.94s 等)は `test_i4_engine_vs_independent_bar_sim.py`+`test_i4_pipeline.py` のみで `test_i4_battery_scenes.py`(i4-5-fills含む)は含まれていない。批評家自身の指摘(CRITIC.md:265)は「途中(場面係)…場面係が返ったあとに残れば[止める]」であり、その後の批評家の再確認記録が無い。下書きはこれを留保なしの既成事実として書いている。P2/P6(なぜ・確認の分解を欠いたまま断定)。

3. [止める] REPORT_finish_2026-09-26.md §4(35〜42行、測っていない範囲・持ち越し)— i4-r3-01(証拠金二重観測の欠陥)は批評家により第3周で[止める]として作業者に戻し中(VERDICTS:297「作業者は…この形のままなので[止める]1件として戻す」)。この監査の起こし文が明かした「コンテナの再起動で作業者も失われ、直しの途中の差分が作業木にある」という事実——すなわち i4-r3-01 の修正が未完了・未検証のまま作業木に残っているという状態——が、下書きの§4のどの行にも書かれていない。委任文§4「2回目の批評で[止める]が残れば止めて報告する」の判定ができる状態に無いことも含め、{COND1}を埋める前提としてこの経緯の開示が要る。落ちれば「測っていない範囲・持ち越し」の記述義務(§5の記録規則)違反。

4. [直す] REPORT_finish_2026-09-26.md:14(条件3の根拠欄)「**全試験で2件落ちた**」という表現 — 同じ報告の§4:37「置き換えた版は11%で打ち切り(`2 failed, 2316 passed, 15 skipped, 1 error`)」と突き合わせると、「全試験」は(i)完走して2件だけ落ちた、という読みと(ii)打ち切られた部分実行で2件落ちた、という読みの両方に取れる。同じ語を2つの意味で使い回している(P2「一度出した用語の意味を変えて使い回す」O-7型)。

5. [直す] REPORT_finish_2026-09-26.md:40(`{CRITIC_CARRY}`)— 埋める内容の指定が下書きに無い。CRITIC.md §5「時間が来て読めなかった範囲」は5点(barmodel.py/engine.py本体・SPEC.md/bar_sim.py本体・場面集差分・item_4の一部試験・置き換えの差分)あるが、この5点全部が§4に反映される保証が本文のどこにも書かれていない。

6. [聞く] REPORT_finish_2026-09-26.md:31-33(§3 案A/案B)— 両案とも帰結は書かれており yes/no を迫る形ではない点は確認したが、両案が実装・検証済みの選択肢か、それとも設計上の提示に留まるか(工数・実行可能性)が書かれていない。オーナーが判断する材料として十分かは判断が要る(P9/A-13は枠組みの変更として正しく上申している点は良いが、判断材料の粒度は問う余地がある)。

[止める] 3 件。

備考: 期限(14:50 UTC)に間に合わせるため、KNOWN_ANSWERS.md との突き合わせ、CRITIC.md §5 で読んでいないと明記された `barmodel.py`/`engine.py`/`SPEC.md`/`bar_sim.py` 本体・置き換え差分・場面集差分の中身までは検査していない(批評家自身が同じ理由で読んでいないものを、この監査でも読み切れていない)。上記1〜3は、6穴を埋める作業そのものより先に解消しないと、埋めた値の根拠が崩れる級のものとして優先度を上げてある。

**リードの処置(14:41 UTC)**: 1 = 役の返り値の逐語を写し直した(上)。2 = 批評家の再検はコンテナの再起動で失われた。代わりにリードが `test_i4_battery_scenes.py -k "i4-5 or i4-6"` を回して 7 passed(i4-5-fills を含む)を実測し、報告に「批評家の再検ではなくリードの実測」と書く。3 = 報告 §4 に i4-r3-01 の経緯(作業者の直しの差分が作業木に残り、リードが批評家の試験 6 件 + critic item_4 83 件を実測して通ることを確かめた。2 回目の批評は行えていない)を書く。4 = 「全試験で 2 件落ちた」を「全試験の実行(11% で打ち切り)で 2 件落ちた」に直す。5 = 批評家の読めなかった範囲 5 点を §4 に書く。6 = 案 A・B の実行可能性(案 A = run_battery.py の一覧に 1 語を足す + 置き換えた版を写す(用意済み)/ 案 B = adapter の書き換え(未着手))を §3 に書く。
