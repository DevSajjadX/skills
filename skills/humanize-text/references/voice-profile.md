# Voice: defaults and profile template

Two parts. Use part 1 when the project has no voice profile. Use part 2 when writing one.

## Part 1 — default human voice

Safe fallback when the only thing known is "sound like a person, not a bot". Adjust to the medium; never invent biography.

- **One thought per sentence.** Short sentences by default, varied length overall. A long line, then a short one.
- **Concrete over abstract.** The place, the number, the thing that broke. Detail is the strongest proof a person was there.
- **First person, contractions.** "I tried", "it's", "didn't".
- **Honest uncertainty.** "I think", "not sure yet", "still figuring it out". Firm only about what the writer actually knows.
- **Answer first** in any reply. Context, thanks, or the joke come after, if at all.
- **Humor at the writer's own expense**, one line, after the facts. Never at the reader's.
- **Plain delivery.** No superlatives about the subject. If a reader used a superlative, thank them without echoing it.
- **Stop at the last real point.** No summary line, no call to action unless the user asked for one.
- **Length ceilings.** Comment reply: 1-3 lines, and a reply longer than the comment reads as AI. Social post: a few short stacked lines. Email: what fits on a phone screen.
- **Emoji:** zero or one, only reacting to something specific. Never doubled, never as bullets.
- **Spelling and punctuation are correct.** Casual is rhythm, not errors.

## Part 2 — profile template

A project voice profile lives in the project (its own skill's `references/`, or a doc the skill points at) and answers these, in this order. Keep it to one page; calibration pairs earn their space, rule lists do not.

```markdown
# Voice profile — <name>

Who the writer is: one paragraph. Role, what they make, how they talk about it,
what claim the voice has to protect (if any).

## Core traits
5-10 numbered traits, each one line of rule plus one example.
Traits are what a reader would notice, not abstractions: "answer first",
"names the place and the hour", "never picks a side in public".

## Hard bans
Things that must never appear, project-specific and stricter than the generic
checklist. State each as an absolute with the reason in half a line.

## Calibration pairs
The load-bearing part. For each recurring situation:

**Input:** the comment, prompt, or draft.

*Wrong version:* the plausible AI-sounding answer.

*Voice:* the correct one.

Cover the awkward cases, not just the easy ones: criticism, hostile or
skeptical readers, questions the writer can't answer, political or otherwise
loaded topics, one-word praise.

## Tone dials
Formality, confidence, humor, drama, length, language. One line each,
stated as a position, e.g. "Formality: low. Contractions always."
```

Rules for keeping a profile useful:

- Facts belong in the project's own records, not in the profile. A profile teaches voice; it must never become the source of truth for track names, dates, or links.
- When the user rejects or edits a draft, that correction is a candidate calibration pair. Add it rather than adding another abstract rule.
- If two traits conflict in practice, write the tie-break into the profile instead of deciding fresh each time.
