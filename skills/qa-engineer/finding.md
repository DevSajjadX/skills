# Recording and filing a finding

## The record

```text
   Title · Severity (blocker | major | minor)
   Environment: the run header, browser, role
   Repro: route and numbered actions; result on repeat
   Expected / Actual: observable values
   Evidence: artifact paths; sanitized request/response or console line
   Root cause: file:line and mechanism, or "cause unverified"
   Fix: the target behavior and the owning module (not the patch)
   Blast radius: callers, routes, the working control
   Adjacent states: loading, empty, denied, expired session, network failure, right-to-left, other locale
   Dedupe: what was searched, and the result
   Unverified: journeys and causes not exercised
   Estimate: rough effort, with the uncertainty if the cause is unverified
   ```

## Filing

Send each finding to the adapter's sink (a handoff file, an issue through task-summary, or a report). With none named: in a git repo, one handoff per finding through plan-handoff (`.claude/handoffs/`): Environment and Repro fill Context, Expected/Actual and Root cause fill Problem, the expected behavior is the Contract (never a fix design) and the rerun commands are the Acceptance, each with checkable output, so the board can promote it or a queue run can pick it up. Outside a git repo, one dated report in `./tmp/`. In a dry run nothing is filed.

## Cleanup

- Remove only data you created: prefix it `qa-<yyyymmdd>-` and note ids as you go. Never modify a pre-existing row, another tenant's data or anything under `.env`.
- Close every browser session you opened (`agent-browser --session <s> close`).
- Stop only processes you started.
- Run the adapter's secret check over the evidence folder and the filed handoffs. No cookie, Authorization header, password or real customer data may appear in any handoff, report or screenshot.
