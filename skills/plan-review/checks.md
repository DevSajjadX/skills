# Plan checks

The one definition of these checks. A plan's author runs them as self-review; plan-review runs them cold.

- **Locators.** A line number (`file.ts:123-145`) is never a task's only locator: earlier tasks and formatters move it. Name the symbol or quote the exact text to find, and give a line number only as a hint.
- **Task interaction.** For task pairs that share a runtime, clock, environment, or mutable state, check the interaction in both directions: does Task B's new mechanism fire on Task A's test stimulus, and does A's fire on B's? "Independent" asserted in one direction only is not independence.
- **Default flips.** A task that changes a default so existing code paths now reach the network, disk, a device, or the wall clock names, in that same task, every existing test fixture and entry point that needs a fake or override. Otherwise the suite silently goes live.
- **Timing assertions.** A test that measures elapsed time or throughput asserts on structure (field present, numeric, non-negative) or on the raw measurement, never on a value derived from a rounded intermediate. On CI the measured work often finishes in under a millisecond, so anything divided by rounded seconds collapses to 0.
