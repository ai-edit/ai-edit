# ai_edit/core/file_manager.py
"""
Handles safe file operations for ai-edit

NEW IN 2025-08-10
-----------------
Adds basic formatting-preservation strategies:

* Retains the original line-ending style (LF vs. CRLF).
* Preserves whether the original file ended with a trailing newline.

These heuristics keep diffs minimal and honour project-specific
formatting conventions without adding heavy external dependencies.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

import click

from ai_edit.utils.diff import apply_diff


class FileManager:
    """Manages file reading, writing, and backups"""

    def __init__(self, project_dir: Path, backup_dir: Path, debug: bool = False):
        """
        Initialize the file manager
        """
        self.project_dir = project_dir
        self.backup_dir = backup_dir
        self.debug = debug

    # ---------------------------------------------------------------------#
    # Basic helpers                                                         #
    # ---------------------------------------------------------------------#
    def _to_full_path(self, file_path: str) -> Path:
        """
        Convert a relative *file_path* (as used in AI responses) into an
        absolute path inside *project_dir*.
        """
        return self.project_dir / file_path

    # ---------------------------------------------------------------------#
    # Public API                                                            #
    # ---------------------------------------------------------------------#
    def get_file_contents(self, file_path: str) -> str:
        """
        Safely read the contents of a file
        """
        full_path = self._to_full_path(file_path)
        if not full_path.is_file():
            return ""

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:  # pragma: no cover
            raise IOError(f"Error reading file {file_path}: {e}") from e

    def create_backup(self, file_path: str) -> Optional[Path]:
        """
        Create a backup of a file
        """
        source_path = self._to_full_path(file_path)
        if not source_path.is_file():
            return None

        backup_file_path = self.backup_dir / file_path
        backup_file_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(source_path, backup_file_path)
        return backup_file_path

    # ---------------------------------------------------------------------#
    # Diff handling                                                         #
    # ---------------------------------------------------------------------#
    def apply_patch(self, file_path: str, diff: str) -> None:
        """
        Apply a unified *diff* to *file_path*.

        The method will:
        1. Read the current file contents.
        2. Apply the diff via :func:`ai_edit.utils.diff.apply_diff`.
        3. Overwrite the file with the patched result.

        A backup is created automatically before patching.
        """
        if self.debug:
            click.echo(f"DEBUG: Applying diff patch to '{file_path}'.")

        # Ensure we have something to patch
        original = self.get_file_contents(file_path)

        # Create backup before mutating anything
        self.create_backup(file_path)

        try:
            patched = apply_diff(original, diff)
        except Exception as exc:  # pragma: no cover
            raise IOError(f"Failed to apply diff to {file_path}: {exc}") from exc

        # Preserve basic formatting choices from the original file
        patched = self._preserve_formatting(original, patched)

        self._write_file(file_path, patched)

    # ---------------------------------------------------------------------#
    # Full-content write helpers                                            #
    # ---------------------------------------------------------------------#
    def apply_changes(self, file_path: str, new_content: str) -> None:
        """
        Update *file_path* either by overwriting its full content or, if
        *new_content* looks like a unified diff, by patching the existing
        file contents.

        Heuristic:
          * If the text starts with '---' and contains a line starting
            with '+++', we treat it as a diff.

        This keeps the public signature unchanged for existing callers
        while enabling diff-based updates transparently.
        """
        is_diff = new_content.lstrip().startswith("---") and "\n+++" in new_content

        if is_diff:
            self.apply_patch(file_path, new_content)
        else:
            if self.debug:
                click.echo(f"DEBUG: Overwriting file '{file_path}' directly.")
            original = self.get_file_contents(file_path)
            new_content = self._preserve_formatting(original, new_content)
            self._write_file(file_path, new_content)

    # ---------------------------------------------------------------------#
    # Internal utilities                                                    #
    # ---------------------------------------------------------------------#
    def _write_file(self, file_path: str, content: str) -> None:
        """
        Low-level file writer that safely creates parent directories.
        """
        full_path = self._to_full_path(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:  # pragma: no cover
            raise IOError(f"Error writing to file {file_path}: {e}") from e

    # ------------------------------------------------------------------#
    # Formatting helpers                                                #
    # ------------------------------------------------------------------#
    @staticmethod
    def _detect_line_ending(text: str) -> str:
        """
        Detect the dominant line-ending style in *text*.
        Returns "\\r\\n" for CRLF or "\\n" for LF. Defaults to LF.
        """
        crlf = text.count("\r\n")
        lf = text.count("\n")
        # Subtract CRLF occurrences from LF count because CRLF also
        # increments the standalone LF counter when counting substrings.
        lf -= crlf
        return "\r\n" if crlf > lf else "\n"

    def _preserve_formatting(self, original: str, updated: str) -> str:
        """
        Apply lightweight transformations so that *updated* honours the
        basic formatting conventions of *original*:

        1. Line-ending style (LF vs. CRLF)
        2. Presence / absence of final trailing newline
        """
        if not original:
            return updated  # Nothing to inherit

        # --- 1. Line endings ------------------------------------------------
        original_ending = self._detect_line_ending(original)
        # Normalise `updated` to LF, then apply the desired style
        normalised = updated.replace("\r\n", "\n")
        if original_ending == "\r\n":
            normalised = normalised.replace("\n", "\r\n")

        # --- 2. Trailing newline -------------------------------------------
        original_has_trailing_nl = original.endswith(original_ending)
        updated_has_trailing_nl = normalised.endswith(original_ending)
        if original_has_trailing_nl and not updated_has_trailing_nl:
            normalised += original_ending
        elif not original_has_trailing_nl and updated_has_trailing_nl:
            normalised = normalised[: -len(original_ending)]

        return normalised
