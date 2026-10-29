// Turn spans from a hand-made transcript (the plugin tests have no process or files): a /goal turn with no
// prompt line, a /compact typed days after the last turn, and a resume that appends earlier lines again.
// Usage: node mods/usage-band/bench/turns.mjs
import { execFileSync } from 'node:child_process'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const { SCAN_AWK, SCAN_SH } = await import(new URL('../hooks/scan.ts', import.meta.url).href)

const prompt = (uuid, promptId, timestamp) => ({ parentUuid: null, isSidechain: false, promptId, type: 'user', message: { role: 'user', content: 'go' }, uuid, timestamp, promptSource: 'sdk' })
const user = (uuid, promptId, timestamp) => ({ parentUuid: null, isSidechain: false, promptId, type: 'user', message: { role: 'user', content: 'x' }, uuid, timestamp })
const reply = (uuid, timestamp) => ({ parentUuid: null, isSidechain: false, message: { model: 'm', id: `msg_${uuid}`, type: 'message', role: 'assistant', content: [] }, uuid, timestamp })

const lines = [
  prompt('a1', 'p1', '2026-10-25T10:00:00.000Z'),
  reply('a2', '2026-10-25T10:05:00.000Z'),
  // /goal an hour later: its lines carry a new promptId and no prompt line
  user('b1', 'p2', '2026-10-25T11:00:00.000Z'),
  reply('b2', '2026-10-25T11:30:00.000Z'),
  // /compact three days later
  user('c1', 'p3', '2026-10-28T20:36:00.000Z'),
  user('c2', 'p3', '2026-10-28T20:37:00.000Z'),
  prompt('d1', 'p4', '2026-10-28T21:00:00.000Z'),
  reply('d2', '2026-10-28T21:10:00.000Z'),
  // a resume appends earlier lines again with their own timestamps
  prompt('a1', 'p1', '2026-10-25T10:00:00.000Z'),
  reply('a2', '2026-10-25T10:05:00.000Z'),
  reply('d3', '2026-10-28T21:12:00.000Z'),
]

const work = mkdtempSync(join(tmpdir(), 'usage-band-turns-'))
const file = join(work, 't.jsonl')
writeFileSync(file, lines.map(l => JSON.stringify(l)).join('\n') + '\n')
const out = execFileSync('/bin/sh', ['-c', SCAN_SH, 'sh', file, join(work, 'st'), SCAN_AWK]).toString()
rmSync(work, { recursive: true })

const got = out.split('\n').filter(l => l.startsWith('T ')).map(l => l.split(' ').slice(1, 3).join(' '))
const want = [
  '2026-10-25T10:00:00.000Z 2026-10-25T10:05:00.000Z',
  '2026-10-25T11:00:00.000Z 2026-10-25T11:30:00.000Z',
  '2026-10-28T20:36:00.000Z 2026-10-28T20:37:00.000Z',
  '2026-10-28T21:00:00.000Z 2026-10-28T21:12:00.000Z',
]
const same = JSON.stringify(got) === JSON.stringify(want)
console.log(same ? 'SAME' : `DIFF\n got  ${got.join('\n      ')}\n want ${want.join('\n      ')}`)
process.exit(same ? 0 : 1)
