#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Number a unified diff, then apply a coordinate-based edit plan to it.

The model picks coordinates; this script is the only thing that writes output.
That is the whole point: every surviving row is byte-identical to the original
diff except for explicit local elisions and the mechanically generated `...`
fold markers, so an abridged diff can never contain an invented line.

Usage:
  abridge.py number <diff-file>              Print the diff with an N| gutter.
  abridge.py apply  <diff-file> <plan.json>  Print the abridged diff.
  abridge.py selftest                        Run the built-in checks.

Plan JSON:
  {"summary": "one line",
   "remove":  [[start, end], ...],           inclusive 1-based line ranges
   "replace": [[line, "old", "new"], ...],   local elision inside one line
   "fold":    [[start, end], ...]}           collapse >=2 rows to one `...`

Copied from the abridge-diff skill in vanenshi/skills (MIT, (c) 2026 Amir
Shekari; see LICENSE-abridge next to this file), itself a modified port of
boldsoftware/meat (Apache-2.0, (c) 2026 Bold Software, Inc.; see LICENSE-meat).
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import tempfile

FILE_META = re.compile(
    r"^(index |--- |\+\+\+ |old mode |new mode |new file mode |deleted file mode "
    r"|similarity index |dissimilarity index |rename |copy |Binary files |GIT binary patch)"
)

# ponytail: regex import detection, not a parser. Covers Go/Python/JS/TS/Rust/
# C/C++/Java/Kotlin single-line forms plus parenthesised or braced blocks.
# Upgrade to tree-sitter only if a real diff shows it dropping behavioral rows.
RE_IMPORT_OPEN = re.compile(r"^(?:import|from\s+\S+\s+import|use\s+[^;]*)\s*[({]\s*$")
RE_IMPORT_LINE = re.compile(
    r"^(?:"
    r"import\b"
    r"|from\s+\S+\s+import\b"
    r"|#\s*include\b"
    r"|use\s+[^;]*;"
    r"|(?:global\s+)?using\s+(?:static\s+)?[A-Za-z_][\w.]*\s*(?:=\s*[\w.]+\s*)?;"
    r"|(?:const|let|var)\s+[^=]+=\s*require\s*\("
    r"|require\s*\("
    r"|export\s+[^;]*\bfrom\s+['\"]"
    r")"
)
# Prose rows like "import the dump first." read as imports; leave prose files alone.
PROSE_EXT = (".md", ".markdown", ".rst", ".txt", ".adoc")


def marker_of(line: str) -> str:
    return line[:1] if line[:1] in ("+", "-", " ") else " "


def content_of(line: str) -> str:
    return line[1:] if line[:1] in ("+", "-", " ") else line


def classify(lines: list[str]) -> list[str]:
    """Tag every physical line as file / hunk / body / other."""
    kinds: list[str] = []
    in_hunk = False
    for ln in lines:
        if ln.startswith("diff --git "):
            in_hunk = False
            kinds.append("file")
        elif ln.startswith("@@"):
            in_hunk = True
            kinds.append("hunk")
        elif in_hunk:
            kinds.append("body")
        elif FILE_META.match(ln):
            kinds.append("file")
        else:
            kinds.append("other")
    return kinds


def sections_of(lines: list[str], kinds: list[str]):
    """Split into a preamble (commit message) and per-file sections."""
    pre: list[int] = []
    secs: list[dict] = []
    cur: dict | None = None
    for i, kind in enumerate(kinds):
        starts_file = lines[i].startswith("diff --git ") or (
            cur is None and lines[i].startswith("--- ")
        )
        if starts_file:
            cur = {"meta": [i], "hunks": []}
            secs.append(cur)
        elif cur is None:
            pre.append(i)
        elif kind == "hunk":
            cur["hunks"].append({"hdr": i, "body": []})
        elif kind == "body" and cur["hunks"]:
            cur["hunks"][-1]["body"].append(i)
        else:
            cur["meta"].append(i)
    return pre, secs


def import_rows(lines: list[str], kinds: list[str]) -> set[int]:
    """Body rows that are import/include/require declarations, block forms included."""
    rows: set[int] = set()
    open_at: int | None = None
    prose = False
    for i, kind in enumerate(kinds):
        ln = lines[i]
        if ln.startswith("diff --git ") or (ln.startswith("+++ ") and ln != "+++ /dev/null"):
            prose = ln.split("\t")[0].lower().endswith(PROSE_EXT)
        if kind != "body" or prose:
            open_at = None
            continue
        text = content_of(lines[i]).strip()
        if open_at is not None:
            rows.add(i)
            if text.startswith(")") or text.startswith("}"):
                open_at = None
            continue
        if RE_IMPORT_OPEN.match(text):
            rows.add(i)
            open_at = i
        elif RE_IMPORT_LINE.match(text):
            rows.add(i)
    return rows


def elision_ok(old: str, new: str) -> bool:
    """`new` must be `old` with omitted spans replaced by ... or …, nothing else."""
    if new == old or not re.search(r"\.\.\.|…", new):
        return False
    parts = re.split(r"\.\.\.|…", new)
    if not (old.startswith(parts[0]) and old.endswith(parts[-1])):
        return False
    pos = 0
    for part in parts:
        if not part:
            continue
        found = old.find(part, pos)
        if found < 0:
            return False
        pos = found + len(part)
    return True


def common_indent(texts: list[str]) -> str:
    indents = [re.match(r"[ \t]*", t).group(0) for t in texts if t.strip()]
    if not indents:
        return ""
    shortest = min(indents, key=len)
    for ind in indents:
        while not ind.startswith(shortest):
            shortest = shortest[:-1]
    return shortest


def abridge(raw: str, plan: dict) -> tuple[str, dict]:
    if not isinstance(plan, dict):
        raise ValueError("plan must be a JSON object")  # noqa: TRY004 -- ValueError is the "plan rejected" contract
    lines = raw.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    kinds = classify(lines)
    keep = [True] * len(lines)
    text = list(lines)
    errors: list[str] = []

    def idx(n: int, what: str) -> int | None:
        if not isinstance(n, int) or not 1 <= n <= len(lines):
            errors.append(f"{what}: line {n} is outside 1..{len(lines)}")
            return None
        return n - 1

    def entries(key: str, *types: type) -> list[list]:
        raw_entries = plan.get(key, [])
        good = []
        for e in raw_entries if isinstance(raw_entries, list) else [raw_entries]:
            if isinstance(e, list) and len(e) == len(types) and all(isinstance(v, t) for v, t in zip(e, types)):
                good.append(e)
            else:
                errors.append(f"{key}: entry {e!r} must be [{', '.join(t.__name__ for t in types)}]")
        return good

    imports = import_rows(lines, kinds)
    for i in imports:
        keep[i] = False

    # Blob hashes orient nobody. Dropped automatically for the same reason as
    # imports: zero judgment, so no plan should spend coordinates on them.
    for i, ln in enumerate(lines):
        if kinds[i] == "file" and ln.startswith("index "):
            keep[i] = False

    removed_by_plan: set[int] = set()
    for entry in entries("remove", int, int):
        start, end = entry
        a, b = idx(start, "remove"), idx(end, "remove")
        if a is None or b is None:
            continue
        if a > b:
            errors.append(f"remove: range {start}-{end} is inverted")
            continue
        for i in range(a, b + 1):
            keep[i] = False
            removed_by_plan.add(i)

    for entry in entries("replace", int, str, str):
        line, old, new = entry
        i = idx(line, "replace")
        if i is None:
            continue
        if kinds[i] != "body":
            errors.append(f"replace: line {line} is diff metadata, not a source row")
            continue
        body = content_of(lines[i])
        if body.count(old) != 1:
            errors.append(
                f"replace: line {line} contains {body.count(old)} occurrences of {old!r}, need exactly 1"
            )
            continue
        if not elision_ok(old, new):
            errors.append(
                f"replace: line {line} new text {new!r} is not {old!r} with omitted spans as ... "
            )
            continue
        text[i] = marker_of(lines[i]) + body.replace(old, new)

    for entry in entries("fold", int, int):
        start, end = entry
        a, b = idx(start, "fold"), idx(end, "fold")
        if a is None or b is None:
            continue
        if b - a < 1:
            errors.append(f"fold: range {start}-{end} must cover at least 2 lines")
            continue
        span = list(range(a, b + 1))
        if any(kinds[i] != "body" for i in span):
            errors.append(f"fold: range {start}-{end} crosses diff metadata or a hunk header")
            continue
        markers = {marker_of(lines[i]) for i in span}
        if len(markers) > 1:
            errors.append(f"fold: range {start}-{end} mixes diff markers {sorted(markers)}")
            continue
        if any(i in imports for i in span):
            errors.append(f"fold: range {start}-{end} covers import rows, which are removed automatically")
            continue
        if any(i in removed_by_plan for i in span):
            errors.append(f"fold: range {start}-{end} overlaps a remove range")
            continue
        indent = common_indent([content_of(lines[i]) for i in span])
        text[a] = markers.pop() + indent + "..."
        keep[a] = True
        for i in span[1:]:
            keep[i] = False

    # A header removed while rows under it survive glues those rows onto the
    # previous hunk or file, so they read as changes somewhere else.
    pre, secs = sections_of(lines, kinds)
    for sec in secs:
        live = [h for h in sec["hunks"] if any(keep[j] for j in h["body"])]
        locators = [i for i in sec["meta"] if re.match(r"diff --git |--- |\+\+\+ ", lines[i])]
        for i in [h["hdr"] for h in live] + (locators if live else []):
            if i in removed_by_plan:
                errors.append(f"remove: line {i + 1} is a header of a hunk or file whose rows survive")

    if errors:
        raise ValueError("\n".join(errors))

    out: list[str] = [text[i] for i in pre if keep[i]]
    for sec in secs:
        live = [h for h in sec["hunks"] if any(keep[j] for j in h["body"])]
        if not live:
            continue
        out += [text[i] for i in sec["meta"] if keep[i]]
        for hunk in live:
            if keep[hunk["hdr"]]:
                out.append(text[hunk["hdr"]])
            out += [text[j] for j in hunk["body"] if keep[j]]

    changed = sum(1 for i, ln in enumerate(lines) if kinds[i] == "body" and ln[:1] in ("+", "-"))
    survived = sum(
        1 for i, ln in enumerate(lines) if kinds[i] == "body" and ln[:1] in ("+", "-") and keep[i]
    )
    stats = {"changed_rows": changed, "kept_rows": survived, "imports_dropped": len(imports)}
    return "\n".join(out) + ("\n" if out else ""), stats


def read_diff(path: str) -> str:
    # surrogateescape round-trips non-UTF-8 bytes (legacy-encoded files) unchanged.
    with open(path, encoding="utf-8", errors="surrogateescape") as fh:
        return fh.read()


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(errors="surrogateescape")
    if len(argv) == 2 and argv[1] == "selftest":
        return selftest()
    if len(argv) == 3 and argv[1] == "number":
        body = read_diff(argv[2])
        rows = body.split("\n")
        if rows and rows[-1] == "":
            rows.pop()
        for n, row in enumerate(rows, 1):
            print(f"{n}|{row}")
        return 0
    if len(argv) == 4 and argv[1] == "apply":
        body = read_diff(argv[2])
        with open(argv[3], encoding="utf-8") as fh:
            plan = json.load(fh)
        try:
            result, stats = abridge(body, plan)
        except ValueError as err:
            print(f"plan rejected:\n{err}", file=sys.stderr)
            return 2
        sys.stdout.write(result)
        summary = plan.get("summary", "")
        print(
            f"kept {stats['kept_rows']}/{stats['changed_rows']} changed rows, "
            f"{stats['imports_dropped']} import rows dropped automatically",
            file=sys.stderr,
        )
        if summary:
            print(f"summary: {summary}", file=sys.stderr)
        return 0
    print(__doc__, file=sys.stderr)
    return 1


def selftest() -> int:
    diff = "\n".join(
        [
            "diff --git a/rand.go b/rand.go",
            "index 1111111..2222222 100644",
            "--- a/rand.go",
            "+++ b/rand.go",
            "@@ -1,9 +1,12 @@",
            " import (",
            ' \t"fmt"',
            '-\t"math/rand"',
            '+\t"crypto/rand"',
            '+\t"encoding/hex"',
            " )",
            "@@ -20,4 +23,8 @@",
            "-    return fmt.Sprintf(\"%x\", b)",
            "+    if _, err := rand.Read(b); err != nil {",
            '+        panic(fmt.Errorf("read entropy: %w", err))',
            "+    }",
            "+    return hex.EncodeToString(b)",
            "diff --git a/gen.pb.go b/gen.pb.go",
            "--- a/gen.pb.go",
            "+++ b/gen.pb.go",
            "@@ -1,2 +1,3 @@",
            "+var x = 1",
            "",
        ]
    )

    out, stats = abridge(diff, {"remove": [[19, 22]], "summary": "s"})
    assert "math/rand" not in out, "import rows must vanish without plan coordinates"

    for row in (
        "using Acme.Core.Data;",
        "using static System.Math;",
        "global using Xunit;",
        "using Alias = System.Text.StringBuilder;",
    ):
        assert RE_IMPORT_LINE.match(row), f"C# import form must be stripped: {row}"
    assert not RE_IMPORT_LINE.match("using var conn = new SqlConnection(cs))"), "C# using-statement is code, not an import"
    assert not RE_IMPORT_LINE.match("using (var scope = factory.CreateScope())"), "C# using-block is code, not an import"
    assert "encoding/hex" not in out, out
    assert "1111111" not in out, "index blob hashes must vanish without plan coordinates"
    assert "rand.Read(b)" in out, out
    assert "gen.pb.go" not in out, "a file whose every body row is removed must lose its headers"
    assert stats["imports_dropped"] == 6, stats
    assert (stats["kept_rows"], stats["changed_rows"]) == (5, 9), stats
    assert out.startswith("diff --git a/rand.go"), out

    out, _ = abridge(
        diff,
        {"replace": [[15, 'fmt.Errorf("read entropy: %w", err)', "fmt.Errorf(...)"]], "remove": [[19, 22]]},
    )
    assert "panic(fmt.Errorf(...))" in out, out

    out, _ = abridge(diff, {"fold": [[14, 16]], "remove": [[19, 22]]})
    assert "+    ..." in out, out
    assert "panic(" not in out, out

    out, _ = abridge(diff, {"replace": [[14, "rand.Read(b)", "rand.Read..."]]})
    assert "rand.Read...;" in out, "a trailing elision is legitimate"

    mixed = "\n".join(
        [
            "diff --git a/README.md b/README.md",
            "--- a/README.md",
            "+++ b/README.md",
            "@@ -1,1 +1,2 @@",
            " intro",
            "+import the dump before running migrations.",
            "diff --git a/src/main.rs b/src/main.rs",
            "--- a/src/main.rs",
            "+++ b/src/main.rs",
            "@@ -1,2 +1,4 @@",
            " fn main() {}",
            "",
            "+use std::{io, fs};",
            "+let x = 1;",
            "",
        ]
    )
    out, stats = abridge(mixed, {})
    assert "import the dump" in out, "prose rows are never treated as imports"
    assert "use std::{io" not in out, "a braced single-line Rust use is an import"
    assert stats["changed_rows"] == 3, "a blank body row is context, not a change"

    with tempfile.NamedTemporaryFile("wb", suffix=".diff", delete=False) as fh:
        fh.write(b"@@ -1 +1 @@\n+caf\xe9\n")
    real_stdout, sys.stdout = sys.stdout, io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    try:
        main(["abridge.py", "number", fh.name])
        sys.stdout.flush()
        raw_out = sys.stdout.buffer.getvalue()
    finally:
        sys.stdout = real_stdout
        os.unlink(fh.name)
    assert raw_out == b"1|@@ -1 +1 @@\n2|+caf\xe9\n", "non-UTF-8 bytes must pass through unchanged"

    for bad, why in [
        ({"fold": [[6, 7]]}, "fold over import rows"),
        ({"fold": [[4, 5]]}, "fold across metadata"),
        ({"fold": [[13, 14]]}, "fold mixing - and + markers"),
        ({"fold": [[14, 14]]}, "single-line fold"),
        ({"replace": [[14, "rand.Read", "rand.Reed"]]}, "elision that rewrites characters"),
        ({"replace": [[14, "nosuchtext", "..."]]}, "elision whose old text is absent"),
        ({"remove": [[999, 999]]}, "out-of-range coordinate"),
        ({"replace": [[14, "rand.Read(b)", "Read..."]]}, "elision dropping a leading span"),
        ({"replace": [[14, "rand.Read(b)", "...Read"]]}, "elision dropping a trailing span"),
        ({"remove": [[12, 12]]}, "hunk header removed while its body survives"),
        ({"remove": [[1, 1]]}, "file row removed while its body survives"),
        ({"remove": [5]}, "flat remove entry"),
        ({"replace": [[14, "rand", 5]]}, "non-string replace text"),
        ([], "plan that is not an object"),
    ]:
        try:
            abridge(diff, bad)
        except ValueError:
            continue
        raise AssertionError(f"expected rejection: {why}")

    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
