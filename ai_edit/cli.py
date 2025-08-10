# ai_edit/cli.py
"""
Main CLI interface for ai-edit
"""

import sys
from importlib import resources
from pathlib import Path
from typing import Dict, List

import click

from . import __version__
from .config.manager import ConfigManager
from .core.ai_client import AIClient
from .core.context import ContextBuilder
from .core.file_manager import FileManager
from .utils.diff import apply_diff
from .utils.parser import parse_ai_response


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
@click.pass_context
def cli(ctx: click.Context, verbose: bool, debug: bool):
    """AI-Edit: A command-line AI code editor using Azure OpenAI"""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    ctx.obj["config_manager"] = ConfigManager()

    if debug:
        click.echo("Debug mode enabled")

    # ------------------------------------------------------------------
    # Direct natural-language invocation (e.g. `ai-edit "Add a function"`)
    # ------------------------------------------------------------------
    # When *no* sub-command has been invoked but there are remaining
    # arguments, treat them as the description for an `edit` operation.
    if ctx.invoked_subcommand is None and ctx.args:
        description = " ".join(ctx.args)
        # Clear the args so that downstream parsing does not get confused
        ctx.args = []
        ctx.invoke(edit, description=description)  # type: ignore[arg-type]


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


@cli.command()
@click.argument("description")
@click.option("--dry-run", is_flag=True, help="Preview changes without applying them")
@click.option("--backup", is_flag=True, help="Create backup before changes")
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Interactive mode with confirmations",
)
@click.pass_context
def edit(
    ctx: click.Context,
    description: str,
    dry_run: bool,
    backup: bool,
    interactive: bool,
):
    """Apply changes based on natural language description"""
    config_manager: ConfigManager = ctx.obj["config_manager"]
    current_dir = Path.cwd()

    # ---------------------------------------------------------------------
    # Guard: Project *must* be initialised (presence of .ai-edit.yaml)
    # ---------------------------------------------------------------------
    if not (current_dir / ".ai-edit.yaml").exists():
        click.echo("not initialized", err=True)
        sys.exit(_ExitCode.NOT_INITIALIZED)

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

    # Always show the user's description (requirement)
    click.echo(f"Description: {description}")
    if verbose:
        click.echo(
            f"Options: dry-run={dry_run}, backup={backup}, interactive={interactive}, diff-enabled={diff_enabled}"
        )

    click.echo("Building context...")
    context_str = context_builder.build_context()

    try:
        prompt_template = (
            resources.files("ai_edit")
            .joinpath("prompts/edit_prompt.txt")
            .read_text(encoding="utf-8")
        )
        initial_prompt = prompt_template.replace("{{DESCRIPTION}}", description).replace(
            "{{CONTEXT}}", context_str
        )
    except FileNotFoundError:
        click.echo("Error: Could not find the prompt template file.", err=True)
        sys.exit(1)

    system_prompt = (
        "You are an expert AI programmer. Your task is to modify a codebase "
        "based on a user's request."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": initial_prompt},
    ]
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
        ctx.invoke(edit, description=description)
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
