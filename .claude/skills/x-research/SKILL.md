---
name: x-research
description: X(旧 Twitter)の公開投稿を、鍵も課金も無しに、この実行環境から実際に動く経路だけで集める手順(調査班向け)。発見は WebSearch、本文の取得は fxtwitter の公開 API。2026-09-19 にリードが各経路を実測して選定(L-219)。
---

# X の調査(無料経路、実測済みのものだけ)

**出所**: オーナー逐語(L-219)「**Xの情報取得に関しては無料で使えるスキルがいくつかある。有用なものを選定して調査班のスキルとして渡す**」。
既存の無料スキル 2 つ(`daymade/claude-code-skills` の twitter-reader、`wcfcarolina13/X-Scraper-MCP`)を読んで比べた結果、**どちらも中身は fxtwitter の公開 API**で、後者が足しているスレッド展開(公式の埋め込み用 syndication)はこの環境では動かない(HTTP 429)。よって外部のスキルは入れず、**この環境で動くと実測した経路だけ**をここに書く。

## 1. 動く経路(2026-09-19 実測、この実行環境から)

| 段 | 経路 | 何が取れるか | 実測 |
|---|---|---|---|
| 発見 | `WebSearch`(道具)で `site:x.com <語>` | 投稿 URL(`x.com/<利用者>/status/<ID>`)と本文の冒頭 | 10 件 / 回。語を変えて複数回引く |
| 本文 | `https://api.fxtwitter.com/i/status/<ID>`(利用者名は不要) | JSON: `text`(長文投稿も全文)、`created_at`、`likes` `retweets` `replies` `views`、`quote`(引用元の投稿ごと)、`replying_to_status`(返信先の ID)、`author`、`media` | HTTP 200、0.2〜0.8 秒。連続 5 回でも 200 |
| 利用者 | `https://api.fxtwitter.com/<利用者>` | 名前・自己紹介・フォロワー数・作成日 | HTTP 200 |
| 翻訳 | `https://api.fxtwitter.com/i/status/<ID>/ja` | `translation.text` | 未実測(公式文書に記載) |

**スレッドの辿り方**: `replying_to_status` が空でなくなるまで、その ID で本文の取得を繰り返す(上へ = 根まで)。**下へ(返信一覧・続き)は取れない**(fxtwitter に端点が無い)。続きの投稿は発見の段で `site:x.com/<利用者>` を引いて探す。

## 2. 動かない経路(同日実測。**再挑戦するときはここに結果を足す**)

公式の埋め込み用 `cdn.syndication.twimg.com` / `syndication.twitter.com`(404 / 429)、nitter 系 `nitter.net` `xcancel.com` `nitter.privacydev.net`(451 / 接続切断 / 502)、`x.com` 直(HTTP 200 だが JS の殻で本文 0)、`api.vxtwitter.com`(403)、`sotwe.com`(Cloudflare 403)、Google / Bing の結果ページの HTML(投稿 URL 0 件)。fxtwitter の検索・時系列の端点(404、存在しない)。

## 3. 手順(調査班)

1. **発見**: `WebSearch` を語を変えて 3 回以上(例: `site:x.com typesafe jev` / `site:x.com "system one" model` / `site:x.com @typesafeai` / 日本語 `site:x.com jev typesafe 使ってみた`)。結果の URL から ID を集める。**引いた語を全部、件数と一緒に報告に書く**(「無い」は、引いた語と件数を添えてはじめて書ける)。
2. **本文**: `python3 scripts/x_fetch.py <URL または ID> ...` を打つ(1 秒に 1 件以下)。1 行 1 投稿の JSON が出る。返信先があれば根まで自動で辿る(`--no-walk` で止める)。
3. **記録**: 各投稿について **URL / 著者 / 日時 / 本文(逐語)/ いいね・RT・返信・表示 / 引用元の要旨 / 取得時刻 / HTTP コード** を残す。本文は要約せず逐語で。判断は書かない(調査班は判定しない)。
4. **取れないとき**: 「どの経路で(URL)・いつ・HTTP 何番」を書く。それ無しに「取れない」と書かない(CLAUDE.md §5.2)。

## 4. 規則

- 鍵・ログイン・課金の経路は使わない(オーナー L-219「無料」)。
- User-Agent はこの用途を名乗る(`trade-research/1.0 (research use)`)。fxtwitter の文書: 「厳格な制限は無いが、洪水・濫用は遮断する」「アプリを UA で名乗れ」。
- 投稿の本文は公開情報だが、**個人の連絡先・私信の類は記録に写さない**。送信先(Jev など)に渡すときは `scripts/jev/redact.py` を通す。
- 発見の段が `WebSearch` に依存していること(検索エンジンが拾わない投稿は見えない)を射程として書く。
