
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from wildcards_gen.core.smart import SmartConfig
from wildcards_gen.core.arranger import arrange_list

class TestArranger(unittest.TestCase):
    def setUp(self):
        self.items = ["apple", "banana", "dog", "cat", "car"]

    @patch('wildcards_gen.core.arranger.check_dependencies', return_value=True)
    @patch('wildcards_gen.core.arranger.load_embedding_model')
    @patch('wildcards_gen.core.arranger.get_cached_embeddings')
    @patch('wildcards_gen.core.arranger.get_lca_name')
    @patch('wildcards_gen.core.arranger.get_medoid_name')
    def test_arrange_list_basic(self, mock_get_medoid, mock_get_lca, mock_get_embeddings, mock_load_model, mock_check_deps):
        # Setup Mocks
        mock_load_model.return_value = MagicMock()
        mock_get_embeddings.return_value = np.zeros((5, 10)) # Dummy embeddings
        
        # Patch HDBSCAN via sys.modules or direct patch?
        # Since hdbscan is imported inside, we need to mock the module or the class if available.
        # Assuming hdbscan IS installed in test env.
        with patch('hdbscan.HDBSCAN') as MockHDBSCAN:
            mock_clusterer = MockHDBSCAN.return_value
            # 0->Group0, 1->Group0, 2->Group1, 3->Group1, 4->-1
            mock_clusterer.labels_ = np.array([0, 0, 1, 1, -1])
            mock_clusterer.probabilities_ = np.array([1.0, 1.0, 1.0, 1.0, 0.0])
            
            mock_get_lca.side_effect = ["fruit", "animal"]
            
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
    @patch('wildcards_gen.core.arranger.get_lca_name')
    def test_arrange_list_threshold_filtering(self, mock_get_name, mock_get_embeddings, mock_load_model, mock_check_deps):
        mock_load_model.return_value = MagicMock()
        mock_get_embeddings.return_value = np.zeros((5, 10))
        
        with patch('hdbscan.HDBSCAN') as MockHDBSCAN:
            mock_clusterer = MockHDBSCAN.return_value
            mock_clusterer.labels_ = np.array([0, 0, 1, 1, -1])
            # Cluster 0: 0.1 (Reject), Cluster 1: 0.9 (Keep)
            mock_clusterer.probabilities_ = np.array([0.1, 0.1, 0.9, 0.9, 0.0])
            
            mock_get_name.return_value = "animal"
            
            groups, leftovers = arrange_list(
                self.items, 
                model_name="dummy", 
                threshold=0.5, 
                min_cluster_size=2
            )
            
            self.assertNotIn("fruit", groups)
            self.assertEqual(len(groups), 1)
            self.assertIn("animal", groups)
            self.assertEqual(sorted(groups["animal"]), ["cat", "dog"])
            self.assertIn("apple", leftovers)
            self.assertIn("banana", leftovers)

    @patch('wildcards_gen.core.arranger.check_dependencies', return_value=True)
    @patch('wildcards_gen.core.arranger.load_embedding_model')
    @patch('wildcards_gen.core.arranger.get_cached_embeddings')
    @patch('wildcards_gen.core.arranger.get_lca_name')
    @patch('wildcards_gen.core.arranger.get_medoid_name')
    def test_arrange_list_fallback_naming(self, mock_get_medoid, mock_get_lca, mock_get_embeddings, mock_load_model, mock_check_deps):
        mock_load_model.return_value = MagicMock()
        mock_get_embeddings.return_value = np.zeros((4, 10))
        
        with patch('hdbscan.HDBSCAN') as MockHDBSCAN:
            mock_clusterer = MockHDBSCAN.return_value
            mock_clusterer.labels_ = np.array([0, 0, 0, 0])
            mock_clusterer.probabilities_ = np.array([1.0, 1.0, 1.0, 1.0])
            
            # Fail both LCA and Medoid
            mock_get_lca.return_value = None 
            mock_get_medoid.return_value = None
            
            items = ["a", "b", "c", "d"]
            groups, leftovers = arrange_list(
                items, 
                model_name="dummy", 
                threshold=0.5, 
                min_cluster_size=2
            )
            
            self.assertEqual(len(groups), 1)
            self.assertIn("Group 1", groups) # Fallback
            self.assertEqual(sorted(groups["Group 1"]), ["a", "b", "c", "d"])

if __name__ == '__main__':
    unittest.main()
