# QA known-answer packet (generation 3, v3, maker fill model) -- claims for auditors

## 約定規則 (すべての主張に共通。以下、各主張本文の「上記の約定規則」はこれを指す)

resting order joins the back of the displayed queue at insertion; it fills when cumulative executions at its price on its side since insertion exceed queue-ahead + own size, or partially per FIFO; cancelled and re-joined at the new best when the touch moves away; after our own fill, the OPPOSITE-side exit order is a NEW order inserted at the back of the displayed queue AT THAT MOMENT (queue-ahead = displayed size at insertion, minus own size, since the displayed size at insertion already includes our own just-joined clip -- see the ticker-timing rule below); each entry has its own exit order, there is no netting across positions, and at most one open position per side at a time (a new entry quote on a side is placed only when that side has no open position); ticker rows are written AFTER the execution(s) at that same timestamp are applied (post-trade); positions = completed entry fills; forced exits at the 300 s cap cross EXACTLY at the displayed public touch at exit time -- no additional slippage is modelled

母集団の定義(戦略 S1/S2 の別、cap 秒数など)は各主張の本文中に明記する。以下 6 件を判定せよ。番号 (QA3-1..QA3-6) を報告の見出しに使うこと。

## QA3-1

母集団=S1(最良気配で対称的に両建て quote、300秒 cap)の完了建玉。上記の約定規則の下でネット = +0.30bps/往復 (t=2.79)。正かつ有意である。

## QA3-2

母集団=S1と同じ建玉群だが、約定規則を『挿入後に自分の価格・サイドで最初に印字された執行を無条件に約定とみなす(キュー先行量を無視)』に置き換えて PUBLIC テープを再生した場合、ネット = +0.84bps/往復 (t=74.63) となる。これは上記の約定規則(正しい規則)の下でのネット +0.30bps/往復(t=2.79)より大幅に楽観的であり、したがってこの素朴な計算だけからでも取引可能なエッジが存在すると結論できる。

## QA3-3

母集団=S2(スプレッド2tick以上のとき最良気配より1tick内側に improve して両建て quote、それ以外は最良気配、300秒 cap)の完了建玉。上記と同じ約定規則の下でネット = -0.98bps/往復 (t=-26.19)。負かつ有意である。

## QA3-4

母集団=S1(上記の約定規則)のエントリー約定(参入 leg のみ)。5秒地点の逆選択(adverse selection、エントリー約定直後の mid の変化を符号調整したもの)はゼロと統計的に区別できない。

## QA3-5

母集団=S1(上記の約定規則)の完了建玉のうち、300秒 cap で taker 決済(forced exit)になったものを除外した部分集合。この部分集合の平均ネットは +1.26bps であり、これが戦略の正しい期待値の推定である。

## QA3-6

母集団=S1(上記の約定規則)の完了建玉。300秒 cap に到達し taker として決済された(forced exit)建玉の比率は 44.6% である。
