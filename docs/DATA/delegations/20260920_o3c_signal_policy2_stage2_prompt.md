# 委任: 方策の模擬 段 2 — 後半 2,000 本の連鎖に一度だけ(2026-09-20)

## 0. 対応表(CLAUDE.md §0.1)
段 1 の委任文 `20260920_o3c_signal_policy2_prompt.md` §0 と同じ(L-269・L-272・L-274・L-321・L-323・L-260)。

**出力はすべて日本語(code の文字列は英語)。判定語を書かない。`paper_logs/` を開かない。Jev を呼ばない。前半で固定したもの(logistic の定数・npz・帯・行動の表)を変えない、後半で再計算しない。後半 2,000 本は一度だけ(再実行は同じ種で同じ結果になる冪等な形。乱数の種 20260920)。Do not commit. Do not push。**

## 1. 読むもの
段 1 の委任文と報告、設計(改訂 2。**出口 = 連鎖の終わり + d、方策 6 本**の訂正あり)、反証者レビュー 8 `REFUTER_REVIEW8_2026-09-20.md`(致命があればリードが直してから、この委任が出る)、`scripts/o3c_signal_policy.py`。

## 2. 作るもの
1. 母集団: 後半(half == 後半)の連鎖(`bundle_id`)のうち、前段の較正サンプル 5,000 件(`backtest_data/o3c_signal_continue_20260920/jev/selection_manifest.json`)を含む連鎖を除いたもの。その総数と除いた数を書く。種 20260920 で 2,000 本を抜く。
2. 段 1 と同じ道具で 6 方策 × 型 × 遅れ 0.5 / 1 / 2 秒を回し、`backtest_data/o3c_signal_policy_20260920/stage2_secondhalf/` に段 1 と同じ構成(cascades / prints_policy / dist_table / position_breakdown / judge_counts / action_counts / tables.md / summary.json / MD5SUMS)で置く。logistic の生の確率は追跡ファイルに書かない(帯の 3 択だけ)。
3. 報告 `docs/PHASE2/O3C/SIGNAL/POLICY_STAGE2_REPORT_2026-09-20.md`: (0) 行数・数値セル数 / (1) §0 の表 / (2) コマンド / (3) 母集団と抜いた連鎖の内訳(単発 / 2 件 / 3 件以上、日数)/ (4) 表(dist_table・位置別・件数)/ (5) 設計に無い判断(全部)/ (6) サニティ(固定したものの MD5 が段 1 と同じ、全部逆張りと全部順張りの符号反転、欠測)/ (7) 限界 / (8) 作ったファイル / (9) テストの末尾行(全スイート、`-q` 無し)。**判定はしない(リードが書く)。**

## 3. 制約
read-only・冪等。既定値を変えるなら列挙して理由を書く。モデル名を書かない。上に書いたファイル以外を変更しない。
