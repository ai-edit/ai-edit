# ai_edit/utils/git.py
"""
Utilities for interacting with Git repositories.
"""
from pathlib import Path

import git


def get_repo(path: Path) -> git.Repo:
    """
    Get the git.Repo object for a given path.

    Args:
        path: The path to search for a repository.

    Returns:
        A git.Repo object.

    Raises:
        git.InvalidGitRepositoryError: If no repository is found.
    """
    return git.Repo(path, search_parent_directories=True)


def apply_diff(repo: git.Repo, diff_text: str) -> None:
    """
    Applies a diff to the Git repository's working directory.

    Args:
        repo: The git.Repo object.
        diff_text: The diff content to apply.

    Raises:
        git.GitCommandError: If the diff cannot be applied.
    """
    repo.git.apply(["-"], p=None, R=None, read_stdin_from_pipe=True, input=diff_text)
