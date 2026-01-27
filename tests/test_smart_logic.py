
import unittest
from unittest.mock import MagicMock
from wildcards_gen.core.smart import SmartConfig, should_prune_node, is_synset_significant

class TestSmartLogic(unittest.TestCase):
    def setUp(self):
        self.config = SmartConfig(enabled=True, min_depth=6, min_hyponyms=10)

    def test_disabled_config(self):
        """If smart mode is disabled, should_prune_node returns False (defer to depth check)."""
        self.config.enabled = False
        synset = MagicMock()
        self.assertFalse(should_prune_node(synset, 5, False, self.config))

    def test_root_never_pruned(self):
        """Root nodes should never be pruned."""
        synset = MagicMock()
        # Even with 1 child and no significance
        self.assertFalse(should_prune_node(synset, 1, True, self.config))

    def test_linear_chain_pruning(self):
        """Nodes with <= 1 child should be pruned."""
        synset = MagicMock()
        # Mock insignificance
        synset.min_depth.return_value = 10 
        synset.closure.return_value = [] # 0 hyponyms
        
        self.assertTrue(should_prune_node(synset, 1, False, self.config))
        self.assertTrue(should_prune_node(synset, 0, False, self.config))
        
    def test_significant_node_kept(self):
        """Significant nodes (by depth) should be kept even if they have children."""
        synset = MagicMock()
        synset.min_depth.return_value = 5 # < min_depth 6
        
        # Has children > 1 so it's not a linear chain failure
        self.assertFalse(should_prune_node(synset, 2, False, self.config))

    def test_insignificant_node_pruned(self):
        """Nodes that are deep and not branching enough should be pruned."""
        synset = MagicMock()
        synset.min_depth.return_value = 8 # > 6
        # Mock low hyponym count
        hyponyms = [MagicMock() for _ in range(5)] # < 10
        synset.closure.return_value = hyponyms
        
        # Even if it has 2 immediate children, it might be pruned if we enforce significance strictly?
        # WAIT: The implementation says: `if is_synset_significant(synset, config): return False`
        # Then `return True` (prune).
        # So yes, if it's NOT significant, it gets pruned.
        
        self.assertTrue(should_prune_node(synset, 2, False, self.config))

    def test_significant_by_hyponyms(self):
        """Significant because of many descendants."""
        synset = MagicMock()
        synset.min_depth.return_value = 8 # Deep
        # Lots of descendants
        hyponyms = [MagicMock() for _ in range(20)] # > 10
        synset.closure.return_value = hyponyms
        
        self.assertFalse(should_prune_node(synset, 2, False, self.config))

if __name__ == '__main__':
    unittest.main()
