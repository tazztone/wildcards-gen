
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from wildcards_gen.core.smart import SmartConfig
# Import normally - let patches handle the mocking during testing
from wildcards_gen.core.arranger import arrange_list

class TestArranger(unittest.TestCase):
    def setUp(self):
        self.items = ["apple", "banana", "dog", "cat", "car"]

    @patch('wildcards_gen.core.arranger.check_dependencies', return_value=True)
    @patch('wildcards_gen.core.arranger.load_embedding_model')
    @patch('wildcards_gen.core.arranger.get_cached_embeddings')
    @patch('wildcards_gen.core.arranger.get_hdbscan_clusters')
    @patch('wildcards_gen.core.arranger.get_lca_name')
    def test_arrange_list_basic(self, mock_get_name, mock_get_clusters, mock_get_embeddings, mock_load_model, mock_check_deps):
        # Setup Mocks
        mock_load_model.return_value = MagicMock()
        mock_get_embeddings.return_value = np.zeros((5, 10)) # Dummy embeddings
        
        # Helper to fake clustering: 0->Group0, 1->Group0, 2->Group1, 3->Group1, 4->-1 (noise)
        mock_get_clusters.return_value = (
            np.array([0, 0, 1, 1, -1]), 
            np.array([1.0, 1.0, 1.0, 1.0, 0.0])
        )
        
        mock_get_name.side_effect = ["fruit", "animal"]
        
        # Run
        groups, leftovers = arrange_list(
            self.items, 
            model_name="dummy", 
            threshold=0.5, 
            min_cluster_size=2
        )
        
        # Verify
        self.assertIn("fruit", groups)
        self.assertIn("animal", groups)
        self.assertEqual(sorted(groups["fruit"]), ["apple", "banana"])
        self.assertEqual(sorted(groups["animal"]), ["cat", "dog"])
        self.assertEqual(leftovers, ["car"])

    @patch('wildcards_gen.core.arranger.check_dependencies', return_value=True)
    @patch('wildcards_gen.core.arranger.load_embedding_model')
    @patch('wildcards_gen.core.arranger.get_cached_embeddings')
    @patch('wildcards_gen.core.arranger.get_hdbscan_clusters')
    @patch('wildcards_gen.core.arranger.get_lca_name')
    def test_arrange_list_threshold_filtering(self, mock_get_name, mock_get_clusters, mock_get_embeddings, mock_load_model, mock_check_deps):
        # Setup: Group 0 has low probability, Group 1 has high
        mock_load_model.return_value = MagicMock()
        mock_get_embeddings.return_value = np.zeros((5, 10))
        
        # apple, banana = cluster 0 (prob 0.1) -> Should be rejected (threshold 0.5)
        # dog, cat = cluster 1 (prob 0.9) -> Should be kept
        # car = noise
        mock_get_clusters.return_value = (
            np.array([0, 0, 1, 1, -1]),
            np.array([0.1, 0.1, 0.9, 0.9, 0.0])
        )
        
        mock_get_name.return_value = "animal"
        
        groups, leftovers = arrange_list(
            self.items, 
            model_name="dummy", 
            threshold=0.5, 
            min_cluster_size=2
        )
        
        # Verify
        self.assertNotIn("fruit", groups)
        self.assertEqual(len(groups), 1)
        self.assertIn("animal", groups)
        self.assertEqual(sorted(groups["animal"]), ["cat", "dog"])
        self.assertIn("apple", leftovers)
        self.assertIn("banana", leftovers)
        self.assertIn("car", leftovers)

    @patch('wildcards_gen.core.arranger.check_dependencies', return_value=True)
    @patch('wildcards_gen.core.arranger.load_embedding_model')
    @patch('wildcards_gen.core.arranger.get_cached_embeddings')
    @patch('wildcards_gen.core.arranger.get_hdbscan_clusters')
    @patch('wildcards_gen.core.arranger.get_lca_name')
    def test_arrange_list_fallback_naming(self, mock_get_name, mock_get_clusters, mock_get_embeddings, mock_load_model, mock_check_deps):
        # Setup: Naming fails (returns None)
        mock_load_model.return_value = MagicMock()
        mock_get_embeddings.return_value = np.zeros((4, 10))
        
        # 4 items, all cluster 0
        mock_get_clusters.return_value = (np.array([0, 0, 0, 0]), np.array([1.0, 1.0, 1.0, 1.0]))
        mock_get_name.return_value = None # Naming failed
        
        items = ["a", "b", "c", "d"]
        groups, leftovers = arrange_list(
            items, 
            model_name="dummy", 
            threshold=0.5, 
            min_cluster_size=2
        )
        
        # Verify
        self.assertEqual(len(groups), 1)
        self.assertIn("Group 1", groups) # Deterministic fallback
        self.assertEqual(sorted(groups["Group 1"]), ["a", "b", "c", "d"])

if __name__ == '__main__':
    unittest.main()
