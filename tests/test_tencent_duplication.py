
import unittest
from unittest.mock import patch, MagicMock
from wildcards_gen.core.datasets import tencent
from wildcards_gen.core.smart import SmartConfig

class TestTencentDuplication(unittest.TestCase):
    
    def test_duplication_on_flatten(self):
        # Mock Data Structure:
        # Root (0) -> Child (1) -> Leaf "Apple"
        # Root (0) -> Child (2) -> Leaf "Banana"
        
        categories = {
            0: {'id': 'n0', 'name': 'Root', 'parent': -1},
            1: {'id': 'n1', 'name': 'Fruit', 'parent': 0},
            2: {'id': 'n2', 'name': 'Veggie', 'parent': 0}, # empty
            3: {'id': 'n3', 'name': 'Apple', 'parent': 1} # Leaf of Fruit
        }
        
        children_map = {
            0: [1, 2],
            1: [3]
        }
        
        roots = [0]
        
        # We need to mock parse_hierarchy_file to return this
        with patch('wildcards_gen.core.datasets.tencent.parse_hierarchy_file') as mock_parse, \
             patch('wildcards_gen.core.datasets.tencent.download_tencent_hierarchy') as mock_dl, \
             patch('wildcards_gen.core.datasets.tencent.ensure_nltk_data'):
            
            mock_parse.return_value = (categories, children_map, roots)
            
            # CONFIGURATION TO TRIGGER BUG:
            # 1. min_leaf_size large enough to cause Child 1 (Fruit) to dissolve.
            #    Fruit has 1 leaf ("Apple"). If min_leaf_size=5, it dissolves.
            # 2. Smart mode enabled.
            # 3. Parent (Root) needs to flatten itself? 
            #    If Fruit dissolves, Root gets "Apple" as orphan.
            #    If Veggie dissolves (empty), Root has only orphans.
            #    If valid_items_added == 0, Root flattens.
            #    Logic: "If all children were pruned/merged, flatten itself"
            
            hierarchy = tencent.generate_tencent_hierarchy(
                smart=True,
                min_leaf_size=5, # Apple (1) < 5 -> Dissolve
                merge_orphans=True, # Allow bubbling
                semantic_arrangement=False # Keep it simple
            )
            
            # Expected: {'Root': ['Apple']} or ['Apple'] depending on if Root is preserved.
            # Bug Expectation: ['Apple', 'Apple']
            
            print("\nResult Hierarchy:")
            print(hierarchy)
            
            # Traverse to find "Apple" count
            def count_apples(node):
                c = 0
                if isinstance(node, list):
                    c += sum(1 for item in node if isinstance(item, str) and item.lower() == 'apple')
                elif isinstance(node, dict):
                    for v in node.values():
                        c += count_apples(v)
                return c
                
            apple_count = count_apples(hierarchy)
            print(f"Apple Count: {apple_count}")
            
            self.assertEqual(apple_count, 1, f"Duplicate items found! Count={apple_count}")

if __name__ == '__main__':
    unittest.main()
