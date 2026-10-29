# tracker fixture

A tiny project whose work items live in a tracker. The tracker CLI is `bin/glab` (a stub over `data.json`; every call is appended to `glab.log`).

## Commands

- Gates: `python gates.py` runs lint, test and the slow e2e gate. `python gates.py --skip e2e` skips the e2e gate. The e2e gate takes `e2e.lock` and fails if the lock already exists, so two overlapping runs fail. The lock and `e2e.log` live in the main checkout, shared by every worktree.
- Tracker: `bin/glab api "projects/:id/milestones?state=active"`, `bin/glab api "projects/:id/issues?milestone=<title>"`, `bin/glab api "projects/:id/issues/<iid>/links"`, `bin/glab issue view <iid> --comments`, `bin/glab issue update <iid> --label <label>`, `bin/glab issue note <iid> -m <text>`.
- Ready label `workflow::ready for dev`, in-progress label `workflow::in dev`, blocked label `workflow::blocked`.
- Ship command: `bin/glab mr merge <branch>` (logs the merge; nothing leaves the machine).
- Install: nothing to install.

## Ask first

- A new dependency of any kind.
