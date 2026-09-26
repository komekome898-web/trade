# 監査: 道具サーベイ 区分 8 の 33 回目の起動文(2026-09-26)

対象: `docs/DATA/delegations/20260923_tools_survey_cat8_run33_prompt.md`(8-035 Apache Spark の 1 行。32 回目の起動文を土台に、§1 を 31 回目の新しい候補の形に戻して作った)。

## 監査 129 回目(owner-auditor、対象 `20260923_tools_survey_cat8_run33_prompt.md@f2059482c3c5`)の逐語

> 監査対象: `docs/DATA/delegations/20260923_tools_survey_cat8_run33_prompt.md`(指紋 `f2059482c3c5`)
>
> 事前に突き合わせた資料: `docs/DATA/delegations/20260923_tools_survey_cat8_run31_prompt.md`・`..._run32_prompt.md`、`docs/AUDITOR/VERDICTS/2026-09-26_tools_scan_cat8_run31.md`・`..._run32.md`、`docs/DATA/tools_catalog_cat8.tsv`(8-035 行)、`docs/DATA/SCAN_2026-09-23_tools_cat8.md`(該当節・行番号)、`docs/DATA/delegations/20260922_tools_survey_prompt.md`(§5・§6)、`docs/OWNER_LOG.md`(L-506〜L-519 の該当行のみ)。
>
> まず、良好だった点(誤検出を避けるため明記): 委任文が引く行番号(3672/3850 行の Apache Spark 記事内一覧、44025/44701 行の節見出し)、台帳 8-035 行の値(全 16 要素 `未判別`・状態 `未着手`・最後の記載 32 回目/44774 行)は、いずれも現物と一致することを実測で確認した。オーナー逐語(L-506「期限を指示した覚えがありません…」、L-507「案A」、L-508/L-509、L-516「数えません」、L-519「案B」)の引用も一字一句 OWNER_LOG.md と一致し、「200 MB」の大きさの線・`find /root -newermt` の範囲拡大はいずれも「リードの仮定/読み」であり「オーナーの決定ではない」と明記されている(誤帰属なし)。
>
> 指摘:
>
> 1. [聞く] `docs/DATA/delegations/20260923_tools_survey_cat8_run33_prompt.md:66` — 最後の手が `find /root -xdev -newermt '<開始の時刻>' -not -path '/root/.claude/*' -type f` になっているが、これは 32 回目検収(`docs/AUDITOR/VERDICTS/2026-09-26_tools_scan_cat8_run32.md` 処置 4)が定めた修正文言「`find /root/.cache/pip -newermt '<開始の時刻>' -type f`」から対象を `/root` 全体に広げたもの。広げた理由(mvn/gradle の `.m2`/`.gradle` を含めるためと推測はできる)が本文にも検収記録にも書かれておらず、決定の記録と実際の起動文が食い違ったまま次に引き継がれている。意図的な改善か確認してほしい。
>
> 2. [直す] `docs/DATA/delegations/20260923_tools_survey_cat8_run33_prompt.md:66` — `TMPDIR` は直前の「最初の手」で作った具体パス(`.../venvs/8-035/tmp`)を指すのに対し、`PIP_CACHE_DIR`・`mvn -Dmaven.repo.local`・`gradle GRADLE_USER_HOME` はいずれも「`<scratchpad の下>`」という抽象表現のままで、具体的な絶対パス(例: `.../venvs/8-035/pip-cache`・`.../venvs/8-035/m2`)が与えられていない。32 回目はまさに `PIP_CACHE_DIR` を一部の手(`pip list`・`pip check`)に付け忘れて `/root/.cache/pip` に書き込む違反が起きたばかり(`docs/AUDITOR/VERDICTS/2026-09-26_tools_scan_cat8_run32.md` §2-2)。再発防止の記述が具体パスまで踏み込んでおらず、同型の付け忘れを防ぐ力が弱いのではないか。
>
> 3. [聞く] `docs/DATA/delegations/20260923_tools_survey_cat8_run33_prompt.md:68` — 「数百 MB 以上なら取らない」とし、その場合 §6-1 の中身検査と最小実行を放棄して `未確認` にする設計。これに対し委任文 `docs/DATA/delegations/20260922_tools_survey_prompt.md` §5-1 は「到達は 1 回の HTTP コードで決めない…ありとあらゆる手段使って全部無理で始めて諦めるような委任文にしないと意味ない」(L-379)と明記している。§1 の N(ソース取得)には「超えるなら `--filter=blob:limit=1m` で大きいファイルを除いて取る」という代替手段があるのに、§2.5 の配布物取得には「取らない」以外の代替(例: Hadoop 抜きビルド・より小さい公式配布物の有無の確認)が示されていない。200 MB は「リードの仮定」と明記されてはいるが、JVM 系で配布物が大きくなりがちな Apache Spark に限って §4.0 の実行依存項目(導入可否・install 所要秒・最小実行・実行所要秒 等)が構造的に `未確認` になりやすい設計になっていないか、これが安全側(棄却側)に振れる形(A-18)になっていないか、確認してほしい。
>
> 4. [聞く] `docs/DATA/delegations/20260923_tools_survey_cat8_run33_prompt.md:20` — 32 回目検収(`docs/AUDITOR/VERDICTS/2026-09-26_tools_scan_cat8_run32.md`「残り 5(OpenClaw・MetaTrader・Spark・NumPy・SciPy)」)のうち、台帳で先に並ぶ 8-026 OpenClaw・8-029 MetaTrader ではなく 8-035 Apache Spark を次に選んだ理由が本文に書かれていない。族の順序を変えること自体を咎める規則は無いが、選定理由の記載が無いため、後から見たときに「なぜこの順か」を追跡できない。
>
> 5. [直す] `docs/DATA/delegations/20260923_tools_survey_cat8_run33_prompt.md:70` — Apache Spark の tar.gz について「公式の署名・ハッシュ(`.sha512` など)と照らし」と指示しているが、署名/ハッシュが一致しなかった場合にどう扱うか(即座に「危険で導入停止」か、他の根拠と合わせて判断するか)が明記されていない。§6-1 の他の所見(バイナリ同梱の有無など)は「『バイナリがある』だけで止めも通しもしない、これはリードの読み」という判断基準が明示されているのに、署名不一致だけ基準が書かれていない。
>
> 検査した範囲で「止める」に該当する欠陥(族の欠測・射程と判定基準の矛盾・オーナー逐語の捏造)は見つからなかった。31・32 回目の学びの引き写し(TMPDIR 化・PIP_CACHE_DIR 徹底・wheel 限定取得・§6-1 の依存全数化・JVM 常駐プロセス確認・mvn/gradle の scratchpad 隔離)は概ね反映されており、行番号・台帳値の引用も現物と一致している。

## 処置(リード、監査 129 回目)

1. **答える・直した**。意図して広げた(リードの決定)。Spark は JVM の道具で、`/root/.m2`・`/root/.gradle`・`/root/.ivy2`・`/root/.cache` のどれにも書きうるので、`/root` 全体を見る。`/root/.claude` はこの会話の道具の記録なので外す。理由を起動文に書いた。
2. **直した**。`TMPDIR`・`PIP_CACHE_DIR`・`-Dmaven.repo.local`・`GRADLE_USER_HOME`・Spark の一時の置き場所を、全部 scratchpad の下の絶対の道で書き、「この 2 つの道をそのまま写す」と書いた。
3. **答える・直した**。そのとおりで、大きさの線だけでは棄却側に振れる。委任文 §5-1 の L-379 の逐語を引き、公式の配布物の全部(Hadoop を含まない版・言語ごとの版・接続の客だけの版など)を名前と大きさで一覧にさせ、200 MB より小さいものが 1 つでもあればそれで §6-1 と最小実行をする、全部が 200 MB 以上のときだけ `未確認`、と書いた。選んだ配布物が候補の機能の全部を含まないときは、含まない部分を書かせる。200 MB はリードの読みのまま(委任文 §6-6「数百 MB 以上」の最小の読み)。区分の完了の報告で、この線が `未確認` を生んだ行があればオーナーに見せる。
4. **答える・直した**。残り 5 のうち `未着手` の 3 行(Spark・NumPy・SciPy。§4.0 の表がまだ無い)を先に、`浅い` の 2 行(OpenClaw・MetaTrader。§4.0 の表が既にある)をあとにする(リードの決定)。`未着手` の中では台帳の番号の順で Spark が最初。起動文に書いた。
5. **直した**。一致しなければその配布物は導入しない、取り直して 2 回とも一致しなければ `危険で導入停止` とし両方のハッシュを書く(リードの読み)、と書いた。

直したあとの起動文の印: `20260923_tools_survey_cat8_run33_prompt.md@9ebaf51f4559`。止める指摘は無いので、33 回目を起動する。
