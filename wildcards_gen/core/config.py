"""
Configuration management.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Base Paths
BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DB_PATH = os.path.join(BASE_DIR, "embeddings.db")


@dataclass
class Config:
    # API
    api_key: str = os.environ.get("OPENROUTER_API_KEY", "")
    model: str = "google/gemini-flash-1.5"

    # Paths
    output_dir: str = OUTPUT_DIR
    config_dir: str = CONFIG_DIR
    db_path: str = DB_PATH

    # Generation Defaults
    instruction_template: str = "# instruction: {gloss}"

    # GUI Defaults
    gui_share: bool = False
    gui_port: int = 7862
    skip_nodes: Optional[List[str]] = field(default_factory=list)

    # ...
    _config: Dict[str, Any] = field(default_factory=dict)

    def get(self, key, default=None):
        """Mock get method for compatibility with dict-like usage in some places."""
        # Check dataclass fields first
        if hasattr(self, key):
            return getattr(self, key)

        # Check _config dict
        if key in self._config:
            return self._config[key]

        # Simple dot notation lookup simulation
        if key == "datasets.imagenet.root_synset":
            return "entity.n.01"
        if key == "generation.default_depth":
            return 10
        if key == "datasets.imagenet.filter":
            return "none"
        if key == "gui.share":
            return self.gui_share
        if key == "gui.server_port":
            return self.gui_port
        if key == "generation.save_stats":
            return True
        if key == "generation.instruction_template":
            return self.instruction_template
        return default

    def set(self, key: str, value: Any):
        """Set configuration value."""
        if hasattr(self, key):
            setattr(self, key, value)
        self._config[key] = value

    def save(self):
        """Save configuration to disk (placeholder)."""
        # In a real implementation, this would write to a config file.
        # For now, we just log it.
        pass


# Global instance
config = Config()
