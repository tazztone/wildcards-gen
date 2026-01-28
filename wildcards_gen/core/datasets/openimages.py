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
from ..wordnet import ensure_nltk_data, get_primary_synset, get_synset_gloss, get_synset_name
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
        next(reader)  # Skip header
        for row in reader:
            if len(row) >= 2:
                id_to_name[row[0]] = row[1]
    
    # Load hierarchy JSON
    with open(hierarchy_path, 'r', encoding='utf-8') as f:
        hierarchy = json.load(f)
    
    return hierarchy, id_to_name


def build_wordnet_hierarchy(
    id_to_name: Dict[str, str],
    structure_mgr: StructureManager,
    with_glosses: bool = True,
    smart_config: Any = None
) -> CommentedMap:
    """
    Build a hierarchy for all labels using WordNet hypernym paths.
    """
    result = CommentedMap()
    
    # Map names to their primary synsets
    # We use a dict to group multiple label IDs that might map to the same synset name
    synset_to_labels = {}
    
    logger.info(f"Mapping {len(id_to_name)} labels to WordNet synsets...")
    for label_id, name in id_to_name.items():
        # Clean name for WordNet lookup
        clean_name = name.lower().replace('/', ' ')
        synset = get_primary_synset(clean_name)
        if synset:
            wnid = f"{synset.pos()}{synset.offset():08d}"
            if wnid not in synset_to_labels:
                synset_to_labels[wnid] = {'synset': synset, 'labels': []}
            synset_to_labels[wnid]['labels'].append(name)
        else:
            # If no synset, add to a catch-all "Other" or root
            if None not in synset_to_labels:
                 # Minimal mock-like synset for things not in WordNet
                 synset_to_labels[None] = {'synset': None, 'labels': []}
            synset_to_labels[None]['labels'].append(name)

    # Now we have synsets for most things. We want to build a tree.
    # To keep it simple and efficient, we'll use the StructureManager's existing logic
    # if we can, but we need a tree structure first.
    
    # Let's group by top-level categories if smart mode is on, 
    # or just build a flat-ish structure grouped by category if not.
    
    # If smart mode is enabled, we can use the synset hierarchy
    if smart_config and smart_config.enabled:
        logger.info("Building dynamic WordNet-based hierarchy...")
        from ..smart import should_prune_node
        
        # Build a temporary tree of synsets
        synset_tree = {} # wnid -> {'parent': wnid, 'children': [wnids], 'labels': [names]}
        
        for wnid, data in synset_to_labels.items():
            synset = data['synset']
            labels = data['labels']
            
            if synset:
                # Find a reasonable parent
                paths = synset.hypernym_paths()
                if paths:
                    # Use the longest path to get the most specific hierarchy
                    path = paths[0]
                    # path is [entity, ..., parent, synset]
                    # We want to register all nodes in the path
                    for i in range(len(path)):
                        curr = path[i]
                        curr_wnid = f"{curr.pos()}{curr.offset():08d}"
                        if curr_wnid not in synset_tree:
                            parent_wnid = None
                            if i > 0:
                                p = path[i-1]
                                parent_wnid = f"{p.pos()}{p.offset():08d}"
                            
                            synset_tree[curr_wnid] = {
                                'synset': curr,
                                'parent': parent_wnid,
                                'children': set(),
                                'labels': []
                            }
                            if parent_wnid:
                                synset_tree[parent_wnid]['children'].add(curr_wnid)
                    
                    # Add labels to the leaf synset
                    curr_wnid = f"{synset.pos()}{synset.offset():08d}"
                    synset_tree[curr_wnid]['labels'].extend(labels)
                else:
                    # No hypernyms? Rare, but add to root
                    if 'root' not in synset_tree:
                        synset_tree['root'] = {'synset': None, 'parent': None, 'children': set(), 'labels': []}
                    synset_tree['root']['labels'].extend(labels)
            else:
                # No synset
                if 'other' not in synset_tree:
                    synset_tree['other'] = {'synset': None, 'parent': None, 'children': set(), 'labels': []}
                synset_tree['other']['labels'].extend(labels)

        # Recursive function to convert synset_tree to CommentedMap
        def build_recursive(wnid, parent_map, depth):
            node = synset_tree[wnid]
            synset = node['synset']
            name = get_synset_name(synset) if synset else wnid.capitalize()
            
            # Smart pruning
            is_root = (depth == 0)
            should_flatten = should_prune_node(
                synset=synset,
                child_count=len(node['children']),
                is_root=is_root,
                config=smart_config
            )
            
            instruction = get_synset_gloss(synset) if synset and with_glosses else None
            
            if should_flatten:
                # Collect all labels in this subtree
                all_labels = []
                def collect_labels(w):
                    n = synset_tree[w]
                    all_labels.extend(n['labels'])
                    for child in n['children']:
                        collect_labels(child)
                collect_labels(wnid)
                
                if all_labels:
                    structure_mgr.add_leaf_list(parent_map, name, sorted(list(set(all_labels))), instruction)
            else:
                # Create category
                child_map = CommentedMap()
                # Sort children by name
                sorted_children = sorted(list(node['children']), key=lambda w: get_synset_name(synset_tree[w]['synset']) if synset_tree[w]['synset'] else w)
                
                for child_wnid in sorted_children:
                    build_recursive(child_wnid, child_map, depth + 1)
                
                # Add labels directly attached to this synset as a "Misc" or similar?
                # Actually, in WordNet, labels are usually at the leaves.
                # If there are labels here, add them.
                if node['labels']:
                    structure_mgr.add_leaf_list(child_map, f"Other {name}", sorted(node['labels']), f"Additional {name} items")
                
                if child_map:
                    parent_map[name] = child_map
                    if instruction:
                        try:
                            parent_map.yaml_add_eol_comment(f"instruction: {instruction}", name)
                        except Exception:
                            pass
        
        # Start from roots (nodes with parent None)
        roots = [wnid for wnid, n in synset_tree.items() if n['parent'] is None]
        for root in sorted(roots):
            build_recursive(root, result, 0)
            
    else:
        # Simple mode: Group by first letter or just one big list?
        # Let's at least group by first WordNet parent if possible, otherwise flat.
        logger.info("Building flat-ish hierarchy for full labels...")
        all_labels = []
        for wnid, data in synset_to_labels.items():
            all_labels.extend(data['labels'])
        
        structure_mgr.add_leaf_list(result, "OpenImages Full", sorted(all_labels), "All 20k+ Open Images labels")

    return result


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
    merge_orphans: bool = False,
    bbox_only: bool = False
) -> CommentedMap:
    """
    Generate hierarchy from Open Images dataset.
    
    Args:
        max_depth: Maximum hierarchy depth before flattening
        with_glosses: Add WordNet glosses as instructions
        smart: Use semantic significance pruning
        merge_orphans: Merge small pruned lists into parent
        bbox_only: Use only the 600 bounding-box labels (legacy mode)
        
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
    
    if bbox_only:
        logger.info("Using legacy BBox mode (600 labels)")
        hierarchy, id_to_name = load_openimages_data()
        
        structure_mgr = StructureManager()
        result = CommentedMap()
        
        # Start from root and parse recursively
        parse_hierarchy_node(
            hierarchy, id_to_name, structure_mgr, result,
            depth=0, max_depth=max_depth, with_glosses=with_glosses,
            smart_config=smart_config
        )
    else:
        logger.info("Using full image-level mode (20k+ labels)")
        _, id_to_name = load_openimages_data()
        
        structure_mgr = StructureManager()
        result = build_wordnet_hierarchy(
            id_to_name, structure_mgr, 
            with_glosses=with_glosses, 
            smart_config=smart_config
        )
    
    return result
