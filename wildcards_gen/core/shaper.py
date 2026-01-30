
import logging
from typing import Dict, List, Any, Union

logger = logging.getLogger(__name__)

class ConstraintShaper:
    """
    Post-process a nested dictionary structure to enforce constraints
    like minimum leaf size and tree depth/flatness.
    """
    
    def __init__(self, tree: Dict[str, Any]):
        self.tree = tree

    def shape(self, min_leaf_size: int = 10, flatten_singles: bool = True, preserve_roots: bool = True) -> Dict[str, Any]:
        """
        Run all shaping passes.
        preserve_roots: if True, do not flatten the top-level dictionary even if it has 1 key.
        """
        processed = self._merge_orphans(self.tree, min_leaf_size)
        if flatten_singles:
            if preserve_roots and isinstance(processed, dict) and len(processed) == 1:
                # Only recursively flatten the *values*, keep the root key.
                # Since _flatten_singles recurses, we just manually recurse on the value.
                key = list(processed.keys())[0]
                val = processed[key]
                processed[key] = self._flatten_singles(val)
            else:
                processed = self._flatten_singles(processed)
        return processed


    def _merge_orphans(self, node: Any, min_size: int) -> Any:
        """
        Recursively merge small sibling groups into 'Other'.
        """
        if isinstance(node, list):
            return sorted(node)
        
        if not isinstance(node, dict):
            return node

        # 1. Recurse down first
        processed_node = type(node)() if isinstance(node, dict) else {}
        for k, v in node.items():
            processed_node[k] = self._merge_orphans(v, min_size)

            
        # 2. Process current level
        # Identify small groups (that are lists, i.e., leaves)
        small_keys = []
        regular_keys = []
        
        for k, v in processed_node.items():
            # count items
            count = 0
            if isinstance(v, list):
                count = len(v)
            elif isinstance(v, dict):
                # Rough count of children? Or just don't merge dicts?
                # Usually we only merge leaf lists. Merging sub-trees is risky.
                count = 99999 
                
            if count < min_size and k != "Other":
                small_keys.append(k)
            else:
                regular_keys.append(k)
                
        if not small_keys:
            return processed_node
            
        # Move small items to 'Other'
        if "Other" not in processed_node:
             processed_node["Other"] = []
             
        # Check type of "Other" - it might be a dict if created recursively?
        # Enforce "Other" is a list for merging items.
        if isinstance(processed_node["Other"], dict):
            # If 'Other' is a dict, we can't easily merge list items into it.
            # Skip merging for safety or rename?
            # Let's assume 'Other' is a bucket for items.
            pass 
        else:
             for k in small_keys:
                 items = processed_node.pop(k)
                 if isinstance(items, list):
                     processed_node["Other"].extend(items)
                     
        # Sort Other
        if isinstance(processed_node["Other"], list):
             processed_node["Other"] = sorted(processed_node["Other"])
             
        # Cleanup: If "Other" is the ONLY key, maybe promote it? 
        # Or if "Other" is empty (shouldn't happen if we added stuff).
        if not processed_node["Other"] and "Other" in processed_node:
            del processed_node["Other"]

        return processed_node

    def _flatten_singles(self, node: Any) -> Any:
        """
        Recursively remove intermediate nodes with only 1 child.
        e.g. {A: {B: ...}} -> {A: ...} (rename A to B? or keep A?)
        Usually: Keep Parent Name, pull Child Content up.
        Actually: logical flattening usually means "A/B" -> "B".
        
        Logic: If node is dict and len(node) == 1:
           child_key = list(node.keys())[0]
           child_val = node[child_key]
           return _flatten_singles(child_val)
           
        But strict flattening might lose context.
        Strategy: Only flatten if the child is a DICT. If child is LIST, it's a leaf node.
        We generally keep {Category: [items]}
        We want to remove {Category: {SubCategory: [items]}} -> {Category: [items]}?
        Or {Category: {SubCategory: [items]}} -> {SubCategory: [items]}?
        
        Let's do: Promotion. Content moves up.
        """
        if isinstance(node, list):
            return node
            
        if not isinstance(node, dict):
            return node
            
        # Recurse values first
        new_node = type(node)() if isinstance(node, dict) else {}
        for k, v in node.items():
            new_node[k] = self._flatten_singles(v)

            
        # Check if single child
        if len(new_node) == 1:
            key = list(new_node.keys())[0]
            val = new_node[key]
            
            # Promote single child content (whether dict or list)
            # This effectively removes the current node's wrapper (key).
            # e.g. {Sub: [items]} -> [items]
            return val

                 
        return new_node
