# 検収: 道具サーベイ 区分 8 の 42 回目(2026-09-27)

対象: `docs/DATA/SCAN_2026-09-23_tools_cat8.md` の `## 区分8 — 42 回目の実行(2026-09-27)` の節(50772 行目から 51333 行目まで)と生ログ `docs/DATA/probes/20260923_tools_8_run42.log`(55 手・25723 行)。起動文 `20260923_tools_survey_cat8_run42_prompt.md@9f201d8681cf`。範囲は 8-026 OpenClaw の E2・E4・E6(読むだけ)。

## 1. リードが確かめたこと

- **この回は 2 つの調査班で済ませた**。1 つ目の調査班は、コンテナの再起動で止まった。生ログの 1〜54 手目と、節の `### 予算` までを書いていた。2 つ目の調査班に続きを渡した。渡したのは「済んだ手を打ち直さない、選んだ頁を切れていない手で読んだか確かめる、最後の確認の手を打ち直す、§7 の道具を打つ」。2 つ目の調査班は、55 手目(最後の確認)と §7 の道具を打った。
- **scratchpad の外への書き込み**: 1 つ目の調査班は、生ログに無い素の殻の手で `/tmp` の直下に 13 個のファイルを書いた。10 個は確認のための出力の写しで、自分で申告した(知見 19・問い 1)。残りの 3 個(`gen_run42_tables.py`・`run42_candlist.txt`・`run42_elemtable.txt`)は報告の表の下書きで、2 つ目の調査班が最後の確認の手で見つけて申告した(知見 22・問い 3)。13 個とも、リードが `.../scratchpad/cat8/run42_tmp/` に移した。生ログに無い殻の手と scratchpad の外への書き込みは、26・31・32・33・36・39・40 回目に続く再発。
- リードの打ち直し(調査班が終わったあと):
  - `check_scan_report.py`(生ログ 42 本)「---- 合計 71 件」。道具が貼った出力は 72 件で、72 は貼る前の K12 の 1 件。
  - `check-elements --round 42`「---- 合計 0 件」。
  - `check "" <生ログ>`「---- 合計 0 件」。
  - `git diff` の消えた行は 4 行。2 つ目の調査班が直したこの回の知見 8・11 と E2・E4 の行で、1〜41 回目の行は消えていない。
  - `find /tmp -maxdepth 1 -newermt '2026-09-27T03:30:00Z' -type f` → 7 個(`claude-command`・`env-manager.log`・`codesign-mcp-config.json`・`environment-manager.out`・`claude-code.log`・`claude-append-system-prompt.txt`・`environment-manager-674225920.diag.log`)。どれもコンテナの再起動のときの実行環境のファイルで、調査班の手ではない。
  - `find /root -xdev -newermt ... -not -path '/root/.claude/*' -type f` → 実行環境の設定・記録のファイル 10 個(`.cache/claude-cli-nodejs/.../mcp-logs-*` 5 個・`.gitconfig`・`.claude.json`・`.ccr/*` 3 個)。これも再起動のときのもの。
- 読みの案(監査のあとに決める): E2・E4・E6 は `未判別` で、案 B の記録あり。見積もりは E2 233,404 行・E4 213,009 行・E6 496,126 行で、どれも 500 の線を大きく超える。

## 2. 監査 148 回目(owner-auditor)の逐語

§3_PLACE

## 3. 処置(リード、監査 148 回目)

§4_PLACE
