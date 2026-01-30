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
from typing import Dict, List, Tuple, Any, Optional

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ..structure import StructureManager
from ..wordnet import ensure_nltk_data, get_primary_synset, get_synset_gloss, get_synset_name
from .downloaders import ensure_openimages_data
from ..smart import should_prune_node, apply_semantic_cleaning, apply_semantic_arrangement

logger = logging.getLogger(__name__)



# Manual cache for OpenImages data
_OPENIMAGES_CACHE = None

def load_openimages_data(progress_callback=None) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Load Open Images hierarchy and class descriptions."""
    global _OPENIMAGES_CACHE
    if _OPENIMAGES_CACHE is not None:
        return _OPENIMAGES_CACHE

    hierarchy_path, classes_path = ensure_openimages_data(progress_callback=progress_callback)
    
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
    
    _OPENIMAGES_CACHE = (hierarchy, id_to_name)
    return hierarchy, id_to_name


# Helper for dynamic hierarchy build
@functools.lru_cache(maxsize=1)
def _get_cached_synset_tree() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Cached worker to build the synset tree structure.
    Returns (synset_to_labels, synset_tree).
    """
    # 1. Load Data (Already Cached)
    _, id_to_name = load_openimages_data()
    
    # 2. Map names to synsets
    synset_to_labels = {}
    logger.info(f"Mapping {len(id_to_name)} labels to WordNet synsets (First Run Only)...")
    
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
                 synset_to_labels[None] = {'synset': None, 'labels': []}
            synset_to_labels[None]['labels'].append(name)

    # 3. Build Tree
    logger.info("Building dynamic WordNet-based hierarchy (First Run Only)...")
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
            
    return synset_to_labels, synset_tree

def build_wordnet_hierarchy(
    id_to_name: Dict[str, str],
    structure_mgr: StructureManager,
    with_glosses: bool = True,
    smart_config: Any = None,
    stats: Optional[Any] = None,
    budget: Optional = None
) -> CommentedMap:
    """
    Build a hierarchy for all labels using WordNet hypernym paths.
    """
    result = CommentedMap()
    
    # If smart mode is enabled, we uses the pre-computed tree
    if smart_config and smart_config.enabled:
        # Uses cached tree structure
        synset_to_labels, synset_tree = _get_cached_synset_tree()
        

        # Recursive function to convert synset_tree to CommentedMap
        def build_recursive(wnid, parent_map, depth, stats=stats, budget=budget):
            """Returns (success, orphans) tuple."""
            if budget and not budget.consume(1):
                if budget.is_exhausted() and stats:
                    stats.log_event("limit_reached", message=f"Traversal limit {budget.limit} reached during build_recursive", data={"limit": budget.limit})
                return (False, [])
            
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
                    unique_labels = sorted(list(set(all_labels)))
                    
                    # Semantic Cleaning
                    if smart_config.semantic_cleanup:
                        unique_labels = apply_semantic_cleaning(unique_labels, smart_config)

                    # Min leaf size check with orphan bubbling
                    if len(unique_labels) < smart_config.min_leaf_size:
                        if smart_config.merge_orphans:
                            return (False, unique_labels)
                        # Otherwise keep as small list
                        pass
                    
                    # Semantic Arrangement (Re-grow)
                    
                    # Semantic Arrangement (Re-grow)
                    if smart_config.semantic_arrangement:
                        arranged_structure, leftovers = apply_semantic_arrangement(unique_labels, smart_config, stats=stats, context=name)
                         
                        if arranged_structure:
                            # Created a sub-hierarchy.
                            # Merge into a temp node first to convert to StructureManager format?
                            
                            # Create a temp map for 'name'
                            temp_node = structure_mgr.create_empty_structure()
                            
                            # DEBUG/GUARD: Ensure structure is merged type
                            if hasattr(arranged_structure, 'items'):
                                try:
                                    structure_mgr.merge_categorized_data(temp_node, arranged_structure)
                                except AttributeError as e:
                                    logger.error(f"Failed to merge structure for {name}: {e}")
                                    raise e
                            else:
                                # Fallback or Logic Error: Treating as list/leaf?
                                # This can happen if arrange returns a single string or list instead of dict.
                                logger.warning(f"arranged_structure for {name} is not dict: {type(arranged_structure)}")
                                if isinstance(arranged_structure, list):
                                     structure_mgr.add_leaf_list(temp_node, "misc", arranged_structure)
                            
                            parent_map[name] = temp_node
                            if instruction:
                                try:
                                    parent_map.yaml_add_eol_comment(f"instruction: {instruction}", name)
                                except Exception: pass
                            
                            if leftovers:
                                structure_mgr.add_leaf_list(temp_node, "misc", leftovers, "Other items")

                        else:
                            # No structure found, just add flat list
                            structure_mgr.add_leaf_list(parent_map, name, unique_labels, instruction)
                        
                    else:
                        structure_mgr.add_leaf_list(parent_map, name, unique_labels, instruction)
                        
                    return (True, [])

                return (False, [])
            else:
                # Create category
                child_map = CommentedMap()
                collected_orphans = []
                # Sort children by name
                sorted_children = sorted(list(node['children']), key=lambda w: get_synset_name(synset_tree[w]['synset']) if synset_tree[w]['synset'] else w)
                
                has_valid_children = False
                for child_wnid in sorted_children:
                    success, orphans = build_recursive(child_wnid, child_map, depth + 1, stats=stats, budget=budget)
                    if success:
                        has_valid_children = True
                    if orphans:
                        collected_orphans.extend(orphans)
                
                # Handle collected orphans - add to misc key
                if collected_orphans and smart_config.merge_orphans:
                    collected_orphans = sorted(list(set(collected_orphans)))
                    
                    # Semantic Cleaning for orphans
                    if smart_config.semantic_cleanup:
                        collected_orphans = apply_semantic_cleaning(collected_orphans, smart_config)

                    # Semantic Arrangement for Orphans
                    if smart_config.semantic_arrangement:
                        arranged_orphans, leftovers = apply_semantic_arrangement(collected_orphans, smart_config, stats=stats, context=f"orphans of {name}")
                        
                        if arranged_orphans:
                            # We have groups for the orphans.
                            # Merge them into child_map (siblings).
                            try:
                                structure_mgr.merge_categorized_data(child_map, arranged_orphans)
                            except AttributeError as e:
                                logger.error(f"Failed to merge orphans for {name}: {e}")
                                raise e
                            collected_orphans = leftovers # Only keep leftovers as orphans
                        else:
                            # Still a flat list
                            collected_orphans = leftovers


                    if 'misc' in child_map:
                        existing = list(child_map['misc']) if child_map['misc'] else []
                        child_map['misc'] = sorted(list(set(existing + collected_orphans)))
                    else:
                        child_map['misc'] = collected_orphans
                    has_valid_children = True
                
                # Add labels directly attached to this synset
                if node['labels']:
                    local_labels = sorted(node['labels'])
                    if smart_config.semantic_cleanup:
                        local_labels = apply_semantic_cleaning(local_labels, smart_config)
                    
                    if local_labels:
                         structure_mgr.add_leaf_list(child_map, f"Other {name}", local_labels, f"Additional {name} items")
                         has_valid_children = True
                
                if has_valid_children and child_map:
                    parent_map[name] = child_map
                    if instruction:
                        try:
                            parent_map.yaml_add_eol_comment(f"instruction: {instruction}", name)
                        except Exception:
                            pass
                    return (True, [])
                return (False, [])
        
        # Start from roots (nodes with parent None)
        roots = [wnid for wnid, n in synset_tree.items() if n['parent'] is None]
        for root in sorted(roots):
            build_recursive(root, result, 0, stats=stats, budget=budget)
            
    else:
        # Simple mode: Group by first letter or just one big list?
        # Let's at least group by first WordNet parent if possible, otherwise flat.
        logger.info("Building flat-ish hierarchy for full labels...")
        
        synset_to_labels, _ = _get_cached_synset_tree()
        
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
    smart_config: Any = None,
    stats: Optional[Any] = None,
    budget: Optional = None
) -> tuple:
    """
    Recursively parse an Open Images hierarchy node.
    
    Returns:
        Tuple[bool, List[str]]: (success, orphans_to_bubble_up)
    """
    if budget and not budget.consume(1):
        if budget.is_exhausted() and stats:
            stats.log_event("limit_reached", message=f"Traversal limit {budget.limit} reached during parse_hierarchy_node", data={"limit": budget.limit})
        return (False, [])

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
        collected_orphans = []
        
        has_valid_children = False
        for subcat in child_nodes:
            success, orphans = parse_hierarchy_node(
                subcat, id_to_name, structure_mgr, child_map,
                depth + 1, max_depth, with_glosses, smart_config, stats=stats, budget=budget
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
                collected_orphans = apply_semantic_cleaning(collected_orphans, smart_config)

            if 'misc' in child_map:
                existing = list(child_map['misc']) if child_map['misc'] else []
                child_map['misc'] = sorted(list(set(existing + collected_orphans)))
            else:
                child_map['misc'] = collected_orphans
            has_valid_children = True
        
        if has_valid_children and child_map:
            parent[name] = child_map
            if instruction:
                try:
                    parent.yaml_add_eol_comment(f"instruction: {instruction}", name)
                except Exception:
                    pass
            return (True, [])
        else:
            # If we became empty, treat self as leaf
            leaves = [name]
            if smart_config and smart_config.enabled and smart_config.semantic_cleanup:
                # Should we clean a single item list? Usually safe, but apply for consistency
                # Wait, 'name' is the category name. If it became empty, we use the category name as a leaf.
                # It's not a list of children. It is valid.
                pass
            structure_mgr.add_leaf_list(parent, name, leaves, instruction)
            return (True, [])
            
    # Branch 2: Flatten / Prune
    elif sub_key and should_flatten:
        # Flatten all descendants
        leaves = collect_leaves_from_node(node, id_to_name)
        
        # Smart Mode: Min leaf check with orphan bubbling
        if smart_config and smart_config.enabled:
            # Semantic Cleaning
            if smart_config.semantic_cleanup:
                 leaves = apply_semantic_cleaning(leaves, smart_config)

            if len(leaves) < smart_config.min_leaf_size:
                if smart_config.merge_orphans:
                    return (False, leaves)
                # Otherwise keep as small list
        
        if leaves:
            structure_mgr.add_leaf_list(parent, name, leaves, instruction)
        else:
            # If cleaning removed everything, or it was empty
            structure_mgr.add_leaf_list(parent, name, [name], instruction)
        return (True, [])
    
    # Branch 3: Leaf Node
    else:
        # Leaf node
        structure_mgr.add_leaf_list(parent, name, [name], instruction)
        return (True, [])


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
    bbox_only: bool = False,
    semantic_cleanup: bool = False,
    semantic_model: str = "minilm",
    semantic_threshold: float = 0.1,
    semantic_arrangement: bool = False,
    semantic_arrangement_threshold: float = 0.1,
    semantic_arrangement_min_cluster: int = 5,
    semantic_arrangement_method: str = "eom",
    debug_arrangement: bool = False,
    skip_nodes: Optional[List[str]] = None,
    orphans_label_template: Optional[str] = None,
    stats: Optional[Any] = None,
    preview_limit: Optional[int] = None,
    progress_callback=None
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
    
    from ..smart import SmartConfig, TraversalBudget
    smart_config = SmartConfig(
        enabled=smart,
        min_depth=min_significance_depth,
        min_hyponyms=min_hyponyms,
        min_leaf_size=min_leaf_size,
        merge_orphans=merge_orphans,
        semantic_cleanup=semantic_cleanup,
        semantic_model=semantic_model,
        semantic_threshold=semantic_threshold,
        semantic_arrangement=semantic_arrangement,
        semantic_arrangement_threshold=semantic_arrangement_threshold,
        semantic_arrangement_min_cluster=semantic_arrangement_min_cluster,
        semantic_arrangement_method=semantic_arrangement_method,
        debug_arrangement=debug_arrangement,
        skip_nodes=skip_nodes,
        orphans_label_template=orphans_label_template,
        preview_limit=preview_limit
    )

    budget = TraversalBudget(preview_limit)
    
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
            smart_config=smart_config, stats=stats, budget=budget
        )
    else:
        logger.info("Using full image-level mode (20k+ labels)")
        _, id_to_name = load_openimages_data()
        
        structure_mgr = StructureManager()
        result = build_wordnet_hierarchy(
            id_to_name, structure_mgr, 
            with_glosses=with_glosses, 
            smart_config=smart_config,
            stats=stats,
            budget=budget
        )
    
    
    # Post-process with ConstraintShaper
    if smart_config.enabled and (min_leaf_size > 0 or merge_orphans):
         from ..shaper import ConstraintShaper
         logger.info("Shaping hierarchy (merging orphans, flattening)...")
         shaper = ConstraintShaper(result)
         result = shaper.shape(min_leaf_size=min_leaf_size, flatten_singles=True, preserve_roots=True)

    return result

