"""
Unified Smart Pruning Logic.

This module encapsulates the "Semantic Significance" logic used to decide 
whether a node should be a full category or flattened into a list.
"""

from typing import Optional, Any, List, Tuple
from .wordnet import get_synset_from_wnid, get_primary_synset, get_synset_name, get_synset_wnid

# Lazy-loaded embedding model for semantic cleaning
_EMBEDDING_MODEL = None

class SmartConfig:
    """Configuration for smart pruning."""
    def __init__(self, 
                 enabled: bool = False,
                 min_depth: int = 6,
                 min_hyponyms: int = 10,
                 min_leaf_size: int = 3,
                 merge_orphans: bool = False,
                 category_overrides: dict = None,
                 semantic_cleanup: bool = False,
                 semantic_model: str = "minilm",
                 semantic_threshold: float = 0.5,
                 semantic_arrangement: bool = False,
                 semantic_arrangement_threshold: float = 0.1,
                 semantic_arrangement_min_cluster: int = 5):
        self.enabled = enabled
        self.min_depth = min_depth
        self.min_hyponyms = min_hyponyms
        self.min_leaf_size = min_leaf_size
        self.merge_orphans = merge_orphans
        self.category_overrides = category_overrides or {}
        self.semantic_cleanup = semantic_cleanup
        self.semantic_model = semantic_model
        self.semantic_threshold = semantic_threshold
        self.semantic_arrangement = semantic_arrangement
        self.semantic_arrangement_threshold = semantic_arrangement_threshold
        self.semantic_arrangement_min_cluster = semantic_arrangement_min_cluster

    def get_child_config(self, node_name: str, node_wnid: Optional[str] = None) -> 'SmartConfig':
        """
        Get a SmartConfig instance for a child node, applying any specific overrides.
        If no overrides match, returns self (optimization).
        """
        if not self.enabled or not self.category_overrides:
            return self

        # Check for overrides
        # Match against Name (case-insensitive?) or WNID
        override = None
        
        # Check WNID first (most precise)
        if node_wnid and node_wnid in self.category_overrides:
            override = self.category_overrides[node_wnid]
        
        # Check Name
        if not override and node_name:
            # Try exact match
            if node_name in self.category_overrides:
                override = self.category_overrides[node_name]
            # Try case-insensitive
            elif node_name.lower() in self.category_overrides:
                override = self.category_overrides[node_name.lower()]
        
        if not override:
            return self

        # Create new config with overrides applied
        # Default behavior: overrides are recursive (they become the new base)
        return SmartConfig(
            enabled=self.enabled,
            min_depth=override.get('min_depth', self.min_depth),
            min_hyponyms=override.get('min_hyponyms', self.min_hyponyms),
            min_leaf_size=override.get('min_leaf_size', self.min_leaf_size),
            merge_orphans=override.get('merge_orphans', self.merge_orphans),
            category_overrides=self.category_overrides, # Propagate the full map
            semantic_cleanup=override.get('semantic_cleanup', self.semantic_cleanup),
            semantic_model=override.get('semantic_model', self.semantic_model),
            semantic_threshold=override.get('semantic_threshold', self.semantic_threshold),
            semantic_arrangement=override.get('semantic_arrangement', self.semantic_arrangement),
            semantic_arrangement_threshold=override.get('semantic_arrangement_threshold', self.semantic_arrangement_threshold),
            semantic_arrangement_min_cluster=override.get('semantic_arrangement_min_cluster', self.semantic_arrangement_min_cluster)
        )


def is_synset_significant(synset: Any, config: SmartConfig) -> bool:
    """
    Determine if a synset is semantically significant enough to be a category.
    
    A concept is significant if:
    - It's shallow in WordNet hierarchy (fundamental concept), OR
    - It has many hyponyms (useful for organization)
    """
    if not synset or not config.enabled:
        return False
        
    # Check depth (shallower = more fundamental)
    # min_depth() returns the shortest path to root
    try:
        depth = synset.min_depth()
        if depth <= config.min_depth:
            return True
    except AttributeError:
        pass
    
    # Check hyponym count (mostly for branching factor)
    try:
        # closure is robust but slow-ish; acceptable for offline gen
        hyponyms = list(synset.closure(lambda s: s.hyponyms()))
        if len(hyponyms) >= config.min_hyponyms:
            return True
    except AttributeError:
        pass
        
    return False

def should_prune_node(
    synset: Any, 
    child_count: int, 
    is_root: bool, 
    config: SmartConfig
) -> bool:
    """
    Decide whether to keep a node as a category or flatten it.
    
    Returns True if the node should be flattened.
    """
    if not config.enabled:
        return False # Fallback to caller's depth check
        
    # Roots never pruned
    if is_root:
        return False
        
    # 1. Linear Chain Check
    # If it only has 1 child, it's just adding noise depth. Prune it.
    # UNLESS it's extremely significant? 
    # No, even significant single-child nodes (like "canine > dog") 
    # are usually better flattened if "canine" effectively equals "dog" in this subtree.
    if child_count <= 1:
        return True
        
    # 2. Semantic Significance Check
    if is_synset_significant(synset, config):
        return False
        
    # If not significant and not a root, prune it.
    return True


def handle_small_leaves(
    leaves: list,
    config: SmartConfig
) -> tuple:
    """
    Handle a leaf list that may be too small per min_leaf_size.
    
    Returns:
        (value_to_add, orphans_to_bubble_up)
        
    If merge_orphans is True and list is small: (None, leaves)
    Otherwise: (leaves, [])
    """
    if not config.enabled:
        return (leaves if leaves else [], [])
    
    if len(leaves) < config.min_leaf_size:
        if config.merge_orphans:
            # Bubble up to parent
            return (None, leaves)
        else:
            # Keep as small list (100% retention)
            return (leaves if leaves else [], [])
    
    return (leaves if leaves else [], [])

def init_semantic_model(model_name: str = "minilm"):
    """Initialize the global embedding model if not already loaded."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        from .linter import load_embedding_model, check_dependencies
        if check_dependencies():
            _EMBEDDING_MODEL = load_embedding_model(model_name)
        else:
            # Log warning or handle gracefully
            print("Warning: Semantic cleaning enabled but dependencies missing. Skipping.")
            _EMBEDDING_MODEL = "DISABLED"

def apply_semantic_cleaning(items: List[str], config: SmartConfig) -> List[str]:
    """
    Clean a list of items using semantic embeddings if enabled.
    Returns the cleaned list.
    """
    global _EMBEDDING_MODEL
    
    if not config.enabled or not config.semantic_cleanup or not items:
        return items
        
    if _EMBEDDING_MODEL is None:
        init_semantic_model(config.semantic_model)
        
    if _EMBEDDING_MODEL == "DISABLED":
        return items
        
    from .linter import clean_list
    cleaned, _ = clean_list(items, _EMBEDDING_MODEL, config.semantic_threshold)
    return cleaned

def apply_semantic_arrangement(items: List[str], config: SmartConfig) -> Tuple[dict, List[str]]:
    """
    Arrange a list of items into semantic sub-groups.
    Returns (named_groups, leftovers).
    """
    if not config.enabled or not config.semantic_arrangement or not items:
        return {}, items
        
    init_semantic_model(config.semantic_model)
    if _EMBEDDING_MODEL is None or _EMBEDDING_MODEL == "DISABLED":
         return {}, items
         
    from .arranger import arrange_list
    return arrange_list(
        items, 
        config.semantic_model, 
        config.semantic_arrangement_threshold,
        config.semantic_arrangement_min_cluster
    )
