"""Configuration management utilities."""

import yaml
from pathlib import Path
from typing import Dict, Any


class Config:
    """Configuration loader and accessor."""

    def __init__(self, config_path: str = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to config file. If None, uses default config.yaml
        """
        if config_path is None:
            # Look for config.yaml in project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config.yaml"

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def get(self, *keys: str, default=None) -> Any:
        """
        Get configuration value by nested keys.

        Args:
            keys: Nested configuration keys
            default: Default value if key not found

        Returns:
            Configuration value

        Example:
            config.get('audio', 'sample_rate') -> 16000
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value

    def get_audio_config(self) -> Dict[str, Any]:
        """Get audio processing configuration."""
        return self.config.get("audio", {})

    def get_video_config(self) -> Dict[str, Any]:
        """Get video processing configuration."""
        return self.config.get("video", {})

    def get_fusion_config(self) -> Dict[str, Any]:
        """Get audio-visual fusion configuration."""
        return self.config.get("fusion", {})

    def get_naming_config(self) -> Dict[str, Any]:
        """Get speaker naming configuration."""
        return self.config.get("naming", {})

    def get_output_config(self) -> Dict[str, Any]:
        """Get output generation configuration."""
        return self.config.get("output", {})

    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing configuration."""
        return self.config.get("processing", {})

    def get_privacy_config(self) -> Dict[str, Any]:
        """Get privacy configuration."""
        return self.config.get("privacy", {})


# Global config instance
_config = None


def get_config(config_path: str = None) -> Config:
    """
    Get global configuration instance.

    Args:
        config_path: Path to config file

    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config


def reload_config(config_path: str = None):
    """
    Reload configuration.

    Args:
        config_path: Path to config file
    """
    global _config
    _config = Config(config_path)
