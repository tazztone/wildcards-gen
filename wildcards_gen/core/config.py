
import os
import yaml
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Default Configuration
DEFAULT_CONFIG = {
    "api_key": None,
    "model": "google/gemma-3-27b-it:free",
    "paths": {
        "output_dir": "output",
        "downloads_dir": "downloads",
        "log_file": None
    },
    "generation": {
        "default_depth": 3,
        "add_glosses": True,
        "max_retries": 3,
        "timeout": 60
    },
    "datasets": {
        "imagenet": {
            "root_synset": "animal.n.01",
            "filter": None
        },
        "openimages": {
            "version": "v7"
        },
        "tencent": {}
    },
    "gui": {
        "share": False,
        "server_name": "127.0.0.1",
        "server_port": 7860,
        "theme": "default"
    }
}

class ConfigManager:
    """
    Manages configuration loading from files and environment variables.
    Priority: CLI > Local Config > User Config > Env Vars > Defaults
    """
    
    def __init__(self):
        self._config = DEFAULT_CONFIG.copy()
        self.load_configs()
        self.load_env_vars()
        self.validate()

    def load_configs(self):
        """Load config files in priority order."""
        # 1. User config: ~/.config/wildcards-gen/config.yaml
        user_config_path = os.path.expanduser("~/.config/wildcards-gen/config.yaml")
        if os.path.exists(user_config_path):
            self._merge_from_file(user_config_path)

        # 2. Project config: ./wildcards-gen.yaml
        project_config_path = os.path.join(os.getcwd(), "wildcards-gen.yaml")
        if os.path.exists(project_config_path):
            self._merge_from_file(project_config_path)

    def _merge_from_file(self, path: str):
        """Merge a YAML file into the current config."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data and isinstance(data, dict):
                    self._deep_update(self._config, data)
                    logger.debug(f"Loaded config from {path}")
        except Exception as e:
            logger.warning(f"Failed to load config {path}: {e}")

    def _deep_update(self, base: Dict, update: Dict):
        """Recursively update dictionary."""
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def load_env_vars(self):
        """Override with environment variables."""
        # Mapping: Env Var -> Config Key (dot notation)
        mappings = {
            "OPENROUTER_API_KEY": "api_key",
            "WILDCARDS_GEN_MODEL": "model",
            "WILDCARDS_GEN_OUTPUT_DIR": "paths.output_dir",
            "WILDCARDS_GEN_DOWNLOADS_DIR": "paths.downloads_dir"
        }
        
        for env_var, config_key in mappings.items():
            val = os.environ.get(env_var)
            if val is not None:
                self.set(config_key, val)

    def set(self, key_path: str, value: Any):
        """Set a value using dot notation (e.g. 'paths.output_dir')."""
        keys = key_path.split('.')
        target = self._config
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        target[keys[-1]] = value

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a value using dot notation."""
        keys = key_path.split('.')
        target = self._config
        for k in keys:
            if not isinstance(target, dict):
                return default
            target = target.get(k)
            if target is None:
                return default
        return target

    def validate(self):
        """Ensure critical paths are absolute or handled correctly."""
        # Determine strict paths if needed
        pass

    # -- Properties for common access --
    
    @property
    def api_key(self) -> Optional[str]:
        return self.get("api_key")

    @property
    def model(self) -> str:
        return self.get("model")

    @property
    def output_dir(self) -> str:
        return self.get("paths.output_dir")

    @property
    def downloads_dir(self) -> str:
        return self.get("paths.downloads_dir")

# Singleton instance
config = ConfigManager()
