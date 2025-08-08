# ai_edit/core/file_manager.py
"""
Handles safe file operations for ai-edit
"""

import shutil
from pathlib import Path
from typing import Optional


class FileManager:
    """Manages file reading, writing, and backups"""

    def __init__(self, project_dir: Path, backup_dir: Path):
        """
        Initialize the file manager

        Args:
            project_dir: The root directory of the project.
            backup_dir: The directory where backups will be stored.
        """
        self.project_dir = project_dir
        self.backup_dir = backup_dir

    def get_file_contents(self, file_path: str) -> str:
        """
        Safely read the contents of a file

        Args:
            file_path: Relative path to the file within the project.

        Returns:
            The content of the file as a string.
        """
        full_path = self.project_dir / file_path
        if not full_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise IOError(f"Error reading file {file_path}: {e}")

    def create_backup(self, file_path: str) -> Optional[Path]:
        """
        Create a backup of a file

        Args:
            file_path: Relative path to the file to back up.

        Returns:
            The path to the created backup file, or None if the file doesn't exist.
        """
        source_path = self.project_dir / file_path
        if not source_path.is_file():
            return None

        backup_file_path = self.backup_dir / file_path
        backup_file_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(source_path, backup_file_path)
        return backup_file_path

    def apply_changes(self, file_path: str, new_content: str) -> None:
        """
        Write new content to a file

        Args:
            file_path: Relative path to the file to be modified.
            new_content: The new content to write to the file.
        """
        full_path = self.project_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception as e:
            raise IOError(f"Error writing to file {file_path}: {e}")
