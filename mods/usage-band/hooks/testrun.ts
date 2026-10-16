import type { Tests } from '../types'

// A Bash command that runs a test suite. shortcut: a list of the common runners; add one when a project's runner is missed.
const RUNNERS =
  /(^|[\s;&|(])(vitest|jest|pytest|mocha|rspec|phpunit|playwright test|cargo test|go test|bun test|deno test|swift test|xcodebuild test|maestro test|(pnpm|npm|yarn|bun)( run)? test(:\S+)?|uv run pytest|claude plugin test|mix test|dotnet test|gradle(w)? test|\.\/gradlew test|mvn test)(\s|$)/

export const isTestCommand = (command: string) => RUNNERS.test(command)

// Passed and failed counts from a runner's summary line, when it prints one.
export function testCounts(output: string): Pick<Tests, 'passed' | 'failed'> {
  const last = (re: RegExp) => {
    const all = [...output.matchAll(re)]
    const n = all.length > 0 ? Number(all[all.length - 1]![1]) : undefined
    return Number.isFinite(n) ? n : undefined
  }
  return { passed: last(/(\d+)\s+(?:tests?\s+)?pass(?:ed|ing)?\b/gi), failed: last(/(\d+)\s+(?:tests?\s+)?fail(?:ed|ures?|ing)?\b/gi) }
}

export function testOutcome(isError: boolean, output: string): Tests {
  const counts = testCounts(output)
  return { state: isError || (counts.failed ?? 0) > 0 ? 'fail' : 'pass', ...counts }
}

// A file whose change makes the last test run stale: source code, not docs or config.
export const isCode = (path: string) => /\.(m?[jt]sx?|cjs|py|rb|go|rs|swift|kt|java|cs|php|ex|exs|c|cc|cpp|h|hpp|vue|svelte)$/i.test(path)
