"""
Test CLI functionality
"""

import tempfile
import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch

from ai_edit.cli import cli


class TestCLI:
    """Test command-line interface"""
    
    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cli_help(self):
        """Test CLI help output"""
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "AI-Edit: A command-line AI code editor" in result.output
    
    def test_cli_version(self):
        """Test CLI version output"""
        result = self.runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
    
    def test_init_command(self):
        """Test init command"""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            assert "Successfully initialized ai-edit" in result.output
            assert Path(".ai-edit.yaml").exists()
    
    def test_init_command_already_initialized(self):
        """Test init command when already initialized"""
        with self.runner.isolated_filesystem():
            # First init
            self.runner.invoke(cli, ["init"])
            
            # Second init should show warning
            result = self.runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            assert "already initialized" in result.output
    
    def test_init_command_force(self):
        """Test init command with force flag"""
        with self.runner.isolated_filesystem():
            # First init
            self.runner.invoke(cli, ["init"])
            
            # Force init should succeed
            result = self.runner.invoke(cli, ["init", "--force"])
            assert result.exit_code == 0
            assert "Successfully initialized ai-edit" in result.output
    
    def test_config_set_get(self):
        """Test config set and get commands"""
        with self.runner.isolated_filesystem():
            # Initialize first
            self.runner.invoke(cli, ["init"])
            
            # Set config value
            result = self.runner.invoke(cli, ["config", "set", "azure.endpoint", "https://test.com/"])
            assert result.exit_code == 0
            assert "Set azure.endpoint" in result.output
            
            # Get config value
            result = self.runner.invoke(cli, ["config", "get", "azure.endpoint"])
            assert result.exit_code == 0
            assert "azure.endpoint = https://test.com/" in result.output
    
    def test_config_list(self):
        """Test config list command"""
        with self.runner.isolated_filesystem():
            # Initialize and set some values
            self.runner.invoke(cli, ["init"])
            self.runner.invoke(cli, ["config", "set", "azure.endpoint", "https://test.com/"])
            self.runner.invoke(cli, ["config", "set", "azure.api_key", "secret"])
            
            # List config
            result = self.runner.invoke(cli, ["config", "list"])
            assert result.exit_code == 0
            assert "azure.endpoint = https://test.com/" in result.output
            assert "azure.api_key = ***" in result.output  # Should be masked
    
    def test_status_command_not_initialized(self):
        """Test status command when not initialized"""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ["status"])
            assert result.exit_code == 0
            assert "not initialized" in result.output
    
    def test_status_command_initialized(self):
        """Test status command when initialized"""
        with self.runner.isolated_filesystem():
            self.runner.invoke(cli, ["init"])
            
            result = self.runner.invoke(cli, ["status"])
            assert result.exit_code == 0
            assert "ai-edit initialized" in result.output
    
    def test_edit_command_not_implemented(self):
        """Test edit command shows not implemented message"""
        with self.runner.isolated_filesystem():
            self.runner.invoke(cli, ["init"])
            
            result = self.runner.invoke(cli, ["edit", "Add a function"])
            assert result.exit_code == 0
            assert "not yet implemented" in result.output
    
    def test_edit_command_not_initialized(self):
        """Test edit command when not initialized"""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ["edit", "Add a function"])
            assert result.exit_code == 1
            assert "not initialized" in result.output
    
    def test_direct_edit_syntax(self):
        """Test direct editing without 'edit' subcommand"""
        with self.runner.isolated_filesystem():
            self.runner.invoke(cli, ["init"])
            
            # This should work the same as 'ai-edit edit "Add a function"'
            result = self.runner.invoke(cli, ["Add a function"])
            assert result.exit_code == 0
            assert "not yet implemented" in result.output
    
    def test_verbose_and_debug_flags(self):
        """Test verbose and debug flags"""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ["--verbose", "--debug", "init"])
            assert result.exit_code == 0
            assert "Debug mode enabled" in result.output
            assert "Initializing ai-edit" in result.output
    
    def test_git_repository_detection(self):
        """Test Git repository detection during init"""
        with self.runner.isolated_filesystem():
            # Without .git directory, should ask for confirmation
            with patch('click.confirm', return_value=False):
                result = self.runner.invoke(cli, ["init"])
                assert result.exit_code == 0
                assert "Initialization cancelled" in result.output
            
            # Create .git directory
            Path(".git").mkdir()
            result = self.runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            assert "Successfully initialized ai-edit" in result.output
