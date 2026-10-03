# W4 の測定の台本(研究の作業場所から移した、2026-10-03)

カード 5〜8 とカード 4 の測定に使った台本(はじめは会話の作業場所 scratchpad にあった。測定用のセッションでも動かせるようにリポジトリに置いた)。
- `run_b2.py`: 1 枚のカードの 1 変種を、暦年の区切りで読んでつないで走らせ、日ごとの軽い測定を書く。`--check` は区切りの同一性の照合。
- `light_b2.py`・`daily_stats.py`: 日ごとの損益の系列からの軽い測定(L-556)。
- `common.py`・`run_v2.py`・`post.py`: 読み込み・区切り・書き出しの共通部。`common.py` の `ROOT` は `/home/user/trade`。
- `c4_map_part0{0,1,2}.txt`: カード 4 の地図(族 (2)、L-565・L-567)の変種のうち、測定用のセッションに分けた残り。

使い方: `PYTHONPATH=src python3 scripts/w4_measure/run_b2.py --card c4 --variant <変種>`(出力は `docs/RESEARCH/cards/c4_owner_matilda_range/measure/<変種>/`)。目標の列の表は `python3 docs/RESEARCH/cards/tools/goal_table_c4.py <変種>`。
