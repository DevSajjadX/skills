# AI writing tells — detection and removal checklist

Distilled from Wikipedia's "Signs of AI writing" (WikiProject AI Cleanup) plus common LLM habits. Scan the draft against every section, rewrite or delete what matches, then scan your own rewrite the same way.

One match is coincidence. Several in one text is the tell.

## 1. Vocabulary (highest signal)

Replace on sight: delve, leverage/leveraging (verb), robust, seamless/seamlessly, landscape (abstract), tapestry, testament, pivotal, crucial, vital, foster/fostering, underscore, highlight (verb, in analysis), showcase, elevate, empower, harness, boast(s), garner, meticulous(ly), intricate/intricacies, interplay, vibrant, enduring, bolster, navigate (abstract), unlock, streamline, "align with", "valuable insights", "key takeaways", game-changer, cutting-edge, "in today's fast-paced world", "evolving landscape", "at the end of the day" (as filler), Additionally/Moreover/Furthermore as sentence openers.

Fix: use the plain word (use, strong, works well, important, help, show) or delete the sentence. Puffery sentences usually carry no information, so deletion is the cheaper fix.

Domain puffery follows the same rule. Whatever the subject is, the words state facts and the subject carries its own weight. Common clusters:

- Nature/travel: breathtaking, stunning, mesmerizing, majestic, serene (as puffery), "hidden gem", "nature's beauty", "capture the beauty of", "escape the hustle", "reminds us to slow down".
- Tech/product: revolutionize, transform, "reimagine", "supercharge", "at scale" (as decoration), "best-in-class", "future-proof".
- Career/LinkedIn: journey, humbled, "excited to share", "lessons learned", "grateful for the opportunity".

## 2. Structural patterns

- **"Not just X, but Y" / "It's not X, it's Y" / "not only... but also"** — state Y directly, or use two plain sentences.
- **Rule of three** ("faster, cleaner, and more scalable"; three parallel bullets; three-part headings) — keep the one or two that matter.
- **Sentence-final "-ing" analysis** ("...enabling teams to ship faster", "...reminding us of what matters") — cut the clause. If the analysis matters, make it a plain sentence.
- **Negative parallelism across sentences** ("This isn't a rewrite. Rather, it constitutes...") — same fix.
- **"X rather than Y"** repeated for false precision.
- **Copula avoidance**: "serves as", "stands as", "represents", "marks", "boasts", "features", "refers to" → "is" or "has".
- **Uniform sentence length and shape.** Real writing varies: a long sentence, then three words. If every sentence is 15-20 words with one comma, that alone reads as generated.
- **Em dash.** LLMs overuse it. Default: at most one per piece, and check the project's rules — some projects ban it outright, and a project ban is absolute (period, comma, or line break instead).

## 3. Content patterns

- **Puffed significance**: "plays a pivotal role", "marks a shift", "reflects broader trends", "lasting legacy". Delete; state facts.
- **Superficial analysis** bolted onto a fact ("...contributing to the broader ecosystem"). Delete.
- **Vague attribution**: "Experts argue", "Studies show", "Many developers believe" with no source. Name the source or own the opinion in first person.
- **Hedging plus overclaiming in one breath**: "While results may vary, this approach revolutionizes...". Pick a lane. Honest hedging on its own is fine and human.
- **Didactic disclaimers**: "It's important to note that...", "It's worth remembering...". Delete the frame, keep any content.
- **Canned challenges/future beats**: "Despite these challenges, the future looks bright". Delete.
- **Summary conclusions**: "In conclusion", "In summary", "Overall...". End on the last real point.
- **Both-sides symmetry** where the writer actually has a view: two balanced paragraphs and no position. Take the position.
- **Generic-anywhere sentences**: if a sentence would fit any post about any subject, it carries no information. Make it concrete or cut it.

## 4. Formatting patterns

- **Bold-header bullets** ("**Performance:** ...", "**Scalability:** ...") → prose, or a plain list only if the items are genuinely enumerable.
- **Title Case Headings** → sentence case.
- **Scattered bolding** of ordinary phrases → remove nearly all of it.
- **Emoji as bullets or section markers** (🚀 ✅ 💡) → remove. Zero or one emoji, inline, only if it reacts to something.
- **Hashtag clusters** (#AI #Tech #Innovation) → zero or one.
- **"🧵👇" bait**, "Let's dive in!", "Let's unpack this" → delete.
- **Mini-tables for two or three facts** → prose.
- **Markdown in a medium that doesn't render it** (comment boxes, DMs, plain email) → strip it.

## 5. Assistant artifacts (delete on sight)

- "I hope this helps", "Would you like me to...", "Certainly!", "Here is a..." preambles.
- Knowledge-cutoff or capability disclaimers, "as of my last update".
- Placeholders left in: [Your Name], [link], YYYY-MM-DD.
- Broken citation tokens and tracking junk: utm_source=chatgpt.com, oaicite, turn0search.
- Restating the user's request back at them before answering.

## 6. What NOT to do while humanizing

- No injected typos, lowercase "i", or broken grammar to fake humanity. Published output is proofread.
- No thesaurus swaps inside the same register.
- No keeping the draft's structure and only changing words.
- No invented specifics: numbers, dates, anecdotes, or quotes. Ask the user or keep the claim modest.
- No stripping caveats, licenses, safety notes, or disclosures that the text needs to be honest.
