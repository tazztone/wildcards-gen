"""
Comparator for Taxonomy Files.

Handles loading, flattening, and comparing YAML structures.
"""

import logging
from typing import Dict, Any, List, Tuple
from pathlib import Path

from wildcards_gen.core.structure import StructureManager
from wildcards_gen.analytics.metrics import calculate_stability

logger = logging.getLogger(__name__)

class TaxonomyComparator:
    def __init__(self):
        self.mgr = StructureManager()

    def flatten_structure(self, structure: Any) -> Dict[str, str]:
        """
        Flatten a hierarchical structure into term -> path mapping.
        
        Example: {
            "animal": {
                "mammal": ["dog", "cat"]
            }
        }
        becomes:
        {
            "dog": "animal/mammal",
            "cat": "animal/mammal"
        }
        """
        flat_map = {}
        
        def traverse(node, path_parts: List[str]):
            if isinstance(node, dict):
                for k, v in node.items():
                    traverse(v, path_parts + [k])
            elif isinstance(node, list):
                # Leaf list
                current_path = "/".join(path_parts)
                for item in node:
                    flat_map[item] = current_path
        
        traverse(structure, [])
        return flat_map

    def compare(self, file1: str, file2: str) -> Dict[str, Any]:
        """
        Compare two YAML files and return stability metrics.
        """
        struct1 = self.mgr.load_structure(file1)
        struct2 = self.mgr.load_structure(file2)
        
        if not struct1 or not struct2:
            raise ValueError("One or both input files could not be loaded or are empty.")

        map1 = self.flatten_structure(struct1)
        map2 = self.flatten_structure(struct2)
        
        terms1 = set(map1.keys())
        terms2 = set(map2.keys())
        
        metrics = calculate_stability(terms1, map1, terms2, map2)
        
        return {
            "file1": file1,
            "file2": file2,
            "metrics": metrics
        }
