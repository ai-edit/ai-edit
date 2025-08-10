"""
ai_edit.utils.diff
~~~~~~~~~~~~~~~~~~

Utility helpers for generating and applying unified diffs.

The main purpose of this module is to let the AI-Edit engine work with
partial file updates instead of having to replace the entire file
content.  `generate_diff` can be used by tests (and later by the CLI) to
create a unified diff, while `apply_diff` turns such a diff back into its
patched form.

The implementation purposefully avoids external dependencies so that the
core package remains lightweight and self-contained.
"""
from __future__ import annotations

import difflib
import re
from typing import List

_UNIFIED_HUNK_RE = re.compile(
    r"""^@@\s
    -(?P<orig_start>\d+)(?:,(?P<orig_count>\d+))?\s
    \+(?P<mod_start>\d+)(?:,(?P<mod_count>\d+))?\s
    @@""",
    re.VERBOSE,
)


def generate_diff(original: str, modified: str) -> str:
    """
    Generate a unified diff between *original* and *modified*.

    Parameters
    ----------
    original:
        The original text.
    modified:
        The modified text.

    Returns
    -------
    str
        A unified diff string that can later be fed into :func:`apply_diff`.
    """
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    diff_iter = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile="original",
        tofile="modified",
        lineterm="",
    )
    # join *with* newlines, because `lineterm=""` strips them
    return "\n".join(diff_iter) + ("\n" if original_lines or modified_lines else "")


def _copy_until(src: List[str], dst: List[str], start_index: int, current_index: int) -> int:
    """
    Copy unchanged lines from *current_index* up to *start_index* from *src* to *dst*.

    Returns
    -------
    int
        The new *current_index* (which will be equal to *start_index*).
    """
    while current_index < start_index:
        dst.append(src[current_index])
        current_index += 1
    return current_index


def apply_diff(original: str, diff: str) -> str:
    """
    Apply a unified diff to *original* and return the patched text.

    The function supports the standard unified diff format that starts
    with the `---` / `+++` headers and contains one or more hunks in the
    form

        @@ -start,count +start,count @@

    Parameters
    ----------
    original:
        The original (unpatched) text.
    diff:
        A unified diff that should be applied to *original*.

    Returns
    -------
    str
        The patched text.

    Raises
    ------
    ValueError
        If the diff cannot be parsed or applied.
    """
    original_lines = original.splitlines(keepends=True)
    patched_lines: List[str] = []

    diff_lines = diff.splitlines(keepends=False)
    i = 0  # index in diff_lines
    orig_index = 0  # cursor in original_lines

    # Skip potential file headers (--- / +++)
    while i < len(diff_lines) and (
        diff_lines[i].startswith("---") or diff_lines[i].startswith("+++")
    ):
        i += 1

    while i < len(diff_lines):
        line = diff_lines[i]
        if not line.startswith("@@"):
            raise ValueError(f"Unexpected diff content at line {i + 1!r}: {line!r}")

        match = _UNIFIED_HUNK_RE.match(line)
        if match is None:
            raise ValueError(f"Malformed hunk header at line {i + 1!r}: {line!r}")

        # Convert 1-based line numbers in diff to 0-based indices
        orig_start = int(match.group("orig_start")) - 1

        # Copy unchanged part that comes before this hunk
        orig_index = _copy_until(original_lines, patched_lines, orig_start, orig_index)

        # Move to first diff line inside current hunk
        i += 1

        # Process hunk lines until next hunk header or end of diff
        while i < len(diff_lines) and not diff_lines[i].startswith("@@"):
            hunk_line = diff_lines[i]

            # -----------------------------------------------------------------
            # Handle standard diff marks or gracefully skip blank spacer lines
            # -----------------------------------------------------------------
            if hunk_line == "":
                # Blank line (produced by difflib for readability) – ignore.
                i += 1
                continue

            if hunk_line.startswith(" "):  # context line, unchanged
                if orig_index >= len(original_lines):
                    raise ValueError("Diff context out of range of original content")
                patched_lines.append(original_lines[orig_index])
                orig_index += 1
            elif hunk_line.startswith("-"):  # removal
                # Skip line in original, do not add to output
                orig_index += 1
            elif hunk_line.startswith("+"):  # addition
                # Add the line without the leading '+'
                patched_lines.append(hunk_line[1:] + ("\n" if not hunk_line.endswith("\n") else ""))
            else:
                raise ValueError(f"Unknown diff mark {hunk_line!r}")
            i += 1

    # Copy the remainder of the original file (after the last hunk)
    patched_lines.extend(original_lines[orig_index:])

    return "".join(patched_lines)
