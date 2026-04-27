"""
Hierarchy Builder Engine.

Consolidates the pruning, cleaning, and arrangement logic into a single pipeline.
Uses TaxonomyNode as the intermediate bridge format.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from .smart import (
    SmartConfig, TraversalBudget, should_prune_node, 
    apply_semantic_cleaning, apply_semantic_arrangement
)
from .shaper import ConstraintShaper
from .config import config

logger = logging.getLogger(__name__)

@dataclass
class TaxonomyNode:
    """Lightweight bridge format for dataset extraction."""
    name: str
    children: List['TaxonomyNode'] = field(default_factory=list)
    items: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class HierarchyBuilder:
    """The central engine for processing taxonomy trees."""
    
    def __init__(self, smart_config: SmartConfig, stats: Optional[Any] = None):
        self.config = smart_config
        self.stats = stats
        self.budget = TraversalBudget(smart_config.preview_limit)

    def build(self, root: TaxonomyNode) -> CommentedMap:
        """Process the raw taxonomy tree and return a final CommentedMap."""
        logger.info(f"Building hierarchy for '{root.name}'...")
        
        # 1. Prune and Arrange
        processed_node, orphans = self._prune_and_collect(root)
        
        # If the root itself was pruned and became orphans
        if not processed_node and orphans:
            # Create a simple list output if that's all we have
            res = CommentedMap()
            res[root.name] = sorted(list(set(orphans)), key=str.casefold)
            return res
        
        # 2. Convert to CommentedMap
        raw_map = CommentedMap()
        if processed_node:
            node_map = self._to_commented_map(processed_node)
            if isinstance(node_map, (dict, CommentedMap)):
                raw_map[processed_node.name] = node_map
            else:
                raw_map[processed_node.name] = node_map
        
        # 3. Final Shaping Pass
        shaper = ConstraintShaper(raw_map)
        shaped = shaper.shape(
            min_leaf_size=self.config.min_leaf_size,
            flatten_singles=True,
            preserve_roots=True,
            orphans_label_template=self.config.orphans_label_template,
            semantic_arrangement_min_cluster=self.config.semantic_arrangement_min_cluster,
            node_name=root.name
        )
        
        return shaped

    def _prune_and_collect(self, node: TaxonomyNode, config: Optional[SmartConfig] = None) -> Tuple[Optional[TaxonomyNode], List[str]]:
        """
        Recursively prune the tree and collect orphans.
        Returns (processed_node, orphans).
        """
        if not self.budget.consume(1):
            return None, []

        current_config = config or self.config
        name = node.name
        metadata = node.metadata
        synset = metadata.get("synset")
        is_root = metadata.get("is_root", False)
        depth = metadata.get("depth", 0)
        
        # 1. Pruning Decision
        should_flatten = False
        if current_config.enabled:
            should_flatten = should_prune_node(
                synset=synset,
                child_count=len(node.children),
                is_root=is_root,
                config=current_config
            )
        
        # 2. Handle Pruned Node (Flatten)
        if should_flatten:
            items = self._collect_all_items(node)
            
            # Semantic Cleaning
            if current_config.enabled and current_config.semantic_cleanup:
                items = apply_semantic_cleaning(items, current_config)
            
            # Semantic Arrangement (Re-grow)
            if current_config.enabled and current_config.semantic_arrangement:
                arranged, leftovers = apply_semantic_arrangement(items, current_config, stats=self.stats, context=name)
                
                if isinstance(arranged, dict) and arranged:
                    # Convert arranged dict to nodes
                    new_children = []
                    for g_name, g_items in arranged.items():
                        new_children.append(TaxonomyNode(name=g_name, items=g_items))
                    
                    if leftovers:
                        label = current_config.orphans_label_template
                        if label and "{}" in label:
                            label = label.format(name)
                        elif not label:
                            label = "misc"
                        new_children.append(TaxonomyNode(name=label, items=leftovers))
                    
                    return TaxonomyNode(name=name, children=new_children, metadata=metadata), []
                else:
                    # It returned a list (failed to cluster or small)
                    items = arranged if isinstance(arranged, list) else items

            # Min leaf size check with orphan bubbling
            if current_config.enabled and len(items) < current_config.min_leaf_size:
                if current_config.merge_orphans:
                    return None, items
            
            return TaxonomyNode(name=name, items=items, metadata=metadata), []

        # 3. Handle Branch Node
        processed_children = []
        collected_orphans = []
        
        for child in node.children:
            # Apply child-specific config if available
            child_config = current_config.get_child_config(child.name, child.metadata.get("wnid"))
            p_child, c_orphans = self._prune_and_collect(child, child_config)
            
            if p_child:
                processed_children.append(p_child)
            if c_orphans:
                collected_orphans.extend(c_orphans)
        
        # 4. Handle Orphans at this level
        if collected_orphans and current_config.enabled and current_config.merge_orphans:
            collected_orphans = sorted(list(set(collected_orphans)), key=str.casefold)
            
            if current_config.semantic_cleanup:
                collected_orphans = apply_semantic_cleaning(collected_orphans, current_config)
            
            if current_config.semantic_arrangement:
                arranged, leftovers = apply_semantic_arrangement(collected_orphans, current_config, stats=self.stats, context=f"orphans of {name}")
                if isinstance(arranged, dict) and arranged:
                    for g_name, g_items in arranged.items():
                        processed_children.append(TaxonomyNode(name=g_name, items=g_items))
                    collected_orphans = leftovers
            
            if collected_orphans:
                label = current_config.orphans_label_template
                if label and "{}" in label:
                    label = label.format(name)
                elif not label:
                    label = "misc"

                # Find if label already exists in children
                existing_misc = next((c for c in processed_children if c.name == label), None)
                if existing_misc:
                    existing_misc.items = sorted(list(set(existing_misc.items + collected_orphans)), key=str.casefold)
                else:
                    processed_children.append(TaxonomyNode(name=label, items=collected_orphans))
            
            collected_orphans = []

        # 5. Final validation for Branch Node
        if not processed_children and not node.items:
            # If everything was pruned/merged away
            return None, collected_orphans
            
        return TaxonomyNode(name=name, children=processed_children, items=node.items, metadata=metadata), collected_orphans

    def _collect_all_items(self, node: TaxonomyNode) -> List[str]:
        """Collect all leaf items from a node and its children."""
        items = list(node.items)
        for child in node.children:
            items.extend(self._collect_all_items(child))
        return sorted(list(set(items)), key=str.casefold)

    def _to_commented_map(self, node: TaxonomyNode) -> Any:
        """Convert TaxonomyNode tree to CommentedMap/list."""
        if not node.children:
            # Leaf list
            items = sorted(node.items, key=str.casefold)
            return CommentedSeq(items) if items else []
            
        res = CommentedMap()
        for child in node.children:
            child_val = self._to_commented_map(child)
            res[child.name] = child_val
            
            # Add instruction comment if available
            instruction = child.metadata.get("instruction")
            if instruction:
                try:
                    res.yaml_add_eol_comment(config.instruction_template.format(gloss=instruction), child.name)
                except Exception:
                    pass
        
        # If this node itself has items (mixed node), add them to 'misc'?
        # In this architecture, we prefer either children OR items.
        if node.items:
            label = self.config.orphans_label_template
            if label and "{}" in label:
                label = label.format(node.name)
            elif not label:
                label = "misc"

            if label not in res:
                res[label] = CommentedSeq(sorted(node.items, key=str.casefold))
            else:
                # Merge items into existing list
                existing = list(res[label])
                res[label] = CommentedSeq(sorted(list(set(existing + node.items)), key=str.casefold))
                
        return res
