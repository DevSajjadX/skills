import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, RenderChildren } from 'claude-code'

import type { Stats } from '../types'
import { bandSvg, bandText, bandWidth, fmtSpan, fmtTokens } from './pills'
import { NO_SCAN, SCAN_AWK, parseScan } from './scan'
import { isCode, isTestCommand, testOutcome } from './testrun'
import { buildView, layouts } from './view'

const PANE = 'usage-band'
const EMPTY: Stats = { transcript: '', scan: NO_SCAN, turnCosts: [] }
const stats = atom({ plugin: 'usage-band', key: 'stats' } as const, EMPTY)
// A Stats kept by an older version lacks newer fields; the spread fills them in.
const load = async ($: EngineInterface): Promise<Stats> => {
  const s = { ...EMPTY, ...(await read($, stats)) }
  return { ...s, scan: { ...NO_SCAN, ...s.scan } }
}

// The transcript is the one record of the whole session (turns before this band loaded, reloads,
// compactions), so tokens, agent time and compactions are read from it, never kept as counters.
// Awaited by the hook that asks: work a hook leaves running is cut off when its dispatch ends.
// shortcut: rereads the whole transcript each turn (~3s at 80 MB, waited on after the turn's own work); scan only the bytes past the last offset if that gets slow.
// The transcript is <config>/projects/<cwd, mangled>/<session id>.jsonl; found by id, not by re-deriving the mangling.
async function findTranscript($: EngineInterface): Promise<string> {
  const known = (await load($)).transcript
  if (known !== '' && (await $.fs.exists(known).catch(() => false))) return known
  const config = (await $.env.get('CLAUDE_CONFIG_DIR')) ?? `${await $.env.get('HOME')}/.claude`
  const id = await $.session.id()
  const r = await $.process.run(['find', `${config}/projects`, '-maxdepth', '2', '-name', `${id}.jsonl`])
  const path = r.stdout.split('\n')[0]?.trim() ?? ''
  if (path !== '') await update($, stats, s => ({ ...EMPTY, ...s, transcript: path }))
  return path
}

const fail = ($: EngineInterface, scanError: string) => update($, stats, s => ({ ...EMPTY, ...s, scanError }))

async function rescan($: EngineInterface) {
  const transcript = await findTranscript($)
  if (transcript === '') return fail($, 'transcript not found')
  const r = await $.process.run(['awk', SCAN_AWK, transcript])
  if (r.exitCode !== 0) return fail($, `awk exited ${r.exitCode}: ${r.stderr.slice(0, 120)}`)
  const scan = parseScan(r.stdout)
  // A local estimate (no API call): the window /context measures against, and where auto-compact runs.
  const breakdown = (await $.session.usage({ breakdown: 'summary' }).catch(() => undefined))?.context.breakdown
  const maxTokens = breakdown?.rawMaxTokens
  const compactAt = breakdown?.isAutoCompactEnabled ? breakdown.autoCompactThreshold : undefined
  await update($, stats, s => ({ ...EMPTY, ...s, scan, maxTokens: maxTokens ?? s.maxTokens, compactAt, scanError: undefined }))
}
const refresh = ($: EngineInterface) => rescan($).catch(err => fail($, String(err).slice(0, 160)))

const openDetails = ($: EngineInterface) => $.ui.open({ id: PANE, title: 'Usage details' })

const clock = (ms: number) => {
  const d = new Date(ms)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'usage-band', description: 'Open the usage details pane (limits, context, tokens, turns, tests)' })
    // The cost so far is the baseline the next turn's own cost is measured from.
    const usd = (await $.session.usage().catch(() => undefined))?.cost?.usd
    await update($, stats, s => ({ ...EMPTY, ...s, costBase: usd ?? s.costBase }))
    await refresh($)
    return next(e)
  }).catch(($, e, next) => next(e))

  on('command.run', { command: 'usage-band' }, async $ => {
    await openDetails($)
    return { text: 'Usage details opened.' }
  })

  on('classic.UserPromptSubmit', async ($, e, next) => {
    // Only records where the transcript is: a scan here would hold up the prompt.
    const isNew = (await load($)).transcript !== e.transcript_path
    await update($, stats, s => (s.transcript === e.transcript_path ? s : { ...EMPTY, ...s, transcript: e.transcript_path }))
    if (isNew) await refresh($)
    return next(e)
  }).catch(($, e, next) => next(e))

  on('session.compact', async ($, e, next) => {
    const done = await next(e)
    if (e.agentId === undefined) await refresh($)
    return done
  }).catch(($, e, next) => next(e))

  // A test run sets the tests pill; a later code edit marks it stale.
  on('tool.call', async ($, e, next) => {
    if (e.tool === 'Bash' && isTestCommand(e.command)) {
      const ran = await next(e)
      if (ran.deny === undefined) {
        // Core sets `text` (the output as the model reads it); Bash's own record is the fallback.
        const rec = ran.result as { stdout?: string; stderr?: string } | undefined
        const tests = testOutcome(ran.isError === true, ran.text ?? `${rec?.stdout ?? ''}\n${rec?.stderr ?? ''}`)
        await update($, stats, s => ({ ...EMPTY, ...s, tests }))
      }
      return ran
    }
    if ((e.tool === 'Edit' || e.tool === 'Write') && isCode(e.file_path)) {
      const ran = await next(e)
      if (ran.deny === undefined && !ran.isError) {
        await update($, stats, s => (s.tests && s.tests.state !== 'stale' ? { ...s, tests: { state: 'stale' as const } } : s))
      }
      return ran
    }
    return next(e)
  }).catch(($, e, next) => next(e))

  on('turn.complete', async ($, e, next) => {
    const done = await next(e)
    if (e.agentId !== undefined) return done
    const usd = (await $.session.usage().catch(() => undefined))?.cost?.usd
    if (usd !== undefined) {
      await update($, stats, x => {
        const s = { ...EMPTY, ...x }
        // A total below the baseline means the ledger started over (/clear): the whole total is this turn's.
        const turn = s.costBase === undefined ? undefined : usd >= s.costBase ? usd - s.costBase : usd
        // A main turn always costs something: a zero is a turn already counted (a reload re-bases mid-turn).
        const isTurn = turn !== undefined && turn > 0
        return { ...s, costBase: usd, turnCosts: isTurn ? [...s.turnCosts, turn].slice(-10) : s.turnCosts }
      })
    }
    await refresh($)
    return done
  }).catch(($, e, next) => next(e))

  // A click on a card: open the details pane with that card's section first.
  on('ui.message', async ($, e, next) => {
    const open = (e.data as { open?: unknown } | null)?.open
    if (typeof open !== 'string') return next(e)
    await update($, stats, s => ({ ...EMPTY, ...s, focus: open }))
    await openDetails($)
    return {}
  }).catch(($, e, next) => next(e))

  // Never calls next: this band replaces whatever plugins beneath would draw here.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)

    const v = buildView(await load($), await $.session.usage(), await $.clock.now())
    const alt = v.pills.map(p => p.title).join('. ')
    const table = $.ui.resolve(e)
    const { Box, Text } = table

    type ClientEl = (p: { key: string; module: string; props: unknown; width: string; height?: string }) => never
    type SvgEl = (p: { source: string; width: number; height: number; alt: string }) => never

    // The terminal: chips in its monospace cells, laid out to the region's real width; they take clicks.
    if (e.surface === 'terminal' && 'Client' in table) {
      const { Client } = table as unknown as { Client: ClientEl }
      // Client props are plain JSON: the round trip drops unset fields and turns a missing cell into null.
      const props = JSON.parse(JSON.stringify({ layouts: layouts(v) }))
      return <Client key="band" module="./band.client.tsx" props={props} width="100%" />
    }
    // Every other surface draws the SVG. Its cells are not monospace (the desktop's are proportional),
    // so the chips would not line up there.
    if ('Svg' in table) {
      const { Svg } = table as unknown as { Svg: SvgEl }
      // The slot's pixel width is not given, only bodyColumns: measured at 94 columns = ~817px, ~8.7px each.
      // shortcut: a fixed factor; if the desktop changes its font, measure again (bodyColumns against the slot width).
      const slot = Math.floor(e.props.bodyColumns * 8.6)
      const all = layouts(v)
      const grids = all.find(g => bandWidth(...g) <= slot) ?? all[all.length - 1]!
      const svg = bandSvg(grids, slot)
      const drawing = <Svg source={svg.source} width={svg.width} height={svg.height} alt={alt} />
      if (!('Client' in table)) return drawing
      // An Svg takes no clicks, so invisible strips lie over it, one per row of cards, each as tall as
      // its share of the drawing (rows are evenly spaced, so the strip edges fall in the gaps).
      const { Client } = table as unknown as { Client: ClientEl }
      const tops = [...new Set(svg.boxes.map(b => b.y))].sort((a, b) => a - b)
      return (
        // No size on the wrapper: a Box measures in cells, the Svg in pixels; it wraps the drawing.
        <Box position="relative">
          {drawing}
          <Box position="absolute" top={0} left={0} width="100%" height="100%" flexDirection="column">
            {tops.map(top => {
              // A two-row card belongs to every strip it spans.
              const row = JSON.parse(JSON.stringify({ boxes: svg.boxes.filter(b => b.y <= top && top < b.y + b.h), width: svg.width }))
              return (
                <Box key={`row-${top}`} width="100%" height={`${100 / tops.length}%`}>
                  <Client key={`hit-${top}`} module="./hit.client.tsx" props={row} width="100%" height="100%" />
                </Box>
              )
            })}
          </Box>
        </Box>
      )
    }
    return (
      <Box flexDirection="row" gap={1} width={e.props.bodyColumns}>
        <Box flexGrow={1} flexShrink={1}>
          <Text dimColor wrap="truncate-end">
            {bandText(v.pills)}
          </Text>
        </Box>
      </Box>
    )
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const s = await load($)
    const usage = await $.session.usage({ breakdown: 'summary' }).catch(() => $.session.usage())
    const v = buildView(s, usage, await $.clock.now())
    const { Box, Text } = $.ui.resolve(e)
    const c = v.context

    const row = (label: string, value: string, sub = '') => (
      <Box key={`${label} ${value} ${sub}`} flexDirection="row" gap={1}>
        <Box width={16}>
          <Text dimColor>{label}</Text>
        </Box>
        <Text bold>{value}</Text>
        {sub !== '' && <Text dimColor>{sub}</Text>}
      </Box>
    )
    const head = (title: string) => (
      <Box key={`h-${title}`} marginTop={1}>
        <Text bold>{title}</Text>
      </Box>
    )

    const limitRows = v.limits.flatMap(l =>
      l === undefined
        ? []
        : [
            row(
              l.kind === 'five_hour' ? '5-hour limit' : '7-day limit',
              `${Math.round(l.pct)}% used`,
              [l.left !== undefined ? `resets in ${fmtSpan(l.left)}` : '', l.fullIn !== undefined ? `full in ~${fmtSpan(l.fullIn)} at this pace` : ''].filter(Boolean).join(' · '),
            ),
          ],
    )
    const categories = (usage.context.breakdown?.categories ?? []).filter(k => k.tokens > 0 && k.kind !== 'free')
    const t = s.scan.tokens
    const log = s.scan.log.slice(-10)
    // turnCosts covers only turns since the band loaded: they line up with the newest turns.
    const costOf = (i: number) => s.turnCosts[s.turnCosts.length - (log.length - i)]

    const sections: [string, RenderChildren[]][] = [
      ['limits', [head('Limits'), limitRows.length > 0 ? limitRows : <Text dimColor>No reading yet.</Text>]],
      [
        'context',
        [
          head('Context'),
          row('in use', `${fmtTokens(c.used)} / ${fmtTokens(c.max)}`, `${Math.round(c.pct)}%`),
          row('auto-compact', c.compactAt !== undefined ? `at ${fmtTokens(c.compactAt)}` : 'off', c.turnsLeft !== undefined ? `~${c.turnsLeft} turns away at ${fmtTokens(c.growth ?? 0)} a turn` : ''),
          row('compactions', String(s.scan.compactions)),
          ...categories.map(k => row(k.name, fmtTokens(k.tokens), c.max > 0 ? `${((k.tokens / c.max) * 100).toFixed(1)}%` : '')),
        ],
      ],
      [
        'tokens',
        [
          head('Tokens'),
          row('input', fmtTokens(t.input + t.cacheWrite), 'uncached + cache writes'),
          row('cache reads', fmtTokens(t.cacheRead), v.cache !== undefined ? `${Math.round(v.cache)}% of input` : ''),
          row('output', fmtTokens(t.output)),
        ],
      ],
      [
        'cost',
        [
          head('Cost'),
          row('session', usage.cost ? `$${usage.cost.usd.toFixed(2)}` : 'n/a', v.avg !== undefined ? `⌀ $${v.avg.toFixed(2)} a turn` : ''),
          v.last !== undefined && row('last turn', `$${v.last.toFixed(2)}`),
        ],
      ],
      [
        'turns',
        [
          head(`Turns (${s.scan.turns}, agent ${fmtSpan(s.scan.agentMs)})`),
          log.length === 0 && <Text dimColor>No turns yet.</Text>,
          ...log
            .map((turn, i) => {
              const cost = costOf(i)
              return row(clock(turn.startAt), fmtSpan(turn.ms), [`ctx ${fmtTokens(turn.ctx)}`, cost !== undefined ? `$${cost.toFixed(2)}` : ''].filter(Boolean).join(' · '))
            })
            .reverse(),
        ],
      ],
      [
        'tests',
        [
          head('Tests'),
          s.tests === undefined
            ? <Text dimColor>No test run seen yet.</Text>
            : row('last run', s.tests.state, [s.tests.passed !== undefined ? `${s.tests.passed} passed` : '', s.tests.failed !== undefined ? `${s.tests.failed} failed` : ''].filter(Boolean).join(' · ')),
        ],
      ],
    ]
    // The section a clicked card asked for comes first; the rest keep their order.
    const ordered = [...sections.filter(([k]) => k === s.focus), ...sections.filter(([k]) => k !== s.focus)]

    return (
      <Box flexDirection="column">
        {s.scanError && <Text color="warning">Could not read the transcript: {s.scanError}</Text>}
        {ordered.flatMap(([, parts]) => parts)}
      </Box>
    )
  }).catch(($, e, next) => next(e))
}
