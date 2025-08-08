# ai_edit/core/__init__.py
"""Core components for AI-Edit"""

from .ai_client import AIClient
from .context import ContextBuilder
from .file_manager import FileManager

__all__ = ["FileManager", "ContextBuilder", "AIClient"]
