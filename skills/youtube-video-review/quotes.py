#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Find each review quote in a transcript and give its real timestamp.

A quote matches when its words appear in order in the transcript, ignoring
case, punctuation and line breaks, so it may span several segments. The
timestamp is the start of the segment where the quote begins.

Usage:
  quotes.py <transcript.json> < quotes.txt   One quote per line. Prints
                                             "mm:ss<TAB>quote" or
                                             "FAIL<TAB>quote"; exit 1 on any FAIL.
  quotes.py selftest                         Run the built-in checks.

transcript.json is the youtube_transcript_api CLI's --format json output (a
list of per-video lists of {text, start, duration}) or one flat list of them.
"""

from __future__ import annotations

import json
import re
import sys

WORD = re.compile(r"\w+")


def segments(data: list) -> list[dict]:
    if data and isinstance(data[0], list):
        if len(data) != 1:
            raise ValueError("transcript holds several videos; pass one")
        data = data[0]
    return data


def index(segs: list[dict]) -> tuple[list[str], list[float]]:
    """Every transcript word, lowercased, with the start of its segment."""
    words, starts = [], []
    for s in segs:
        for w in WORD.findall(s["text"].lower()):
            words.append(w)
            starts.append(float(s["start"]))
    return words, starts


def find(quote: str, words: list[str], starts: list[float]) -> float | None:
    q = WORD.findall(quote.lower())
    if not q:
        return None
    for i in range(len(words) - len(q) + 1):
        if words[i:i + len(q)] == q:
            return starts[i]
    return None


def stamp(seconds: float) -> str:
    s = int(seconds)
    h, m = divmod(s // 60, 60)
    return f"{h}:{m:02}:{s % 60:02}" if h else f"{m:02}:{s % 60:02}"


def run(path: str, quotes: list[str]) -> int:
    with open(path, encoding="utf-8") as f:
        words, starts = index(segments(json.load(f)))
    failed = 0
    for quote in (q.strip() for q in quotes):
        if not quote:
            continue
        at = find(quote, words, starts)
        print(f"{stamp(at)}\t{quote}" if at is not None else f"FAIL\t{quote}")
        failed += at is None
    return 1 if failed else 0


def selftest() -> int:
    segs = [{"text": "All right, so here we are", "start": 0.0, "duration": 2},
            {"text": "in front of the\nelephants", "start": 2.5, "duration": 2},
            {"text": "really long trunks", "start": 3725.0, "duration": 2}]
    words, starts = index(segments([segs]))
    assert find("Here we are, in front", words, starts) == 0.0  # spans segments
    assert find("the ELEPHANTS", words, starts) == 2.5
    assert find("elephants have trunks", words, starts) is None  # words out of order
    assert find("...", words, starts) is None
    assert stamp(3725.0) == "1:02:05" and stamp(65.9) == "01:05"
    try:
        segments([segs, segs])
        raise AssertionError("several videos accepted")
    except ValueError:
        pass
    print("selftest ok")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "selftest":
        return selftest()
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    return run(argv[1], sys.stdin.read().splitlines())


if __name__ == "__main__":
    sys.exit(main(sys.argv))
