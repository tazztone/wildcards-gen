"""
Open Images dataset hierarchy generator.

Generates skeleton YAML from Open Images hierarchy with WordNet glosses
as # instruction: comments.

NOTE: This fixes the flat output issue from the original Hierarchy-Generator
by properly preserving the subcategory structure.
"""

import json
import csv
import functools
import logging
from typing import Dict, Tuple, Any, Optional

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ..structure import StructureManager
from ..wordnet import ensure_nltk_data, get_primary_synset, get_synset_gloss
from .downloaders import ensure_openimages_data

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def load_openimages_data() -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Load Open Images hierarchy and class descriptions."""
    hierarchy_path, classes_path = ensure_openimages_data()
    
    # Load class descriptions (ID -> Name)
    id_to_name = {}
    with open(classes_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                id_to_name[row[0]] = row[1]
    
    # Load hierarchy JSON
    with open(hierarchy_path, 'r', encoding='utf-8') as f:
        hierarchy = json.load(f)
    
    return hierarchy, id_to_name


def get_openimages_gloss(name: str) -> str:
    """Get WordNet gloss for an Open Images category."""
    synset = get_primary_synset(name.lower())
    if synset:
        return get_synset_gloss(synset)
    return f"Items related to {name}"


def parse_hierarchy_node(
    node: Dict[str, Any],
    id_to_name: Dict[str, str],
    structure_mgr: StructureManager,
    parent: CommentedMap,
    depth: int,
    max_depth: int,
    with_glosses: bool = True,
    smart_config: Any = None
) -> None:
    """
    Recursively parse an Open Images hierarchy node.
    """
    label_id = node.get('LabelName')
    name = id_to_name.get(label_id, label_id)
    
    # Handle the root entity specially
    if label_id == '/m/0bl9f' and name == label_id:
        name = 'Entity'
        
    # Check for subcategories
    sub_key = None
    if 'Subcategory' in node:
        sub_key = 'Subcategory'
    elif 'Subcategories' in node:
        sub_key = 'Subcategories'
        
    child_nodes = node.get(sub_key, []) if sub_key else []
    
    # Get instruction and Synset (for Smart Mode)
    instruction = None
    synset = None
    
    # Try to resolve to WordNet
    synset = get_primary_synset(name.lower())
    if synset:
        instruction = get_synset_gloss(synset) if with_glosses else None
    else:
        # Fallback instruction
        if with_glosses:
            instruction = f"Items related to {name}"
    
    # Determine pruning
    should_flatten = False
    
    if smart_config and smart_config.enabled:
        from ..smart import should_prune_node
        is_root = (depth == 0)
        should_flatten = should_prune_node(
            synset=synset,
            child_count=len(child_nodes),
            is_root=is_root,
            config=smart_config
        )
    else:
        # Traditional depth check
        if depth >= max_depth:
            should_flatten = True

    # Branch 1: Keep as Category
    if sub_key and not should_flatten:
        # Has children - create nested structure
        child_map = CommentedMap()
        
        valid_children_count = 0
        for subcat in child_nodes:
            parse_hierarchy_node(
                subcat, id_to_name, structure_mgr, child_map,
                depth + 1, max_depth, with_glosses, smart_config
            )
            valid_children_count += 1
        
        # If all children were pruned away/merged, we might become empty.
        # But StructureManager logic in sub-calls handles adding to our child_map.
        
        if child_map:
            parent[name] = child_map
            if instruction:
                try:
                    parent.yaml_add_eol_comment(f"instruction: {instruction}", name)
                except Exception:
                    pass
        else:
            # If we became empty (e.g. all children filtered), enforce leaf rule?
            # OpenImages is explicit, so we usually just fallback to treating self as leaf.
            structure_mgr.add_leaf_list(parent, name, [name], instruction)
            
    # Branch 2: Flatten / Prune
    elif sub_key and should_flatten:
        # Flatten all descendants
        leaves = collect_leaves_from_node(node, id_to_name)
        
        # Smart Mode: Min leaf check
        if smart_config and smart_config.enabled:
             if len(leaves) < smart_config.min_leaf_size:
                 return # Skip entirely (merge up)
        
        if leaves:
            structure_mgr.add_leaf_list(parent, name, leaves, instruction)
        else:
            structure_mgr.add_leaf_list(parent, name, [name], instruction)
    
    # Branch 3: Leaf Node
    else:
        # Leaf node
        structure_mgr.add_leaf_list(parent, name, [name], instruction)


def collect_leaves_from_node(
    node: Dict[str, Any],
    id_to_name: Dict[str, str]
) -> list:
    """Collect all leaf names from a node tree."""
    leaves = []
    
    sub_key = None
    if 'Subcategory' in node:
        sub_key = 'Subcategory'
    elif 'Subcategories' in node:
        sub_key = 'Subcategories'
    
    if sub_key:
        for subcat in node[sub_key]:
            leaves.extend(collect_leaves_from_node(subcat, id_to_name))
    else:
        label_id = node.get('LabelName')
        name = id_to_name.get(label_id, label_id)
        if name and name != label_id:  # Only add if we have a proper name
            leaves.append(name)
    
    return sorted(set(leaves))


def generate_openimages_hierarchy(
    max_depth: int = 4,
    with_glosses: bool = True,
    smart: bool = False,
    min_significance_depth: int = 6,
    min_hyponyms: int = 10,
    min_leaf_size: int = 3,
    merge_orphans: bool = False
) -> CommentedMap:
    """
    Generate hierarchy from Open Images dataset.
    
    Args:
        max_depth: Maximum hierarchy depth before flattening
        with_glosses: Add WordNet glosses as instructions
        smart: Use semantic significance pruning
        merge_orphans: Merge small pruned lists into parent
        
    Returns:
        CommentedMap with the hierarchy
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
    
    logger.info("Generating Open Images hierarchy...")
    hierarchy, id_to_name = load_openimages_data()
    
    structure_mgr = StructureManager()
    result = CommentedMap()
    
    # Start from root and parse recursively
    parse_hierarchy_node(
        hierarchy, id_to_name, structure_mgr, result,
        depth=0, max_depth=max_depth, with_glosses=with_glosses,
        smart_config=smart_config
    )
    
    return result
