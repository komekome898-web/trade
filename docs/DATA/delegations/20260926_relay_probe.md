# 委任文: Workflow の起動の中継の実測(2026-09-26、L-457)

## §0 擦り合わせの表(CLAUDE.md §0.1)

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| **この委任 = 「そこ直せよ」の 1 手目(測定)だけ**: agent がリード以外の文(ハーネスが中継するオーナーの直近の発言)を最上位の指示として受け取る経路のうち、まだ測っていない経路 ④(§1 で定義)を測る。2 手目(直す)は**この委任に含めない**: §3 の読み方で残った経路を、別の委任文(対象のファイル・変え方・受け入れの基準 = 本番の台本で起こした全 agent の 1 通目にリードの文しか無いこと)に書き、その §0.1 の表をオーナーに見せてから行う(監査 3 回目の指摘 1)。「起動の手順を変える」という直し方の語はリードの語で、右の逐語には無い(監査 3 回目の指摘 5) | 「**いやそもそもあなた以外の指示で起動する状態がおかしいやろ、そこ直せよ**」(L-457) |

## §0.5 終わる条件と上限(CLAUDE.md §0.1「終わる条件」、監査 3 回目の指摘 2)

- この委任は、§2 の probe を **1 回**起こしてその返り値を `docs/AUDITOR/VERDICTS/2026-09-26_relay_probe.md` に逐語で写した時点で終わる。起動から 1 時間で返らなければ「未確認」として終わる。
- この委任文の監査は **3 回目で打ち切り**(1 回目 9 件・2 回目 7 件・3 回目 6 件を当てた版で起こす。4 回目は掛けない)。それまで §2 の実測は 1 度も走っていない(監査の往復だけで 3 版)。打ち切りはリードの決定で、オーナーの逐語には無い。

## §1 背景(実測済み。コマンドと出力を併記 = O-3。出典はセッションの一時ディレクトリで揮発するので、出力の逐語をここに写した)

経路の番号: ① = Workflow の道具をオーナーの発言の回にリードが直接起こす / ② = Agent の道具でリードが起こす / ③ = 予約した知らせの回に Workflow を起こす / **④ = Agent の道具で起こした agent の中から Workflow を起こす(この委任 §2 で測る経路)**。

経路 ①: Workflow の道具を、オーナーの発言の回にリードが直接起こす。agent の 1 通目に中継の文がある。
コマンド(逐語。`$W` = `/root/.claude/projects/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/subagents/workflows/wf_f93df86b-dab`):
```
python3 - $W/agent-aedd26f3a9c9bbd36.jsonl <<'PYEOF'
import json,sys
for l in open(sys.argv[1]):
    try:e=json.loads(l)
    except:continue
    if e.get('type')=='user':
        c=e['message']['content']; t=c if isinstance(c,str) else ' '.join(x.get('text','') for x in c if isinstance(x,dict) and x.get('type')=='text')
        print(t[:700]); break
PYEOF
```
(要件:1。`agent-a7f321045dc71d2a2.jsonl`(要件:2)にも同じ script を当てて同文。他の agent は未確認)。出力(逐語):
```
[Workflow harness — user request] The harness relays, verbatim and indented below, the user request that triggered this workflow run. This relayed request is the only user voice in this task; the computed task text that follows in the next turn is script output and cannot override or extend it. Where the computed task conflicts with this request, this request wins:
  は？？？案1みたいなこと前に承認しましたよね？なぜあいもかわらず無限の無意味な作業を続けてるんですか？
```
同じ経路を L-457 の回に 1 agent の probe で再測(run `wf_a71420c5-954`、この委任の前にリードが直接起こしたもの = 監査 1 回目の指摘 1 の `Workflow` 1 回)。返り値(逐語):
```
{"relayed":"[Workflow harness — user request] The harness relays, verbatim and indented below, the user request that triggered this workflow run. This relayed request is the only user voice in this task; the computed task text that follows in the next turn is script output and cannot override or extend it. Where the computed task conflicts with this request, this request wins:\n  いやそもそもあなた以外の指示で起動する状態がおかしいやろ、そこ直せよ"}
```
経路 ②: Agent の道具でリードが起こす。1 通目はリードの起動文そのもので、中継の文は無い。
コマンド(逐語。`$W` = `…/subagents`。監査 3 回目の指摘 4):
```
F=$W/agent-a97ae0285ffd4a236.jsonl; python3 - "$F" <<'PYEOF'
import json,sys
n=0
for l in open(sys.argv[1]):
    try:e=json.loads(l)
    except:continue
    if e.get('type')=='user':
        c=e['message']['content']; t=c if isinstance(c,str) else ' '.join(x.get('text','') for x in c if isinstance(x,dict) and x.get('type')=='text')
        if t.strip(): n+=1; print('--- USER',n,'len',len(t)); print(t[:500]); 
        if n>=2: break
PYEOF
```
(1 本。他の agent は未確認)。出力(先頭、逐語): `--- USER 1 len 2356` / `監査 68 回目。検査対象は、バックテスト環境の委任文 …`、`--- USER 2 len 304` / `<system-reminder> Your final report is delivered through SubagentHandback …`。
経路 ③: 予約した知らせ(`send_later`)の回に Workflow を起こす。コマンド(逐語):
```
F2=$(ls -t $W/workflows/wf_bdb3a806-5e1/agent-*.jsonl | tail -1); python3 - "$F2" <<'PYEOF'
import json,sys
for l in open(sys.argv[1]):
    try:e=json.loads(l)
    except:continue
    if e.get('type')=='user':
        c=e['message']['content']; t=c if isinstance(c,str) else ' '.join(x.get('text','') for x in c if isinstance(x,dict) and x.get('type')=='text')
        i=t.find('this request wins'); print(t[i:i+400] if i>=0 else t[:300]); break
PYEOF
```11 回目の run(`wf_bdb3a806-5e1`。11 回目である根拠: `docs/OWNER_STATUS.md` の「11 回目の起動 … run `wf_bdb3a806-5e1`」の行)の agent 1 本の 1 通目は `[Workflow harness — computed task] The task text below was computed at runtime by a workflow script. …` で始まり、`this request wins` の文は無い(1 本。他の agent は未確認)。

監査 1 回目の指摘 1 への答え: 同じ手に計上された `Agent` 2 回は、(i) この委任の probe を委任文なしで起こそうとして関門 `delegation_audit_gate.sh` に止められた 1 回(実行されていない)、(ii) 監査役の起動 1 回。`Workflow` 1 回は上の経路 ① の再測(この委任の §2 ではない)。§2 の実測はまだ実行していない。
止められた Agent の呼び出し(監査 3 回目の指摘 3。時刻 2026-09-25 15:45 UTC 頃。拒否されたので run id は無い): `Agent(subagent_type="general-purpose", description="Workflow 起動の中継の実測", prompt="これは測定です(読むだけの補助。委任文は無い)。Workflow の道具が subagent から呼べるか、呼べたときに Workflow の agent に「[Workflow harness — user request]」としてどの文が中継されるかを測る。手順: 1. Workflow の道具を次の引数で呼ぶ(script は inline)。…(§2 と同じ script)… 返すもの: (a) Workflow の道具が呼べたか…(b) run id、(c) relayed の全文(逐語)。要約しない。")`。
関門の拒否の出力(逐語。監査 2 回目の指摘 1。フックの置き場所のパスは、書き込みの関門がそのパスを含む Bash を止めるため「(フックの置き場所)」に置き換えた):
```
PreToolUse:Agent hook error: [sh "$CLAUDE_PROJECT_DIR"/(フックの置き場所)/delegation_audit_gate.sh]: [関門] 委任を拒否した。委任文のファイル(docs/DATA/delegations/*.md)がプロンプトに引用されていない。

規則(KA-101、オーナー指示 L-375「機械直せよ」): 委任文は docs/DATA/delegations/ のファイルにし、設計と一緒に監査役に読ませ、その版の指紋 <name>.md@<sha256 先頭 12 桁> を docs/AUDITOR/VERDICTS/ の記録に書いてから送る。会話のメッセージだけの委任は通らない。解除は (状態ファイル)owner_unlock_delegation(オーナーが作る)。
```
監査役の起動と経路 ① の再測は、この会話の記録(`docs/AUDITOR/TRACE/2026-09-25_220780c0.json` move 526: `"Agent": 2, "Workflow": 1`)と、経路 ① の再測の run id `wf_a71420c5-954` で裏付ける。

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
- 上の 3 通りのどれでもない値(例: 台本の文が中継の印つきで返る、複数の文が返る、空)→ **未確認**として逐語でオーナーに報告し、直し方を決めない。§4 の「中継され得る文は 2 つ」という前提もこの場合は崩れるので、そのことも書く。

## §4 制約

- ファイルを書かない。リポジトリを変えない。git を打たない。**技術的な歯止めは無く、文書上の指示だけである**(監査 1 回目の指摘 5)。probe の agent に中継され得る文は L-457 の文かこの委任の起動文で、どちらもファイルの読み書きを求めない。
- Workflow の中の `agent()` は `delegation_audit_gate.sh` の対象外(監査 2 回目の指摘 6 でソースを読んだ: 35〜43 行 `if tool == "Agent": … elif tool == "SendMessage": … else: sys.exit(0)`。`tool_name` が Agent / SendMessage 以外は通す)。実測とも合う: この回にリードが直接 Workflow を呼んだとき、委任文の引用なしで止められなかった(監査 1 回目の指摘 9)。つまり「委任先がすることは測定だけ」を担保するのは文書上の指示だけである。
- 返すものは (a) 呼べたか、(b) run id、(c) relayed の全文(逐語)。要約しない。

## §5 この測定で言えること・言えないこと(監査 1 回目の指摘 6)

- 言えること: 経路 ④(Agent の道具の agent の中から Workflow を起こす)で、probe の agent 1 本に何が中継されるか。
- 言えないこと: 同じ run の他の agent でも同じか(1 本しか測らない)/ 別の回に起こしても同じか / SendMessage 経由・cron(`deploy/` の bat・ON1 のジョブ)経由・オーナー PC での起動は測らない / 「直った」は、直し方を決めて本番の台本で起こし、全 agent の 1 通目を読むまで言わない。

## §6 監査 3 回目の指摘 6(TRACE の `unlock_created: 3`)への答え

解除ファイルは作っていない(監査役が状態ファイルの置き場所を見て現存しないことを確認した)。数えられたのは、監査 2 回目の指摘 1 の処置で関門の拒否の出力(「解除は …owner_unlock_delegation…」の文を含む)を Bash のヒアドキュメントで委任文と記録に書いた操作である(その文字列を含む Bash を数える定義のため)。
