
import logging
import csv
from collections import defaultdict
from typing import Dict, Any, List, Optional
from .downloaders import download_tencent_hierarchy
from ..wordnet import get_synset_gloss, ensure_nltk_data, get_synset_from_wnid

logger = logging.getLogger(__name__)

def parse_hierarchy_file(file_path: str) -> Dict[str, Any]:
    """Parse the Tencent hierarchy file into parent-child map."""
    # format: category_index, category_id, index_of_parent_category, category name
    # header: 1st line
    
    categories = {}  # index -> (id, name, parent_index)
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

def build_recursive(current_idx: int, categories: Dict, children_map: Dict, depth: int, max_depth: int, with_glosses: bool) -> Any:
    """Recursively build hierarchy dict."""
    cat_info = categories[current_idx]
    name = cat_info['name']
    
    # Clean name (take first if comma separated)
    clean_name = name.split(',')[0].strip()
    
    # Add instruction
    instruction = ""
    if with_glosses:
        # Tencent IDs are WNIDs (e.g. n00002452)
        synset = get_synset_from_wnid(cat_info['id'])
        if synset:
            instruction = get_synset_gloss(synset)
        else:
            instruction = f"Items related to {clean_name}"
            
    # Check if leaf or max depth
    children_indices = children_map.get(current_idx, [])
    
    if not children_indices or depth >= max_depth:
        # Leaf node
        return [clean_name]
    
    # Branch node
    subtree = {}
    
    # Store instruction on the branch key? 
    # StructureManager handles comments via key lookups or special handling.
    # We'll return a dict where keys are children.
    # WAIT: Standard format is `Parent: { Child1: [...], Child2: [...] }`
    # We need to construct the subtree such that the caller attaches it to this node.
    
    # Actually, the recursive function returns the VALUE for the current node.
    
    child_dict = {}
    for child_idx in children_indices:
        child_val = build_recursive(child_idx, categories, children_map, depth + 1, max_depth, with_glosses)
        child_name = categories[child_idx]['name'].split(',')[0].strip()
        
        # Add instruction to child key using parsed comments convention?
        # StructureManager adds comments based on key matching.
        # We can simulate this by returning a dict with keys.
        # BUT we need to pass the instruction up so it can be attached.
        
        # StructureManager expects:
        # { "child_name": content }
        # And we set comments separately or use Ruamel manually? 
        # StructureManager uses `recursive_comment_add` which looks up instructions from a side-channel or existing comments?
        # No, `StructureManager` preserves existing comments. 
        # Here we are generating NEW structure. 
        # We should use `StructureManager`'s comment adding utility if possible, 
        # OR format it such that we can add comments later.
        
        # Better approach: Return a dict structure, and a separate "instructions" map?
        # Or just use the `# instruction:` string in the key? No, that's ugly.
        
        # Let's rely on StructureManager.create_structure which takes a dict.
        # Then we post-process to add comments.
        child_dict[child_name] = child_val

    return child_dict

def generate_tencent_hierarchy(
    max_depth: int = 5, 
    with_glosses: bool = True,
    smart: bool = False,
    min_significance_depth: int = 6,
    min_hyponyms: int = 10,
    min_leaf_size: int = 3
) -> Dict:
    """Generate Tencent ML-Images hierarchy."""
    file_path = download_tencent_hierarchy()
    categories, children_map, roots = parse_hierarchy_file(file_path)
    
    if with_glosses:
        ensure_nltk_data()
    
    def collect_leaves(idx: int) -> List[str]:
        """Collect all descendant leaf names."""
        leaves = []
        children = children_map.get(idx, [])
        
        if not children:
            name = categories[idx]['name'].split(',')[0].strip()
            leaves.append(name)
        else:
            for child_idx in children:
                leaves.extend(collect_leaves(child_idx))
        
        return leaves

    from ruamel.yaml.comments import CommentedMap
    from ..smart import SmartConfig, should_prune_node
    
    smart_config = SmartConfig(
        enabled=smart,
        min_depth=min_significance_depth,
        min_hyponyms=min_hyponyms,
        min_leaf_size=min_leaf_size
    )
    
    def build_commented(current_idx: int, current_depth: int) -> Any:
        cat_info = categories[current_idx]
        name = cat_info['name'].split(',')[0].strip()
        wnid = cat_info['id']
        
        children = children_map.get(current_idx, [])
        
        # Base case: actual leaf
        if not children:
            return None
            
        # Decision logic: keep as category or flatten?
        should_flatten = False
        
        if smart:
            synset = get_synset_from_wnid(wnid)
            is_root = categories[current_idx]['parent'] == -1
            
            should_flatten = should_prune_node(
                synset=synset, 
                child_count=len(children), 
                is_root=is_root, 
                config=smart_config
            )
        else:
            # Traditional depth-based pruning
            if current_depth >= max_depth:
                should_flatten = True

        if should_flatten:
            leaves = collect_leaves(current_idx)
            # Filter self-matches
            normalized_name = name.lower()
            filtered_leaves = sorted(list(set([l for l in leaves if l.lower() != normalized_name])), key=str.casefold)
            
            # Min leaf size check for smart mode
            if smart and len(filtered_leaves) < smart_config.min_leaf_size:
                return None # Merge into parent
                
            return filtered_leaves if filtered_leaves else None

        # Build category
        cm = CommentedMap()
        sorted_children = sorted(children, key=lambda idx: categories[idx]['name'].split(',')[0].strip().casefold())
        
        valid_items_added = 0
        for child_idx in sorted_children:
            child_name = categories[child_idx]['name'].split(',')[0].strip()
            child_val = build_commented(child_idx, current_depth + 1)
            
            # If child_val is None, it means the child was empty or merged upward
            if child_val is not None or not smart:
                cm[child_name] = child_val
                valid_items_added += 1
                
                # Add comment
                if with_glosses:
                    child_wnid = categories[child_idx]['id']
                    synset = get_synset_from_wnid(child_wnid)
                    instr = get_synset_gloss(synset) if synset else f"Items related to {child_name}"
                    cm.yaml_add_eol_comment(f"# instruction: {instr}", child_name)
        
        if valid_items_added == 0:
            # If all children were pruned/merged, flatten itself
            leaves = collect_leaves(current_idx)
            normalized_name = name.lower()
            filtered_leaves = sorted(list(set([l for l in leaves if l.lower() != normalized_name])), key=str.casefold)
            return filtered_leaves if filtered_leaves else None
            
        return cm

    # Root level
    final_map = CommentedMap()
    sorted_roots = sorted(roots, key=lambda idx: categories[idx]['name'].split(',')[0].strip().casefold())
    
    for root_idx in sorted_roots:
        root_name = categories[root_idx]['name'].split(',')[0].strip()
        final_map[root_name] = build_commented(root_idx, 1)
        
        if with_glosses:
            wnid = categories[root_idx]['id']
            synset = get_synset_from_wnid(wnid)
            instr = get_synset_gloss(synset) if synset else f"Items related to {root_name}"
            final_map.yaml_add_eol_comment(f"# instruction: {instr}", root_name)
            
    return final_map
