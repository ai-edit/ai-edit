# ai-edit

A command-line AI code editor that uses Azure OpenAI to make intelligent changes to your codebase through natural language instructions.

## Overview

`ai-edit` is a powerful CLI tool that allows developers to describe code changes in natural language and have them automatically implemented using Azure OpenAI's advanced language models. Instead of manually editing files, simply describe what you want to achieve, and `ai-edit` will analyze your codebase and make the necessary changes.

## Features

- **Natural Language Interface**: Describe changes in plain English
- **Azure OpenAI Integration**: Leverages GPT-5 and other Azure AI models
- **Repository Context Awareness**: Understands your codebase structure and patterns
- **Safety First**: Dry-run mode, backups, and confirmations before changes
- **Git Integration**: Tracks changes and integrates with your version control workflow
- **Multi-file Operations**: Can modify multiple files in a single operation
- **Smart Context Building**: Automatically includes relevant code context

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

### Install from PyPI (coming soon)

```bash
pip install ai-edit
```

## Quick Start

1. **Initialize in your project directory:**
   ```bash
   cd ai-edit
   ai-edit init
   ```

2. **Configure Azure OpenAI credentials:**
   ```bash
   ai-edit config set azure-endpoint "https://your-resource.openai.azure.com/"
   ai-edit config set azure-key "your-api-key"
   ai-edit config set model-name "gpt-5"
   ```

3. **Make your first AI-powered edit:**
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

### Advanced Operations
```bash
# Multiple file changes
ai-edit "Implement user authentication across all API endpoints"

# Add tests
ai-edit "Create comprehensive unit tests for the payment processing module"

# Documentation
ai-edit "Add detailed docstrings to all public methods in the API module"
```

### Safety Features
```bash
# Preview changes without applying them
ai-edit --dry-run "Optimize database queries in the analytics service"

# Interactive mode with confirmations
ai-edit --interactive "Refactor the entire user management system"

# Create backup before changes
ai-edit --backup "Rewrite the authentication middleware"
```

## Configuration

### Azure OpenAI Setup

1. Create an Azure OpenAI resource in the Azure portal
2. Deploy a model (GPT-5 recommended)
3. Get your endpoint URL and API key
4. Configure ai-edit:

```bash
ai-edit config set azure-endpoint "https://your-resource.openai.azure.com/"
ai-edit config set azure-key "your-api-key"
ai-edit config set azure-api-version "2024-02-01"
ai-edit config set model-name "gpt-5"
```

### Project Configuration

Create a `.ai-edit.yaml` file in your project root:

```yaml
# AI model configuration
azure:
  endpoint: "https://your-resource.openai.azure.com/"
  model: "gpt-5"
  api_version: "2024-02-01"

# Context settings
context:
  max_files: 50
  max_tokens: 8000
  ignore_patterns:
    - "node_modules/**"
    - "*.log"
    - "*.tmp"
    - "__pycache__/**"

# Safety settings
safety:
  require_confirmation: true
  create_backups: true
  dry_run_default: false
```

## Command Reference

### Core Commands
- `ai-edit init` - Initialize ai-edit in current directory
- `ai-edit "description"` - Apply changes based on description
- `ai-edit status` - Show repository analysis and context

### Configuration
- `ai-edit config set <key> <value>` - Set configuration value
- `ai-edit config get <key>` - Get configuration value
- `ai-edit config list` - List all configuration

### Safety & Utilities
- `ai-edit --dry-run "description"` - Preview changes without applying
- `ai-edit --backup "description"` - Create backup before changes
- `ai-edit rollback` - Rollback last changes
- `ai-edit history` - Show change history

## Development

### Setting up Development Environment

```bash
git clone https://github.com/ai-edit/ai-edit.git
cd ai-edit
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
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
│   │   └── safety.py       # Backup and safety features
│   ├── config/
│   │   └── manager.py      # Configuration management
│   └── utils/
│       ├── git.py          # Git integration
│       └── parser.py       # Response parsing
├── tests/
├── docs/
└── examples/
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Security

- API keys are stored securely in user configuration
- All changes are logged and can be rolled back
- Sensitive files can be excluded via configuration
- Dry-run mode allows safe preview of changes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Roadmap

- [ ] Support for multiple AI providers (OpenAI, Claude, etc.)
- [ ] Web interface for visual code editing
- [ ] Integration with popular IDEs
- [ ] Advanced refactoring capabilities
- [ ] Code review and suggestion features
- [ ] Team collaboration features

## Support

- 📝 [Documentation](https://github.com/ai-edit/ai-edit/docs)
- 🐛 [Issue Tracker](https://github.com/ai-edit/ai-edit/issues)
- 💬 [Discussions](https://github.com/ai-edit/ai-edit/discussions)

---

**Made with ❤️ by developers, for developers**
