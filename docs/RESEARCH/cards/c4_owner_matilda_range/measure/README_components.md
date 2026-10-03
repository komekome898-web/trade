# カード 4 マチルダ: 部品ごとの効果の 14 本(2026-10-03)

関門 ② の前の生の出力の説明。言葉の判定(効く・効かない)は書かない。損益は bp・持ち高 1 単位(7 段 = 1)あたり・経費の前。

## 何を測ったか
- 族(1): 部品ごとの効果(L-018「強い部分の利益率をあげ、弱い部分の避け方」、オーナーに見せた族の切り方 L-567 の前の返答)。基準 = v37 のとおりの全部入り(`full`)。そこから 1 つずつ外す: 小さすぎの門(`no_width`)・静観と再開(`no_trend`)・時間で出る(`no_time`)・段(`no_levels`)、逆転順張りに替える(`follow`)、核だけ(`core` = 4 つを全部外す)。それぞれレンジの端を実体(`body`)とヒゲ(`wick`)で。
- 関数: `src/bot/research/cards/library/c4_owner_matilda_range.py`(第 4 稿 8767172c、値の表の拡張 b8351cc1)。変種の作り方は scratchpad の台本 `run_b2.py` の `C4_KW`(`full` = 既定の引数、`no_width` = width_gate=False、`no_trend` = trend_gate=False、`no_time` = time_exit=False、`no_levels` = levels=False、`follow` = on_trend='follow'、`core` = 4 つとも False)。
- 期間: 2015-11-28T15:00Z 〜 2023-12-17T15:00Z(bitFlyer FX の 1 分足、封印の前)。**CARD.md に登録していた始まりは 2017-08-17T15:00Z で、走らせた期間と違っていた(監査の止める 1)。** 走らせの台本の既定の期間(カード 5〜8 の決め「封印の外の全期間」、`W4_batch2_LEAD_REVIEW.md`)をそのまま使ったリードの誤り。決め直し: カード 5〜8 と同じ理由(段 2 は封印の外の全期間、A-10 で縮めない。このカードは bitFlyer だけを使う)で全期間を本値にし、CARD.md を直した。登録していた期間の表も並べる(下)。2015〜2016 年は空きが多い年(CARD.md 迷った点 8)。暦年の区切りで読んでつないだ(区切り 9)。
- 走らせ方: `PYTHONPATH=src:<scratchpad>/w4/batch2:<scratchpad>/w4/measure python3 <scratchpad>/w4/batch2/run_b2.py --card c4 --variant <変種>`。4 本ずつ同時。1 本あたり約 850 秒、最大 RSS 約 1.37GB(run_record.json)。
- 表の計算: `docs/RESEARCH/cards/tools/goal_table_c4.py`(取引 = 持ち高の向きが続いた区間。最大の落ち込み・最悪の月・プラスの月は daily.csv から)。

## 表(生の出力から。関門 ② の前。2026-10-03 に 1 回目の監査の指摘で作り直し)

列の出所(監査の直す 3・5): 1 日あたり・区間 = 各 `daily_stats.json`。取引・1 取引あたり・勝率・保有・買い/売り = 各 `extra.json`(`bot.research.cards.pnl` の規則。前の版の表は `goal_table_c4.py` の足の並びの添字の規則で、core_body で 1 取引あたり −0.53850 対 −0.53870 の差があった。この版は extra.json にそろえた)。総量・日の数・2017-08-18 以降・対の差 = 各 `daily.csv`。持ち高の大きさの平均 |e| = 各 `run.npz`。計算 = `docs/RESEARCH/cards/tools/c4_components_tables.py`、出力 = `measure/components_tables.json`。区間 = circular block bootstrap(塊 1 日・1,000 回・種 20261002・95%)。bp は持ち高 1 単位(段を全部積んだ状態 = 1)あたり。`no_levels`・`core` は段が無いので 1 段目で持ち高 1、ほかは 1 段 = 1/7。そのため変種で持ち高の大きさが違う(|e| の列)。最大の落ち込みは bp。

### 全期間(2015-11-28〜2023-12-17、日の数 2,941)

| 変種 | 1 日あたり(bp) | 95% 区間 | 総量(bp) | 取引の数 | 取引/日 | 1 取引あたり(bp) | 勝率 | 保有の中央(分) | 平均 |e| | 買い / 売り(bp) | 最大の落ち込み(bp) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full_body | -6.4 | [-7.6, -5.3] | -18,829 | 150,288 | 51.1 | -0.125 | 72% | 2 | 0.025 | -9,037 / -9,792 | 19,002 |
| full_wick | -2.8 | [-3.3, -2.2] | -8,197 | 62,038 | 21.1 | -0.132 | 65% | 2 | 0.008 | -3,757 / -4,440 | 8,552 |
| no_width_body | -6.4 | [-7.6, -5.3] | -18,831 | 150,306 | 51.1 | -0.125 | 72% | 2 | 0.025 | -9,037 / -9,795 | 19,001 |
| no_width_wick | -2.8 | [-3.3, -2.2] | -8,200 | 62,045 | 21.1 | -0.132 | 65% | 2 | 0.008 | -3,757 / -4,443 | 8,552 |
| no_trend_body | -2.4 | [-9.6, 5.0] | -6,925 | 417,583 | 142.0 | -0.017 | 91% | 3 | 0.262 | 26,543 / -33,468 | 30,693 |
| no_trend_wick | -0.2 | [-7.0, 7.1] | -502 | 419,029 | 142.5 | -0.001 | 91% | 3 | 0.260 | 33,352 / -33,855 | 30,825 |
| no_time_body | -6.4 | [-7.6, -5.3] | -18,807 | 150,282 | 51.1 | -0.125 | 72% | 2 | 0.025 | -9,011 / -9,796 | 18,977 |
| no_time_wick | -2.8 | [-3.3, -2.2] | -8,192 | 62,031 | 21.1 | -0.132 | 65% | 2 | 0.008 | -3,750 / -4,442 | 8,552 |
| no_levels_body | -36.3 | [-41.6, -30.9] | -106,752 | 132,223 | 45.0 | -0.807 | 67% | 3 | 0.137 | -53,841 / -52,911 | 108,723 |
| no_levels_wick | -17.2 | [-20.0, -14.3] | -50,466 | 58,058 | 19.7 | -0.869 | 61% | 2 | 0.047 | -25,498 / -24,968 | 53,366 |
| follow_body | -15.9 | [-19.7, -12.2] | -46,812 | 707,035 | 240.4 | -0.066 | 74% | 3 | 0.191 | -16,679 / -30,134 | 48,006 |
| follow_wick | -11.1 | [-14.7, -7.5] | -32,677 | 808,131 | 274.8 | -0.040 | 71% | 2 | 0.183 | -11,696 / -20,981 | 33,900 |
| core_body | -48.8 | [-61.7, -37.5] | -143,476 | 266,338 | 90.6 | -0.539 | 78% | 4 | 0.734 | -26,573 / -116,903 | 146,778 |
| core_wick | -46.7 | [-59.9, -35.2] | -137,365 | 274,408 | 93.3 | -0.501 | 78% | 4 | 0.729 | -23,865 / -113,500 | 141,644 |

### CARD.md に登録していた期間(2017-08-18 以降の日本時間の日、日の数 2313)

| 変種 | 1 日あたり(bp) | 95% 区間 | 総量(bp) |
|---|---|---|---|
| full_body | -6.7 | [-7.9, -5.3] | -15,383 |
| full_wick | -3.1 | [-3.7, -2.5] | -7,138 |
| no_width_body | -6.7 | [-7.9, -5.3] | -15,382 |
| no_width_wick | -3.1 | [-3.7, -2.5] | -7,138 |
| no_trend_body | 8.9 | [0.6, 17.8] | 20,504 |
| no_trend_wick | 11.1 | [3.5, 19.6] | 25,748 |
| no_time_body | -6.7 | [-7.9, -5.3] | -15,382 |
| no_time_wick | -3.1 | [-3.7, -2.5] | -7,138 |
| no_levels_body | -39.4 | [-45.1, -33.4] | -91,091 |
| no_levels_wick | -19.6 | [-22.9, -16.3] | -45,444 |
| follow_body | -9.6 | [-13.8, -5.7] | -22,113 |
| follow_wick | -3.6 | [-7.4, 0.0] | -8,402 |
| core_body | -31.1 | [-44.2, -17.4] | -72,029 |
| core_wick | -30.5 | [-43.3, -16.3] | -70,588 |

### 部品ごとの効果(同じレンジの端の全部入りとの、日ごとの損益の差。監査の聞く 10)

| 変種 | 差の 1 日あたり・全期間(bp) | 95% 区間 | 差の 1 日あたり・2017-08-18 以降 | 95% 区間 |
|---|---|---|---|---|
| no_width_body − full | -0.0 | [-0.0, 0.0] | 0.0 | [0.0, 0.0] |
| no_width_wick − full | -0.0 | [-0.0, 0.0] | -0.0 | [-0.0, 0.0] |
| no_trend_body − full | 4.0 | [-3.0, 11.6] | 15.5 | [7.6, 24.8] |
| no_trend_wick − full | 2.6 | [-4.2, 10.0] | 14.2 | [6.6, 22.7] |
| no_time_body − full | 0.0 | [-0.0, 0.0] | 0.0 | [0.0, 0.0] |
| no_time_wick − full | 0.0 | [-0.0, 0.0] | 0.0 | [0.0, 0.0] |
| no_levels_body − full | -29.9 | [-34.2, -25.6] | -32.7 | [-37.5, -28.0] |
| no_levels_wick − full | -14.4 | [-16.8, -11.9] | -16.6 | [-19.2, -13.8] |
| follow_body − full | -9.5 | [-12.9, -5.8] | -2.9 | [-7.0, 0.7] |
| follow_wick − full | -8.3 | [-11.8, -4.8] | -0.5 | [-4.3, 3.1] |
| core_body − full | -42.4 | [-54.8, -31.5] | -24.5 | [-37.0, -10.9] |
| core_wick − full | -43.9 | [-56.9, -32.6] | -27.4 | [-40.1, -13.3] |

月の円(建玉 60 万円)は、`W4_first3_RESULTS.md` の読み方「1 日あたり × 30.4 日 × 建玉 60 万円(資金 30 万円 × 2 倍、計画 1-2)」と同じ換算(監査の直す 5)。1 日あたり 1bp = 月 1,824 円。

年ごとの日の数(年ごとの表の分母): 2015 年 33・2016 年 366・2017 年 365・2018 年 365・2019 年 365・2020 年 366・2021 年 365・2022 年 365・2023 年 351(2015 年は 11-28 からの 33 日)。

## 分かっている限り
- 【事実】`no_width` と `no_time` は `full` とほぼ同じ: 決定のある足 3,982,104 本のうち、持ち高が違う足は 55 本と 52 本(`full_body` との比較。前の版の 1,069 本・1,066 本は決定の無い足 1,014 本を数えていた誤り、監査の直す 2)。幅の門(150 円 ÷ 2019-09-04 の値段)と時間で出る(40 分)は、この期間ではほとんど効いていない。保有の中央値は 2 分。
- 区切りの同一性の照合【事実】: `full_body`・`follow_wick`・`no_trend_body` の 3 変種で、2018 年の 1 年(足 521,307 本・決定 520,293)を一度に読んだ結果と月の区切り 11 か所でつないだ結果を比べ、3 本とも持ち高の食い違い 0(`exposure_identical: true`)。コマンド `run_b2.py --card c4 --variant <変種> --check --start 2018-01-01T00:00:00Z --end 2019-01-01T00:00:00Z`、出力 `measure/check_c4_<変種>.json`。監査役が追加で core_body・no_levels_wick・no_time_wick・no_width_body の 4 本を同じ形で照合し、4 本とも食い違い 0(`measure/check_c4_<変種>.json`)。合わせて 7/14 本。残り 7 本(full_wick・no_width_wick・no_trend_wick・no_time_body・no_levels_body・follow_body・core_wick)・ほかの年・本番の暦年の境の区切りは確かめていない。
- 負けの場面の分け(族 (3))はまだ出していない。

## 出力のファイル(sha256)

- `core_body/daily.csv` 7934d932ef1c215473c15aa8629a1464e2f1c7886632fe4220b6934afe0e84c3
- `core_body/daily_stats.json` 0a1d84b95dd95caf941d5fdc856a9e3a640cd4441861a5a069fbd92c3513adcf
- `core_body/diagnostics.json` 0d275edd6a34281114063ce8fb812548aba5019f8dd85e75b9c43103e289ca7a
- `core_body/extra.json` 1139a197b23a97b3fe7811b2b75174cbe21f8de9176bb535ffca23fa46a269dc
- `core_body/run_record.json` 5770f2a0fc92403df05e70d1b794d3ec34f03d50c9aea03ff09b1ea82e81e8c2
- `core_wick/daily.csv` 9d0fefda63c6ea468450c84197cad088cd3a45adbf66a1588ef020735d8bb615
- `core_wick/daily_stats.json` 848fedda26f2f830e6560016aa875ba9932b9ad5cb805c5ba4701a1ebddfe5a7
- `core_wick/diagnostics.json` 0d275edd6a34281114063ce8fb812548aba5019f8dd85e75b9c43103e289ca7a
- `core_wick/extra.json` 5a7d3705fb88f44b2961d7202def1a1d6bd77739922a9c50db6e50626997a22b
- `core_wick/run_record.json` 6d91a0bddad8e9f01adfc77df8726e1deb485f849ce645047f11d1dc09ce9248
- `follow_body/daily.csv` c379b459cd13d3625f16517d98c058a544b7020f47c809acf0940e26d69f8dcc
- `follow_body/daily_stats.json` c44e7682cc44997f9e7f56c4ec6366f792727dda6542e1404aaca90f50cf7b81
- `follow_body/diagnostics.json` 0d275edd6a34281114063ce8fb812548aba5019f8dd85e75b9c43103e289ca7a
- `follow_body/extra.json` bc4b2293ae34f62fa6f13256841d81977f07ea0a2ac1de7c7787487ea397833a
- `follow_body/run_record.json` 98fd8a5ce1f98e67be40fa14f6a6229e2413f85042a13b2e89239f8e78993a1b
- `follow_wick/daily.csv` b89d4073fafd4b0673c767b5451f0d3efab7bd97350bd2f10bc415b7d8f7bd71
- `follow_wick/daily_stats.json` e0d587dff388b1178df0efe0bda975af45b67f0dcf752ea44b7add1d4fcbbe32
- `follow_wick/diagnostics.json` 0d275edd6a34281114063ce8fb812548aba5019f8dd85e75b9c43103e289ca7a
- `follow_wick/extra.json` 945eb8cde8b2435982c0a76680235e768205aa05fdb65c221967204f45d17f17
- `follow_wick/run_record.json` 1dcdbb2f1f1a482c5887fe2a16c7ab6d895cca9e9eb620b63554b4c6da1314d2
- `full_body/daily.csv` c9afb2fb123d6cfb71404b98e408d47a72445f016b42369cab02eb3b8c0e438d
- `full_body/daily_stats.json` 651264a5d9fa35b7548d94502b878c94288782d48fd3e181e890711ad63692ec
- `full_body/diagnostics.json` 0d275edd6a34281114063ce8fb812548aba5019f8dd85e75b9c43103e289ca7a
- `full_body/extra.json` d288b2b9dbdad359546ac14e2ffae853b8b7b75ee72eb33116b32bfb7c64f861
- `full_body/run_record.json` a4a4dcfbcbfcf23d2f90c881436bdb2fea4834db9beccc154cd74e8110e17f39
- `full_wick/daily.csv` ecf564a99fd12147ff220ab760b2bcfcf792f2bddd8c05aee4d7a9f2081a268e
- `full_wick/daily_stats.json` 8e0b0838840a3e575c23119d0e308f01fbf3ed40325dca36adfbb97eec18a43b
- `full_wick/diagnostics.json` 0d275edd6a34281114063ce8fb812548aba5019f8dd85e75b9c43103e289ca7a
- `full_wick/extra.json` 198a1dc191f85cbbeec06e2a52cbf71b5892ae87d383f8364d9b7676fe080b25
- `full_wick/run_record.json` 0ab8cf3711e3fcec7b57c2fd71432a9da21abb5c5bff9e3e9a09b7f5309d754d
- `no_levels_body/daily.csv` 0406881d5fcc5abedb7348b66be138a71555fd42e804f9246698e5828f54160a
- `no_levels_body/daily_stats.json` 30330d829b16c0e0fccd1dbb52d70b47e4e52967cac56028682a722e7f0499cc
- `no_levels_body/diagnostics.json` 0d275edd6a34281114063ce8fb812548aba5019f8dd85e75b9c43103e289ca7a
- `no_levels_body/extra.json` 81e583084388537671b24c6cfd909e01c0954f1e67bb0c6a3741d5a5a6002c8e
- `no_levels_body/run_record.json` 14d35f2a69b68cfe100342ced5c20b556dfa3b8b091713ad2d6e6ae04abb97f5
- `no_levels_wick/daily.csv` a8cd94f2fc996180ab35ab74d7aa43b7e0b48eef9ba7a2fc3e91730e3f7e6f62
- `no_levels_wick/daily_stats.json` 3e55413d948ba9828719d8804dae7537d054d8a7d73e480393be4eca65c30673
- `no_levels_wick/diagnostics.json` 0d275edd6a34281114063ce8fb812548aba5019f8dd85e75b9c43103e289ca7a
- `no_levels_wick/extra.json` f729d6ad044ea66b45fe21021089433df78606d0a8909e496cf595c4ded49421
- `no_levels_wick/run_record.json` 84917c51689cd238bd112f4d4189201a5162c14afdb9fa619478a549f061dbfd
- `no_time_body/daily.csv` 75bc9c4414bff54ff6301bfe74e8b43b87ec09d2d8510c6de84ced43d87a9acd
- `no_time_body/daily_stats.json` 3480e552b138c7fb2fc77d2fb266be0d91cf276e602599fc30caa49c6aeed351
- `no_time_body/diagnostics.json` 0d275edd6a34281114063ce8fb812548aba5019f8dd85e75b9c43103e289ca7a
- `no_time_body/extra.json` 786a9d79214659c3fa86475e8058b2fe36f59f4857ad67bd21701113bdd5ba96
- `no_time_body/run_record.json` 4c0c923430711b0d196168c81177ec2a860dae5c9215f4355aaaf50649022a9c
- `no_time_wick/daily.csv` 0cccb6e7f08a154e46e1d9398c37b18ed5328b2f4000835049ece0676a2a4771
- `no_time_wick/daily_stats.json` 113da870a1a2f747aecc32e90eb71724f9a68181e334dfe840246550b9b05ef8
- `no_time_wick/diagnostics.json` 0d275edd6a34281114063ce8fb812548aba5019f8dd85e75b9c43103e289ca7a
- `no_time_wick/extra.json` 10f58e304477edc54cd362c32d01c2779f40a3be1c96408e85cd8160fcb905a4
- `no_time_wick/run_record.json` cb1aea003025aaa96e114ecc6771b0202aa0488baceb3ab810ea42d78ecd31e3
- `no_trend_body/daily.csv` d24762b7ed75813312170179e2edbc4a86b273c90847f3c22b4fd63f33880798
- `no_trend_body/daily_stats.json` bd4b8202805d520bf16a076e934fd6af0eeb5e22e2653dc1cb20672948b7adc2
- `no_trend_body/diagnostics.json` 0d275edd6a34281114063ce8fb812548aba5019f8dd85e75b9c43103e289ca7a
- `no_trend_body/extra.json` f16ce579add368a96359a2cde5ed0de8c90c0e4ebb9ab509903a9f399965b359
- `no_trend_body/run_record.json` 896efa02337cb397aa552c12c32aacd06e619fdc0c8ac34db158ba88ecb02ac4
- `no_trend_wick/daily.csv` ce6463a7bba827890953652859b2f568b4428d5907fa36cb0149e6eb093f18f9
- `no_trend_wick/daily_stats.json` f431ff5ad9b35d105725e5bcd58790c4f3ad673a4981258c8f39c84d1a25fffa
- `no_trend_wick/diagnostics.json` 0d275edd6a34281114063ce8fb812548aba5019f8dd85e75b9c43103e289ca7a
- `no_trend_wick/extra.json` 0991e3990e82c8e936c6662d5f3833fd4f2d43e6d12c63a961fe7c191859d0e9
- `no_trend_wick/run_record.json` 4bb72aa5a6dbe9dd3325a24a5fbb81a7703de7bfaf7e3dfe913e6e2a53d41012
- `no_width_body/daily.csv` 45f73318b214ed44bccafe7a395823be8ffe9282ac402407ee0b2836c6d44fe5
- `no_width_body/daily_stats.json` 4af4179e92f2188304280441c9f340af3bb310e6b05798598ba7290e90e1ef61
- `no_width_body/diagnostics.json` 0d275edd6a34281114063ce8fb812548aba5019f8dd85e75b9c43103e289ca7a
- `no_width_body/extra.json` d1d5dda8fcf7be5bddea2f0bdf3d1c09aae479e1e97c6af7a14edccf39be8931
- `no_width_body/run_record.json` ba08a36726c26a32c49d6793c142968f4aba97c8853a5faab5e6e995f2f68bba
- `no_width_wick/daily.csv` 5d3b8e5bbdcef50046afd74f7681685f83fc5d654334d8f166d56f8f4f25f7c0
- `no_width_wick/daily_stats.json` ee8b659118cd49d5a51f03166987898998ac6184f881a80d6dbbc25110a9ab80
- `no_width_wick/diagnostics.json` 0d275edd6a34281114063ce8fb812548aba5019f8dd85e75b9c43103e289ca7a
- `no_width_wick/extra.json` d7ab5e49b9a3367c4cc799dba702d3249b7a0df8d1ed8fe1d002a379bed07134
- `no_width_wick/run_record.json` 3cff2332f728f71feaa7ea77d75708296b0843add86cfd641578c63afe199fc6

## 監査の 1 回目への対応の追記(2026-10-03)
- 台本: 走らせに使った台本は、走らせの途中まで scratchpad にあり、のちに `scripts/w4_measure/run_b2.py`(コミット 6935ad1b)としてリポジトリに入れた。関数は 8767172c(既定の動き)と b8351cc1(値の表の拡張のみ)。監査役が現行の台本と関数で 14 本の先頭 3 か月を走らせ直し、持ち高がビット一致した。run_record.json には台本・関数のハッシュは入っていない(監査の聞く 11)。
- run.npz の sha256(監査の直す 7):
  - `full_body/run.npz` ca7f18984173edf96f5c639f88387c709d39abbcf2dbbd5e91d00b6ead2075f1
  - `full_wick/run.npz` f99d4cc07aefffe18526044ae98d2d8f040f70293ade8e75e96f2357d8cbfc56
  - `no_width_body/run.npz` 5cdca50e9b0dcc1070ef586f1b52ab0ac6e68456de85c4e365448063eb8a9ec3
  - `no_width_wick/run.npz` ba3036c40f60c9856e2b43a3a7fa6fa4e76fcecfe1e11c2432a9e224e48c8d1a
  - `no_trend_body/run.npz` b5e83bbb8019d157122d8080e3cafb34838ee93d71de239140b0adc05a6d36a6
  - `no_trend_wick/run.npz` 6c20c1a32a6b6396d6bc948833edd1637501534fe378270b2640bd212d091d17
  - `no_time_body/run.npz` e5ff7252ef715796f020d0c184468ea7cfb5d8521c8834b0b81f111474619dc3
  - `no_time_wick/run.npz` e9508a3050d40bfaced31e453b58f376f729164efcc255cdb86eabc23eed7355
  - `no_levels_body/run.npz` f19c298a1441f2968f2820d0eb6addc4614517358fca5572e9dd942826d53fdf
  - `no_levels_wick/run.npz` cda49284fccd16e2678f05173679ba4dc356a8c22e0492f631647e80dbe66175
  - `follow_body/run.npz` 60552a13bd2af0498a40262cbc314e7f50d09610ee6c2b37eb0451732d090f67
  - `follow_wick/run.npz` 05d9ef37db0453e4e22300194ef145470cf8b9a74cce80edf3545c12bb65d8f2
  - `core_body/run.npz` 5cb1a9c3d4a91fd4d9fee4e675b0faec556462dea06e52678d7480bbcdf8461f
  - `core_wick/run.npz` 8f3320a1e604de6a032f84583f264cef7264cf9607fd23eefc5b01e0158e4fc6
- 反証の量のうち「一方向の状態の足を除いた損益」は、run.npz に状態の列が無く、この回では出していない。部品ごとの効果(対の差)は上の表に出した(監査の聞く 10)。
- Jev の設計の段の判定(監査の聞く 12): Jev はオーナーの指示で保留(L-569)。このカードには節を置かない。
