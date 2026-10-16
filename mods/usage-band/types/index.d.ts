export type Tokens = { input: number; output: number; cacheRead: number; cacheWrite: number }
// log: the last turns, oldest first, ctx the context the turn's last reply was answered over;
// sinceCompact: turns since the last compaction (all of them when there was none).
export type TurnLog = { startAt: number; ms: number; ctx: number }
export type Scan = { agentMs: number; turns: number; tokens: Tokens; compactions: number; log: TurnLog[]; sinceCompact: number }
export type Tests = { state: 'pass' | 'fail' | 'stale'; passed?: number; failed?: number }
// maxTokens: the window /context measures against (the compaction window, which may be under the model's).
// scanError: why the last transcript read failed, shown on the band instead of silent zeros.
// turnCosts: the last turns' cost, newest last, each the session cost's rise over that turn; costBase: the total
// when the last turn ended. The transcript records no prices, so these are kept as the session goes.
export type Stats = {
  transcript: string
  scan: Scan
  maxTokens?: number
  compactAt?: number
  scanError?: string
  turnCosts: number[]
  costBase?: number
  // The last test run's outcome, 'stale' once code changed after it; absent before any run.
  tests?: Tests
  // The pane section a clicked card asked for; it opens when clicked.
  focus?: string
  // The pane's sections drawn open; the rest show their header and summary only.
  open?: string[]
}

declare module 'claude-code' {
  interface PluginState {
    'usage-band': { stats: Stats }
  }
}
