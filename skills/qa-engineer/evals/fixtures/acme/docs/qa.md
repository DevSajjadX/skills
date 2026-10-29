# QA adapter (fixture: the fictional Acme app)

## Start the app
`preview_start acme` (launch entry `acme`, runs `acme run --isolated`). Ports are random per run: read the web origin from the dashboard output.
Seed: `ACME_SEED_DEMO=true`, forwarded only when the shell already set it; creates two tenants (Company A, Company B) with one admin each, and one platform staff account.

## Read first
- `AGENTS.md`, cards `api/src/Modules/<M>/AGENTS.md` and `web/src/features/<f>/AGENTS.md`.
- `.pm/DO_NOT_DO.md`; deliberate gaps in `ARCHITECTURE.md`.
- Decision records in `docs/adr/` (ADR-3 origin and proxy, ADR-6 tenancy, ADR-10 seller side, ADR-11 errors).

## Roles
company-a (+15550000001), company-b (+15550000002), staff (+15550000003). Recipe `docs/qa/signin.json`.
Code read from `/api/dev/sent-sms` (mocked sender only).
Sign-in limits: defined in `api/src/Modules/Identity/SignInLimits.cs` (read it; the values are not copied here). A 429 on the send step means the earlier code is live.

## Oracles
Spec `api/openapi/acme.json`, regenerated with `pnpm gen:api`. Header `X-Requested-With: acme-web` on every non-GET.
Error shape: `application/problem+json` with non-null `detail` and `errorKey`, including framework 404 and 400. Catalogs `api/src/Modules/<M>/Text/messages.{ar,en}.json`. Languages: ar, en.
Tenant-owned resources: products, verification, audit entries.
Proxy `web/src/proxy.ts`: signed-out pages answer 302 to `/auth?next=...`, never 307.

## Isn't a bug
- The cross-company market view in `web/src/features/trade/AGENTS.md` is the product.
- A seller reading its own inquiries via `IgnoreQueryFilters` (ADR-10).
- Cross-tenant allow-list: `api/tests/IgnoreQueryFiltersTests.cs` `AllowList`.
- Category tree shared by all companies (platform-owned).
- Same code step for numbers with and without an account.

## Journeys
1. Auth and the active company. 2. Catalog. 3. Staff categories. 4. Audit log. 5. Locale and RTL. 6. Narrow viewport (375).

## Findings go to
`.claude/handoffs/` via plan-handoff. Evidence `web/tmp/qa-<date>/`. Secret check `<project scanner> dir . --redact`. Dry run `DRY_RUN=1`.
