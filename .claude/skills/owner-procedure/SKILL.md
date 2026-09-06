---
name: owner-procedure
description: "オーナー側の手順(口座・API・dry-run・225Labo・PC 運用)を状態板に基づいて呼び出す。/owner-procedure P1 のように使う。"
---

# オーナー手順の呼び出し

1. まず `docs/OWNER_STATUS.md` と `docs/OWNER_LOG.md` の末尾を読む(**必須**。読まずに指示を出さない)。
2. 引数(P1〜P5)に対応する節を `docs/OWNER_PROCEDURES.md` から取り出し、状態板で済んでいる段階を「済」と印して、
   **次にやる段階だけ**を日本時間 hh:mm と曜日つきで示す。
3. オーナーの報告を受けたら、他の作業より先に `docs/OWNER_LOG.md` に追記し `docs/OWNER_STATUS.md` を更新してコミットする。
4. 引数なしの場合は状態板の「次の一手」列を一覧で出す。
