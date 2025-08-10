"""
Unit and integration tests for ai_edit.utils.diff and FileManager diff
application workflow.
"""

import textwrap
from pathlib import Path

import pytest

from ai_edit.core.file_manager import FileManager
from ai_edit.utils.diff import apply_diff, generate_diff


@pytest.mark.parametrize(
    ("original", "modified"),
    [
        (
            "",
            "first line\nsecond line\n",
        ),
        (
            "keep\nremove-me\nkeep-2\n",
            "keep\nkeep-2\nadded\n",
        ),
        (
            # mix edits, removals and additions
            textwrap.dedent(
                """\
                line 1
                line 2
                line 3
                line 4
                """
            ),
            textwrap.dedent(
                """\
                line 1
                line 2 – edited
                line 4
                line 5 (new)
                """
            ),
        ),
    ],
)
def test_generate_and_apply_diff_roundtrip(original: str, modified: str) -> None:
    """
    A basic round-trip check:

    1. Generate a unified diff from *original* → *modified*.
    2. Apply the diff back onto *original*.
    3. Expect the patched result to equal *modified*.
    """
    diff = generate_diff(original, modified)
    assert diff.startswith("---")  # rudimentary sanity-check

    patched = apply_diff(original, diff)
    assert patched == modified


def test_file_manager_apply_patch(tmp_path: Path) -> None:
    """
    Integration-style test for FileManager.apply_patch:

    Creates a temporary file, applies a diff, verifies file contents have
    changed *and* a backup copy exists.
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    # Arrange
    file_rel = Path("sample.txt")
    original_content = "alpha\nbeta\ngamma\n"
    modified_content = "alpha\nBETA (edited)\ngamma\nDELTA (new)\n"

    (project_dir / file_rel).write_text(original_content, encoding="utf-8")

    fm = FileManager(project_dir=project_dir, backup_dir=backup_dir, debug=True)
    diff = generate_diff(original_content, modified_content)

    # Act
    fm.apply_patch(str(file_rel), diff)

    # Assert: file content updated
    current = (project_dir / file_rel).read_text(encoding="utf-8")
    assert current == modified_content

    # Assert: backup has been created and still contains *original_content*
    backup_file = backup_dir / file_rel
    assert backup_file.is_file(), "Expected backup file to be created"
    assert backup_file.read_text(encoding="utf-8") == original_content
