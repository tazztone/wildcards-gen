
import logging
from typing import Dict, List, Any, Union, Optional
from ruamel.yaml.comments import CommentedMap
from .config import config

logger = logging.getLogger(__name__)

class ConstraintShaper:
    """
    Post-process a nested dictionary structure to enforce constraints
    like minimum leaf size and tree depth/flatness.
    """
    
    def __init__(self, tree: Dict[str, Any]):
        self.tree = tree

    def shape(self, min_leaf_size: int = 10, flatten_singles: bool = True, preserve_roots: bool = True, orphans_label_template: Optional[str] = None) -> Dict[str, Any]:
        """
        Run all shaping passes.
        preserve_roots: if True, do not flatten the top-level dictionary even if it has 1 key.
        """
        processed = self._merge_orphans(self.tree, min_leaf_size, orphans_label_template)

        # 2. Prune Tautologies (A -> A -> B)
        processed = self._prune_tautologies(processed)
        
        if flatten_singles:
            if preserve_roots and isinstance(processed, dict) and len(processed) == 1:
                # Only recursively flatten the *values*, keep the root key.
                # Since _flatten_singles recurses, we just manually recurse on the value.
                key = list(processed.keys())[0]
                val = processed[key]
                processed[key] = self._flatten_singles(val, is_root=False)
            else:
                processed = self._flatten_singles(processed, is_root=True)

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
            
            # Preserve comments
            if isinstance(node, CommentedMap) and k in node.ca.items:
                 new_node.ca.items[title_k] = node.ca.items[k]

        return new_node


    def _prune_tautologies(self, node: Any) -> Any:
        """
        Recursively remove nodes where parent name equals child name.
        """
        if not isinstance(node, dict):
            return node

        new_node = type(node)() if isinstance(node, dict) else {}
        for k, v in node.items():
            # First recurse down
            v = self._prune_tautologies(v)
            
            # Check for tautology in children
            if isinstance(v, dict):
                k_norm = k.lower().strip()
                # Find any child that matches the parent name
                match_key = next((ck for ck in v.keys() if ck.lower().strip() == k_norm), None)
                
                if match_key:
                    child_val = v[match_key]
                    # If it's the ONLY child, promote it entirely
                    if len(v) == 1:
                         new_node[k] = child_val
                         # Preserve comment
                         if isinstance(v, CommentedMap) and match_key in v.ca.items:
                              new_node.ca.items[k] = v.ca.items[match_key]
                    else:
                         # It has siblings. We should "dissolve" the matching child into the parent.
                         # BUT: a dict key 'k' can't hold both a list and other dicts easily in YAML 
                         # without a sub-key.
                         
                         # Actually, if the child matches the parent, it usually means 
                         # those items BELONG in the parent directly.
                         # We'll keep the other siblings as sub-categories.
                         
                         # To avoid complex merging, if child_val is a list, and others are dicts:
                         # We'll just rename the matching child to something like "General" or similar?
                         # Or just keep it. 
                         
                         # Let's try: if the matching child is a list, we can't merge it into the 
                         # parent dict 'k' without a key. 
                         
                         # Re-read the user's example: 
                         # Wine:
                         #   Wine: [...]
                         #   Misc: [...]
                         # This IS what they had. They want to avoid the double 'Wine'.
                         
                         # Best fix: Rename the sub-'Wine' to 'General' or 'Base'
                         v[f"General {k}"] = v.pop(match_key)
                         new_node[k] = v
                    continue

            new_node[k] = v
            # Preserve comment from current key
            if isinstance(node, CommentedMap) and k in node.ca.items:
                 new_node.ca.items[k] = node.ca.items[k]
            
        return new_node

    def _merge_orphans(self, node: Any, min_size: int, orphans_label_template: Optional[str] = None) -> Any:
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
            processed_node[k] = self._merge_orphans(v, min_size, orphans_label_template)
            # Preserve comment for this key
            if isinstance(node, CommentedMap) and k in node.ca.items:
                 processed_node.ca.items[k] = node.ca.items[k]

            
        # 2. Process current level
        small_keys = []
        orphan_items = []
        context_items = []
        
        # Target label base
        target_label_base = orphans_label_template if orphans_label_template else "Other"

        for k, v in processed_node.items():
            # If this key is already a generic bin, we might want to merge it
            is_existing_generic = k.lower() in ["other", "misc"] or k.startswith("Other (") or k.startswith("misc (")
            
            if isinstance(v, list):
                if len(v) < min_size or is_existing_generic:
                    small_keys.append(k)
                    orphan_items.extend(v)
                else:
                    context_items.extend(v)
            elif isinstance(v, dict):
                # We don't merge dicts, but they provide context
                pass

        if not small_keys:
            return processed_node
            
        # Determine Label
        other_label = target_label_base
        
        # Use contextual naming if possible (only if it's the generic "Other" or "misc")
        # We check both to catch different default conventions
        is_generic = other_label.lower() in ["other", "misc"]
        
        if is_generic:
            try:
                from .arranger import generate_contextual_label
                other_label = generate_contextual_label(orphan_items, context_items, fallback=other_label)
            except (ImportError, Exception):
                pass

        # Move to new label
        if other_label not in processed_node:
             processed_node[other_label] = []
             # Add instruction comment if it's a CommentedMap
             if isinstance(processed_node, CommentedMap):
                try:
                    # If it's a renamed label like "Other (Fish)", use that context
                    instr_context = other_label
                    if is_generic and "(" in other_label:
                        # Extract the part in parenthesis
                        import re
                        match = re.search(r"\((.*?)\)", other_label)
                        if match:
                            instr_context = f"{match.group(1)} related items"
                    
                    if instr_context.lower() in ["other", "misc"]:
                         comment = config.instruction_template.format(gloss=f"Miscellaneous items")
                    else:
                         comment = config.instruction_template.format(gloss=f"Miscellaneous {instr_context}")
                    processed_node.yaml_add_eol_comment(comment, other_label)
                except Exception as e:
                    logger.debug(f"Failed to add shaper comment: {e}")
             else:
                logger.debug(f"processed_node is NOT CommentedMap, it is {type(processed_node)}")
        
        # Safety: If other_label is one of the keys we planned to merge, 
        # remove it from the merge list so we don't pop the destination.
        if other_label in small_keys:
            small_keys.remove(other_label)
        
        if isinstance(processed_node[other_label], list):
             for k in small_keys:
                 items = processed_node.pop(k)
                 if isinstance(items, list):
                     processed_node[other_label].extend(items)
             processed_node[other_label] = sorted(list(set(processed_node[other_label])), key=str.casefold)
        
        return processed_node

    def _flatten_singles(self, node: Any, is_root: bool = False) -> Any:
        """
        Recursively remove intermediate nodes with only 1 child.
        """
        if isinstance(node, list):
            return node
            
        if not isinstance(node, dict):
            return node
            
        # Recurse values first
        new_node = type(node)() if isinstance(node, dict) else {}
        for k, v in node.items():
            new_node[k] = self._flatten_singles(v, is_root=False)
            # Preserve comment from current key
            if isinstance(node, CommentedMap) and k in node.ca.items:
                 new_node.ca.items[k] = node.ca.items[k]

            
        # Check if single child
        if len(new_node) == 1:
            key = list(new_node.keys())[0]
            val = new_node[key]
            
            # If we are at the root level, we generally want to keep the name
            # e.g. Matter: { Food: ... } -> Keep Matter.
            if is_root:
                 return new_node

            # Protect leaf lists from flattening (preserves Category name for list)
            # UNLESS the key is a generic container like 'misc' or 'Other'
            if isinstance(val, list):
                if key not in ["misc", "Other", "misc (Category 1)"]:
                    return new_node
            
            # Promote single child content
            # Only promote if:
            # 1. Child is a list AND key is generic (Other/Misc)
            # 2. Child is a dict and we have explicit redundancy (already handled by _prune_tautologies)
            # 3. Parent key is a "wrapper" node with only 1 child and it's not a root.
            
            # If we want to keep Matter -> Food -> Beverage -> Wine:
            # Beverage: { Wine: [...] } must NOT flatten to Wine: [...]
            if isinstance(val, dict):
                 # Keep the hierarchy if the names are different
                 return new_node
                 
            if isinstance(val, list):
                # Only flatten generic wrappers for lists
                if key.lower() in ["misc", "other"]:
                    return val
                return new_node
            
            return val

        return new_node
