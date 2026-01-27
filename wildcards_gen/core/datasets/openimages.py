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
    with_glosses: bool = True
) -> None:
    """
    Recursively parse an Open Images hierarchy node.
    
    FIXED: Properly preserves subcategory structure instead of flattening.
    """
    label_id = node.get('LabelName')
    name = id_to_name.get(label_id, label_id)
    
    # Handle the root entity specially
    if label_id == '/m/0bl9f' and name == label_id:
        name = 'Entity'
    
    # Get instruction
    instruction = get_openimages_gloss(name) if with_glosses else None
    
    # Check for subcategories
    sub_key = None
    if 'Subcategory' in node:
        sub_key = 'Subcategory'
    elif 'Subcategories' in node:
        sub_key = 'Subcategories'
    
    if sub_key and depth < max_depth:
        # Has children - create nested structure
        subcats = node[sub_key]
        child_map = CommentedMap()
        
        for subcat in subcats:
            parse_hierarchy_node(
                subcat, id_to_name, structure_mgr, child_map,
                depth + 1, max_depth, with_glosses
            )
        
        if child_map:
            parent[name] = child_map
            if instruction:
                try:
                    parent.yaml_add_eol_comment(f"instruction: {instruction}", name)
                except Exception:
                    pass
        else:
            # No valid children, make it a leaf
            structure_mgr.add_leaf_list(parent, name, [name], instruction)
    
    elif sub_key and depth >= max_depth:
        # At max depth: flatten all descendants
        leaves = collect_leaves_from_node(node, id_to_name)
        if leaves:
            structure_mgr.add_leaf_list(parent, name, leaves, instruction)
        else:
            structure_mgr.add_leaf_list(parent, name, [name], instruction)
    
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
    with_glosses: bool = True
) -> CommentedMap:
    """
    Generate hierarchy from Open Images dataset.
    
    Args:
        max_depth: Maximum hierarchy depth before flattening
        with_glosses: Add WordNet glosses as instructions
        
    Returns:
        CommentedMap with the hierarchy
    """
    ensure_nltk_data()
    
    logger.info("Generating Open Images hierarchy...")
    hierarchy, id_to_name = load_openimages_data()
    
    structure_mgr = StructureManager()
    result = CommentedMap()
    
    # Start from root and parse recursively
    parse_hierarchy_node(
        hierarchy, id_to_name, structure_mgr, result,
        depth=0, max_depth=max_depth, with_glosses=with_glosses
    )
    
    return result
