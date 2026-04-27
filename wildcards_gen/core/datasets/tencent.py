
import logging
import csv
import functools
from collections import defaultdict
from typing import Dict, Any, List, Optional, Tuple, Set
from ruamel.yaml.comments import CommentedMap

from .downloaders import download_tencent_hierarchy
from ..config import config
from ..wordnet import get_synset_gloss, ensure_nltk_data, get_synset_from_wnid
from ..presets import DATASET_CATEGORY_OVERRIDES, DATASET_PRESET_OVERRIDES
from ..builder import TaxonomyNode
from ..smart import TraversalBudget

logger = logging.getLogger(__name__)

@functools.lru_cache(maxsize=1)
def parse_hierarchy_file(file_path: str) -> Tuple[Dict[int, Dict], Dict[int, List[int]], List[int]]:
    """Parse the Tencent hierarchy file into parent-child map."""
    categories = {}  # index -> {id, name, parent}
    children_map = defaultdict(list)  # parent_index -> [child_indices]
    roots = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        next(reader)  # skip header
        
        for row in reader:
            if not row: continue
            idx = int(row[0])
            cat_id = row[1]
            parent_idx = int(row[2])
            name = row[3]
            
            categories[idx] = {'id': cat_id, 'name': name, 'parent': parent_idx}
            
            if parent_idx == -1:
                roots.append(idx)
            else:
                children_map[parent_idx].append(idx)
                
    return categories, children_map, roots

def build_taxonomy_tree(
    idx: int,
    categories: Dict[int, Dict],
    children_map: Dict[int, List[int]],
    depth: int,
    max_depth: int,
    with_glosses: bool = True,
    budget: Optional[TraversalBudget] = None
) -> Optional[TaxonomyNode]:
    """Pure extractor for Tencent ML-Images."""
    if budget and not budget.consume():
        return None
    cat_info = categories[idx]
    
    # Clean name (remove synset variants)
    name = cat_info['name'].split(',')[0].strip()
    wnid = cat_info['id']
    
    # Get instruction
    instruction = None
    if with_glosses:
        synset = get_synset_from_wnid(wnid)
        if synset:
            instruction = get_synset_gloss(synset)
    if not instruction:
        instruction = f"Items related to {name}"
        
    children_indices = children_map.get(idx, [])
    
    # Leaf logic
    if not children_indices or depth >= max_depth:
        # Collect all leaves in this subtree
        leaves = []
        def collect_leaves_recursive(c_idx):
            sub_children = children_map.get(c_idx, [])
            if not sub_children:
                leaves.append(categories[c_idx]['name'].split(',')[0].strip())
            else:
                for sub_child in sub_children:
                    collect_leaves_recursive(sub_child)
        
        collect_leaves_recursive(idx)
        
        return TaxonomyNode(
            name=name,
            children=[],
            items=sorted(list(set(leaves)), key=str.casefold),
            metadata={
                "instruction": instruction,
                "wnid": wnid,
                "depth": depth,
                "is_root": (cat_info['parent'] == -1)
            }
        )
    
    # Branch Logic
    child_nodes = []
    for c_idx in children_indices:
        child_node = build_taxonomy_tree(
            c_idx, categories, children_map, 
            depth + 1, max_depth, with_glosses, budget
        )
        if child_node:
            child_nodes.append(child_node)
            
    return TaxonomyNode(
        name=name,
        children=child_nodes,
        metadata={
            "instruction": instruction,
            "wnid": wnid,
            "depth": depth,
            "is_root": (cat_info['parent'] == -1)
        }
    )

def generate_tencent_hierarchy(
    max_depth: int = 4,
    with_glosses: bool = True,
    preview_limit: Optional[int] = None,
    **kwargs # Accept and ignore smart args
) -> Optional[TaxonomyNode]:
    """
    Generate Tencent ML-Images TaxonomyNode tree.
    """
    ensure_nltk_data()
    file_path = download_tencent_hierarchy()
    categories, children_map, roots = parse_hierarchy_file(file_path)
    
    logger.info(f"Extracting Tencent hierarchy (roots={len(roots)}, max_depth={max_depth})")
    
    root_nodes = []
    # Sort roots by name for stability
    sorted_roots = sorted(roots, key=lambda idx: categories[idx]['name'].split(',')[0].strip().casefold())
    
    budget = TraversalBudget(preview_limit)
    
    for root_idx in sorted_roots:
        node = build_taxonomy_tree(
            root_idx, categories, children_map,
            depth=0, max_depth=max_depth,
            with_glosses=with_glosses,
            budget=budget
        )
        if node:
            root_nodes.append(node)
            
    if not root_nodes:
        return None
        
    if len(root_nodes) == 1:
        return root_nodes[0]
        
    # Virtual root for multiple real roots
    return TaxonomyNode(
        name="Tencent ML-Images",
        children=root_nodes,
        metadata={"is_root": True, "depth": -1}
    )
