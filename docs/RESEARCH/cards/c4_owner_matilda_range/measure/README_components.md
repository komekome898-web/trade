# カード 4 マチルダ: 部品ごとの効果の 14 本(2026-10-03)

関門 ② の前の生の出力の説明。言葉の判定(効く・効かない)は書かない。損益は bp・持ち高 1 単位(7 段 = 1)あたり・経費の前。

## 何を測ったか
- 族(1): 部品ごとの効果(L-018「強い部分の利益率をあげ、弱い部分の避け方」、オーナーに見せた族の切り方 L-567 の前の返答)。基準 = v37 のとおりの全部入り(`full`)。そこから 1 つずつ外す: 小さすぎの門(`no_width`)・静観と再開(`no_trend`)・時間で出る(`no_time`)・段(`no_levels`)、逆転順張りに替える(`follow`)、核だけ(`core` = 4 つを全部外す)。それぞれレンジの端を実体(`body`)とヒゲ(`wick`)で。
- 関数: `src/bot/research/cards/library/c4_owner_matilda_range.py`(第 4 稿 8767172c、値の表の拡張 b8351cc1)。変種の作り方は scratchpad の台本 `run_b2.py` の `C4_KW`(`full` = 既定の引数、`no_width` = width_gate=False、`no_trend` = trend_gate=False、`no_time` = time_exit=False、`no_levels` = levels=False、`follow` = on_trend='follow'、`core` = 4 つとも False)。
- 期間: 2015-11-28T15:00Z 〜 2023-12-17T15:00Z(bitFlyer FX の 1 分足、封印の前)。暦年の区切りで読んでつないだ(区切り 9)。
- 走らせ方: `PYTHONPATH=src:<scratchpad>/w4/batch2:<scratchpad>/w4/measure python3 <scratchpad>/w4/batch2/run_b2.py --card c4 --variant <変種>`。4 本ずつ同時。1 本あたり約 850 秒、最大 RSS 約 1.37GB(run_record.json)。
- 表の計算: `docs/RESEARCH/cards/tools/goal_table_c4.py`(取引 = 持ち高の向きが続いた区間。最大の落ち込み・最悪の月・プラスの月は daily.csv から)。

## 表(生の出力から。関門 ② の前)

| 変種 | 1 日あたり | 95% 区間(1 日塊) | 取引/日 | 1 取引あたり | 勝率 | 保有(中央、分) | 持ち高 ≠ 0 の割合 | 月の円(60 万円) | 最大の落ち込み |
|---|---|---|---|---|---|---|---|---|---|
| core_body | -48.8 | [-61.7, -37.5] | 90.6 | -0.54 | 78% | 4 | 0.73 | -88,983 | 146,778 |
| core_wick | -46.7 | [-59.9, -35.2] | 93.3 | -0.50 | 78% | 3 | 0.73 | -85,194 | 141,644 |
| follow_body | -15.9 | [-19.7, -12.2] | 240.4 | -0.07 | 74% | 3 | 0.73 | -29,033 | 48,006 |
| follow_wick | -11.1 | [-14.7, -7.5] | 274.8 | -0.04 | 71% | 2 | 0.76 | -20,266 | 33,900 |
| full_body | -6.4 | [-7.6, -5.3] | 51.1 | -0.13 | 72% | 2 | 0.13 | -11,678 | 19,002 |
| full_wick | -2.8 | [-3.3, -2.2] | 21.1 | -0.13 | 65% | 2 | 0.05 | -5,084 | 8,552 |
| no_levels_body | -36.3 | [-41.6, -30.9] | 45.0 | -0.81 | 67% | 3 | 0.14 | -66,207 | 108,723 |
| no_levels_wick | -17.2 | [-20.0, -14.3] | 19.7 | -0.87 | 61% | 2 | 0.05 | -31,299 | 53,366 |
| no_time_body | -6.4 | [-7.6, -5.3] | 51.1 | -0.13 | 72% | 2 | 0.13 | -11,664 | 18,977 |
| no_time_wick | -2.8 | [-3.3, -2.2] | 21.1 | -0.13 | 65% | 2 | 0.05 | -5,081 | 8,552 |
| no_trend_body | -2.4 | [-9.6, 5.0] | 142.0 | -0.02 | 91% | 3 | 0.65 | -4,295 | 30,693 |
| no_trend_wick | -0.2 | [-7.0, 7.1] | 142.5 | -0.00 | 91% | 3 | 0.65 | -312 | 30,825 |
| no_width_body | -6.4 | [-7.6, -5.3] | 51.1 | -0.13 | 72% | 2 | 0.13 | -11,679 | 19,001 |
| no_width_wick | -2.8 | [-3.3, -2.2] | 21.1 | -0.13 | 65% | 2 | 0.05 | -5,086 | 8,552 |

年ごと(1 日あたり、bp):

| 変種 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|---|---|---|
| core_body | -180 | -113 | -65 | -61 | -21 | 13 | -16 | -63 | -53 |
| core_wick | -173 | -114 | -41 | -61 | -34 | 7 | -15 | -59 | -47 |
| follow_body | 35 | -15 | -61 | 14 | 2 | -2 | -40 | -14 | -15 |
| follow_wick | 37 | -14 | -57 | 23 | 13 | -1 | -35 | -6 | -16 |
| full_body | 2 | -1 | -18 | -7 | -3 | -1 | -14 | -7 | -2 |
| full_wick | 3 | 0 | -6 | -4 | -1 | -2 | -7 | -2 | -1 |
| no_levels_body | 19 | -4 | -86 | -52 | -29 | -18 | -63 | -35 | -8 |
| no_levels_wick | 25 | 1 | -33 | -27 | -12 | -14 | -40 | -14 | -2 |
| no_time_body | 3 | -1 | -18 | -7 | -3 | -1 | -14 | -7 | -2 |
| no_time_wick | 3 | 0 | -6 | -4 | -1 | -2 | -7 | -2 | -1 |
| no_trend_body | -68 | -63 | 21 | -3 | 9 | 36 | 24 | -13 | -25 |
| no_trend_wick | -68 | -62 | 26 | -1 | 12 | 40 | 25 | -12 | -24 |
| no_width_body | 2 | -1 | -18 | -7 | -3 | -1 | -14 | -7 | -2 |
| no_width_wick | 3 | 0 | -6 | -4 | -1 | -2 | -7 | -2 | -1 |

## 分かっている限り
- 【事実】`no_width` と `no_time` は `full` とほぼ同じ: 持ち高が違う足は全 3,983,118 本のうち 1,069 本と 1,066 本(`full_body` との比較)。幅の門(150 円 ÷ 2019-09-04 の値段)と時間で出る(40 分)は、この期間ではほとんど効いていない。保有の中央値は 2 分。
- 区切りの同一性の照合【事実】: `full_body`・`follow_wick`・`no_trend_body` の 3 変種で、2018 年の 1 年(足 521,307 本・決定 520,293)を一度に読んだ結果と月の区切り 11 か所でつないだ結果を比べ、3 本とも持ち高の食い違い 0(`exposure_identical: true`)。コマンド `run_b2.py --card c4 --variant <変種> --check --start 2018-01-01T00:00:00Z --end 2019-01-01T00:00:00Z`、出力 `measure/check_c4_<変種>.json`。ほかの 11 変種・ほかの年・本番の暦年の境の区切りは確かめていない。
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
