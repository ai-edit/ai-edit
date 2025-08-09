# ai_edit/utils/parser.py
"""
Parses the AI's response to extract file operations and tool calls.
"""
import re
from typing import Any, Dict, List


def parse_ai_response(response: str) -> List[Dict[str, Any]]:
    """
    Parses the raw text response from the AI into a structured list of operations.
    This can include code modifications or tool calls.

    Returns:
        A list of operation dictionaries.
    """
    code_ops = _parse_code_blocks(response)
    tool_ops = _parse_tool_calls(response)

    # Prioritize tool calls. If the AI is asking for a tool, don't apply code yet.
    if tool_ops:
        return tool_ops
    return code_ops


def _parse_code_blocks(response: str) -> List[Dict[str, Any]]:
    """Parses fenced code blocks for file modifications."""
    operations = []
    pattern = re.compile(r"```(?:\w+:)?(.+?)\n(.*?)\n```", re.DOTALL)
    for match in pattern.finditer(response):
        file_path = match.group(1).strip()
        content = match.group(2).strip()
        operations.append({"type": "modify_file", "path": file_path, "content": content})
    return operations


def _parse_tool_calls(response: str) -> List[Dict[str, Any]]:
    """Parses XML-formatted tool calls."""
    operations = []
    pattern = re.compile(
        r"<tool_call>.*?<name>(.*?)</name>.*?<path>(.*?)</path>.*?</tool_call>", re.DOTALL
    )
    for match in pattern.finditer(response):
        tool_name = match.group(1).strip()
        file_path = match.group(2).strip()
        if tool_name == "read_file":
            operations.append({"type": "read_file", "path": file_path})
    return operations
