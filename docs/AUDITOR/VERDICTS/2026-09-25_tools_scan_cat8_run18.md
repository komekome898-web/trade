# 検収: 道具サーベイ 区分 8 の 18 回目(2026-09-25、リード)

対象: `docs/DATA/SCAN_2026-09-23_tools_cat8.md` の `## 区分8 — 18 回目の実行(2026-09-25)`(35575 行目から)/ 生ログ `docs/DATA/probes/20260923_tools_8_run18.log`(11,608 行・3,033,270 バイト)。届いたままのコミット fc43462。起動文の印 `20260923_tools_survey_cat8_run18_prompt.md@4bc5c0d40b3f`(この回から、ほかの回の起動文を参照しない形)。

## 0. 費用と時間

調査班 678,762 トークン・3,260,749 ms(54.3 分)・道具 283 回。

## 1. 受け入れ検査(調査班の報告)

`check-elements --round 18` 0 件 / `check` 0 件 / `check_scan_report.py` 38 件(K1・K2・K13。前の回からのものと、§4.0 の表の書き直しに伴う同型の複写)。

## 2. リードが見た点と直し

- **理由の表の書き方**: 型の文の当てはめは、行の表とファイルの表では見られなかった(`なし` の 4 要素は全部 (乙) で、行ごとの判定は E1a 5 行・E2 2 行・E3a/E3b 0 行)。「同じ理由を 2 行以上に書きたくなったら決まりにする」は守られた。
- **ただし決まりが語ごとの決まりだった**: `### 決まりの一覧` の多くは `(?i).valid|valid.`・`(?i).range|range.`・`(?i).missing|missing.`・`(?i).test|test.` のように「検索した語の前か後ろに 1 字ある」だけの形で、`(?i)compar\w+`・`(?i)differ\w*` も語そのものを取る。行の前後の字をほとんど見ていない。道具の説明に「止められない」と書いた型(検索した語に、ありふれた前後の字を付けた決まり)に当たる。理由の文には「全707件の当たりを読み、うち25件を無作為抽出して個別に文脈を確認」とあり、1 行ずつ読んではいない。13・14 回目の「語ごとの決まりを先に立てて当てはめる」と同じ型。
- **リードが確かめた範囲**: AlgoNetwork の当たりのうち、ブログの記事(`blog_*.txt`)の行は、概念の一般の説明で、候補の機能の記述ではない(記事が「AlgoNetwork が〜する」と書いていれば別)。候補の機能の記述が出うるのは製品の頁(`faqs.txt`・`_root.txt`・`algonetwork.txt`・`trade-with-algorithms.txt`・`propsubstitute.txt`・`publish-pros.txt`・`white-label.txt`・`ai-landing.txt`・`about-us.txt`・`terms-of-use.txt`・`backtest.txt`・`trading-bot-marketplace.txt`、別の製品の `algobuild.txt`)なので、そこの当たりをリードが全部読んだ(E1a の手 33 行目 20 行、E2 の手 10409 行目 24 行、E3a・E3b の手 2054・2297 行目は 0 行 = 全部ブログ)。
  - **E1a は `なし` が誤り(`なし` 側に振れていた)**: `faqs.txt:73`「you can compare any two strategies like-for-like」、`trade-with-algorithms.txt:113`「Compare win rates, profit factors, and risk metrics openly.」、`_root.txt:97`「Buyers compare like with like」は、2 つ以上の戦略のバックテスト・フォワードテストの出力を並べて差を見せる機能。設計票 §3 の E1a の述語「**2 つ以上の実装(または実装と参照値)の出力を突き合わせて、差を出す機能**」に当たる。決まり `r_compare_prose`(`(?i)compar\w+`)は、これらの行を「比較する編集記事の一般叙述」として取っていた。**`印`・段 2**(並べて見せ、合否は人が決める)にした。
  - E2: 製品の頁の当たりは「publishing criteria (Sortino ratio,」(公開の基準)、「validates it with a complete backtest」(戦略の検証)、「Sort: Win rate ↓」(並べ替え)、「Quant Researcher · Singapore」(「gap」の部分一致)、「legally valid cases」など。データの欠け・重複・順序・範囲の違反を検出する機能ではない。**`なし` を受け取る。**
  - E3a・E3b: 当たりは全部ブログの記事(ルックアヘッド・生存者の偏りの解説)。**`なし` を受け取る。**
  - E6 `印`・段 1: 根拠「Every backtest and live trade is auditable. No cherry-picking.」は、結果を取捨選択せずに全部見せるという主張で、正しさを確かめる機能の文書の記述(段 1)。**受け取る**(監査で、E1a〜E5 と重ならないかを見る)。
- **Oryon**:
  - E6 `印`・段 3: README「Every feature and target in Oryon ships with contract tests...The test infrastructure is part of the public API. Contributions must pass the same contracts.」と、`#[macro_export]` の契約テストのマクロ。公開の API として、利用者が自分で書く実装(Oryon のトレイトを満たす型)に掛けられるので、L-516 の「候補が自分自身を試験する仕組み」には当たらない(報告の問い 1 への答え)。**受け取る。**
  - E1b の段: 調査班は段 4 とした(根拠 `run_features_pipeline_pandas(fp, df)` が pandas の DataFrame を受け付ける)。設計票 §4.1 の E1b の対象は「同じ種類の出力を出す計算に入れる入力(**データと戦略・計算のコード**)」で、外から持ち込めるのはデータだけ(計算は Oryon 自身の特徴量)。「対象の一部だけが外から持ち込めるものは段 3」により **段 3** にした。
- **状態**: 2 候補とも E1a〜E6 に `未判別` が無く、§4.0 の表の `未確認` の理由は、登録が要る・一次資料に数が無い・実装の作業はサーベイの外、など(「時間」ではない)。**`深掘り` を受け取る**(報告の問い 2・3 は監査で見る)。

## 3. 台帳

`import --round 18`: 変わった所 9。`set` で 8-037 E1a を `印`・段 2、8-041 段_E1b を 3。`check` 0 件。`recount`: 深掘り 26 / 残り 11(8-026・8-029・8-030〜8-035・8-038・8-039・8-040)。

## 4. 判定

**一部受け取り**(E1a を直したうえで、2 候補を `深掘り`)。中身の監査 95 回目を通す。

**語ごとの決まりについて**: 道具は足さない(L-102)。次の起動文に「決まりの正規表現は、検索した語の前後の字(その行の文脈)を入れる。検索した語に 1 字足しただけの決まり(`.X|X.`)や、語そのものを取る決まり(`X\w*`)は書かない。その語が出る行がすべて同じ意味なら、決まりにせず (甲) で、ファイルごとに読んで書く」と書く。守られたかは、リードが検収で決まりの一覧を読んで確かめる(この回と同じ手)。
