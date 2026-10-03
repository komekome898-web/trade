# カード 9 (a) 全期間の走らせの出力の台帳(2023-06-25〜2024-10-14、Binance COIN-M)

元の置き場: `data/c9_run_a/full_20230625_20241014/`(`.gitignore` の `data/` で git の外)。結果の文書は `RESULTS.md`。
表はすべて `make_tables.py --section manifest` の出力をそのまま埋めた(sha256 は hashlib、行数は gzip を開いて数えた)。

- `run_a/` に写したもの: 委任文の一覧どおり `dist_*.csv`・`label_counts.csv`・`policy_*_counts.csv`・`three_way_calibration.csv`・`three_way_model.json`・`run_meta.json`。
- 写していないもの: 委任文で「写さない」とされた大きい gz(`anchors_prints`・`controls`・`policy_cascades`・`policy_legs`・`jev_states`)。
- **委任文の一覧に名指しの無い 2 つ**: `anchors_bundles.csv.gz` と `three_way_probs.csv.gz`(どちらも `.csv.gz`)。「写す」一覧の `three_way_*.csv/json` に `.csv.gz` が入るかは書かれていないので、写さずに下の表に載せた(作業者の判断。写すかはリードが決める)。
- `chunks/`(日ごとの途中の出力)は載せていない(第 2 稿の `make_tables.py` は `chunks/scurve` と `chunks/controls` の見出しを読む)。
- 第 2 稿の `control_iv.py` の出力 `run_a/control_iv_out/`、第 3 稿の `control_ivh.py` の出力 `run_a/control_ivh_out/`(対照 (iv-h)・起点の版・(iv) の取れなかった原因)と `three_way_m.py` の出力 `run_a/three_way_m_out/`(3 択の作り直し)、第 4 稿の `control_iv_days.py` の出力 `run_a/control_iv_days_out/` と `three_way_m_policy.py` の出力(`three_way_m_out/` の `policy_*_3m*`)は、リードの指示で `run_a/` に置いた。sha256 と行数は表 manifest_iv。
- t8 の元の `chunks/scurve/*.npz`(走らせの途中の出力。git の外)の sha256 と点の数は表 manifest_scurve(2 回目の監査の聞く 22。リードが受け入れた)。
- 走らせの記録 `data/c9_run_a/full.log` は一つ上の置き場にあるので、別の表(manifest_log)に載せた。
- 行数は、gzip を開いて数えた物理行と、別の出所(`run_meta.json`・`dist_policy.csv`)の数を表 manifest_check で突き合わせた。

再現:

```
PYTHONPATH=src python3 docs/RESEARCH/cards/c9_liquidation_cascade/run_a/make_tables.py \
    --in data/c9_run_a/full_20230625_20241014 --iv docs/RESEARCH/cards/c9_liquidation_cascade/run_a/control_iv_out --section manifest
```

<!-- BLOCK:manifest -->
出所: `data/c9_run_a/full_20230625_20241014/` の直下(`chunks/` を除く)のファイルを `sha256`(hashlib)と行数(gzip を開いて数えた)で並べた

| ファイル | バイト | sha256 | 行数 | 数え方 | run_a/ に写したか |
|---|---|---|---|---|---|
| anchors_bundles.csv.gz | 778319 | e8a8f1926b68c3384f272a06e5da6a601f5b640f932bb3aff863feaadf59c8ff | 65204 | 見出しを除いた行数 | 写していない |
| anchors_prints.csv.gz | 20073630 | de55cf9191a88befb59168139a1ee52e346189b2ed8e46fdb6c1345873289878 | 53398 | 見出しを除いた行数 | 写していない |
| controls.csv.gz | 35054264 | 84f85106ad87433f37a666708b704a89581c1994a8c0604ffdec2bcf934c82c0 | 158658 | 見出しを除いた行数 | 写していない |
| dist_policy.csv | 139391 | 7014430cfae7d331f7d91687b8da6f09a40c6299bd6c046a3d924bf3d8255326 | 504 | 見出しを除いた行数 | 写した |
| dist_reaction.csv | 248211 | 3431f0a54b5dc27d2f55380c3ebf384917024a09320c6220f548f7989d48362a | 1200 | 見出しを除いた行数 | 写した |
| dist_s_curve.csv | 1127504 | a52a195ac048f0d07ab2a2d62daa05449a907b37ae717266e52f3d95e4142ce1 | 4320 | 見出しを除いた行数 | 写した |
| dist_size_split.csv | 125082 | c3155d2863a6c0e51e3694f6487d29520109638483fc35de36fa56e0a262a190 | 540 | 見出しを除いた行数 | 写した |
| jev_states.jsonl.gz | 5765227 | e0240e0d22d0acca28af832f47f2d8f8fc975ac3e9fb1ab3fcc08d93d5a0b131 | 53398 | 行数(1 行 = 1 プリント) | 写していない |
| label_counts.csv | 140 | 7b3e03a26b1852ee4ef6ad69f772a7a32ed549e3b1e65731b7fa6a06967f2df3 | 3 | 見出しを除いた行数 | 写した |
| policy_action_counts.csv | 7428 | 41b5f549deda1a8154de20fc32bdb216c1f8aabbbaa5ab65838c9826996cfc0d | 178 | 見出しを除いた行数 | 写した |
| policy_cascades.csv.gz | 6926179 | 657ae5b41a53c530761d0de6571fb617892fd532b1e2e092e9f0df1141202d5b | 932372 | 見出しを除いた行数 | 写していない |
| policy_judge_counts.csv | 4478 | 6e9d4cef8c03f845a63da47daf734d4d51be1d8c11bbc3dec210fd2101829630 | 120 | 見出しを除いた行数 | 写した |
| policy_legs.csv.gz | 7450456 | 8b00c84b421efb9157058797872374c3bbfabca22dd2761ad4b38dbc659e503b | 1108974 | 見出しを除いた行数 | 写していない |
| run_meta.json | 88537 | 0852ebb6aa59584442aecea0cb738fec73bff4762dea38206637e2dc6cc69fe2 | - | json(行の表ではない) | 写した |
| three_way_calibration.csv | 5030 | ec6bfe77650b70d02b76495a56f156cfed1912812b00a87440dc43d59450dcbd | 73 | 見出しを除いた行数 | 写した |
| three_way_model.json | 2889 | 040156da8e649e2b9b43a3eb02bf59ee098ba9e69e6feaa7181c6fe0df523ceb | - | json(行の表ではない) | 写した |
| three_way_probs.csv.gz | 493054 | 3caa139aeef54354e46b2c0be839a5c6a32ad2c6b749b77122b02d3b627e852c | 53398 | 見出しを除いた行数 | 写していない |
<!-- /BLOCK -->

<!-- BLOCK:manifest_copy -->
出所: 同じ台本で、元と `run_a/` の写しの sha256 を比べた

| ファイル | 元の sha256 | run_a/ の sha256 | 一致 |
|---|---|---|---|
| dist_policy.csv | 7014430cfae7d331f7d91687b8da6f09a40c6299bd6c046a3d924bf3d8255326 | 7014430cfae7d331f7d91687b8da6f09a40c6299bd6c046a3d924bf3d8255326 | 1 |
| dist_reaction.csv | 3431f0a54b5dc27d2f55380c3ebf384917024a09320c6220f548f7989d48362a | 3431f0a54b5dc27d2f55380c3ebf384917024a09320c6220f548f7989d48362a | 1 |
| dist_s_curve.csv | a52a195ac048f0d07ab2a2d62daa05449a907b37ae717266e52f3d95e4142ce1 | a52a195ac048f0d07ab2a2d62daa05449a907b37ae717266e52f3d95e4142ce1 | 1 |
| dist_size_split.csv | c3155d2863a6c0e51e3694f6487d29520109638483fc35de36fa56e0a262a190 | c3155d2863a6c0e51e3694f6487d29520109638483fc35de36fa56e0a262a190 | 1 |
| label_counts.csv | 7b3e03a26b1852ee4ef6ad69f772a7a32ed549e3b1e65731b7fa6a06967f2df3 | 7b3e03a26b1852ee4ef6ad69f772a7a32ed549e3b1e65731b7fa6a06967f2df3 | 1 |
| policy_action_counts.csv | 41b5f549deda1a8154de20fc32bdb216c1f8aabbbaa5ab65838c9826996cfc0d | 41b5f549deda1a8154de20fc32bdb216c1f8aabbbaa5ab65838c9826996cfc0d | 1 |
| policy_judge_counts.csv | 6e9d4cef8c03f845a63da47daf734d4d51be1d8c11bbc3dec210fd2101829630 | 6e9d4cef8c03f845a63da47daf734d4d51be1d8c11bbc3dec210fd2101829630 | 1 |
| three_way_calibration.csv | ec6bfe77650b70d02b76495a56f156cfed1912812b00a87440dc43d59450dcbd | ec6bfe77650b70d02b76495a56f156cfed1912812b00a87440dc43d59450dcbd | 1 |
| three_way_model.json | 040156da8e649e2b9b43a3eb02bf59ee098ba9e69e6feaa7181c6fe0df523ceb | 040156da8e649e2b9b43a3eb02bf59ee098ba9e69e6feaa7181c6fe0df523ceb | 1 |
| run_meta.json | 0852ebb6aa59584442aecea0cb738fec73bff4762dea38206637e2dc6cc69fe2 | 0852ebb6aa59584442aecea0cb738fec73bff4762dea38206637e2dc6cc69fe2 | 1 |
<!-- /BLOCK -->

<!-- BLOCK:manifest_check -->
出所: 上の表の行数と、別の出所(右端)から数えた数を並べた

| ファイル | 上の表の行数 | 別の出所の数 | 一致 | 別の出所 |
|---|---|---|---|---|
| anchors_prints.csv.gz | 53398 | 53398 | 1 | run_meta 一意化.一意 |
| jev_states.jsonl.gz | 53398 | 53398 | 1 | run_meta 一意化.一意 |
| three_way_probs.csv.gz | 53398 | 53398 | 1 | run_meta 一意化.一意 |
| controls.csv.gz | 158658 | 158658 | 1 | run_meta 対照の取れた数 の 取れた の和 |
| anchors_bundles.csv.gz | 65204 | 65204 | 1 | run_meta 束の数 の和 |
| policy_cascades.csv.gz | 932372 | 932372 | 1 | dist_policy.csv 単位 = 連鎖1本(入らないを0で含める) の 連鎖の数 の和 |
| policy_legs.csv.gz | 1108974 | 1108974 | 1 | dist_policy.csv 単位 = 1レグ の n + n_nan の和 |
<!-- /BLOCK -->

<!-- BLOCK:manifest_iv -->
出所: 第 2 稿・第 3 稿の追加の計算の出力(`control_iv.py`・`control_ivh.py`・`three_way_m.py`)

| ファイル | バイト | sha256 | 行数 | 数え方 |
|---|---|---|---|---|
| run_a/control_iv_out/control_iv_meta.json | 3126 | c65105aee629e59d835c62cf27aae3fc82464bf152132d3ccf06254e1b753de1 | - | json(行の表ではない) |
| run_a/control_iv_out/controls_iv.csv.gz | 4531456 | daded3273823226dd232daaa65dfed9c4b5ae29107293f0582a4901084538cbf | 16968 | 見出しを除いた行数 |
| run_a/control_iv_out/ii_reproduction.csv.gz | 1423248 | 593ec4b2c452d1784ad4228765f58613578c398eb92323237dfd86690af7843f | 53398 | 見出しを除いた行数 |
| run_a/control_iv_out/prints_reanchor.csv.gz | 10005668 | 4a3444d1774ea43749787c95b1d25bb0d5915bf25566097851794d1702423663 | 53398 | 見出しを除いた行数 |
| run_a/control_ivh_out/control_ivh_meta.json | 304 | cf7ba7a43a897ebf6c9c69c2a2df4add370ade684134f02441335f1ea4222ab1 | - | json(行の表ではない) |
| run_a/control_ivh_out/controls_iv_versions.csv.gz | 2543319 | 60564d4c25c49d8ec68f2c15b7522359d1ef8cdfcfe91612f934a9977d22fe5a | 16968 | 見出しを除いた行数 |
| run_a/control_ivh_out/controls_ivh.csv.gz | 2280874 | e78276fd0fe280b7202d48cb40d0dcbf0612f30d8537233562d2f9b826d3c484 | 6222 | 見出しを除いた行数 |
| run_a/control_ivh_out/iv_unmatched_cause.csv.gz | 117838 | b29153f3cd3424f67f9740f0d4b5e80a853befc58b06379c4e4c3720c7978fae | 36430 | 見出しを除いた行数 |
| run_a/control_ivh_out/prints_versions.csv.gz | 9616982 | c119caab02972564d7c713a6c04f41e768e2b0de9cc4bb9718d0ca68b52a8ed3 | 53398 | 見出しを除いた行数 |
| run_a/three_way_m_out/policy_3m_meta.json | 7208 | aecc71b69005ef20b4393e2cd6179bd68d148c625346b01630e8b6ac2fba50ad | - | json(行の表ではない) |
| run_a/three_way_m_out/policy_3m_meta_oldcheck.json | 8036 | 51e431543fb9246f8c6dd5706cb0d2682e70737a6feb5a0db4563aafca2da531 | - | json(行の表ではない) |
| run_a/three_way_m_out/policy_cascades_3m.csv.gz | 1227302 | dec915846196d82b62263f858f682f662e0134d6d39fc12389099e10c548cee3 | 149924 | 見出しを除いた行数 |
| run_a/three_way_m_out/policy_cascades_3m_oldcheck.csv.gz | 23080 | a3d17fa181da024896d866f9758fcfba1fcac7c7b862df76d84793525dec29cb | 2756 | 見出しを除いた行数 |
| run_a/three_way_m_out/policy_legs_3m.csv.gz | 1211089 | 0a0353e566e08aee06be9970e452cf42b57c1f9777230a15a4991c984524f014 | 160022 | 見出しを除いた行数 |
| run_a/three_way_m_out/policy_legs_3m_oldcheck.csv.gz | 25461 | 87225e4318f9929ec07714593f99be20a3ac7b70a5539c9d93f952a5efb7ae99 | 3236 | 見出しを除いた行数 |
| run_a/three_way_m_out/three_way_m_calibration.csv | 5198 | 1ef63cfae6f28c9999780dc8ca36ca813bcd6d708c0da9704e96ae5def43d67e | 75 | 見出しを除いた行数 |
| run_a/three_way_m_out/three_way_m_model.json | 3235 | 0592c76dcf67f13239b7ec2959a1957e4ef1a75de3ffb8ff43ae029000283310 | - | json(行の表ではない) |
| run_a/three_way_m_out/three_way_m_probs.csv.gz | 494955 | b57e849d59e009fa723c4418749bf36b4b41608fa90386b19599f987163e3226 | 53398 | 見出しを除いた行数 |
| run_a/control_iv_days_out/control_iv_days_meta.json | 325 | c8e6fa3d3b0c7e5615d66b6983f1c39bf279ccc185c4b051228da563d99c81d6 | - | json(行の表ではない) |
| run_a/control_iv_days_out/controls_iv_d0.csv.gz | 2449270 | d469ee204b0eff28c4928d155008f3b057a80b43547a3193bc1f1c5d8072913b | 10067 | 見出しを除いた行数 |
| run_a/control_iv_days_out/controls_iv_d7.csv.gz | 4834871 | c6b786c8906ac65af04248204586682e586840fef54d8535a1704d6469a0f164 | 19471 | 見出しを除いた行数 |
| run_a/control_iv_days_out/grid_band_noliq.csv | 345 | 4cf6a2b50bfea933e870f75ed545c0a4020d76fda51b8828c1120666c715f642 | 10 | 見出しを除いた行数 |
| run_a/control_iv_days_out/ivh_unmatched_cause.csv.gz | 127226 | c9a29ea1d506d45a37c08ae47c65432bbe189796d34e8190415d0a5f92bc79eb | 47176 | 見出しを除いた行数 |
<!-- /BLOCK -->

<!-- BLOCK:manifest_scurve -->
出所: `data/c9_run_a/full_20230625_20241014/chunks/scurve/`(t8 の元。監査の聞く 22 で載せた)

| ファイル | バイト | sha256 | 点の数(s の長さ) | 列(遅れ × h) |
|---|---|---|---|---|
| 合計 478 ファイル | 386997590 |  | 3946565 |  |
| chunks/scurve/2023-06-25.npz | 695114 | 9c86f6ace48138e1c114d842c3a38038ab97316f7bb6800ee383fd996c72d0e6 | 7088 | 24 |
| chunks/scurve/2023-06-26.npz | 798994 | 771742012621ad7d97c324b1d3f89e2883a153a5e1bed39409517f9eadb2547b | 8148 | 24 |
| chunks/scurve/2023-06-27.npz | 651504 | 8609627fdabf6c5ebb91e79be0f723a201fb509aaa6c14c87b0fc13d645e853d | 6643 | 24 |
| chunks/scurve/2023-06-28.npz | 763812 | fb09dbb734bdd32c5c01f07b542203ace33ebf8ca5351d2da83d9566613cdde2 | 7789 | 24 |
| chunks/scurve/2023-06-29.npz | 566636 | 569c89651eb8468c558bc8dd68e92f24b395055678b6497a5b3ffd30efd09e61 | 5777 | 24 |
| chunks/scurve/2023-06-30.npz | 1204224 | 3ac729b726e404830e367ae91a4deff52e00722d567985da439dbadf2f1f0a3b | 12283 | 24 |
| chunks/scurve/2023-07-01.npz | 133966 | 4e204db050072ed9d86559da9bc3f79161cfa097b750feabd8e3e6b2eb93a5aa | 1362 | 24 |
| chunks/scurve/2023-07-02.npz | 258720 | c0045ab1a90a10a518ad4614fe2403ba00ecf08ca39cf641e72c0b45d81625fb | 2635 | 24 |
| chunks/scurve/2023-07-03.npz | 630924 | 9de753d8285656027f4074a1a632380a1c8a3b71f18e41bc7177ad42ab484a62 | 6433 | 24 |
| chunks/scurve/2023-07-04.npz | 418460 | 5e921fdd54e0a5c8725519d95bcb564fa41e0d4740ad18bf0db29f6f45d303c2 | 4265 | 24 |
| chunks/scurve/2023-07-05.npz | 493136 | f93f28b839a96adad1873c802eebd010305fb08437724b1360be92f471311176 | 5027 | 24 |
| chunks/scurve/2023-07-06.npz | 1228822 | b818cc43148a7b0a35f40f0b2c305ceddcf1edd07b0f0ebff9b36fda5cebeb42 | 12534 | 24 |
| chunks/scurve/2023-07-07.npz | 428652 | af25118ef7bb0ff8069e0db472122306868cc6aacb8d2ceca65df0a7e3a3c316 | 4369 | 24 |
| chunks/scurve/2023-07-08.npz | 132986 | fa90805343d9765af05a7a6b047843ba179ba177d7f2877e65f346240b50176a | 1352 | 24 |
| chunks/scurve/2023-07-09.npz | 209720 | 423d83d0e154b5093483524ee743a83816e4019a59732717e6c4cae96a790d2e | 2135 | 24 |
| chunks/scurve/2023-07-10.npz | 845838 | 56ae85b84f9b429bc2e1368e7e4b6fb3dc3c25c8ef5e067d61455b6c26bdbd16 | 8626 | 24 |
| chunks/scurve/2023-07-11.npz | 489412 | cfbee6b862c27e894e1bc8501ff3dfec15e8875b16a295cfde0633df53182d80 | 4989 | 24 |
| chunks/scurve/2023-07-12.npz | 552524 | 3c6e6d251823359ffe6d47fd74ab710bfae03285c797e47f2d3488fd53add921 | 5633 | 24 |
| chunks/scurve/2023-07-13.npz | 890918 | 0094ea66291671cfdb9a868188ffe6c9d6583296b741fdc1d011eb45b3f04f5b | 9086 | 24 |
| chunks/scurve/2023-07-14.npz | 764204 | 24929d1850d4107a3164d45b86435e87af799434f9ffa8eda33b08d36a1b7b87 | 7793 | 24 |
| chunks/scurve/2023-07-15.npz | 18130 | bcd504a4648af65db807954d34460e38a0e234b3689d101dd7846504fbcc9440 | 180 | 24 |
| chunks/scurve/2023-07-16.npz | 243040 | 35a505b0e87feed6121ddbbc419ceb14be9eae2084e277543b038780c5033121 | 2475 | 24 |
| chunks/scurve/2023-07-17.npz | 553504 | b1aab28c18666d4e87862a4eb2d668da0ce81a5a0553cf18e9dd67b64b25caed | 5643 | 24 |
| chunks/scurve/2023-07-18.npz | 519890 | 90b3923a08f43d9134b0092480ad5c1259141ae7abeefb1e83d93a4a0cac89f4 | 5300 | 24 |
| chunks/scurve/2023-07-19.npz | 542038 | 38d9702fd2ed7b93e7fdf4777e2c5daede4ee13476b0661bcc32b3e2a3c1a470 | 5526 | 24 |
| chunks/scurve/2023-07-20.npz | 619164 | 5cf05c5cc0f46a8367cb3ccac43f9f21ba38ef1bc5cb8ad67d389a1b436e044d | 6313 | 24 |
| chunks/scurve/2023-07-21.npz | 269598 | 05e66e9c7200dbd8a7a088512d20d4baf42f754b8b08d1ea6c5142dc4b60b58c | 2746 | 24 |
| chunks/scurve/2023-07-22.npz | 162092 | 345ed1c7685a871d56010da6b76c090f300cb07a8dc4da7aa1bb97d4acdceb2a | 1649 | 24 |
| chunks/scurve/2023-07-23.npz | 249312 | 16ee1d0c53f2a158ab4edcdfa04eba4040eb704272b83193f3c44795af9fe627 | 2539 | 24 |
| chunks/scurve/2023-07-24.npz | 758814 | f9424ba7460bf33061b511c9bc6b4eda5cb8365aa5547ddce2a10d3e0c2ec651 | 7738 | 24 |
| chunks/scurve/2023-07-25.npz | 275870 | cf5876299118c599543b2285ab6e4f1fdadb93878116cf1ccd7dd8ead771320e | 2810 | 24 |
| chunks/scurve/2023-07-26.npz | 404936 | 5943a3687b9813bcc38fdf2d1632a2442c8c6bd94b8c2fb313fff0db28c9660e | 4127 | 24 |
| chunks/scurve/2023-07-27.npz | 289394 | 7c342cef3e1146a276c5a6a26af241a3354138dfdae070adf36d40844eb19934 | 2948 | 24 |
| chunks/scurve/2023-07-28.npz | 342216 | c0a23dbeb3513c5b34c995c5c3cc57e5d1c91dca75f7f7564008acb562a4828c | 3487 | 24 |
| chunks/scurve/2023-07-29.npz | 72716 | d87013bdc7c44e25bb1ba88651504de4a58db4512864a4be750d4f89f9f45df1 | 737 | 24 |
| chunks/scurve/2023-07-30.npz | 126224 | 40edc2cb5e5dcb5648dda554503accde2f3901f16605cb44e4b6c8fe294c9edb | 1283 | 24 |
| chunks/scurve/2023-07-31.npz | 279496 | 7fc1c6f65e0f4fb3ddf381693d5c4b510153e721fe665ff7b39e5f98b500bec2 | 2847 | 24 |
| chunks/scurve/2023-08-01.npz | 673358 | e65658224b4e7f1df49fc79b20cf66cdf4027792fde822501acc252a700a184e | 6866 | 24 |
| chunks/scurve/2023-08-02.npz | 889350 | a7ff66e8a7e62265df226713b10715cf6909e6fb9e2c893e01a5461c886f5fd2 | 9070 | 24 |
| chunks/scurve/2023-08-03.npz | 332710 | 11c20eac7166af238ab3a9910322a6954bd0a6d7bacd837b0f7100704d9b9e48 | 3390 | 24 |
| chunks/scurve/2023-08-04.npz | 254604 | ea944ebedf1fa70f4415ca3da7f5fc0bdfe67fdc13108552f440cfecf66c8a2e | 2593 | 24 |
| chunks/scurve/2023-08-05.npz | 35770 | 95bfd1eac0aeeca604cf4b61ad4876147a9c801eef187aff124db0914aa0b492 | 360 | 24 |
| chunks/scurve/2023-08-06.npz | 132202 | 1aaec672750f91de18ef0ce85158a2dfd95c717cc5a6b01ed74b9c03a8fd80a1 | 1344 | 24 |
| chunks/scurve/2023-08-07.npz | 459032 | 41f99588d586a78c0df7292fe12c461191ebf8a5c550b3ccf17a5781c067c944 | 4679 | 24 |
| chunks/scurve/2023-08-08.npz | 838194 | 9a8a3911ea044abfde904614694383965765b677c36001ca78987d06d46ed4be | 8548 | 24 |
| chunks/scurve/2023-08-09.npz | 608090 | db5d51a8b1aafff7ba322c174d32647752c09c8ae1df2363eb846a60ee2c0150 | 6200 | 24 |
| chunks/scurve/2023-08-10.npz | 253330 | 01ac17cae93ba4daa25f014bb295e5cf4286139e4484db37b45e1170932b6f06 | 2580 | 24 |
| chunks/scurve/2023-08-11.npz | 94472 | 46d3ebdd87dd635a4b56d187423c5b2b115248a965d39d1d49b0a905f81acc49 | 959 | 24 |
| chunks/scurve/2023-08-12.npz | 18130 | a0888eec263c9d0a1f60dee917536b52b54255960565a935bc77053f4b12664a | 180 | 24 |
| chunks/scurve/2023-08-13.npz | 139454 | 4272cb2c25e86ecbe86ae5bbbadf73995c2825381974d3264938f845fc126d81 | 1418 | 24 |
| chunks/scurve/2023-08-14.npz | 496860 | 3fe3111c113b46e9686889541701ce9cfedaa5374464faa1cb798fee6451450b | 5065 | 24 |
| chunks/scurve/2023-08-15.npz | 176694 | c9a20e451cbe8ffe3e1c8487745936ab14c3a87d4b99d595b225566df1fdc5e1 | 1798 | 24 |
| chunks/scurve/2023-08-16.npz | 386022 | 6a693d4a7d5f0574290e4da9b704674a7f948458be9f179868411d6ff130215e | 3934 | 24 |
| chunks/scurve/2023-08-17.npz | 1635228 | 84c64307c2ad30e1b5a80027b859426c2a3a8d61641ab809e79c9f504082a0c3 | 16681 | 24 |
| chunks/scurve/2023-08-18.npz | 1492834 | b71b034c3c6a9488acfb402d03a89436b0aa2f26e7eaa54bef36b5192bf6e6f7 | 15228 | 24 |
| chunks/scurve/2023-08-19.npz | 383964 | 07832a90f4862dc49bb50206f984c604d137490815837331eb655ffe40cbff4c | 3913 | 24 |
| chunks/scurve/2023-08-20.npz | 224518 | 42e024a06a55c85d49bfba6b71ce96159e8b72e5d3df6c72dbc89c3e1afaa85b | 2286 | 24 |
| chunks/scurve/2023-08-21.npz | 444920 | 2f1c9868c1f04c9437a0c62ae49972c35eb1bd840f6d38821bb0aa294c588471 | 4535 | 24 |
| chunks/scurve/2023-08-22.npz | 632884 | 17cf620ee56bc5965f4079099012a5d45de5036c5ddc92198a9a25e884f0fd42 | 6453 | 24 |
| chunks/scurve/2023-08-23.npz | 816732 | b555f3357da28edae42e01e4a49b4463c0a667fc342e240db787847e736dbd98 | 8329 | 24 |
| chunks/scurve/2023-08-24.npz | 546056 | 23dc8a48fca10cb7353a4ebc3c43a4d366072135e006ef9b253c03265ad695d8 | 5567 | 24 |
| chunks/scurve/2023-08-25.npz | 474320 | 985fd374a1b1b4754ff552aaa8384698da049c5d022258d6b138c40b1bd0dddc | 4835 | 24 |
| chunks/scurve/2023-08-26.npz | 35770 | 4da2ae9f3df3c0725ef4bbd43ea0b35ba0c21ae2a4006d5f4ebc6f45c532552c | 360 | 24 |
| chunks/scurve/2023-08-27.npz | 104762 | d2bf364c85f75b6bde224baff85c16126c87a1912da1739cc69703c8c6dd0017 | 1064 | 24 |
| chunks/scurve/2023-08-28.npz | 226478 | 46eaef90f086b081331fe76c7261a9ec205571c2e2d90f3d338ce365186de235 | 2306 | 24 |
| chunks/scurve/2023-08-29.npz | 983724 | 5b1567fee63f1b59e668e00827d623cbcee35f324d2e6978d8e5bc3af718477c | 10033 | 24 |
| chunks/scurve/2023-08-30.npz | 582316 | 7db069095c02f36f12dc45212350b9f6331a950cab4274b091a34fc8b12becf6 | 5937 | 24 |
| chunks/scurve/2023-08-31.npz | 699132 | b8432b19fd3790a0aca038bb487ce28761fe5f9b060f4b111b06c2bb28a94b7a | 7129 | 24 |
| chunks/scurve/2023-09-01.npz | 524300 | cb8710715892c8f9bbaca6e4a5b865806720e410690b1f568ca0cf9eba52082d | 5345 | 24 |
| chunks/scurve/2023-09-02.npz | 159348 | 7c252b0e31935176ec396d26c727774db9357e28954b76d0a09475ec989cd2fc | 1621 | 24 |
| chunks/scurve/2023-09-03.npz | 221970 | 8cd2aa1b9510003aa6598ab5c1472432bd88975e6c6891cb78c4049b39f59fd3 | 2260 | 24 |
| chunks/scurve/2023-09-04.npz | 345940 | 7d9b419f88bd5bc9d7fc16a31424cdf746fdbc471835796a27f7feef6f726261 | 3525 | 24 |
| chunks/scurve/2023-09-05.npz | 307328 | 033dd084b4801873590e11d1cbe7fbf3a5496b2e82297c14ac965a07d4006e0d | 3131 | 24 |
| chunks/scurve/2023-09-06.npz | 412286 | 6aed45825bd80a024fae0275ca733745045c0d8fc11c1e506da672f553ca2c50 | 4202 | 24 |
| chunks/scurve/2023-09-07.npz | 583884 | e82694d4d9837afb560c644634561e89818343e53907e2dac52f278b205bfe87 | 5953 | 24 |
| chunks/scurve/2023-09-08.npz | 399056 | 55276aab01bae60929ee37e2c8c79368b95b51ccf39871bbb61dc23177dffc76 | 4067 | 24 |
| chunks/scurve/2023-09-09.npz | 490 | 58f3fffe7b29de83e1f4024b49b79343800a3e43a9c55b2752bec2db40e6457c | 0 | 24 |
| chunks/scurve/2023-09-10.npz | 189532 | 50f5e9910dd1c5fb034b0d65f39bb04c46a34bdc5345ae35918cf7e74ce87e42 | 1929 | 24 |
| chunks/scurve/2023-09-11.npz | 574280 | 5305f54ef0f792710b09a19bdea87e74c1e3e3591b0b1af5949cabed6d1daa1c | 5855 | 24 |
| chunks/scurve/2023-09-12.npz | 773514 | 4e5ca791ead88c3a4d5a0240f5b1574ecd7fab308e17b9d9aecb22c530982f80 | 7888 | 24 |
| chunks/scurve/2023-09-13.npz | 445998 | ddbc7916767edc34d1a4701aa3b6d98be0c4d8973d53061aee8ec3c6b5953f4e | 4546 | 24 |
| chunks/scurve/2023-09-14.npz | 568694 | 6bad7eee7b7f8f774ded5e7b883e86471b98cb7f323be0e5cc5056a3bc946581 | 5798 | 24 |
| chunks/scurve/2023-09-15.npz | 561344 | 5e411660e858778e1584cdd258d9cd6a5687301ef6a901aa0dbc9fea5adf540f | 5723 | 24 |
| chunks/scurve/2023-09-16.npz | 161896 | 7c5bcc520997e6dc365cef3b385718b14df5bd1fa334cdd9cd796c290bbe55ce | 1647 | 24 |
| chunks/scurve/2023-09-17.npz | 169638 | 4f8a4e2d3f2f2ea4ca1c696a2b317d789917f851d1878d4e6e86faa484367ddb | 1726 | 24 |
| chunks/scurve/2023-09-18.npz | 1014104 | 2ab810fbbcf4dcccfe250198166e3020dfcf3c40be1e73082a59b8bf1cc7cac7 | 10343 | 24 |
| chunks/scurve/2023-09-19.npz | 975100 | 24f911dd26623f58a0ebca9d62d652a3e18e28b0b776f6501de8238616334e8a | 9945 | 24 |
| chunks/scurve/2023-09-20.npz | 659638 | e75fc26d214b22059d4d7617ca0efe5722ef9f7e9e483296a1cc5a4d9fbd047b | 6726 | 24 |
| chunks/scurve/2023-09-21.npz | 701092 | 15a2274d6eb7fd5b674286bd335777e1f14008ba930e3ea6b00483b82b549b0f | 7149 | 24 |
| chunks/scurve/2023-09-22.npz | 214522 | c90e02e37052b6c0d74f74be96b460c08bd5ab6a42d31287a7d1ee43c3a744db | 2184 | 24 |
| chunks/scurve/2023-09-23.npz | 490 | 58f3fffe7b29de83e1f4024b49b79343800a3e43a9c55b2752bec2db40e6457c | 0 | 24 |
| chunks/scurve/2023-09-24.npz | 198254 | 3d024f60b9ec632e6068bbaa0526a5132453e0280c429425daf7096d52570c58 | 2018 | 24 |
| chunks/scurve/2023-09-25.npz | 490 | 58f3fffe7b29de83e1f4024b49b79343800a3e43a9c55b2752bec2db40e6457c | 0 | 24 |
| chunks/scurve/2023-09-26.npz | 331926 | 9bd2369a07faf8a0d4665d15155b9b03d6af04467c278bb3375556692816f698 | 3382 | 24 |
| chunks/scurve/2023-09-27.npz | 667380 | 1137dbdcaa8ffc8bbcf6d1be200817c64728ae3a80163b0a8f6727d69a523750 | 6805 | 24 |
| chunks/scurve/2023-09-28.npz | 745584 | fec6e25b6788559f6a08b2a6014260e03b35fd8727766da516e9074cd783c7ed | 7603 | 24 |
| chunks/scurve/2023-09-29.npz | 545860 | 6b7592c519fb14c8925e64c28dc310ffba7f935e341fd9a9c9a481cca30f179d | 5565 | 24 |
| chunks/scurve/2023-09-30.npz | 93198 | e6322bde623c1d561c18ea3e840bac39987aad794ee78413217470a11c519dc3 | 946 | 24 |
| chunks/scurve/2023-10-01.npz | 360542 | 2d13b47af8235affbf1c3ee89c8032954f0ad67d67702bdc7198c0e70fc88f87 | 3674 | 24 |
| chunks/scurve/2023-10-02.npz | 1070062 | 5998eec171f334f595a315d32c264ad19d3484317d224eba4e53dd6604451473 | 10914 | 24 |
| chunks/scurve/2023-10-03.npz | 552328 | 8c97a6c920d926baa069e6adac7bc363bb5ba5dc1897532f57e4ef9c7963bded | 5631 | 24 |
| chunks/scurve/2023-10-04.npz | 421988 | 13cfdc7d12915e75d71a94a3c01ca6fb380ca7c940129c250cc6679c06910316 | 4301 | 24 |
| chunks/scurve/2023-10-05.npz | 584080 | e7e4522a9adec6ebd901be928ae8fb974d061c63d5ab7cdbd2bc59a8041c1333 | 5955 | 24 |
| chunks/scurve/2023-10-06.npz | 677376 | d0c63138d636a1faeb32420babf9daec23e56b1d53d4a231e93f27f943496550 | 6907 | 24 |
| chunks/scurve/2023-10-07.npz | 66444 | 7e7f3dd36a329c18d57b43a64fd087bd30929a60299de9f1e956a32fed2cb6bf | 673 | 24 |
| chunks/scurve/2023-10-08.npz | 389550 | a462a14a866622cd0d6db2267deadda297a8dceb1a559872d53015dfb33fea25 | 3970 | 24 |
| chunks/scurve/2023-10-09.npz | 600348 | 14b8bc1c0db5e679c2c0bea37699a82c419fc740c654e82d7fb8fbb8a57cfc7f | 6121 | 24 |
| chunks/scurve/2023-10-10.npz | 536844 | de73380ced2546d52633291d640a1a27420bb7f3cbc947da64719f67531a3078 | 5473 | 24 |
| chunks/scurve/2023-10-11.npz | 646702 | d071d4aac733217187d2335d6d16853fc6693853273496b79201fce092813f1c | 6594 | 24 |
| chunks/scurve/2023-10-12.npz | 283318 | 7a908d4f4423a0ca805e3d5cd9bd40a001d814ac4dfda6d7a006f29ddd01d235 | 2886 | 24 |
| chunks/scurve/2023-10-13.npz | 420812 | 28fbd889e315c7bea0963be0261798fcee84a770999692cd39317d96db17f52a | 4289 | 24 |
| chunks/scurve/2023-10-14.npz | 53018 | ddc7d686aadc31a42580c22661d13c3f424687b3e1ac1a802d5bc005485b0876 | 536 | 24 |
| chunks/scurve/2023-10-15.npz | 246862 | fa9605d3af657fd18c407b9fedf812f899c37b7d780de128319c87d7ba706487 | 2514 | 24 |
| chunks/scurve/2023-10-16.npz | 1217846 | 2b019482b6b1648e6abaa1b6dc22c7d6bc1dad4327dbd1ec233d7a022de05b2e | 12422 | 24 |
| chunks/scurve/2023-10-17.npz | 792526 | 9fd0fe71ae4a16216f62fbb3fae9e5b1bd95d9002ee21a674f366f330db29c90 | 8082 | 24 |
| chunks/scurve/2023-10-18.npz | 416402 | 2b3c46aa9a2c72ad2338c12f72cc10afdaa6ac1c98172a72063b5682366bc723 | 4244 | 24 |
| chunks/scurve/2023-10-19.npz | 601426 | 757a4f77a72a44e13b6d7d496ed525b29c18bff65d75991c2f6f9028df627cc0 | 6132 | 24 |
| chunks/scurve/2023-10-20.npz | 1222256 | c36e605582b86701efafeef76695ff221a2f4375f423c299cbfb83166dc0048d | 12467 | 24 |
| chunks/scurve/2023-10-21.npz | 552622 | 7f7f2bb7038ad1a076ec8711374b027649af62d2f2134a8a5d9643aed04c2052 | 5634 | 24 |
| chunks/scurve/2023-10-22.npz | 372498 | 32117120f4a9819307840d4f55456b9bb1448a69f348104c8807b5b0eb2f6551 | 3796 | 24 |
| chunks/scurve/2023-10-23.npz | 2091418 | 55c93f83d281376cebba10c77826b727cf88ca7ee3512a4d8858065cfa43bce8 | 21336 | 24 |
| chunks/scurve/2023-10-24.npz | 2588768 | f961d5df75208a603745aee3341db2df8cdcce3c8a62db61021e7df9752b8719 | 26411 | 24 |
| chunks/scurve/2023-10-25.npz | 1430506 | 8159a2bb2ef0637eda072c8535bf108d844e4b4ec5ccaef134f1a233ed22bc84 | 14592 | 24 |
| chunks/scurve/2023-10-26.npz | 1146208 | 45e18ee016dd4f1966dcc959f70de8450d26c65a50b11d71b442265e2200c857 | 11691 | 24 |
| chunks/scurve/2023-10-27.npz | 872788 | c73b50daad5139ca3f77f32272876524930f583ba63f3d29d472b89139691a4f | 8901 | 24 |
| chunks/scurve/2023-10-28.npz | 302526 | 758ed3345a4377b55edba6f04616d12e65b21332be004d70a2bb7da750554df7 | 3082 | 24 |
| chunks/scurve/2023-10-29.npz | 634256 | 535c30ba821e1e9da8fbd83bb5dad4d7f3c52580e27cf3dfde4d5bced505ba89 | 6467 | 24 |
| chunks/scurve/2023-10-30.npz | 596232 | 00d100ccd098e8e1194625db7f04cb73bb9e04fe8435b77d56812acb6b9f0b48 | 6079 | 24 |
| chunks/scurve/2023-10-31.npz | 769790 | 625dcb3f40391c5f095fc9497224a8183f518ee9eea317b014c81434aa271bea | 7850 | 24 |
| chunks/scurve/2023-11-01.npz | 990976 | 79ea146b8b558ccafe268c4a6ff027d41512f8cd5c1958b7d5b6c92206fe98fb | 10107 | 24 |
| chunks/scurve/2023-11-02.npz | 1036252 | 721c441d3b1441b952cc7a2a6f833ee7c816ab515df34d82ba07ec3cb82fce92 | 10569 | 24 |
| chunks/scurve/2023-11-03.npz | 950208 | a63e9dabadf1e85e67f71ed19b00b4cb7d87b70102db35aabd33d070076a945c | 9691 | 24 |
| chunks/scurve/2023-11-04.npz | 389452 | a687144f10f9666935eb8cff2279aaa67216da58067c37f9cc3e48725ea50c82 | 3969 | 24 |
| chunks/scurve/2023-11-05.npz | 562520 | 40d8cce6edc9af40b4037b0430c20868b10eb9d1cf48f0f338173accdcc8b11b | 5735 | 24 |
| chunks/scurve/2023-11-06.npz | 558698 | 145319da92983012b40448a3b226de1b6c8420cb302ce4e825a9852f6e1b9b38 | 5696 | 24 |
| chunks/scurve/2023-11-07.npz | 914046 | 057b3b02b9e291e8eb2e94bf0e5889dd69abba2991d37232d836d2b4de270b70 | 9322 | 24 |
| chunks/scurve/2023-11-08.npz | 645428 | debce80a348a181b3d779771fd16407c4aafb22ca07c923a884ea4f3418ab06f | 6581 | 24 |
| chunks/scurve/2023-11-09.npz | 1592500 | 0d90e7d76287a1e4b783fc391b0ab727d9cf714f2b4c24a81f12d3b08023d859 | 16245 | 24 |
| chunks/scurve/2023-11-10.npz | 1106420 | cc563a0c047453bac0a0469d01ed34a69e447a6134fe756de90ad7559a5f4ad5 | 11285 | 24 |
| chunks/scurve/2023-11-11.npz | 573692 | a6bf8b6a5053f4cb3f1a6834e563d4f4e31fd430e326175aa2ec514e7982aa98 | 5849 | 24 |
| chunks/scurve/2023-11-12.npz | 246862 | 43977dcbfa105aa099daacc96643f523a2be167a1bc635a0246779a3dd77140e | 2514 | 24 |
| chunks/scurve/2023-11-13.npz | 782432 | 2969b18506b45abe943f55c1c8d124fab66dfc57ed57a1ac45d447e0b14090a4 | 7979 | 24 |
| chunks/scurve/2023-11-14.npz | 1231664 | 1a80ac567885fad9901d977955b9f2f87e8f5f1b84b90a2e2bb63b7bf1a93662 | 12563 | 24 |
| chunks/scurve/2023-11-15.npz | 1270374 | 1c28932e9d73272dd22b2d04868c945153636ad4be740215fa13060e500c1714 | 12958 | 24 |
| chunks/scurve/2023-11-16.npz | 1492540 | 3c09c5ceae576d614bc60704b4a6567de084d28596d511018a3d9d8af7268fe9 | 15225 | 24 |
| chunks/scurve/2023-11-17.npz | 872788 | b84770657545be440091e45293cb6d6ca18580a8a67b8176b67aaf4d13e69b80 | 8901 | 24 |
| chunks/scurve/2023-11-18.npz | 350840 | fbaf5adb33dd181f46eb1ea07afad0559d921bf4a0cee2a509d31d5af252ac56 | 3575 | 24 |
| chunks/scurve/2023-11-19.npz | 592704 | 2663420a395cb3b1ae257b5bdc4888a281e3e9fdaaee9ce9a69166931edf36ab | 6043 | 24 |
| chunks/scurve/2023-11-20.npz | 771652 | 9cf27a9abbbd4bbc8ae766c9170777291e9d04a0ff71359f2c93a8081507e411 | 7869 | 24 |
| chunks/scurve/2023-11-21.npz | 1362690 | 9321b9397126d7432357c6d1f88af8ba3bbd771fe11e7076278b3e3eb8209cb5 | 13900 | 24 |
| chunks/scurve/2023-11-22.npz | 817222 | c4f681dfa0ae0118a7c6078fd9b56a0f648ac536cd77eff0955faea5e2fb1a92 | 8334 | 24 |
| chunks/scurve/2023-11-23.npz | 472556 | 07811af60b78b71151262e2bd2b850112ee9dd1862577ef05f7962b845d8df66 | 4817 | 24 |
| chunks/scurve/2023-11-24.npz | 752738 | ad70815307af4a59aeace6cfddb6b916d4f4f0e5ab53d4bf2793264de2bbc6cf | 7676 | 24 |
| chunks/scurve/2023-11-25.npz | 53410 | 7f29e5e88ddf38a6b5aaa497d55f436f7c022f9d6fa982fc864792f48016776c | 540 | 24 |
| chunks/scurve/2023-11-26.npz | 494312 | 13db479e14d58f33667762eb6b5bf2befa630f96ae490a76047939f66145d6d3 | 5039 | 24 |
| chunks/scurve/2023-11-27.npz | 680414 | e4264e57f7df7d3a81b5b4d44437057c88fae8eef5bc02c00758520ac41b8db5 | 6938 | 24 |
| chunks/scurve/2023-11-28.npz | 709422 | 0e04c0e3660ca5693640661201742530fb27ab302b583d8bad1eb9c48dbfeca3 | 7234 | 24 |
| chunks/scurve/2023-11-29.npz | 685020 | 63a635a485f599a1b764a09d15654546bdc285e30cc1e6553b543a283e3609b9 | 6985 | 24 |
| chunks/scurve/2023-11-30.npz | 532728 | cac05c3def1884137ac582e09c9a9031e5ad217c60ea8f350b7911d521545d80 | 5431 | 24 |
| chunks/scurve/2023-12-01.npz | 891408 | f3d05523b3bbaeb705cda952aa5a0591007e935ca14e3648ec8977867acc8205 | 9091 | 24 |
| chunks/scurve/2023-12-02.npz | 316834 | afd37d255d25d8fe871a9180a0978374db6c5fdef2160e3699648a943a3c6299 | 3228 | 24 |
| chunks/scurve/2023-12-03.npz | 577612 | 7f59026690ae4460f0fc1caa72892ad9fdee9854bb7949c3c44013b3175274ac | 5889 | 24 |
| chunks/scurve/2023-12-04.npz | 1941086 | 096c6d6c402587ca7cdea0d3dfb1f7c0d067fdc1a149ca17ef8749a8736449b2 | 19802 | 24 |
| chunks/scurve/2023-12-05.npz | 1676976 | 596aa5a148f1ac91acfd5c89a6a98795ae06b70d984f0362277f71ac5bfdd437 | 17107 | 24 |
| chunks/scurve/2023-12-06.npz | 1291346 | aae45d859cce6d970ab5841bdab83130777376b6a619bac44ae867e0e81fdd3b | 13172 | 24 |
| chunks/scurve/2023-12-07.npz | 1001756 | 9bf796b38899a0ead076155add8192d9708e49bc7b6b4b649118a751b827e76d | 10217 | 24 |
| chunks/scurve/2023-12-08.npz | 841820 | 726d49005f4d3457dbe0f6f86282467ff8eb29032036da972051bc0d88f48c78 | 8585 | 24 |
| chunks/scurve/2023-12-09.npz | 518910 | cc068f7700c724c2f0fbcccd3b2c845913c781f3f296af1ccfcb889e2dae8ba9 | 5290 | 24 |
| chunks/scurve/2023-12-10.npz | 355250 | 52f5db558732f7339979db0df1ab05590162fc5c9417406204fd0cc7a9e9d68b | 3620 | 24 |
| chunks/scurve/2023-12-11.npz | 1879640 | b9e3737fb13b0a8f96e398ec2c2595c2b127da54c506c2418a96219e533d7039 | 19175 | 24 |
| chunks/scurve/2023-12-12.npz | 1252930 | f3569b4b233326faf5c946163dd6045c0e567f502eac54a00d68fd2ab54f5ee1 | 12780 | 24 |
| chunks/scurve/2023-12-13.npz | 968828 | d4ba23c13e687a8dcaa5119c70f936c0e4df29cab9865c8a7f43444118918ace | 9881 | 24 |
| chunks/scurve/2023-12-14.npz | 942760 | e5d476a41d32cb44bac068422d5e3c4d08eabee13fa87421978ccded3cd2e10c | 9615 | 24 |
| chunks/scurve/2023-12-15.npz | 863576 | 58bad6ec8762e06a47a1b3ce54c7c1e1190da5991d814a2bdb31aca61bcb7723 | 8807 | 24 |
| chunks/scurve/2023-12-16.npz | 485002 | 3736d854e435a474e6eafb46124b73dbf379988e14efb61065c0994688eaaba9 | 4944 | 24 |
| chunks/scurve/2023-12-17.npz | 878766 | ecc991941d468037ccfa4d226b1592130abaa42227a5e6c7631d7a34e58bd651 | 8962 | 24 |
| chunks/scurve/2023-12-18.npz | 1215298 | 501571f1b4d1839ba2d1ca77464f02cf896d44169a1a126b3b6a0557b7ceb3cd | 12396 | 24 |
| chunks/scurve/2023-12-19.npz | 1179724 | 89f083b737d7589bb377331961525a0e61cf6944ed96bbe0e328f82da6fb13df | 12033 | 24 |
| chunks/scurve/2023-12-20.npz | 996660 | 7f820742ae04b7731daceaa4ade166c1f8c17533ab862ddd1256109532ad41a8 | 10165 | 24 |
| chunks/scurve/2023-12-21.npz | 780766 | ef7b1e367d52fdd5d6499a865b8717d7fda18aedae523e673e06799c70d29c61 | 7962 | 24 |
| chunks/scurve/2023-12-22.npz | 607110 | 60f1f79289c7144dc6fd9485c00811ad91aaed61861169f4cc63de1281f3bf44 | 6190 | 24 |
| chunks/scurve/2023-12-23.npz | 312228 | ad0385c50ad80b40b09f65b009e17107bb9b07dce6b6808d01eb2ba6f9de2bc9 | 3181 | 24 |
| chunks/scurve/2023-12-24.npz | 469714 | b3fb90bb133e884528ebe6debfab37658bc89bc62b8b33a8004adb3788f66f8d | 4788 | 24 |
| chunks/scurve/2023-12-25.npz | 444920 | 5790cdae05791f972274801dc21dd633183250d277d74a87903ec3959fcb6b9c | 4535 | 24 |
| chunks/scurve/2023-12-26.npz | 871220 | 585cb91a6d00eefc5e83ec8a989045ffe962f13e91ddde839298b81d618b8059 | 8885 | 24 |
| chunks/scurve/2023-12-27.npz | 681688 | ccda53560771db703846b08aee8581a9e6d72732dd0d60dc36cab217245e9453 | 6951 | 24 |
| chunks/scurve/2023-12-28.npz | 1015378 | b00ac8476046d41c65878a6b4642b878b6d33e24e3ba5ed1f6762164bf10a50e | 10356 | 24 |
| chunks/scurve/2023-12-29.npz | 932274 | ac62e8aecd2cb7b6bfaa1a9ee46857fc8865cb1ed647e837fb478959204df49f | 9508 | 24 |
| chunks/scurve/2023-12-30.npz | 630532 | 33405a8c1484f4681f650db41194729bc009ea00711c14a62ceaac6be9a91b4c | 6429 | 24 |
| chunks/scurve/2023-12-31.npz | 560560 | 19b4fa70b1c7fafea98ec76722df5fe1dd179afea8ec741cfdd5bb0bed884577 | 5715 | 24 |
| chunks/scurve/2024-01-01.npz | 758912 | 5fde032e15e1d3cf1e49f01884ee6c2b5a33f0819af6ba17dc8d7c4765e70880 | 7739 | 24 |
| chunks/scurve/2024-01-02.npz | 1612982 | c815a853fec607e5493e3580ba645c8fefa4c1aca85e88eb7833969d61954260 | 16454 | 24 |
| chunks/scurve/2024-01-03.npz | 1432858 | aa5defe2521c0f96a3794d51acd5be591b55d064ea43c30c14ff0b1c77408e3d | 14616 | 24 |
| chunks/scurve/2024-01-04.npz | 1091230 | be552088b5816402b816a1bfa1fd2c05b2b20306fbac111ee4b90d3b0622d761 | 11130 | 24 |
| chunks/scurve/2024-01-05.npz | 983136 | 7bfac1a11e301eb9cb2259fc0f03c2b6a0740c9d322ddb1bda7cfc198eb3f484 | 10027 | 24 |
| chunks/scurve/2024-01-06.npz | 361032 | 04d6d23bf782198bb541945c90027aaf43f8abf29396299c5543d723790a76b2 | 3679 | 24 |
| chunks/scurve/2024-01-07.npz | 705698 | e273c7684e583c91348ebaac21d66fbf684879fac061ae527877c7846bc90334 | 7196 | 24 |
| chunks/scurve/2024-01-08.npz | 1597008 | 56356d6a96dfca0de91c5ba8363aa1c5d3f8d155b6f0ea702f3d6428c18a5029 | 16291 | 24 |
| chunks/scurve/2024-01-09.npz | 1230390 | 2ed46819d2462f4db0055516f347d08a154ce69e95ab557fdb9cc72e6346c4dd | 12550 | 24 |
| chunks/scurve/2024-01-10.npz | 1912764 | 4db56c8f0c0a2f46d49a3351114f608a648ac32df53f15da0f0a988d2e12eb8b | 19513 | 24 |
| chunks/scurve/2024-01-11.npz | 1812902 | 68def218d53ce87c4dc03c40ca52f42d7e9ef1d36babdca11277990109832f94 | 18494 | 24 |
| chunks/scurve/2024-01-12.npz | 2012136 | 1911ba1727a999b4cbacd10bef29ff36f0996527f2a25730f87c0d5478c6f220 | 20527 | 24 |
| chunks/scurve/2024-01-13.npz | 739508 | 0b418393a48bdc8c629800a30b1261386cb8b0d3dbdb8140211025354d9a7e8d | 7541 | 24 |
| chunks/scurve/2024-01-14.npz | 962262 | 67509038668ce29c3366477cb35719effe0eab2428a8c140965288a490d7e5e6 | 9814 | 24 |
| chunks/scurve/2024-01-15.npz | 935998 | 5064b3f2e09f39263afe84fcac2cdaf8e1c8299a8db2949b44923498be0f501c | 9546 | 24 |
| chunks/scurve/2024-01-16.npz | 934822 | 4cf2fbbe3002bb8b6e9a7d4109d185936518aa3ae5c1d5423b18148df039e53a | 9534 | 24 |
| chunks/scurve/2024-01-17.npz | 946190 | 341690bb604df668f03781993f06d57ff0ad8f3422ee767661122949683c372d | 9650 | 24 |
| chunks/scurve/2024-01-18.npz | 1008812 | 9694522b97e8bf7c8ee57b3381503493e5db15fc4626002d680803fb466601f4 | 10289 | 24 |
| chunks/scurve/2024-01-19.npz | 1071042 | acc37c402d47d200e825d19e48e0a0145a1a629c503a0d4b407345d0456b5128 | 10924 | 24 |
| chunks/scurve/2024-01-20.npz | 194432 | b78a5c4100e652695de08367aca1462bdd39f31ef2913697d2eab408e108d67f | 1979 | 24 |
| chunks/scurve/2024-01-21.npz | 164346 | a46a13b41c1cd6404227fc4763bc74d2c7b14207e13f96dd14613749ba91c1a1 | 1672 | 24 |
| chunks/scurve/2024-01-22.npz | 1342502 | f572830e3ef87d060190e1ac86d4c22e1160067c982e96ae83797063233f0fbe | 13694 | 24 |
| chunks/scurve/2024-01-23.npz | 1491854 | 89fea4ba82926bc9874a49c1842b070ceef8c6f2da7c49cfb21403edb33559d6 | 15218 | 24 |
| chunks/scurve/2024-01-24.npz | 928844 | bdb556e0ebf65885cc486be7fec128babee33c72f29d86e461d6aaf725b68e7b | 9473 | 24 |
| chunks/scurve/2024-01-25.npz | 488138 | 5481d319cacaeccf4a33c3ac438d974119fe83be9806d2d8811853e24612360f | 4976 | 24 |
| chunks/scurve/2024-01-26.npz | 1141798 | d313e08e31c09d3d4de7fb8502d98265b176542f888e94f09184ae76845ceb8c | 11646 | 24 |
| chunks/scurve/2024-01-27.npz | 278026 | 7501d6f148d43fa27ad87ffed079bdba2af2552c4f943305f72dfd4480cd7208 | 2832 | 24 |
| chunks/scurve/2024-01-28.npz | 693546 | 96f910436dcb7370422ece14ee691f7ed5e2978af2659266bae9ae8452a7cf00 | 7072 | 24 |
| chunks/scurve/2024-01-29.npz | 897288 | 9665a1a85b85e94dd063ce063de6d34d185a9e8d81663b43adae014fb76815ee | 9151 | 24 |
| chunks/scurve/2024-01-30.npz | 828100 | 920c49865ef74371dd2ce9880d26ed5f6b2dd572887a325616e2d660e742ae6a | 8445 | 24 |
| chunks/scurve/2024-01-31.npz | 801150 | daaf9597fbcdecd9cca9efcc20e4483dd6d66a5e608b3a078f3490c5d4aa9df7 | 8170 | 24 |
| chunks/scurve/2024-02-01.npz | 796838 | 5eb124d2234d73480f222a0b6b34b29e0db6ceaf0da6b7358128fcdecadbfd1e | 8126 | 24 |
| chunks/scurve/2024-02-02.npz | 564186 | d627264e39b8c8fdbff81190e17d73f6483ac65c7a09821da74becf6feb637f6 | 5752 | 24 |
| chunks/scurve/2024-02-03.npz | 171304 | 583f8b810fc87ac4c6d9ecfb9ef2fc1a783a80973f750757f78f8baea433edb9 | 1743 | 24 |
| chunks/scurve/2024-02-04.npz | 383180 | 92f7e417c5f4fbb60557ad3be6f7703a51ecd48cc834883361bd3ed2cc5d288f | 3905 | 24 |
| chunks/scurve/2024-02-05.npz | 783804 | b8f5410f4e15295e9c6cb0f7fc542d98fc31aee08c268d1d0a48df98853e646e | 7993 | 24 |
| chunks/scurve/2024-02-06.npz | 384356 | 301a900e4b44c826b46a5f467dd0fc861152c507b2bdc353f48f2709af94e38b | 3917 | 24 |
| chunks/scurve/2024-02-07.npz | 712166 | acac342acdca5203dfe1320a51d78da74ab8eb909e8772095638c1c9cccf28c3 | 7262 | 24 |
| chunks/scurve/2024-02-08.npz | 736274 | 11b35bb0757ad5188111f401ea4976bd715221b2e33848d8b113171ab2766352 | 7508 | 24 |
| chunks/scurve/2024-02-09.npz | 1399440 | ab3eb27db5e0ef5f8fa886a60e023230b1b003af03283922bb41d8267830b19e | 14275 | 24 |
| chunks/scurve/2024-02-10.npz | 526358 | 0d7b2142bf9533c22ac8be45fc78d20e12c4478cacd418203b19b9b8db9af2cd | 5366 | 24 |
| chunks/scurve/2024-02-11.npz | 602798 | 8a6833318965dfaae864e55117111bb05cdfbd00ee9baa671515c70dcc2d08c4 | 6146 | 24 |
| chunks/scurve/2024-02-12.npz | 1405418 | 80b0e7ad1b233dd48f31f816422f4482c870976371c9ea397609cb79d4ef5702 | 14336 | 24 |
| chunks/scurve/2024-02-13.npz | 1307222 | 5df6602b0ddc41a8284c84d03ef3f5bb4973ad3ba00eaad99fcc559748672dbb | 13334 | 24 |
| chunks/scurve/2024-02-14.npz | 1013516 | edd09f4deb48d961fefd762c45b03f5d22c92623c30c66aa08bdfa34b69d77c6 | 10337 | 24 |
| chunks/scurve/2024-02-15.npz | 1119160 | 0da8a49f1c74ce8462af7fed55a7b170998ed05b0f6de1a5fcaf2ac2aff8ef9c | 11415 | 24 |
| chunks/scurve/2024-02-16.npz | 840546 | 00bb77f6cd7c19f7f2683c9a8f89dabc2498246c5f4df47ba4ab68509a51fa73 | 8572 | 24 |
| chunks/scurve/2024-02-17.npz | 787822 | 58195f2ceea821de83958eb0b9c31507ca4f07c66a920d076bdeb6b4eb4ee8d0 | 8034 | 24 |
| chunks/scurve/2024-02-18.npz | 588294 | 497abab9b71be05d07561e8d56729e5b95cbc2ddbf1338d120be167cb64ee7f1 | 5998 | 24 |
| chunks/scurve/2024-02-19.npz | 704620 | 3b0d162aa9a603a7ab10a871066b28e41370d6db5ef5814ee2958b1abaffacdb | 7185 | 24 |
| chunks/scurve/2024-02-20.npz | 960008 | 74a4e3df0a6983b7bc001b5287c01be7201fd75beebf9ce92c13faf1d1c33d71 | 9791 | 24 |
| chunks/scurve/2024-02-21.npz | 1162868 | f97b253e3598888c96a29c4eb640924e937829181caea6ddbc936b8914087b15 | 11861 | 24 |
| chunks/scurve/2024-02-22.npz | 690606 | dc5232f23678e21246d98737e0f477bdb187883c8be1fa807f361634cc8f90f2 | 7042 | 24 |
| chunks/scurve/2024-02-23.npz | 512148 | 7878bff39e782a232308e131957dbd2506ffbccb833b8fa0f33933d0a4fe347a | 5221 | 24 |
| chunks/scurve/2024-02-24.npz | 167090 | f4e1f3c760abf9d936667d9dcd24fece5c39cbdd705c03639fee976ff7431c56 | 1700 | 24 |
| chunks/scurve/2024-02-25.npz | 345548 | b7eb1c6a9f68b7ef152e053bfd61e8e26fa4d4e22ff5e729f556ca6400a403eb | 3521 | 24 |
| chunks/scurve/2024-02-26.npz | 1138564 | ce6b904b19a031a0d6b0c33b4e08fdd9fa0b2f373a255fe1688b49689f5216f8 | 11613 | 24 |
| chunks/scurve/2024-02-27.npz | 1664922 | 2e4da903ccdbfe79a99e6c18fd072532d00f84b5740ca20e6c2f0318b78e6b52 | 16984 | 24 |
| chunks/scurve/2024-02-28.npz | 2907856 | 1461dc1ba2bc817f005044627280c3acd90f821b3960693f1286759f19e17a27 | 29667 | 24 |
| chunks/scurve/2024-02-29.npz | 2515170 | be8b09df0f8e019d45e48dbd932d08ed1074874a0a597b12dce933a4537125b9 | 25660 | 24 |
| chunks/scurve/2024-03-01.npz | 1243032 | 2221d1649941f04892d90a0dc9d674d848a4d0b44fd0fa280d80ba0a431dfc73 | 12679 | 24 |
| chunks/scurve/2024-03-02.npz | 581728 | 314f0ddc1cdc34c6d08326fdf0e9e7b2745b0aae5dbc27bf240397acba0b361b | 5931 | 24 |
| chunks/scurve/2024-03-03.npz | 811048 | 5a2cd5915433fe6d67589db61c9cf6fec8e2620cd149cc6672191471082967c0 | 8271 | 24 |
| chunks/scurve/2024-03-04.npz | 2299178 | db40501dfe896e91a291111f69ed012ff422ba5cfd0d99eafae0dabfd51cba64 | 23456 | 24 |
| chunks/scurve/2024-03-05.npz | 3905986 | a067deeff88ef4e7b491ab13ee41cf7c2c05ece66456a68854eb08ed33d9e14a | 39852 | 24 |
| chunks/scurve/2024-03-06.npz | 2342788 | 655c59c3dd20e0a4cdd0eaff4b5d96ee57dc2447331ef66f982d3e0dec6b30a3 | 23901 | 24 |
| chunks/scurve/2024-03-07.npz | 1129744 | bbadc5a9a2ef3c04b95fad21fd267f5365831d1e627bc8f58256ecedaaff523d | 11523 | 24 |
| chunks/scurve/2024-03-08.npz | 1496166 | 1213bf53915275283fc13bc7f0410f6e3719a95b9180f6d8b46fad81212b4e35 | 15262 | 24 |
| chunks/scurve/2024-03-09.npz | 448350 | ee9602970b30fd5052ee606bdcbbd11af91da9c5001d1bc56dafc6a255daa75d | 4570 | 24 |
| chunks/scurve/2024-03-10.npz | 990290 | a91c33a961884125e22371fa100eec4d95fab4cb7afb9857905c89c16d9d2adb | 10100 | 24 |
| chunks/scurve/2024-03-11.npz | 1777132 | d548c8ac6c14d3757ae4c2fd4b7a020a52f9ead4464797fa4307366dbc6fd353 | 18129 | 24 |
| chunks/scurve/2024-03-12.npz | 1683248 | 3edeaa68fda0f20fa4a92027f34be1e8a1a5149c8472959b1967b2fc8c192189 | 17171 | 24 |
| chunks/scurve/2024-03-13.npz | 1073296 | 5473c1161118d069abd15f48803c44ef66916bd3d7fbc809207a742a38fcd26c | 10947 | 24 |
| chunks/scurve/2024-03-14.npz | 2191966 | 7ffc362a66643887e83c244116514c498f43c4bc12bb1789306719c9d44a6854 | 22362 | 24 |
| chunks/scurve/2024-03-15.npz | 3111108 | ee6e6e3f97b18c50c52dc0c520c4811aed4d8092e092d636e1b56a9052559911 | 31741 | 24 |
| chunks/scurve/2024-03-16.npz | 1740578 | edef1084d2e0fe8519f5977304dda5373fa4562b775ad28a5c69486a391fc7b3 | 17756 | 24 |
| chunks/scurve/2024-03-17.npz | 1436092 | a009da7c5e6e2e8ef71fec800da4cb4f8d418a8798292cf74c9ba9312a64901b | 14649 | 24 |
| chunks/scurve/2024-03-18.npz | 1533014 | 168c285d02832a2dcfa70da3244cb8327edc852f54026237fdc67873a76c538c | 15638 | 24 |
| chunks/scurve/2024-03-19.npz | 3065048 | 725b072118923182f6ed4ad3ad63c89ec667917ad35e442a8c348928b5ae03d6 | 31271 | 24 |
| chunks/scurve/2024-03-20.npz | 2592198 | 15ef8a16e89ce34c76d62b4707d7bec1b343fe6ee6848e4a71b9723c2a482a5c | 26446 | 24 |
| chunks/scurve/2024-03-21.npz | 1681876 | eb5e3982d1ce259d0441cade88ac120ed701b958d681e088815ae4a5639f1752 | 17157 | 24 |
| chunks/scurve/2024-03-22.npz | 1759296 | 357791e101a3914cd0d183128550f79a1e8cb21cfffbbe05284d8056348fa3f8 | 17947 | 24 |
| chunks/scurve/2024-03-23.npz | 1124452 | 5d52daacb1914ab039be06d0d7bc8c9e505c2d01bc3b1afedcee01cf9270f835 | 11469 | 24 |
| chunks/scurve/2024-03-24.npz | 992740 | 00afd0437e730ba43e58f23461d717b41180e6285d478b5bfb3bf12c5ad805ae | 10125 | 24 |
| chunks/scurve/2024-03-25.npz | 1542030 | 9299db1c8288e520b33adc7a56a790252b7727f2b287815b7f971c4df176f367 | 15730 | 24 |
| chunks/scurve/2024-03-26.npz | 1179038 | 27d5b5bc8cb4a1029f01d0da4a2acce2c22b3205ae69ad27b1f0f1368b5d1696 | 12026 | 24 |
| chunks/scurve/2024-03-27.npz | 1348480 | e80b8614a4ce7859079266872e430cc3f3e8b239ee17ed9115a5e82097187e36 | 13755 | 24 |
| chunks/scurve/2024-03-28.npz | 880040 | e7189c9bb881e9488e1d85efb45adf1f0089d54233c379cb3573f61438c6a942 | 8975 | 24 |
| chunks/scurve/2024-03-29.npz | 662480 | a92fd9cfd6b84871333bb907388a99ffc7126ff0b170c7bc2da4ef882651b7ad | 6755 | 24 |
| chunks/scurve/2024-03-30.npz | 308210 | d70d35660ba45f412856f9ab711c24ca48b6045e024e30d71e2494f08cc0bc28 | 3140 | 24 |
| chunks/scurve/2024-03-31.npz | 439628 | 2244d51a9a96a65f2beb024173652dfeb796092c20c316fff9c5cb2f28749554 | 4481 | 24 |
| chunks/scurve/2024-04-01.npz | 1152186 | 2a5eae04b477e820a943cc064b048734baabeb344c51b2e523ac62fa20aefbf9 | 11752 | 24 |
| chunks/scurve/2024-04-02.npz | 2165800 | 2bc32a46c9111d4a43e8662478a3427b23ecd032f606f423ba2eb0148459ca9f | 22095 | 24 |
| chunks/scurve/2024-04-03.npz | 1076824 | 48342ca94cc44bffceca3dac1606df4ecebfda319bfca42f3fbd54f9b5678a99 | 10983 | 24 |
| chunks/scurve/2024-04-04.npz | 1268316 | 7fdbdc09a17dad2031405b3dd9a5ba2d440fdf4c9b0f7215fe02df8d678b3f0a | 12937 | 24 |
| chunks/scurve/2024-04-05.npz | 1144738 | b51bf9ef1636b543cbc631604068c36b30a1daa9040fdef45184db7e5ca95c14 | 11676 | 24 |
| chunks/scurve/2024-04-06.npz | 449624 | 27e9d00f91f077456f6a489f271c33eb20c0a32c8d0bc2f6c3212224626638c4 | 4583 | 24 |
| chunks/scurve/2024-04-07.npz | 590940 | 8eb9349da9a990f3f8b843fc0a8c0df98099c714299ebbe287d242865e389c31 | 6025 | 24 |
| chunks/scurve/2024-04-08.npz | 1098188 | 78e6b0f3b8efd596bee5cd4d2a19451ab98e78b6914247b4d5c4c850a12c458e | 11201 | 24 |
| chunks/scurve/2024-04-09.npz | 1089956 | 040cd3157b367fe50126e750dc6e5320ef1499d03f4b1eb4c0afc4e3eb638430 | 11117 | 24 |
| chunks/scurve/2024-04-10.npz | 1077608 | c5e0e9c2aa54dd792e12ba8badcad20872fa59493c7a769556017178651b0275 | 10991 | 24 |
| chunks/scurve/2024-04-11.npz | 792330 | a9c2178fdb68587740a3e3ed6ae0c41766c45fd9d44d44adf8f2d94777f7b86a | 8080 | 24 |
| chunks/scurve/2024-04-12.npz | 1275274 | 65ef70e2be35fa2778974297699b77b985455c1323569e75b904b0bd5c66ad6a | 13008 | 24 |
| chunks/scurve/2024-04-13.npz | 2038890 | cc79cf968373d1c82e4668949c4db83ecec791469656945433537f0c6e568b71 | 20800 | 24 |
| chunks/scurve/2024-04-14.npz | 1847300 | b2c8db4f1e8f9937d4288c32973b94389103ff3f8ef7f3a54db4d72b85c05ee2 | 18845 | 24 |
| chunks/scurve/2024-04-15.npz | 1589462 | 9ecb76b931715e8dd10dbf2dce412130f9aa2b7729fcba6ff9efab31baa18013 | 16214 | 24 |
| chunks/scurve/2024-04-16.npz | 1838578 | d97ce6ec02123eaa0e91259e42ebe98f9d528f4980f966ca8fdc55c22951c19d | 18756 | 24 |
| chunks/scurve/2024-04-17.npz | 1716078 | c9c4eda512f49e5b4fa3555f3e619271babe34b1964c5ac7091e74ee333727ea | 17506 | 24 |
| chunks/scurve/2024-04-18.npz | 1387288 | 7d0fe6f2bb3ecca2abb166bb61628b287c921cd3b12e4e446c9c175cd1fa00b9 | 14151 | 24 |
| chunks/scurve/2024-04-19.npz | 2142378 | fb4b382152d40be3a856d1ad30dd6f7e61d64c1e03b8c7040bd5d463210619df | 21856 | 24 |
| chunks/scurve/2024-04-20.npz | 715890 | 2c92a0c75068434afefa6ec14cacb21709ba4c47f113d73cd8e9767ebadd1055 | 7300 | 24 |
| chunks/scurve/2024-04-21.npz | 605934 | 53372cb589d881d082069330bbaeaf4aeab129f028d3c51444f06c7cb6563ab3 | 6178 | 24 |
| chunks/scurve/2024-04-22.npz | 871710 | 050e6b018b5e61919dd4ea42d33039c7de8b48c748a32526a578bda99696f143 | 8890 | 24 |
| chunks/scurve/2024-04-23.npz | 617596 | a1072c8539e1e43615d2b5320b501cd640f7ed3057e4bbda5467e658faa39043 | 6297 | 24 |
| chunks/scurve/2024-04-24.npz | 831236 | 892fc74ef173d4806175a83694b606070e1257fa8fa241ed5c827b820d74c74d | 8477 | 24 |
| chunks/scurve/2024-04-25.npz | 1105146 | 238e20a07a12ee6036b9b9fea1908e826a8d17366191a1e6b96422130772d98e | 11272 | 24 |
| chunks/scurve/2024-04-26.npz | 783314 | 36f91185feb88889c903178f813464cb4c0a156063116e80464db618ee5f7d14 | 7988 | 24 |
| chunks/scurve/2024-04-27.npz | 429534 | 22cc4858a92274eada240d73f5d742fd8a78ece70cd145f8d265f215f9dccf0a | 4378 | 24 |
| chunks/scurve/2024-04-28.npz | 443156 | 2e27644c0211a8f65dace54797ddbe68b976db2685cf8fbfad8baae8e8d179fb | 4517 | 24 |
| chunks/scurve/2024-04-29.npz | 941878 | b49b35113547897e9148399a8f2f096238715b542b752050897d1b179ce014f2 | 9606 | 24 |
| chunks/scurve/2024-04-30.npz | 1515766 | fc249d3c8461144b4c24861c1bc02334c11cf84dcbb6020e7165255db29f3111 | 15462 | 24 |
| chunks/scurve/2024-05-01.npz | 2360820 | d36870156ea9361b512a76b66e98f5c4e6d9226d945bcbebfaf44d05cdfd6526 | 24085 | 24 |
| chunks/scurve/2024-05-02.npz | 848876 | 1a8a381e44f04cf8e9cabfa0d7d86b3074ee2bad3ddb1cddc7057a6c35e39db8 | 8657 | 24 |
| chunks/scurve/2024-05-03.npz | 1245090 | 5c1026459455925c908635c084cd06ae3fa37c7781b6526c1b3701a4302f6bcd | 12700 | 24 |
| chunks/scurve/2024-05-04.npz | 752836 | 31d2bd52f0ddb4b2d13fd0b7ae73f76f69c4cf47dea7cdb21df40e48e00e8d17 | 7677 | 24 |
| chunks/scurve/2024-05-05.npz | 670516 | d2e48da0a83a795db247fe0634820b5092e2b41bf91b28cfed69fc6c30cdca3b | 6837 | 24 |
| chunks/scurve/2024-05-06.npz | 1010772 | 3ca28e27a9e3337fdbd1cdd705d134a29b917b4f4dd478469cbbad0fe2976c07 | 10309 | 24 |
| chunks/scurve/2024-05-07.npz | 802620 | b50748dfabffcf87da2631b68543314dc0a75493a6783052adf8dd7168d84b5d | 8185 | 24 |
| chunks/scurve/2024-05-08.npz | 1008616 | 1d1e6220d45a2012531b9504e60265d41abddaaffaec5fb75deae133bf2daca2 | 10287 | 24 |
| chunks/scurve/2024-05-09.npz | 979314 | b521dd441fc97202b9a8c104d6d18b8155d8689c620448f7f1e3a64c307706e7 | 9988 | 24 |
| chunks/scurve/2024-05-10.npz | 1048894 | 00dc2401410b3a53d914a50e087dc81e1560b33e16651710a4a259703972b035 | 10698 | 24 |
| chunks/scurve/2024-05-11.npz | 254408 | 7e2bccc0ea0d72d745469a9c51977ac6c14a562e1c6e3345231d6dab26ef498a | 2591 | 24 |
| chunks/scurve/2024-05-12.npz | 274008 | 51603467fdf698c5d53487993c81f91dc4d2ae1f5c374c88cd785f5008159f40 | 2791 | 24 |
| chunks/scurve/2024-05-13.npz | 840938 | fc5dfde2d2b33d5ac406c234a55db8c6bfb301e49d4a622a3aba698ea6d31c53 | 8576 | 24 |
| chunks/scurve/2024-05-14.npz | 855050 | 4067b0e3babccbc7f792c4331077c13519cb315152ec8fad6e7266e3e938a9d0 | 8720 | 24 |
| chunks/scurve/2024-05-15.npz | 1020572 | e19b82253c199f2d2611d4c97f84a5d04b4317d8cbfe08c0399b01877816b0a2 | 10409 | 24 |
| chunks/scurve/2024-05-16.npz | 918750 | bfbe7703411ded3a1066e12d41c29aa8dd5c498d126db8bac15842e6268451a7 | 9370 | 24 |
| chunks/scurve/2024-05-17.npz | 783902 | 092b7d6fdc98b3b0ca5f616c689a51df0cbd4f4d22a17f00549ffa92b0c4689c | 7994 | 24 |
| chunks/scurve/2024-05-18.npz | 240982 | df74ba9967c7e46029e9bc52070e8810ce170d2c9456b35dd72b1317fdf276da | 2454 | 24 |
| chunks/scurve/2024-05-19.npz | 554386 | 5049eb15842eead57dcea69303ef7fa4937782d50cb768b993d255f82e17b87b | 5652 | 24 |
| chunks/scurve/2024-05-20.npz | 1092112 | 177405ec1e7d84ec26cc93fd5a85002cbcb1698b352b4cc1946e0962b6c5609e | 11139 | 24 |
| chunks/scurve/2024-05-21.npz | 899836 | bd81cfc7a40ab5c16df6792b6cbca23a99806925a9506fbdbf7def018abede49 | 9177 | 24 |
| chunks/scurve/2024-05-22.npz | 773024 | f88eaee190d805295c71acef91b84faa000d1c6af2471e2bc4f7549555f24b10 | 7883 | 24 |
| chunks/scurve/2024-05-23.npz | 904148 | 7c0a43c2aea310accf6bcf03860c02b1e48fff4cf5112c29e310afb64a82746b | 9221 | 24 |
| chunks/scurve/2024-05-24.npz | 785176 | 924347c5112f4cbaf977a4d6c9b1e8874b74fafc14851ea3f07f1b7bd95ed14e | 8007 | 24 |
| chunks/scurve/2024-05-25.npz | 229026 | 1d5e96247024604319905993dc0ce67181574ce8297c115c81909487b7bf0cca | 2332 | 24 |
| chunks/scurve/2024-05-26.npz | 221676 | c9d10fe0f4f06d660a7cc237bf9b936172cf613734f98b3b1e40a3aed70269f9 | 2257 | 24 |
| chunks/scurve/2024-05-27.npz | 693154 | 078709ced82c4a3908b2664a5194fe7a13774266a71e84c52da657fc10a0ff51 | 7068 | 24 |
| chunks/scurve/2024-05-28.npz | 972650 | ae67e69baf507f273f713e97992596cead63526262ca69661dc5403310fc5ddd | 9920 | 24 |
| chunks/scurve/2024-05-29.npz | 517146 | 046a70359758faaca75ddd0a35cc640efd16a86c904599c8503f7573eb9570ba | 5272 | 24 |
| chunks/scurve/2024-05-30.npz | 677768 | 69bdddea7d615ccde8faca5e4cfbfe51c47b7ec2a89e908c8787c725634876a7 | 6911 | 24 |
| chunks/scurve/2024-05-31.npz | 565460 | fa51ee8e5de81a39814bb91cb950f768472511c5323d28de77636fdba8d36e79 | 5765 | 24 |
| chunks/scurve/2024-06-01.npz | 490 | 58f3fffe7b29de83e1f4024b49b79343800a3e43a9c55b2752bec2db40e6457c | 0 | 24 |
| chunks/scurve/2024-06-02.npz | 357210 | 7c20906d463c00cf3a7ec736b0ab704ecd43a7da096becce5a2d167494288f73 | 3640 | 24 |
| chunks/scurve/2024-06-03.npz | 848876 | 423b57f3b1152d5f76de6b329b204ec9a338eb8b559b039810abab8685e1f128 | 8657 | 24 |
| chunks/scurve/2024-06-04.npz | 709422 | 48a4d66249e4195574d535fea38eeb5f0ba8ad2eec79a5269f1247fc8d3b4e64 | 7234 | 24 |
| chunks/scurve/2024-06-05.npz | 704424 | 520cbc47290066d9a481c9ab9a8561204f86f948b693d7e644d04ca30dd5af27 | 7183 | 24 |
| chunks/scurve/2024-06-06.npz | 492058 | 4281691b994c81a7f20c46a344ff1468b7c24ce64505cb0b72b7d879a4c8c598 | 5016 | 24 |
| chunks/scurve/2024-06-07.npz | 902286 | d438e3876462907bbb879fcfe9769829ec5e5ac42ea6780147861712551c3308 | 9202 | 24 |
| chunks/scurve/2024-06-08.npz | 18228 | 9e14a66e9143444d4e2b83b8387a1bdf7c2cd7c431ad526db07b5c1052ae21c7 | 181 | 24 |
| chunks/scurve/2024-06-09.npz | 218148 | 283826a724d717ab311ca2cad6fa6faff02884ba5f5505daf2ecd2b0df43e93e | 2221 | 24 |
| chunks/scurve/2024-06-10.npz | 328006 | 152bff368df1af154cd5bf90291280fd2e20d12985278900d174438b6586fc3d | 3342 | 24 |
| chunks/scurve/2024-06-11.npz | 490 | 58f3fffe7b29de83e1f4024b49b79343800a3e43a9c55b2752bec2db40e6457c | 0 | 24 |
| chunks/scurve/2024-06-12.npz | 490 | 58f3fffe7b29de83e1f4024b49b79343800a3e43a9c55b2752bec2db40e6457c | 0 | 24 |
| chunks/scurve/2024-06-13.npz | 807618 | d31ae8025927ff62fcc93d1b7a64f91b045a98ea046b729a85fb9e2351d90c0a | 8236 | 24 |
| chunks/scurve/2024-06-14.npz | 744898 | ab86baea32601b68cf5cecca7057d40a77c9810a8f5f7c4ba0a0691a8878abb3 | 7596 | 24 |
| chunks/scurve/2024-06-15.npz | 143962 | 8d60c180f53fbeaed280aa8e0a826b052725b7754c1b52699716f11ba79035bc | 1464 | 24 |
| chunks/scurve/2024-06-16.npz | 138670 | ed84247816ebd97f25d9a58e6f9fef277c977e38a71dbb43e9b3caf4dd4cb043 | 1410 | 24 |
| chunks/scurve/2024-06-17.npz | 898954 | fb6a2944debe48ee12f3eca3ad306ad597e513bdb9fcc75f972e0b875d336028 | 9168 | 24 |
| chunks/scurve/2024-06-18.npz | 1079078 | a46c11cadc08859b15cdbe2f98dca50c266905a1f1739e5be2aef0de5a333b5a | 11006 | 24 |
| chunks/scurve/2024-06-19.npz | 377888 | f00b60f499f2c6981a57b19bcd5c617c808cf6f162afc0cfaa44a1341e835de4 | 3851 | 24 |
| chunks/scurve/2024-06-20.npz | 763224 | fde1f844c388c5bcde882802dbc4973c64982aadc95b92657ccbcbb93a7350e7 | 7783 | 24 |
| chunks/scurve/2024-06-21.npz | 744016 | 48a774428c1f75efc6cd8b81722a17151ef09c218c182d5fed34925154f467f3 | 7587 | 24 |
| chunks/scurve/2024-06-22.npz | 35770 | 70d40077c3578cc0dd58ea12b40a2ae2d098c6eace42d6c14d87c244f697d288 | 360 | 24 |
| chunks/scurve/2024-06-23.npz | 311934 | dcb2b3038cd79470a3799fb72a59a5f80ef7707c920438c119dd723d675d85b4 | 3178 | 24 |
| chunks/scurve/2024-06-24.npz | 1723820 | f87357da423795089ad70f8a0ce56a5ed7162a271c48251866fc5715ba4dd930 | 17585 | 24 |
| chunks/scurve/2024-06-25.npz | 802130 | 100c61b718669292191fc5ae797e376b35758315a7d4151af8a1686bf96859fc | 8180 | 24 |
| chunks/scurve/2024-06-26.npz | 595056 | 928c64ea2e4b672ef6f0cc2a694b724777c8ef4fae1f63b1d69405ef0c13d785 | 6067 | 24 |
| chunks/scurve/2024-06-27.npz | 467754 | cb9b31e2a9c70bf5bcb422a7ed79ab728d1825622405270296e4c638a3afcd25 | 4768 | 24 |
| chunks/scurve/2024-06-28.npz | 640332 | 772a769cd79c45b7c3443e00a895e44606428e3d7c809d0df279107f6b52978a | 6529 | 24 |
| chunks/scurve/2024-06-29.npz | 190904 | 7ee2a9ef48eaf1f42d44e2edfbee6c9aa3eb275a5caa1c69931160ea41ab0ef9 | 1943 | 24 |
| chunks/scurve/2024-06-30.npz | 348880 | e4dbba00ba68437463c8bb264acff85c80d7dab4e088633779a9907a28f97ed9 | 3555 | 24 |
| chunks/scurve/2024-07-01.npz | 455112 | 090d6e6aa33ea93c446378d22bb62a0aa01c0d6c4a312409002cabeeb1a9cbe6 | 4639 | 24 |
| chunks/scurve/2024-07-02.npz | 419146 | 9bf499ae824c3faba4e0fd0c080017a769a9b9ca37960c83ad45d6a2a0d2ca95 | 4272 | 24 |
| chunks/scurve/2024-07-03.npz | 839762 | a3fe26af74368c0cbbb60d737b15cc492514ab01c05d10e2aa80c5ed61ab8628 | 8564 | 24 |
| chunks/scurve/2024-07-04.npz | 1617294 | 3896715bd1f144685e772d2a067ac7734837661bf7376865939e87215800c8a6 | 16498 | 24 |
| chunks/scurve/2024-07-05.npz | 1515276 | 34756bb786e9ac5f567cc3519804d92849ff4298f07e043c7249e5a0a00a43cd | 15457 | 24 |
| chunks/scurve/2024-07-06.npz | 605738 | eb1f510650bf55faa431da7b16367003c7460e245a14349bf2b78afdd3bbfd3f | 6176 | 24 |
| chunks/scurve/2024-07-07.npz | 895524 | 92ed6d19a19b7092991eef6ee2cfb9ea38a89a580790e0568da8e38bcf87c755 | 9133 | 24 |
| chunks/scurve/2024-07-08.npz | 1525076 | b226289ba3d36e61e61cd7ad89aeba5397848e0f7432b8bcfaebbe2a7ce43b76 | 15557 | 24 |
| chunks/scurve/2024-07-09.npz | 847210 | f9edc771d38730a1a1a455b7c63af6176805432e722aaacdddfd60ef55658f9b | 8640 | 24 |
| chunks/scurve/2024-07-10.npz | 632492 | f018e5b9e666b4495bea5f2968d576fd3f3c1f65ab1369c7dc13a46d0faee620 | 6449 | 24 |
| chunks/scurve/2024-07-11.npz | 924434 | edf63165c575c1dfcaf2b767e86ee351ee81ec6ebb95abb3e33cc5a318e71dfb | 9428 | 24 |
| chunks/scurve/2024-07-12.npz | 816340 | 0027a55b2ada55ec05240e1c4c1cf5a5cf912363605e34e65b916fbf5e0b8304 | 8325 | 24 |
| chunks/scurve/2024-07-13.npz | 287434 | 14251562c1521030de575b1b9a001aed564a838c1855f563c0e585a85a466cf7 | 2928 | 24 |
| chunks/scurve/2024-07-14.npz | 574966 | 8dac7899b24aa863fe0c8e53db561055fa751fd992f0ac7680d6786f5148fc76 | 5862 | 24 |
| chunks/scurve/2024-07-15.npz | 1135526 | ba64f5dbf76ab318a2ab64f7d8ccbfb6c6b1732b254b3652f0c58f2265cacafc | 11582 | 24 |
| chunks/scurve/2024-07-16.npz | 1214906 | 6aa2b3f8ff48062294f3912ecb0ad0da3f21b73ded2b2da2360a90716bd655ac | 12392 | 24 |
| chunks/scurve/2024-07-17.npz | 1038114 | ed637ce2dcb43839553c9cadc7c0a024be1c5be95b7a05deec32bcb69dab51a7 | 10588 | 24 |
| chunks/scurve/2024-07-18.npz | 866418 | dee2e7c7fc5e09e477bbca37fa24929174784125d4c5bf23c9bd35499a243639 | 8836 | 24 |
| chunks/scurve/2024-07-19.npz | 964320 | 0d04204a7ddfbe7230fba4a03ec2e7c542a3c195d5fbf717cea91118263936f0 | 9835 | 24 |
| chunks/scurve/2024-07-20.npz | 389648 | 4fa5e01be14244e212e6d52cdc83102b622302b105d9b2802ef8eb82a637ebb3 | 3971 | 24 |
| chunks/scurve/2024-07-21.npz | 784392 | ef418d84cd1ec06b70ccd7364f74b45e6de79dcd2934375975777b5cab5af1cd | 7999 | 24 |
| chunks/scurve/2024-07-22.npz | 931882 | 365beb80ad1e4c40c4133bed128fbe25b4cd098e10213c59eb7d1a4f015a6ba9 | 9504 | 24 |
| chunks/scurve/2024-07-23.npz | 880138 | e5e5eca2153130f8f8ae379c493e09d4a1fd3c49fc6edb6d8fb4801619fe6e1b | 8976 | 24 |
| chunks/scurve/2024-07-24.npz | 654248 | e9bae051f2fc033bb4e856bc280c42dcd79dc50e01c5199774f6b25f918b3ee5 | 6671 | 24 |
| chunks/scurve/2024-07-25.npz | 868084 | c9442721a47bac6bed75207b05ed23ffd289e5e33a71585589b80f16e5accf11 | 8853 | 24 |
| chunks/scurve/2024-07-26.npz | 710696 | 3ff725531cd1a52c4983f68848de2727d422b969627c00b70b4949f05ea403b2 | 7247 | 24 |
| chunks/scurve/2024-07-27.npz | 847210 | 6accd75f38147a4613c971af3e97424c2c5a8e470a152b72d98a682cfc9e9de8 | 8640 | 24 |
| chunks/scurve/2024-07-28.npz | 423556 | a6a732c6141ea8fe154388640b7fd538535d3df492633fe64654c2ca27258f8e | 4317 | 24 |
| chunks/scurve/2024-07-29.npz | 990094 | 1c171dde2cc5a4429790e1b4fe3641476a4c41c0d6a750b44d29c7754d34e531 | 10098 | 24 |
| chunks/scurve/2024-07-30.npz | 863086 | cbcbe34343040736cadca54a50404e3cd9607276ebca55e13f3d02715c5836c0 | 8802 | 24 |
| chunks/scurve/2024-07-31.npz | 894348 | 60337f988dd0704b325116154ba55deb37f4ad7314722122bc472d6a3828f37a | 9121 | 24 |
| chunks/scurve/2024-08-01.npz | 1566530 | 66e040efd4c3c91589ebf136d26778620dae59ea109a67fdfcb424062facb9b7 | 15980 | 24 |
| chunks/scurve/2024-08-02.npz | 1656984 | 428fcdb8d84f11fdeabac24f0c85047ccff2e0db43ae9b16acd936b6d2060eb3 | 16903 | 24 |
| chunks/scurve/2024-08-03.npz | 951090 | f1e15fdb78c1a2d9bb661d2d89b56e1abadcb399aee838cc730280c2d9b9d850 | 9700 | 24 |
| chunks/scurve/2024-08-04.npz | 1423940 | 6e3e8218cb87bc0835d8d79bd44c281fe05ed493089bf0de55a8657ec18a4eb3 | 14525 | 24 |
| chunks/scurve/2024-08-05.npz | 4968306 | 914de2864edecf2e167212bd385788a9faf6bdc1ed50cc031112673f883a9db4 | 50692 | 24 |
| chunks/scurve/2024-08-06.npz | 1580250 | 7430d8f49259e0d936ae5f365512cb62153331ccc3d5b9be79f8f58d5c1258a6 | 16120 | 24 |
| chunks/scurve/2024-08-07.npz | 1459612 | b09794ecb44f62242b92f6a9f602b9bd8dd7e0db278b0a35ed7c822dbab2e6a6 | 14889 | 24 |
| chunks/scurve/2024-08-08.npz | 1418550 | 41cd8a731cfb5fe57aba1d850b0493e04619b9cc7b806b1ae2bca2cd0661e625 | 14470 | 24 |
| chunks/scurve/2024-08-09.npz | 1060066 | b9bbf8e68e91dcb109e7f3299bb2003090bdd614c82ee47936bd794efcc94eb4 | 10812 | 24 |
| chunks/scurve/2024-08-10.npz | 335748 | 510e34e0730348c0b7d350b36a1215bf7cf7a44439656fd31e64d0e802a9e36e | 3421 | 24 |
| chunks/scurve/2024-08-11.npz | 906304 | 4644d5acf4567a678499a2a92e7d1429babd9710b3ac46ffb7cf4f105eddf541 | 9243 | 24 |
| chunks/scurve/2024-08-12.npz | 1163554 | 731afa3a34156a2e9eba03eca120cbbd3ae5849c7513a7e07f0db70c717e301b | 11868 | 24 |
| chunks/scurve/2024-08-13.npz | 963438 | de2c766d508e4c0ba8eabb5deefb5804a66a054b08daa0359f78d9c7a912911c | 9826 | 24 |
| chunks/scurve/2024-08-14.npz | 858088 | 4b3b5a6ebbb66a2ca533acbf980d0f57afd7a1a8c79f9017ec8169c6ee54d08f | 8751 | 24 |
| chunks/scurve/2024-08-15.npz | 1101128 | ba527ac714ff37385d78c73f21e6582b0ec4ed5755644ab20a151c7d462a1128 | 11231 | 24 |
| chunks/scurve/2024-08-16.npz | 992544 | 0223e2ffc08e6e2efc4f5a690e1fb09ef38869b2b51a5b4d809d3983fc75b4dd | 10123 | 24 |
| chunks/scurve/2024-08-17.npz | 200312 | 68b8cead1536a2c4846e5a074166b28dea511502a1d93b1c00c4e7022e1809b8 | 2039 | 24 |
| chunks/scurve/2024-08-18.npz | 561344 | 935795bcea550c2c8eb039f45ae08a8e00e459276b12ffa1c4f91180cece264c | 5723 | 24 |
| chunks/scurve/2024-08-19.npz | 601426 | 1b1729c37ddcb024473787157b4e1724f0a14c3f2fbbd66b383b6ab4d0371318 | 6132 | 24 |
| chunks/scurve/2024-08-20.npz | 740684 | 7d9eb13577b0fd9720e555df2e1f85c325f1cf9f9ce09576414fc0627b515b09 | 7553 | 24 |
| chunks/scurve/2024-08-21.npz | 821828 | 890163b1705afcff9b32d09bece3d5ad67b8eb5ada87ea6421857c95c1e6efa1 | 8381 | 24 |
| chunks/scurve/2024-08-22.npz | 630140 | 61f872a81ba908bc3f95eefd7dec32e8bf3e171c0965a9fa39f931c1fdeb7908 | 6425 | 24 |
| chunks/scurve/2024-08-23.npz | 966574 | dac954a97e598e3991ebae7cdfc5816d4564b6d2a6deea1a756f023c6fc80bc6 | 9858 | 24 |
| chunks/scurve/2024-08-24.npz | 437766 | a675ada1fb2c91aca113b651d69e8747732606ffd36da0391721283c86e23855 | 4462 | 24 |
| chunks/scurve/2024-08-25.npz | 339962 | faeeabf866f8bbba5d5ff486e8e3a52ca0a06e039cd412c48150069f6ae03e67 | 3464 | 24 |
| chunks/scurve/2024-08-26.npz | 660618 | d1b9aaedfa7b7cc6f0745bda1277543b9e18e10a6ef4caf4b9dd879aed616382 | 6736 | 24 |
| chunks/scurve/2024-08-27.npz | 988232 | b838b0018de575a8c9695a44ef763b4d0a74d36463b0a5ecde4ff742cb61092b | 10079 | 24 |
| chunks/scurve/2024-08-28.npz | 1083194 | 9a43acec2b79aff6cccf3b418d6fd73b677a0f2acca7e63c23355d240051f360 | 11048 | 24 |
| chunks/scurve/2024-08-29.npz | 840546 | 2e22a8d1f19e8a34821d32bd61c55e125486f794090b539085ffaa54191d6989 | 8572 | 24 |
| chunks/scurve/2024-08-30.npz | 728336 | 012e5aca09b6d0aeb511d3d422c47bba68e9fc7500e210dea26edd0097433070 | 7427 | 24 |
| chunks/scurve/2024-08-31.npz | 141806 | 4b187e3b7ea07a879e5f20541804bac3e8a869b4f96cfab1426d9139ddd5ea20 | 1442 | 24 |
| chunks/scurve/2024-09-01.npz | 874258 | 7795f051081cf8768106c54efbcd28b6003ab056612a7774b11cadc6dd056877 | 8916 | 24 |
| chunks/scurve/2024-09-02.npz | 491568 | 0db63b1442e50b9c1d810226f5ce3d0fa7824ed96bfc1b0636276702bb2d4f58 | 5011 | 24 |
| chunks/scurve/2024-09-03.npz | 687078 | 84737d33b8d4f51d5d21c5a2ca3fd91cf6da9599d55f48d02033fd82d315d686 | 7006 | 24 |
| chunks/scurve/2024-09-04.npz | 758128 | dfe2973892285593d35ab623bd072780dfb84b59c581f553b190d4d40292f0e7 | 7731 | 24 |
| chunks/scurve/2024-09-05.npz | 672966 | d5616d8349c269ea194d99ac91c1848a951ad9dc5d2694c59b28d744b8fa1091 | 6862 | 24 |
| chunks/scurve/2024-09-06.npz | 1217454 | f35411dfeacdbf98e2d053fa4f66f5aed58c483a38064720ce804d349a04e6a6 | 12418 | 24 |
| chunks/scurve/2024-09-07.npz | 411306 | 0c281652cc1326e4007f9b91d6925b7d2f7ff0eb9193857dfe1606f2bc8238d5 | 4192 | 24 |
| chunks/scurve/2024-09-08.npz | 455210 | dbbf735442c1de5c516bc08611039924c8955cc8476f2bdc92c4db43aac26820 | 4640 | 24 |
| chunks/scurve/2024-09-09.npz | 990192 | 41b1dc709ac8472fe9fbe446265cad0a456840758d652bfecd6089c5918be5c5 | 10099 | 24 |
| chunks/scurve/2024-09-10.npz | 802326 | f3d8a6da147afaa6d43e02f641247faa5d37d61705b4375d1dd8cdf78baca3e6 | 8182 | 24 |
| chunks/scurve/2024-09-11.npz | 982842 | 9bd620f81d1fa5930b80a6f7674908b7a4099e90251975923dd1256712f911aa | 10024 | 24 |
| chunks/scurve/2024-09-12.npz | 695408 | 72710e2c9335bc646384e4c5f80d287dcb763d54df4505d75d8aa164c9bd9a38 | 7091 | 24 |
| chunks/scurve/2024-09-13.npz | 744996 | 4adbab80d96d1f77c95f215468ec7e25d2719c13647939e9388584082ceec1df | 7597 | 24 |
| chunks/scurve/2024-09-14.npz | 250096 | 4610e4c7cff2d239fa8eadbad97b2e08ca5be86c4c88598a1b66efebdc92e156 | 2547 | 24 |
| chunks/scurve/2024-09-15.npz | 334572 | 91051c06d431d1c6b253e43e6d30e7f2d656d4e3ed2dcf14b3c7efcb0cb42afa | 3409 | 24 |
| chunks/scurve/2024-09-16.npz | 793016 | cb638967a0465c2738a1f8da7bec7c55f78686a76aed0211ebf31807c354c33b | 8087 | 24 |
| chunks/scurve/2024-09-17.npz | 858382 | 9c23c08eed2f4d8c4256945b71432758b1b0f71d621663f821cdb5111d2ae8b5 | 8754 | 24 |
| chunks/scurve/2024-09-18.npz | 1014300 | 9d7b3847ff65ea34c786a640be4caf4c3e4c291063a069a2becd44bf38b31483 | 10345 | 24 |
| chunks/scurve/2024-09-19.npz | 884450 | 68e01fa0dbcecbf371bffb5322b8ed3167d1c51e1791bc415d45940472cadbdf | 9020 | 24 |
| chunks/scurve/2024-09-20.npz | 676886 | 4de85ca96ad569f41541c66260e86aacebf80b0ebff4eeb382410fc81b42caca | 6902 | 24 |
| chunks/scurve/2024-09-21.npz | 140140 | effd69fd93cace8fe6cd976c58c0755e8886182770bba12ede40984e8b1da95b | 1425 | 24 |
| chunks/scurve/2024-09-22.npz | 581434 | 4d56ef8d6f36bfe1f0fc438bf5d68e35cfe981aa7258c18751cecf3c2d91b8d0 | 5928 | 24 |
| chunks/scurve/2024-09-23.npz | 575554 | 43cb680421bc65ed0e5eb2751ab9bac52faae9225ef7e9c0e86351550f77a134 | 5868 | 24 |
| chunks/scurve/2024-09-24.npz | 820848 | 3de193dd16e0b384738df947fc7f22a4a0d7b0fcaf7da5a494544e5723d5d763 | 8371 | 24 |
| chunks/scurve/2024-09-25.npz | 466186 | 902220df5a56e023b31df820680421648ee09f720fbff7448a98752b272b044a | 4752 | 24 |
| chunks/scurve/2024-09-26.npz | 895720 | e24574ab71415fa2b64f07e0030ab404b3b251689bcd7a1818392844d7826bf3 | 9135 | 24 |
| chunks/scurve/2024-09-27.npz | 659834 | 27da5f4ce768b54c4bcddf4d55f4706015153226dee405b860f900180e47d25a | 6728 | 24 |
| chunks/scurve/2024-09-28.npz | 237552 | 9a10230e3a5e0d13961e347cab502ad045f2318c5ad3ec1e50345541be7f5582 | 2419 | 24 |
| chunks/scurve/2024-09-29.npz | 199822 | d32e428056ca0f6807a9c19767b3747cb7f5ec34f1bdfbb9e412108b63364a97 | 2034 | 24 |
| chunks/scurve/2024-09-30.npz | 999208 | 099b05dde96974959746923aff4d1f0f21132e381208b17f2b5ddb3e653e4f42 | 10191 | 24 |
| chunks/scurve/2024-10-01.npz | 1201676 | e82530ebd983380d1b3f3c4bb2c4fe3f808ce0883b41b8da8fe655133d56b9f8 | 12257 | 24 |
| chunks/scurve/2024-10-02.npz | 987546 | c3d7b4e0f58bf3ada981ab7307df5e42c82bd36ebe9e7be2e8f87995a1f02fd9 | 10072 | 24 |
| chunks/scurve/2024-10-03.npz | 855834 | c7748670f42a39968f3ed619128671252a37e1a6ca740779df377abd9ed1d4a1 | 8728 | 24 |
| chunks/scurve/2024-10-04.npz | 696976 | 1efcb40283282e83233beb5c1e3e7eb1e03172a67908645250c47ca62d1c5939 | 7107 | 24 |
| chunks/scurve/2024-10-05.npz | 263718 | 8b58a155a83600f3659356bc90f1a60ee88e075bc2444c122bc079ac9c9b1ae0 | 2686 | 24 |
| chunks/scurve/2024-10-06.npz | 329476 | 8ba6930fb3eafd3ec6eee17bd2314adeb2f752860f2c623105ff31b713f4432f | 3357 | 24 |
| chunks/scurve/2024-10-07.npz | 943740 | d567d2e39b9fec928d9dd0c7b6cb32f0afabf0fadc7740519a0e61b54746c06f | 9625 | 24 |
| chunks/scurve/2024-10-08.npz | 596820 | 56bb4022e94331e62e3548efe731c92d3be7bad4c55d4a61759a708b52d374b8 | 6085 | 24 |
| chunks/scurve/2024-10-09.npz | 607600 | 444720ac3b38ff4861ba107cba3fa71468e05bf24ffb02fd0b666364486da897 | 6195 | 24 |
| chunks/scurve/2024-10-10.npz | 844662 | 28ce96739be6b3c65d76a744f280fd5dbcb2e823e5ed33f419320abb8ab42abf | 8614 | 24 |
| chunks/scurve/2024-10-11.npz | 560364 | 98641c735d9ad226160dd7661d3865b1f56cb64ee4f1f60b092932e206c750dd | 5713 | 24 |
| chunks/scurve/2024-10-12.npz | 263914 | 898eaf780912d76c2eb2ee6ddc0be76903d634f5141df6e1ca2f141274427c31 | 2688 | 24 |
| chunks/scurve/2024-10-13.npz | 510482 | 6fa1f238f767b4c264f7f1169da6cd3ff0decb02402c3f67c52829bd62bb7cec | 5204 | 24 |
| chunks/scurve/2024-10-14.npz | 281652 | aace636edd7b9b55a558d9b85c1b63ab9032c938718aa99f068ce794fa47b70c | 2869 | 24 |
<!-- /BLOCK -->

<!-- BLOCK:manifest_log -->
出所: 走らせの記録

| ファイル | バイト | sha256 | 行数 |
|---|---|---|---|
| data/c9_run_a/full.log | 30314 | 7b070b673a7d4a575a75082380ad265b91c7a04028a43fc02e778deccc36ad6d | 485 |
<!-- /BLOCK -->
