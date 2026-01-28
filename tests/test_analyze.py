
import unittest
from wildcards_gen.core import analyze

class TestAnalyze(unittest.TestCase):
    def test_compute_stats_simple(self):
        """Test stats on a simple depth-1 tree."""
        tree = {
            "root": ["leaf1", "leaf2", "leaf3"]
        }
        stats = analyze.compute_dataset_stats(tree)
        
        self.assertEqual(stats.max_depth, 1)
        self.assertEqual(stats.total_leaves, 3)
        # total_nodes counts all non-leaf nodes (root dict counts as a node)
        self.assertGreaterEqual(stats.total_nodes, 1)
        self.assertEqual(stats.leaf_sizes, [3])

    def test_compute_stats_nested(self):
        """Test stats on nested structure."""
        tree = {
            "root": {
                "branch1": ["a", "b"],
                "branch2": {
                    "sub": ["c"]
                }
            }
        }
        stats = analyze.compute_dataset_stats(tree)
        
        self.assertEqual(stats.max_depth, 3) # root -> branch2 -> sub -> c
        self.assertEqual(stats.total_leaves, 3)
        
    def test_suggest_thresholds(self):
        """Test heuristic suggestions."""
        # Create a mock stats object
        stats = analyze.DatasetStats()
        stats.max_depth = 10
        stats.total_leaves = 5000 # Large dataset
        stats.branching_factors = [10]*500
        stats.leaf_sizes = [2]*2500 # Small lists
        
        suggestions = analyze.suggest_thresholds(stats)
        
        # Max depth 10 -> suggest ~8 but capped at 4 usually
        self.assertLessEqual(suggestions['min_depth'], 4)
        
        # 5000 leaves -> suggest flattening
        self.assertGreater(suggestions['min_hyponyms'], 40)
        
        # Small avg leaf size -> low min_leaf_size suggestion
        self.assertTrue(suggestions['min_leaf_size'] >= 3)

if __name__ == '__main__':
    unittest.main()
