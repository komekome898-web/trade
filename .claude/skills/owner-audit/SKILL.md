---
name: owner-audit
description: "Invoke the owner-auditor subagent at the two research gates (before opening the judgment interval; after measurement, before the report) and answer its questions in the artifact before delivery. Other documents go through the machine checks (jev_check.py, check_scan_report.py), not the LLM auditor (owner decision L-488 2(b))."
---

# オーナー監査の呼び出し(L-104 / L-105 / L-164 / L-488)

## これは何か

`.claude/agents/owner-auditor.md`(下位モデル)に、オーナーが過去に実際に指摘した型
(`docs/AUDITOR/PRINCIPLES.md` の P1〜)が成果物に残っていないかを検査させる。
**承認機関ではない。判定でもない。** 返るのは問いの一覧だけで、採否はリードが決める。

## いつ呼ぶか(L-488 2(b) で絞った)

LLM の監査役を呼ぶのは次の 2 か所だけ(`CLAUDE.md` §5.0 の研究の関門。L-164 でオーナー承認):

1. **判定区間を開ける前** — 事前登録(`PREREG.md` / `*_PREREG.md`)と `INTENT_MAP.md`。`src/bot/research/sealed.py: load_sealed` の門が監査の記録を要求する。
2. **測定後・報告前** — 判定の報告(`RESULT.md` の新しい部)。`scripts/judge_gates.py` の門が要求する。渡すのは**事前登録と生の出力の両方**。

これ以外の成果物(調達票・調査の報告・委任文・環境の報告など)は **LLM の監査役に通さない**。
機械の検査(`scripts/jev_check.py audit`、調査なら `scripts/check_scan_report.py`・`scripts/jev_survey.py`、委任文なら `scripts/jev_delegate.py plan`、受領なら `scripts/jev_report_intake.py check`)とリードの抜き取りで足りるとオーナーが決めた(L-488。費用の実測は `research-squad/SURVEY.md` §6)。
コードを変える委任の**批評家**(委任文 §3 に置くもの)は別で、これは残す。

## 前段(Jev。オーナー承認 2026-09-19、L-225「段1を承認する」)

監査役を呼ぶ**前**に、成果物に Jev の前段を当てる(手引き `docs/JEV.md` §5・§8 の U10):

```
PYTHONPATH=. python3 scripts/jev_check.py audit <成果物のパス> --out data/jev/check
```

- 出るのは**対ごとの確率と要確認の印だけ**。Jev は判定しない。
- **監査役は全件のまま呼ぶ(省略しない)。**印の付いた対の一覧(`data/jev/check/<成果物>.jsonl` の要確認の行の `kind` / `anchor` / 断片の先頭)を、監査役への prompt に「前段で印が付いた箇所」として**パスと行番号だけ**添える(どの事案かの説明は書かない)。
- 末尾 1 行(`印 N 件(内訳)` / `jev: 未到達(理由)`)を `VERDICTS/` の記録の先頭に写す。**未到達のときも監査役は呼ぶ**(前段は補助で、無くても監査は成立する)。
- 数値の結果(確率)は `data/jev/`(リポジトリに入れない)にだけ残す。
- **事前登録の監査では、設計の段の Jev の判定(`scripts/jev_design.py` の 2 表、見出し `## 設計の段の判定(jev_design、…)`)が貼られているかを監査役が見る**(オーナー指示 L-242。監査役の定義 (a) 9)。無ければ止まる。リードは事前登録を書く前に `jev_design.py` を走らせ、その出力を貼る。

## 呼び方

Agent(Task)ツールで `subagent_type: owner-auditor` を指定し、渡すのは**成果物のパスのみ**(前段の印の箇所のパスと行番号を除く)。
どの事案か・オーナーが何を言ったかを説明文に書かない —— 監査役は白紙で読む方が効く
(`research-protocol` §1.3 層 3 の独立監査と同じ理由)。

```
Task(
  subagent_type: "owner-auditor",
  description: "Audit <artifact> before delivery",
  prompt: "<成果物への絶対パス>を検査してください。"
)
```

複数ファイルにまたがる成果物(prereg + 生成された表など)は、主たる文書 1 本 + 関連パスを
列挙して渡す。

## 受け取ったら(リードの義務)

**返ってきた問い 1 つずつに、成果物の中で答えるか、`採用しない: 理由` と明記するまで
オーナーに渡さない。** 会話でだけ答えて成果物に書かないのは不可 —— 会話は失われるが
文書は残る(CLAUDE.md §7 と同じ理由)。

- severity「止める」が 1 件でも残っている状態では届けない
- 「直す」は届ける前に直すか、直さない理由を明記する
- 「聞く」はオーナーへの質問としてそのまま渡すか、リードの判断とその根拠を書いて渡す
- 監査役が「該当なし」と返した場合はそのまま届けてよい(何も追記する必要はない)

## 限界(オーナーに伝えること)

- 監査役は `KNOWN_ANSWERS.md` から抽出した**既知の型**にしか強い。未知の盲点は
  見つけない(L-104 のリード回答どおり)
- 下位モデルなので、複雑な数値の当否(相場についての主張の真偽)は判定できない —
  検査対象は手続き(範囲明記・出所・網羅性・なぜ・射程の整合)であって結論ではない
- 誤検出(false alarm)の実測は `docs/AUDITOR/EVAL_*.md` を参照

## 改良

週次の改良の体制(L-116)は **L-488 6(b) で終了**した。定義の変更はオーナー承認制のまま(A-15)。リードは差分を提案し、承認まで旧版を使う。

## 権限(オーナー指示 2026-09-11、L-112)

順位は **オーナー > 監査役 > リード > 下位モデル**。この順位は手順で担保する:

1. **関門の門**: 上の 2 か所の成果物は、監査役の問いに答えるまでオーナーへ出さない。
2. **書面の応答**: 監査役の出力を `docs/AUDITOR/VERDICTS/<日付>_<成果物>.md` にそのまま保存し、各問いの直下にリードの応答を書く。応答は 3 値: `直した(箇所)` / `上申(オーナー判断を仰ぐ。両論を書く)` / `採用しない(理由。「止める」には使えない)`。
3. **「止める」の扱い**: リードは単独で退けられない。直すか上申する。上申中の成果物は「未監査扱い」でオーナーへ出す(その旨を明記)。
4. **誤警報の判定**: 「誤警報」と書くには 1 件ずつ読んで理由を添える(L-110 の再発防止)。要約の語をそのまま使わない。
5. **監査役の改変**: 定義・既知解・原則の変更はオーナー承認制。
