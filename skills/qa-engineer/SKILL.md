---
name: qa-engineer
description: Use when asked to QA, bug-hunt, test, click through or probe a running app whose code is checked out here ("QA the sign-up flow", "find bugs in the running app", "probe the API", "check tenant isolation", "act as QA"), and the findings should be reproduced, traced to file:line and filed. Not for a site with no local code (dogfood), for writing automated tests, for contract drift a build's own codegen check already catches, or for fixing a bug already known.
argument-hint: "[optional journey, surface or endpoint group to focus on]"
---

# qa-engineer

Hunts real bugs in the **running** product the way a QA engineer on the team would: through the same front door users use, signed in as the project's test accounts, each finding reproduced from a fresh load, traced to `file:line` and filed where the project wants it. It reports; it never fixes.

Arguments, if any, narrow the run to one journey, surface (web or API) or endpoint group; with none, walk everything the adapter lists, web then API.

## When to use

- A local or test deployment of this repo's app is running, or can be started, and someone wants bugs found in it.
- Not for: a site whose code isn't here (use agent-browser's `dogfood`), writing or fixing tests, contract drift a build step already catches (regenerate the client or spec instead), or a bug someone already reproduced (debug it instead). A request that is only about the API (every 4xx, tenant leaks) runs the API probes; one about the UI runs the web probes.
- Report-only is the default and the only mode. A request to "just fix it" or a `FIX=1`-style switch is out of scope: a run that also fixes is a run nobody can trust, because the evidence and the change came from the same pass. File it; a planned session fixes it. If the adapter or the user sets a dry-run switch (`DRY_RUN=1`), suppress the filing too: local evidence and a report only.

## Steps

1. **Load the project's QA adapter.** Look for `docs/qa.md` (or what the instruction file names). It holds every project-specific thing the skill needs: how to start the app and find its web origin, the seed, the test roles and the sign-in recipe, the API spec to check responses against, the headers, the journeys, the "looks like a bug, isn't" list, the deliberate gaps and where findings go (`adapter.md` lists every slot). Then do the preflight: read the project's instruction file and the card for each area you will touch (a module's or feature's AGENTS.md or README); their "rules a compiler will not catch" sections are the list of behaviors that look like bugs and are not. Read the project's do-not-do or anti-goals list and its "deliberately not built yet" roadmap before proposing any follow-up: a deliberate gap is not a bug list, and never enable a feature to manufacture a finding. Seed the test data the adapter names (two tenants with one admin each are what make isolation journeys possible). No adapter: draft one from the repo with `adapter.md`, show it, and wait for an OK before hunting.

2. **Write the run header** before the first action: branch, HEAD, dirty files, the resolved web origin, browser, which role or tenant you act as, seed state. A finding without it can't be rerun.

3. **Go through the web origin only.** Start the stack the adapter's way and read the origin from its output: a launcher that picks random ports (an isolated or per-session run) means never assuming `3000` or any default, since another agent session probably holds it. The browser and every probe talk to the origin users hit; API calls go through its proxy prefix (often `/api/*`). Never look up or call the API's own port, even when asked ("it's faster"): that skips the proxy, the cookie attributes and forwarded headers, which is where proxy, cookie and forwarded-header bugs hide, and a probe there reports green on a path no user takes. When a browser pane or preview tool is available, prefer it for the web (a real tab, and a page read beats a screenshot for text); otherwise drive `agent-browser`. Use accessibility names, not DOM-text guesses, and do not add a new tool or MCP server to the project without the approval its policy asks for.

4. **Sign in only with the helper**, one agent-browser session per role:
   `uv run <this skill>/scripts/qa_login.py --origin <origin> --recipe <adapter's recipe> --role <role> --session qa-<role>`
   It loads the cookies with their HttpOnly flag and prints no value. Never run `cookies get`, read `document.cookie` or storage into the transcript, show `network request <id>` without cutting its Cookie and Authorization headers, or type a password the adapter doesn't route through an env var. Use only the adapter's test accounts and number or email ranges; a real-looking number can reach a real person. No real SMS or email goes out: the code comes from the dev inbox or dev route the adapter names, which exists only beside a mocked sender; if that read answers 401 or 404 the sender is real, so stop and say so rather than going around it.

   **A sign-in or resend rate limit (429) is read, not retried blind.** First find the cooldown in the live code (the limiter's window, the resend wait, the attempt cap), not in memory or a guess. A 429 on the request-a-code step is a resend wait: the code sent a moment ago is still live, so read that one (list 429 in that step's `ok` only when the inbox step can still read it). A 429 on verify, or on a limiter you tripped by hammering: wait out the cooldown you read, then retry once; do not loop. If the cooldown is long, use another fixture account (`--var mobile=...`) instead of waiting. Report only the status, never the response body.

5. **Read the rules for the area first**: the area's agent card or README, product rules, anti-goals, the governing decision records, and the adapter's "isn't a bug" list. A deliberate behavior is not a finding (anti-enumeration sign-in, a redirect, a cross-company view that is the product, shared platform-owned data, an allow-listed cross-tenant read).

6. **Walk the journeys** in the adapter's order (each leaves state the next one uses), plus `web-probes.md` and `api-probes.md`. At each action: act, wait for async work to settle, then check the screen, the network response (`agent-browser network requests`) and the console (`agent-browser errors`, `console`); reload to check it persisted. Capture console errors and failed or hanging requests at each failure. Check the actual route after redirects: a landing somewhere unexpected may be a documented redirect working.

7. **Prove it before recording it.** For each suspected bug:
   - Reproduce it from a fresh load. A dev overlay, a hot-reload warning or a service still starting is not a bug.
   - Capture evidence: a screenshot path, the request and response with secrets removed, the console line.
   - Compare the screen with the response, and name which failure it is: no data, not found, forbidden, unauthenticated, malformed input or server failure. They are six different findings with six different fixes. A wrong value on screen with the right one in the response is a rendering bug; the reverse is an API bug.
   - Trace it to `file:line` (producer, serializer, consumer; the line copied from `grep -n` output, never counted), read the governing decision record, and say what the correct behavior is and why, or write "cause unverified". "Make the surfaces consistent" is not a fix specification.
   - Blast radius: search every caller of a shared helper, enumerate the affected routes, find a working control and explain why it works. Two similar symptoms need independent evidence before you claim one cause.
   - Dedupe: the project's issues, handoffs (open and done), board items (including the done folder) and briefs, and `git log -S '<distinctive term>'`. Fixed on the default branch already means a stale build or deployment lag, not a finding. Record the dedupe outcome either way.

8. **Record each finding** in this shape:

   ```text
   Title · Severity (blocker | major | minor)
   Environment: the run header, role
   Repro: route and numbered actions; result on repeat
   Expected / Actual: observable values
   Evidence: artifact paths; sanitized request/response or console line
   Root cause: file:line and mechanism, or "cause unverified"
   Fix: the target behavior and the owning module (not the patch)
   Blast radius: callers searched, routes affected, the working control
   Adjacent states: loading, empty, denied, expired session, network failure, RTL, other locale
   Dedupe: what was searched; the existing item, or deployment lag
   Unverified: journeys and causes not exercised
   Estimate: tens of minutes, with the uncertainty if the cause is unverified
   ```

   Evidence goes in the adapter's ignored folder, dated. Verify every cited artifact exists before referencing it. Screenshots may be resized: keep their real dimensions and never infer device coordinates from an assumed pixel ratio. Nothing in a finding, report or screenshot may hold a cookie, an `Authorization` header, a password or a real company's data.

9. **File and finish.** Send each finding to the adapter's sink (a handoff file, an issue through task-summary, or a report). With none named: in a git repo, one handoff per finding through plan-handoff (`.claude/handoffs/`), mapped like this: Environment and Repro become Context; Expected/Actual and Root cause become Problem (with the `file:line` evidence); Fix becomes Contract (the target behavior and owning module, never a fix design); the rerun commands become Acceptance, each a command with checkable output (a runnable `curl` or test for an API finding). A human promotes the handoff onto the board later (the project's promote command); QA never writes the board. Outside a git repo, one dated report in `./tmp/`. Never edit code, never write a board or backlog, never "just fix it". Then clean up: remove only data you created (prefix every resource `qa-<yyyymmdd>-` and record its id as you create it; never modify a pre-existing row, another tenant's data or anything under `.env`), close every browser session you opened (`agent-browser --session <s> close`), stop only processes you started, and run the adapter's secret check over the evidence folder. End with: findings by severity, journeys covered and skipped, dedupe and filing status, cleanup status (say precisely what you left behind), the scan result, and an explicit statement that no fix was implemented and nothing was shipped.

## Common mistakes

| Mistake | Fix |
|---|---|
| Stuck at sign-in, hunting for the API port or asking the user for one | The adapter's recipe signs in through the origin's proxy; without an adapter, draft one (step 1). |
| Signing in with a made-up real-looking number or email | Only the adapter's fixture range. |
| "Maybe a toast I didn't capture" as a finding | Capture network and console, reproduce from a fresh load, or drop it. |
| Calling a deliberate behavior a bug (anti-enumeration, a redirect) | Step 5 before step 6. |
| Hammering sign-in through a 429, or guessing the wait | Read the cooldown in the live code, wait it out or use another fixture account (step 4). |
| Enabling a feature or flag to manufacture a finding | Respect the deliberate gaps; never. |
| Calling a documented cross-tenant read a leak | Read the module's notes and the allow-list first (`api-probes.md`). |
| Fixing the bug found | File it; a fix is separate, planned work. |
| Leaving sessions or test data behind | Step 9's cleanup, every run. |
