# skills

Agent skills for readable, ADHD-friendly PR and work-item pages, session wrap-up, logo design, text humanizing and purchase research — installable with the [skills CLI](https://github.com/vercel-labs/skills) into Claude Code, Cursor, Codex, OpenCode, and 70+ other agents.

## Install

```bash
# all skills, interactive
npx skills add Esi-Abolfazl/skills

# one skill, global, Claude Code only, no prompts
npx skills add Esi-Abolfazl/skills --skill pr-summary -g -a claude-code -y

# needed by wrap's review step
npx skills add vanenshi/skills --skill reviewing-changes -g -y
```

## Skills

| Skill | What it does |
|---|---|
| [brand-identity](skills/brand-identity/SKILL.md) | Designs logos end to end — new marks, refreshes, and production on an approved mark (favicon/app-icon sets, colorways): brief, positioning sentence, competitor/cliché scan, 10+ ideas into 3+ concepts from 2+ directions, one recommended and built into lockups and full-color/mono/reverse colorways. Masters are outlined SVG paths, legibility is proven on inspected 16/32/48 px renders, and everything ships on one presentation board with a spec. A refresh inventories what customers already recognize before redesigning. Logo only — not color/type/imagery systems or full brand boards. |
| [pr-summary](skills/pr-summary/SKILL.md) | Turns a PR — or a work item's PR bundle — from Azure DevOps or GitHub into one HTML page: why the change exists, how it works, what changed. Whole picture on the first screen, never a wall of diff rows. |
| [wrap](skills/wrap/SKILL.md) | Closes a session: sweeps leftovers, reviews the diff with the `reviewing-changes` skill and applies its findings, retires debt, syncs docs, runs the repo's gates, regroups unpushed commits by concern, drafts the commit message. Bare `/wrap` regroups unpushed commits if they look messy and only drafts the commit message; `c` commits, `s` regroups, `m [branch]` regroups then merges (default: the default branch), `--p` pushes, `--f` regroups the whole branch and pushes with `--force-with-lease`. Full table: the skill's [help block](skills/wrap/SKILL.md#9-report). Ships a commit gate hook (see below); expects `reviewing-changes` from [vanenshi/skills](https://github.com/vanenshi/skills) (see Install). |
| [task-summary](skills/task-summary/SKILL.md) | Pulls a work item or issue into a readable page: description as written (sanitized), comments in order, screenshots embedded. Also creates and edits items from session findings; descriptions can be bilingual (full text + short summary). |
| [text-humanizer](skills/text-humanizer/SKILL.md) | Rewrites a draft (or drafts a reply from scratch) so it reads as a specific person wrote it, or only checks a text for AI tells and reports. Voice comes from a project voice profile, then your personal profile when your standing instructions name one, then samples of your writing, then one question; scans against an AI-tells checklist and re-scans its own output. Never fakes humanity with typos or invents specifics. |
| [product-purchase-research](skills/product-purchase-research/SKILL.md) | Shopping research tuned to one buyer: fit to stated use over top specs, dealbreakers as hard filters, only your markets — every one checked — and every option priced as landed USD at a live rate with its source. Your region, markets, stores and dealbreakers live in a private profile on your machine (`${XDG_CONFIG_HOME:-~/.config}/product-purchase-research/profile.md`, untouched by skill updates): the first run asks and writes it, every run shows it, and you change it anytime by editing the file or just asking. |

## Connecting

Nothing to set up front. Paste a link — the skill resolves its own access, in order: a connected MCP server for that provider → the provider's CLI (`az`, `gh`, `glab`), signed in → REST with a token from the environment → plain `git` for diffs. When no path works, it names what's missing and asks how you want to connect. Azure DevOps and GitHub are exercised daily; GitLab and others ride the same ladder.

`pr-summary` bundles its diff-abridging tools — `abridging.md`, `abridge.py`, `rubric.md`, copied from the `abridge-diff` skill in [vanenshi/skills](https://github.com/vanenshi/skills) (MIT, see [`LICENSE-abridge`](skills/pr-summary/LICENSE-abridge)), itself a port of [boldsoftware/meat](https://github.com/boldsoftware/meat) (Apache-2.0, see [`LICENSE-meat`](skills/pr-summary/LICENSE-meat)) — so it needs no companion skills.

## Commit gate (wrap)

`skills/wrap/hooks/wrap-gate.sh` swaps the model's plain `git commit` for `/wrap c`. Soft gate: the first direct commit in a turn is denied once with an instruction to invoke `Skill(wrap, c)` itself (never to ask the user); that deny arms the gate, so a retry — or wrap's own commit — passes. A user-typed `/wrap …` or the model's `Skill(wrap)` also arms it; every new prompt disarms it. Nothing ever blocks; any question comes from wrap itself (its Arguments section lists every ask). Needs `jq` on PATH; without it the hook prints an error and the gate is off. Wire it in `~/.claude/settings.json`:

```json
"PreToolUse":       [{ "matcher": "Bash",  "hooks": [{ "type": "command", "command": "~/.claude/skills/wrap/hooks/wrap-gate.sh", "timeout": 5 }] }],
"PostToolUse":      [{ "matcher": "Skill", "hooks": [{ "type": "command", "command": "~/.claude/skills/wrap/hooks/wrap-gate.sh", "timeout": 5 }] }],
"UserPromptSubmit": [{                    "hooks": [{ "type": "command", "command": "~/.claude/skills/wrap/hooks/wrap-gate.sh", "timeout": 5 }] }]
```

## Adding a skill

1. Create `skills/<skill-name>/SKILL.md` — start from [TEMPLATE.md](TEMPLATE.md).
2. `name` matches the directory. `description` says only when to use the skill — the triggers, never the workflow.
3. Extra files (templates, scripts, references) sit next to the SKILL.md.
4. Spec: [agentskills.io/specification](https://agentskills.io/specification).

## Developing locally

Skills in this repo are symlinked into `~/.claude/skills/` and `~/.agents/skills/` (the cross-runtime path Codex, Copilot CLI, and Gemini CLI also read), so edits go live in every agent immediately. `npx skills add .` installs a copy instead, so it is not a substitute:

```bash
ln -s "$(pwd)/skills/<skill-name>" ~/.claude/skills/<skill-name>
ln -s "$(pwd)/skills/<skill-name>" ~/.agents/skills/<skill-name>
```

Checks — run the ones for what you changed, from the repo root:

```bash
bash tests/template-parity.sh                 # pr-summary and task-summary share one CSS block and one image-host rule, copied by hand
bash skills/wrap/tests/dry-run.sh             # wrap's git mechanics, plus parity with SKILL.md's commands
bash skills/wrap/tests/gate.sh                # wrap's commit-gate hook
uv run skills/pr-summary/abridge.py selftest
uv run skills/task-summary/sanitize.py selftest
```
