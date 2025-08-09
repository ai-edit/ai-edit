### `README.md`

# ai-edit

A command-line AI code editor that uses Azure OpenAI to make intelligent changes to your codebase through natural language instructions.

## Overview

`ai-edit` is a powerful CLI tool that allows developers to describe code changes in natural language and have them automatically implemented using Azure OpenAI's advanced language models. Instead of manually editing files, simply describe what you want to achieve, and `ai-edit` will analyze your codebase and make the necessary changes.

## Features

  - **Natural Language Interface**: Describe changes in plain English.
  - **Azure OpenAI Integration**: Leverages models deployed on Azure AI.
  - **Repository Context Awareness**: Understands your codebase structure to inform the AI.
  - **Safety First**: Includes a dry-run mode, backups, and interactive confirmation before applying changes.
  - **Uses Git for Precise Patching**: Generates `diffs` and applies them using Git to preserve file formatting and make precise changes.
  - **Multi-file Operations**: Can parse and apply changes to multiple files in a single operation.
  - **Externalized Prompts**: Manages prompts in external files for easier customization.

## Installation

### Prerequisites

  - Python 3.8 or higher
  - Git (for repository management)
  - Azure OpenAI API access

### Install from Source

```bash
git clone https://github.com/ai-edit/ai-edit.git
cd ai-edit
pip install -e .
```

## Quick Start

1.  **Initialize in your project directory:**

    ```bash
    cd your-project/
    ai-edit init
    ```

2.  **Configure Azure OpenAI credentials:**

    ```bash
    ai-edit config set azure.endpoint "https://sfo.openai.azure.com/"
    ai-edit config set azure.api_key "your-api-key"
    ai-edit config set azure.api_version "2025-01-01-preview"
    ai-edit config set azure.model "o3"
    ```

    > **⚠️ Security Warning:** The `.ai-edit.yaml` file now contains your secret Azure OpenAI API key. Add this file to your project's `.gitignore` to prevent accidentally committing your credentials to version control.

    > ```bash
    > echo ".ai-edit.yaml" >> .gitignore
    > ```

3.  **Make your first AI-powered edit:**

    ```bash
    ai-edit "Add error handling to the user login function"
    ```

## Usage Examples

### Basic Code Modifications

```bash
# Add functionality
ai-edit "Add input validation to the email field in user registration"

# Refactor code
ai-edit "Extract the database connection logic into a separate utility class"

# Fix issues
ai-edit "Fix the memory leak in the image processing function"
```

## Configuration

Create a `.ai-edit.yaml` file in your project root or use the `config set` command. The configuration supports setting the model, context rules, and safety defaults.

```yaml
# AI model configuration
azure:
  endpoint: "https://sfo.openai.azure.com/"
  model: "o3"
  api_version: "2025-01-01-preview"

# Context settings
context:
  max_files: 50
  max_tokens: 8000
  ignore_patterns:
    - "node_modules/**"
    - "*.log"

# Safety settings
safety:
  require_confirmation: true
  create_backups: true
```

## Command Reference

### Core Commands

  - `ai-edit init` - Initialize ai-edit in the current directory.
  - `ai-edit "description"` - Apply changes based on a natural language description.
  - `ai-edit status` - Show repository analysis and context.

### Configuration

  - `ai-edit config set <key> <value>` - Set a configuration value.
  - `ai-edit config get <key>` - Get a configuration value.
  - `ai-edit config list` - List all current configuration settings.

### Safety & Utilities

  - `ai-edit --dry-run "description"` - Preview changes without applying them.
  - `ai-edit --interactive "description"` - Request confirmation before applying changes.
  - `ai-edit --backup "description"` - Create a backup of files before changes are applied.

## Development

### Setting up Development Environment

```bash
git clone https://github.com/ai-edit/ai-edit.git
cd ai-edit
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### Development Shortcut (Optional)

This project includes a `venv.rc` file which contains a shell function to quickly activate or deactivate the virtual environment.

1.  **Add the function to your shell profile.** Choose the command for your shell (e.g., `.bashrc`, `.zshrc`).

    ```bash
    # For Zsh users:
    cat venv.rc >> ~/.zshrc

    # For Bash users:
    cat venv.rc >> ~/.bashrc
    ```

2.  **Reload your shell.** You can either open a new terminal window or run `source ~/.zshrc` (or your respective shell file).

3.  **Use the `vv` command.** Once set up, you can navigate to the project's root directory and use the `vv` command to toggle the environment on and off.

    ```bash
    # In the project root, this will activate the venv
    vv

    # Run it again to deactivate
    vv
    ```

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
black ai_edit/
flake8 ai_edit/
```

## Architecture

```
ai-edit/
├── ai_edit/
│   ├── __init__.py
│   ├── cli.py              # Command-line interface
│   ├── core/
│   │   ├── ai_client.py    # Azure OpenAI integration
│   │   ├── context.py      # Repository context building
│   │   ├── file_manager.py # File operations
│   ├── config/
│   │   └── manager.py      # Configuration management
│   ├── prompts/
│   │   └── edit_prompt.txt # Prompt templates
│   └── utils/
│       ├── git.py          # Git integration
│       └── parser.py       # Response parsing
└── tests/
```

## Roadmap

  - **Enhanced Git Workflow**:
      - Automatically commit changes made by the AI.
      - A `rollback` command to revert the last set of changes.
      - A `history` command to show a log of AI-driven changes.
  - **Advanced AI Interaction**:
      - Support for other AI providers (OpenAI, Claude, local models).
      - A "feedback loop" where compiler or test errors are sent back to the AI for self-correction.
  - **Safety and Reliability**:
      - Change logging for auditing purposes.
  - **IDE Integration**:
      - VS Code or JetBrains plugin for a seamless workflow.
  - **Broader Distribution**:
      - Publish on PyPI for easy `pip install ai-edit`.

## Support

- 🐛 [Issue Tracker](https://github.com/ai-edit/ai-edit/issues)

---

**Made with ❤️ by developers, for developers**
