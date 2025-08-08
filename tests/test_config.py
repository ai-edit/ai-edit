"""
Test configuration manager functionality
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from ai_edit.config.manager import ConfigManager


class TestConfigManager:
    """Test configuration management"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_manager = ConfigManager(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_default_config_structure(self):
        """Test that default configuration has expected structure"""
        config = ConfigManager.DEFAULT_CONFIG
        
        assert "azure" in config
        assert "context" in config
        assert "safety" in config
        assert "general" in config
        
        assert "endpoint" in config["azure"]
        assert "api_key" in config["azure"]
        assert "model" in config["azure"]
        
        assert "max_files" in config["context"]
        assert "max_tokens" in config["context"]
        assert "ignore_patterns" in config["context"]
    
    def test_initialize_project(self):
        """Test project initialization"""
        self.config_manager.initialize_project(self.temp_dir)
        
        config_file = self.temp_dir / ".ai-edit.yaml"
        assert config_file.exists()
        
        # Test that config file contains expected structure
        config = self.config_manager._load_project_config()
        assert config is not None
        assert "azure" in config
        assert "context" in config
    
    def test_initialize_project_force(self):
        """Test forced project initialization"""
        # First initialization
        self.config_manager.initialize_project(self.temp_dir)
        
        # Second initialization without force should raise error
        with pytest.raises(ValueError, match="already initialized"):
            self.config_manager.initialize_project(self.temp_dir)
        
        # With force should succeed
        self.config_manager.initialize_project(self.temp_dir, force=True)
        assert (self.temp_dir / ".ai-edit.yaml").exists()
    
    def test_set_and_get_config(self):
        """Test setting and getting configuration values"""
        self.config_manager.initialize_project(self.temp_dir)
        
        # Test setting simple values
        self.config_manager.set_config("azure.endpoint", "https://test.openai.azure.com/")
        assert self.config_manager.get_config("azure.endpoint") == "https://test.openai.azure.com/"
        
        # Test setting nested values
        self.config_manager.set_config("azure.model", "gpt-4")
        assert self.config_manager.get_config("azure.model") == "gpt-4"
        
        # Test default values
        assert self.config_manager.get_config("nonexistent.key", "default") == "default"
    
    def test_environment_variable_override(self):
        """Test that environment variables override config values"""
        self.config_manager.initialize_project(self.temp_dir)
        self.config_manager.set_config("azure.endpoint", "https://config.openai.azure.com/")
        
        with patch.dict(os.environ, {"AI_EDIT_AZURE_ENDPOINT": "https://env.openai.azure.com/"}):
            assert self.config_manager.get_config("azure.endpoint") == "https://env.openai.azure.com/"
    
    def test_type_conversion(self):
        """Test automatic type conversion for known config keys"""
        self.config_manager.initialize_project(self.temp_dir)
        
        # Test integer conversion
        self.config_manager.set_config("context.max_files", "100")
        assert self.config_manager.get_config("context.max_files") == 100
        assert isinstance(self.config_manager.get_config("context.max_files"), int)
        
        # Test boolean conversion
        self.config_manager.set_config("safety.require_confirmation", "true")
        assert self.config_manager.get_config("safety.require_confirmation") is True
        
        self.config_manager.set_config("safety.create_backups", "false")
        assert self.config_manager.get_config("safety.create_backups") is False
    
    def test_flatten_dict(self):
        """Test dictionary flattening functionality"""
        nested_dict = {
            "level1": {
                "level2": {
                    "key": "value"
                },
                "simple": "test"
            },
            "root": "data"
        }
        
        flattened = self.config_manager._flatten_dict(nested_dict)
        expected = {
            "level1.level2.key": "value",
            "level1.simple": "test",
            "root": "data"
        }
        
        assert flattened == expected
    
    def test_get_all_config(self):
        """Test getting all configuration as flattened dict"""
        self.config_manager.initialize_project(self.temp_dir)
        self.config_manager.set_config("azure.endpoint", "https://test.openai.azure.com/")
        self.config_manager.set_config("azure.model", "gpt-4")
        
        all_config = self.config_manager.get_all_config()
        
        assert "azure.endpoint" in all_config
        assert "azure.model" in all_config
        assert "context.max_files" in all_config
        assert all_config["azure.endpoint"] == "https://test.openai.azure.com/"
    
    def test_validate_config(self):
        """Test configuration validation"""
        # Without initialization, validation should fail
        assert not self.config_manager.validate_config()
        
        # With initialization but no Azure config, should fail
        self.config_manager.initialize_project(self.temp_dir)
        assert not self.config_manager.validate_config()
        
        # With Azure endpoint but no key, should fail
        self.config_manager.set_config("azure.endpoint", "https://test.openai.azure.com/")
        assert not self.config_manager.validate_config()
        
        # With both endpoint and key, should pass
        self.config_manager.set_config("azure.api_key", "test-key")
        assert self.config_manager.validate_config()
    
    def test_get_azure_config(self):
        """Test getting Azure-specific configuration"""
        self.config_manager.initialize_project(self.temp_dir)
        self.config_manager.set_config("azure.endpoint", "https://test.openai.azure.com/")
        self.config_manager.set_config("azure.api_key", "test-key")
        self.config_manager.set_config("azure.model", "gpt-4-turbo")
        
        azure_config = self.config_manager.get_azure_config()
        
        assert azure_config["endpoint"] == "https://test.openai.azure.com/"
        assert azure_config["api_key"] == "test-key"
        assert azure_config["model"] == "gpt-4-turbo"
        assert azure_config["api_version"] == "2024-02-01"  # default value
