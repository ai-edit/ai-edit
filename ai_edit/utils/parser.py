# ai_edit/utils/parser.py
"""
Parses the AI's response to extract file operations.
"""
import re
from typing import Any, Dict, List


def parse_ai_response(response: str) -> List[Dict[str, Any]]:
    """
    Parses the raw text response from the AI into a structured list of operations.

    This function looks for fenced code blocks with file paths to extract changes.
    E.g.,
    ```python:path/to/file.py
    ... new content ...
    ```

    Args:
        response: The raw string response from the AI model.

    Returns:
        A list of operation dictionaries.
    """
    operations = []
    # Regex to find fenced code blocks with a language and path
    pattern = re.compile(r"```(?:\w+:)?(.+?)\n(.*?)\n```", re.DOTALL)

    for match in pattern.finditer(response):
        file_path = match.group(1).strip()
        content = match.group(2).strip()

        operations.append(
            {
                "operation": "modify",
                "file_path": file_path,
                "content": content,
            }
        )

    return operations
