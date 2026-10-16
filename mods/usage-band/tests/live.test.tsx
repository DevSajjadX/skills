import { describe, expect, test } from 'claude-code/testing'

import { bandRows, cardX } from './drawn'

const NOW = Date.parse('2026-10-16T12:00:00Z')
const BAND = { component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 200, scroll: { offset: 0, bodyRows: 6 } } } as const
const PANE = { component: 'Pane', requestId: 'usage-band', props: { title: 'Usage details', isFocused: true, bodyColumns: 80, placement: 'dock' } } as const

const engine = (on: (...a: never[]) => void) => {
  const o = on as unknown as (ev: string, fn: (...a: never[]) => unknown) => void
  o('session.usage', () => ({ value: { startedAt: NOW, context: { tokens: 1000, window: 10_000, percent: 10 }, rateLimits: [], cost: { usd: 1 } } }))
  o('clock.now', () => ({ value: NOW }))
}

describe('tests pill', () => {
  test('a Bash test run sets it, a later code edit stales it, a non-test command leaves it', async ($, on) => {
    engine(on as never)
    let out = { isError: false, text: ' 12 pass\n 0 fail\n' }
    // As core answers: the tool's record, the text the model reads, isError on a failure.
    on('tool.call', () => ({ result: { stdout: out.text, stderr: '', interrupted: false }, text: out.text, ...(out.isError ? { isError: true } : {}) }) as never)

    const text = async () => {
      const ui = await $.ui.mount({ plugin: 'usage-band', surface: 'terminal', ...BAND } as never)
      await ui.resize({ columns: 200, rows: 4, in: 'band' } as never)
      const t = bandRows(await ui.drawn({ in: 'band' } as never)).join('\n')
      await ui.unmount()
      return t
    }

    await $.tool.call({ tool: 'Bash', command: 'ls tests' } as never)
    expect(await text()).not.toContain('tests')

    await $.tool.call({ tool: 'Bash', command: 'pnpm test' } as never)
    expect(await text()).toMatch(/✓ tests[^\n]*\n[^\n]*12 passed/)

    out = { isError: false, text: 'ok' }
    await $.tool.call({ tool: 'Edit', file_path: '/p/a.ts', old_string: 'a', new_string: 'b' } as never)
    expect(await text()).toMatch(/○ tests[^\n]*\n[^\n]*stale/)

    out = { isError: true, text: 'Tests: 2 failed, 10 passed' }
    await $.tool.call({ tool: 'Bash', command: 'vitest run' } as never)
    expect(await text()).toMatch(/✗ tests[^\n]*\n[^\n]*2 failed/)
  })
})

describe('click', () => {
  test('a click on the ctx card opens the pane with Context first', async ($, on) => {
    engine(on as never)
    const opened: string[] = []
    on('ui.open', (_$, e) => (opened.push((e as { id: string }).id), { value: { isPlaced: true } }) as never)

    // Desktop: one strip per card row; the strip that gets the click is the row, the column is x.
    const band = await $.ui.mount({ plugin: 'usage-band', surface: 'desktop', ...BAND } as never)
    const strips = (await band.findAll({ type: 'Client' } as never)) as unknown as { key: string; props: { props: { boxes: { x: number; w: number; tone: string }[]; width: number } } }[]
    expect(strips.length).toBe(2)
    const top = strips.find(c => c.props.props.boxes.some(b => b.tone === 'ctx'))!
    const { boxes, width } = top.props.props
    const ctx = boxes.find(b => b.tone === 'ctx')!
    const cols = 94
    await band.resize({ columns: cols, rows: 1, in: top.key } as never)
    const x = Math.floor(((ctx.x + ctx.w / 2) / width) * cols)
    await band.pointer({ type: 'down', x, y: 0, button: 'left', in: top.key } as never)
    await band.pointer({ type: 'up', x, y: 0, button: 'left', in: top.key } as never)
    expect(opened).toEqual(['usage-band'])
    await band.unmount()

    // Terminal: a click on the ctx chip does the same.
    const term = await $.ui.mount({ plugin: 'usage-band', surface: 'terminal', ...BAND } as never)
    await term.resize({ columns: 200, rows: 4, in: 'band' } as never)
    const tx = cardX(await term.drawn({ in: 'band' } as never), 0, 'ctx')
    expect(tx).toBeGreaterThan(0)
    await term.pointer({ type: 'up', x: tx, y: 0, button: 'left', in: 'band' } as never)
    expect(opened).toEqual(['usage-band', 'usage-band'])
    await term.unmount()

    const pane = await $.ui.mount({ plugin: 'usage-band', surface: 'desktop', ...PANE } as never)
    const heads = (await pane.findAll({ type: 'Text' } as never)).map(t => String((t as { text?: string }).text))
    const first = heads.find(h => /^(Limits|Context|Tokens|Cost|Turns|Tests)/.test(h))
    expect(first).toBe('Context')
    await pane.unmount()
  })
})

describe('details', () => {
  test('the pane draws every section', async ($, on) => {
    engine(on as never)
    for (const surface of ['terminal', 'desktop'] as const) {
      const pane = await $.ui.mount({ plugin: 'usage-band', surface, ...PANE } as never)
      for (const h of ['Limits', 'Context', 'Tokens', 'Cost', 'Tests']) expect(await pane.find({ type: 'Text', text: new RegExp(`^${h}`) } as never)).toBeDefined()
      await pane.unmount()
    }
  })
})
