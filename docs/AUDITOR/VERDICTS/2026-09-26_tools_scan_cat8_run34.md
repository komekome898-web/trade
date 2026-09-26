# 検収: 道具サーベイ 区分 8 の 34 回目(2026-09-26、リード)

対象: `docs/DATA/SCAN_2026-09-23_tools_cat8.md` の `## 区分8 — 34 回目の実行(2026-09-26)`(45966 行目から)/ 生ログ `docs/DATA/probes/20260923_tools_8_run34.log`(43,550 バイト)。受け取ったままの形はコミット e52f717。

## 0. 費用と時間

調査班 360,953 トークン・1,299,233 ms(21.7 分)・道具 104 回。

## 1. 受け入れ検査(リードが打ち直した)

`check_scan_report.py`(34 本)`---- 合計 61 件` / `check-elements --round 34` 0 件 / `check "" run34.log` 0 件 / 過去の節から消えた行 0。見出しの行 17 本の全部に `[sandbox …]` がある(`grep '^--- ' run34.log | grep -c sandbox` → 17)。`find /tmp -maxdepth 1 -newermt '2026-09-26T20:31:00'` → `/tmp` 自身だけ、`find /root -xdev -newermt '2026-09-26T20:31:00' -not -path '/root/.claude/*' -type f` → 出力なし。

## 2. リードが見つけたこと(監査の前)

1. **E4 は `未判別` のまま、案 B の記録あり**。見積もり `files_with_hits=1661 total_lines=14613`(500 行超)。文書 347 頁の道と題、ソースの全 3,565 ディレクトリへの語の機械的な選び方は、どちらも 0 件(リードが打ち直した: `doc_titles.txt` 347 行に E4 の語の組 → 0、`find src/spark -type d` に同じ語 → 0)。加えて `chronolog|time.order|…` の全文検索で 20 ファイル、33 回目の Kafka 連携の頁の読み直し。
2. **Auto CDC の逐語**(`docs/declarative-pipelines-programming-guide.md`「It is what lets Auto CDC apply events by their intended order rather than the order they happen to land in.」、`Changelog.java`「distinct commits in strictly increasing event-time order across batches」)は、これまでで最も「時刻順」に近い。調査班は、(a)「市場データ」を言う逐語が無い (b) 適用先はターゲットの表の維持で戦略・執行の再実行ではない、で `未判別` とし、問い 1 にした。
3. scratchpad の外への書き込み・生ログに無い手は無かった(1 のとおり)。

## 3. 中身の監査(132 回目、owner-auditor)の逐語

(監査の後に書く)

## 4. 処置(リード、監査 132 回目)

(監査の後に書く)

### リードの読みの案(監査に掛ける)

- E4 `未判別`(案 B の記録あり)を受け取る。Auto CDC は、述語の「記録した市場データを」「戦略・執行・計算を再実行する」のうち「計算」(`netChanges`)はありうるが、「市場データ」を言う逐語が無い。E2 と同じく、汎用の道具の当て方の問い(区分の完了の報告でオーナーに見せる)に入れる。**安全側に振るために未判別にするのではなく、述語の対象の語が無いので決めない**。
- 8-035 は、未判別の要素(E3a・E4・E6)の全部に案 B の記録があるので、**「残り」に数えない**(§4.0 の過半の条件は監査で数え直してほしい)。**残り 4**(OpenClaw・MetaTrader・NumPy・SciPy)。35 回目 = NumPy。
