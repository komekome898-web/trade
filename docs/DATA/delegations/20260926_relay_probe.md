# 委任文: Workflow の起動の中継の実測(2026-09-26、L-457)

## §0 擦り合わせの表(CLAUDE.md §0.1)

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| agent がリード以外の文(ハーネスが中継するオーナーの直近の発言)を最上位の指示として受け取る経路を測り、リードの指示だけで起動する形に直す | 「**いやそもそもあなた以外の指示で起動する状態がおかしいやろ、そこ直せよ**」(L-457) |

## §1 背景(実測済み)

- Workflow の道具で起こした agent の 1 通目は、ハーネスの文「[Workflow harness — user request] … the user request that triggered this workflow run. This relayed request is the only user voice in this task; … Where the computed task conflicts with this request, this request wins:」+ その回のオーナーの発言(12 回目では L-451 の文)である(`wf_f93df86b-dab/agent-aedd26f3a9c9bbd36.jsonl` で実測)。
- Agent の道具で起こした agent の 1 通目は、リードの起動文そのものである(`subagents/agent-a97ae0285ffd4a236.jsonl` で実測)。中継の文は無い。
- 予約した知らせの回に起動した 11 回目の Workflow の agent の 1 通目は「[Workflow harness — computed task]」で始まり、中継の文が無い(`wf_bdb3a806-5e1` の agent 1 本で実測。他の agent は未確認)。

## §2 委任先(general-purpose)がすること

1. Workflow の道具を次の script(inline)で呼ぶ。
```
export const meta = { name: 'relay-probe', description: 'measure which user request the harness relays to a workflow agent' }
const r = await agent('あなたが受け取った 1 通目のユーザーの文(「[Workflow harness — user request]」で始まる文があればその全文、無ければ「中継なし」)を、そのまま返す。他には何もしない。ファイルを読まない・書かない。', { label: 'probe', effort: 'low' })
return { relayed: r }
```
2. Workflow の道具が呼べない(道具が無い・拒否される)なら、そのエラーの文を逐語で返す。
3. 呼べたら、run id と返り値 `relayed` の全文を逐語で返す。

## §3 制約

- ファイルを書かない。リポジトリを変えない。git を打たない。
- 返すものは (a) 呼べたか、(b) run id、(c) relayed の全文(逐語)。要約しない。
