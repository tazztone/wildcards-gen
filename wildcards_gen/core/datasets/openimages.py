"""
Open Images dataset hierarchy generator.

Generates skeleton YAML from Open Images hierarchy with WordNet glosses
as # instruction: comments.
"""

import json
import csv
import functools
import logging
from typing import Dict, List, Tuple, Any, Optional

from ..config import config
from ..wordnet import ensure_nltk_data, get_primary_synset, get_synset_gloss, get_synset_name
from .downloaders import ensure_openimages_data
from ..builder import TaxonomyNode
from ..smart import TraversalBudget

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

@functools.lru_cache(maxsize=1)
def _get_cached_synset_tree() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Build the synset tree structure for 20k mode."""
    _, id_to_name = load_openimages_data()
    
    # Map names to synsets
    synset_to_labels = {}
    for label_id, name in id_to_name.items():
        clean_name = name.lower().replace('/', ' ')
        synset = get_primary_synset(clean_name)
        if synset:
            wnid = f"{synset.pos()}{synset.offset():08d}"
            if wnid not in synset_to_labels:
                synset_to_labels[wnid] = {'synset': synset, 'labels': []}
            synset_to_labels[wnid]['labels'].append(name)
        else:
            if None not in synset_to_labels:
                 synset_to_labels[None] = {'synset': None, 'labels': []}
            synset_to_labels[None]['labels'].append(name)

    synset_tree = {} # wnid -> {'synset': synset, 'parent': wnid, 'children': [wnids], 'labels': [names]}
    for wnid, data in synset_to_labels.items():
        synset = data['synset']
        labels = data['labels']
        if synset:
            paths = synset.hypernym_paths()
            if paths:
                path = paths[0]
                for i in range(len(path)):
                    curr = path[i]
                    curr_wnid = f"{curr.pos()}{curr.offset():08d}"
                    if curr_wnid not in synset_tree:
                        parent_wnid = f"{path[i-1].pos()}{path[i-1].offset():08d}" if i > 0 else None
                        synset_tree[curr_wnid] = {'synset': curr, 'parent': parent_wnid, 'children': set(), 'labels': []}
                        if parent_wnid: synset_tree[parent_wnid]['children'].add(curr_wnid)
                curr_wnid = f"{synset.pos()}{synset.offset():08d}"
                synset_tree[curr_wnid]['labels'].extend(labels)
            else:
                if 'root' not in synset_tree: synset_tree['root'] = {'synset': None, 'parent': None, 'children': set(), 'labels': []}
                synset_tree['root']['labels'].extend(labels)
        else:
            if 'other' not in synset_tree: synset_tree['other'] = {'synset': None, 'parent': None, 'children': set(), 'labels': []}
            synset_tree['other']['labels'].extend(labels)
    return synset_to_labels, synset_tree

def build_taxonomy_tree_from_synsets(wnid, synset_tree, depth, max_depth, with_glosses, budget: Optional[TraversalBudget] = None) -> Optional[TaxonomyNode]:
    if budget and not budget.consume():
        return None
    node_data = synset_tree[wnid]
    synset = node_data['synset']
    name = get_synset_name(synset) if synset else wnid.capitalize()
    instruction = get_synset_gloss(synset) if synset and with_glosses else f"Items related to {name}"
    
    children = node_data['children']
    if not children or depth >= max_depth:
        # Leaf: collect all labels in subtree
        labels = list(node_data['labels'])
        def collect_labels_recursive(w):
            n = synset_tree[w]
            labels.extend(n['labels'])
            for child in n['children']: collect_labels_recursive(child)
        for child in children: collect_labels_recursive(child)
        
        return TaxonomyNode(
            name=name, children=[], items=sorted(list(set(labels)), key=str.casefold),
            metadata={"instruction": instruction, "synset": synset, "depth": depth, "is_root": node_data['parent'] is None}
        )
    
    child_nodes = []
    for c_wnid in sorted(list(children)):
        child = build_taxonomy_tree_from_synsets(c_wnid, synset_tree, depth + 1, max_depth, with_glosses, budget)
        if child: child_nodes.append(child)
        
    # Also add labels directly at this node as a child
    if node_data['labels']:
        child_nodes.append(TaxonomyNode(name=f"Other {name}", items=sorted(node_data['labels'], key=str.casefold)))

    return TaxonomyNode(
        name=name, children=child_nodes,
        metadata={"instruction": instruction, "synset": synset, "depth": depth, "is_root": node_data['parent'] is None}
    )

def build_taxonomy_tree_from_json(node, id_to_name, depth, max_depth, with_glosses, budget: Optional[TraversalBudget] = None) -> Optional[TaxonomyNode]:
    if budget and not budget.consume():
        return None
    label_id = node.get('LabelName')
    name = id_to_name.get(label_id, label_id)
    if label_id == '/m/0bl9f' and name == label_id: name = 'Entity'
    
    synset = get_primary_synset(name.lower())
    instruction = get_synset_gloss(synset) if synset and with_glosses else f"Items related to {name}"
    
    sub_key = 'Subcategory' if 'Subcategory' in node else 'Subcategories' if 'Subcategories' in node else None
    child_json_nodes = node.get(sub_key, []) if sub_key else []
    
    if not child_json_nodes or depth >= max_depth:
        # Leaf: collect all descendant names
        leaves = []
        def collect_leaves_recursive(n):
            l_id = n.get('LabelName')
            l_name = id_to_name.get(l_id)
            if l_name: leaves.append(l_name)
            sk = 'Subcategory' if 'Subcategory' in n else 'Subcategories' if 'Subcategories' in n else None
            for sc in n.get(sk, []): collect_leaves_recursive(sc)
        collect_leaves_recursive(node)
        
        return TaxonomyNode(
            name=name, children=[], items=sorted(list(set(leaves)), key=str.casefold),
            metadata={"instruction": instruction, "synset": synset, "depth": depth, "is_root": depth == 0}
        )
    
    child_nodes = []
    for c_node in child_json_nodes:
        child = build_taxonomy_tree_from_json(c_node, id_to_name, depth + 1, max_depth, with_glosses, budget)
        if child: child_nodes.append(child)
        
    return TaxonomyNode(
        name=name, children=child_nodes,
        metadata={"instruction": instruction, "synset": synset, "depth": depth, "is_root": depth == 0}
    )

def generate_openimages_hierarchy(
    max_depth: int = 4,
    with_glosses: bool = True,
    bbox_only: bool = False,
    preview_limit: Optional[int] = None,
    **kwargs # Accept and ignore smart args
) -> Optional[TaxonomyNode]:
    """
    Generate Open Images TaxonomyNode tree.
    """
    ensure_nltk_data()
    hierarchy, id_to_name = load_openimages_data()
    
    budget = TraversalBudget(preview_limit)
    
    if bbox_only:
        logger.info("Extracting Open Images (BBox mode)")
        return build_taxonomy_tree_from_json(hierarchy, id_to_name, 0, max_depth, with_glosses, budget)
    else:
        logger.info("Extracting Open Images (Full mode)")
        _, synset_tree = _get_cached_synset_tree()
        roots = [wnid for wnid, n in synset_tree.items() if n['parent'] is None]
        
        root_nodes = []
        for root in sorted(roots):
            node = build_taxonomy_tree_from_synsets(root, synset_tree, 0, max_depth, with_glosses, budget)
            if node: root_nodes.append(node)
            
        if not root_nodes: return None
        if len(root_nodes) == 1: return root_nodes[0]
        return TaxonomyNode(name="Open Images", children=root_nodes, metadata={"is_root": True, "depth": -1})
