"""
Configuration management for ai-edit
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml


class ConfigManager:
    """Manages configuration for ai-edit projects and global settings"""

    DEFAULT_CONFIG = {
        # Azure OpenAI settings
        "azure": {"endpoint": None, "api_key": None, "api_version": "2024-02-01", "model": "gpt-4"},
        # Agent settings
        "agent": {
            "max_turns": 15,
        },
        # Context settings
        "context": {
            "max_files": 50,
            "max_tokens": 8000,
            "ignore_patterns": [
                "node_modules/**",
                "*.log",
                "*.tmp",
                "__pycache__/**",
                ".git/**",
                "*.pyc",
                "*.pyo",
                "*.pyd",
                ".pytest_cache/**",
                ".coverage",
                "htmlcov/**",
                "dist/**",
                "build/**",
                "*.egg-info/**",
            ],
        },
        # Safety settings
        "safety": {
            "require_confirmation": True,
            "create_backups": True,
            "dry_run_default": False,
            "backup_dir": ".ai-edit-backups",
        },
        # Change-application engine settings
        # ``diff_enabled`` toggles whether ai-edit should *apply* incoming
        # unified-diff patches.  When set to ``false`` the engine will fall
        # back to full-file replacements.
        "change_engine": {
            "diff_enabled": True,
        },
        # General settings
        "general": {"verbose": False, "editor": None},  # Will use $EDITOR or default
    }

    def __init__(self, project_dir: Optional[Path] = None):
        """
        Initialize config manager

        Args:
            project_dir: Project directory path. If None, uses current directory.
        """
        self.project_dir = project_dir or Path.cwd()
        self.config_file = self.project_dir / ".ai-edit.yaml"
        self.global_config_dir = Path.home() / ".config" / "ai-edit"
        self.global_config_file = self.global_config_dir / "config.yaml"

        # Ensure global config directory exists
        self.global_config_dir.mkdir(parents=True, exist_ok=True)

    def initialize_project(self, project_dir: Path, force: bool = False) -> None:
        """
        Initialize ai-edit configuration in a project directory

        Args:
            project_dir: Directory to initialize
            force: Whether to overwrite existing configuration
        """
        self.project_dir = project_dir
        self.config_file = project_dir / ".ai-edit.yaml"

        if self.config_file.exists() and not force:
            raise ValueError("Project already initialized. Use --force to overwrite.")

        # Create default project configuration
        config = self.DEFAULT_CONFIG.copy()

        # Try to inherit some settings from global config
        global_config = self._load_global_config()
        if (
            global_config
            and "azure" in global_config
            and isinstance(global_config["azure"], dict)
            and isinstance(config["azure"], dict)
        ):
            config["azure"].update(global_config["azure"])

        self._save_config(config, self.config_file)

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation

        Args:
            key: Configuration key (e.g., 'azure.endpoint')
            default: Default value if key not found
        """
        # First try project config, then global config
        config = self._load_project_config()
        if not config:
            config = self._load_global_config()

        if not config:
            return default

        # Handle environment variable overrides
        env_key = f"AI_EDIT_{key.upper().replace('.', '_').replace('-', '_')}"
        env_value = os.getenv(env_key)
        if env_value:
            return env_value

        # Navigate nested dictionary
        keys = key.split(".")
        value = config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set_config(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation

        Args:
            key: Configuration key (e.g., 'azure.endpoint')
            value: Value to set
        """
        # Load existing config or create new one
        config: Dict[str, Any]
        if self.config_file.exists():
            loaded_config = self._load_project_config()
            config = loaded_config if loaded_config is not None else self.DEFAULT_CONFIG.copy()
        else:
            config = self.DEFAULT_CONFIG.copy()

        # Navigate nested dictionary and set value
        keys = key.split(".")
        current: Union[Dict[str, Any], Any] = config

        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Convert string values for known types
        final_key = keys[-1]
        if key in ["context.max_files", "context.max_tokens", "agent.max_turns"]:
            value = int(value)
        elif key in [
            "safety.require_confirmation",
            "safety.create_backups",
            "safety.dry_run_default",
            "general.verbose",
            "change_engine.diff_enabled",
        ]:
            value = str(value).lower() in ("true", "1", "yes", "on")

        current[final_key] = value

        # Save configuration
        self._save_config(config, self.config_file)

    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration as a flat dictionary with dot notation keys"""
        config = self._load_project_config()
        if not config:
            config = self._load_global_config()

        if not config:
            return {}

        return self._flatten_dict(config)

    def _load_project_config(self) -> Optional[Dict[str, Any]]:
        """Load project-specific configuration"""
        if not self.config_file.exists():
            return None

        try:
            with open(self.config_file, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return None

    def _load_global_config(self) -> Optional[Dict[str, Any]]:
        """Load global configuration"""
        if not self.global_config_file.exists():
            return None

        try:
            with open(self.global_config_file, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return None

    def _save_config(self, config: Dict[str, Any], config_file: Path) -> None:
        """Save configuration to file"""
        try:
            with open(config_file, "w") as f:
                yaml.dump(config, f, default_flow_style=False, indent=2, sort_keys=True)
        except Exception as e:
            raise ValueError(f"Failed to save configuration: {e}")

    def _flatten_dict(
        self, d: Dict[str, Any], parent_key: str = "", sep: str = "."
    ) -> Dict[str, Any]:
        """Flatten nested dictionary with dot notation keys"""
        items: List[Tuple[str, Any]] = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def validate_config(self) -> bool:
        """Validate current configuration"""
        config = self._load_project_config()
        if not config:
            return False

        # Check required Azure settings
        azure_config = config.get("azure", {})
        if not azure_config.get("endpoint") or not azure_config.get("api_key"):
            return False

        return True

    def get_azure_config(self) -> Dict[str, Any]:
        """Get Azure OpenAI configuration"""
        return {
            "endpoint": self.get_config("azure.endpoint"),
            "api_key": self.get_config("azure.api_key"),
            "api_version": self.get_config("azure.api_version", "2024-02-01"),
            "model": self.get_config("azure.model", "gpt-4"),
        }
