# The project's QA adapter

One file per project, `docs/qa.md` by default, plus its sign-in recipe. The skill is generic; the adapter holds everything specific to this app. Draft it from the repo when it's missing, show it, and start hunting only after an OK.

## Template

```markdown
# QA adapter

## Start the app
<command, e.g. the launch config entry>; the web origin is <where to read it: a log line, a fixed port>.
Seed: <env flag or command that loads test data, or "none">.

## Roles
| Role | What it can do | Sign-in recipe role |
|---|---|---|
| <company-a> | <files requests in company A> | company-a |

Recipe: `docs/qa/signin.json`. Test accounts come only from <the fixture range, e.g. mobiles starting 09999>.
Secrets the recipe reads from env: <QA_ADMIN_PASSWORD, where it is set>, or none.

## Oracles
API spec: <path to the committed OpenAPI file, or none>. Product rules: <PRODUCT.md, acceptance flows>.
Required request headers: <e.g. X-Requested-With: app-web on every non-GET>.

## Journeys
1. <name>: <steps a user takes>; watch for <the high-value failure>.

## Isn't a bug
- <deliberate behavior that looks wrong, and the doc that says so>

## Findings go to
<a handoff file per finding at .claude/handoffs/YYYY-MM-DD-<slug>.md | an issue via task-summary | one report>.
Evidence folder: <an ignored path, e.g. web/tmp/qa-<date>/>.
Secret check: <a command that must print nothing, e.g. `grep -rliE 'cookie|authorization|password|bearer' <evidence folder>`, or the project's scanner if it takes a folder>.
```

## Sign-in recipe

JSON read by `scripts/qa_login.py`. `{name}` is a role var or an earlier extract; `{env:NAME}` reads an env var, so a password never sits in the file. Each step's `ok` lists the statuses that count as success (default 2xx); `extract` takes a regex's first group from the body. A step with an `extract` is asked again up to `retries` times (default 5, `retry_delay` 0.5 s) until the pattern matches, since a dev inbox can lag the step that sent the message.

```json
{
  "headers": { "X-Requested-With": "app-web" },
  "flows": {
    "sms": [
      { "method": "POST", "path": "/api/auth/start", "json": { "mobile": "{mobile}" }, "ok": [200, 202] },
      { "method": "GET", "path": "/api/dev/sent-sms?mobile={mobile}", "extract": { "code": "\\b(\\d{6})\\b" } },
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

A rate limit or resend wait often answers without the pending-sign-in cookie, so don't list it in `ok`; use a fresh fixture account (`--var mobile=...`) instead.

## Drafting it from the repo

- **Start:** the launch config (`.claude/launch.json`, `docker-compose`, `package.json` scripts, the README's run section).
- **Sign-in:** the auth module's routes and its dev or mock routes (a mock SMS inbox, an email catcher, a mock identity provider) and the test fixtures' accounts (`tests/e2e/fixtures*`). Walk the sign-in once through the browser to confirm the steps before writing the recipe.
- **Oracles:** a committed OpenAPI or schema file; the product spec and acceptance flows.
- **Journeys:** the product's acceptance path first, then each role's main jobs.
- **Isn't a bug:** "rules a compiler will not catch" sections, anti-goals, documented deliberate gaps.
- **Sink:** where the project keeps handoffs or issues; never its board or roadmap directly.
