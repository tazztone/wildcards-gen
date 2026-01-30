"""
Presets Configuration.

Central source of truth for semantic pruning presets and dataset-specific overrides.
"""

# Universal presets: (min_depth, min_hyponyms, min_leaf, merge_orphans, semantic_clean, semantic_arrange, semantic_arrange_method)
SMART_PRESETS = {
    "Ultra-Detailed": (8, 5, 1, True, True, True, 'eom'),
    "Detailed": (6, 10, 3, True, True, True, 'eom'),
    "Balanced": (4, 50, 5, True, True, True, 'eom'),
    "Compact": (3, 100, 8, True, True, True, 'eom'),
    "Flat": (2, 500, 10, True, True, True, 'eom'),
    "Ultra-Flat": (1, 1000, 20, True, True, True, 'leaf'), # Leaf method best for ultra-flat micro-clusters
}

# Dataset-specific overrides (dataset_name -> preset_name -> values)
DATASET_PRESET_OVERRIDES = {
    "Open Images": {
        "Balanced": (4, 50, 5, True, True, True, 'eom'),
        "Compact": (3, 200, 10, True, True, True, 'eom'),  # Increased threshold to preserve structure
        "Flat": (2, 1500, 15, True, True, True, 'eom'),    # Very aggressive threshold needed for this dataset
    },
    "Tencent ML-Images": {
        "Balanced": (4, 30, 5, True, True, True, 'eom'),
        "Compact": (3, 100, 10, True, True, True, 'eom'),
        "Compact": (3, 100, 10, True, True, True, 'eom'),
        "Flat": (2, 600, 20, True, True, True, 'eom'),     # Higher leaf size to reduce noise in dense lists
        "SKIP_NODES": ['placental', 'organism', 'living thing', 'whole', 'object', 'physical entity', 'causal agent'],
        "orphans_label_template": "other_{}",
    },
    "ImageNet": {
        # ImageNet works well with defaults
    },
}

# Per-Category Static Overrides (dataset_name -> category_name -> config)
DATASET_CATEGORY_OVERRIDES = {
    # Example:
    # "ImageNet": {
    #     "person": {"min_hyponyms": 1000}, # Always flatten person
    # }
}

