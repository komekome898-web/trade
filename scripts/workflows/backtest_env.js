export const meta = {
  name: 'backtest-env-rebuild',
  description: 'Build the new backtest engine item by item: fixed requirements, worker, independent dossier, strict critic, blind pairwise judges (owner L-405..L-408)',
  phases: [
    { title: '要件の固定', detail: '資料係が項目ごとの要件と比較の観点を固定する' },
    { title: '作る', detail: '作業者が持ち物のファイルだけを書く' },
    { title: '比較資料', detail: '資料係が名前を伏せた資料を同じ雛形で作る' },
    { title: '批評', detail: '非常に厳しい批評家が試験を書いて壊しにいく' },
    { title: '盲検', detail: '2 組 x 3 体の審査員がどちらが優れて見えるかを選ぶ' },
    { title: '欠けているもの', detail: '完全性の批評家が抜けを探す' },
  ],
}

const DOC = 'docs/DATA/delegations/20260923_backtest_env_prompt.md'
const MARK = args.marker
const REC = 'docs/DISCUSSIONS/2026-09-23_backtest_env'
const SCR = args.scratch
const MODEL = 'sonnet'
// Jev front stage: 場面係・資料係(表)・批評家 = 実装の段 (L-419). Owner L-429: the opus tier is Opus 5.5;
// args.opus_model pins the id (omitted on run 6 so its cached agents keep their keys; measured: alias 'opus' = claude-opus-5-5)
const OPUS = args.opus_model || 'opus'
const IMPL_MODEL = OPUS

const HEAD = `委任文 ${DOC}(指紋 ${MARK})を最初に全部読み、その指示にだけ従うこと。起動文と委任文が食い違えば委任文が優先する。` +
  `オーナーの目に触れる文(記録のファイルを含む)は日本語で書く。コードとコメントは英語。モデル名を書かない。git commit / git push をしない。` +
  `一時ファイルとログは ${SCR} の下に、名前に項目番号・周・役を入れて置く。`
const HEAD2 = args.marker_new ? HEAD.split(MARK).join(args.marker_new) : HEAD
// L-433: every role scrutinizes before returning (delegation §3「提出前の吟味」)
const SCRUTINY_FIX = `\n**返す前の吟味(委任文 §3「提出前の吟味」、L-433。直す役の文)**: 固定した要件・場面集の規則・これまでの指摘を読み直し、指摘 1 件ごとに直した根拠(ファイル:行、コマンドと出力)を書く。指摘された 1 か所だけでなく同じ根の全箇所を直す。批評家の試験と場面集の試験を回して落ちるものを残さない。「非常に厳しい批評家なら何を [止める] にするか」を自分で列べて返す前に潰す。場当たりの直しをしない。止められる前提で作業しない。(6) 直した規則ごとに、その規則の入力の空間を全格子で列べる敵対者の試験(批評家の probe の形。実装の場合分けから入力を作らない)を先に書き、規則を直したあと通す。列に入れなかったものを試験のファイルに書く(リードの設計 docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_7/LEAD_DESIGN.md §3.3)。`
const SCRUTINY_BUILD = `\n**返す前の吟味(委任文 §3「提出前の吟味」、L-433。最初に作る役の文)**: 固定した要件・場面集の規則 1〜9・比較の観点を読み直し、自分の作ったものを「非常に厳しい監査役・批評家なら何を [止める] にするか」の目で観点ごとに列べ、返す前に潰す。止められる前提で作らない。吟味の記録を、要件なら要件のファイルの末尾、場面集の最初の作りなら DEFINITIONS.md の末尾、直しなら ROOTCAUSE のファイルに書く。`
const SCRUTINY_TABLE = `\n**返す前の吟味(委任文 §3「提出前の吟味」、L-433。資料係(表)の文)**: 表の観点ごとの一致の数を出力から自分で数え直し、表と一致させる。全対象を全場面に通したか(通らなかった場面の注記に試したことと実測があるか)、注記に道具を特定できる語が無いか、組ごとの 2 通りの表の md5 を確かめたか、materials に記録を全部保存したかを確かめ、notes に書く。`
const SCRUTINY_CRITIC = `\n**返す前の吟味(委任文 §3「提出前の吟味」、L-433。批評家の文)**: 指摘 1 件ごとに根拠(試験・コマンドと出力)を自分で再現し、格付けを委任文 §3「批評家」の基準に照らし、前の周の指摘の直りを自分で確かめる(直ったものを挙げない・直っていないものを見逃さない)。指摘の相手(場面集 / 実装)を付け違えていないか確かめる。記録は CRITIC.md に書く。`
const SCRUTINY_JUDGE = `返す前の吟味(委任文 §3「提出前の吟味」、L-433。審査員の文): 観点ごとの数えを表から自分で数え直し、reasons に書いた数と一致するかを確かめる。`
const SCRUTINY_GAPS = `\n**返す前の吟味(委任文 §3「提出前の吟味」、L-433。「欠けているもの」の批評家の文)**: 挙げた欠けが本当に無いか(実際に動かして確かめたか)、既にある項目の [直す] と重ならないかを確かめ、記録のファイルに書く。`

const ITEMS = args.items  // [{id, title}]

const REQ_SCHEMA = { type: 'object', properties: {
  path: { type: 'string' }, perspectives: { type: 'array', items: { type: 'string' } },
  survey_candidates: { type: 'integer' }, extraction_command: { type: 'string' } },
  required: ['path', 'perspectives', 'survey_candidates', 'extraction_command'] }

const WORK_SCHEMA = { type: 'object', properties: {
  changed_files: { type: 'array', items: { type: 'string' } },
  tests_added: { type: 'integer' }, test_command: { type: 'string' }, test_tail: { type: 'string' },
  structural_change: { type: 'string' }, unmet: { type: 'array', items: { type: 'string' } },
  questions_for_lead: { type: 'array', items: { type: 'string' } } },
  required: ['changed_files', 'tests_added', 'test_command', 'test_tail', 'structural_change', 'unmet', 'questions_for_lead'] }
// §6 report fields one-to-one (item 0 round 1 of run 5 keeps WORK_SCHEMA so it replays from the record)
const WORK_SCHEMA2 = { type: 'object', properties: { ...WORK_SCHEMA.properties,
  requirement_evidence: { type: 'array', items: { type: 'string' } }, external_tool_checks: { type: 'string' } },
  required: [...WORK_SCHEMA.required, 'requirement_evidence', 'external_tool_checks'] }


const FINDING = { type: 'object', properties: {
  id: { type: 'string' }, level: { type: 'string', enum: ['止める', '直す', '示唆'] },
  text: { type: 'string' }, evidence: { type: 'string' },
  repeat_of: { type: ['string', 'null'] }, patchwork: { type: 'boolean' },
  target: { type: 'string', enum: ['場面集', '実装'] },
  fix_files: { type: 'array', items: { type: 'string' }, minItems: 1 } },  // audit 58-3 / 59-1: the files the fix must change; empty or missing = implementation side (blocks the pass)
  required: ['id', 'level', 'text', 'evidence', 'repeat_of', 'patchwork', 'target', 'fix_files'] }
const CRITIC_SCHEMA = { type: 'object', properties: {
  findings: { type: 'array', items: FINDING },
  structural_change_since_prev: { type: 'boolean' }, record_path: { type: 'string' } },
  required: ['findings', 'structural_change_since_prev', 'record_path'] }

const JUDGE_SCHEMA = { type: 'object', properties: {
  choice: { type: 'string', enum: ['左', '右', '同等'] }, reasons: { type: 'string' },
  missing_in_choice: { type: 'string' } },
  required: ['choice', 'reasons', 'missing_in_choice'] }

const GAP_SCHEMA = { type: 'object', properties: {
  new_items: { type: 'array', items: { type: 'object', properties: {
    title: { type: 'string' }, owned: { type: 'string' }, requirement: { type: 'string' }, why_missing: { type: 'string' } },
    required: ['title', 'owned', 'requirement', 'why_missing'] } },
  record_path: { type: 'string' } },
  required: ['new_items', 'record_path'] }

function dir(item, r) { return `${REC}/item_${item.id}/round_${r}` }

async function fixRequirements(item) {
  return agent(`${item.id === 0 ? HEAD : HEAD2}
あなたは項目 ${item.id}「${item.title}」の資料係(要件の固定)です。委任文 §3「要件と判定の固定」と「調査結果の側の選び方」に従い、
${REC}/item_${item.id}/REQUIREMENTS.md を書いて固定してください。中身:
1. 委任文 §2 の項目 ${item.id} の行(逐語)。${item.extra || ''}
2. 比較の観点(観点ごとに 1 行、測れる形)。オーナーの完了の形「すべてが調査結果以上の信頼性と再現性に優れたもの」を観点の軸にする。
3. 調査結果の側: docs/DATA/tools_catalog.tsv の該当する要素の列に印がある行を、スクリプトで機械的に全部抜き出す(人が足し引きしない)。該当する要素の列が無い項目は、docs/DATA/SCAN_2026-09-21_tools.md への grep の語を先に書いてから打ち、当たった候補を全部取る。使ったコマンドをそのまま書く。観点ごとに段(機構)が最も高い機構を、候補番号と SCAN の行つきで書く。
4. 当方の現状(旧 src/bot/backtest/ ほか)の該当箇所をファイル:行で書く。
**すでに ${REC}/item_${item.id}/REQUIREMENTS.md があれば、それは固定済みの要件なので書き直さない。**委任文の今の版と食い違う箇所があるときだけ、その箇所を直し、直した行と理由をファイルの末尾に書き足す。
${SCRUTINY_BUILD}
このファイル以外は書かない。`, { label: `要件:${item.id}`, phase: '要件の固定', schema: REQ_SCHEMA, model: MODEL, effort: 'high' })
}

const BAT_SCHEMA = { type: 'object', properties: {
  battery_dir: { type: 'string' }, definitions: { type: 'string' }, runner: { type: 'string' },
  scenarios: { type: 'integer' }, mutant: { type: 'string' },
  survey_run: { type: 'array', items: { type: 'string' } },
  survey_not_run: { type: 'array', items: { type: 'string' } } },
  required: ['battery_dir', 'definitions', 'runner', 'scenarios', 'mutant', 'survey_run', 'survey_not_run'] }

const TABLE_SCHEMA = { type: 'object', properties: {
  tables: { type: 'object', properties: {
    current_1: { type: 'string' }, current_2: { type: 'string' },
    survey_1: { type: 'string' }, survey_2: { type: 'string' },
    mutant_1: { type: 'string' }, mutant_2: { type: 'string' } },
    required: ['current_1', 'current_2', 'survey_1', 'survey_2', 'mutant_1', 'mutant_2'] },
  commands: { type: 'string' }, adapters_changed: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' },
  identical: { type: 'object', properties: { current: { type: 'boolean' }, survey: { type: 'boolean' }, mutant: { type: 'boolean' } }, required: ['current', 'survey', 'mutant'] } },
  required: ['tables', 'commands', 'adapters_changed', 'notes', 'identical'] }

const AUDIT_SCHEMA = { type: 'object', properties: {
  findings: { type: 'array', items: { type: 'object', properties: {
    level: { type: 'string', enum: ['止める', '直す', '聞く'] }, text: { type: 'string' } }, required: ['level', 'text'] } } },
  required: ['findings'] }

async function fixBattery(item, req) {
  return agent(`${item.id === 0 ? HEAD : HEAD2}
あなたは項目 ${item.id}「${item.title}」の場面係です(作業者でも資料係でもない。委任文 §3「盲検の作り直し」「場面集」「調査結果の側の選び方」に従う)。固定した要件: ${req.path}。
1. 要件の観点ごとに、実行できる場面を tests/bt/battery/item_${item.id}/ に作る。**値の場面**(合成の入力と、エンジンを見ずに手計算・閉じた式で出した正解。出し方を書く)と**能力の場面**(X ができるかを実際に呼んで試す)。場面の定義を 1 つの文書 tests/bt/battery/item_${item.id}/DEFINITIONS.md に書く(場面ごとに 入力 / 期待 / 何を測るか。道具の名前は書かない)。
2. 場面を対象ごとに走らせる runner(tests/bt/battery/item_${item.id}/run_battery.py、引数 --target と --out、同じ場面を 2 回走らせて一致も記録)と、当方の現状(旧 src/bot/backtest/ ほか)と調査結果の側の道具の adapter を書く。新実装の adapter は資料係が毎周書くので、ここでは口だけ決める。
3. 調査結果の側: ${req.path} の候補を**全部**、委任文 §4 の安全の規則で scratchpad の venv(${SCR}/venvs/)に入れて場面に通す。入れられたもの / 入れられなかったもの(理由と試したこと)を全部返す。
4. 委任文 §3「動かせない候補の検討と再現」に従う: 動かせなかった候補を 1 件も検討せずに外さず、全部を tests/bt/battery/item_${item.id}/opponents/CONSIDERED.md の検討表に載せる(機構 / 実装で確かめたか / 再現した・持たないと確認した・スキップ: 明らかに弱い・再現できない / 理由と根拠)。段のある観点は段(既定と実装で確かめたもの)で最も強い候補を、段の無い観点は実装で確かめられる候補を全部、最小の再現として opponents/ に書く。スキップは理由を書いたときだけ(理由なし・推測のスキップは禁止)。理由は、段のある観点は「段が低い」(段の値と調査報告の行)、段の無い観点は「上位互換」だけ(動かせた候補か再現した候補の機構が、その候補の能力を 1 つ残らず含むことを調査報告の行で 1 能力ずつ示す。段の代わりの指標を作らない)。材料は (a) SCAN の書き写し → (b) 一次資料を §4 のネットワークの規則で読むだけ(道具台帳 §3 の 11 件は (b) をしない)。根拠を注釈に 1 対 1。工夫を足さない、弱めない。再現した行は表で他と区別しない。検討表は返す前に python3 scripts/check_bt_considered.py <検討表> --write を走らせて誤り 0 件にし(場面集の規則 9。集計は道具が書く)、出力の最後の行を survey_not_run の最初に入れる。
5. 試金石用に、新実装に不具合を 1 つだけ仕込む仕組み(tests/bt/battery/item_${item.id}/mutant.py。新実装を包んで 1 か所だけ誤らせる。何を誤らせたかを mutant に書く)を作る。新実装の本体は変えない。
**委任文 §3「場面集の規則」1〜9 を全部守る**(能力の場面も呼んだ結果を正解と突き合わせる / 振る舞いを試し作りの形を試さない / 観点ごとにまとめる / 動かせた道具は全場面に通す / 検討表の 4 分類 / 試験の置き場所)。前の起動の場面集が ${`tests/bt/battery/item_${item.id}/`} にあれば、規則に合わせて作り直す(使える部分は使ってよい)。
${(args.prior_battery_record || {})[item.id] ? `前の起動の場面集への監査役の指摘とリードの処置: ${args.prior_battery_record[item.id]}(同じ欠陥を繰り返さない)。` : ''}${SCRUTINY_BUILD}
作業者はこの場面集を読めるが変えない。`, { label: `場面:${item.id}`, phase: '要件の固定', schema: BAT_SCHEMA, model: IMPL_MODEL, effort: 'high' })
}

const BAT2_SCHEMA = { type: 'object', properties: {
  battery_dir: { type: 'string' }, definitions: { type: 'string' }, runner: { type: 'string' },
  scenarios: { type: 'integer' }, mutant: { type: 'string' },
  survey_run: { type: 'array', items: { type: 'string' } },
  survey_not_run: { type: 'array', items: { type: 'string' } },
  lead_answer_changes: { type: 'array', items: { type: 'string' } },  // audit 56-3 / L-443: what the repair changed in the lead's answer and why (empty if nothing)
  rootcause: { type: 'string' }, check_output: { type: 'string' } },
  required: ['battery_dir', 'definitions', 'runner', 'scenarios', 'mutant', 'survey_run', 'survey_not_run', 'rootcause', 'check_output', 'lead_answer_changes'] }

const BAT_AUDIT_SCHEMA = { type: 'object', properties: {
  findings: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, level: { type: 'string', enum: ['止める', '直す', '聞く'] }, text: { type: 'string' },
    repeat_of: { type: ['string', 'null'] } }, required: ['id', 'level', 'text', 'repeat_of'] } } },
  required: ['findings'] }

async function auditBattery(item, bat, n, prev) {
  return agent(`検査対象: 項目 ${item.id}「${item.title}」の場面集 ${bat.definitions} と、その置き場所 ${bat.battery_dir}(検めるのは差分と試験の結果(L-443): 場面係の直しが tests/bt/battery/ の外(実装 src/bot/bt/・作業者の試験 tests/bt/item_${item.id}/・批評家の試験 tests/bt/critic/item_${item.id}/)に触れていないかを「git diff --name-only HEAD」と「git status --short」で自分で検め、ROOTCAUSE の主張の表の (c)(d) の試験と場面集の試験・mutant を自分で走らせて通るかを見る。散文の定義は求めない = 場面集の側とされた指摘が実は実装の欠陥だった(相手の付け違い)ときの独立の照合、監査 60-3。runner・当方の現状と調査結果の側の adapter・検討表 opponents/CONSIDERED.md・再現 opponents/・mutant)。作業者はまだ動いていない(この監査は作業者の 1 周目の前)。委任文 ${DOC} §3「盲検の作り直し」「場面集」「場面集の規則」1〜9「調査結果の側の選び方」「動かせない候補の検討と再現」と照らす。python3 scripts/check_bt_considered.py ${bat.battery_dir}/opponents/CONSIDERED.md を自分で走らせ、出力を見る(道具が見るのは形だけ。理由の中身・再現が一次資料どおりかは読んで確かめる)。場面が新実装に有利な範囲に偏っていないか、場面が振る舞いでなく作りの形を試していないか(期待の値が要件の文から独立に出せるか)、出所を示す語、断定と範囲、動かせなかった候補の記録を検査する。${(args.lead_notes || {})[item.id] ? `リードの注記(前の起動の戻しの設計・条件。必ず読む): ${(args.lead_notes || {})[item.id]}` : ''}${(args.prior_battery_record || {})[item.id] ? `前の起動の場面集への監査役の指摘とリードの処置: ${(args.prior_battery_record || {})[item.id]}` : ''}指摘は [止める] / [直す] / [聞く] の印つきで返し、id を b${n}-1, b${n}-2, … と振る。${prev ? `前の回の指摘(id つき): ${JSON.stringify(prev).slice(0, 8000)}。` : ''}指摘ごとに repeat_of を必ず埋める: 前の回までの指摘と同じ理由なら前の指摘の id、そうでなければ null。「同じ理由」= 同じ根本原因の族(前の指摘と同じ機構の別の形。例: 帰属の穴が dict → 対象の class → 戦略の外の呼び出し、と形を変えたもの)。同じ場所・同じ文言に限らない。「同じ型の穴」と書くなら repeat_of を付ける(直ったものは挙げない。直ったかは自分で確かめる)。委任文 §3「周回の数え方と止める条件」4。`,
    { label: `監査役(場面):${item.id}#${n}`, phase: '批評', schema: BAT_AUDIT_SCHEMA, agentType: 'owner-auditor', model: MODEL })
}

// L-443 (2): the definition step (場面係 writes a prose definition, 監査役(定義) audits it) is gone; a battery repair
// carries its own machine (claim table: deriving function / hand-written remainder / failing test / mutant) and the
// battery auditor reads the diff and the test results, not prose (owner: 「その案に賛成します。今すぐ体制を変えて進めてください。」)
async function repairBattery(item, req, bat, findings, n) {
  return agent(`${HEAD2}
あなたは項目 ${item.id}「${item.title}」の場面係です(場面集の第 ${n} 回の直し。作業者でも資料係でもない)。固定した要件: ${req.path}。場面集 ${bat.definitions}(置き場所 ${bat.battery_dir})に、監査役が次の指摘を出した(逐語):
${JSON.stringify(findings).slice(0, 12000)}
**場面集の主張の表(L-443、オーナー承認)**: 直しの前に ${bat.battery_dir}/ROOTCAUSE_${n}.md に、この直しが触る主張の族ごとに 4 列の表を書く: (a) その主張を場面の入力と実行の記録から導く関数(ファイル:関数名)/ (b) 手書きが残る部分(残るなら、なぜ機械で導けないか)/ (c) 手書きの主張が 1 つでも残っていれば落ちる試験(ファイル:試験名)/ (d) 主張を作る機械への mutant の試験。散文の定義は書かない(定義の段は無い)。指摘の族に当たる主張の全部をこの形にしてから直す。
リードの答え(リードの注記にある正の定義など)の内容を変えるなら、変えた点と理由を ROOTCAUSE_${n}.md の節「リードに聞くこと」に書き、同じ文を lead_answer_changes に返す(無ければ空の配列)。書き先はこの 2 つだけ。
${(args.lead_notes || {})[item.id] ? `リードの注記(前の起動の戻しの設計・条件。必ず読む): ${(args.lead_notes || {})[item.id]}` : ''}${(args.prior_battery_record || {})[item.id] ? `前の起動の場面集への監査役の指摘とリードの処置: ${(args.prior_battery_record || {})[item.id]}` : ''}
**直す前に** ${bat.battery_dir}/ROOTCAUSE_${n}.md に、指摘 1 件ごとに「なぜ起きたか(根本原因)」と「どの作りを変えるか」を書く(委任文 §3「根本的解決」)。[聞く] にはそこで答える。指摘の文言だけに合わせる直しをしない: 同じ種類の欠陥を場面集の全体(全観点・全場面・検討表の全行)で探して直す。
そのうえで委任文 §3「場面集」「場面集の規則」1〜9「調査結果の側の選び方」「動かせない候補の検討と再現」に合わせて、場面の定義・runner・当方の現状と調査結果の側の adapter・検討表・再現・mutant を直す([直す] も直す)。**実装(src/bot/bt/ の下)と作業者の試験(tests/bt/item_${item.id}/)には触れない**(場面集の側の直しが実装に及ぶなら、それは相手の付け違い = rootcause に書いて止める。監査 60-3)。返す前に「git diff --name-only HEAD」を走らせ、その出力を rootcause のファイルの末尾に貼る(tests/bt/battery/ の外のファイルがあれば理由を書く)。場面の期待は要件の文から独立に出せる振る舞いで書き、新実装の内部の名前・形を写さない(規則 2)。
検討表は返す前に python3 scripts/check_bt_considered.py ${bat.battery_dir}/opponents/CONSIDERED.md --write を走らせて誤り 0 件にし、出力の最後の行を check_output に入れる(規則 9)。rootcause には ROOTCAUSE の path を入れる。
${SCRUTINY_FIX}
作業者はこの場面集を読めるが変えない。`, { label: `場面の直し:${item.id}#${n}`, phase: '要件の固定', schema: BAT2_SCHEMA, model: IMPL_MODEL, effort: 'high' })
}

// L-441 (案 2) + audit 58-3: item 0 passes on the implementation-side [止める] only. The side is not the critic's tag
// alone: a [止める] whose fix_files touch src/bot/bt/ is implementation-side whatever its tag (a mis-tag cannot open
// the gate), and the report auditor re-reads every battery-tagged [止める] (prompt below). Pure: tested by node --test.
function splitStops(item, stops) {
  if (item.id !== 0) return { impl: stops, bat: [] }
  // audit 59-1: fix_files is self-reported too, so the default is the side that blocks the pass: no file named (empty or
  // missing) = implementation side. A battery-side stop must name only battery files (tests/bt/) to be counted as battery.
  const isImpl = f => f.target === '実装' || !(f.fix_files || []).length || !(f.fix_files || []).every(x => String(x).replace(/^\.\//, '').startsWith('tests/bt/'))
  return { impl: stops.filter(isImpl), bat: stops.filter(f => !isImpl(f)) }
}

// L-443 (3) + audit 62-1/62-2: whether this round's judges sit. Pure: in the framework fingerprint and node-tested.
// structural = the critic saw a structural change (a missing critic counts as one, the conservative side for the
// round count); judgeNow = first round, or a pass candidate (no implementation-side [止める]), or structural.
function judgeRound(attempt, c, stopsImpl) {
  const structural = attempt === 1 || (c ? !!c.structural_change_since_prev : true)
  return { structural, judgeNow: attempt === 1 || stopsImpl.length === 0 || structural }
}

async function runItem(item) {
  // pre = a launch that continues from an existing, audited battery (L-426/L-427): skip requirements, battery build and the pre-worker audit
  const pre = (args.prebuilt || {})[item.id] || null
  const req = pre ? { path: pre.req } : await fixRequirements(item)
  if (!req) return { item, status: 'error', stage: 'requirements' }
  let bat = pre ? pre.bat : await fixBattery(item, req)
  if (!bat) return { item, status: 'error', stage: 'battery' }
  // battery audit before the worker; the 場面係 repairs until no [止める].
  // Stop rule = L-407 C as is: stop when the same reason survives 3 audits in a row. Battery audits share the
  // item's 10 rounds with the worker (L-418 "案1 共有").
  // L-420: rounds carry across launches (rounds where a delegate did not work are excluded by the lead's count)
  const prior = (args.prior_rounds || {})[item.id] || { rounds: 0, findings: null, chain: {} }
  const batHist = []
  // L-421/L-424: the battery-side chain carries across launches under prior_rounds[id].battery_chain (the key the lead
  // writes; `chain` is accepted for older args) and continues into the in-round repairs of this launch
  const bchain = { ...(prior.battery_chain || prior.chain || {}) }
  let prevF = prior.findings
  for (let n = 1; !pre; n++) {
    if (item.id !== 0 && prior.rounds + n > 10) return { item, status: 'escalate', reason: '場面集の監査が 10 回に達した(L-407 の最大 10 周。L-418 で作業者の周と共有)', attempts: 0, req, bat, batteryHistory: batHist, history: [] }
    const a = await auditBattery(item, bat, n, prevF)
    const fs = a ? a.findings : [{ id: `b${n}-x`, level: '止める', text: '監査役が返らなかった' }]
    batHist.push({ n, findings: fs })
    const stops = fs.filter(f => f.level === '止める')
    if (!stops.length) break
    stops.forEach(f => { bchain[f.id] = f.repeat_of && bchain[f.repeat_of] ? bchain[f.repeat_of] + 1 : 1 })
    const rep3 = stops.find(f => bchain[f.id] >= 3)
    if (rep3) return { item, status: 'escalate', reason: `場面集の監査で同じ未達の理由が 3 回続いた(L-407): ${rep3.text.slice(0, 300)}`, attempts: 0, req, bat, batteryHistory: batHist, history: [] }
    const fixed = await repairBattery(item, req, bat, fs, n)
    if (!fixed) return { item, status: 'error', stage: 'battery_repair', batteryHistory: batHist, history: [] }
    bat = { ...bat, ...fixed }
    prevF = fs
  }
  const history = []
  let counted = prior.rounds + batHist.length, nonStructural = 0  // L-418: battery audits count toward the same 10; L-420: carried across launches
  const chain = { ...(prior.critic_chain || {}) }  // L-421: the same-reason count carries across launches
  const cbchain = { ...bchain, ...((pre && pre.battery_chain) || {}) }  // L-424: 場面集 findings are counted apart from 実装 findings; same chain as the pre-worker audits
  // audit 63-1: the blind-judge loss streak carries across launches (委任文 §3「周回の数え方と止める条件」4) under
  // prior_rounds[id].loss_streak, written by the lead from the last history entry's lossStreak snapshot
  const lossStreak = { current: 0, survey: 0, ...((prior.loss_streak && typeof prior.loss_streak === 'object') ? prior.loss_streak : {}) }
  let attempt = pre ? pre.attempt_offset : 0
  if (pre) history.push({ attempt, seeded: true, critic: { findings: pre.last_findings }, judges: pre.judges || {}, audit: null })
  while (item.id === 0 || counted < 10) {  // L-433: item 0 has no round cap
    attempt++
    const d = dir(item, attempt)
    const prev = history[history.length - 1]
    // L-434: the 場面係 repairs battery-side findings while the worker repairs implementation-side ones;
    // the repaired battery is audited before the 資料係 (L-427/L-428 count it with this round)
    const batFix = prev ? (prev.critic ? prev.critic.findings : []).filter(f => f.target === '場面集' && f.level !== '示唆') : []
    let midAudits = []
    const repairP = (async () => {
      if (!batFix.length) return null
      let fixList = batFix
      for (let k = 1; ; k++) {
        const fixed = await repairBattery(item, req, bat, fixList, `r${attempt}-${k}`)
        if (!fixed) return { error: 'battery_repair_in_round' }
        bat = { ...bat, ...fixed }
        const a = await auditBattery(item, bat, `r${attempt}-${k}`, fixList)
        const fs = a ? a.findings : [{ id: `b-r${attempt}-${k}-x`, level: '止める', text: '監査役が返らなかった' }]
        midAudits.push({ k, findings: fs })
        const bst = fs.filter(f => f.level === '止める')
        if (!bst.length) return null
        bst.forEach(f => { cbchain[f.id] = f.repeat_of && cbchain[f.repeat_of] ? cbchain[f.repeat_of] + 1 : 1 })
        const r3 = bst.find(f => cbchain[f.id] >= 3)
        if (r3) return { escalate: `場面集の直しの監査で同じ未達の理由が 3 回続いた(L-407・L-424): ${r3.text.slice(0, 300)}` }
        fixList = fs
      }
    })()
    const allFix = history.flatMap(h => (h.critic ? h.critic.findings : []).filter(f => f.level !== '示唆'))  // critic sees both targets for repeat_of
    const openFix = history.flatMap(h => [...(h.critic ? h.critic.findings : []).filter(f => f.level !== '示唆' && f.target !== '場面集'), ...((h.audit && h.audit.findings) || []).filter(f => f.level !== '聞く').map(f => ({ ...f, source: '監査役' }))])
    const wP = agent(`${attempt === 1 && item.id === 0 ? HEAD : HEAD2}
あなたは項目 ${item.id}「${item.title}」の作業者です(第 ${attempt} 周)。固定した要件: ${req.path}(変えない)。場面集: ${bat.definitions}(読めるが変えない。場面だけを特別扱いする直しは [止める])。持ち物は委任文 §2 の項目 ${item.id} の行のファイルだけ。${item.extra || ''}${(args.lead_notes || {})[item.id] || ''}
${attempt === 1 ? '最初の周です。要件の全行と比較の観点を満たす実装と試験を書く。' :
`前の周の批評・監査役・盲検の結果(未解消の指摘をすべて直す対象に入れる):
指摘(全周の [止める]・[直す]): ${JSON.stringify(openFix).slice(0, 12000)}
前の周の盲検: ${JSON.stringify(prev.judges).slice(0, 6000)}
**直す前に** ${d}/ROOTCAUSE.md に、指摘 1 件ごとに「なぜ起きたか(根本原因)」と「どの構造を変えるか」を書く(委任文 §3「根本的解決」)。場当たりの直し(試験だけの特別扱い・閾値や既定値をずらす・文言合わせ・機能を外す)をしない。`}
${SCRUTINY_FIX}
${batFix.length ? '場面係が同時に場面集(tests/bt/battery/item_' + item.id + '/)を直している(L-434)。場面集は読むだけで、場面集の実行は自分の作業の最後に 1 回だけ行う。' : ''}
試験は tests/bt/item_${item.id}/ に置く(委任文 §3「場面集の規則」7。src/ の下に置かない)。批評家の試験が試験自身の誤りで落ちるときは変えずに理由を報告に書く(規則 8)。自分の項目の試験と核の試験を回し、末尾の行を返す。structural_change には、この周で変えた構造を 1〜3 文で書く。${attempt === 1 && item.id === 0 ? `委任文 §6 の報告を ${d}/REPORT.md に書く。` : '委任文 §6 の報告は返り値の欄で返す(ファイルに書かない。リードの道具が REPORT.md に書き出す)。要件の各行の根拠(ファイル:行)は requirement_evidence に 1 行ずつ、満たせなかった行とその理由は unmet に、§4 の検査の結果は external_tool_checks に(外部の道具を入れていなければ「入れていない」)。'}`,
      { label: `作る:${item.id}#${attempt}`, phase: '作る', schema: attempt === 1 && item.id === 0 ? WORK_SCHEMA : WORK_SCHEMA2, model: item.model === 'opus' ? OPUS : (item.model || MODEL), effort: 'high' })
    const [w, repairOut] = await Promise.all([wP, repairP])
    if (repairOut && repairOut.error) return { item, status: 'error', stage: repairOut.error, attempt, history }
    if (repairOut && repairOut.escalate) return { item, status: 'escalate', reason: repairOut.escalate, attempts: attempt, req, bat, history }
    if (!w) return { item, status: 'error', stage: 'worker', attempt, history }

    const t = await agent(`${HEAD2}
あなたは項目 ${item.id} の資料係(第 ${attempt} 周。作業者とは別の者)です。委任文 §3「比較の表」に従う。**文章を書かない。表はスクリプトの出力だけ。**
1. 新実装の adapter を ${bat.battery_dir} に書く(新実装の公開された口だけを呼ぶ。新実装の本体は変えない)。
2. ${bat.runner} で、新実装・当方の現状・調査結果の側(入れられた道具すべて)・試金石(${bat.mutant})を、それぞれ 2 回走らせる。
3. 委任文 §3「比較の表」と「場面集の規則」3〜5 に従う(観点ごとにまとめ、観点ごとの一致の数を出す / 動かせた道具は全場面に通し、動かなかった場面は試したこととエラーと実測の時間を注記 / セルは正しさと再現の 2 欄 / 最も良い結果の順 = 正解と一致 > 対応なし > 不一致 > 結果なし、同じなら再現の欄で上下)。スクリプトで次の 6 つの表を ${d}/ に作る。行は 2 つだけで記号「A」「B」で伏せる。列 = 場面(観点ごとにまとめる)、セルは 2 つの欄(正しさ = 正解と一致 / 対応なし / 不一致(値)/ 結果なし、再現 = 2 回の実行で同じ / 2 回で違う(値)/ 結果なし)。調査結果の側は場面ごとに動かせた道具のうち最も良い結果を 1 行に寄せる(どの道具かは伏せる)。
   current_1(A = 新実装、B = 当方の現状)/ current_2(A と B を入れ替え)/ survey_1(A = 新実装、B = 調査結果の側)/ survey_2(入れ替え)/ mutant_1(A = 新実装、B = 試金石)/ mutant_2(入れ替え)。
   ファイル名は ${d}/表_<ランダムな 6 文字>.md にし、どの表が何かは表のファイルに書かない(返り値の tables と ${d}/materials/ の対応表に書く)。${d}/ に表_*.md がこの周の 6 枚のほかにあれば、前の起動のものなので ${d}/materials/stale/ に移し、移したことを commands に書く。
4. 表を作るスクリプト・実行の記録・対応表・確認に打ったコマンドの出力は、全部 ${d}/materials/ にファイルで保存する(scratchpad だけに置かない)。表の注記に道具を特定できる具体(道具の名前・時刻など)を書かず、それは materials の記録に書く(委任文 §3「比較の表」)。
5. 各組の 2 通りの表(current_1 と current_2 など)がバイト単位で同じかを md5sum で確かめ、出力を materials に保存し、identical に返す(同じなら委任文 §0 の L-422 でその組は同等)。
6. 相手の道具の結果は、場面集の指紋(委任文 §3「相手の道具の結果の再利用」のコマンド)が前の周と同じなら前の周の materials の結果を使ってよい(使ったことと指紋を materials と notes に記録)。新実装と試金石は毎周走らせる。${SCRUTINY_TABLE}
実データから出た数値は入れない。打ったコマンドを commands に返す。`,
      { label: `表:${item.id}#${attempt}`, phase: '比較資料', schema: TABLE_SCHEMA, model: IMPL_MODEL, effort: 'medium' })
    if (!t) return { item, status: 'error', stage: 'table', attempt, history }

    const critic = agent(`${HEAD2}
あなたは項目 ${item.id}「${item.title}」の批評家(第 ${attempt} 周。新しく起こされた者)です。**非常に厳しく**。固定した要件 ${req.path}、場面集 ${bat.definitions}、調査結果の該当行を手元に置く。
自分で試験を書いて壊しにいく(試験は tests/bt/critic/item_${item.id}/ に置く。壊れた試験は残し、作業者が直す)。前の周までの批評家の試験のうち、作業者が「試験自身の誤り」と報告したものを確かめ、誤りなら直すか理由を書いて取り下げる(委任文 §3「場面集の規則」8)。場面集が規則 1〜9 を守っているか(能力を申告で数えていないか等)も見る。前の周で「直った」とされた点も自分で確かめ直す。資料係の adapter(${JSON.stringify(t.adapters_changed).slice(0, 2000)})が対象を公平に呼んでいるか(新実装だけ有利・他が不利になる呼び方でないか)、場面係の検討表(${bat.battery_dir}/opponents/CONSIDERED.md)のスキップの理由が調査結果の行で裏付けられているか、再現(${bat.battery_dir}/opponents/)が一次資料どおりで弱められていないか、場面集が要件の観点を全部覆っているかも見る。
${attempt > 1 ? `前の周までの指摘(場面集の側は、この周の前に場面係が直し監査役が見た = 委任文 §3「場面集」): ${JSON.stringify(allFix).slice(0, 12000)}。同じ理由の指摘には repeat_of に前の指摘の id を入れ、そうでなければ null(必ず埋める)。「同じ理由」= 同じ根本原因の族(前の指摘と同じ機構の別の形。例: 帰属の穴が dict → 対象の class → 戦略の外の呼び出し、と形を変えたもの)。同じ場所・同じ文言に限らない。(直ったものは挙げない。直ったかは自分で確かめる)。` : (prior.critic_findings ? `前の起動の最後に数えた周の批評家の指摘(委任文 §3「周回の数え方と止める条件」4。id つき): ${JSON.stringify(prior.critic_findings).slice(0, 10000)}。同じ理由の指摘には repeat_of に前の指摘の id を入れ、そうでなければ null(必ず埋める)。「同じ理由」= 同じ根本原因の族(前の指摘と同じ機構の別の形。例: 帰属の穴が dict → 対象の class → 戦略の外の呼び出し、と形を変えたもの)。同じ場所・同じ文言に限らない。(直ったものは挙げない。直ったかは自分で確かめる)。` : '')}
場当たりの直し(試験や場面だけの特別扱い・閾値や既定値をずらす・文言合わせ・機能を外して要件から逃げる)を見つけたら patchwork=true の [止める] にする。格付けは委任文 §3「批評家」の「格付けの基準」どおり(要件・観点を 1 つでも満たさない / 正解と合わない / 試験が落ちる / 信頼性・再現性を崩す / 場当たり / §4 の禁止 / 場面集の規則違反 は [止める]。迷ったら重い方)。前の周の [直す]・[示唆] に [止める] の基準に当たるものがあれば付け直して理由を書く。
${attempt > 1 ? `前の周から構造の変化が無ければ structural_change_since_prev=false(作業者の申告: ${w.structural_change.slice(0, 1000)})。` : 'structural_change_since_prev は true。'}
指摘ごとに target を付ける: 場面集の側(tests/bt/battery/ の下 = 場面の定義・正解・runner・adapter・検討表・再現・mutant、資料係の表)なら「場面集」、新実装(src/bot/bt/)と作業者の試験なら「実装」。fix_files に、その指摘を直すために変えるべきファイルの path(リポジトリ相対)を全部書く(相手の根拠。src/bot/bt/ の下が 1 つでもあれば台本は相手を「実装」と数える = 付け違いで通過の判定が変わらないための機械、監査 58-3)。場面集の側の指摘は次の周の前に場面係が直す(委任文 §3「場面集」)。指摘の id は「i${item.id}-r${attempt}-<連番>」。根拠はファイル:行か、実行したコマンドと出力。記録を ${d}/CRITIC.md に書く。${SCRUTINY_CRITIC}`,
      { label: `批評:${item.id}#${attempt}`, phase: '批評', schema: CRITIC_SCHEMA, model: IMPL_MODEL, effort: 'high' })

    const judge = (key, file, newIsA, k) => agent(`あなたは盲検の審査員です。読むのは次の 2 つのファイルだけ(リポジトリの他の場所を開かない)。
場面の定義: ${bat.definitions}
結果の表: ${file}
表の行 A と行 B は 2 つの対象(バックテストのエンジン)です。どちらがどれかは知らされません。
問い: **表に示された実行の結果から、どちらの対象の振る舞いがより正しく(正解との一致・能力の有無)、より再現的(2 回の実行の一致)か。**観点ごとに比べ、場面の数の多い観点に引きずられない。資料の書き方は採点しない。
choice は行 A なら「左」、行 B なら「右」、表に示された結果にどちらが優れると言える差が無ければ「同等」。理由と、選んだ側に足りない場面(同等なら両方に足りない場面)を日本語で書く。${SCRUTINY_JUDGE}`,
      { label: `盲検:${item.id}#${attempt}:${key}${k}`, phase: '盲検', schema: JUDGE_SCHEMA, model: OPUS, effort: 'medium' })
      .then(j => j ? { ...j, new_chosen: j.choice !== '同等' && (j.choice === '左') === newIsA, opp_chosen: j.choice !== '同等' && (j.choice === '左') !== newIsA } : null)
    const trio = key => [0, 1, 2].map(k => {
      const v = (k + attempt) % 2 === 0 ? 1 : 2
      return judge(key, t.tables[`${key}_${v}`], v === 1, k)
    })

    if (attempt === 1) {
      const batAudit = await agent(`検査対象: 項目 ${item.id}「${item.title}」の最初の結果の表 ${Object.values(t.tables).join(' / ')} と、表を作った資料係の記録(${JSON.stringify({ commands: t.commands, adapters_changed: t.adapters_changed, notes: t.notes }).slice(0, 4000)})。場面集 ${bat.definitions} は作業者の前に監査を通っている(${batHist.length} 回)。委任文 ${DOC} §3「盲検の作り直し」「場面集の規則」「比較の表」と照らし、表が場面集の全場面に全員(当方の現状・調査結果の側の動かせた道具と再現・新実装)を通しているか、新実装の adapter が公開の口だけを公平に呼んでいるか、表に出所を示す語が残っていないか、断定と範囲を検査する。表が 6 枚そろっていなければ [止める]。指摘は [止める] / [直す] / [聞く] の印つきで返す。`,
        { label: `監査役(表):${item.id}`, phase: '批評', schema: AUDIT_SCHEMA, agentType: 'owner-auditor', model: MODEL })
      const batStops = batAudit ? batAudit.findings.filter(f => f.level === '止める') : [{ level: '止める', text: '監査役が返らなかった' }]
      if (batStops.length) return { item, status: 'escalate', reason: '最初の表が監査役の [止める] を受けた = 資料係の作りを直す', attempts: attempt, req, bat, batteryHistory: batHist, history: [{ attempt, worker: w, table: t, batteryAudit: batAudit }] }
      const cal = (await Promise.all(trio('mutant'))).filter(Boolean)
      const calOk = cal.length === 3 && cal.every(j => j.new_chosen)
      log(`項目 ${item.id} 試金石: 仕込んでいない方を選んだ ${cal.filter(j => j.new_chosen).length}/3`)
      if (!calOk) return { item, status: 'escalate', reason: '審査員の試金石に落ちた(不具合を仕込んだ版を選んだ審査員がいた)= 表・問いの作りを直す', attempts: attempt, req, bat, history: [{ attempt, worker: w, table: t, calibration: cal }] }
    }

    // L-422: a group whose two tables are byte-identical is 'equal' and passes without judges
    const eqC = !!t.identical.current, eqS = !!t.identical.survey
    const c = await critic
    const stops = c ? c.findings.filter(f => f.level === '止める') : [{ id: 'critic-missing', level: '止める', text: '批評家が返らなかった', evidence: '', repeat_of: null, patchwork: false, target: '実装', fix_files: ['src/bot/bt/'] }]
    // L-441 (案 2): item 0 passes on the implementation-side [止める] only; its battery-side [止める] are repaired in
    // parallel by batteryFollowUp() and do not hold items 1..12 (owner: 「案2 実装の通過と場面集の直しを分ける」)
    const { impl: stopsImpl, bat: stopsBat } = splitStops(item, stops)
    // L-443 (3): the blind judges sit only on a pass-candidate round (no implementation-side [止める]), on a round whose
    // structure changed (the critic's structural_change_since_prev) and on the first round; other rounds carry the last
    // judged round's verdicts (judgedAt) — a pass always rests on this round's own judges
    const { structural: structNow, judgeNow } = judgeRound(attempt, c, stopsImpl)
    let jc = [], jsv = [], judgedAt = attempt
    if (judgeNow) {
      const js = await Promise.all([...(eqC ? [] : trio('current')), ...(eqS ? [] : trio('survey'))])
      jc = (eqC ? [] : js.slice(0, 3)).filter(Boolean); jsv = (eqS ? [] : js.slice(eqC ? 0 : 3)).filter(Boolean)
    } else {
      const lastJ = [...history].reverse().find(h => h.judges && ((h.judges.current || []).length || (h.judges.survey || []).length))
      if (lastJ) { jc = lastJ.judges.current; jsv = lastJ.judges.survey; judgedAt = lastJ.attempt }
      log(`項目 ${item.id} 第 ${attempt} 周: 審査員は起こさない(実装の側の止める ${stopsImpl.length} 件・構造の変化なし)。第 ${judgedAt} 周の判定を使う(L-443)`)
    }
    const winsC = jc.filter(j => j.new_chosen).length, winsS = jsv.filter(j => j.new_chosen).length
    // L-431/L-432: parts pass on 'equal or better' (the opponent must not have a majority); item 13 needs 圧倒 (L-407 D 案2)
    const lossC = jc.filter(j => j.opp_chosen).length, lossS = jsv.filter(j => j.opp_chosen).length
    const overwhelm = item.id === 13
    const okC = eqC || (jc.length === 3 && (overwhelm ? winsC >= 2 : lossC < 2)), okS = eqS || (jsv.length === 3 && (overwhelm ? winsS >= 2 : lossS < 2))
    let audit = null
    if (okC && okS && stopsImpl.length === 0) {
      audit = await agent(`検査対象: 項目 ${item.id}「${item.title}」の作業者の報告(返り値の逐語: ${JSON.stringify(w).slice(0, 15000)})と、そこから引かれたファイル。組の判定: 対現状 ${eqC ? '同等(表が左右同一 = L-422)' : winsC + '/3'}・対調査 ${eqS ? '同等(表が左右同一 = L-422)' : winsS + '/3'}。審査員の出力の逐語(この周。new_chosen = 新実装を選んだ、opp_chosen = 相手を選んだ): ${JSON.stringify([...jc, ...jsv]).slice(0, 12000)}。批評家の出力の逐語: ${JSON.stringify(c ? c.findings : []).slice(0, 8000)}。${stopsBat.length ? `場面集の側の [止める] ${stopsBat.length} 件は、オーナー決定 L-441(「案2 実装の通過と場面集の直しを分ける」)により項目 0 の通過を止めず、通過のあと場面係が項目 1〜12 と並行して直す(台本の batteryFollowUp)。場面集の側の [止める] が残っていること自体はこの監査の [止める] の根拠にしない。**ただし、場面集の側とされた [止める] の 1 件ごとに、本文・根拠・fix_files を読み、直すべき物が実装(src/bot/bt/)なら付け違い = 通過の迂回として [止める] にする**(監査 58-3)。付け違いの候補(逐語): ${JSON.stringify(stopsBat.map(f => ({ id: f.id, target: f.target, fix_files: f.fix_files, text: f.text.slice(0, 600) }))).slice(0, 6000)}。リードはオーナーへの通過の報告にその件数と逐語を「並行して直しているもの」として書く。` : ''}round_${attempt}/JUDGES.md・AUDIT.md・REPORT.md は Workflow の記録からリードが周の終わりに書き出す(この監査の時点では無いことがある。無いことは [止める] の根拠にしない。第 9 周の報告の監査の指摘 1)。委任文 ${DOC} §0 の表のオーナーの原文と照らす。指摘は [止める] / [直す] / [聞く] の印つきで返す。`,
        { label: `監査役:${item.id}#${attempt}`, phase: '批評', schema: AUDIT_SCHEMA, agentType: 'owner-auditor', model: MODEL })
    }
    const auditStops = audit ? audit.findings.filter(f => f.level === '止める') : []
    history.push({ attempt, worker: w, table: t, critic: c, audit, judges: { current: jc, survey: jsv }, judgedAt, winsC, winsS, lossC, lossS, eqC, eqS, midAudits, lossStreak: { ...lossStreak } })
    const pass = audit !== null && auditStops.length === 0
    log(`項目 ${item.id} 第 ${attempt} 周: 対現状 ${eqC ? '同等(表が同一)' : `新 ${winsC}・相手 ${lossC}・同等 ${jc.length - winsC - lossC}`}・対調査 ${eqS ? '同等(表が同一)' : `新 ${winsS}・相手 ${lossS}・同等 ${jsv.length - winsS - lossS}`}・批評の止める ${stops.length} 件(実装 ${stopsImpl.length}・場面集 ${stopsBat.length})・監査役の止める ${audit ? auditStops.length : '未実施'} → ${pass ? '通過' : '未達'}`)
    if (pass) return { item, status: 'pass', attempts: attempt, req, bat, history, openBattery: c ? c.findings.filter(f => f.target === '場面集' && f.level !== '示唆') : [], bchain: cbchain }

    // counting rules (委任文 §3 根本的解決)
    const structural = structNow  // audit 62-2: one definition (judgeRound), a missing critic counts as structural
    if (structural) { counted++; nonStructural = 0 } else { nonStructural++ }
    if (nonStructural >= 2) return { item, status: 'escalate', reason: '構造の変化が無い周が 2 回続いた', attempts: attempt, req, history }
    let repeated = null
    for (const f of stops) {
      const ch = f.target === '場面集' ? cbchain : chain
      ch[f.id] = f.repeat_of && ch[f.repeat_of] ? ch[f.repeat_of] + 1 : 1
      if (ch[f.id] >= 3) repeated = f
    }
    // audit 62-1: a loss is counted only on a round whose judges actually sat; a carried-over verdict is not a new judgement
    if (judgeNow) { lossStreak.current = okC ? 0 : lossStreak.current + 1; lossStreak.survey = okS ? 0 : lossStreak.survey + 1 }
    history[history.length - 1].lossStreak = { ...lossStreak }  // the snapshot the lead carries into the next launch
    if (repeated) return { item, status: 'escalate', reason: `同じ [止める] が 3 周続いた${item.id === 0 ? '(項目 0: 未達ではなくリードへの戻し = L-436)' : ''}: ${repeated.text}`, attempts: attempt, req, history }
    if (lossStreak.current >= 3 || lossStreak.survey >= 3) return { item, status: 'escalate', reason: `盲検で 3 周続けて負けた(対現状 ${lossStreak.current}・対調査 ${lossStreak.survey})`, attempts: attempt, req, history }
  }
  return { item, status: 'escalate', reason: '周回の上限 10 に達した', attempts: attempt, req, history }
}

// L-441 (案 2): after item 0 passes on the implementation side, its battery-side findings keep being repaired in
// parallel with items 1..12 — the definition step for [止める] as always (L-440 案 1), the repair, then the battery
// audit — until the audit has no [止める] or the family rule returns it to the lead (no repair cap: L-433). Never silent:
// a stop is written to FOLLOWUP_STOPPED.md by an agent (audit 59-4)
async function batteryFollowUp(item, req, bat, findings, chainObj) {
  const hist = []
  let fixList = findings
  // audit 59-4: an end that is not a pass is written to a file by an agent, so it shows in the journal (the stall watcher
  // and the 見回り grep the label) and on disk — log() alone reaches nobody until the run ends
  const done = async out => {
    log(`並行の直し(項目 ${item.id}): ${out.status}${out.reason ? ' — ' + out.reason : ''}(直し ${hist.length} 回)`)
    if (out.status !== 'pass') await agent(`${HEAD2}
並行の直し(項目 ${item.id})が止まった。次の文をそのまま ${REC}/item_${item.id}/battery/FOLLOWUP_STOPPED.md に書く(1 行目に状態、2 行目に理由、3 行目に直しの回数 ${hist.length})。ほかは何もしない。状態: ${out.status}。理由: ${out.reason || out.stage || ''}`, { label: `並行の直しの戻し:${item.id}`, phase: '要件の固定', model: MODEL, effort: 'low' })
    return out
  }
  log(`並行の直し(項目 ${item.id})を始める: 指摘 ${findings.length} 件(止める ${findings.filter(f => f.level === '止める').length})`)
  // no repair cap: item 0 has no round cap (L-433); the follow-up ends on a clean battery audit or the family rule (3)
  for (let k = 1; ; k++) {
    const n = `f${k}`
    const fixed = await repairBattery(item, req, bat, fixList, n)
    if (!fixed) return done({ status: 'error', stage: 'battery_followup', history: hist, bat })
    bat = { ...bat, ...fixed }
    const a = await auditBattery(item, bat, n, fixList)
    const fs = a ? a.findings : [{ id: `b${n}-x`, level: '止める', text: '監査役が返らなかった', repeat_of: null }]
    hist.push({ k: n, findings: fs })
    const stops = fs.filter(f => f.level === '止める')
    log(`並行の直し(項目 ${item.id}) ${n}: 監査役(場面)の止める ${stops.length} 件`)
    if (!stops.length) return done({ status: 'pass', history: hist, bat })
    stops.forEach(f => { chainObj[f.id] = f.repeat_of && chainObj[f.repeat_of] ? chainObj[f.repeat_of] + 1 : 1 })
    const r3 = stops.find(f => chainObj[f.id] >= 3)
    if (r3) return done({ status: 'escalate', reason: `場面集の並行の直しの監査で同じ未達の理由が 3 回続いた(L-407): ${r3.text.slice(0, 300)}`, history: hist, bat })
    fixList = fs
  }
}

function brief(r) {
  if (!r) return null
  const last = r.history && r.history[r.history.length - 1]
  return { id: r.item.id, title: r.item.title, status: r.status, reason: r.reason || null, attempts: r.attempts || 0,
    req: r.req ? r.req.path : null,
    battery: r.batteryHistory ? r.batteryHistory.map(h => ({ n: h.n, stops: h.findings.filter(f => f.level === '止める').map(f => f.text.slice(0, 300)) })) : null,
    last: last ? { winsC: last.winsC, winsS: last.winsS,
      findings: last.critic ? last.critic.findings : null,
      judges: last.judges, loss_streak: last.lossStreak || null, worker: { test_tail: last.worker.test_tail, unmet: last.worker.unmet, questions: last.worker.questions_for_lead, changed: last.worker.changed_files } } : null }
}

const results = {}
const only = args.only || null
const byId = Object.fromEntries(ITEMS.map(it => [it.id, it]))

// stage 1: core
if (!only || only.includes(0)) {
  results[0] = await runItem(byId[0])
  if (results[0].status !== 'pass') return { stopped_at: 'core', results: Object.values(results).map(brief) }
}
// L-441 (案 2): the battery-side findings left open at item 0's pass are repaired while items 1..12 run
let batteryFollow = null
if (results[0] && results[0].openBattery && results[0].openBattery.length) {
  log(`L-441: 項目 0 は実装の側で通過。場面集の側の指摘 ${results[0].openBattery.length} 件は項目 1〜12 と並行して場面係が直す`)
  batteryFollow = batteryFollowUp(byId[0], results[0].req, results[0].bat, results[0].openBattery, results[0].bchain || {})
}
async function finish(out) { out.battery_followup = batteryFollow ? await batteryFollow : null; return out }

// stage 2: items 1..12 in parallel
const mid = ITEMS.filter(it => it.id >= 1 && it.id <= 12 && (!only || only.includes(it.id)))
const midRes = await parallel(mid.map(it => () => runItem(it)))
midRes.forEach((r, i) => { results[mid[i].id] = r || { item: mid[i], status: 'error' } })
const blocked = Object.values(results).filter(r => r.status !== 'pass')
if (blocked.length) return finish({ stopped_at: 'parallel', results: Object.values(results).map(brief) })

// stage 3: compat (14), then integration (13)
for (const id of [14, 13]) {
  if (only && !only.includes(id)) continue
  results[id] = await runItem(byId[id])
  if (results[id].status !== 'pass') return finish({ stopped_at: `item_${id}`, results: Object.values(results).map(brief) })
}

// stage 4: completeness critic loop
let nextId = 15
let gapRounds = 0
const extra = []
while (true) {
  const leftovers = Object.values(results).flatMap(r => {
    const last = r.history[r.history.length - 1]
    return (last.critic ? last.critic.findings : []).filter(f => f.level !== '止める').map(f => ({ item: r.item.id, ...f }))
  })
  const gap = await agent(`${HEAD2}
あなたは「欠けているものは何か」の批評家です(委任文 §3 の最後の段)。オーナーの完了の形「このプロジェクトで実施し得る全てのバックテストが可能な汎用バックテスト環境」「すべてが調査結果以上の信頼性と再現性に優れたもの」「そのバックテストの内容を項目別にダッシュボードから確認できるように」に照らし、
いまの src/bot/bt/・ダッシュボード・試験を実際に動かして、欠けている項目を探す。道具台帳・データ(§1)・research-protocol・今の研究スクリプトが使う測り方(読むのは測り方だけ。結論は読まない)と突き合わせる。
各項目で残った [直す]・[示唆]: ${JSON.stringify(leftovers).slice(0, 20000)}
欠けているものがあれば、新しい項目(持ち物と要件)として返す。無ければ空の配列。記録を ${REC}/GAPS_${nextId}.md に書く。${SCRUTINY_GAPS}`,
    { label: `欠けているもの#${nextId}`, phase: '欠けているもの', schema: GAP_SCHEMA, model: MODEL, effort: 'high' })
  if (!gap || gap.new_items.length === 0) break
  const newItems = gap.new_items.map(g => ({ id: nextId++, title: g.title, extra: `持ち物: ${g.owned}。要件: ${g.requirement}(欠けていた理由: ${g.why_missing})` }))
  extra.push(...newItems.map(x => x.id))
  const rs = await parallel(newItems.map(it => () => runItem(it)))
  rs.forEach((r, i) => { results[newItems[i].id] = r || { item: newItems[i], status: 'error' } })
  if (rs.some(r => !r || r.status !== 'pass')) return finish({ stopped_at: 'gaps', results: Object.values(results).map(brief) })
  gapRounds++
  if (gapRounds >= 3) return finish({ stopped_at: 'gaps_3_rounds', extra_items: extra, results: Object.values(results).map(brief) })
}
return finish({ stopped_at: 'done', extra_items: extra, results: Object.values(results).map(brief) })
