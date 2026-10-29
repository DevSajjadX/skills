# The project's QA adapter

One file per project, `docs/qa.md` by default, plus its sign-in recipe. The skill is generic; the adapter holds everything specific to this app: every name, route, flag, document and journey the skill would otherwise have to hard-code. Draft it from the repo when it's missing, show it, and start hunting only after an OK.

## Template

```markdown
# QA adapter

## Start the app
<command, e.g. the launch config entry>; the web origin is <where to read it: a log line, a dashboard, a fixed port>.
Ports: <fixed, or "random per run (isolated mode): read the origin from the output, never assume a default; another agent session may hold the usual ports">.
Seed: <env flag or command that loads test data, how it must be passed to the launcher (e.g. only forwarded when the shell already set it), what it creates (e.g. two tenants with one admin each), and whether it is idempotent>, or "none".
Stop only what you started: <how>.

## Read first (preflight)
- Instruction file: <AGENTS.md / CLAUDE.md / README>; per-area cards: <path pattern, e.g. api/src/Modules/<M>/AGENTS.md, web/src/features/<f>/AGENTS.md>. Their "rules a compiler will not catch" sections list what looks like a bug and is not.
- Do-not-do / anti-goals: <path>. Deliberate gaps ("what we deliberately don't have yet"): <path>. Never enable a feature to manufacture a finding.
- Decision records: <folder, e.g. docs/adr/>, with the ones that govern origin, proxy, tenancy, locale, errors, paging.

## Roles
| Role | What it can do | Sign-in recipe role |
|---|---|---|
| <company-a> | <files requests in company A> | company-a |
| <company-b> | <a second tenant: makes isolation journeys possible> | company-b |
| <staff> | <platform staff, if any> | staff |

Recipe: `docs/qa/signin.json`. Test accounts come only from <the fixture range, e.g. mobiles starting 09999, the seed's constants file>; they are not secret and have no real person behind them.
How the code is read: <dev inbox or dev route, the route itself, and "exists only beside a mocked sender">. A 401 or 404 there means a real sender: stop.
Secrets the recipe reads from env: <QA_ADMIN_PASSWORD, where it is set>, or none.
Sign-in rate limits: <the limiter's window, resend wait and attempt cap, with the file:line that defines them; whether a 429 on the request step means "the code sent earlier is still live">. Recipe steps that may answer 429 and still be read: <which, listed in that step's `ok`>.
Anonymous-looking sign-in: <anti-enumeration rule: a number with and without an account get the same step>.

## Oracles
API spec: <path to the committed OpenAPI file, or none>; how it is generated and the command that would regenerate it (a spec that disagrees with the code usually means the regeneration was skipped; the project's gate may already catch it).
Product rules: <PRODUCT.md, acceptance flows>.
Required request headers: <e.g. X-Requested-With: app-web on every non-GET; a 4xx without it is the guard working, not a finding>.
Proxy: <file that forwards /api/*, the redirect status it must use for signed-out pages (302 or 303, never 307 or 308, which replay a form post), the landing URL pattern such as /auth?next=...>.
Error shape: <e.g. application/problem+json with a non-null detail and a stable error key, including framework-raised errors (unknown route, unparseable body); where the message catalogs live per language; which test should catch a key missing in one language>.
Paging: <keyset or offset, cursor documentation, ordering collation the client must not re-sort>.
Tenant-owned resources: <the resources one tenant must never see of another's, e.g. products, verification, audit entries>.
Active context: <how a user switches account, workspace or company, and the rule that a save lands in the context its tab shows (decision record)>.

## Isn't a bug
- <deliberate behavior that looks wrong, and the doc that says so>
- Shared on purpose across tenants: <e.g. a platform-owned category tree>; allow-listed cross-tenant reads: <the allow-list file or test, each with its reason>; a cross-company view that is the product: <where documented>.
- Actor-less audit entries: <which events are written with no actor, and why>.
- Dev-only anonymous routes: <which, and the mocked provider they sit beside>.

## Journeys
Run in this order; each leaves state the next one uses. The argument may narrow to one.
1. <name>: <steps a user takes>; watch for <the high-value failure>; not a bug: <what looks wrong and is not>.
(Typical slots: auth and the active context; the main list-and-create flow with validation and mixed-script text; a privileged area as staff and as a plain member; the audit log and its action labels, timestamps and numerals; locale and direction (cookie name, whether the address ever changes, soft switch keeps a half-filled form); a narrow viewport (<width, default 375>) re-run of <journeys>.)

## API journeys
<Every 4xx carries the error shape and key; tenant isolation between the two roles (own rows, verification, audit); paging stability under writes with cursors from another endpoint, mangled, and another tenant's; the anonymous surface against the declared allow-list (<where declared>); rate limiting and the forwarded-header trust (<where the trust is documented, and what is expected locally vs staging, e.g. the deploy checklist step>).>

## Tools
Web driver: <browser pane or preview tool if the host has one, else agent-browser>. New tools or MCP servers need <the approval path>; do not add one.

## Findings go to
<a handoff file per finding at .claude/handoffs/YYYY-MM-DD-<slug>.md (Environment and Repro to Context, Expected/Actual and Root cause to Problem, Fix to Contract, rerun commands to Acceptance) | an issue via task-summary | one report>.
Never the board or roadmap directly: <the project's promote command is the only writer>.
Dedupe sources: <issues, handoffs open and done, board folders including done, briefs, `git log -S`>.
Evidence folder: <an ignored path, e.g. web/tmp/qa-<date>/>.
Dry-run switch: <e.g. DRY_RUN=1 suppresses the filing: evidence and a report only>, or none.
Secret check: <the project's secret scanner run over the checkout (it must cover the evidence folder and the handoffs or reports the run wrote), exit 0>. Avoid a keyword grep: it flags every finding that is about cookies.
Cleanup: <resource prefix qa-<yyyymmdd>-, and anything that must never be touched: pre-existing rows, other tenants, .env>.
```

## Sign-in recipe

JSON read by `scripts/qa_login.py`. `{name}` is a role var or an earlier extract; `{env:NAME}` reads an env var, so a password never sits in the file. Each step's `ok` lists the statuses that count as success (default 2xx); `extract` takes a regex's first group from the body. A step with an `extract` is asked again up to `retries` times (default 5, `retry_delay` 0.5 s) while the status is ok and the pattern has not matched, since a dev inbox can lag the step that sent the message. `"dev_read": true` on the inbox step turns a 401 or 404 into exit 5: the sender looks real, stop.

```json
{
  "headers": { "X-Requested-With": "app-web" },
  "flows": {
    "sms": [
      { "method": "POST", "path": "/api/auth/start", "json": { "mobile": "{mobile}" }, "ok": [200, 202, 429] },
      { "method": "GET", "path": "/api/dev/sent-sms?mobile={mobile}", "dev_read": true, "extract": { "code": "\\b(\\d{6})\\b" } },
      { "method": "POST", "path": "/api/auth/verify", "json": { "code": "{code}" } }
    ],
    "password": [
      { "method": "POST", "path": "/api/auth/admin", "json": { "user": "{user}", "password": "{env:QA_ADMIN_PASSWORD}" } }
    ]
  },
  "roles": {
    "company-a": { "flow": "sms", "vars": { "mobile": "09999000001" } },
    "admin": { "flow": "password", "vars": { "user": "qa-admin" } }
  }
}
```

### Rate limits and 429

Read the limiter's cooldown from the live code and write it in the adapter. Two cases:

- **429 on the step that sends the code** is a resend wait: the code sent a moment ago is still in the dev inbox. List 429 in that step's `ok` (as above) so the next step reads the live code. This works only where the inbox step can still read it.
- **429 anywhere else** (verify, a limiter you tripped): don't list it in `ok`. Wait out the cooldown the adapter records, retry once, or use a fresh fixture account (`--var mobile=...`). Never loop.

A sign-in that fails prints the status only, never a body.

## Drafting it from the repo

- **Start:** the launch config (`.claude/launch.json`, `docker-compose`, `package.json` scripts, the README's run section); whether it randomizes ports.
- **Sign-in:** the auth module's routes and its dev or mock routes (a mock SMS inbox, an email catcher, a mock identity provider), the limiter's settings, and the test fixtures' accounts (`tests/e2e/fixtures*`, the seed's constants). Walk the sign-in once through the browser to confirm the steps before writing the recipe.
- **Oracles:** a committed OpenAPI or schema file; the proxy file and its redirect status; the error-shape decision record; the product spec and acceptance flows.
- **Journeys:** the product's acceptance path first, then each role's main jobs; staff-only areas; the audit log; locale and direction; narrow viewport.
- **Isn't a bug:** "rules a compiler will not catch" sections, anti-goals, documented deliberate gaps, the cross-tenant allow-list, dev-only anonymous routes.
- **Sink:** where the project keeps handoffs or issues; never its board or roadmap directly.
