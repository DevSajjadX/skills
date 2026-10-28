---
name: qa-engineer
description: Use when asked to QA, bug-hunt, test, click through or probe a running app whose code is checked out here ("QA the sign-up flow", "find bugs in the running app", "probe the API", "check tenant isolation", "act as QA"), and the findings should be reproduced, traced to file:line and filed. Not for a site with no local code (dogfood), for writing automated tests, or for fixing a bug already known.
---

# qa-engineer

Hunts real bugs in the **running** product the way a QA engineer on the team would: through the same front door users use, signed in as the project's test accounts, each finding reproduced from a fresh load, traced to `file:line` and filed where the project wants it. It reports; it never fixes.

## When to use

- A local or test deployment of this repo's app is running, or can be started, and someone wants bugs found in it.
- Not for: a site whose code isn't here (use agent-browser's `dogfood`), writing or fixing tests, or a bug someone already reproduced (debug it instead).

## Steps

1. **Load the project's QA adapter.** Look for `docs/qa.md` (or what the instruction file names). It holds: how to start the app and find its web origin, the test roles and the sign-in recipe, the API spec to check responses against, the journeys, the "looks like a bug, isn't" list and where findings go. No adapter: draft one from the repo with `adapter.md`, show it, and wait for an OK before hunting.

2. **Write the run header** before the first action: branch, HEAD, dirty files, web origin, roles used, seed state. A finding without it can't be rerun.

3. **Go through the web origin only.** The browser and every probe talk to the origin users hit; API calls go through its proxy prefix (often `/api/*`). Never look up or call the API's own port: that skips the proxy, the cookie attributes and forwarded headers, which is where bugs hide.

4. **Sign in only with the helper**, one agent-browser session per role:
   `uv run <this skill>/scripts/qa_login.py --origin <origin> --recipe <adapter's recipe> --role <role> --session qa-<role>`
   It loads the cookies with their HttpOnly flag and prints no value. Never run `cookies get`, read `document.cookie` or storage into the transcript, show `network request <id>` without cutting its Cookie and Authorization headers, or type a password the adapter doesn't route through an env var. Use only the adapter's test accounts and number or email ranges; a real-looking number can reach a real person.

5. **Read the rules for the area first**: the area's agent card or README, product rules, anti-goals, and the adapter's "isn't a bug" list. A deliberate behavior is not a finding.

6. **Walk the journeys.** The adapter's, plus `web-probes.md` and `api-probes.md`. At each action: act, wait for it to settle, then check the screen, the network response (`agent-browser network requests`) and the console (`agent-browser errors`, `console`); reload to check it persisted.

7. **Prove it before recording it.** For each suspected bug:
   - Reproduce it from a fresh load. A dev overlay, a hot-reload warning or a service still starting is not a bug.
   - Capture evidence: a screenshot path, the request and response with secrets removed, the console line.
   - Compare the screen with the response, and name which failure it is: no data, not found, forbidden, unauthenticated, malformed input or server failure.
   - Trace it to `file:line` (producer, serializer, consumer) and the rule it breaks, or write "cause unverified".
   - Blast radius: other callers and routes, and a working control that shows the difference.
   - Dedupe: the project's issues or handoffs (open and done) and `git log -S '<term>'`. Fixed on the default branch already means a stale build, not a finding.

8. **Record each finding** in this shape:

   ```text
   Title · Severity (blocker | major | minor)
   Environment: the run header, role
   Repro: route and numbered actions; result on repeat
   Expected / Actual: observable values
   Evidence: artifact paths; sanitized request/response or console line
   Root cause: file:line and mechanism, or "cause unverified"
   Fix: the target behavior and the owning module (not the patch)
   Blast radius: callers, routes, the working control
   Dedupe: what was searched, and the result
   ```

9. **File and finish.** Send each finding to the adapter's sink (a handoff file, an issue through task-summary, or a report); with none named, one dated report in the repo's ignored tmp folder. Never edit code, never write a board or backlog, never "just fix it". Then clean up: remove only data you created (prefix it `qa-<yyyymmdd>-` and note ids as you go), close every browser session you opened (`agent-browser --session <s> close`), stop only processes you started, and run the adapter's secret check over the evidence folder. End with: findings by severity, journeys covered and skipped, dedupe and filing status, cleanup status, the scan result, and "no fix was made".

## Common mistakes

| Mistake | Fix |
|---|---|
| Stuck at sign-in, hunting for the API port or asking the user for one | The adapter's recipe signs in through the origin's proxy; without an adapter, draft one (step 1). |
| Signing in with a made-up real-looking number or email | Only the adapter's fixture range. |
| "Maybe a toast I didn't capture" as a finding | Capture network and console, reproduce from a fresh load, or drop it. |
| Calling a deliberate behavior a bug (anti-enumeration, a redirect) | Step 5 before step 6. |
| Fixing the bug found | File it; a fix is separate, planned work. |
| Leaving sessions or test data behind | Step 9's cleanup, every run. |
