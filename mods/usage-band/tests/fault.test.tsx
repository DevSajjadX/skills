import { describe, expect, test } from 'claude-code/testing'
import type { Register } from 'claude-code'

import { register } from '../hooks/register'

type Hook = (...a: unknown[]) => unknown
// The kit raises ui.fault only for a Client that really fails, and these modules have no input that
// fails them, so the hooks are taken from register itself and run on a fake of the two calls they make.
// shortcut: the drawings without Clients after a fault go untested; add a mount test once the kit can fail a Client on demand.
const hooksOf = () => {
  const hooks = new Map<string, Hook>()
  const on = ((event: string, ...rest: unknown[]) => (hooks.set(event, rest.at(-1) as Hook), { catch: () => undefined })) as unknown as Parameters<Register>[0]
  register(on, {} as never)
  return hooks
}
// What the desktop reported when the frame missed its load watchdog (claude.ai-web.log, 2026-10-18).
const FAULT = { surface: 'desktop', component: 'AbovePrompt', requestId: 'r', element: 'hit-0', module: 'hooks/hit.client.tsx', phase: 'load', reason: "did not load: the module's top level never settled" }

describe('fault', () => {
  test('a torn-down Client is drawn again on the next retry beat, and only then', async () => {
    const hooks = hooksOf()
    let beat: (() => void) | undefined
    let every = 0
    const invalidated: string[] = []
    const $ = {
      clock: { every: (ms: number, fn: () => void) => ((every = ms), (beat = fn), { cancel: () => undefined }) },
      ui: { invalidate: (event: string) => invalidated.push(event) },
      // The rest of session.start is not under test: its first awaited call fails it, after the timer started.
      command: { register: () => Promise.reject(new Error('not under test')) },
    }
    const next = async () => ({})
    await Promise.resolve(hooks.get('session.start')!($, { cwd: '/p', surface: 'desktop', isInteractive: true }, next)).catch(() => undefined)
    expect(every).toBe(30_000)

    beat!()
    expect(invalidated).toEqual([])

    expect(await hooks.get('ui.fault')!($, FAULT, next)).toEqual({})
    beat!()
    expect(invalidated).toEqual(['ui.render'])

    // Drawn again and not failed since: the beat has nothing to retry.
    beat!()
    expect(invalidated).toEqual(['ui.render'])
  })
})
