# AI-Edit Implementation TODO (Re-verified – 2025-08-10)

## Verification Report (Automated Check – 2025-08-10)

The latest automated audit re-checked all steps that are currently marked **✅ implemented** in this document.

Result: **0 discrepancies** detected.

_All items marked **✅ implemented** were confirmed to be present and functioning as specified._

Summary:
* ✅ 14 / 14 items confirmed.
* ❌ 0 / 14 item requires a fix.

---

Legend:
✅ = Confirmed implemented | ❌ = Missing / incomplete implementation | [p] = Partially complete

---

1. ✅ **Phase 3 → Change Application Engine → Step 4 (CLI / Orchestration)**
   `ai_edit/cli.py` checks `kind == "diff"` and calls `FileManager.apply_patch(...)` when enabled.

2. ✅ **Phase 3 → Response Processing → Error Recovery**
   `ai_edit/utils/parser.py` emits `warning: unclosed_fence_recovered` for unclosed fenced blocks.

3. ✅ **Phase 3 → Change Application Engine → Step 6 (`diff_enabled` flag)**
   When `change_engine.diff_enabled` is set to **False**, the CLI now downgrades any unified diff
   to a _full-file replacement_. Internally the diff is transformed into the updated content
   using `ai_edit.utils.diff.apply_diff` and then written out with `FileManager.apply_changes(...)`.

_All other previously completed items remain verified and correct._

---

## Running the Test Suite

The repository contains three main test modules in the `tests/` directory:

* `tests/test_cli.py` – validates CLI behaviour and user interaction.
* `tests/test_config.py` – covers configuration management logic.
* `tests/test_diff.py` – unit & integration tests for diff generation / application.

### Quick start
# 1 · (Optional) create and activate a virtual environment
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate

# 2 · Install ai-edit with development dependencies
pip install -e ".[dev]"

# 3 · Run the whole test suite
pytest
Extra options:
pytest -q                                    # minimal output
pytest --cov=ai_edit --cov-report=term-missing   # coverage

---

## Phase 1: Project Foundation ✅ COMPLETED
- [x] Set up Python package structure.
- [x] Basic CLI Framework with `init`, `config`, and `status` commands.
- [x] Configuration Management using `.ai-edit.yaml` and environment variables.

## Phase 2: Core Infrastructure ✅ COMPLETED
- [x] Azure OpenAI Integration with `ai_edit/core/ai_client.py`.
- [x] Repository Context Building with `ai_edit/core/context.py`, respecting `.gitignore`.
- [x] File Management System with `ai_edit/core/file_manager.py` for safe reads, writes, and backups.

## ------------------ CURRENT DEVELOPMENT FOCUS ------------------

## Phase 3: AI Processing Pipeline 🟡 PARTIALLY COMPLETED
*A functional baseline exists. Remaining tasks focus on improving precision and robustness.*

- [p] **Change Application Engine**
  - [x] Apply full file content changes.
  - [x] Implement `diff` generation and application for more precise, partial file updates.
    Implementation checklist:
      1. `ai_edit/utils/diff.py` ✅
      2. `ai_edit/core/file_manager.py` ✅
      3. `ai_edit/utils/parser.py` ✅
      4. `ai_edit/cli.py` ✅
      5. Tests (`tests/test_diff.py`) ✅
      6. Optional: Config flag (`.ai-edit.yaml`) ✅
  - [ ] Add strategies to preserve existing code formatting and style where possible.

- [p] **Response Processing**
  - [x] Create `ai_edit/utils/parser.py` to parse AI responses for file operations.
  - [x] Extract full file paths and content from fenced code blocks.
  - [x] Implement error recovery for malformed or ambiguous AI responses.

- [p] **Prompt Engineering**
  - [x] Create context injection templates from external files.
  - [ ] Design specialized prompts for different request types (add, modify, refactor, fix).
  - [ ] Implement few-shot examples in prompts to improve AI accuracy.

## Phase 4: Safety and Validation
*Crucial for user trust and multi-language support.*

- [p] **Core Safety Features**
  - [x] Implement `--dry-run`, `--interactive`, and `--backup` flags in the CLI.
  - [ ] Create `ai_edit/utils/git.py` for automated Git operations.
  - [ ] Automatically create a Git commit before applying changes.
  - [ ] Implement a `rollback` command to revert the last set of changes.

- [ ] **Configurable Validation Engine (NEW)**
  - [ ] Add a `validation_command` (e.g., `make`, `npm test`, `swift build`) to `.ai-edit.yaml`.
  - [ ] After applying changes, automatically run the specified validation command.
  - [ ] Capture the `stdout` and `stderr` from the command.

- [ ] **AI Feedback Loop (NEW)**
  - [ ] If the validation command fails, feed the compiler/linker errors back to the AI.
  - [ ] Use a new prompt template asking the AI to fix the errors based on the feedback.
  - [ ] Re-apply the new, corrected changes from the AI.

## ------------------ NEXT PRIORITIES ------------------

## Phase 5: Advanced Features
- [ ] **Multi-step Operations**
  - [ ] Break complex changes into sequential steps with user confirmation.
- [ ] **Interactive Mode Enhancements**
  - [ ] Implement a conversational interface for clarification questions.

## Phase 6: Testing and Quality
- [ ] **Unit and Integration Testing**
  - [ ] Set up `pytest` framework and write tests for all core components (AI client, parser, file manager).
  - [ ] Create end-to-end tests for common use cases in different languages.
- [p] **Code Quality**
  - [x] Set up pre-commit hooks with `black`, `flake8`, `isort`, `mypy`.

## ------------------ FUTURE VISION ------------------

## Phase 7: User Experience
- [ ] **CLI Enhancements**
  - [ ] Add progress indicators for long operations.
  - [ ] Improve output formatting and color with `rich`.
  - [ ] Add support for shell auto-completion.
- [ ] **Documentation**
  - [ ] Update README with real, multi-language examples.
  - [ ] Create a comprehensive usage and configuration guide.
  - [ ] Provide example projects for testing and demonstration.

## Phase 8: Distribution
- [ ] **Package Distribution**
  - [ ] Prepare for PyPI release.
  - [ ] Set up GitHub Actions for CI/CD to automate testing and releases.
- [ ] **Installation Methods**
  - [ ] Create a Homebrew formula for macOS users.
  - [ ] Publish a Docker image for containerised use.

## Phase 9: Advanced Integrations
- [ ] **Additional AI Providers**
  - [ ] Create a provider abstraction layer.
  - [ ] Add support for the official OpenAI API, Anthropic Claude, and local models via Ollama.
- [ ] **IDE Integration**
  - [ ] Plan and develop a VS Code extension or JetBrains plugin.
- [ ] **Collaboration Features**
  - [ ] Add support for team configuration sharing.
  - [ ] Implement audit logging for changes.
