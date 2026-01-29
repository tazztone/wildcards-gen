"""
Presets Configuration.

Central source of truth for semantic pruning presets and dataset-specific overrides.
"""

# Universal presets: (min_depth, min_hyponyms, min_leaf, merge_orphans)
SMART_PRESETS = {
    "Ultra-Detailed": (8, 5, 1, True),
    "Detailed": (6, 10, 3, True),
    "Balanced": (4, 50, 5, True),
    "Compact": (3, 100, 8, True),
    "Flat": (2, 500, 10, True),
    "Ultra-Flat": (1, 1000, 20, True),
}

# Dataset-specific overrides (dataset_name -> preset_name -> values)
DATASET_PRESET_OVERRIDES = {
    "Open Images": {
        "Balanced": (4, 50, 5, True),
        "Compact": (3, 200, 10, True),  # Increased threshold to preserve structure
        "Flat": (2, 1500, 15, True),    # Very aggressive threshold needed for this dataset
    },
    "Tencent ML-Images": {
        "Balanced": (4, 30, 5, True),
        "Compact": (3, 100, 10, True),
        "Flat": (2, 600, 20, True),     # Higher leaf size to reduce noise in dense lists
    },
    "ImageNet": {
        # ImageNet works well with defaults
    },
}
