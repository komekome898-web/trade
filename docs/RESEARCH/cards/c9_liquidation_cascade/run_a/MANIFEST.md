# カード 9 (a) 全期間の走らせの出力の台帳(2023-06-25〜2024-10-14、Binance COIN-M)

元の置き場: `data/c9_run_a/full_20230625_20241014/`(`.gitignore` の `data/` で git の外)。結果の文書は `RESULTS.md`。
表はすべて `make_tables.py --section manifest` の出力をそのまま埋めた(sha256 は hashlib、行数は gzip を開いて数えた)。

- `run_a/` に写したもの: 委任文の一覧どおり `dist_*.csv`・`label_counts.csv`・`policy_*_counts.csv`・`three_way_calibration.csv`・`three_way_model.json`・`run_meta.json`。
- 写していないもの: 委任文で「写さない」とされた大きい gz(`anchors_prints`・`controls`・`policy_cascades`・`policy_legs`・`jev_states`)。
- **委任文の一覧に名指しの無い 2 つ**: `anchors_bundles.csv.gz` と `three_way_probs.csv.gz`(どちらも `.csv.gz`)。「写す」一覧の `three_way_*.csv/json` に `.csv.gz` が入るかは書かれていないので、写さずに下の表に載せた(作業者の判断。写すかはリードが決める)。
- `chunks/`(日ごとの途中の出力)は載せていない(第 2 稿の `make_tables.py` は `chunks/scurve` と `chunks/controls` の見出しを読む)。
- 第 2 稿で足した `control_iv.py` の出力 `run_a/control_iv_out/`(対照 (iv)・起点を変えた react・(ii) の流し直し)は、リードの指示で `run_a/` に置いた。sha256 と行数は表 manifest_iv。
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
出所: `control_iv.py` の出力(この回の追加の計算)

| ファイル | バイト | sha256 | 行数 | 数え方 |
|---|---|---|---|---|
| run_a/control_iv_out/control_iv_meta.json | 3126 | c65105aee629e59d835c62cf27aae3fc82464bf152132d3ccf06254e1b753de1 | - | json(行の表ではない) |
| run_a/control_iv_out/controls_iv.csv.gz | 4531456 | daded3273823226dd232daaa65dfed9c4b5ae29107293f0582a4901084538cbf | 16968 | 見出しを除いた行数 |
| run_a/control_iv_out/ii_reproduction.csv.gz | 1423248 | 593ec4b2c452d1784ad4228765f58613578c398eb92323237dfd86690af7843f | 53398 | 見出しを除いた行数 |
| run_a/control_iv_out/prints_reanchor.csv.gz | 10005668 | 4a3444d1774ea43749787c95b1d25bb0d5915bf25566097851794d1702423663 | 53398 | 見出しを除いた行数 |
<!-- /BLOCK -->

<!-- BLOCK:manifest_log -->
出所: 走らせの記録

| ファイル | バイト | sha256 | 行数 |
|---|---|---|---|
| data/c9_run_a/full.log | 30314 | 7b070b673a7d4a575a75082380ad265b91c7a04028a43fc02e778deccc36ad6d | 485 |
<!-- /BLOCK -->
