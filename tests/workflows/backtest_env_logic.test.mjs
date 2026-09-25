// node --test tests/workflows/ — the pure parts of scripts/workflows/backtest_env.js (audit 58-5): the item-0 side split
// (L-441 + 58-3) and the parallel battery follow-up's exits (pass / same-family 3 / 5 repairs). The functions are cut out
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
const makeFollowUp = (st) => new Function('defineThenAudit', 'repairBattery', 'auditBattery', 'log', `${cut('batteryFollowUp')}; return batteryFollowUp`)(
  st.defineThenAudit, st.repairBattery, st.auditBattery, st.log || (() => {}))

const stop = (id, target, fix_files = [], repeat_of = null) => ({ id, level: '止める', target, fix_files, repeat_of, text: id, evidence: '', patchwork: false })

test('item 0: a stop tagged 場面集 whose fix touches src/bot/bt/ counts as implementation-side (58-3)', () => {
  const r = splitStops({ id: 0 }, [stop('a', '場面集', ['tests/bt/battery/item_0/scenes.py']), stop('b', '場面集', ['./src/bot/bt/core/engine.py']), stop('c', '実装', [])])
  assert.deepEqual(r.impl.map(f => f.id), ['b', 'c'])
  assert.deepEqual(r.bat.map(f => f.id), ['a'])
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

test('follow-up stops after 5 repairs when stops keep changing family', async () => {
  let k = 0
  const f = makeFollowUp({ defineThenAudit: async () => ({ definition: 'd' }), repairBattery: async () => ({}),
    auditBattery: async () => { k++; return { findings: [{ id: `n${k}`, level: '止める', text: 'new', repeat_of: null }] } } })
  const out = await f({ id: 0 }, {}, {}, [stop('i0', '場面集')], {})
  assert.equal(out.status, 'escalate'); assert.match(out.reason, /5 回/); assert.equal(k, 5)
})

test('follow-up escalates when the definition step escalates', async () => {
  const f = makeFollowUp({ defineThenAudit: async () => ({ escalate: '定義の段が 3 回で通らなかった' }), repairBattery: async () => ({}), auditBattery: async () => ({ findings: [] }) })
  const out = await f({ id: 0 }, {}, {}, [stop('i0', '場面集')], {})
  assert.equal(out.status, 'escalate'); assert.match(out.reason, /定義の段/)
})
