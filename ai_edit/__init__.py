"""
AI-Edit: A command-line AI code editor using Azure OpenAI
"""

__version__ = "0.1.0"
__author__ = "Denis Bystruev"
__email__ = "denis@bystruev.com"
__description__ = "A command-line AI code editor that uses Azure OpenAI to make intelligent changes to your codebase"

from .cli import main

__all__ = ["main"]
