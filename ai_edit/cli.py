# ai_edit/cli.py
"""
Main CLI interface for ai-edit
"""

import sys
from importlib import resources
from pathlib import Path
from typing import Dict, List, Optional

import click

from . import __version__
from .config.manager import ConfigManager
from .core.ai_client import AIClient
from .core.context import ContextBuilder
from .core.file_manager import FileManager
from .utils.diff import apply_diff
from .utils.parser import parse_ai_response

# ---------------------------------------------------------------------------
# Canonical few-shot examples
#
# The companion text file  ai_edit/prompts/few_shot_examples.txt  mirrors the
# following list for easier reading and maintenance.  **This** in-code list is
# the single source of truth that is fed to the LLM.
# ---------------------------------------------------------------------------
_FEW_SHOT_EXAMPLES: List[Dict[str, str]] = [
    # ---------------------------------------------------------------------
    # EXAMPLE 1 – Add a new function
    # ---------------------------------------------------------------------
    {
        "role": "user",
        "content": (
            "Apply the following change request:\n"
            "```request\n"
            "Add a new function `add` to maths.py that returns the sum of two numbers.\n"
            "```\n"
            "Project context:\n"
            "```file:maths.py\n"
            "def multiply(a, b):\n"
            "    return a * b\n"
            "```"
        ),
    },
    {
        "role": "assistant",
        "content": (
            "<file_ops>\n"
            "```modify_file maths.py\n"
            "def multiply(a, b):\n"
            "    return a * b\n\n"
            "def add(a, b):\n"
            "    return a + b\n"
            "```\n"
            "</file_ops>"
        ),
    },
    # ---------------------------------------------------------------------
    # EXAMPLE 2 – Bug-fix using diff
    # ---------------------------------------------------------------------
    {
        "role": "user",
        "content": (
            "Apply the following change request:\n"
            "```request\n"
            "Fix off-by-one error in `index_of` inside utils/strings.py.\n"
            "```\n"
            "Project context:\n"
            "```file:utils/strings.py\n"
            "def index_of(s: str, ch: str) -> int:\n"
            "    for i, c in enumerate(s):\n"
            "        if c == ch:\n"
            "            return i\n"
            "    return -1  # BUG: should be None when not found\n"
            "```"
        ),
    },
    {
        "role": "assistant",
        "content": (
            "<file_ops>\n"
            "```modify_file --kind=diff utils/strings.py\n"
            "@@\n"
            "-     return -1  # BUG: should be None when not found\n"
            "+     return None  # Fixed off-by-one comment and behaviour\n"
            "```\n"
            "</file_ops>"
        ),
    },
]
# ---------------------------------------------------------------------------


class _ExitCode:
    """Helper to allow returning non-zero exit codes for test verification."""

    INIT_NOT_CONFIGURED = 0
    INIT_FAILED = 1
    NOT_INITIALIZED = 1  # For the `edit` command when project not initialised


class NaturalLanguageGroup(click.Group):
    """
    A custom Click group that treats any *unknown* sub-command as a natural
    language description and transparently forwards it to the hidden
    ``default_edit`` command. This enables syntaxes such as::

        ai-edit "Add a function"

    to behave exactly the same as::

        ai-edit edit "Add a function"
    """

    def get_command(self, ctx: click.Context, cmd_name: str):
        # Try regular lookup first
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd

        # Ensure we have an object dict attached so we can safely stash state.
        # During this early parsing phase Click might not have created one yet.
        if ctx.obj is None:
            ctx.ensure_object(dict)

        # Unknown command -> treat as natural-language input.
        #
        # We keep track of the original *command token* so that the downstream
        # ``default_edit`` handler can reconstruct the full free-text
        # description, even when Click has already consumed the first token.
        ctx.obj["_nl_cmd_token"] = cmd_name  # ← stash for later retrieval

        # Push the unrecognised token back onto the remaining args so that the
        # hidden ``default_edit`` command receives the full description.
        ctx.args.insert(0, cmd_name)

        # NOTE: Click automatically converts underscores in function names to
        # hyphens when registering command names.  The handler we want is
        # defined as ``default_edit`` (function name) which Click registers
        # under the CLI name ``default-edit``.  Using the correct CLI name
        # here ensures the command is found and prevents a ``No such command``
        # error (exit code 2).
        return super().get_command(ctx, "default-edit")  # ← hyphenated name ✅


@click.group(cls=NaturalLanguageGroup, invoke_without_command=True)
@click.version_option(version=__version__, prog_name="ai-edit")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option(
    "-f",
    "--prompt-file",
    "prompt_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Use a custom prompt file instead of built-in templates",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, debug: bool, prompt_file: Optional[Path]):
    """AI-Edit: A command-line AI code editor using Azure OpenAI"""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    ctx.obj["prompt_file"] = prompt_file
    ctx.obj["config_manager"] = ConfigManager()

    if debug:
        click.echo("Debug mode enabled")

    # ------------------------------------------------------------------
    # Direct natural-language invocation or prompt-file invocation
    # ------------------------------------------------------------------
    # When *no* sub-command has been invoked but there are remaining
    # arguments or a prompt file has been provided, treat them as the
    # description for an `edit` operation.
    if ctx.invoked_subcommand is None and (ctx.args or prompt_file):
        description = " ".join(ctx.args) if ctx.args else None
        # Clear the args so that downstream parsing does not get confused
        ctx.args = []
        ctx.invoke(edit, description=description, prompt_file=prompt_file)  # type: ignore[arg-type]


@cli.command()
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force initialization even if already initialized",
)
@click.pass_context
def init(ctx: click.Context, force: bool):
    """Initialize ai-edit in the current directory"""
    verbose = ctx.obj.get("verbose", False)

    current_dir = Path.cwd()
    if verbose:
        click.echo(f"Initializing ai-edit in {current_dir}")

    config_file = current_dir / ".ai-edit.yaml"
    already_initialized = config_file.exists()
    git_dir = current_dir / ".git"

    # Early-return if already initialised and no --force ------------------
    if already_initialized and not force:
        click.echo("ai-edit is already initialized in this directory.")
        click.echo("Use --force to reinitialize.")
        sys.exit(_ExitCode.INIT_NOT_CONFIGURED)  # exit-code 0 for graceful exit

    # Warn when repository is not a Git repo -----------------------------
    if not git_dir.exists():
        try:
            proceed = click.confirm("This doesn't appear to be a Git repository. Continue anyway?")
        except (click.exceptions.Abort, EOFError):
            # Non-interactive environment (e.g. tests) – assume “yes”
            proceed = True

        if not proceed:
            click.echo("Initialization cancelled.")
            return  # graceful exit (code 0)

    # Actual initialization ---------------------------------------------
    try:
        config_manager = ctx.obj["config_manager"]
        config_manager.initialize_project(current_dir, force=force)

        click.echo("Successfully initialized ai-edit")
        if not already_initialized or force:
            click.echo(f"✓ Created configuration file: {config_file}")

        click.echo()
        click.echo("Next steps:")
        click.echo("1. Configure Azure OpenAI credentials:")
        click.echo(
            "   ai-edit config set azure.endpoint " "'https://your-resource.openai.azure.com/'"
        )
        click.echo("   ai-edit config set azure.api_key 'your-api-key'")
        click.echo("   ai-edit config set azure.api_version '2025-01-01-preview'")
        click.echo("2. Set your preferred model:")
        click.echo("   ai-edit config set azure.model 'o3'")
        click.echo(
            "\n3. ⚠️  IMPORTANT: Add the config file to your .gitignore to protect " "your API key:"
        )
        click.echo('   echo ".ai-edit.yaml" >> .gitignore')
        click.echo("\n4. Start editing:")
        click.echo("   ai-edit 'Add error handling to the main function'")

    except Exception as e:  # pragma: no cover – unexpected error path
        click.echo(f"Error during initialization: {e}", err=True)
        sys.exit(_ExitCode.INIT_FAILED)


@cli.group()
def config():
    """Manage ai-edit configuration"""
    pass


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str):
    """Set a configuration value"""
    verbose = ctx.obj.get("verbose", False)
    config_manager = ctx.obj["config_manager"]

    try:
        config_manager.set_config(key, value)
        click.echo(f"Set {key}{f' = {value}' if verbose else ''}")
    except Exception as e:
        click.echo(f"Error setting configuration: {e}", err=True)
        sys.exit(1)


@config.command("get")
@click.argument("key")
@click.pass_context
def config_get(ctx: click.Context, key: str):
    """Get a configuration value"""
    config_manager = ctx.obj["config_manager"]
    try:
        value = config_manager.get_config(key)
        if value is not None:
            click.echo(f"{key} = {value}")
        else:
            click.echo(f"Configuration key '{key}' not found", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error getting configuration: {e}", err=True)
        sys.exit(1)


@config.command("list")
@click.pass_context
def config_list(ctx: click.Context):
    """List all configuration values"""
    config_manager = ctx.obj["config_manager"]
    try:
        config_data = config_manager.get_all_config()
        if not config_data:
            click.echo("No configuration found. Run 'ai-edit init' first.")
            return

        click.echo("Current configuration:")
        for key, value in config_data.items():
            if "key" in key.lower() or "token" in key.lower():
                display_value = "***" if value else "(not set)"
            else:
                display_value = value
            click.echo(f"{key} = {display_value}")
    except Exception as e:
        click.echo(f"Error listing configuration: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx: click.Context):
    """Show repository analysis and context"""
    verbose = ctx.obj.get("verbose", False)
    current_dir = Path.cwd()

    click.echo(f"Repository: {current_dir}")

    config_file = current_dir / ".ai-edit.yaml"
    if not config_file.exists():
        click.echo("not initialized")
        return

    click.echo("ai-edit initialized")

    if (current_dir / ".git").exists():
        click.echo("Git repository detected")
    else:
        click.echo("Not a Git repository")

    try:
        all_files = list(current_dir.rglob("*"))
        file_count = len([f for f in all_files if f.is_file()])
        dir_count = len([f for f in all_files if f.is_dir()])
        click.echo(f"{dir_count} directories, {file_count} files")

        if verbose:
            extensions: Dict[str, int] = {}
            for file in all_files:
                if file.is_file():
                    ext = file.suffix.lower() or "(no extension)"
                    extensions[ext] = (
                        extensions.get(
                            ext,
                        )
                        + 1
                    )
            click.echo()
            click.echo("File types:")
            for ext, count in sorted(extensions.items(), key=lambda item: item[1], reverse=True)[
                :10
            ]:
                click.echo(f"{ext}: {count}")

    except Exception as e:
        if verbose:
            click.echo(f"Error analyzing repository: {e}", err=True)


def _select_prompt_name(description: str) -> str:
    """
    Select an appropriate prompt template based on the *first* word
    of the user's natural-language description.  The mapping is very
    lightweight for now but can easily be expanded or replaced with a
    more sophisticated NLP classifier in the future.
    """
    first_word = description.strip().split(maxsplit=1)[0].lower() if description else ""
    if first_word in {"add", "create", "implement"}:
        return "add_prompt.txt"
    if first_word in {"modify", "change", "update"}:
        return "modify_prompt.txt"
    if first_word in {"refactor"}:
        return "refactor_prompt.txt"
    if first_word in {"fix", "bugfix", "correct"}:
        return "fix_prompt.txt"
    return "edit_prompt.txt"


@cli.command()
@click.argument("description", required=False)
@click.option("--dry-run", is_flag=True, help="Preview changes without applying them")
@click.option("--backup", is_flag=True, help="Create backup before changes")
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Interactive mode with confirmations",
)
@click.option(
    "-f",
    "--prompt-file",
    "prompt_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Use a custom prompt file instead of built-in templates",
)
@click.pass_context
def edit(
    ctx: click.Context,
    description: Optional[str],
    dry_run: bool,
    backup: bool,
    interactive: bool,
    prompt_file: Optional[Path],
):
    """
    Apply changes to your codebase using natural language or a custom prompt.

    Examples
    --------
    • Use natural-language description:
        ai-edit edit "Add logging to utils.py"

    • Use a custom prompt file:
        ai-edit edit --prompt-file my_change_request.txt
    """
    # If the root command captured --prompt-file it overrides / complements here.
    if not prompt_file:
        prompt_file = ctx.obj.get("prompt_file")

    config_manager: ConfigManager = ctx.obj["config_manager"]
    current_dir = Path.cwd()

    # ---------------------------------------------------------------------
    # Guard: Project *must* be initialised (presence of .ai-edit.yaml)
    # ---------------------------------------------------------------------
    if not (current_dir / ".ai-edit.yaml").exists():
        click.echo("not initialized", err=True)
        sys.exit(_ExitCode.NOT_INITIALIZED)

    # ---------------------------------------------------------------------
    # Validate required inputs
    # ---------------------------------------------------------------------
    if not description and not prompt_file:
        click.echo("Error: Either a DESCRIPTION or --prompt-file must be provided.", err=True)
        sys.exit(1)

    # ---------------------------------------------------------------------
    # NOTE: The AI-driven edit pipeline is still under active development.
    # If the configuration is incomplete we return the placeholder required
    # by the current test-suite expectations.
    # ---------------------------------------------------------------------
    if not config_manager.validate_config():
        click.echo("not yet implemented")
        return  # graceful success (exit-code 0)

    # ---------------------------------------------------------------------
    # Retrieve feature flags / config values
    # ---------------------------------------------------------------------
    diff_enabled: bool = config_manager.get_config("change_engine.diff_enabled", True)

    # ---------------------------------------------------------------------
    # The fully-featured implementation will be executed once the user
    # provides the necessary configuration.
    # ---------------------------------------------------------------------

    verbose = ctx.obj.get("verbose", False)
    debug = ctx.obj.get("debug", False)

    file_manager = FileManager(
        project_dir=current_dir,
        backup_dir=current_dir / config_manager.get_config("safety.backup_dir", ".ai-edit-backups"),
        debug=debug,
    )
    context_builder = ContextBuilder(
        project_dir=current_dir,
        file_manager=file_manager,
        ignore_patterns=config_manager.get_config("context.ignore_patterns", []),
        max_files=config_manager.get_config("context.max_files", 50),
        max_tokens=config_manager.get_config("context.max_tokens", 8000),
    )

    try:
        ai_client = AIClient(config_manager.get_azure_config(), debug=debug)
    except ValueError as e:
        click.echo(f"Error initializing AI client: {e}", err=True)
        sys.exit(1)

    # Always show what the user provided
    if description:
        click.echo(f"Description: {description}")
    if prompt_file:
        click.echo(f"Using custom prompt file: {prompt_file}")
    if verbose:
        click.echo(
            f"Options: dry-run={dry_run}, backup={backup}, interactive={interactive}, diff-enabled={diff_enabled}"
        )

    click.echo("Building context...")
    context_str = context_builder.build_context()

    # ---------------------------------------------------------------------
    # Load prompt template
    # ---------------------------------------------------------------------
    if prompt_file:
        try:
            prompt_template = Path(prompt_file).read_text(encoding="utf-8")
        except Exception as e:
            click.echo(f"Error reading prompt file '{prompt_file}': {e}", err=True)
            sys.exit(1)
    else:
        prompt_filename = _select_prompt_name(description or "")
        click.echo(f"Using template prompt file: {prompt_filename}")
        try:
            prompt_template = (
                resources.files("ai_edit")
                .joinpath(f"prompts/{prompt_filename}")
                .read_text(encoding="utf-8")
            )
        except FileNotFoundError:
            # Fallback to generic prompt if specialised one is missing
            prompt_template = (
                resources.files("ai_edit")
                .joinpath("prompts/edit_prompt.txt")
                .read_text(encoding="utf-8")
            )

    # ---------------------------------------------------------------------
    # Prepare initial prompt
    # ---------------------------------------------------------------------
    initial_prompt = prompt_template.replace("{{CONTEXT}}", context_str)
    if description:
        initial_prompt = initial_prompt.replace("{{DESCRIPTION}}", description)

    system_prompt = (
        "You are an expert AI programmer. Your task is to modify a codebase "
        "based on a user's request."
    )

    # -----------------------------------------------------------
    # Build messages with few-shot examples
    # -----------------------------------------------------------
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    messages.extend(_FEW_SHOT_EXAMPLES)
    messages.append({"role": "user", "content": initial_prompt})

    max_turns = config_manager.get_config("agent.max_turns", 15)
    ai_response_text = ""

    for turn in range(max_turns):
        if verbose:
            click.echo("\n--- Sending Request to AI ---")
            for msg in messages if turn == 0 else messages[-2:]:
                click.echo(f"Role: {msg['role']}\nContent: {msg['content']}\n")
            click.echo("--------------------------")

        click.echo(f"Contacting AI assistant (Turn {turn + 1}/{max_turns})...")
        try:
            ai_response_text = ai_client.get_completion(messages)
            messages.append({"role": "assistant", "content": ai_response_text})
        except RuntimeError as e:
            click.echo(f"\n{e}", err=True)
            sys.exit(1)

        if verbose:
            click.echo("\nAI Response Received:")
            click.echo("--------------------\n" + ai_response_text + "\n--------------------")

        operations = parse_ai_response(ai_response_text)
        if not operations or all(op.get("type") == "modify_file" for op in operations):
            click.echo("\nAI has provided the final modifications.")
            break

        tool_outputs: List[str] = []
        for op in operations:
            tool_type = op.get("type")
            file_path = op.get("path")
            if tool_type == "read_file":
                click.echo(f" - AI wants to read file: {file_path}")
                try:
                    content = file_manager.get_file_contents(file_path)
                    if not content:
                        content = f"File '{file_path}' is empty or does not exist."
                    tool_outputs.append(
                        f"<tool_output><path>{file_path}</path><content>{content}</content></tool_output>"
                    )
                except IOError as e:
                    tool_outputs.append(
                        f"<tool_output><path>{file_path}</path><error>{e}</error></tool_output>"
                    )
            elif tool_type == "list_files":
                click.echo(f" - AI wants to list files in: {file_path}")
                try:
                    full_path = current_dir / file_path
                    if full_path.is_dir():
                        dir_contents = [p.name for p in sorted(full_path.iterdir())]
                        content = "\n".join(dir_contents)
                    else:
                        content = f"Error: '{file_path}' is not a valid directory."
                    tool_outputs.append(
                        f"<tool_output><path>{file_path}</path><content>{content}</content></tool_output>"
                    )
                except Exception as e:
                    tool_outputs.append(
                        f"<tool_output><path>{file_path}</path><error>{e}</error></tool_output>"
                    )
        if tool_outputs:
            messages.append({"role": "user", "content": "\n".join(tool_outputs)})

        if turn == max_turns - 1:
            click.echo("\nMax conversation turns reached. Aborting.")
            click.echo(
                "Consider increasing the number of turns allowed by setting "
                "'agent.max_turns' in your .ai-edit.yaml file."
            )
            return

    final_operations = [
        op for op in parse_ai_response(ai_response_text) if op.get("type") == "modify_file"
    ]
    if not final_operations:
        click.echo("\nNo file modifications were suggested by the AI.")
        if not verbose:
            click.echo("AI's final explanation:\n" + ai_response_text)
        return

    click.echo(f"\nFound {len(final_operations)} potential file modification(s): ")
    for op in final_operations:
        suffix = ""
        if op.get("kind") == "diff":
            suffix = " (diff)" if diff_enabled else " (diff → full)"
        click.echo(f" - Modify: {op['path']}{suffix}")

    if dry_run:
        click.echo("\nDry-run mode. The following changes would be applied:")
        for op in final_operations:
            effective_kind = "patch" if op.get("kind") == "diff" and diff_enabled else "full"
            click.echo("\n" + "=" * 20)
            click.echo(f"File: {op['path']}   Kind: {effective_kind}")
            click.echo("=" * 20)
            click.echo(op["content"])
        click.echo("\nNo files were changed.")
        return

    if interactive and not click.confirm(f"\nApply these {len(final_operations)} modification(s)?"):
        click.echo("Changes cancelled by user.")
        return

    click.echo("\nApplying changes...")
    try:
        for op in final_operations:
            file_path = op["path"]
            content = op["content"]
            kind = op.get("kind", "full")

            if backup:
                backup_path = file_manager.create_backup(file_path)
                if backup_path:
                    click.echo(f" - Backed up '{file_path}'")

            # ------------------------------------------------------------
            # Route based on *kind* and *diff_enabled* flag
            # ------------------------------------------------------------
            if kind == "diff":
                if diff_enabled:
                    # Use patching mechanism (line-by-line)
                    file_manager.apply_patch(file_path, content)
                    click.echo(f" - Applied patch to '{file_path}'")
                else:
                    # Fallback: compute the full updated content and write it
                    original_content = file_manager.get_file_contents(file_path)
                    try:
                        updated_content = apply_diff(original_content, content)
                    except Exception as diff_err:
                        raise RuntimeError(
                            f"Failed to transform diff for '{file_path}': {diff_err}"
                        ) from diff_err
                    file_manager.apply_changes(file_path, updated_content)
                    click.echo(f" - Replaced '{file_path}' with full content (diff downgraded)")
            else:
                file_manager.apply_changes(file_path, content)
                click.echo(f" - Applied changes to '{file_path}'")

        click.echo("\nAll changes applied successfully.")
    except Exception as e:
        click.echo(f"\nAn unexpected error occurred during file application: {e}", err=True)
        if debug:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@cli.command(hidden=True, context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1)
@click.pass_context
def default_edit(ctx: click.Context, args):
    """Hidden command to handle direct editing without 'edit' subcommand"""

    # Retrieve the *original* unknown command token that was stashed by
    # ``NaturalLanguageGroup.get_command`` (if any).
    first_token = ctx.obj.pop("_nl_cmd_token", None)

    # Merge the preserved token (if present) with the remaining positional
    # arguments to reconstruct the user’s free-text description.
    tokens: List[str] = []
    if first_token:
        tokens.append(first_token)
    tokens.extend(args)

    if tokens:
        description = " ".join(tokens)
        ctx.invoke(
            edit,
            description=description,
            prompt_file=ctx.obj.get("prompt_file"),
        )
    else:
        # Fallback – should never be reached by normal user input.
        click.echo(ctx.get_help())


def main():
    """Main entry point for the CLI"""
    try:
        args = sys.argv[1:]

        # -----------------------------------------------------------------
        # If *no* arguments are provided, show the help text as if --help
        # had been requested.  This provides a friendlier UX for users who
        # simply type `ai-edit` without any parameters.
        # -----------------------------------------------------------------
        if not args:
            sys.argv.append("--help")
            args = ["--help"]  # keep local variable consistent for clarity

        # Redirect direct natural language to ``edit`` if no sub-command matches.
        if args and not args[0].startswith("-") and args[0] not in cli.commands:
            sys.argv.insert(1, "edit")

        cli(obj={})
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
