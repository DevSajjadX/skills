---
name: humanize-text
description: Use when the user asks to humanize or de-AI a text, to "make it sound like me", or to check a text for AI tells; when they paste a draft with just "fix this" or "this sounds like ChatGPT"; or to draft a reply or post in their voice — blog posts, tweets/X and LinkedIn posts, social or marketing copy, comment replies, emails, docs, release notes, bios. Also use as the last gate before any text this session wrote goes public.
---

# Humanize text

Turns a draft into something a specific person plausibly wrote. Three jobs:

1. **Humanize a draft** the user pastes (or that another skill just generated).
2. **Draft a reply/post from scratch** in a voice, when there is no draft yet (comment replies, DMs, short posts).
3. **Check only**, when the user asks whether a text reads as AI: run step 2, then report instead of rewriting. Quote each match with its `ai-tells.md` section, and give a verdict using that file's threshold (one match is coincidence, several is the tell). Rewrite only if asked.

The engine is the same every way: know the voice, remove the tells, keep the facts.

## Workflow

1. **Pin the job, the medium, and the voice.**
   - Medium matters more than length: a comment reply, a LinkedIn post, and a changelog entry fail differently.
   - Voice source, in order: a project voice profile (found as in Voice profiles below) → the user's personal voice profile, when their standing instructions (global CLAUDE.md or memory) name one and the text goes out under the user's own name → samples of the user's own writing in the repo or the conversation → ask one question (who is writing, for whom). If the answer still gives no voice, use the `references/voice-profile.md` Part 1 defaults. Never invent a persona.
   - If the user gave no draft and no facts, ask for the facts. Do not fill gaps with invented specifics.
2. **Scan for tells.** Read `references/ai-tells.md` and check the draft (or your own draft) against every section. Read it, don't work from memory: the vocabulary list is the part that decays.
3. **Rewrite in the voice.** Use the voice source pinned in step 1. Keep every real fact; delete sentences that carry none.
4. **Self-check.** Re-scan your output against the same checklist. Rewrites reintroduce tells, especially rule-of-three and sentence-final "-ing" clauses. Anything that survives gets fixed before you answer.
5. **Deliver ready to paste.** For a check, deliver the job-3 report instead. Otherwise the final text, in the target medium's format, set apart from anything else you say. Outside it: no change log, at most one sentence on the biggest change. Never imply anything was sent, posted, or published.

## Voice profiles

A voice profile is a project-owned file the humanizer reads: who the writer is, core traits, hard bans, tone dials, and calibration pairs (bad version vs. voice version of the same content). Calibration pairs do more work than any rule list.

- Project has one → read it and defer to it. To find it, use the path the calling skill or the project's CLAUDE.md gives. If neither gives one, use the first `voice-profile.md` in the repo, skipping this skill's own folder. If you find none, the project has no profile. Project bans override the generic checklist; the project can be stricter, never looser.
- Project has none → fall back as in step 1 (personal profile, samples, one question, then the `references/voice-profile.md` defaults), and offer once to write a profile if the user expects to do this repeatedly.

## Hard rules

- **Never fake humanity with errors.** No injected typos, no lowercase "i", no dropped capitals, no broken grammar. Casual comes from rhythm and word choice.
- **Never invent specifics.** No made-up numbers, dates, anecdotes, quotes, or sources. Ask, or keep the claim modest.
- **Never thesaurus-swap within the same register.** "leverage" → "utilize" is not a fix; "use" is.
- **Never keep an AI draft's shape and only change its words.** A listicle of abstractions gets restructured, not repainted.
- **Preserve meaning.** Humanizing removes puffery and hedging theater, not facts, caveats that matter, licenses, safety notes, or required disclosures.

## Boundaries

This skill rewrites and drafts words. It does not decide strategy (what to post, when, whether to reply at all), and it does not generate structured marketing kits — if a project has skills for those, they produce the draft and this one is the last gate before it ships.

## References

- `references/ai-tells.md` — the detection and removal checklist. Read in step 2 and again for the self-check.
- `references/voice-profile.md` — default voice, plus the template for writing a project voice profile.
