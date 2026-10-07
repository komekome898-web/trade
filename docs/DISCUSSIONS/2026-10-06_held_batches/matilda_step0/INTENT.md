# マチルダの意図と族の表(工程 0 の成果、オーナーに見せるもの)

出所: 原典 `docs/legacy/matilda_for_TaroCamp37.py`(v37)・`docs/legacy/matilda_v52.py`(v52)。2 つの読み(`LEAD_READ.md`・`INDEPENDENT_READ.md`)と突き合わせ(`RECONCILE.md`)から作った。行の詳しい根拠は `INDEPENDENT_READ.md` の各節。
オーナーの逐語: L-776「**全ての変数は固定値でなく調整可能な値で、それはバックテストで探る族の種類と同義です。modeの切り替えとかもあったと思う。**」/ L-018「**『コードから戦略意図を汲み取り、その戦略の強み弱みを分析し、現環境に適応した戦略を構築して欲しい』**」。
この文書は測定の形・1 分足への写し方を書かない(工程 0 の S6)。

## 1. 意図

- **レンジでナンピンする機械**(v37:19-21、v52:22-24「**レンジの上方でS、下方でL、中央付近で決済するよ。レンジである限り損はしない。損する時はレンジブレイク時と利確指値に届かない長期間のポジ保有時**」)。
- **狙い**: 直近 range_count 本の高安で作ったレンジの中心は足ごとに動く。中心から entry_setting × ボラ 離れた側で逆向きに建て、さらに逆行したら step × ボラ の間隔で段を積み(ナンピン)、中心寄りで利確する。段が増えるほど 1 段あたりの利確の幅を割って早く逃げる(v37:71・881)。儲けの源は「入る距離と出る距離の差」(v37:139「**この差分が利益になるからね**」)。
- **置き方**: 指値は厚い板の手前に置く(O-4、v37:159)。板を盾にして約定の値段を良くする。
- **避けたいもの**:
  - 在庫の膨らみ(「**基本はナンピンBotなのでここの調整ミスると危険だよ**」v37:108)→ 段数の上限。
  - 動きが小さすぎるレンジ(「**ポジポジ病防止**」v37:131)→ 幅の門。
  - 利確に届かない長い保有 → alert_count 分で利確の線を緩め、倍で成行(v37:126-129)。
  - レンジが壊れる一方向の動き → v37 はブレイクを判定し、逆の玉を成行で切り、確認がとれればブレイクの向きに積む(大きく取って損を埋める、v37:113)。v41 からはブレイクを外し、vr = レンジ幅 ÷ ボラ で「レンジかトレンドか」を見分けて設定の組を入れ替える(v52:86・122-125「**vr>10のときはヒゲ狙いで逆張り、vr<10のときはレンジ内で細かくポジ取って損切りはしない**」)。
  - 取引所の事情(SFD の帯・メンテ前後・API の制限)。
- **設定値は相場に合わせて調整するもの**: 「**これらの設定値次第で運用方法が結構変わると思う。必要に応じてカスタマイズしてみてほしい**」(v37:166-167)、entry:exit の比は「**慎重派は 4:3 、欲張りさんは 5:1 、高回転の 2:1 みたいに自由に決めてね**」(v37:140)。
- **オーナーの言語化(2026-09-08 §7)とコードの対応**: §7-3「大きく動いた後は静観し、新しいレンジの中心へ戻ったら再開」は、v37 ではブレイクの解除(値段が中心を戻る、v37:952-965)に当たるが、コードは静観だけでなく、出来高のある順行の足が出るとブレイクの向きに積む(v37:1001-1005)。v52 ではブレイクが無く、vr の組の入れ替えが代わり(RECONCILE #10)。

## 2. 1 巡回の流れ(要点。詳しくは INDEPENDENT_READ §3)

- 足ごと(v37 1 分・v52 5 秒): ヒゲの切り落とし(beard_ignore)→ ボラ(vola_count 本の平均実体)→ レンジ(range_count 本の高安・中心・幅)→ v37: ブレイクの線・b_signal・expantion_flg / v52: vr → 設定の組 → 線(建ての境 ssp・lsp = 中心 ± entry_setting × ボラ、利確 sep・lep = 中心 ± exit_setting × ボラ)。
- 巡回ごと(v37 0.6 秒・v52 0.8 秒):
  - 建ての側: v37 = 値段が 中心 ± entry_setting × ボラ の外に出た側。v52 = 値段が中心より上なら売り・下なら買い(建ての指値は ssp より上・lsp より下にだけ)。幅の門・SFD・(v52)取引所の状態・時刻の偏りで止まる。
  - 建て: 厚い板(bigvol)の 2 円手前に sizemin の指値。前に出した指値から step × ボラ 以上離れた板を、深い方へ探す。段数の上限まで、1 巡回 1 本。出した指値は合図が続く間は残る。
  - 決済: 時間(alert_count で緩め、倍で成行)、反対の向き(v37 = 反対の建ての域、v52 = 中心をまたぐ)で成行。利確の形は v37 = 建値 ± ボラ × step_exit ÷ 段数 に届いた板 / v52 = exit_mode(0 ドテン・1 中心付近 sep・lep・2 値幅)。
- v52 の休む時間は、呼び出しが消されていて効かない(v52:1127)。

## 3. 族の表

### 3.1 原典の設定の区切りにある全部(機械の検査 `scripts/road/source_params.py` の対象)

印: 「族」= バックテストで探る値(L-776)。「除外」= 売買に効かない、またはオーナーの決まりで置き換わるもの(理由つき)。何を実際に振るかは、この表をお見せしてから決める(工程 0 の S5)。

```params matilda_for_TaroCamp37.py
inifile: 除外 設定ファイルを読む口(売買に効かない)
apikey: 除外 API の鍵(売買に効かない)
secret: 除外 API の鍵(売買に効かない)
public_api: 除外 API の口(売買に効かない)
api: 除外 API の口(売買に効かない)
discord_flg: 除外 通知だけ
WHURL_a: 除外 通知だけ
LINE_NOTIFY_API_URL: 除外 通知だけ
line_flg: 除外 通知だけ
LINE_NOTIFY_TOKEN: 除外 通知だけ
sizemin: 除外 1 段の量はオーナーの決まり(L-745・L-746: 20 万円 × 70% ÷ 段数 ÷ 値段)で決める
sizemax: 族 段数の上限(order_count = sizemax ÷ sizemin、v37:236)として
sizealert: 除外 表示だけ(v37:408・415。コメントの「損切りor撤退指値」に当たるコードは無い)
sizealert_limit: 除外 表示の回数だけ
breakexitsize: 族
fukuri: 除外 量はオーナーの決まりで決め、複利にしない(L-744)
leverage: 除外 量はオーナーの決まりで決める(L-745)
collateral_using: 除外 量はオーナーの決まりで決める(比率 70%、L-746)
pos_count: 除外 複利の量の計算だけに使う(v37:1138)。段数は sizemax で振る
alert_ratio: 除外 表示の量の計算だけ
foot: 族
vola_count: 族
range_count: 族
alert_count: 族
range_setting: 族
over_range_setting: 族
entry_setting: 族
exit_setting: 族 v37 のコードでは使われない(コメントだけ)。v52 の sep・lep の形で効く
break_delay: 族 0 でブレイクの仕組みを切る切り替えを兼ねる
beard_ignore: 族
step_setting: 族
step_exit: 族
bigvol: 族 板のデータが要る
wid: 族 板のデータが要る
entryvol: 除外 bigvol の写しで、ブレイク中に sizemin に替わる状態の値(v37:831-834)。bigvol で振る
```

```params matilda_v52.py
inifile: 除外 設定ファイルを読む口(売買に効かない)
apikey: 除外 API の鍵(売買に効かない)
secret: 除外 API の鍵(売買に効かない)
public_api: 除外 API の口(売買に効かない)
api: 除外 API の口(売買に効かない)
discord_flg: 除外 通知だけ
WHURL_a: 除外 通知だけ
LINE_NOTIFY_API_URL: 除外 通知だけ
line_flg: 除外 通知だけ
LINE_NOTIFY_TOKEN: 除外 通知だけ
settings_inner: 族 vr が vr_setting 未満のときの組
settings_inner.entry_setting: 族
settings_inner.exit_setting: 族
settings_inner.entry_step: 族
settings_inner.sizemin: 除外 1 段の量はオーナーの決まりで決める(L-745・L-746)
settings_inner.sizemax: 族 段数の上限として
settings_inner.order_count: 族
settings_inner.order_delay: 族
settings_inner.alert_count: 族
vr_setting: 族
settings_outer: 族 vr が vr_setting 以上のとき・時刻の偏りがあるときの組
settings_outer.entry_setting: 族
settings_outer.exit_setting: 族
settings_outer.entry_step: 族
settings_outer.sizemin: 除外 1 段の量はオーナーの決まりで決める(L-745・L-746)
settings_outer.sizemax: 族 段数の上限として
settings_outer.order_count: 族
settings_outer.order_delay: 族
settings_outer.alert_count: 族
time_anomaly: 族 切り替え
over_sleep: 族 切り替え(v52 では休む処理が呼ばれず効かない、v52:1127)
order_delay: 除外 settings_outer の写し(v52:134。param_set で毎足上書き)
entry_setting: 除外 settings_outer の写し(v52:136)
exit_setting: 除外 settings_outer の写し(v52:137)
entry_step: 除外 settings_outer の写し(v52:138)
sizemin: 除外 settings_outer の写し(v52:140)
sizemax: 除外 settings_outer の写し(v52:141)
order_count: 除外 settings_outer の写し(v52:142)
sizealert: 除外 表示だけ
sizealert_limit: 除外 表示の回数だけ
foot: 族
vola_count: 族
range_count: 族
alert_count: 除外 起動時の値で、param_set が組の alert_count で上書きする(v52:436・451)
range_setting: 族
over_range_setting: 族
exit_mode: 族 切り替え(0 ドテン・1 中心付近・2 値幅)
exit_step: 族
beard_ignore: 族
bigvol: 族 板のデータが要る
wid: 族 板のデータが要る
fukuri: 除外 量はオーナーの決まりで決め、複利にしない(L-744)
leverage: 除外 量はオーナーの決まりで決める(L-745)
collateral_using: 除外 量はオーナーの決まりで決める(比率 70%、L-746)
pos_count: 除外 複利の量の計算だけに使う(v52:1050)
alert_ratio: 除外 表示の量の計算だけ
```

### 3.2 処理の中に直に書かれた値・切り替え(機械では抜き出せない。2 つの読みで拾った)

| 値・切り替え | 版と行 | 何を決めるか | 族か |
|---|---|---|---|
| 厚い板の何円手前に置くか(2 円) | v37:842・866、v52:754・797 | 建ての指値の位置 | 族(板のデータが要る) |
| 利確の指値の板からのずれ(v37 0 円・v52 2 円) | v37:892・906、v52:831・866 | 利確の指値の位置 | 族(板のデータが要る) |
| ブレイクの線の距離(レンジ幅の半分)・2 倍のレンジ | v37:505・508・493・497 | ブレイクの判定 | 族 |
| b_signal の数え方(出来高が平均を超えた足の形) | v37:512-534・621-643 | ブレイク中の順行・逆行の確認 | 族(切り替え) |
| SFD の帯 4.8 / 5.2% | v37:972-990、v52:913-926 | 建てを止める・片側だけにする | 取引所の制度。族にするかを決める(問い) |
| 休む時間(23:50〜0:00・3:50〜4:15) | v37:325-338 | 日付またぎ・メンテ前後 | 取引所の事情。族にするかを決める(問い) |
| 時刻の偏りの表(曜日・時間) | v52:361-366 | time_anomaly の向き | 族(time_anomaly と一緒) |
| 緩めた利確の「建値 ± 100 円」 | v52:841・849・855・874・882・888 | 中心寄りの利確が損になるときの値段 | 族 |
| 時刻の偏りの利確の幅(レンジ幅) | v52:826・861 | time_anomaly の玉の利確 | 族 |
| 自動ロットの段数 5 / 7(expantion_flg) | v37:1059-1062 | レンジの確度で段数を替える | 族(段数の切り替えとして) |
| 強制の成行を一括か sizemin ずつか | v37:703-714、v52:567-581 | 決済のやり方 | 族(切り替え) |
| 巡回の間隔 0.6 / 0.8 秒・注文後の待ち | v37:1109、v52:1015 ほか | 判定の頻度 | 写し方の段で決める(1 分足では足ごと) |
| 最小ロット 0.01 | 各所 | 取引所の最小注文 | 取引所の制度(オーナーの決まりは 0.001 BTC 未満切り捨て、L-746) |

## 4. 分からないこと(INDEPENDENT_READ §5 の 18 件と、リードの読み §5)

主なもの:
1. v52 の inner / outer の、オーナーが実際に使った値と vr_setting(出荷の値は 2 組が同じ、vr_setting 100、コメントの例は 10)。「ヒゲ狙いで逆張り」をどの値で表すつもりだったか。
2. v37 の exit_setting がコードで使われていないこと(利確の意図は「中心から exit_setting × ボラ」か「建値から step_exit × ボラ ÷ 段数」か)。
3. v52 で休む処理の呼び出しを消した理由(v52:1127)。
4. v37 の左右の非対称(全部の取り消しの条件 v37:1092、ブレイク中の entryvol の切り替えが買いだけ v37:831-834)が意図か。
5. 板のデータ(厚い板の手前に置く)が過去の期間にあるか(写し方の段で調べる)。
