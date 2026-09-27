# 区分 8: OpenClaw の文書 17 頁の読み取りの起動文(2026-09-27)

あなたは読むだけの調査班です。調べる対象は、道具 OpenClaw(チャット・エージェントの運用基盤)の文書の 17 頁です。この起動文に書いたもの(述語の 3 行と 17 頁)のほかは読まないでください。とくに `docs/OWNER_STATUS.md`・`docs/OWNER_LOG.md`・`docs/AUDITOR/` の下・`docs/DATA/SCAN_2026-09-23_tools_cat8.md`・`docs/DATA/tools_catalog_cat8.tsv`・`docs/DATA/probes/` の下・`docs/DATA/delegations/` の下のほかの起動文は開かない。

## 読むもの

1. 述語: `docs/DATA/surveys/CAT8_DESIGN.md` の 54 行(E2)・57 行(E4)・59 行(E6)。それぞれ全文を読み、この字のとおりに当てる。
2. 頁: `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/8-026/openclaw/` の下の次の 17 頁(一覧のファイルは `.../scratchpad/cat8/p17/pages.txt`)。**17 頁とも、全部の行を読む**(Read で offset と limit を使い、切れずに最後の行まで読む)。
   - `docs/ci/release-validation.md`
   - `docs/ci/release-validation/full-release-validation.md`
   - `docs/ci/release-validation/install-smoke-and-docker-e2e.md`
   - `docs/ci/release-validation/live-and-e2e-shards.md`
   - `docs/ci/release-validation/package-acceptance.md`
   - `docs/ci/release-validation/plugin-prerelease.md`
   - `docs/gateway/troubleshooting/config-validation-and-probes.md`
   - `docs/reference/database-schemas/layout.md`
   - `docs/reference/full-release-validation.md`
   - `docs/reference/full-release-validation/continuation.md`
   - `docs/reference/full-release-validation/dispatch.md`
   - `docs/reference/full-release-validation/evidence.md`
   - `docs/reference/full-release-validation/extended-stable.md`
   - `docs/reference/full-release-validation/profiles.md`
   - `docs/reference/full-release-validation/release-checks.md`
   - `docs/reference/full-release-validation/stages.md`
   - `docs/reference/session-management-compaction/schema.md`

## やること

- 頁ごとに、次の 3 つを書く。
  - 行数(`wc -l` の値)。
  - 最後まで読んだか。
  - E2・E4・E6 の述語のどれかに**当たりうる機能**を言う文。文ごとに、原文の逐語と `道:行` を書く。
- **当たりうる文は広く拾う。**述語の一部だけに当たる文も拾い、どの語に当たり、どの語に当たらないかを書く。その機能が OpenClaw の開発者が OpenClaw 自身を試験するものか、利用者が自分のデータや計算に掛けるものかも書く(判断に迷ったら迷ったと書く)。
- 当たりうる文が無い頁は「無い」と書き、その頁が何の頁かを 1 文で書く。
- 数は、打ったコマンドの出力から数えて書く。

## 決まり

- 候補のコードを動かさない。
- 取ってこない。
- 書いてよいのは `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/p17/` の下だけ。
- commit も push もしない。
- 返答は日本語で、頁ごとの表で返す。
- 返答の最後に、この起動文のほかに読んだファイルを全部並べる(述語の 3 行と 17 頁のほかに無ければ「無い」と書く)。会話の始めに状態板や作業の経緯を含む文が渡されていたら、そのことも書く。
