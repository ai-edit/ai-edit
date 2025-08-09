# ai_edit/core/context.py
"""
Builds the repository context for the AI model.
"""

from pathlib import Path
from typing import List

import git
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

from .file_manager import FileManager


class ContextBuilder:
    """Gathers and formats repository context for the AI."""

    def __init__(
        self,
        project_dir: Path,
        file_manager: FileManager,
        ignore_patterns: List[str],
        max_files: int,
        max_tokens: int,
    ):
        """
        Initialize the ContextBuilder.

        Args:
            project_dir: The root directory of the project.
            file_manager: An instance of FileManager to read files.
            ignore_patterns: A list of patterns to ignore, from config.
            max_files: Maximum number of files to include in the context.
            max_tokens: Maximum number of tokens for the context.
        """
        self.project_dir = project_dir
        self.file_manager = file_manager
        self.ignore_patterns = ignore_patterns
        self.max_files = max_files
        self.max_tokens = max_tokens
        self._ignore_spec = self._load_ignore_patterns()

    def _load_ignore_patterns(self) -> PathSpec:
        """Load ignore patterns from .gitignore and config."""
        patterns = self.ignore_patterns[:]  # Start with config patterns

        # Add patterns from .gitignore if it exists
        try:
            repo = git.Repo(self.project_dir, search_parent_directories=True)
            gitignore_path = Path(repo.working_tree_dir) / ".gitignore"
            if gitignore_path.is_file():
                with open(gitignore_path, "r") as f:
                    patterns.extend(f.readlines())
        except git.InvalidGitRepositoryError:
            # Not a git repo, so no .gitignore to load
            pass

        return PathSpec.from_lines(GitWildMatchPattern, patterns)

    def _get_repo_structure(self) -> str:
        """
        Generate a string representing the repository's root files and directory tree.
        """
        lines = []
        # First, list all files in the root directory
        for path in sorted(self.project_dir.iterdir()):
            if not self._ignore_spec.match_file(str(path.relative_to(self.project_dir))):
                if path.is_file():
                    lines.append(f"└── {path.name}")

        # Then, list all directories
        for path in sorted(self.project_dir.iterdir()):
            if not self._ignore_spec.match_file(str(path.relative_to(self.project_dir))):
                if path.is_dir():
                    lines.append(f"├── {path.name}/")

        return "\n".join(lines)

    def build_context(self) -> str:
        """
        Build the initial, high-level context string to be sent to the AI.
        """
        repo_structure = self._get_repo_structure()
        context_parts = [
            "Repository root structure:",
            "==========================",
            repo_structure,
        ]
        return "\n".join(context_parts)
