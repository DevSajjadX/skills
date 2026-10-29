# QA adapter

## Start the app
`make dev`; the web origin is the "web ready at ..." log line. Never assume a port.
Seed: `SEED_DEMO=1 make dev` loads two teams.

## Roles
| Role | What it can do | Sign-in recipe role |
|---|---|---|
| team-a | files tickets for team A | team-a |
| team-b | files tickets for team B | team-b |

Recipe: `docs/qa/signin.json`. Test accounts come only from `qa-*@example.test`.

## Oracles
API spec: `openapi.json`. Required request headers: `X-Requested-With: ticketdesk-web` on every non-GET.

## Journeys
1. Sign up, log out, sign in, switch team, log out.
2. File a ticket, list it, reload.
3. Public status board.

## Isn't a bug
- The public board shows other teams' tickets (ADR-0004).
- Same sign-in answer for unknown emails.

## Findings go to
One handoff per finding at `.claude/handoffs/YYYY-MM-DD-<slug>.md`.
Evidence folder: `tmp/qa-<date>/`.
Secret check: `grep -rliE 'cookie|authorization|password|bearer' tmp/qa-<date> .claude/handoffs` must print nothing.
