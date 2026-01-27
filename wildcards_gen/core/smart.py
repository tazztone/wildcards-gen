"""
Unified Smart Pruning Logic.

This module encapsulates the "Semantic Significance" logic used to decide 
whether a node should be a full category or flattened into a list.
"""

from typing import Optional, Any
from .wordnet import get_synset_from_wnid, get_primary_synset

class SmartConfig:
    """Configuration for smart pruning."""
    def __init__(self, 
                 enabled: bool = False,
                 min_depth: int = 6,
                 min_hyponyms: int = 10,
                 min_leaf_size: int = 3):
        self.enabled = enabled
        self.min_depth = min_depth
        self.min_hyponyms = min_hyponyms
        self.min_leaf_size = min_leaf_size

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
