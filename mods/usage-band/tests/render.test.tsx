import { describe, expect, test } from 'claude-code/testing'

import { bandRows } from './drawn'

const BAND = { component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 120, scroll: { offset: 0, bodyRows: 6 } } } as const
const NOW = Date.parse('2026-10-16T12:00:00Z')

describe('band', () => {
  test('the terminal draws chips laid out to its width; the desktop draws the SVG under a click layer', async ($, on) => {
    on('session.usage', () => ({ value: {
      startedAt: NOW - 3_600_000,
      context: { tokens: 954_200, window: 1_000_000, percent: 95 },
      rateLimits: [{ kind: 'five_hour', percentUsed: 20, resetsAt: new Date(NOW + 9_600_000).toISOString() }],
      cost: { usd: 4.32 },
    } }))
    on('session.turns', () => ({ value: 5 }))
    on('clock.now', () => ({ value: NOW }))

    const desk = await $.ui.mount({ plugin: 'usage-band', surface: 'desktop', ...BAND } as never)
    expect(await desk.find({ type: 'Svg' } as never)).toBeDefined()
    expect(await desk.find({ type: 'Client', key: 'hit-0' } as never)).toBeDefined()
    await desk.unmount()

    for (const surface of ['terminal'] as const) {
      const ui = await $.ui.mount({ plugin: 'usage-band', surface, ...BAND } as never)
      expect(await ui.find({ type: 'Client', key: 'band' } as never)).toBeDefined()

      await ui.resize({ columns: 160, rows: 4, in: 'band' } as never)
      const wide = bandRows(await ui.drawn({ in: 'band' } as never))
      expect(wide.length).toBe(2)
      expect(wide[0]).toContain('5h')
      expect(wide[0]).toContain('20%')
      expect(wide[0]).toContain('2h 40m')
      expect(wide[0]).toContain('954.2k/1M')
      expect(wide[1]).toContain('$4.32')

      await ui.resize({ columns: 60, rows: 6, in: 'band' } as never)
      expect(bandRows(await ui.drawn({ in: 'band' } as never)).length).toBe(4)
      await ui.unmount()
    }
  })
})
