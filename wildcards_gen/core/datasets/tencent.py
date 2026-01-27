
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

def generate_tencent_hierarchy(max_depth: int = 3, with_glosses: bool = True) -> Dict:
    """Generate Tencent ML-Images hierarchy."""
    file_path = download_tencent_hierarchy()
    categories, children_map, roots = parse_hierarchy_file(file_path)
    
    if with_glosses:
        ensure_nltk_data()
    
    full_tree = {}
    instructions = {}
    
    def build(current_idx, current_depth):
        cat_info = categories[current_idx]
        name = cat_info['name'].split(',')[0].strip()
        wnid = cat_info['id']
        
        # Get instruction
        if with_glosses:
            synset = get_synset_from_wnid(wnid)
            if synset:
                instructions[name] = get_synset_gloss(synset)
            else:
                instructions[name] = f"Items related to {name}"
        
        children = children_map.get(current_idx, [])
        if not children or current_depth >= max_depth:
            return [name] # Leaf represented as list of 1? Or just empty list?
            # Standard leaf in this project is list of strings.
        
        subtree = {}
        for child_idx in children:
            child_name = categories[child_idx]['name'].split(',')[0].strip()
            subtree[child_name] = build(child_idx, current_depth + 1)
            
        return subtree

    # Process all roots
    for root_idx in roots:
        root_name = categories[root_idx]['name'].split(',')[0].strip()
        full_tree[root_name] = build(root_idx, 1)
        
    # Attach instructions? 
    # Limitation: StructureManager.to_string expects standard dict.
    # Use StructureManager helper to add comments?
    # It has `add_comment_recursive`.
    
    # We return the tree, but we need to pass instructions too.
    # The current pattern in datasets/imagenet.py is:
    # It embeds instructions directly? No, it uses `comment_map`.
    
    # HACK: We'll attach instructions to the output dict using a special attribute or just return both?
    # The existing generators return a Dist. 
    # Let's check imagenet.py...
    # It returns a plain dict. And uses `set_instruction_comment` on the Ruamel object? 
    # No, imagenet.py returns a CommentedMap from Ruamel YAML!
    
    # So we need to use ruamel.yaml directly here or StructureManager.
    from ruamel.yaml.comments import CommentedMap
    
    def build_commented(current_idx, current_depth):
        cat_info = categories[current_idx]
        name = cat_info['name'].split(',')[0].strip()
        wnid = cat_info['id']
        
        children = children_map.get(current_idx, [])
        
        # Leaf logic
        if not children or current_depth >= max_depth:
            return [name]
            
        cm = CommentedMap()
        for child_idx in children:
            child_name = categories[child_idx]['name'].split(',')[0].strip()
            child_val = build_commented(child_idx, current_depth + 1)
            
            cm[child_name] = child_val
            
            # Add comment to this key in the parent map (cm)
            if with_glosses:
                child_wnid = categories[child_idx]['id']
                synset = get_synset_from_wnid(child_wnid)
                instr = get_synset_gloss(synset) if synset else f"Items related to {child_name}"
                cm.yaml_add_eol_comment(f"# instruction: {instr}", child_name)
                
        return cm

    # Root level
    final_map = CommentedMap()
    for root_idx in roots:
        root_name = categories[root_idx]['name'].split(',')[0].strip()
        
        # Valid root check (Tencent has 4 roots)
        final_map[root_name] = build_commented(root_idx, 1)
        
        # Add comment for root
        if with_glosses:
            wnid = categories[root_idx]['id']
            synset = get_synset_from_wnid(wnid)
            instr = get_synset_gloss(synset) if synset else f"Items related to {root_name}"
            final_map.yaml_add_eol_comment(f"# instruction: {instr}", root_name)
            
    return final_map
