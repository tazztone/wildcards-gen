"""
Unified Smart Pruning Logic.

This module encapsulates the "Semantic Significance" logic used to decide 
whether a node should be a full category or flattened into a list.
"""

from typing import Optional, Any, List, Tuple
from .wordnet import get_synset_from_wnid, get_primary_synset, get_synset_name, get_synset_wnid



class TraversalBudget:
    """
    Simple budget tracker for Fast Preview mode.
    Thread-safe enough for recursive calls (not concurrent threads).
    """
    def __init__(self, limit: Optional[int]):
        self.limit = limit
        self.current = 0
        self._exhausted = False

    def consume(self, amount: int = 1) -> bool:
        """
        Consume 'amount' from budget. 
        Returns True if budget was available (success).
        Returns False if budget is exhausted (should stop).
        """
        if self.limit is None:
            return True
        
        if self._exhausted:
            return False
            
        self.current += amount
        if self.current > self.limit:
            self._exhausted = True
            return False
            
        if self.current == self.limit:
            self._exhausted = True
            
        return True

    def is_exhausted(self) -> bool:
        if self.limit is None:
            return False
        return self._exhausted

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
                 semantic_arrangement_min_cluster: int = 5,
                 semantic_arrangement_method: str = "eom",
                 debug_arrangement: bool = False,
                 skip_nodes: list = None,
                 orphans_label_template: str = "misc",
                 preview_limit: Optional[int] = None,
                 # Advanced Tuning
                 umap_n_neighbors: int = 15,
                 umap_min_dist: float = 0.1,
                 umap_n_components: int = 5,
                 hdbscan_min_samples: Optional[int] = None):
        """
        Initializes the SmartConfig.

        Args:
            enabled (bool): Whether smart pruning is enabled.
            min_depth (int): Minimum WordNet depth for a synset to be considered significant.
            min_hyponyms (int): Minimum number of hyponyms for a synset to be considered significant.
            min_leaf_size (int): Minimum number of items a leaf node must have to not be merged.
            merge_orphans (bool): Whether to merge "orphan" items (those not fitting into any category).
            category_overrides (dict): Specific configuration overrides for certain categories.
            semantic_cleanup (bool): Whether to perform semantic cleanup on categories.
            semantic_model (str): Name of the semantic model to use for embeddings.
            semantic_threshold (float): Similarity threshold for semantic cleanup.
            semantic_arrangement (bool): Whether to semantically arrange items into sub-categories.
            semantic_arrangement_threshold (float): Similarity threshold for semantic arrangement.
            semantic_arrangement_min_cluster (int): Minimum items for a semantic arrangement cluster.
            semantic_arrangement_method (str): Method for semantic arrangement (e.g., "eom").
            debug_arrangement (bool): Show arrangement stats.
            skip_nodes (list): Nodes to structurally skip (elide) while promoting children.
            orphans_label_template (str): Template for orphan categories (e.g. "other_{}").
            preview_limit (int): Max items/nodes to process (Fast Preview). None = unlimited.
            umap_n_neighbors (int): UMAP neighbors (default 15).
            umap_min_dist (float): UMAP min distance (default 0.1).
            umap_n_components (int): UMAP components (default 5).
            hdbscan_min_samples (int): HDBSCAN min samples (default uses min_cluster).
        """
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
        self.semantic_arrangement_method = semantic_arrangement_method
        self.debug_arrangement = debug_arrangement
        self.skip_nodes = set(skip_nodes) if skip_nodes else set()
        self.orphans_label_template = orphans_label_template
        self.preview_limit = preview_limit
        self.umap_n_neighbors = umap_n_neighbors
        self.umap_min_dist = umap_min_dist
        self.umap_n_components = umap_n_components
        self.hdbscan_min_samples = hdbscan_min_samples

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
            semantic_arrangement_min_cluster=override.get('semantic_arrangement_min_cluster', self.semantic_arrangement_min_cluster),
            semantic_arrangement_method=override.get('semantic_arrangement_method', self.semantic_arrangement_method),

            debug_arrangement=override.get('debug_arrangement', self.debug_arrangement),
            skip_nodes=override.get('SKIP_NODES', self.skip_nodes),
            orphans_label_template=override.get('orphans_label_template', self.orphans_label_template),
            
            umap_n_neighbors=override.get('umap_n_neighbors', self.umap_n_neighbors),
            umap_min_dist=override.get('umap_min_dist', self.umap_min_dist),
            umap_n_components=override.get('umap_n_components', self.umap_n_components),
            hdbscan_min_samples=override.get('hdbscan_min_samples', self.hdbscan_min_samples)
        )


# ... (skipping unchanged functions) ...

def apply_semantic_arrangement(
    items: List[str], 
    config: SmartConfig, 
    stats: Optional[Any] = None, 
    context: Optional[str] = None,
    return_metadata: bool = False
) -> Tuple:
    """
    Arrange a list of items into semantic sub-groups.
    Returns the nested structure (dict or list).
    """
    if not config.enabled or not config.semantic_arrangement or not items:
        return ({}, items, {}) if return_metadata else ({}, items)
        
    from .linter import load_embedding_model, check_dependencies
    
    
    if not check_dependencies():
         return ({}, items, {}) if return_metadata else ({}, items)
    
    from .arranger import arrange_hierarchy
    
    # Use recursive arrangement
    result = arrange_hierarchy(
         items,
         max_depth=2, # Configurable?
         max_leaf_size=config.semantic_arrangement_min_cluster, # reuse min cluster?
         # Pass other params via kwargs to arrange_hierarchy if needed?
         model_name=config.semantic_model,
         threshold=config.semantic_arrangement_threshold,
         min_cluster_size=config.semantic_arrangement_min_cluster,
         method=config.semantic_arrangement_method,
         return_metadata=return_metadata,
         # Advanced Tuning
         umap_n_neighbors=config.umap_n_neighbors,
         umap_min_dist=config.umap_min_dist,
         umap_n_components=config.umap_n_components,
         min_samples=config.hdbscan_min_samples
    )
    
    metadata = {}
    if return_metadata and isinstance(result, tuple):
         # arrange_hierarchy might return (result, meta) if we updated it?
         # correctly arrange_hierarchy in arranger.py (lines 482+) does NOT take return_metadata arg for itself, 
         # it takes **kwargs and passes them to arrange_list.
         # BUT arrange_hierarchy returns a purely structural object (dict or list).
         # It does not return native metadata yet.
         # We might lose metadata from the top level call.
         # For now, let's assume we just want the structure.
         pass
         
    return result




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
        
    # 0. Skip List / Force Prune Check
    if config.skip_nodes:
        # Check by name
        # We need the node name? Is 'synset' name?
        # Synset name is like 'entity.n.01', not 'entity'.
        # We rely on exact name match or WNID.
        # However, `synset` object is passed here.
        # Check WNID
        try:
             wnid = get_synset_wnid(synset)
             if wnid and wnid in config.skip_nodes:
                 return True
        except: pass
        
        # Check Name (Lemma)
        if synset:
             # Check lemma names
             for lemma in synset.lemma_names():
                 if lemma in config.skip_nodes or lemma.replace('_', ' ') in config.skip_nodes:
                     return True
    
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

def apply_semantic_cleaning(items: List[str], config: SmartConfig) -> List[str]:
    """
    Clean a list of items using semantic embeddings if enabled.
    Returns the cleaned list.
    """
    if not config.enabled or not config.semantic_cleanup or not items:
        return items
        
    from .linter import load_embedding_model, check_dependencies, clean_list
    
    if not check_dependencies():
        return items
        
    model = load_embedding_model(config.semantic_model)
    cleaned, _ = clean_list(items, model, config.semantic_threshold)
    return cleaned


