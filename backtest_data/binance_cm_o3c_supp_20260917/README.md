# binance_cm_o3c_supp_20260917 — `binance_cm_o3c_20260913` の補遺(1 日分)

取得日: 2026-09-17(この環境、`curl` で `data.binance.vision` から)。
中身: `aggTrades/BTCUSD_PERP/BTCUSD_PERP-aggTrades-2023-06-24.zip`(1,178,051 バイト、展開して 89,972 行 + ヘッダ)と公式 `.CHECKSUM`(sha256 一致を `sha256sum -c` で確認)。

理由: 本体スナップショットの aggTrades は 2023-06-25 から始まるため、1 件目(価格帯の観測表、`docs/PHASE2/O3C/PRICE_LEVEL/DESIGN_2026-09-17.md`)の窓 W = 24h が最初の日だけ短くなっていた(監査役の指摘、`docs/AUDITOR/VERDICTS/2026-09-17_price_level.md` 3)。本体の単位(MD5SUMS 封印済み)には手を入れず、別単位として置く。使うときは両方を 1 つの根に重ねる(`scripts/o3c_price_level_table.py --data-root` に、両方へのシンボリックリンクを束ねたディレクトリを渡す)。
