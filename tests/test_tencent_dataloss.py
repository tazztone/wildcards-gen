
import unittest
from unittest.mock import patch, MagicMock
from wildcards_gen.core.datasets import tencent
from wildcards_gen.core.smart import SmartConfig
from ruamel.yaml import CommentedMap

class TestTencentDataLoss(unittest.TestCase):
    
    def test_dataloss_on_arranged_orphans(self):
        # Mock Data Structure:
        # Root (0) -> Child (1) -> Leaf "Apple"
        # Root (0) -> Child (2) -> Leaf "Banana"
        # Both children dissolve due to min_leaf_size=5
        
        categories = {
            0: {'id': 'n0', 'name': 'Root', 'parent': -1},
            1: {'id': 'n1', 'name': 'Fruit', 'parent': 0},
            2: {'id': 'n2', 'name': 'Veggie', 'parent': 0},
            3: {'id': 'n3', 'name': 'Apple', 'parent': 1},
            4: {'id': 'n4', 'name': 'Banana', 'parent': 2}
        }
        children_map = {0: [1, 2], 1: [3], 2: [4]}
        roots = [0]
        
        with patch('wildcards_gen.core.datasets.tencent.parse_hierarchy_file') as mock_parse, \
             patch('wildcards_gen.core.datasets.tencent.download_tencent_hierarchy') as mock_dl, \
             patch('wildcards_gen.core.datasets.tencent.ensure_nltk_data'), \
             patch('wildcards_gen.core.smart.apply_semantic_arrangement') as mock_arrange:
            
            mock_parse.return_value = (categories, children_map, roots)
            
            # Mock arrange to return a Dict when called for Orphans
            # This simulates finding structure in the orphans
            def side_effect(items, config, stats=None, context=None, return_metadata=False):
                # If we are arranging orphans (context starts with "orphans of")
                if context and "orphans of" in context:
                    print(f"Arranging Orphans: {items}")
                    return ({"Group A": items}, [], {}) if return_metadata else ({"Group A": items}, [])
                return (items, [], {}) if return_metadata else (items, [])

            mock_arrange.side_effect = side_effect
            
            # Run with semantic_arrangement=True
            hierarchy = tencent.generate_tencent_hierarchy(
                smart=True,
                min_leaf_size=5, # Force dissolve
                merge_orphans=True,
                semantic_arrangement=True,
                semantic_arrangement_threshold=0.1
            )
            
            print("\nResult Hierarchy:")
            print(hierarchy)
            
            # Expectation: 
            # Root -> Group A -> [Apple, Banana]
            # Bug: Root -> Empty or Missing Group A
            
            def find_apple(node):
                if isinstance(node, list):
                    return "Apple" in node or "apple" in node
                elif isinstance(node, dict):
                    return any(find_apple(v) for v in node.values())
                return False
                
            found = find_apple(hierarchy)
            self.assertTrue(found, "Data Loss! 'Apple' not found in hierarchy.")

if __name__ == '__main__':
    unittest.main()
