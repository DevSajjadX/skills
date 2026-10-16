import { describe, expect, test } from 'claude-code/testing'

import { parseScan } from '../hooks/scan'

describe('scan', () => {
  test('sums turn spans, logs each turn, reads token and compaction totals', () => {
    const out = 'T 2026-10-16T08:50:00.000Z 2026-10-16T08:55:00.000Z 1000\nT 2026-10-16T09:00:00.000Z 2026-10-16T09:00:30.000Z 3000\nU 1 2 3 4\nC 5\n'
    expect(parseScan(out)).toEqual({
      agentMs: 330_000,
      turns: 2,
      tokens: { input: 1, output: 2, cacheRead: 3, cacheWrite: 4 },
      compactions: 5,
      log: [
        { startAt: Date.parse('2026-10-16T08:50:00.000Z'), ms: 300_000, ctx: 1000 },
        { startAt: Date.parse('2026-10-16T09:00:00.000Z'), ms: 30_000, ctx: 3000 },
      ],
      sinceCompact: 2,
    })
  })
  test('a compaction restarts the count of turns since it', () => {
    const out = 'T 2026-10-16T08:50:00.000Z 2026-10-16T08:51:00.000Z 9000\nB\nT 2026-10-16T09:00:00.000Z 2026-10-16T09:01:00.000Z 2000\nC 1\n'
    const scan = parseScan(out)
    expect(scan.sinceCompact).toBe(1)
    expect(scan.turns).toBe(2)
  })
  test('empty output is an empty scan', () => {
    expect(parseScan('').turns).toBe(0)
  })
})
