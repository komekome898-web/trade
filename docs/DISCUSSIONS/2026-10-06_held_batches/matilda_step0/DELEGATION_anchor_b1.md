# 委任文: 直し B1 — 1 段目の約定値段からの距離で値段が決まる段(取引所の模型・道の土台・表・検査)

種類: 作る

1 版目。オーナーの決め L-815「1.c」・L-816「1.a」・L-817(問い 1・2 とも a)の仕組みの側。マチルダがこの仕組みを使う形と、自分の注文どうしの交差の扱い(L-816「3.a」)は直し B2 の委任で、この委任には入れない。受け入れはリードが書いた実行できる試験 `tests/road/test_anchor_b1_spec.py`(場面の戦略 `tests/road/road_anchor_strategy.py`)。直し A(`DELEGATION_matilda_v37_fixA.md`)を受け取った後に渡す(どちらも `src/bot/bt/road/` を直すため)。

## 着手前の表

作業者は、着手の前に「やろうとすること × オーナーの原文の該当語(逐語)」の 2 列の表を出す(CLAUDE.md §0.1 のまま)。この委任文は、検めと事前の批評の後にオーナーの承認を受けてから渡す(L-793「**委任文の検査が通ったのち、私に委任してよいか聞き、私の承認が得られてから委任すれば右の列は私の承認済のものになるでしょ。**」)。承認の逐語は末尾の `## オーナーの承認` の節にある。右の列には、承認の逐語と、その行の根になる委任文の節の名前(例: 取引所の模型を直す行は「作るもの」の 1、試験を通す行は「受け入れ」)を書く。委任文のどこにも書かれていないことをする行は右が空になり、その行は着手せず「問いとして返したこと」に書く。

## 目的(オーナーの逐語)

- L-815「**1段目を基準にそれ以降の足をステップ毎の値段で約定させないとナンピンにならない**」
- L-816「**1.a**」(リードの問いの例: 段 7,000,050・6,999,950・6,999,850・6,999,750、間隔 100、次の足 始値 6,999,800・安値 6,999,700 → 1 段目は始値 6,999,800 で約定、2 段目からはその約定値段を基準に 100 ずつ下(6,999,700・6,999,600・6,999,500)で、値段が届いたときだけ約定。この例では 2 段目だけ)
- L-817「**問い 2(B-1) a**」(1 段目が約定した足の中で 2 段目以降を約定させるのは、良い側・悪い側の両方)
- L-791「**測定に限らず全ての委任において、委任のミスでやり直しが発生しない委任文の書き方と仕組み**」
- リードの設計(オーナーの逐語ではない): 段の値段は注文を出すときには決まらない(根の約定値段で決まる)ので、取引所の模型に「根に付いた段」の注文の形を足す。今の「建てに付いた決済」(`attached_to`)と同じ置き方にする。

## 作るもの

1. 取引所の模型 `src/bot/bt/fill/venue.py` に、根に付いた段の注文を足す。
   - 注文の `OrderRequest.extra` の鍵 `anchored_to`(根の client_order_id)と `anchor_offset`(距離、0 でない有限の数)。知らない鍵を拒む所(`src/bot/bt/fill/venue.py:552`)に足す。段は GTC の指値で、値段は無い(`price` = None)。
   - 段は根が最初に約定するまで何も効かない(今の決済の「attached」と同じ待ち方)。根の最初の約定値段 F で、段の値段 = F + 距離 を銘柄の刻みに切り捨てた値段(売りも買いも切り捨て。L-783、`src/bot/bt/road/strategy.py:39-41`)。根の 2 回目からの約定では変えない。根が「範囲の内」で約定しても「始値」で約定しても、F はその約定値段。
   - 値段が決まった時刻から待つ(`rest_since` = その時刻)。根が約定した足で、段の値段が足の範囲の内(安値 ≦ 値段 ≦ 高値)なら、段の値段で約定させる。良い側・悪い側の両方(L-817)。約定の印は (bar_rule, attached_exit, "anchor_bar")。次の足からはふつうの指値(bar_rule)。
   - 根が約定した足の処理は、`_tier2_bar` が足の始めに並べた注文の輪(`src/bot/bt/fill/venue.py:949-974`)の途中で起きる。その途中で値段が決まった段も、同じ足で上のとおり試す(輪の中の並べ直しに頼らない)。
   - 効き始めた段は、今の決済が効き始めるときと同じく、自分の反対の注文と出会う(決まり self_trade。`src/bot/bt/fill/venue.py:342-373`)。
   - 段に付いた決済(`attached_to` = 段)は、段が約定してから今の決まり(attached_exit)で効く。
   - 根が何も約定せずに閉じたら(取り消し・拒否・取引所が閉じた)、まだ効いていない段を `Canceled` 理由 "anchor_root_closed_unfilled" で閉じる(`attached_parent_closed` と同じ置き方。`src/bot/bt/fill/venue.py:375-390`)。効いていない段の取り消しは受ける。
   - 根が知らない番号・既に閉じた・既に約定した・段や決済の注文・売買が違う段は拒む(`Reject`。理由の語は作業者が決めてよい)。
2. 道の土台 `src/bot/bt/road/strategy.py` の `place` と `place_with_exit` に `anchor=None`・`offset=None` を足す(試験の冒頭の注の口)。誤りは止める(試験 `test_v5_bad_anchor_refused` の 13 通り。根が既に約定した段も止める = `test_v3_level_after_root_filled_refused`)。段は値段を送らず、`extra` に `anchored_to`・`anchor_offset` を入れる。量は size_ref で写す(今の量の口)。モジュールの説明に口を書き足す。
3. 道の記録の表 `src/bot/bt/road/tables.py` の注文の表に、列 `anchored_to`・`anchor_offset`・`anchor_px` を足す(説明の文つき)。anchor_px は、土台が根の最初の約定の知らせを受けた時に、その時まだ閉じていない段に書く(F + 距離 を刻みに切り捨てた値段)。段の `limit_px`・`sent_limit_px` は空。受け付けられた指値の値段の突き合わせ(`src/bot/bt/road/tables.py:335-339`)は、段では anchor_px と比べる。
4. 検査 `src/bot/bt/road/check.py` の (vii) に、段の確かめを足す: anchor_px = 根の最初の約定値段 + 距離 を刻みに切り捨てた値段か / 根が無い・根が段や決済・売買が違う段は失敗 / 段の約定は根の最初の約定の時刻より前に無い / 根の約定の足での段の約定は fill_case "anchor_bar" で段の値段、ほかの足は今の bar_rule の決まりを anchor_px で当てる。指値の値段の検め(`src/bot/bt/road/check.py:1264-1278`)と約定の決まりの検め(`src/bot/bt/road/check.py:1300-1378`)は、段の行を空の limit_px で落とさない。新しい確かめは新しい関数に置く(直し A の検査の直しと重ねないため)。

決まりの正本は、上の「作るもの」と試験 `tests/road/test_anchor_b1_spec.py`(リードが書いた。冒頭の注に口がある)。**試験は変えない。**試験どうし、試験とこの委任文が食い違う、または試験とこの委任文だけでは決まらない、と気づいたら、そこで止めて問いとして返す(それに依らない部分は続ける)。

## 読んだ事実

| # | 事実 | 確かめ |
|---|---|---|
| データ | この委任は市場のデータを読まない。試験は tmp の根の下に書いた合成の 1 分足だけで走る(時刻 2023-11-14、封印の境より前) | この委任には無い(合成の足だけ) |
| 既存の決まり | 取引所の模型が知る extra の鍵は oco と attached_to だけで、ほかは拒む | `src/bot/bt/fill/venue.py:552` |
| 既存の決まり | 建てに付いた決済は、建てが約定するまで「attached」で待ち、約定で効き始め、自分の反対の注文と出会い、楽観側だけ建ての足で試す | `src/bot/bt/fill/venue.py:342-373` |
| 既存の決まり | 建てが何も約定せずに閉じると、付いた決済は理由 attached_parent_closed で閉じる | `src/bot/bt/fill/venue.py:375-390` |
| 既存の決まり | 1 分足の指値の決まり range_open: 待ち始めの後の足で、範囲の内は指値、約定する向きに範囲の外は始値 | `src/bot/bt/fill/venue.py:949-974` |
| 既存の決まり | 土台は指値を刻みに切り捨てて送る(売りも買いも。L-783) | `src/bot/bt/road/strategy.py:39-41` |
| 既存の決まり | 量の口 size_ref は、取引の最初の段の量の計算の列を写す | `src/bot/bt/road/strategy.py:405-485` |
| 既存の決まり | 表を作るとき、受け付けられた指値は取引所の模型が持つ値段と送った値段を突き合わせる(段は送った値段が無い) | `src/bot/bt/road/tables.py:335-339` |
| 既存の決まり | 検査 (vii) は、送った値段 = 計算した値段の刻みの切り捨て、と、約定を足の範囲・始値・建ての足で確かめる | `src/bot/bt/road/check.py:1264-1278`・`src/bot/bt/road/check.py:1300-1378` |
| 既存の決まり | 受け入れの試験は、作る前は全部落ちる(段の口が無い TypeError と、列が無い) | `PYTHONPATH=src python -m pytest tests/road/test_anchor_b1_spec.py` → 27 failed |
| 既存の決まり | 量は 7,000,050 円の買い・段数 2 で 0.009、6,999,950 円で 0.01 | `PYTHONPATH=src python3 -c "from bot.bt.road.strategy import size_detail, MARGIN_JPY, USE_RATIO; print(size_detail(margin_jpy=MARGIN_JPY, use_ratio=USE_RATIO, levels=2, price=6999950.0, quote_ccy='JPY', usdjpy_at_entry=None))"` → `(Decimal('0.01000007142908163629740212430'), 0.01)` |
| 既存の決まり | 直し A の記録の指紋の試験は、注文の表の列を足すと指紋が変わって落ちる(この委任ではマチルダは段を使わないので、変わるのは空の 3 列だけのはず) | `tests/road/test_matilda_v37_r2_spec.py:110-114` |
| 列の意味 | 注文の表の attached_to は、建てと一緒に出した決済の親の建ての番号 | `src/bot/bt/road/tables.py:190` |

## 決めてよいこと・決めてはいけないこと

| 選び | 決め |
|---|---|
| 出力の置き場 | 直すのは `src/bot/bt/fill/venue.py`・`src/bot/bt/road/strategy.py`・`src/bot/bt/road/tables.py`・`src/bot/bt/road/check.py` だけ。作業者が足したい試験は `tests/road/test_anchor_b1_extra.py` に置いてよい。走らせの出力は試験の tmp だけ |
| 分母・数え方 | この委任には無い(数えない) |
| 比べの方法 | 段の値段 = F + 距離 を刻みに切り捨て(売りも買いも)。範囲の内 = 安値 ≦ 値段 ≦ 高値(今の range_open と同じ等号) |
| 確かめ方 | 試験 `tests/road/test_anchor_b1_spec.py` と `tests/road` の全部が飛ばし 0 で通る(直し A の記録の指紋の試験だけは H5 のとおり) |
| 依存 | Python の標準ライブラリと、このリポジトリの今あるもの |
| 絞り方・選び方 | この委任には無い(測らない) |
| 単位・通貨のそろえ方 | 値段は値段の通貨(円)、距離も同じ通貨。量は size_ref で写す |
| 試験で決まらない内部の形 | 作業者が決めてよい(取引所の模型の段の状態の名前・拒む理由の語・関数の分け方)。決めたことを報告に書く |

## 変えないもの

- H1: 試験 `tests/road/test_anchor_b1_spec.py`・`tests/road/road_anchor_strategy.py` と既存の試験(`tests/road/` の今あるファイル)を変えない。確かめ: `git diff --stat tests/` が空。
- H2: 道の試験が全部通る(H5 の 1 件を除く)。確かめ: `PYTHONPATH=src python -m pytest tests/road --deselect tests/road/test_matilda_v37_r2_spec.py::test_a2_record_unchanged_on_walk` が全部 passed(飛ばし 0)。
- H3: 注文の表の今の列と、ほかの表の列を変えない(注文の表の終わりに 3 列を足すだけ)。確かめ: `PYTHONPATH=src python -c "from bot.bt.road.tables import SCHEMA; print({k: [c[0] for c in v['columns']] for k, v in SCHEMA['tables'].items()})"` の出力が、直す前と比べて注文の表に 3 列が足されただけ。
- H4: 約定の決まりの宣言・core・走らせ・戦略を変えない。確かめ: `git diff --stat src/bot/bt/fill/spec.py src/bot/bt/core src/bot/bt/pipeline.py src/bot/strategy` が空。
- H5: マチルダの記録は、足した 3 列のほかは変わらない。確かめ: 直し A の試験 `test_a2_record_unchanged_on_walk` と同じ走らせで、注文の表から 3 列を除いて 4 つの表の指紋を取り、試験の PINNED と同じ(コマンドと出力を報告に出す)。PINNED の取り直しはリードがする(作業者は変えない)。

## 壊す場面

| 場面 | 書いたこと |
|---|---|
| 封印の境 | この委任には無い(合成の足だけ。実データを読まない) |
| 日・足・期間の境 | U1(根が約定した足と次の足で、段の約定の当たり方が anchor_bar と range に分かれる)・U3(根を取り消した時刻と同じ時刻に段が閉じる) |
| 等号 | U1(段の値段 = 安値 ちょうどで約定)・U2(売りの段の値段 = 高値 ちょうどで約定) |
| 欠け | U3(根が約定しないまま閉じる → 段の値段が決まらない、anchor_px は空)・U5(距離・size_ref が無い) |
| 参照の値が無い | U5(知らない根)・U6(根の番号を書き換えると検査が落とす) |
| 拒否・状態不明・届かない | U5(誤った口は止める)・U3(根が約定した後の段は止める) |
| 遅れ | U4(段に付けた決済は、悪い側では次の足から) |
| 交差と後からの変化 | U3(段を取り消した後に根が約定しても段は効かない)・U1(根の 2 回目からの約定で段の値段を変えない: 根は 1 回で約定するので、作業者の足す試験で場面を作るなら `test_anchor_b1_extra.py`)・U4(段の決済が効き始めるときに自分の反対の注文と出会う決まりは今と同じ) |
| 浮動小数・刻み・丸め | U2(買いの段 6,999,699.5 → 6,999,699 は足の安値に届かない、売りの段 7,000,300.5 → 7,000,300 は高値ちょうど。切り上げると結果が変わる) |
| 慣らし | この委任には無い(慣らしを持たない仕組み。足 1・2 本目は動かない足) |
| 宣言した値の書き換え | U6(anchor_px・根の番号・距離・段の約定の値段を書き換えると検査が落とす) |
| 並行の変更 | この委任には無い(作業者は 1 名。直し A が同じ `src/bot/bt/road/` を直すので、A を受け取ってコミットした後に渡す) |

## 受け入れ

各項目は、試験 `tests/road/test_anchor_b1_spec.py` の挙げた試験が、試験を変えずに通ること。全体で飛ばし 0。

- U1: 段の約定(L-816 の例): `test_v1_levels_fill_from_root_fill_price`・`test_v1_root_filled_in_range_anchors_on_its_limit`
- U2: 刻みの切り捨て: `test_v2_buy_level_floored`・`test_v2_sell_level_floored`
- U3: 根が閉じる・段を取り消す・後から出す: `test_v3_root_closed_unfilled_closes_levels`・`test_v3_level_canceled_before_root_fills`・`test_v3_level_after_root_filled_refused`
- U4: 段に付けた決済: `test_v4_exit_attached_to_level`
- U5: 口の誤り: `test_v5_bad_anchor_refused`(13 通り)・`test_v5_good_anchor_sends_no_price`
- U6: 表の列と検査: `test_v6_columns`・`test_v6_tampering_fails_check`(4 通り)

## 変異の表

作業者が作り、報告に付ける。U1〜U6 と H1〜H5 の番号ごとに 1 行以上: 「作った物をわざと壊す変更(例: 段の値段を切り上げにする・悪い側では根の足で段を試さない・途中で値段が決まった段を同じ足で試さない)」と「それで落ちた試験(`tests/road/test_anchor_b1_spec.py::test_名前`)」。壊した変更は作業者の tmp の写しで当て、本物は壊したまま残さない。壊した変更で試験が 1 つも落ちなかったら、その行の落ちた試験の欄は「落ちなかった」と書き、問いとして返す(受け取りの検めはその行を落とす)。H の行は、確かめのコマンドと結果の 1 行の要約。

形: `| 番号 | 壊した変更 | 落ちた試験 |`

## 決まった制約
- 封印の置き場 `docs/RESEARCH/WINDOW1/`・`backtest_data/phase2_sealed/` は読まない。2023-12-17T15:00Z より後のデータを読まない。
- `git worktree add` をしない。Do not commit. Do not push. git add もしない。
- フック・`.claude/settings.json`・`githooks/`・`.claude/agents/` を変えない。
- コード・コメント・ログ・文書にモデル名を書かない。出す文は日本語。
- 委任文に書かれていない選びが出たら、選ばずに問いとして返す(委任文の「決めてよいこと」に書かれたものだけは自分で決めてよい)。

## 終わる条件と上限

- 終わる条件: U1〜U6 の試験が飛ばし 0 で通り、H1〜H5 が通り、変異の表の全部の行で壊した変更が試験を落とした。
- 上限: 作業者 1 周、または 3 時間。試験が食い違う・決まらないと分かったら、その件は止めて問いとして返し、それに依らない部分は続ける。

## 報告

- 着手前の表
- 直したファイルの一覧
- 試験のコマンドと出力(`PYTHONPATH=src python -m pytest tests/road`)
- H1〜H5 の確かめのコマンドと出力(H5 は 3 列を除いた指紋と PINNED)
- `## 変異の表`(上の形)
- 試験で決まらず作業者が決めた内部の形の一覧
- `## 問いとして返したこと`(行頭を `- Q1:` から番号にする。無ければ「問いとして返したことは無い。」と書く)
- 報告は返事に出す(リードが `docs/DISCUSSIONS/2026-10-06_held_batches/matilda_step0/REPORT_anchor_b1.md` に写す)
- 日本語で。

## 途中の決め

作業者の問いにリードが答えたら、ここに `- Q数字:` の行で足し、印を取り直す。
