# ai_edit/cli.py

"""
Main CLI interface for ai-edit
"""

import sys
from pathlib import Path
from typing import Dict

import click

from . import __version__
from .config.manager import ConfigManager

# from .core.file_manager import FileManager


@click.group()
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
        click.echo("Debug mode enabled", err=True)


@cli.command()
@click.option(
    "--force", "-f", is_flag=True, help="Force initialization even if already initialized"
)
@click.pass_context
def init(ctx: click.Context, force: bool):
    """Initialize ai-edit in the current directory"""
    verbose = ctx.obj.get("verbose", False)
    current_dir = Path.cwd()

    if verbose:
        click.echo(f"Initializing ai-edit in {current_dir}")

    # Check if already initialized
    config_file = current_dir / ".ai-edit.yaml"
    if config_file.exists() and not force:
        click.echo("ai-edit is already initialized in this directory.")
        click.echo("Use --force to reinitialize.")
        return

    # Check if we're in a Git repository
    git_dir = current_dir / ".git"
    if not git_dir.exists():
        if not click.confirm("This doesn't appear to be a Git repository. Continue anyway?"):
            click.echo("Initialization cancelled.")
            return

    try:
        config_manager = ctx.obj["config_manager"]
        config_manager.initialize_project(current_dir, force=force)
        click.echo("✓ Successfully initialized ai-edit")
        click.echo(f"✓ Created configuration file: {config_file}")
        click.echo()
        click.echo("Next steps:")
        click.echo("1. Configure Azure OpenAI credentials:")
        click.echo("   ai-edit config set azure.endpoint 'https://your-resource.openai.azure.com/'")
        click.echo("   ai-edit config set azure.api_key 'your-api-key'")
        click.echo("2. Set your preferred model:")
        click.echo("   ai-edit config set azure.model 'gpt-4'")
        click.echo("3. Start editing:")
        click.echo("   ai-edit 'Add error handling to the main function'")

    except Exception as e:
        click.echo(f"Error during initialization: {e}", err=True)
        sys.exit(1)


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

    try:
        config_manager = ctx.obj["config_manager"]
        config_manager.set_config(key, value)

        if verbose:
            click.echo(f"Set {key} = {value}")
        else:
            click.echo(f"✓ Set {key}")

    except Exception as e:
        click.echo(f"Error setting configuration: {e}", err=True)
        sys.exit(1)


@config.command("get")
@click.argument("key")
@click.pass_context
def config_get(ctx: click.Context, key: str):
    """Get a configuration value"""
    try:
        config_manager = ctx.obj["config_manager"]
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
    try:
        config_manager = ctx.obj["config_manager"]
        config_data = config_manager.get_all_config()

        if not config_data:
            click.echo("No configuration found. Run 'ai-edit init' first.")
            return

        click.echo("Current configuration:")
        for key, value in config_data.items():
            # Hide sensitive values
            if "key" in key.lower() or "token" in key.lower():
                display_value = "***" if value else "(not set)"
            else:
                display_value = value
            click.echo(f"  {key} = {display_value}")

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

    # Check if initialized
    config_file = current_dir / ".ai-edit.yaml"
    if not config_file.exists():
        click.echo("❌ ai-edit not initialized. Run 'ai-edit init' first.")
        return

    click.echo("✓ ai-edit initialized")

    # Check Git status
    git_dir = current_dir / ".git"
    if git_dir.exists():
        click.echo("✓ Git repository detected")
    else:
        click.echo("⚠️  Not a Git repository")

    # Show basic file counts
    try:
        all_files = list(current_dir.rglob("*"))
        file_count = len([f for f in all_files if f.is_file()])
        dir_count = len([f for f in all_files if f.is_dir()])

        click.echo(f"📁 {dir_count} directories, {file_count} files")

        if verbose:
            # Show file type breakdown
            extensions: Dict[str, int] = {}
            for file in all_files:
                if file.is_file():
                    ext = file.suffix.lower() or "(no extension)"
                    extensions[ext] = extensions.get(ext, 0) + 1

            click.echo()
            click.echo("File types:")
            for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:10]:
                click.echo(f"  {ext}: {count}")

    except Exception as e:
        if verbose:
            click.echo(f"Error analyzing repository: {e}", err=True)


@cli.command()
@click.argument("description")
@click.option("--dry-run", is_flag=True, help="Preview changes without applying them")
@click.option("--backup", is_flag=True, help="Create backup before changes")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode with confirmations")
@click.pass_context
def edit(ctx: click.Context, description: str, dry_run: bool, backup: bool, interactive: bool):
    """Apply changes based on natural language description"""
    verbose = ctx.obj.get("verbose", False)
    config_manager = ctx.obj["config_manager"]

    # Check if initialized
    current_dir = Path.cwd()
    if not (current_dir / ".ai-edit.yaml").exists():
        click.echo("❌ ai-edit not initialized. Run 'ai-edit init' first.")
        sys.exit(1)

    # Validate Azure configuration
    if not config_manager.validate_config():
        click.echo("❌ Azure OpenAI configuration is missing or invalid.", err=True)
        click.echo(
            "Please set 'azure.endpoint' and 'azure.api_key' using the 'config set' command.",
            err=True,
        )
        sys.exit(1)

    # Setup file manager
    # backup_dir_name = config_manager.get_config("safety.backup_dir", ".ai-edit-backups")
    # file_manager = FileManager(project_dir=current_dir, backup_dir=current_dir / backup_dir_name)

    if dry_run:
        click.echo("🔍 Dry-run mode: previewing changes...")

    if verbose:
        click.echo(f"Description: {description}")
        click.echo(f"Options: dry-run={dry_run}, backup={backup}, interactive={interactive}")

    # TODO: Implement actual AI editing logic
    click.echo("🚧 AI editing functionality not yet implemented")
    click.echo("This will be implemented in Phase 2 & 3")


# Default command - if no subcommand is provided and there's an argument, treat it as edit
@cli.command(hidden=True, context_settings=dict(ignore_unknown_options=True))
@click.argument("args", nargs=-1)
@click.pass_context
def default_edit(ctx: click.Context, args):
    """Hidden command to handle direct editing without 'edit' subcommand"""
    if args:
        description = " ".join(args)
        ctx.invoke(edit, description=description)
    else:
        click.echo(ctx.get_help())


def main():
    """Main entry point for the CLI"""
    try:
        # If called with arguments that don't match any command, treat as edit
        if (
            len(sys.argv) > 1
            and not sys.argv[1].startswith("-")
            and sys.argv[1] not in ["init", "config", "status", "edit"]
        ):
            # Insert 'edit' command
            sys.argv.insert(1, "edit")

        cli(obj={})
    except KeyboardInterrupt:
        click.echo("\n⚠️  Operation cancelled by user", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
