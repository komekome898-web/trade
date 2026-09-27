# 画面の値と実行記録のファイルの値の突き合わせ

委任文 §2-6「表示の値と実行記録のファイルの値を 3 か所以上突き合わせる」。画面 = `scripts/dashboard.py --port 8300 --runs-dir backtest_runs/k1_newenv_a` のバックテストのタブを Playwright(Chromium `/opt/pw-browsers/chromium-1194`)で開き、各タブの `#bt-body` の文字列を `shown_values.json` に写した(写し = `*.png`)。ファイル = 同じ実行の `record.json` / `metrics.json` / `repro.json` / `data_quality.json`、および外側の `docs/PHASE2/K1/PREREG.md` の sha256sum と `FOLD_MANIFEST.json`。

一覧のタブに出た実行の数: 47(撮影時点で `backtest_runs/k1_newenv_a` にあった実行)。

| 実行(升) | 画面の欄(タブ) | 画面に出た値 | ファイルの値(出所) | 一致 |
|---|---|---|---|---|
| `34624564bf77`(60|s19/b24|both) | 往復の数(概要) | `6726` | `6726`(metrics.json trades.n) | 一致 |
| `34624564bf77`(60|s19/b24|both) | 1 件ごとの bp の平均(概要) | `-2.76275` | `-2.76275`(metrics.json trades.mean_bp) | 一致 |
| `34624564bf77`(60|s19/b24|both) | 事前登録の sha256(再現性) | `a36bbf51dba5822c2ff20e4045ef0332531499e05782adb8e066ec2a72207082` | `a36bbf51dba5822c2ff20e4045ef0332531499e05782adb8e066ec2a72207082`(record.json prereg_sha256) | 一致 |
| `34624564bf77`(60|s19/b24|both) | 事前登録の sha256 = PREREG.md の sha256sum(再現性) | `a36bbf51dba5822c2ff20e4045ef0332531499e05782adb8e066ec2a72207082` | `a36bbf51dba5822c2ff20e4045ef0332531499e05782adb8e066ec2a72207082`(sha256sum docs/PHASE2/K1/PREREG.md) | 一致 |
| `34624564bf77`(60|s19/b24|both) | データの sha256(前提) | `cafe2ea91c83ccd1c2691d2a7dee124a8b7eb93930ef8498228c5f005559f5be` | `cafe2ea91c83ccd1c2691d2a7dee124a8b7eb93930ef8498228c5f005559f5be`(FOLD_MANIFEST.json outputs) | 一致 |
| `34624564bf77`(60|s19/b24|both) | 読んだ行 / 残した行(データ品質) | `26276 / 26276` | `26276 / 26276`(data_quality.json manifest.files[0]) | 一致 |
| `34624564bf77`(60|s19/b24|both) | taker 手数料(円)(費用) | `0` | `0`(metrics.json costs.taker_fee) | 一致 |
| `0496c25877ee`(15|s19/b24|both) | 往復の数(概要) | `14751` | `14751`(metrics.json trades.n) | 一致 |
| `0496c25877ee`(15|s19/b24|both) | 1 件ごとの bp の平均(概要) | `-2.68625` | `-2.68625`(metrics.json trades.mean_bp) | 一致 |
| `0496c25877ee`(15|s19/b24|both) | 事前登録の sha256(再現性) | `a36bbf51dba5822c2ff20e4045ef0332531499e05782adb8e066ec2a72207082` | `a36bbf51dba5822c2ff20e4045ef0332531499e05782adb8e066ec2a72207082`(record.json prereg_sha256) | 一致 |
| `0496c25877ee`(15|s19/b24|both) | 事前登録の sha256 = PREREG.md の sha256sum(再現性) | `a36bbf51dba5822c2ff20e4045ef0332531499e05782adb8e066ec2a72207082` | `a36bbf51dba5822c2ff20e4045ef0332531499e05782adb8e066ec2a72207082`(sha256sum docs/PHASE2/K1/PREREG.md) | 一致 |
| `0496c25877ee`(15|s19/b24|both) | データの sha256(前提) | `e3f705461b49c5ebb7a2b3c82e0a9f93a929069c9998c1a347c63d08993355a9` | `e3f705461b49c5ebb7a2b3c82e0a9f93a929069c9998c1a347c63d08993355a9`(FOLD_MANIFEST.json outputs) | 一致 |
| `0496c25877ee`(15|s19/b24|both) | 読んだ行 / 残した行(データ品質) | `105056 / 105056` | `105056 / 105056`(data_quality.json manifest.files[0]) | 一致 |
| `0496c25877ee`(15|s19/b24|both) | taker 手数料(円)(費用) | `0` | `0`(metrics.json costs.taker_fee) | 一致 |
