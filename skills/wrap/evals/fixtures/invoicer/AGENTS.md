# Invoicer
Fixture project. Gate: `sh gates.sh`.

## Ship
- flow: pr
- host: glab (fakes `bin/glab` and `bin/gh` record calls to `$FAKE_CALLS`)
- ci: none
- merge-method: fast-forward
- may-merge: yes
- sync: rebase
- batching: on
- generated: `src/gen/**`, regenerated with `sh regen.sh`
- pr_template: .gitlab/merge_request_templates/Default.md
- branch-naming: feat/<slug>
- commit-format: Conventional Commits
