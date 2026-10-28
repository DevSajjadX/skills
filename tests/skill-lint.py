# /// script
# requires-python = ">=3.11"
# ///
"""Check every skills/<dir>/SKILL.md for the structure a skill loader and a reader rely on.

FAIL (exit 1): no frontmatter, `name` not equal to the folder, no description, or an
evals/evals.json that isn't valid skill-creator JSON.
WARN (exit 0): a description that doesn't open with a trigger ("Use when" / "Use for") or names
no case the skill is not for ("Not for", "not for", "Skip").

  uv run tests/skill-lint.py            # lint the repo
  uv run tests/skill-lint.py selftest
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import tempfile

TRIGGER = re.compile(r"^Use (when|for)\b")
SKIP = re.compile(r"\b(Not for|not for|Skip)\b")


def frontmatter(text: str) -> dict[str, str] | None:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and not line.startswith((" ", "\t")):
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            fields[key.strip()] = value
    return fields


def lint_evals(path: pathlib.Path, skill: str) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        return [f"evals.json is not valid JSON ({e})"]
    problems = []
    if data.get("skill_name") != skill:
        problems.append(f"evals.json skill_name is {data.get('skill_name')!r}, not {skill!r}")
    evals = data.get("evals")
    if not isinstance(evals, list) or not evals:
        return problems + ["evals.json has no evals list"]
    for i, e in enumerate(evals):
        missing = [k for k in ("id", "prompt", "expected_output") if k not in e]
        if missing:
            problems.append(f"evals.json eval {i} lacks {', '.join(missing)}")
    return problems


def lint(root: pathlib.Path) -> tuple[list[str], list[str]]:
    fails, warns = [], []
    for skill_md in sorted(root.glob("*/SKILL.md")):
        d = skill_md.parent.name
        fm = frontmatter(skill_md.read_text(encoding="utf-8"))
        if fm is None:
            fails.append(f"{d}: no frontmatter")
            continue
        if fm.get("name") != d:
            fails.append(f"{d}: name is {fm.get('name')!r}, not the folder name")
        desc = fm.get("description", "")
        if not desc:
            fails.append(f"{d}: no description")
        else:
            if not TRIGGER.match(desc):
                warns.append(f"{d}: description doesn't open with \"Use when\" or \"Use for\"")
            if not SKIP.search(desc):
                warns.append(f"{d}: description names no case the skill is not for")
        evals = skill_md.parent / "evals" / "evals.json"
        if evals.exists():
            fails += [f"{d}: {p}" for p in lint_evals(evals, d)]
    return fails, warns


def report(fails: list[str], warns: list[str]) -> int:
    for f in fails:
        print(f"FAIL  {f}")
    for w in warns:
        print(f"WARN  {w}")
    print(f"{len(fails)} fail, {len(warns)} warn")
    return 1 if fails else 0


def selftest() -> int:
    def make(root: pathlib.Path, d: str, fm: str, evals: str | None = None) -> None:
        (root / d).mkdir()
        (root / d / "SKILL.md").write_text(f"---\n{fm}\n---\n\n# {d}\n")
        if evals is not None:
            (root / d / "evals").mkdir()
            (root / d / "evals" / "evals.json").write_text(evals)

    with tempfile.TemporaryDirectory() as t:
        root = pathlib.Path(t)
        make(root, "good", 'name: good\ndescription: "Use when X happens. Not for Y."',
             json.dumps({"skill_name": "good", "evals": [{"id": 1, "prompt": "p", "expected_output": "o"}]}))
        make(root, "renamed", "name: other\ndescription: Use when X. Not for Y.")
        make(root, "vague", "name: vague\ndescription: Helps with X.")
        make(root, "badevals", "name: badevals\ndescription: Use when X. Not for Y.", "{nope")
        fails, warns = lint(root)
    checks = [
        ("a clean skill passes", not any(x.startswith("good:") for x in fails + warns)),
        ("a name unlike its folder fails", any(x.startswith("renamed:") for x in fails)),
        ("a description with no trigger warns", any("vague:" in w and "Use when" in w for w in warns)),
        ("a description with no skip case warns", any("vague:" in w and "not for" in w for w in warns)),
        ("broken evals JSON fails", any(x.startswith("badevals:") for x in fails)),
    ]
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        sys.exit(selftest())
    sys.exit(report(*lint(pathlib.Path(__file__).resolve().parents[1] / "skills")))
