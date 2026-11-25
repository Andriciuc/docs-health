"""Markdown helpers shared by the scripts: fenced code blocks and ATX headings.

Regex-based on purpose (stdlib only). They cover what doc sets use, not all of CommonMark.
"""
import re

FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def scan(text):
    """Yield (kind, line) for each line of text.

    kind is "open" or "close" for a fence line, "code" for a line inside a fenced block
    and "text" for everything else.
    """
    in_code = False
    for line in text.splitlines():
        if FENCE.match(line):
            in_code = not in_code
            yield ("open" if in_code else "close"), line
        else:
            yield ("code" if in_code else "text"), line


def heading(line):
    """(level, text) if line is an ATX heading, else None."""
    m = HEADING.match(line)
    return (len(m.group(1)), m.group(2)) if m else None


def headings(text):
    """(level, text) for every heading outside fenced code."""
    return [h for kind, line in scan(text) if kind == "text" and (h := heading(line))]
