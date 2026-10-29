---
name: qa-engineer
description: Use when asked to QA, bug-hunt, test, click through or probe a running app whose code is checked out here ("QA the sign-up flow", "find bugs in the running app", "probe the API", "check tenant isolation", "act as QA"), and the findings should be reproduced, traced to file:line and filed. Not for a site with no local code (dogfood), for writing automated tests, or for fixing a bug already known.
argument-hint: "[optional journey or surface to focus on]"
---

# qa-engineer

Hunts real bugs in the **running** product the way a QA engineer on the team would: through the same front door users use, signed in as the project's test accounts, each finding reproduced from a fresh load, traced to `file:line` and filed where the project wants it. It reports; it never fixes.

## When to use

- A local or test deployment of this repo's app is running, or can be started, and someone wants bugs found in it.
- Not for: a site whose code isn't here (use agent-browser's `dogfood`), writing or fixing tests, or a bug someone already reproduced (debug it instead).

## Steps

1. **Load the project's QA adapter.** Look for `docs/qa.md` (or what the instruction file names). It holds: how to start the app and find its web origin, the test roles and the sign-in recipe, the API spec to check responses against, the journeys, the "looks like a bug, isn't" list and where findings go. No adapter: draft one from the repo with `adapter.md`, show it, and wait for an OK before hunting.

2. **Write the run header** before the first action: branch, HEAD, dirty files, web origin, roles used, seed state. A finding without it can't be rerun. Read the origin from where the adapter says; never assume a default port, since another agent session may hold it. An argument narrows the run to one journey or surface; otherwise run the adapter's journeys in its order, because each leaves state the next one uses. `DRY_RUN=1` suppresses handoff writes: local evidence and a report only, useful for a first run on a new adapter.

3. **Go through the web origin only.** The browser and every probe talk to the origin users hit; API calls go through its proxy prefix (often `/api/*`). Never look up or call the API's own port: that skips the proxy, the cookie attributes and forwarded headers, which is where bugs hide.

4. **Sign in only with the helper**, one agent-browser session per role:
   `uv run <this skill>/scripts/qa_login.py --origin <origin> --recipe <adapter's recipe> --role <role> --session qa-<role>`
   It loads the cookies with their HttpOnly flag and prints no value. Never run `cookies get`, read `document.cookie` or storage into the transcript, show `network request <id>` without cutting its Cookie and Authorization headers, or type a password the adapter doesn't route through an env var. Use only the adapter's test accounts and number or email ranges; a real-looking number can reach a real person. When the sign-in screens themselves are under test, walk them in the browser (the adapter names where a dev code is read) instead of using the helper.

5. **Read the rules for the area first**: the area's agent card or README, product rules, anti-goals, and the adapter's "isn't a bug" list. A deliberate behavior is not a finding. Never enable a feature (flag, config) to manufacture a finding: deliberate gaps on the roadmap are not a bug list, and anti-goals are read before proposing any follow-up.

6. **Walk the journeys.** The adapter's, plus `web-probes.md` and `api-probes.md`. At each action: act, wait for it to settle, then check the screen, the network response (`agent-browser network requests`, including requests that hang) and the console (`agent-browser errors`, `console`); reload to check it persisted. Target elements by their accessibility names (snapshot refs), not DOM-text guesses, read page text rather than a screenshot for anything textual, and check the actual route after a redirect: it may be the redirect working.

7. **Prove it before recording it.** For each suspected bug:
   - Reproduce it from a fresh load. A dev overlay, a hot-reload warning, an automation timing artifact, a stale dev build or a service still starting is not a bug.
   - Capture evidence: a screenshot path, the request and response with secrets removed, the console line. Check that every cited artifact exists before referencing it. Screenshots may be resized: keep their real dimensions and never infer device coordinates from an assumed pixel ratio.
   - Compare the screen with the response, and name which failure it is: no data, not found, forbidden, unauthenticated, malformed input or server failure.
   - Trace it to `file:line` (producer, serializer, consumer; the line copied from `grep -n` output, never counted) and the rule it breaks, or write "cause unverified". Read the governing decision record (ADR, product rule) and say what correct behavior is and why; "make the surfaces consistent" is not a fix spec.
   - Blast radius: other callers and routes, and a working control that shows the difference. Two similar symptoms need independent evidence before you claim one cause.
   - Dedupe: the project's issues, handoffs (open and done), board items and briefs, and `git log -S '<term>'`. Fixed on the default branch already means a stale build, not a finding.

8. **Record each finding** in this shape:

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

9. **File and finish.** Send each finding to the adapter's sink (a handoff file, an issue through task-summary, or a report). With none named: in a git repo, one handoff per finding through plan-handoff (`.claude/handoffs/`): Environment and Repro fill Context, Expected/Actual and Root cause fill Problem, the expected behavior is the Contract (never a fix design) and the rerun commands are the Acceptance, each with checkable output, so the board can promote it or a queue run can pick it up. Outside a git repo, one dated report in `./tmp/`. Never edit code, never write a board or backlog, never "just fix it". Then clean up: remove only data you created (prefix it `qa-<yyyymmdd>-` and note ids as you go; never modify a pre-existing row, another tenant's data or anything under `.env`), close every browser session you opened (`agent-browser --session <s> close`), stop only processes you started, and run the adapter's secret check over the evidence folder and the filed handoffs. No cookie, Authorization header, password or real customer data may appear in any handoff, report or screenshot. End with: findings by severity, journeys covered and skipped, dedupe and filing status, cleanup status stated precisely (including anything left behind), the scan result, and "no fix was made".

## Common mistakes

| Mistake | Fix |
|---|---|
| Stuck at sign-in, hunting for the API port or asking the user for one | The adapter's recipe signs in through the origin's proxy; without an adapter, draft one (step 1). |
| Signing in with a made-up real-looking number or email | Only the adapter's fixture range. |
| "Maybe a toast I didn't capture" as a finding | Capture network and console, reproduce from a fresh load, or drop it. |
| Calling a deliberate behavior a bug (anti-enumeration, a redirect) | Step 5 before step 6. |
| Enabling a flag to make a gap show up | Deliberate gaps are not findings (step 5). |
| Fixing the bug found | File it; a fix is separate, planned work. |
| Leaving sessions or test data behind | Step 9's cleanup, every run. |
