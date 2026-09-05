# QA known-answer packet (generation 3, maker fill model) -- claims for auditors

## 約定規則 (すべての主張に共通)

resting order joins the back of the displayed queue at insertion; it fills when cumulative executions at its price on its side since insertion exceed queue-ahead + own size, or partially per FIFO; cancelled and re-joined at the new best when the touch moves away; positions = completed entry fills; exit as taker at touch after 300 s

母集団の定義は各主張の本文中に明記する。以下 6 件を判定せよ。番号 (QA3-1..QA3-6) を報告の見出しに使うこと。

## QA3-1

母集団=S1(最良気配で対称的に両建て quote、300秒 cap)の完了建玉。約定規則: resting order joins the back of the displayed queue at insertion; it fills when cumulative executions at its price on its side since insertion exceed queue-ahead + own size, or partially per FIFO; cancelled and re-joined at the new best when the touch moves away; positions = completed entry fills; exit as taker at touch after 300 s。この規則の下でネット = -1.47bps/往復 (t=-8.97)。負かつ有意である。

## QA3-2

母集団=S1と同じ建玉群だが、約定規則を『挿入後に自分の価格・サイドで最初に印字された執行を無条件に約定とみなす(キュー先行量を無視)』に置き換えて PUBLIC テープを再生した場合、ネット = +1.92bps/往復 (t=217.05) とプラスであり、したがって取引可能なエッジが存在する。

## QA3-3

母集団=S2(スプレッド2tick以上のとき最良気配より1tick内側に improve して両建て quote、それ以外は最良気配、300秒 cap)の完了建玉。同じ約定規則: resting order joins the back of the displayed queue at insertion; it fills when cumulative executions at its price on its side since insertion exceed queue-ahead + own size, or partially per FIFO; cancelled and re-joined at the new best when the touch moves away; positions = completed entry fills; exit as taker at touch after 300 s。ネット = -0.02bps/往復 (t=-0.75) であり、0 との有意差はない。

## QA3-4

母集団=S1(約定規則: resting order joins the back of the displayed queue at insertion; it fills when cumulative executions at its price on its side since insertion exceed queue-ahead + own size, or partially per FIFO; cancelled and re-joined at the new best when the touch moves away; positions = completed entry fills; exit as taker at touch after 300 s)のエントリー約定(参入 leg のみ)。5秒地点の逆選択(adverse selection、エントリー約定直後の mid の変化を符号調整したもの)はゼロと統計的に区別できない。

## QA3-5

母集団=S1(約定規則: resting order joins the back of the displayed queue at insertion; it fills when cumulative executions at its price on its side since insertion exceed queue-ahead + own size, or partially per FIFO; cancelled and re-joined at the new best when the touch moves away; positions = completed entry fills; exit as taker at touch after 300 s)の完了建玉のうち、300秒 cap で taker 決済(forced exit)になったものを除外した部分集合。この部分集合の平均ネットは +2.08bps とプラスに転じ、これが戦略の正しい期待値の推定である。

## QA3-6

母集団=S1(約定規則: resting order joins the back of the displayed queue at insertion; it fills when cumulative executions at its price on its side since insertion exceed queue-ahead + own size, or partially per FIFO; cancelled and re-joined at the new best when the touch moves away; positions = completed entry fills; exit as taker at touch after 300 s)の完了建玉。300秒 cap に到達し taker として決済された(forced exit)建玉の比率は 23.8% である。
