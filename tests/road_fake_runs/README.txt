作り物の道の走らせ(ダッシュボードのバックテストの表示の試験・確かめ用。本物の戦略の結果ではない)。
runs/<run_id>/ = record.json・repro.json と road/(道の記録 road-record-7)だけ。
作り方: メインの作業ブランチの道のコード(src/bot/bt/pipeline.py、src/bot/bt/road/)に PYTHONPATH を向け、
  python make_fake_runs.py <メインの src> <出力先>
足は本物の bitFlyer FX_BTC_JPY の 1 分足(2020-03-11〜03-14、封印の前)。make_fake_runs.py は pipeline の乱数の生成器を
本物の足の読み出しに差し替えて走らせる(だから record.json の generators は random_walk のまま。作り物)。
fake_road_demo.py = 作り物の戦略(段のある指値)。road_scene_strategy.py = メインの tests/road/road_scene_strategy.py の写し。
