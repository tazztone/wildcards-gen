
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
        
        # 2. Prune Tautologies (A -> A -> B)
        processed = self._prune_tautologies(processed)
        
        if flatten_singles:
            if preserve_roots and isinstance(processed, dict) and len(processed) == 1:
                # Only recursively flatten the *values*, keep the root key.
                # Since _flatten_singles recurses, we just manually recurse on the value.
                key = list(processed.keys())[0]
                val = processed[key]
                processed[key] = self._flatten_singles(val)
            else:
                processed = self._flatten_singles(processed)
        # 4. Normalize Casing (Categories: Title Case, Items: lowercase)
        processed = self._normalize_casing(processed)
        
        return processed


    def _normalize_casing(self, node: Any) -> Any:
        """
        Force Title Case for category names and lowercase for leaf items.
        """
        if isinstance(node, list):
            # Sort and deduplicate items while lowercasing
            return sorted(list(set(str(item).lower() for item in node)))
            
        if not isinstance(node, dict):
            return node

        new_node = type(node)() if isinstance(node, dict) else {}
        for k, v in node.items():
            title_k = k.title()
            norm_v = self._normalize_casing(v)
            
            if title_k in new_node:
                # Merge collisions
                existing = new_node[title_k]
                if isinstance(existing, list) and isinstance(norm_v, list):
                    new_node[title_k] = sorted(list(set(existing + norm_v)))
                elif isinstance(existing, dict) and isinstance(norm_v, dict):
                    existing.update(norm_v)
                # If mixed types, the last one wins (rare in this app)
                else:
                    new_node[title_k] = norm_v
            else:
                new_node[title_k] = norm_v
                
        return new_node


    def _prune_tautologies(self, node: Any) -> Any:
        """
        Recursively remove nodes where parent name equals child name.
        e.g. {Fish: {Fish: [...]}} -> {Fish: [...] }
        """
        if not isinstance(node, dict):
            return node

        new_node = type(node)() if isinstance(node, dict) else {}
        for k, v in node.items():
            # First recurse down
            v = self._prune_tautologies(v)
            
            # Check for tautology with single child
            if isinstance(v, dict) and len(v) == 1:
                child_key = list(v.keys())[0]
                if k.lower().strip() == child_key.lower().strip():
                    # Promote child's value to current key
                    new_node[k] = v[child_key]
                    continue
            
            new_node[k] = v
            
        return new_node


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
        small_keys = []
        orphan_items = []
        context_items = []
        
        for k, v in processed_node.items():
            if k == "Other":
                continue
            
            if isinstance(v, list):
                if len(v) < min_size:
                    small_keys.append(k)
                    orphan_items.extend(v)
                else:
                    context_items.extend(v)
            elif isinstance(v, dict):
                # We don't merge dicts, but they provide context
                # (Ideally we'd recursive gather, but sibling list items are usually enough)
                pass

        if not small_keys:
            return processed_node
            
        # Determine Label
        other_label = "Other"
        try:
            from .arranger import generate_contextual_label
            other_label = generate_contextual_label(orphan_items, context_items)
        except (ImportError, Exception):
            pass

        # Move to new label
        if other_label not in processed_node:
             processed_node[other_label] = []
        
        if isinstance(processed_node[other_label], list):
             for k in small_keys:
                 items = processed_node.pop(k)
                 if isinstance(items, list):
                     processed_node[other_label].extend(items)
             processed_node[other_label] = sorted(processed_node[other_label])
        
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
            
            # Protect leaf lists from flattening (preserves Category name for list)
            # UNLESS the key is a generic container like 'misc' or 'Other'
            if isinstance(val, list):
                if key not in ["misc", "Other"]:
                    return new_node
            
            # Promote single child content (whether dict or list)
            # This effectively removes the current node's wrapper (key).
            # e.g. {Sub: {Deep: ...}} -> {Deep: ...}
            return val

                 
        return new_node
