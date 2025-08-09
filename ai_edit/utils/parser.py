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
    tool_ops = _parse_tool_calls(response)
    # Prioritize tool calls. If the AI is asking for a tool, don't apply code yet.
    if tool_ops:
        return tool_ops

    # If no tool calls, parse for the final code block modifications.
    code_ops = _parse_code_blocks(response)
    return code_ops


def _parse_code_blocks(response: str) -> List[Dict[str, Any]]:
    """
    Parses fenced code blocks for file modifications using a line-by-line approach
    with fence counting to correctly handle nested code blocks.
    """
    operations: List[Dict[str, Any]] = []
    lines = response.split("\n")
    in_file_block = False
    current_content: List[str] = []
    current_path = ""
    fence_level = 0

    file_block_pattern = re.compile(r"```(?:\w+:)(.+)")

    for line in lines:
        if not in_file_block:
            match = file_block_pattern.match(line)
            if match:
                # Start of a new file modification block at level 0
                in_file_block = True
                current_path = match.group(1).strip()
                fence_level = 1
        elif in_file_block:
            # Check for opening or closing fences to manage nesting level
            if line.strip().startswith("```"):
                if line.strip() == "```":
                    fence_level -= 1
                else:  # Handles ```bash etc.
                    fence_level += 1

            # If we've returned to level 0, the main block is closed
            if fence_level == 0:
                operations.append(
                    {
                        "type": "modify_file",
                        "path": current_path,
                        "content": "\n".join(current_content).strip(),
                    }
                )
                # Reset for the next potential file block
                in_file_block = False
                current_content = []
                current_path = ""
            else:
                current_content.append(line)

    return operations


def _parse_tool_calls(response: str) -> List[Dict[str, Any]]:
    """Parses XML-formatted tool calls."""
    operations: List[Dict[str, Any]] = []
    # Use findall to capture all tool_call blocks
    pattern = re.compile(
        r"<tool_call>.*?<name>(.*?)</name>.*?<path>(.*?)</path>.*?</tool_call>", re.DOTALL
    )

    matches = pattern.findall(response)
    for tool_name, file_path in matches:
        tool_name = tool_name.strip()
        file_path = file_path.strip()
        if tool_name in ["read_file", "list_files"]:
            operations.append({"type": tool_name, "path": file_path})

    return operations
