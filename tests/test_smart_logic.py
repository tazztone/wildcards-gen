
import unittest
from unittest.mock import MagicMock
from wildcards_gen.core.smart import SmartConfig, should_prune_node, is_synset_significant, handle_small_leaves

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


class TestHandleSmallLeaves(unittest.TestCase):
    """Tests for handle_small_leaves function (data retention logic)."""

    def test_disabled_config_keeps_leaves(self):
        """When smart mode disabled, always return leaves as-is."""
        config = SmartConfig(enabled=False)
        leaves = ['a', 'b']
        value, orphans = handle_small_leaves(leaves, config)
        self.assertEqual(value, ['a', 'b'])
        self.assertEqual(orphans, [])

    def test_small_list_kept_by_default(self):
        """Small lists are kept as-is when merge_orphans=False (100% retention)."""
        config = SmartConfig(enabled=True, min_leaf_size=3, merge_orphans=False)
        leaves = ['a', 'b']  # < 3 items
        value, orphans = handle_small_leaves(leaves, config)
        self.assertEqual(value, ['a', 'b'])
        self.assertEqual(orphans, [])

    def test_small_list_bubbled_up_with_merge_orphans(self):
        """Small lists bubble up when merge_orphans=True."""
        config = SmartConfig(enabled=True, min_leaf_size=3, merge_orphans=True)
        leaves = ['katydid', 'locust']  # < 3 items
        value, orphans = handle_small_leaves(leaves, config)
        self.assertIsNone(value)
        self.assertEqual(orphans, ['katydid', 'locust'])

    def test_large_list_always_kept(self):
        """Lists >= min_leaf_size are always kept regardless of merge_orphans."""
        config = SmartConfig(enabled=True, min_leaf_size=3, merge_orphans=True)
        leaves = ['a', 'b', 'c', 'd']  # >= 3 items
        value, orphans = handle_small_leaves(leaves, config)
        self.assertEqual(value, ['a', 'b', 'c', 'd'])
        self.assertEqual(orphans, [])

    def test_empty_list_handled(self):
        """Empty list returns empty list (not None)."""
        config = SmartConfig(enabled=True, min_leaf_size=3, merge_orphans=False)
        value, orphans = handle_small_leaves([], config)
        self.assertEqual(value, [])
        self.assertEqual(orphans, [])

    def test_single_item_list_kept_by_default(self):
        """Single item list kept when merge_orphans=False."""
        config = SmartConfig(enabled=True, min_leaf_size=3, merge_orphans=False)
        leaves = ['tongs']
        value, orphans = handle_small_leaves(leaves, config)
        self.assertEqual(value, ['tongs'])
        self.assertEqual(orphans, [])

    def test_single_item_bubbled_with_merge_orphans(self):
        """Single item bubbles up when merge_orphans=True."""
        config = SmartConfig(enabled=True, min_leaf_size=3, merge_orphans=True)
        leaves = ['tongs']
        value, orphans = handle_small_leaves(leaves, config)
        self.assertIsNone(value)
        self.assertEqual(orphans, ['tongs'])


class TestSmartConfigMergeOrphans(unittest.TestCase):
    """Tests for SmartConfig merge_orphans field."""

    def test_merge_orphans_default_false(self):
        """merge_orphans defaults to False."""
        config = SmartConfig(enabled=True)
        self.assertFalse(config.merge_orphans)

    def test_merge_orphans_can_be_set(self):
        """merge_orphans can be set to True."""
        config = SmartConfig(enabled=True, merge_orphans=True)
        self.assertTrue(config.merge_orphans)


if __name__ == '__main__':
    unittest.main()
