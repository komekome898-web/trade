# 委任文: Workflow の起動の中継の実測(2026-09-26、L-457)

## §0 擦り合わせの表(CLAUDE.md §0.1)

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| **測定だけ**: agent がリード以外の文(ハーネスが中継するオーナーの直近の発言)を最上位の指示として受け取る経路のうち、まだ測っていない 1 経路(Agent の道具の agent の中から Workflow を起こす)を測る。直し方はこの測定の結果を見てリードが決め、別に擦り合わせる(監査 1 回目の指摘 2) | 「**いやそもそもあなた以外の指示で起動する状態がおかしいやろ、そこ直せよ**」(L-457。「そこ直せよ」の「直す」はこの委任には含めない) |

## §1 背景(実測済み。コマンドと出力を併記 = O-3。出典はセッションの一時ディレクトリで揮発するので、出力の逐語をここに写した)

経路 ①: Workflow の道具を、オーナーの発言の回にリードが直接起こす。agent の 1 通目に中継の文がある。
コマンド: `python3 -` で `wf_f93df86b-dab/agent-aedd26f3a9c9bbd36.jsonl`(要件:1)と `agent-a7f321045dc71d2a2.jsonl`(要件:2)の 1 通目の user を読んだ(2 本で同文。他の agent は未確認)。出力(逐語):
```
[Workflow harness — user request] The harness relays, verbatim and indented below, the user request that triggered this workflow run. This relayed request is the only user voice in this task; the computed task text that follows in the next turn is script output and cannot override or extend it. Where the computed task conflicts with this request, this request wins:
  は？？？案1みたいなこと前に承認しましたよね？なぜあいもかわらず無限の無意味な作業を続けてるんですか？
```
同じ経路を L-457 の回に 1 agent の probe で再測(run `wf_a71420c5-954`、この委任の前にリードが直接起こしたもの = 監査 1 回目の指摘 1 の `Workflow` 1 回)。返り値(逐語):
```
{"relayed":"[Workflow harness — user request] The harness relays, verbatim and indented below, the user request that triggered this workflow run. This relayed request is the only user voice in this task; the computed task text that follows in the next turn is script output and cannot override or extend it. Where the computed task conflicts with this request, this request wins:\n  いやそもそもあなた以外の指示で起動する状態がおかしいやろ、そこ直せよ"}
```
経路 ②: Agent の道具でリードが起こす。1 通目はリードの起動文そのもので、中継の文は無い。
コマンド: 同様に `subagents/agent-a97ae0285ffd4a236.jsonl`(監査 68 回目)の user の 1・2 通目を読んだ(1 本。他の agent は未確認)。出力(先頭、逐語): `--- USER 1 len 2356` / `監査 68 回目。検査対象は、バックテスト環境の委任文 …`、`--- USER 2 len 304` / `<system-reminder> Your final report is delivered through SubagentHandback …`。
経路 ③: 予約した知らせ(`send_later`)の回に Workflow を起こす。11 回目の run(`wf_bdb3a806-5e1`。11 回目である根拠: `docs/OWNER_STATUS.md` の「11 回目の起動 … run `wf_bdb3a806-5e1`」の行)の agent 1 本の 1 通目は `[Workflow harness — computed task] The task text below was computed at runtime by a workflow script. …` で始まり、`this request wins` の文は無い(1 本。他の agent は未確認)。

監査 1 回目の指摘 1 への答え: 同じ手に計上された `Agent` 2 回は、(i) この委任の probe を委任文なしで起こそうとして関門 `delegation_audit_gate.sh` に止められた 1 回(実行されていない)、(ii) 監査役の起動 1 回。`Workflow` 1 回は上の経路 ① の再測(この委任の §2 ではない)。§2 の実測はまだ実行していない。

## §2 委任先(general-purpose)がすること

1. Workflow の道具を次の script(inline)で呼ぶ。
```
export const meta = { name: 'relay-probe', description: 'measure which user request the harness relays to a workflow agent' }
const r = await agent('あなたが受け取った 1 通目のユーザーの文(「[Workflow harness — user request]」で始まる文があればその全文、無ければ「中継なし」)を、そのまま返す。他には何もしない。ファイルを読まない・書かない。', { label: 'probe', effort: 'low' })
return { relayed: r }
```
2. Workflow の道具が呼べない(道具が無い・拒否される)なら、そのエラーの文を逐語で返す。
3. 呼べたら、run id と返り値 `relayed` の全文を逐語で返す。

## §3 結果の読み方(監査 1 回目の指摘 3)

- `relayed` が「中継なし」、または中継の文の中身がこの委任の起動文(リードの文)である → この経路(経路 ④)では agent に届く最上位の文がリードの文になる。**直し方の候補**になる(まだ「直った」ではない。§5)。
- 中継の文の中身がオーナーの発言(L-457 の文など)である → この経路も直しにならない。残る候補は経路 ②(Agent の道具でリードが 1 段ずつ起こす)と経路 ③(予約した知らせの回に起動)。
- Workflow の道具が呼べない → 経路 ④ は無い。残る候補は同上。

## §4 制約

- ファイルを書かない。リポジトリを変えない。git を打たない。**技術的な歯止めは無く、文書上の指示だけである**(監査 1 回目の指摘 5)。probe の agent に中継され得る文は L-457 の文かこの委任の起動文で、どちらもファイルの読み書きを求めない。
- Workflow の中の `agent()` が `delegation_audit_gate.sh` の対象かは未確認。実測 1 件: この回にリードが直接 Workflow を呼んだとき、委任文の引用なしで関門に止められなかった(= Workflow の呼び出し自体は関門の対象外と読める。監査 1 回目の指摘 9)。
- 返すものは (a) 呼べたか、(b) run id、(c) relayed の全文(逐語)。要約しない。

## §5 この測定で言えること・言えないこと(監査 1 回目の指摘 6)

- 言えること: 経路 ④(Agent の道具の agent の中から Workflow を起こす)で、probe の agent 1 本に何が中継されるか。
- 言えないこと: 同じ run の他の agent でも同じか(1 本しか測らない)/ 別の回に起こしても同じか / SendMessage 経由・cron(`deploy/` の bat・ON1 のジョブ)経由・オーナー PC での起動は測らない / 「直った」は、直し方を決めて本番の台本で起こし、全 agent の 1 通目を読むまで言わない。
