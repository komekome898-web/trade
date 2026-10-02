# 批評家の記録: L2 後から取れない出所の記録の台本(W2)

Workflow wf_3706782f-c5b のレーンの批評家の出力(構造化された返り値の全文)。応答は末尾。

## 1 回目の批評家

止める 1・直す 3

**読み(逐語)**: まだ PC に入れてはいけない。理由は 2 つ。(1)【事実】stop_all.bat と restart_all.bat が新しい 2 つの常駐を止めも確かめもしない。既存の試験 test_every_launched_component_is_also_stopped_and_verified が落ち、夜間の再起動のあとも古いコードが動き続ける。(2)【事実】gzip を 'at' で追記する書き方は、強制終了が書き込み中に当たると、その日のそれ以後の行が読めなくなる。直す時に止める側を足すと毎晩強制終了されるようになるので、record_liquidations の Writer の型(完結した 1 メンバを 'ab' で追記し、起動時に末尾を検める)に揃えてからにする。加えて【推定】start_all・share_logs の日本語の rem が cp932 で読まれると改行を食い、HL・OKX の起動行が実行されない恐れがある(rem を ASCII にすれば消える)。この 3 点と配線の試験を足せば、Deribit(fetch_all の 1 行)を含めて入れてよいと読む。git に積む量(約 1 GB/月【推定】)をどうするかは、入れる前にリードの判断が要る。安全不変条件と封印への抵触は見つからなかった。

- **[止める]** 【事実】start_all.bat に足した 2 つの常駐(record_hyperliquid.py・record_okx_traders.py)が stop_all.bat と restart_all.bat の [4/5] 確認に入っておらず、既存の試験が落ちる。restart_all は『再起動した』と表示しながら、この 2 つは古いコードのまま動き続ける。start_all の重複起動の防止がそれを見て起動を飛ばし続けるので、自然には直らない(2026-09-09 の記録器の事故と同じ型)。docs/OPERATIONS.md 自身が『stop_all.bat の停止の一覧にはまだ 2 つの常駐が入っていない(担当外)』と認めている。担当を広げる判断はリードに要る。
  - 場所: deploy/start_all.bat:35,37 / deploy/stop_all.bat:12 / deploy/restart_all.bat [4/5] / docs/OPERATIONS.md 追加節の末尾
  - 筋書き・根拠: 実行: PYTHONPATH=src python -m pytest tests/test_record_hyperliquid.py tests/test_record_okx_traders.py tests/test_record_deribit_oi.py tests/test_record_liquidations.py tests/test_record_venues.py tests/test_deploy.py tests/test_record_liquidations_writer.py -p no:cacheprovider --basetemp=.../critic_L2/tmp → 『FAILED tests/test_record_liquidations.py::test_every_launched_component_is_also_stopped_and_verified ... AssertionError: stop_all が record_hyperliquid.py を止めない』『1 failed, 86 passed』。直し方: stop_all.bat と restart_all.bat の [4/5] の両方の照合式に *record_hyperliquid.py* と *record_okx_traders.py* を足す(この試験が両方を要求している)。

- **[直す]** 【事実】gzip の書き方が、このリポジトリで既に事故を起こした型(L-121、オーナー PC で 10 ファイル)のまま。BufferedDailyGz.flush と append_gz_rows が gzip.open(path,'at') で 1 メンバを書くので、書いている途中で強制終了(stop_all の Stop-Process -Force。上の『止める』を直すと毎晩起きる)されると終わりの無いメンバが残る。その後に追記した行はすべて読めなくなり、壊れたメンバの断片が 1 行として読まれる。OKX は起動時の重複防止の鍵(seen_hist)をこのファイルから戻すので、二重書きも起きる。さらに flush は書く前にバッファを空にしている(HL 147 行・OKX 168 行)ため、書き込み中の例外 1 回で全ファイル分の未書き出しの行が失われる。また _maybe_flush が try の外にある(HL sweep 365 行、OKX record_trader 400 行)ため、書き込みの失敗 1 回で 1 周(HL は約 157 分)/1 回分が打ち切られる。直し方の手本は既にある: record_liquidations.py の Writer(gzip.compress() で完結した 1 メンバを作り、open(path,'ab') で 1 回で追記し、起動時に _heal_if_needed で末尾を検める)。
  - 場所: scripts/record_hyperliquid.py:146-160,365 / scripts/record_okx_traders.py:167-181,400 / scripts/record_deribit_oi.py:83-95
  - 筋書き・根拠: 再現(scratch/critic_L2/trunc_demo.py): history に 1 行書く → 途中で切れたメンバ(gzip.compress(...)[:40])を足す → BufferedDailyGz で 2 行追記 → 出力『rows readable after restart-append: ['1', 'x']』(2・3 の行は読めず、ゴミの 'x' が行になる)『gzip.decompress: BadGzipFile Incorrect length of data produced』『seen_hist restored: ['1', 'x']』。record_venues.py も同じ 'at' の書き方である(この点は既存の問題で、新しい台本がそれに倣ってよい理由にはならない)。

- **[直す]** 【推定】(cmd.exe はここに無いので実行していない)start_all.bat・share_logs.bat に足した日本語の rem 行は UTF-8 で書かれている。cp932 の DBCS 規則で読むと、行の最後のバイトが先行バイトになって改行を食う行がある。食われた行の次は、start_all.bat では Hyperliquid の起動行(35 行)と OKX の起動行(37 行)、share_logs.bat では mkdir paper_logs\hyperliquid(65 行)。これらが黙って実行されない恐れがある。既存の日本語の行(start_all 27 行)は同じ検めで ok と出るので、今動いている事実はこの恐れの反証にならない。直し方は安い: fetch_all.bat の追加分と同じく rem を ASCII で書く。
  - 場所: deploy/start_all.bat:32,33,34,36 / deploy/share_logs.bat:64
  - 筋書き・根拠: 検め(python: 各行の UTF-8 バイトを cp932 の先行バイト 0x81-0x9F・0xE0-0xFC で 2 バイトずつ読み進め、行末の先行バイトが CR/LF を消費するかを見た)の出力: 『deploy/start_all.bat 32 EATS_EOL』『33 EATS_EOL』『34 EATS_EOL』『36 EATS_EOL』『deploy/share_logs.bat 64 EATS_EOL』。既存の行は『start_all.bat 27 ok』『share_logs.bat 28 ok』。HEAD の deploy/*.bat 全体では check_liq_recorder.bat 47 行(endlocal)だけが該当。

- **[直す]** 【事実】試験が仕様の主張を確かめ切っていない。(a) 3 本の試験は新しいファイルなので変更前は import の失敗で落ちる(自明)。一方で、配線の試験が無い: start_all が起動する・stop_all/restart_all が止めて確かめる・share_logs が共有する・fetch_all が呼ぶ、のどれも試験で固めていない。venues には test_deploy_bats_carry_the_venue_recorder がある。これを書いていれば上の『止める』はこのレーンの中で見つかった。(b) 途中で切れた末尾の試験は Deribit だけで、それも『鍵を戻せる』ことしか見ておらず、『切れた後の追記が読める』ことを見ていない。HL・OKX には無い。(c) HL の『殺された後の再起動』の筋(周の途中で止まった時の扱い)の試験が無い。
  - 場所: tests/test_record_hyperliquid.py / tests/test_record_okx_traders.py / tests/test_record_deribit_oi.py:133-142
  - 筋書き・根拠: 『試験は全部通る(86 passed)のに、既存の試験 1 件が落ちる』『trunc_demo で追記分が読めない』という 2 つの事実が、新しい試験の網の外にある。

- **[聞く]** 【事実】+【推定】share_logs.bat は paper_logs を git add・commit・push する。新しい 3 つの出所の量は、レーン自身の【推定】で合計約 30〜35 MB/日(HL 15〜25・OKX 10・Deribit 5.6)、月に約 1 GB が git の履歴に積まれる。既に .git は 3.8 GB あり、これまで共有した venues は合計 159 MB。L-039 では『246 GB を git に載せると壊れる』としてアーカイブを git の対象外にした。全部を共有するか、一覧・要約・一部だけにするかは、リード(必要ならオーナー)が決めること。
  - 場所: deploy/share_logs.bat:63-70 / docs/OPERATIONS.md 量の見込み
  - 筋書き・根拠: 実行: du -sh .git → 3.8G、git count-objects -vH → size-pack: 3.15 GiB、du -sh paper_logs/venues → 159M、paper_logs/tape → 231M。

- **[注記]** 【事実】HL の 1 周(約 157 分)が途中で殺されると、accounts/positions の行は残るが sweeps の行(n_ok など)は残らない。docstring の『答えたのに行の無い口座はその時に建玉が無かった』は、その周には当てはめられない。読み手は sweeps の行の無い sweep_id を『不明』として扱う必要がある(周の始めにも 1 行書く、などで解ける)。また再起動するたびにファイルの先頭の口座から巡回し直す。
  - 場所: scripts/record_hyperliquid.py:43-45,366-371
  - 筋書き・根拠: 夜間の再起動が周の途中に当たる → その sweep_id の positions はあるが sweeps_ に行が無い。

- **[注記]** 【推定】使い方の欄に書かれた一回きりの実行(HL --max-addresses、OKX --max-pages の取り込み)を常駐と同時に打つと、2 つのプロセスが同じ日の gz に追記する。record_liquidations が持つ鍵ファイルのような、二重に書くことの防止が無い。逆に一回きりの実行が動いている間に start_all の見張りが回ると、照合 *record_okx_traders.py* に当たるので常駐の起動が飛ばされる。
  - 場所: scripts/record_hyperliquid.py:52 / scripts/record_okx_traders.py:423-425 / deploy/start_all.bat:48
  - 筋書き・根拠: オーナーが手順どおり --max-pages 500 で取り込みを打つ → 常駐と同じ history_YYYYMMDD.csv.gz に同時に追記する。

- **[注記]** 【事実】KeyboardInterrupt を受けると flush せずに SystemExit(0) で終わる(HL・OKX。最大 60 秒分の行が消える)。【事実】OKX の _restore は全期間の history_*.csv.gz を毎回の起動で読むので、起動の時間と記憶の量が際限なく増える。【推定】share_logs の copy が追記中のファイルを開いている間、Python の追記が PermissionError になりうる(record_venues と同じ条件。上の flush の直しで影響は 1 回分に収まる)。
  - 場所: scripts/record_hyperliquid.py:410-414 / scripts/record_okx_traders.py:221-226,447-451
  - 筋書き・根拠: Ctrl+C → バッファの行を書かずに終わる。

- **[注記]** 【事実】安全不変条件(CLAUDE.md §1)と封印に抵触する箇所は見つからなかった。3 本とも公開の読み取りだけを使う(HL は /info の clearinghouseState と stats-data の順位表、OKX は copytrading/public-* と rubik、Deribit は public/get_book_summary_by_currency)。鍵・発注・秘密情報の扱いは無い。封印の台帳(backtest_data/phase2_sealed/*/SEALED.json)にこの 3 つの出所は載っていない。【事実】OKX の伏せられた建玉(instId が空)にも subPosId が入っているので、重複防止の鍵 (sweep_id, sub_pos_id) は潰れない。【事実】新しい出所は retention_snapshot.py の出所の一覧に入っていない(壊してはいないが、保全の対象外になっている)。
  - 場所: scripts/record_*.py 全体 / backtest_data/phase2_sealed / scripts/retention_snapshot.py:167
  - 筋書き・根拠: 実行: grep -l 'hyperliquid\|okx_traders\|deribit_options' backtest_data/phase2_sealed/*/SEALED.json → 該当なし(exit 1)。OKX の公開の口を 10 人分叩いた結果: 『total 134 blank instId 21 blank subPosId 0』(D442CF34E4AEEAF1 は code 60004)。

## 2 回目の批評家(直しの後)

止める 2・直す 5

**読み(逐語)**: §0.1 の表: 「変更の読み・壊れる筋書き・試験・PC で動くか・封印と安全不変条件を見る(ファイルは変えない)」=「批評家です。ファイルを一切変更しないこと」「叩く点: 壊れる筋書き…」/「Hyperliquid・OKX・Deribit の記録の台本と deploy の 3 つの bat・OPERATIONS.md だけを対象にする」=「このレーンのファイルだけ」/「指摘ごとに 止める・直す・聞く・注記 を付ける」=「指摘ごとに level を…」。右が空の行は無い。

読み: このままでは PC に入れない。止める 2 件。(1) heal_tail が正常なメンバを偶然のバイト列 1f8b08 で『切れた』と誤判定し、その場で切り詰めて日のファイルを読めなくする。本環境で 2 通り再現した(Deribit の book、Hyperliquid の順位表+同じ UTC 日の再起動)【事実】。頻度は Deribit でおよそ 6 日に 1 回、順位表で同じ日に再起動した日の約 22%【推定、一様乱数の仮定】。雛形の record_liquidations.py は改名するだけで中身を壊さないので、それより後退している。(2) start_all.bat が 2 つの常駐を起動するのに stop_all/restart_all が止めず、既存の試験が 1 件落ちる【事実】。(2) だけ直すと毎晩同じ UTC 日に再起動するようになり、(1) の順位表の露出が毎日になるので、2 つは同じコミットで入れる。直す 5 件: 速さの制御の試験が無い(全速にした写しでも 37 件通る)、OKX の全ファイル復元の試験が弱い、OPERATIONS.md の Deribit の書き込み失敗の記述が違う、Deribit の復元が役に立たないのに 1 回約 440MB・2 秒かかる、share_logs で今日の途中のファイルを二重にコミットする(聞くの件に付けた)。聞く 1 件: 共有の量(git の中で月 1.7〜2.3GB 増える【推定】、100MB を超えるファイルが 1 つでもあると共有全体が止まる)。封印(新しい出所はどの封印の単位にも入っていない)と §1 の安全不変条件(読み取りだけ、鍵なし、発注なし)は守られている【事実】。新しい試験 37 件は全部通る。仕様の 3 つ(Hyperliquid の大口・OKX の上位の人・Deribit の行使価格ごとの建玉)は情報の地図 §5-1B の区分 C の升を全部覆っている。上の 2 件の直しと、その 2 件を落とす試験(偶然の魔法の数を含むメンバを置いても切り詰めない/start_all と stop_all の照合)が入れば、PC に入れてよいと読む。scratch の再現の台本: /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/wf1/critic_L2/{false_magic2.py,lb_magic2.py,restore_only.py,sim_deribit.py}。遅い版の false_magic.py(背景の bjpzuwo12)は false_magic2.py で同じことを示したので結果を待っていない。作業ツリーのファイルは変えていない(変異の確かめは scratch の写しで行い、cmp で同一を確かめた)。

- **[止める]** heal_tail(3 本とも同じ写し)が、正常に書き終えた gzip メンバを『強制終了で切れたメンバ』と誤判定して途中で切り詰め、日のファイルを普通の gzip の読み手で読めない状態にする。原因は src/bot/research/gz_members.split_raw_members が圧縮済みのバイト列の中の偶然の 1f 8b 08 でもメンバを割ること。雛形とうたう record_liquidations.py の _heal_if_needed はファイルを丸ごと改名するだけ(中身は無傷)だが、新しい 3 本は open(path,'r+b').truncate(keep) でその場で切り詰めるので、同じ誤判定でも被害が大きい。OPERATIONS.md の『強制終了の後の最初の書き込みからは .csv.gz が普通の gzip の読み手でまた読める』が成り立たない
  - 場所: scripts/record_deribit_oi.py:121-144(heal_tail)・163-174(read_gz_rows)/scripts/record_hyperliquid.py:163-186・189-216・369-383(_restore)/scripts/record_okx_traders.py:183-206・209-236・344-347/docs/OPERATIONS.md 667-670 行
  - 筋書き・根拠: 【事実】再現 1(/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/wf1/critic_L2/false_magic2.py): 中に 1f8b08 を含む 33KB の完結したメンバ(=前の回の 1 回分)を book_20261002.csv.gz に置く→普通の gzip で 302 行読める→次の回(新しいプロセス)の最初の追記で『[record_deribit_oi] book_20261002.csv.gz: last 21358 bytes were not a whole gzip member (killed mid-write) -> moved to book_20261002.cut1.bin』→その後の普通の gzip の読み『error Error -3 while decompressing data: invalid distance too far back』、台本自身の読み取りも 300 行を失う。再現 2(同ディレクトリ lb_magic2.py): 中に 1f8b08 を含む順位表の日のファイル→同じ UTC 日の再起動で _restore が『restored addresses 0 etags set()』(先頭メンバが切れ扱いで全行を捨てる)→順位表を取り直し→追記の前の heal_tail が『last 4093 bytes ... moved to leaderboard_20261002.cut1.bin』→普通の gzip は『EOFError Compressed file ended before the end-of-stream marker was reached』、台本自身の読み取りは 0 行。頻度は【推定】(圧縮後のバイトを一様乱数とみなし 3 バイトの一致を 1/2^24 とした仮定): Deribit は 1 回のメンバ約 28KB(本環境で実物の応答 96 回を模擬して日のファイル 5.44MB/192 メンバ)×1 日 96 回の検査で約 0.16 回/日=およそ 6 日に 1 回。Hyperliquid の順位表は 1 メンバ 4.25MB(台本の docstring の値)なので、そのメンバが一致を含む確率は約 22%/日で、同じ UTC 日に再起動したとき(夜間再起動 04:02 JST=19:02 UTC は同じ UTC 日)に壊れる。OKX は全 history ファイルの復元で、一致を含むメンバの sub_pos_id が鍵から落ち、『一度だけ書く』が崩れうる。直し方の案: メンバの境界は zlib の unused_data で先頭から順に解いて決め、魔法の数での分割は順の解読が失敗した位置から先だけに使う/末尾が順に解けて eof で終わるなら何もしない/切り詰めずに雛形どおり改名する。下の『止めない』の件と同時に入れること(stop_all に入ると毎晩同じ UTC 日に再起動するので、順位表の露出が毎日になる)

- **[止める]** start_all.bat が 2 つの常駐(record_hyperliquid.py・record_okx_traders.py)を起動するのに、stop_all.bat と restart_all.bat の [4/5] がそれらを止めず確かめない。既存の試験 test_every_launched_component_is_also_stopped_and_verified(2026-09-09 の事故の再発防止)が落ちる。3 本の docstring は『一回きりの実行の前に deploy\stop_all.bat で常駐を止めよ』とオーナーに指示しているが、それでは止まらない
  - 場所: deploy/start_all.bat:39,42/deploy/stop_all.bat:12/deploy/restart_all.bat:122/scripts/record_hyperliquid.py:60-62/scripts/record_okx_traders.py:53-56/docs/OPERATIONS.md 677-681 行(未了と自認)
  - 筋書き・根拠: 【事実】PYTHONPATH=src python -m pytest tests/test_deploy.py tests/test_record_venues.py tests/test_record_liquidations.py tests/test_repair_gz_listing.py -p no:cacheprovider --basetemp=.../critic_L2/tmp → 『FAILED tests/test_record_liquidations.py::test_every_launched_component_is_also_stopped_and_verified ... AssertionError: stop_all が record_hyperliquid.py を止めない』1 failed, 71 passed。【推定】PC での帰結: (a) 夜間の restart_all が『再起動した』と出しながら 2 つは古いコードのまま走り続け、git pull で入れた直し(上の heal_tail の直しを含む)が再起動まで届かない。(b) オーナーが docstring どおり stop_all のあとに --max-pages などの一回きりを打つと、常駐と 2 つのプロセスが同じ .csv.gz に同時に追記する(台本自身が『止める仕組みは無い』と書いている状態)。レーンは 1 行ずつの差分を用意済みと書いているので、それを同じコミットで入れれば解ける(deploy の bat はフック・settings・githooks ではない)

- **[聞く]** 共有の量。share_logs.bat が 3 つの出所の日のファイルを毎日 git に積むと、レーン自身の見込みでも 1 日 30.6〜40.6MB、さらに 06:30 JST(=21:30 UTC)の共有はその UTC 日のファイルを約 9 割の時点で一度コミットし翌日に完成版を再びコミットするので、git の中では約 1.9 倍になる。この量を git で運ぶのでよいか、リード(必要ならオーナー)の判断が要る
  - 場所: deploy/share_logs.bat:63-71/docs/OPERATIONS.md 664-665 行(量の見込み)
  - 筋書き・根拠: 【事実】本環境の .git は 3.8G(git count-objects: size-pack 3.15 GiB)。【推定】30.6〜40.6MB/日 ×約 1.9 ≈ 58〜77MB/日 ≈ 月 1.7〜2.3GB 増える(見込みはレーンの小さな試しからの延長で、オーナーの PC での実測ではない)。研究側の空きは約 14GB(課題文)。GitHub は 1 ファイル 100MB を超えると push を拒むので、どれか 1 つの日のファイル(候補は Hyperliquid の positions_*)がそれを超えると share_logs の push 全体が失敗し、既存の全出所の共有が止まる【未確認: 出所ごと・ファイルごとの大きさの内訳は書かれていない】。直す側の案(直す扱い): share_logs は完了した UTC 日のファイルだけを写し、今日のファイルを写さない(二重のコミットが消える)

- **[直す]** Hyperliquid の速さの制御(公表の上限の半分)が試験で押さえられていない。sweep() が sleep するかを見る試験が無く、req_interval の計算だけを見ている
  - 場所: tests/test_record_hyperliquid.py:101-108/scripts/record_hyperliquid.py:466-467
  - 筋書き・根拠: 【事実】作業ツリーを scratch(.../critic_L2/repo)に写し、record_hyperliquid.py の 'next_at = self._clock() + self.req_interval' を 'next_at = self._clock()'(待たずに全速で叩く)に変えても新しい試験 37 件が全部通る(37 passed)。外へ向けた唯一の安全の主張(1 分あたり重み 1200 の半分)が壊れても気づけない。FakeSession と記録用の sleep で、N 件の呼び出しの間の待ちの合計が (N-1)×0.2 秒以上であることを確かめる試験を足す

- **[直す]** OKX の決済済み建玉の鍵を『全部の history ファイルから』戻すという主張を試験が確かめていない(試験のファイルが 2 つだけ)
  - 場所: tests/test_record_okx_traders.py:159-177/scripts/record_okx_traders.py:344
  - 筋書き・根拠: 【事実】scratch の写しで glob("history_*.csv.gz") を sorted(...)[-2:](新しい 2 ファイルだけ)に変えても 37 passed。3 つ以上の日のファイル(いちばん古いものに鍵)を置く試験にする。同じ写しで、ページの上限に届いたときの raise を return に変えても 37 passed(docstring の『上限に届くと errors に 1 行』も押さえられていない)

- **[直す]** OPERATIONS.md の共通の段落が『書き込みの失敗はその行を手元に残して次の回に書く』と 3 つ全部について書いているが、Deribit は 15 分ごとの一回きりのプロセスなので、終わる時点で書けなかった行はプロセスと一緒に消える(終了コード 1 とログだけ残る)。台本の docstring の方は正しい
  - 場所: docs/OPERATIONS.md 671-672 行/scripts/record_deribit_oi.py:314-338,355
  - 筋書き・根拠: 【事実】run_once は最後に一度だけ再試行し、残りを self.unwritten に数えて main が 1 を返すだけで、行を次の回へ渡す仕組みが無い(コードを読んだ)。share_logs の copy がファイルを掴んでいる間に 15 分の回が当たると、その回の BTC・ETH の行と errors の 'write' 行も失われる。文書を『Deribit はその回の中で 1 回だけ再試行し、残りは失われて終了コード 1』に直す

- **[直す]** fetch_all.bat の置き場所の理由『1 回 0.2〜0.6 秒で安い』は API の呼び出し 1 回の時間で、プロセス全体の重さではない。Deribit の _restore は毎回、昨日と今日の book ファイルを全行の dict に展開するが、usOut は応答ごとに新しいので戻した鍵が当たることは無い
  - 場所: deploy/fetch_all.bat:19-23/scripts/record_deribit_oi.py:261-266
  - 筋書き・根拠: 【事実】実物の応答(本環境から get_book_summary_by_currency を BTC 990 銘柄・ETH 832 銘柄で 1 回ずつ取得)を 96 回分書いた日のファイル(5.44MB)を昨日・今日の 2 つ置き、新しいプロセスで DeribitOiRecorder を作ると『restore s 2.36 keys 192 maxrss MB 438.5』(.../critic_L2/restore_only.py)。その日の終わりに近いほど、15 分ごとに約 440MB・約 2 秒を、重複を一度も防がない処理に使う。record_oi.py の後なので OI は遅らせないが、理由の文と実際の重さが合っていない。復元をやめるか鍵の 2 列だけ読む、または文を実測に直す

- **[注記]** 封印と安全不変条件は守られている
  - 場所: scripts/record_*.py(3 本)/backtest_data/phase2_sealed/*/SEALED.json
  - 筋書き・根拠: 【事実】8 つの封印の単位(P2-01〜P2-08b)のファイル一覧に okx・deribit・hyper・ratio・oi・option を含むパスは 0 件(SEALED.json を読んで検索)。3 本は backtest_data を読まない。3 本とも公開の読み取りだけで、鍵・発注の端点・LIVE の切り替えに触れない(コードを読んだ)。リポジトリの中でほかに Hyperliquid を叩く台本は無い(grep の当たりは dashboard.py の表示文と research_position_ladder.py の注釈だけ)

- **[注記]** Hyperliquid の順位表に同じアドレスが 2 回あると、その口座は 1 周で 2 回聞かれ、accounts の行が 2 回書かれる(positions は sweep 内の seen で 1 回になる)
  - 場所: scripts/record_hyperliquid.py:285-304,463-490
  - 筋書き・根拠: 【未確認】実物の順位表(38.8MB)に重複があるかは確かめていない。scratch の写しで sweep 内の seen を外しても 37 passed(account_rows 側でも銘柄の重複を落としているので、現状は重複防止が二重)

- **[注記]** OKX の指導者の一覧の重複防止の鍵は昨日と今日の 2 日分だけ戻すので、dataVer が 3 日以上変わらず途中で再起動すると、同じ (data_ver, inst_type, unique_code) をもう一度書く。OPERATIONS.md の『同じ行は二度書かず』の例外
  - 場所: scripts/record_okx_traders.py:330-341
  - 筋書き・根拠: 【未確認】OKX の dataVer がどれくらいの間隔で変わるかは確かめていない。毎時変わるなら起きない

- **[注記]** Windows の起動の行と cp932 は通っている
  - 場所: deploy/start_all.bat:39,42/deploy/share_logs.bat:63-71/deploy/fetch_all.bat:19-23
  - 筋書き・根拠: 【事実】:launch の %~2 に引数('--loop'・'--loop 3600')を入れても、cmd /c ".venv\Scripts\python.exe %~2 >> %~4 2>&1" で引数としてそのまま渡る形になっている(コードを読んだ。cmd.exe での実行は本環境ではできないので【未確認】)。test_deploy.py の全件と cp932 の行末の検査は通った。共有の途中で copy が書きかけのメンバを写すと、paper_logs 側の写しは末尾が切れたメンバで終わることがある(書き込みは 1 回の write なので幅は狭い)

## リードの応答

- **2 回目も [止める](2 件)。計画 第 5 版 §4-1 により、直し続けずに止める。** 根本の原因:
  1. 強制終了で切れた gzip の後始末(heal_tail)が、圧縮済みのバイト列の中に偶然現れる gzip の先頭の印(1f 8b 08)でメンバを割る既存の部品(`gz_members.split_raw_members`)を使い、その場で切り詰めた。リポジトリには、ファイルを丸ごと改名するだけで中身を壊さない実績のある型(`record_liquidations.py` の Writer)があったのに、委任文はそれを型として指定していなかった。
  2. 起動の台本(start_all.bat)はレーンの範囲に入れ、止める台本(stop_all.bat・restart_all.bat)は範囲の外にした。起動と停止は対になっているのに、リードが範囲を片側だけで切った。1 回目の批評家がこれを [止める] とし、作業者は範囲の外なので直せなかった。
  どちらも委任文(リードの仕様)の不備(F2)。作り直すときは、Writer の型を指定し、起動・停止・再起動の 3 つを同じ範囲に入れる。共有の量(月に約 1 GB を git に積む)はオーナーに判断を求める。
