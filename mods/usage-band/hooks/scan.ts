import type { Scan } from '../types'

// One pass over the session's transcript (JSONL, often past the 4 MiB $.fs.read limit): every turn's
// first and last timestamp and the context its last reply was answered over (T), each background task from its launching tool call
// to the notification that it finished (W: work between turns), each compaction (B), the token usage of each assistant message once (streaming repeats a
// message over several lines), and the compaction boundaries. Quotes inside message text are
// escaped in JSONL, so an unescaped key match is structural; the top-level timestamp is a line's last.
// shortcut: a background task counts only once its notification lands (a running one, or one with no tool-use-id such as a
// Monitor event, adds nothing yet); track open launches from their "running in background" results if a live tick matters.
// shortcut: subagent transcripts live in their own files and are not counted; read subagents/*.jsonl too if their tokens matter.
export const SCAN_AWK = `function num(s, k) { if (match(s, "\\"" k "\\":[0-9]+")) return substr(s, RSTART + length(k) + 3, RLENGTH - length(k) - 3) + 0; return 0 }
{
  pre = substr($0, 1, 400)
  if (index(pre, "\\"isSidechain\\":true")) next
  if (index($0, "\\"subtype\\":\\"compact_boundary\\"")) { c++; print "B" }
  s = $0; ts = ""; tail = ""
  while (match(s, /"timestamp":"[^"]*"/)) { ts = substr(s, RSTART + 13, RLENGTH - 14); tail = substr(s, RSTART + RLENGTH); s = tail }
  if (ts == "") next
  if (index(tail, "\\"promptSource\\":")) {
    if (start != "") print "T", start, end, tc + 0
    if (index($0, "<task-notification>") && match($0, /<tool-use-id>toolu_[A-Za-z0-9]+/)) { k = substr($0, RSTART + 13, RLENGTH - 13); if (k in launch) print "W", launch[k], ts }
    start = ts; end = ts; tc = 0; next
  }
  if (index(pre, "\\"role\\":\\"assistant\\"")) {
    end = ts
    if (match($0, /"type":"tool_use","id":"toolu_[A-Za-z0-9]+"/)) launch[substr($0, RSTART + 24, RLENGTH - 25)] = ts
    id = NR
    if (match(pre, /"id":"msg_[A-Za-z0-9]+"/)) id = substr(pre, RSTART + 6, RLENGTH - 7)
    u = $0
    while (match(u, /"usage":\\{/)) u = substr(u, RSTART + RLENGTH)
    ui[id] = num(u, "input_tokens"); uo[id] = num(u, "output_tokens"); ur[id] = num(u, "cache_read_input_tokens"); uw[id] = num(u, "cache_creation_input_tokens")
    tc = ui[id] + ur[id] + uw[id]
  } else if (index(pre, "\\"role\\":\\"user\\"")) end = ts
}
END {
  if (start != "") print "T", start, end, tc + 0
  for (k in ui) { i += ui[k]; o += uo[k]; r += ur[k]; w += uw[k] }
  print "U", i + 0, o + 0, r + 0, w + 0
  print "C", c + 0
}`

export const NO_SCAN: Scan = { agentMs: 0, turns: 0, tokens: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 }, compactions: 0, log: [], sinceCompact: 0 }
const LOG = 20

// Agent time is the union of turns and background tasks: a turn that hands work to a background task ends
// while that work runs, and turns or tasks that overlap count once.
function unionMs(spans: [number, number][]): number {
  let ms = 0
  let reach = -Infinity
  for (const [a, b] of [...spans].sort((x, y) => x[0] - y[0])) {
    if (b > reach) ms += b - Math.max(a, reach)
    reach = Math.max(reach, b)
  }
  return ms
}

export function parseScan(stdout: string): Scan {
  const scan: Scan = { ...NO_SCAN, tokens: { ...NO_SCAN.tokens }, log: [] }
  const spans: [number, number][] = []
  for (const line of stdout.split('\n')) {
    const [tag, a = '', b = '', c = '', d = ''] = line.trim().split(' ')
    if (tag === 'B') {
      scan.sinceCompact = 0
    } else if (tag === 'T') {
      const ms = Date.parse(b) - Date.parse(a)
      const turnMs = Number.isFinite(ms) && ms > 0 ? ms : 0
      scan.turns += 1
      scan.sinceCompact += 1
      if (turnMs > 0) spans.push([Date.parse(a), Date.parse(b)])
      scan.log = [...scan.log, { startAt: Date.parse(a) || 0, ms: turnMs, ctx: Number(c) || 0 }].slice(-LOG)
    } else if (tag === 'W') {
      const [from, to] = [Date.parse(a), Date.parse(b)]
      if (to > from) spans.push([from, to])
    } else if (tag === 'U') {
      scan.tokens = { input: Number(a) || 0, output: Number(b) || 0, cacheRead: Number(c) || 0, cacheWrite: Number(d) || 0 }
    } else if (tag === 'C') {
      scan.compactions = Number(a) || 0
    }
  }
  scan.agentMs = unionMs(spans)
  return scan
}
