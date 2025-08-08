#!/usr/bin/env python3
"""
Setup script for development installation
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, check=True):
    """Run a command and optionally check for success"""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
        return e


def main():
    """Set up development environment"""
    print("Setting up ai-edit development environment...")
    
    # Check if we're in a virtual environment
    if sys.prefix == sys.base_prefix:
        print("⚠️  Warning: You don't appear to be in a virtual environment.")
        print("It's recommended to create and activate a virtual environment first:")
        print("  python -m venv venv")
        print("  source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
        
        if not input("Continue anyway? [y/N]: ").lower().startswith('y'):
            sys.exit(0)
    
    # Install package in development mode
    print("\n📦 Installing ai-edit in development mode...")
    run_command([sys.executable, "-m", "pip", "install", "-e", ".[dev]"])
    
    # Install pre-commit hooks
    print("\n🔧 Setting up pre-commit hooks...")
    run_command([sys.executable, "-m", "pre_commit", "install"], check=False)
    
    # Run tests to ensure everything works
    print("\n🧪 Running tests...")
    run_command([sys.executable, "-m", "pytest", "tests/", "-v"], check=False)
    
    print("\n✅ Development environment setup complete!")
    print("\nYou can now use the following commands:")
    print("  ai-edit --help          # Show help")
    print("  ai-edit init            # Initialize a project")
    print("  pytest                  # Run tests")
    print("  black ai_edit/          # Format code")
    print("  flake8 ai_edit/         # Lint code")
    print("  mypy ai_edit/           # Type check")


if __name__ == "__main__":
    main()
