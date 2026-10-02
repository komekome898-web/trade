# W2 記録の台本 第 2 版の仕様(計画 第 5 版 並走 2 の 1)

リードが委任の前に書く仕様。第 1 版は批評家に 2 回 [止める] を受けて止めた(`docs/AUDITOR/VERDICTS/2026-10-02_W2_recorders.md`)。原因は委任文の不備 2 つ(実績のある書き方を指定しなかった / 起動と停止の台本を別の範囲に切った)。この版はその 2 つを直してから渡す。

- オーナーの逐語: L-550「**3.受け入れる**」(後から取れない出所の記録を毎日 git で共有する量 月約 1GB を受け入れる)。L-039「取れる時に取れるだけ取る」。
- 第 1 版の台本と試験は `scratchpad/wf1/l2_stopped/` に退避してある(出所への問い合わせ・列の作りはそのまま使ってよい。書き方と後始末は下の §2 で置き換える)。

## 1. 範囲(起動・停止・再起動・共有・取得を 1 つの範囲にする)

| ファイル | すること |
|---|---|
| `scripts/record_hyperliquid.py`・`scripts/record_okx_traders.py`・`scripts/record_deribit_oi.py` | 第 1 版を元に、§2 の書き方に置き換える |
| `src/bot/research/gz_members.py` | §2-2 の「末尾のメンバが完結しているか」の関数を足す |
| `scripts/record_liquidations.py` | `_heal_if_needed` を §2-2 の関数に置き換える(同じ原因の誤判定を持つため) |
| `deploy/start_all.bat`・`stop_all.bat`・`restart_all.bat`・`share_logs.bat`・`fetch_all.bat` | 起動するものは必ず止めて確かめる。追加の行の注記(rem)は ASCII だけで書く |
| `docs/OPERATIONS.md` | 運用の節。Deribit は一回きりのプロセスであることなど、台本の実際の振る舞いどおりに書く |
| 試験 | §3 |

## 2. 書き方

### 2-1 追記の書き方
- `scripts/record_liquidations.py` の `Writer` と同じ型にする: 行はメモリに積み、`gzip.compress()` で完結した 1 メンバを作って 1 回の `open(path, "ab")` で追記する。`gzip.open(path, "at")` は使わない。
- バッファは、書き込みが成功してから空にする(書く前に空にしない)。書き込みの失敗は、その周を打ち切らずにログに出して次の回に書き直す。
- 同じ日のファイルに 2 つのプロセスが書かないよう、`record_liquidations.py` の鍵(`_acquire_lock`)と同じ型の鍵を持つ。

### 2-2 強制終了の後始末
- **ファイルをその場で切り詰めない。** 末尾のメンバが完結していなければ、ファイルを丸ごと `<名前>.truncN.<拡張子>` に改名し、新しいファイルに書き始める(`record_liquidations.py` の型)。
- 「末尾のメンバが完結しているか」は、圧縮済みのバイト列の中の 1f 8b 08 を探して割る方法(`split_raw_members`)では決めない。そのバイト列は圧縮済みのデータの中にも偶然現れ、数 MB のファイルでは無視できない確率で現れる(第 1 版の批評家の再現 `scratchpad/wf1/critic_L2/false_magic2.py`)。代わりに、`zlib.decompressobj` で先頭から順にメンバを読み(1 つのメンバが終わったら `unused_data` から次のメンバを読む)、最後まで読めて最後のメンバが終わっていれば完結、と判定する関数を `gz_members.py` に足す。順に読めない(途中で例外)ときは不完全とみなして改名する。
- `gz_members.py` の冒頭の説明にある「偶然の一致は現実の心配ではない」は、数 MB のファイルでは成り立たない。説明を直す(確率の計算を書く)。

### 2-3 共有
- `share_logs.bat` で共有するのは、**終わった UTC 日のファイルだけ**(当日の書きかけのファイルは共有しない)。同じ日のファイルを書きかけと完成の 2 回コミットすると、git の中の量が約 1.9 倍になるため(第 1 版の批評家の [聞く])。
- 既存の記録(清算・venues)の共有の仕方は変えない。

## 3. 試験(これが無いと終わらない)

1. 配線: start_all が起動する常駐は、stop_all が止め、restart_all が確かめる(既存の `test_every_launched_component_is_also_stopped_and_verified` が通る)。share_logs が 3 つの出所の終わった日のファイルを共有し、当日のファイルを共有しない。fetch_all が Deribit を呼ぶ。
2. 強制終了: 書いている途中で殺したファイルの後に再起動して追記したとき、(a) 改名された元のファイルから殺される前の行が読める (b) 新しいファイルが普通の gzip の読み手で全部読める。3 つの台本と `record_liquidations.py` の全部で確かめる。
3. 偶然の 1f 8b 08: 圧縮済みのバイト列の中に 1f 8b 08 を含む完結したファイルを、「完結」と判定し、改名しない(第 1 版の批評家の再現を試験にする)。
4. 第 1 版の批評家の [直す] のうち試験の不足: Hyperliquid の速さの制御で sweep が実際に待つこと、OKX の決済済み建玉の鍵を全部の history ファイルから戻すこと。
5. bat の rem 行が ASCII だけであること。
6. 直す前の版(第 1 版、`split_raw_members` を使った判定)で 2・3 が落ちることを示す。

## 4. 守ること・終わる条件

- 安全不変条件(CLAUDE.md §1)・封印に触れない。公開の読み取りの API だけを使う。
- git の commit/stash/checkout/reset/push を打たない(リードが批評家の後にコミットする)。
- 終わる条件: §1 の全ファイルが §2 のとおりで、§3 の試験が通り、既存の `tests/test_record_liquidations.py`・`tests/test_record_venues.py`・`tests/test_deploy.py` が通る。
- 批評家に 2 回目も [止める] を受けたら、直し続けずに止めて原因を出す(計画 §4-1)。
