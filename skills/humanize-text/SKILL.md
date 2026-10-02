---
name: humanize-text
description: Rewrite any draft so it does not read as AI-written, in a stated or inferred human voice. Use when the user asks to humanize, de-AI, "make it sound like me", or to check a text for AI tells — blog posts, social posts, comment replies, emails, docs, release notes, bios. Also use as the last gate before any text this session produced goes public. Projects can layer their own voice profile on top; this skill owns the generic engine and the AI-tells checklist.
---

# Humanize text

Turns a draft into something a specific person plausibly wrote. Two jobs:

1. **Humanize a draft** the user pastes (or that another skill just generated).
2. **Draft a reply/post from scratch** in a voice, when there is no draft yet (comment replies, DMs, short posts).

The engine is the same both ways: know the voice, remove the tells, keep the facts.

## Workflow

1. **Pin the job, the medium, and the voice.**
   - Medium matters more than length: a comment reply, a LinkedIn post, and a changelog entry fail differently.
   - Voice source, in order: a project voice profile (see below) → samples of the user's own writing in the repo or the conversation → ask one question. Never invent a persona.
   - If the user gave no draft and no facts, ask for the facts. Do not fill gaps with invented specifics.
2. **Scan for tells.** Read `references/ai-tells.md` and check the draft (or your own draft) against every section. Read it, don't work from memory: the vocabulary list is the part that decays.
3. **Rewrite in the voice.** Follow the voice profile if there is one, otherwise the defaults in `references/voice-profile.md`. Keep every real fact; delete sentences that carry none.
4. **Self-check.** Re-scan your output against the same checklist. Rewrites reintroduce tells, especially rule-of-three and sentence-final "-ing" clauses. Anything that survives gets fixed before you answer.
5. **Deliver ready to paste.** Final text only, in the target medium's format. No change log; one sentence on the biggest change is enough. Never imply anything was sent, posted, or published.

## Voice profiles

A voice profile is a project-owned file the humanizer reads: who the writer is, core traits, hard bans, tone dials, and calibration pairs (bad version vs. voice version of the same content). Calibration pairs do more work than any rule list.

- Project has one → read it and defer to it. Project bans override the generic checklist; the project can be stricter, never looser.
- Project has none → use `references/voice-profile.md` defaults, and offer once to write a profile if the user expects to do this repeatedly.

## Generic defaults, when no profile exists

- Short sentences, one thought each. Contractions. First person if the writer is a person.
- Concrete over abstract: the place, the number, the thing that went wrong.
- Honest uncertainty ("I think", "not sure yet") instead of confident filler.
- Say the thing, then stop. Cut the summarizing last line.
- Formatting matches the medium: no markdown headers in a comment box, no bold-header bullets in a post.
- Emoji: zero or one, only where it reacts to something.

## Hard rules

- **Never fake humanity with errors.** No injected typos, no dropped capitals, no broken grammar. Casual comes from rhythm and word choice.
- **Never invent specifics.** No made-up numbers, dates, anecdotes, or sources. Ask, or keep the claim modest.
- **Never thesaurus-swap within the same register.** "leverage" → "utilize" is not a fix; "use" is.
- **Never keep an AI draft's shape and only change its words.** A listicle of abstractions gets restructured, not repainted.
- **Preserve meaning.** Humanizing removes puffery and hedging theater, not facts, caveats that matter, or required disclosures.

## Boundaries

This skill rewrites and drafts words. It does not decide strategy (what to post, when, whether to reply at all), and it does not generate structured marketing kits — if a project has skills for those, they produce the draft and this one is the last gate before it ships.

## References

- `references/ai-tells.md` — the detection and removal checklist. Read in step 2 and again for the self-check.
- `references/voice-profile.md` — default voice, plus the template for writing a project voice profile.
