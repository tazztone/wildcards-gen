"""
ImageNet dataset hierarchy generator.

Generates skeleton YAML from ImageNet classes with WordNet glosses
as # instruction: comments.

Supports:
- Tree mode: Top-down from any root synset
- WNID mode: Bottom-up from specific WNIDs
- Filtering: ImageNet-1k or ImageNet-21k subsets
"""

import json
import functools
import logging
from typing import Dict, List, Optional, Set, Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ..structure import StructureManager
from ..wordnet import (
    ensure_nltk_data, get_synset_from_wnid, get_primary_synset,
    get_synset_name, get_synset_gloss, get_synset_wnid,
    is_in_valid_set, get_all_descendants, is_abstract_category
)
from ..presets import DATASET_CATEGORY_OVERRIDES
from .downloaders import ensure_imagenet_1k_data, ensure_imagenet_21k_data

try:
    from nltk.corpus import wordnet as wn
except ImportError:
    wn = None

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def load_imagenet_1k_wnids() -> Set[str]:
    """Load the set of ImageNet-1k WNIDs."""
    logger.info("Loading ImageNet-1k class list...")
    list_path = ensure_imagenet_1k_data()
    try:
        with open(list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        valid_wnids = set()
        for key, value in data.items():
            if isinstance(value, list) and len(value) >= 1:
                valid_wnids.add(value[0])
        return valid_wnids
    except Exception as e:
        logger.error(f"Failed to load ImageNet-1k WNIDs: {e}")
        return set()


@functools.lru_cache(maxsize=1)
def load_imagenet_21k_wnids() -> Set[str]:
    """Load the set of ImageNet-21k WNIDs."""
    logger.info("Loading ImageNet-21k class list...")
    ids_path, _ = ensure_imagenet_21k_data()
    wnids = set()
    try:
        with open(ids_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    wnids.add(line)
    except Exception as e:
        logger.error(f"Failed to load ImageNet-21k WNIDs: {e}")
    return wnids


def build_tree_recursive(
    synset,
    structure_mgr: StructureManager,
    parent: CommentedMap,
    valid_wnids: Optional[Set[str]],
    depth: int,
    max_depth: int,
    with_glosses: bool = True,
    strict_filter: bool = True,
    blacklist_abstract: bool = False,
    smart_config: Any = None,
    regex_list: List[Any] = None,
    excluded_synsets: Set[Any] = None
) -> tuple:
    """
    Recursively build hierarchy tree from a synset.
    
    Returns:
        Tuple[bool, List[str]]: (success, orphans_to_bubble_up)
    """
    name = get_synset_name(synset)
    
    # 1. Subtree Exclusion Check
    if excluded_synsets and synset in excluded_synsets:
        return (False, [])
        
    # 2. Regex Exclusion Check
    if regex_list:
        for pattern in regex_list:
            if pattern.search(name):
                return (False, [])
    
    # Blacklist check
    if blacklist_abstract and is_abstract_category(synset):
        return (False, [])
    
    # Strict primary synset check
    if strict_filter:
        primary = get_primary_synset(name)
        if primary and primary != synset:
            return (False, [])
            
    # Get instruction from gloss
    instruction = get_synset_gloss(synset) if with_glosses else None
    
    children = synset.hyponyms()
    
    # Determine if we should prune (flatten) at this level
    should_flatten = False
    
    if smart_config and smart_config.enabled:
        from ..smart import should_prune_node
        # ImageNet root is depth 0
        is_root = (depth == 0)
        should_flatten = should_prune_node(
            synset=synset,
            child_count=len(children),
            is_root=is_root,
            config=smart_config
        )
    else:
        # Traditional depth limit
        if depth >= max_depth:
            should_flatten = True

    # Flatten logic
    if should_flatten:
        descendants = get_all_descendants(synset, valid_wnids)
        if descendants:
            # Smart Mode: Semantic Cleaning
            if smart_config and smart_config.enabled and smart_config.semantic_cleanup:
                from ..smart import apply_semantic_cleaning
                descendants = apply_semantic_cleaning(descendants, smart_config)

            # Smart Mode: Semantic Arrangement (Re-grow)
            # If we flattened a potentially large list, try to re-group meaningful parts
            if smart_config and smart_config.enabled and smart_config.semantic_arrangement:
                from ..smart import apply_semantic_arrangement
                named_groups, leftovers = apply_semantic_arrangement(descendants, smart_config)
                
                # Add named groups as sub-categories
                for group_name, terms in named_groups.items():
                    # We create a simple leaf list for each group
                    # Instruction? Maybe "semantically grouped terms from {name}"?
                    # For now, no specific instruction, just the terms.
                    structure_mgr.add_leaf_list(parent, group_name, terms, f"instruction: items related to {group_name}")
                
                # Replace descendants with leftovers for the main list
                descendants = leftovers

            # Smart Mode: Min leaf size check with orphan bubbling
            if smart_config and smart_config.enabled:
                if len(descendants) < smart_config.min_leaf_size:
                    if smart_config.merge_orphans:
                        # Bubble up as orphans
                        return (False, descendants)
                    # Otherwise, keep as small list (100% retention)
            
            if descendants:
                structure_mgr.add_leaf_list(parent, name, descendants, instruction)
            return (True, [])
        elif valid_wnids is None or is_in_valid_set(synset, valid_wnids):
            structure_mgr.add_leaf_list(parent, name, [name], instruction)
            return (True, [])
        return (False, [])
    
    # Branch Logic (Not Flattened)
    if not children:
        # Leaf node
        if valid_wnids is None or is_in_valid_set(synset, valid_wnids):
            structure_mgr.add_leaf_list(parent, name, [name], instruction)
            return (True, [])
        return (False, [])
    
    # Create category for this node
    child_map = CommentedMap()
    has_valid_children = False
    collected_orphans = []
    
    for child in children:
        # Determine child-specific config
        child_config = smart_config
        if smart_config and smart_config.enabled:
             child_name_simple = get_synset_name(child)
             child_wnid = get_synset_wnid(child)
             child_config = smart_config.get_child_config(child_name_simple, child_wnid)

        success, orphans = build_tree_recursive(
            child, structure_mgr, child_map, valid_wnids,
            depth + 1, max_depth, with_glosses, strict_filter, blacklist_abstract,
            child_config, regex_list, excluded_synsets
        )
        if success:
            has_valid_children = True
        if orphans:
            collected_orphans.extend(orphans)
    
    # Handle collected orphans - add to misc key
    if collected_orphans and smart_config and smart_config.merge_orphans:
        collected_orphans = sorted(list(set(collected_orphans)))
        
        # Semantic Cleaning for Orphans
        if smart_config.semantic_cleanup:
            from ..smart import apply_semantic_cleaning
            collected_orphans = apply_semantic_cleaning(collected_orphans, smart_config)

        # Semantic Arrangement for Orphans (Misc)
        if smart_config.semantic_arrangement:
            from ..smart import apply_semantic_arrangement
            named_groups, leftovers = apply_semantic_arrangement(collected_orphans, smart_config)
            
            # Add named groups as peer categories to 'misc'
            for group_name, terms in named_groups.items():
                structure_mgr.add_leaf_list(child_map, group_name, terms, f"instruction: items related to {group_name}")
            
            # Leftovers become the new misc
            collected_orphans = leftovers

        if collected_orphans: # Only add misc if there are still items
            if 'misc' in child_map:
                # Merge with existing misc
                existing = list(child_map['misc']) if child_map['misc'] else []
                child_map['misc'] = sorted(list(set(existing + collected_orphans)))
            else:
                child_map['misc'] = collected_orphans
        has_valid_children = True
    
    if has_valid_children:
        parent[name] = child_map
        if instruction:
            try:
                parent.yaml_add_eol_comment(f"instruction: {instruction}", name)
            except Exception:
                pass
        return (True, [])
    elif valid_wnids is None or is_in_valid_set(synset, valid_wnids):
        structure_mgr.add_leaf_list(parent, name, [name], instruction)
        return (True, [])
    
    return (False, [])


def generate_imagenet_tree(
    root_synset_str: str = "entity.n.01",
    max_depth: int = 4,
    filter_set: Optional[str] = None,
    with_glosses: bool = True,
    strict_filter: bool = True,
    blacklist_abstract: bool = False,
    smart: bool = False,
    min_significance_depth: int = 6,
    min_hyponyms: int = 10,
    min_leaf_size: int = 3,
    merge_orphans: bool = False,
    exclude_regex: Optional[List[str]] = None,
    exclude_subtree: Optional[List[str]] = None,
    smart_overrides: Optional[Dict] = None,
    semantic_cleanup: bool = False,
    semantic_model: str = "minilm",
    semantic_threshold: float = 0.1,
    semantic_arrangement: bool = False,
    semantic_arrangement_threshold: float = 0.1,
    semantic_arrangement_min_cluster: int = 5
) -> CommentedMap:
    """
    Generate ImageNet hierarchy tree from a root synset.
    
    Args:
        root_synset_str: Root synset (e.g., 'entity.n.01', 'animal.n.01')
        max_depth: Maximum depth before flattening
        filter_set: '1k', '21k', or None for all
        with_glosses: Add WordNet glosses as instructions
        strict_filter: Only include primary synset meanings
        blacklist_abstract: Skip abstract categories
        smart: Use semantic significance pruning
        merge_orphans: Merge small pruned lists into parent
        exclude_regex: Regex patterns to exclude by name
        exclude_subtree: Synset names/WNIDs to prune entire subtrees
        smart_overrides: Dictionary of per-category smart config overrides
        semantic_cleanup: Enable semantic outlier detection
        semantic_model: Model to use for cleaning/arrangement
        semantic_threshold: Threshold for cleaning
        semantic_arrangement: Enable semantic clustering
        semantic_arrangement_threshold: Threshold for clustering
        semantic_arrangement_min_cluster: Min cluster size
    """
    ensure_nltk_data()
    
    # Determine overrides (CLI/Args > Preset)
    preset_overrides = DATASET_CATEGORY_OVERRIDES.get("ImageNet", {})
    final_overrides = preset_overrides.copy()
    if smart_overrides:
        final_overrides.update(smart_overrides)

    from ..smart import SmartConfig
    smart_config = SmartConfig(
        enabled=smart,
        min_depth=min_significance_depth,
        min_hyponyms=min_hyponyms,
        min_leaf_size=min_leaf_size,
        merge_orphans=merge_orphans,
        category_overrides=final_overrides,
        semantic_cleanup=semantic_cleanup,
        semantic_model=semantic_model,
        semantic_threshold=semantic_threshold,
        semantic_arrangement=semantic_arrangement,
        semantic_arrangement_threshold=semantic_arrangement_threshold,
        semantic_arrangement_min_cluster=semantic_arrangement_min_cluster
    )
    
    # Load filter set
    valid_wnids = None
    if filter_set == '1k':
        valid_wnids = load_imagenet_1k_wnids()
    elif filter_set == '21k':
        valid_wnids = load_imagenet_21k_wnids()
    
    # Get root synset
    try:
        root_synset = wn.synset(root_synset_str)
    except Exception:
        logger.error(f"Could not find root synset: {root_synset_str}")
        return CommentedMap()
        
    # Prepare exclusions
    import re
    regex_list = [re.compile(r) for r in exclude_regex] if exclude_regex else []
    
    excluded_synsets = set()
    if exclude_subtree:
        for s_str in exclude_subtree:
            try:
                # Try as WNID first
                if s_str.startswith('n') and len(s_str) > 5 and s_str[1:].isdigit():
                    s = get_synset_from_wnid(s_str)
                else:
                    s = wn.synset(s_str)
                
                if s:
                    excluded_synsets.add(s)
                else:
                    logger.warning(f"Could not resolve excluded subtree: {s_str}")
            except Exception:
                logger.warning(f"Could not resolve excluded subtree: {s_str}")
    
    logger.info(
        f"Building hierarchy from {root_synset_str} "
        f"(depth={max_depth}, filter={filter_set or 'none'})"
    )
    
    structure_mgr = StructureManager()
    result = CommentedMap()
    
    # We pass exclusions to build_tree_recursive via a context object or added args
    # For now, let's update build_tree_recursive signature first or wrap it
    
    build_tree_recursive(
        root_synset, structure_mgr, result, valid_wnids,
        depth=0, max_depth=max_depth,
        with_glosses=with_glosses,
        strict_filter=strict_filter,
        blacklist_abstract=blacklist_abstract,
        smart_config=smart_config,
        regex_list=regex_list,
        excluded_synsets=excluded_synsets
    )
    
    return result


def generate_imagenet_from_wnids(
    wnids: List[str],
    max_depth: int = 10,
    max_hypernym_depth: Optional[int] = None,
    with_glosses: bool = True
) -> CommentedMap:
    """
    Generate hierarchy bottom-up from a list of WNIDs.
    
    Args:
        wnids: List of WordNet IDs (e.g., ['n02084071', 'n02121808'])
        max_depth: Maximum output depth
        max_hypernym_depth: Limit on hypernym chain length
        with_glosses: Add WordNet glosses as instructions
        
    Returns:
        CommentedMap with the hierarchy
    """
    ensure_nltk_data()
    
    if not wnids:
        return CommentedMap()
    
    logger.info(f"Processing {len(wnids)} WNIDs (bottom-up)...")
    
    structure_mgr = StructureManager()
    
    # Build raw tree from hypernym paths
    raw_tree: Dict[str, Any] = {}
    
    for wnid in wnids:
        synset = get_synset_from_wnid(wnid)
        if not synset:
            continue
        
        paths = synset.hypernym_paths()
        if not paths:
            continue
        
        # Use primary path
        primary_path = paths[0]
        
        # Apply hypernym depth limit
        if max_hypernym_depth is not None and max_hypernym_depth > 0:
            path_to_use = primary_path[-max_hypernym_depth:]
        else:
            path_to_use = primary_path
        
        current = raw_tree
        for node in path_to_use:
            node_name = get_synset_name(node)
            if node_name not in current:
                current[node_name] = {}
            current = current[node_name]
    
    # Convert to CommentedMap with glosses
    def convert_tree(tree: dict, depth: int) -> CommentedMap:
        result = CommentedMap()
        
        for key, value in tree.items():
            if depth >= max_depth or not value:
                # Flatten: collect all leaves
                leaves = collect_leaves(value) if value else [key]
                if not leaves:
                    leaves = [key]
                seq = CommentedSeq(sorted(set(leaves)))
                result[key] = seq
            else:
                result[key] = convert_tree(value, depth + 1)
            
            # Add gloss
            if with_glosses:
                synset = get_primary_synset(key)
                if synset:
                    try:
                        result.yaml_add_eol_comment(
                            f"instruction: {get_synset_gloss(synset)}", key
                        )
                    except Exception:
                        pass
        
        return result
    
    def collect_leaves(tree: dict) -> List[str]:
        leaves = []
        for key, value in tree.items():
            if not value:
                leaves.append(key)
            else:
                leaves.extend(collect_leaves(value))
        return leaves
    
    return convert_tree(raw_tree, 0)
