"""Configuration handling for Personal Health MCP System."""

import os
from pathlib import Path
from typing import Any

import yaml

from personal_health.exceptions import ConfigurationError


class Config:
    """Application configuration manager."""

    def __init__(
        self, config_path: Path | str | None = None, env: str = os.getenv("APP_ENV", "dev")
    ) -> None:
        """Initialize configuration.

        Args:
            config_path: Path to main config file.
            env: Environment name (dev, prod, etc.).

        Raises:
            ConfigurationError: If config cannot be loaded.
        """
        if config_path is None:
            config_path = (
                Path(__file__).resolve().parent.parent.parent / "configs" / "personal_health.yaml"
            )

        if isinstance(config_path, str):
            config_path = Path(config_path)

        self.config_path = config_path
        self.env = env
        self._config: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load and merge configuration files.

        Raises:
            ConfigurationError: If config files cannot be loaded.
        """
        try:
            # Load main config
            with open(self.config_path) as f:
                self._config = yaml.safe_load(f) or {}

            # Load environment-specific config if it exists
            env_config_path = self.config_path.parent / "environments" / f"{self.env}.yaml"
            if env_config_path.exists():
                with open(env_config_path) as f:
                    env_config = yaml.safe_load(f) or {}
                self._merge_configs(self._config, env_config)

        except FileNotFoundError as e:
            raise ConfigurationError(f"Configuration file not found: {self.config_path}") from e
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML configuration: {e}") from e

    def _merge_configs(self, base: dict[str, Any], override: dict[str, Any]) -> None:
        """Merge override config into base config (in-place).

        Args:
            base: Base configuration dictionary.
            override: Override configuration dictionary.
        """
        for key, value in override.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key.

        Args:
            key: Configuration key (e.g., "server.host", "database.path").
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        keys = key.split(".")
        value: Any = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value

    def __getitem__(self, key: str) -> Any:
        """Get configuration value using bracket notation.

        Args:
            key: Configuration key.

        Returns:
            Configuration value.

        Raises:
            KeyError: If key not found.
        """
        value = self.get(key)
        if value is None:
            raise KeyError(f"Configuration key not found: {key}")
        return value
