
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
    @patch('wildcards_gen.core.arranger.compute_umap_embeddings')
    @patch('wildcards_gen.core.arranger.get_lca_name')
    @patch('wildcards_gen.core.arranger.get_medoid_name')
    def test_arrange_list_basic(self, mock_get_medoid, mock_get_lca, mock_umap, mock_get_embeddings, mock_load_model, mock_check_deps):
        # Setup Mocks
        mock_load_model.return_value = MagicMock()
        mock_get_embeddings.return_value = np.zeros((5, 10))
        mock_umap.return_value = np.zeros((5, 5)) # Reduced embeddings
        
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
    @patch('wildcards_gen.core.arranger.compute_umap_embeddings')
    @patch('wildcards_gen.core.arranger.get_lca_name')
    def test_arrange_list_threshold_filtering(self, mock_get_name, mock_umap, mock_get_embeddings, mock_load_model, mock_check_deps):
        mock_load_model.return_value = MagicMock()
        mock_get_embeddings.return_value = np.zeros((5, 10))
        mock_umap.return_value = np.zeros((5, 5))
        
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
    @patch('wildcards_gen.core.arranger.compute_umap_embeddings')
    @patch('wildcards_gen.core.arranger.get_lca_name')
    @patch('wildcards_gen.core.arranger.get_medoid_name')
    def test_arrange_list_fallback_naming(self, mock_get_medoid, mock_get_lca, mock_umap, mock_get_embeddings, mock_load_model, mock_check_deps):
        mock_load_model.return_value = MagicMock()
        mock_get_embeddings.return_value = np.zeros((4, 10))
        mock_umap.return_value = np.zeros((4, 5))
        
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
            # Expect "Group (a)" because 'a' is the medoid (first item in sorted list usually or mock embeddings make it so?)
            # Medoid calculation uses embeddings. All zero. 
            # If all zero, first item is medoid? 
            # medoid_idx = np.argmin(distances). distances all 0. argmin=0.
            # term[0] is "a".
            self.assertIn("Group (a)", groups) 
            self.assertEqual(sorted(groups["Group (a)"]), ["a", "b", "c", "d"])



    @patch('wildcards_gen.core.arranger.check_dependencies', return_value=True)
    @patch('wildcards_gen.core.arranger.load_embedding_model')
    @patch('wildcards_gen.core.arranger.get_cached_embeddings')
    @patch('wildcards_gen.core.arranger.compute_umap_embeddings')
    @patch('wildcards_gen.core.arranger.get_lca_name')
    def test_return_metadata(self, mock_get_lca, mock_umap, mock_get_embeddings, mock_load_model, mock_check_deps):
        mock_load_model.return_value = MagicMock()
        mock_get_embeddings.return_value = np.zeros((3, 10))
        mock_umap.return_value = np.zeros((3, 5))
        mock_get_lca.return_value = "fruit"
        
        with patch('hdbscan.HDBSCAN') as MockHDBSCAN:
            mock_clusterer = MockHDBSCAN.return_value
            mock_clusterer.labels_ = np.array([0, 0, 0])
            mock_clusterer.probabilities_ = np.array([1.0, 1.0, 1.0])
            
            # Default call (no metadata)
            res = arrange_list(self.items[:3], model_name="dummy", return_metadata=False, min_cluster_size=2)
            self.assertEqual(len(res), 2) # groups, leftovers
            
            # Call with metadata
            groups, leftovers, metadata = arrange_list(self.items[:3], model_name="dummy", return_metadata=True, min_cluster_size=2)
            self.assertIn("fruit", metadata)
            self.assertEqual(metadata["fruit"]["source"], "lca")

    @patch('wildcards_gen.core.arranger.check_dependencies', return_value=True)
    @patch('wildcards_gen.core.arranger.load_embedding_model')
    @patch('wildcards_gen.core.arranger.get_cached_embeddings')
    @patch('wildcards_gen.core.arranger.compute_umap_embeddings')
    @patch('wildcards_gen.core.arranger.get_lca_name')
    @patch('wildcards_gen.core.arranger.get_medoid_name')
    @patch('wildcards_gen.core.arranger.get_primary_synset')
    def test_hybrid_naming_collision(self, mock_get_synset, mock_get_medoid, mock_get_lca, mock_umap, mock_get_embeddings, mock_load_model, mock_check_deps):
        mock_load_model.return_value = MagicMock()
        mock_get_embeddings.return_value = np.zeros((4, 10))
        mock_umap.return_value = np.zeros((4, 5))
        
        # Mock synsets for validation
        mock_lca_synset = MagicMock()
        mock_lca_synset.pos.return_value = 'n'
        mock_lca_synset.offset.return_value = 12345
        
        mock_medoid_synset = MagicMock()
        mock_medoid_synset.pos.return_value = 'n'
        mock_medoid_synset.offset.return_value = 67890
        
        # Simulate that LCA is a hypernym of medoid
        mock_medoid_synset.lowest_common_hypernyms.return_value = [mock_lca_synset]
        
        mock_get_synset.side_effect = lambda x: mock_lca_synset if x == "bird" else mock_medoid_synset

        with patch('hdbscan.HDBSCAN') as MockHDBSCAN:
            mock_clusterer = MockHDBSCAN.return_value
            # Two clusters
            mock_clusterer.labels_ = np.array([0, 0, 1, 1])
            mock_clusterer.probabilities_ = np.array([1.0, 1.0, 1.0, 1.0])
            
            # Both return SAME LCA "bird"
            mock_get_lca.return_value = "bird"
            mock_get_medoid.return_value = None # Fix: prevent MagicMock return
            
            # Define side effect for get_medoid for the two clusters (approx)
            # Actually arranger calls get_medoid inside _generate_descriptive_name or only if LCA fails? 
            # It calls it inside now if needed? No, logic is:
            # 1. Base name = LCA (if exists).
            # 2. Collision check: if name in named_groups -> try hybrid.
            
            # Mock `check_dependencies` is already True.
            
            # We need to simulate that the first cluster grabs "bird", 
            # and the second cluster also gets "bird", triggers collision, 
            # and uses medoid from metadata to resolve it.
            
            # The cluster terms are needed to mock medoid term extraction.
            # But here we just want to verify the key.
            
            res = arrange_list(["a", "b", "c", "d"], model_name="dummy", min_cluster_size=2)
            groups, leftovers = res
            
            # We expect "bird" and "bird (something)" or "bird 2"
            keys = sorted(groups.keys())
            self.assertTrue(any(k.startswith("bird") for k in keys))
            self.assertEqual(len(keys), 2)

if __name__ == '__main__':
    unittest.main()
