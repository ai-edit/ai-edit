#!/usr/bin/env python3
"""
Allow ai_edit to be executable as a module with python -m ai_edit
"""

from .cli import main

if __name__ == "__main__":
    main()
