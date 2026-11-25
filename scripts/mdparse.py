"""Markdown helpers shared by the scripts: fenced code blocks and ATX headings.

Regex-based on purpose (stdlib only). They cover what doc sets use, not all of CommonMark.
"""
import re

FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def scan(text):
    """Yield (kind, line) for each line of text.

    kind is "open" or "close" for a fence line, "code" for a line inside a fenced block
    and "text" for everything else. As in CommonMark, a block opened with N backticks
    (or tildes) is closed only by a line of at least N of the same character and nothing
    else, so a ``` line inside a ~~~~ block is code, not a fence.
    """
    fence = None  # the run that opened the current block, e.g. "```" or "~~~~"
    for line in text.splitlines():
        m = FENCE.match(line)
        if fence is None and m:
            fence = m.group(1)
            yield "open", line
        elif fence is not None and m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) \
                and line.strip() == m.group(1):
            fence = None
            yield "close", line
        else:
            yield ("code" if fence else "text"), line


def heading(line):
    """(level, text) if line is an ATX heading, else None."""
    m = HEADING.match(line)
    return (len(m.group(1)), m.group(2)) if m else None


def headings(text):
    """(level, text) for every heading outside fenced code."""
    return [h for kind, line in scan(text) if kind == "text" and (h := heading(line))]
