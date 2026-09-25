// node --test tests/workflows/ — the pure parts of scripts/workflows/backtest_env.js (audit 58-5): the item-0 side split
// (L-441 + 58-3 + 59-1) and the parallel battery follow-up's exits (pass / same-family 3 / repair error; no repair cap, no definition step = L-443). The functions are cut out
// of the script text and run with stubs, because the script itself only runs inside the Workflow harness.
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const src = readFileSync(join(here, '..', '..', 'scripts', 'workflows', 'backtest_env.js'), 'utf8')
function cut(name) {
  const i = src.indexOf(`function ${name}(`)
  const start = src.lastIndexOf('\n', i) + 1
  let depth = 0, j = src.indexOf('{', i)
  for (; j < src.length; j++) { if (src[j] === '{') depth++; else if (src[j] === '}') { depth--; if (depth === 0) break } }
  return src.slice(start, j + 1)
}
const splitStops = new Function(`${cut('splitStops')}; return splitStops`)()
const makeFollowUp = (st) => new Function('repairBattery', 'auditBattery', 'log', 'agent', 'HEAD2', 'REC', 'MODEL', `${cut('batteryFollowUp')}; return batteryFollowUp`)(
  st.repairBattery, st.auditBattery, st.log || (() => {}), st.agent || (async () => 'ok'), '', '/rec', 'm')

const stop = (id, target, fix_files = [], repeat_of = null) => ({ id, level: '止める', target, fix_files, repeat_of, text: id, evidence: '', patchwork: false })

test('item 0: a stop tagged 場面集 whose fix touches src/bot/bt/ counts as implementation-side (58-3)', () => {
  const r = splitStops({ id: 0 }, [stop('a', '場面集', ['tests/bt/battery/item_0/scenes.py']), stop('b', '場面集', ['./src/bot/bt/core/engine.py']), stop('c', '実装', ['x'])])
  assert.deepEqual(r.impl.map(f => f.id), ['b', 'c'])
  assert.deepEqual(r.bat.map(f => f.id), ['a'])
})

test('item 0: a 場面集-tagged stop with empty, missing or non-battery fix_files blocks the pass (59-1)', () => {
  const r = splitStops({ id: 0 }, [stop('e', '場面集', []), { ...stop('m', '場面集'), fix_files: undefined }, stop('o', '場面集', ['tests/bt/battery/item_0/scenes.py', 'docs/x.md'])])
  assert.deepEqual(r.impl.map(f => f.id), ['e', 'm', 'o']); assert.equal(r.bat.length, 0)
})

test('other items: every stop blocks the pass', () => {
  const r = splitStops({ id: 3 }, [stop('a', '場面集', ['tests/bt/battery/item_3/x.py'])])
  assert.equal(r.impl.length, 1); assert.equal(r.bat.length, 0)
})

test('follow-up passes when the battery audit has no stop', async () => {
  const logs = []
  const f = makeFollowUp({ defineThenAudit: async () => ({ definition: 'd' }), repairBattery: async () => ({ scenarios: 33 }),
    auditBattery: async () => ({ findings: [{ id: 'x', level: '直す', text: '', repeat_of: null }] }), log: m => logs.push(m) })
  const out = await f({ id: 0 }, {}, { scenarios: 32 }, [stop('i0-r11-02', '場面集')], {})
  assert.equal(out.status, 'pass'); assert.equal(out.bat.scenarios, 33); assert.equal(out.history.length, 1)
  assert.ok(logs.some(m => m.includes('pass')))
})

test('follow-up returns to the lead when the same family stops 3 times', async () => {
  let k = 0
  const f = makeFollowUp({ defineThenAudit: async () => ({ definition: 'd' }), repairBattery: async () => ({}),
    auditBattery: async () => { k++; return { findings: [{ id: `s${k}`, level: '止める', text: 'same', repeat_of: k > 1 ? `s${k - 1}` : null }] } } })
  const chain = {}
  const out = await f({ id: 0 }, {}, {}, [stop('i0', '場面集')], chain)
  assert.equal(out.status, 'escalate'); assert.match(out.reason, /3 回続いた/); assert.equal(k, 3); assert.equal(chain.s3, 3)
})

test('follow-up has no repair cap (L-433): new families keep being repaired until the audit is clean', async () => {
  let k = 0
  const f = makeFollowUp({ defineThenAudit: async () => ({ definition: 'd' }), repairBattery: async () => ({}),
    auditBattery: async () => { k++; return { findings: k < 7 ? [{ id: `n${k}`, level: '止める', text: 'new', repeat_of: null }] : [] } } })
  const out = await f({ id: 0 }, {}, {}, [stop('i0', '場面集')], {})
  assert.equal(out.status, 'pass'); assert.equal(k, 7)
})

test('a follow-up that does not pass is written to a file by an agent (59-4)', async () => {
  const calls = []
  let k = 0
  const f = makeFollowUp({ repairBattery: async () => ({}),
    auditBattery: async () => { k++; return { findings: [{ id: `s${k}`, level: '止める', text: 'same', repeat_of: k > 1 ? `s${k - 1}` : null }] } },
    agent: async (prompt, opts) => { calls.push({ prompt, opts }); return 'ok' } })
  const out = await f({ id: 0 }, {}, {}, [stop('i0', '場面集')], {})
  assert.equal(out.status, 'escalate'); assert.equal(calls.length, 1)
  assert.equal(calls[0].opts.label, '並行の直しの戻し:0'); assert.match(calls[0].prompt, /FOLLOWUP_STOPPED\.md/)
})

test('a repair that returns nothing ends the follow-up as an error, also written to the file', async () => {
  const calls = []
  const f = makeFollowUp({ repairBattery: async () => null, auditBattery: async () => ({ findings: [] }), agent: async (prompt, opts) => { calls.push(opts.label); return 'ok' } })
  const out = await f({ id: 0 }, {}, {}, [stop('i0', '場面集')], {})
  assert.equal(out.status, 'error'); assert.deepEqual(calls, ['並行の直しの戻し:0'])
})
