# データ品質保証の完了条件(2026-09-05、オーナー指示: これが終わるまでフェーズ 2 は始めない)

「終わった」を測れる条件に落とす。各項目は実機(オーナー PC)の成果物で確認したときだけ「済」にする。

| # | 条件 | 確認方法 | 状態 |
|---|---|---|---|
| 1 | 全ファイルに schema がある(`schema_undefined` = 0) | オーナー PC の `QUALITY.json` で 0 | VM で 0(schema 35 件)。オーナー PC は 14:03 UTC 時点 134(17 schema のプッシュ前)→ 次回 fetch_all で 0 の見込み |
| 2 | 品質点検の全フラグが「説明済み」か「修正済み」のどちらかになっている | データセットごとの点検台帳 `docs/DATA_QA_TRIAGE.md`: フラグ種別 × 件数 × 判断(仕様どおり / 既知欠陥として schema に記載 / 収集側の修正 / 未解決) | 作業中(14:03 UTC の修正版レポートで台帳化中) |
| 3 | 台帳がオーナー PC で毎回生成・共有される | 2 回連続の share で `INTAKE_latest.json` の生成時刻が更新 | **済**(13:46 と 14:18 UTC の 2 回、1,595 → 1,602 ファイル) |
| 4 | 保持期限スナップショットが 6 ソース全てで作成される | オーナー PC の `backtest_data/auto_*` が 6 種 | 3/6(OKX 3 種は収集開始後の次回 fetch_all で作成される見込み) |
| 5 | 既存スナップショットの完全性(MD5SUMS があるものは全一致、無いものは作成) | `scripts/verify_snapshots.py` を VM とオーナー PC で実行し不一致 0 | VM 側: 実行済み(MD5SUMS の無かった 13 ディレクトリに新規作成、不一致 0)。オーナー PC: fetch_all に組込み、次回共有で確認 |
| 6 | 板記録の切断 34 本について、読み出し可能範囲を記録し、新規記録が完結していること | `scripts/repair_gz_listing.py` の出力を共有、新規ファイルが `truncated` でない | fetch_all に組込み済み(WS_GZ_LISTING.json)。次回共有で確認 |
| 7 | 既知のデータ損失の台帳がある | `docs/DATA_LOSS_REGISTER.md`: 何が・いつからいつまで・なぜ・復旧可否 | **済**(`docs/DATA_LOSS_REGISTER.md`) |
| 8 | 定数の出所: `assumed` / `null` の定数が判定に使われない仕組み(`require_source`)と、未計測定数の一覧 | `config/constants.yaml` の `assumed`/null 一覧 + 各々の計測計画 | **済**(`scripts/constants_inventory.py`、`docs/CONSTANTS_TODO.md`)。計測は各項目の計画どおり |
| 9 | ダッシュボードの「データ台帳」表が実機で表示される | オーナーのスクリーンショット | 未確認 |
| 10 | 単一の真実: 研究側の読み手が共有コピー(`paper_logs/`)を読み、読んだコピーを出力に書く | `gates.shared_or_local` の利用箇所の棚卸し + 直読みの残りを列挙 | **済**(`docs/SINGLE_SOURCE_AUDIT.md`: 研究側の直読み 11 件を共有コピー経由に修正、読んだコピーを出力に表示) |

完了の宣言はリードが本表を全て「済」にし、オーナーが承認したときに行う。
