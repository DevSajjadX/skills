# Recording and filing a finding

## The record

```text
Title · Severity (blocker | major | minor)
Environment: the run header (web origin, branch, HEAD, browser, role or tenant, seed state)
Repro: exact route and numbered actions; result on repeat
Expected / Actual: observable values and states
Evidence: verified artifact paths; sanitized request/response or console line
Root cause: file:line and mechanism, or "cause unverified"
Fix: the target behavior and the owning module (not the patch)
Blast radius: callers searched, routes affected, the working control
Adjacent states: loading, empty, denied, expired session, network failure, right-to-left, other locale
Dedupe: what was searched, and the result (an existing item, or deployment lag)
Unverified: journeys and causes not exercised
Estimate: tens of minutes, with the uncertainty if the cause is unverified
```

Evidence goes in the adapter's ignored folder, dated. Verify every cited artifact exists before referencing it. Screenshots may be resized: keep their real dimensions and never infer device coordinates from an assumed pixel ratio. Nothing in a finding, report or screenshot may hold a cookie, an `Authorization` header, a password or a real company's data.

## Filing

Send each finding to the adapter's sink (a handoff file, an issue through task-summary, or a report). With none named: in a git repo, one handoff per finding through plan-handoff (`.claude/handoffs/`), mapped like this: Environment and Repro become Context; Expected/Actual and Root cause become Problem (with the `file:line` evidence); Fix becomes Contract (the target behavior and owning module, never a fix design); the rerun commands become Acceptance, each a command with checkable output (a runnable `curl` or test for an API finding). A human promotes the handoff onto the board later (the project's promote command), so the board can promote it or a queue run can pick it up; QA never writes the board. Outside a git repo, one dated report in `./tmp/`. In a dry run nothing is filed: local evidence and a report only.

## Cleanup

- Remove only data you created: prefix it `qa-<yyyymmdd>-` and note ids as you go. Never modify a pre-existing row, another tenant's data or anything under `.env`.
- Close every browser session you opened (`agent-browser --session <s> close`).
- Delete any `--jar` cookie file.
- Stop only processes you started.
- Run the adapter's secret check over the evidence folder and every handoff or report the run wrote. No cookie, Authorization header, password or real customer data may appear in any handoff, report or screenshot.
- Say precisely what you left behind.
