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
    smart_config: Any = None
) -> bool:
    """
    Recursively build hierarchy tree from a synset.
    """
    name = get_synset_name(synset)
    
    # Blacklist check
    if blacklist_abstract and is_abstract_category(synset):
        return False
    
    # Strict primary synset check
    if strict_filter:
        primary = get_primary_synset(name)
        if primary and primary != synset:
            return False
            
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
            # Smart Mode: Min leaf size check
            if smart_config and smart_config.enabled:
                if len(descendants) < smart_config.min_leaf_size:
                    # Merge upward (return False to indicate no category created here)
                    # Use add_leaf_list logic but return False?
                    # Wait, if we return False, the parent sees no children.
                    # BUT we want to pass the leaves up.
                    # StructureManager doesn't support "passing up".
                    # We have to just skip creating *this* category, 
                    # but we can't easily merge 20 items into parent's other items in this recursive structure.
                    # Compromise: If heavily pruned, just don't output it?
                    # Or treat it as a leaf node with values.
                    pass
            
            structure_mgr.add_leaf_list(parent, name, descendants, instruction)
            return True
        elif valid_wnids is None or is_in_valid_set(synset, valid_wnids):
            structure_mgr.add_leaf_list(parent, name, [name], instruction)
            return True
        return False
    
    # Branch Logic (Not Flattened)
    if not children:
        # Leaf node
        if valid_wnids is None or is_in_valid_set(synset, valid_wnids):
            structure_mgr.add_leaf_list(parent, name, [name], instruction)
            return True
        return False
    
    # Create category for this node
    child_map = CommentedMap()
    has_valid_children = False
    
    for child in children:
        if build_tree_recursive(
            child, structure_mgr, child_map, valid_wnids,
            depth + 1, max_depth, with_glosses, strict_filter, blacklist_abstract,
            smart_config
        ):
            has_valid_children = True
    
    if has_valid_children:
        parent[name] = child_map
        if instruction:
            try:
                parent.yaml_add_eol_comment(f"instruction: {instruction}", name)
            except Exception:
                pass
        return True
    elif valid_wnids is None or is_in_valid_set(synset, valid_wnids):
        structure_mgr.add_leaf_list(parent, name, [name], instruction)
        return True
    
    return False


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
    merge_orphans: bool = False
) -> CommentedMap:
    """
    Generate ImageNet hierarchy tree from a root synset.
    
    Args:
        root_synset_str: Root synset (e.g., 'animal.n.01', 'entity.n.01')
        max_depth: Maximum depth before flattening
        filter_set: '1k', '21k', or None for all
        with_glosses: Add WordNet glosses as instructions
        strict_filter: Only include primary synset meanings
        blacklist_abstract: Skip abstract categories
        smart: Use semantic significance pruning
        merge_orphans: Merge small pruned lists into parent
    """
    ensure_nltk_data()
    
    from ..smart import SmartConfig
    smart_config = SmartConfig(
        enabled=smart,
        min_depth=min_significance_depth,
        min_hyponyms=min_hyponyms,
        min_leaf_size=min_leaf_size,
        merge_orphans=merge_orphans
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
    
    logger.info(
        f"Building hierarchy from {root_synset_str} "
        f"(depth={max_depth}, filter={filter_set or 'none'})"
    )
    
    structure_mgr = StructureManager()
    result = CommentedMap()
    
    build_tree_recursive(
        root_synset, structure_mgr, result, valid_wnids,
        depth=0, max_depth=max_depth,
        with_glosses=with_glosses,
        strict_filter=strict_filter,
        blacklist_abstract=blacklist_abstract,
        smart_config=smart_config
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
